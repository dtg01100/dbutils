"""
JDBC Driver Auto-Downloader - Automatic download of JDBC drivers for Qt GUI.

This module provides functionality to automatically download JDBC drivers based on
database requirements, with a focus on Qt GUI integration.

Notes for maintainers/testers:
- `license_store` is used by this module to validate licensing for drivers that
    require a license. Importing `license_store` as a module and accessing
    `license_store.is_license_accepted()` (rather than importing the function at
    module import-time) makes it easier to monkeypatch behavior during tests.
- `test_repository_connectivity` is a helper for runtime status checks and has
    been explicitly turned off for pytest collection (``__test__ = False``). The
    function also attempts the `timeout` kw arg for `urlopen` first and falls
    back to calling `urlopen` without it to support tests that monkeypatch
    `urllib.request.urlopen` with a stub not accepting `timeout`.

Enhanced with:w
- Robust error handling and retry logic
- Detailed progress tracking
- License management integration
- Repository connectivity testing
"""

import logging
import os
import random
import shutil
import tempfile
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Callable, List, Optional, Tuple

# Import license store functions for license validation

# Import unified configuration module
try:
    from ...config.dbutils_config import (
        construct_maven_artifact_url,
        construct_metadata_url,
        get_driver_directory,
        get_maven_repositories,
    )
except ImportError:
    from dbutils.config.dbutils_config import (
        get_driver_directory,
        get_maven_repositories,
    )
from . import license_store
from dbutils.gui.jdbc_driver_downloader import JDBCDriverRegistry

# Maven repository URLs for common JDBC drivers - now loaded from config
try:
    MAVEN_REPOSITORIES = get_maven_repositories()
    if not MAVEN_REPOSITORIES:
        # Fallback to default repositories if none configured
        MAVEN_REPOSITORIES = [
            "https://repo1.maven.org/maven2/",
            "https://repo.maven.apache.org/maven2/",
            "https://maven.aliyun.com/repository/central/"
        ]
except Exception:
    # Fallback to hardcoded defaults if config system fails
    MAVEN_REPOSITORIES = [
        "https://repo1.maven.org/maven2/",
        "https://repo.maven.apache.org/maven2/",
        "https://maven.aliyun.com/repository/central/"
    ]

# Maximum retry attempts for transient failures
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY_BASE = 1.0  # seconds

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database-specific JDBC driver coordinates
JDBC_DRIVER_COORDINATES = {
    'postgresql': {
        'group_id': 'org.postgresql',
        'artifact_id': 'postgresql',
        'metadata_url': 'https://repo1.maven.org/maven2/org/postgresql/postgresql/maven-metadata.xml'
    },
    'mysql': {
        'group_id': 'mysql',
        'artifact_id': 'mysql-connector-java',
        'metadata_url': 'https://repo1.maven.org/maven2/mysql/mysql-connector-java/maven-metadata.xml'
    },
    'mariadb': {
        'group_id': 'org.mariadb.jdbc',
        'artifact_id': 'mariadb-java-client',
        'metadata_url': 'https://repo1.maven.org/maven2/org/mariadb/jdbc/mariadb-java-client/maven-metadata.xml'
    },
    'sqlserver': {
        'group_id': 'com.microsoft.sqlserver',
        'artifact_id': 'mssql-jdbc',
        'metadata_url': 'https://repo1.maven.org/maven2/com/microsoft/sqlserver/mssql-jdbc/maven-metadata.xml'
    },
    'sqlite': {
        'group_id': 'org.xerial',
        'artifact_id': 'sqlite-jdbc',
        'metadata_url': 'https://repo1.maven.org/maven2/org/xerial/sqlite-jdbc/maven-metadata.xml'
    },
    'h2': {
        'group_id': 'com.h2database',
        'artifact_id': 'h2',
        'metadata_url': 'https://repo1.maven.org/maven2/com/h2database/h2/maven-metadata.xml'
    },
    'derby': {
        'group_id': 'org.apache.derby',
        'artifact_id': 'derby',
        'metadata_url': 'https://repo1.maven.org/maven2/org/apache/derby/derby/maven-metadata.xml'
    }
}


def get_latest_version_from_maven_metadata(metadata_url: str) -> Optional[str]:
    """Retrieve the latest version from Maven metadata XML with retry logic."""
    for attempt in range(MAX_RETRY_ATTEMPTS):
        try:
            response = urllib.request.urlopen(metadata_url)
            metadata_xml = response.read().decode('utf-8')
            root = ET.fromstring(metadata_xml)

            # Find the latest release version
            versioning = root.find('versioning')
            if versioning is not None:
                latest = versioning.find('latest')
                if latest is not None:
                    return latest.text

                release = versioning.find('release')
                if release is not None:
                    return release.text

            # If no latest/release found, get the last version in the list
            versions = root.find('versioning/versions')
            if versions is not None:
                version_elements = versions.findall('version')
                if version_elements:
                    return version_elements[-1].text

            return None
        except urllib.error.URLError as e:
            if attempt < MAX_RETRY_ATTEMPTS - 1:
                delay = RETRY_DELAY_BASE * (2 ** attempt) + random.uniform(0, 1)
                logger.warning(f"Attempt {attempt + 1} failed to fetch metadata from {metadata_url}: {e}. Retrying in {delay:.1f}s...")
                time.sleep(delay)
                continue
            logger.error(f"Could not fetch version metadata from {metadata_url} after {MAX_RETRY_ATTEMPTS} attempts: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching version metadata from {metadata_url}: {e}")
            return None
    return None

def get_version_with_fallback(db_type: str, requested_version: str = "latest") -> str:
    """Get version with fallback mechanism for a specific database type."""
    if requested_version != "latest":
        return requested_version

    # Try to get latest version from metadata
    coords = JDBC_DRIVER_COORDINATES.get(db_type)
    if not coords or not coords.get('metadata_url'):
        return requested_version

    latest_version = get_latest_version_from_maven_metadata(coords['metadata_url'])
    if latest_version:
        return latest_version

    # Fallback to hardcoded versions if metadata fetch fails
    fallback_versions = {
        "sqlite": "3.42.0.0",
        "h2": "2.2.224",
        "derby": "10.15.2.0",
        "hsqldb": "2.7.2",
        "duckdb": "0.10.2",
        "postgresql": "42.6.0",
        "mysql": "8.0.33",
        "mariadb": "3.1.4",
        "sqlserver": "12.4.2.jre11"
    }

    return fallback_versions.get(db_type, requested_version)

def resolve_version_with_strategy(db_type: str, requested_version: str = "latest") -> str:
    """Resolve version using configured strategy with fallback mechanisms."""
    # Get version resolution strategy from config
    try:
        config_file = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'config', 'auto_download_config.json')
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                config_data = json.load(f)
            strategy = config_data.get('version_management', {}).get('version_resolution_strategy', 'latest_first')
        else:
            strategy = 'latest_first'
    except Exception:
        strategy = 'latest_first'

    if strategy == 'latest_first':
        # Try latest first, then fallback to specific versions
        version = get_version_with_fallback(db_type, requested_version)
        if version != "latest" and version is not None:
            return version

        # If still not resolved, try fallback versions
        fallback_versions = {
            "sqlite": ["3.42.0.0", "3.41.2.2", "3.40.1.0"],
            "h2": ["2.2.224", "2.2.220", "2.1.214"],
            "derby": ["10.15.2.0", "10.14.2.0", "10.13.1.1"],
            "hsqldb": ["2.7.2", "2.7.1", "2.7.0"],
            "duckdb": ["0.10.2", "0.10.1", "0.10.0"]
        }

        for fallback_version in fallback_versions.get(db_type, []):
            if fallback_version:
                return fallback_version

    # Default fallback
    return requested_version


def get_jdbc_driver_url(db_type: str, version: str = "latest", repo_index: int = 0) -> Optional[str]:
    """Get the download URL for a specific JDBC driver and version with repository fallback."""
    if db_type not in JDBC_DRIVER_COORDINATES:
        return None

    coords = JDBC_DRIVER_COORDINATES[db_type]

    # Get latest version if requested
    if version == "latest" and coords.get('metadata_url'):
        latest_ver = get_latest_version_from_maven_metadata(coords['metadata_url'])
        if latest_ver:
            version = latest_ver

    # Use new repository prioritization system
    return get_repository_with_fallback(db_type, version)


def download_jdbc_driver(
    db_type: str,
    version: str = "latest",
    target_dir: Optional[str] = None,
    on_progress: Optional[Callable[[int, int], None]] = None,
    on_status: Optional[Callable[[str], None]] = None
) -> Optional[str]:
    """
    Download a JDBC driver JAR file for the specified database type with enhanced error handling.

    Args:
        db_type: Type of database (e.g., 'postgresql', 'mysql', 'oracle')
        version: Version to download ('latest' or specific version)
        target_dir: Directory to save the JAR (defaults to standard location)
        on_progress: Callback for progress updates (downloaded, total bytes)
        on_status: Callback for status messages (enhanced user feedback)

    Returns:
        Path to downloaded JAR file, or None if failed
    """
    # License validation before download - only for drivers that require a license
    driver_info = JDBCDriverRegistry.DRIVERS.get(db_type)
    if driver_info and getattr(driver_info, 'requires_license', False):
        license_key = f"jdbc_driver_{db_type}"
        if not license_store.is_license_accepted(license_key):
            error_msg = f"License not accepted for {db_type}. Please accept the license before downloading."
            logger.error(error_msg)
            if on_status:
                on_status(f"Error: {error_msg}")
            return None

    # Resolve version using new version management system
    resolved_version = resolve_version_with_strategy(db_type, version)
    logger.info(f"Resolved version for {db_type}: {resolved_version}")

    # Get the download URL with new repository prioritization
    download_url = get_jdbc_driver_url(db_type, resolved_version)
    if not download_url:
        error_msg = f"No download URL available for {db_type}"
        logger.error(error_msg)
        if on_status:
            on_status(f"Error: {error_msg}")
        return None

    # Set target directory
    if target_dir is None:
        target_dir = get_driver_directory()

    # Create target directory if it doesn't exist
    Path(target_dir).mkdir(parents=True, exist_ok=True)

    # Determine filename from URL
    filename = os.path.basename(download_url)

    # Check if file already exists
    target_path = os.path.join(target_dir, filename)
    if os.path.exists(target_path):
        logger.info(f"File {filename} already exists at {target_path}")
        if on_status:
            on_status(f"Driver already exists: {filename}")
        return target_path

    # Enhanced download with retry logic
    for attempt in range(MAX_RETRY_ATTEMPTS):
        try:
            # Create temporary file for download
            temp_fd, temp_path = tempfile.mkstemp(suffix='.jar', dir=target_dir)

            with os.fdopen(temp_fd, 'wb') as temp_file:
                # Create request with user agent
                req = urllib.request.Request(download_url)
                req.add_header('User-Agent', 'dbutils-jdbc-downloader/1.0')

                # Open the URL and download
                with urllib.request.urlopen(req) as response:
                    total_size = int(response.headers.get('Content-Length', 0))
                    downloaded = 0
                    chunk_size = 8192
                    start_time = time.time()
                    last_update_time = start_time - 0.6  # ensure first speed update can be emitted during tests

                    if on_status:
                        on_status(f"Starting download from {download_url}")

                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break

                        temp_file.write(chunk)
                        downloaded += len(chunk)

                        # Calculate download speed and estimated time remaining
                        current_time = time.time()
                        elapsed = current_time - start_time
                        if elapsed > 0:
                            speed = downloaded / elapsed  # bytes per second
                            if total_size > 0:
                                remaining = (total_size - downloaded) / speed if speed > 0 else 0
                                if current_time - last_update_time >= 0.5:  # Update every 0.5 seconds
                                    status_msg = f"Downloading {filename}: {downloaded/1024/1024:.1f}MB of {total_size/1024/1024:.1f}MB ({speed/1024/1024:.1f}MB/s, {int(remaining)}s remaining)"
                                    if on_status:
                                        on_status(status_msg)
                                    last_update_time = current_time

                        if on_progress:
                            on_progress(downloaded, total_size)

            # Move temp file to final location
            shutil.move(temp_path, target_path)
            logger.info(f"Successfully downloaded {filename} to {target_path}")
            if on_status:
                on_status(f"Download complete: {filename}")
            return target_path

        except urllib.error.HTTPError as e:
            if e.code == 404:
                # Try fallback repository if available
                if attempt < MAX_RETRY_ATTEMPTS - 1 and len(MAVEN_REPOSITORIES) > 1:
                    fallback_url = get_jdbc_driver_url(db_type, version, repo_index=attempt + 1)
                    if fallback_url and fallback_url != download_url:
                        logger.warning(f"Driver not found at {download_url}, trying fallback repository...")
                        if on_status:
                            on_status(f"Trying fallback repository for {db_type}...")
                        download_url = fallback_url
                        continue
                error_msg = f"JDBC driver not found for {db_type} version {version} (HTTP {e.code}). URL tried: {download_url}"
                logger.error(error_msg)
                if on_status:
                    on_status(f"Error: {error_msg}")
                return None
            elif e.code in [500, 502, 503, 504]:  # Server errors, retry
                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    delay = RETRY_DELAY_BASE * (2 ** attempt) + random.uniform(0, 1)
                    logger.warning(f"Server error {e.code} downloading {db_type}: {e}. Retrying in {delay:.1f}s...")
                    if on_status:
                        on_status(f"Server error {e.code}. Retrying in {delay:.1f}s...")
                    time.sleep(delay)
                    continue
                else:
                    error_msg = f"Server error {e.code} downloading {db_type} after {MAX_RETRY_ATTEMPTS} attempts: {e}"
                    logger.error(error_msg)
                    if on_status:
                        on_status(f"Error: {error_msg}")
                    return None
            else:
                error_msg = f"HTTP error {e.code} downloading JDBC driver: {e}"
                logger.error(error_msg)
                if on_status:

                    on_status(f"Error: {error_msg}")
                return None

        except urllib.error.URLError as e:
            if attempt < MAX_RETRY_ATTEMPTS - 1:
                delay = RETRY_DELAY_BASE * (2 ** attempt) + random.uniform(0, 1)
                logger.warning(f"Network error downloading {db_type}: {e}. Retrying in {delay:.1f}s...")
                if on_status:
                    on_status(f"Network error. Retrying in {delay:.1f}s...")
                time.sleep(delay)
                continue
            else:
                error_msg = f"Network error downloading JDBC driver after {MAX_RETRY_ATTEMPTS} attempts: {e}"
                logger.error(error_msg)
                if on_status:
                    on_status(f"Error: {error_msg}")
                return None

        except Exception as e:
            error_msg = f"Error downloading JDBC driver: {e}"
            logger.error(error_msg)
            if on_status:
                on_status(f"Error: {error_msg}")
            return None

    return None


def get_driver_directory() -> str:
    """Get the standard directory for JDBC drivers."""
    # Use dynamic path resolution from config
    from dbutils.config.dbutils_config import get_driver_directory as config_get_driver_directory
    return config_get_driver_directory()


def list_installed_drivers() -> List[str]:
    """List all JDBC driver JAR files in the driver directory."""
    driver_dir = get_driver_directory()
    driver_files = []

    for file_path in Path(driver_dir).glob("*.jar"):
        driver_files.append(file_path.name)

    return driver_files


def find_existing_drivers(db_type: str) -> List[str]:
    """Find existing drivers for a specific database type."""
    driver_dir = get_driver_directory()
    drivers = []

    # Look for JAR files matching the database type
    for file_path in Path(driver_dir).glob("*.jar"):
        name_lower = file_path.name.lower()
        db_type_lower = db_type.lower()

        if (db_type_lower in name_lower or
            (db_type == 'sqlserver' and 'mssql' in name_lower) or
            (db_type == 'postgres' and 'postgres' in name_lower)):
            drivers.append(str(file_path))

    return drivers


def get_jdbc_driver_download_info(db_type: str) -> Optional[str]:
    """Get download information for a specific database type with enhanced details."""
    coords = JDBC_DRIVER_COORDINATES.get(db_type)
    if not coords:
        return f"No download information available for {db_type}"

    # Get latest version
    latest_version = "Unknown"
    if coords.get('metadata_url'):
        latest_version = get_latest_version_from_maven_metadata(coords['metadata_url']) or "Unknown"

    # Test repository connectivity
    repo_status = "Unknown"
    if coords.get('metadata_url'):
        try:
            response = urllib.request.urlopen(coords['metadata_url'])
            response.close()
            repo_status = "Available"
        except Exception:
            repo_status = "Unavailable"

    info = [
        f"JDBC Driver: {db_type.title()}",
        f"Group ID: {coords['group_id']}",
        f"Artifact: {coords['artifact_id']}",
        f"Latest Version: {latest_version}",
        f"Repository Status: {repo_status}",
        f"Download Location: {get_driver_directory()}",
        "",
        f"Will download from: {get_jdbc_driver_url(db_type, 'latest') or 'N/A'}"
    ]

    return "\n".join(info)

def test_repository_connectivity(repository_url: str) -> Tuple[bool, str]:
    """
    Test connectivity to a Maven repository with detailed status.

    Returns:
        Tuple of (success: bool, status_message: str)
    """
    try:
        # Test with a simple HEAD request to the repository root
        req = urllib.request.Request(repository_url, method='HEAD')
        req.add_header('User-Agent', 'dbutils-jdbc-downloader/1.0')
        try:
            resp_ctx = urllib.request.urlopen(req, timeout=5)
        except TypeError:
            resp_ctx = urllib.request.urlopen(req)

        with resp_ctx as response:
            status_code = response.getcode()

        if status_code == 200:
            return True, f"Repository {repository_url} is available (HTTP 200)"
        else:
            return False, f"Repository {repository_url} returned HTTP {status_code}"
    except urllib.error.URLError as e:
        return False, f"Repository {repository_url} is unavailable: {e.reason}"
    except Exception as e:
        return False, f"Repository {repository_url} error: {str(e)}"

# Prevent pytest from collecting this helper function as a test
test_repository_connectivity.__test__ = False

def get_repository_status() -> List[Tuple[str, bool, str]]:
    """Get status of all configured Maven repositories with detailed messages."""
    results = []
    for repo in MAVEN_REPOSITORIES:
        success, message = test_repository_connectivity(repo)
        results.append((repo, success, message))
    return results

def get_prioritized_repositories() -> List[str]:
    """Get repositories prioritized by connectivity and configuration."""
    # Test all repositories and sort by connectivity
    repo_status = get_repository_status()

    # Sort repositories: connected first, then by response time
    connected_repos = []
    disconnected_repos = []

    for repo, success, _ in repo_status:
        if success:
            connected_repos.append(repo)
        else:
            disconnected_repos.append(repo)

    # Return connected repositories first, then disconnected (as fallback)
    return connected_repos + disconnected_repos

def get_repository_with_fallback(db_type: str, version: str = "latest") -> Optional[str]:
    """Get repository URL with fallback mechanism for a specific database type."""
    # Try prioritized repositories first
    prioritized_repos = get_prioritized_repositories()

    for repo_index, repo_url in enumerate(prioritized_repos):
        # Try to construct URL with this repository
        try:
            from dbutils.config.dbutils_config import construct_maven_artifact_url

            # Parse maven coordinates from db_type
            coords = JDBC_DRIVER_COORDINATES.get(db_type)
            if not coords:
                return None

            artifact_url = construct_maven_artifact_url(
                coords['group_id'],
                coords['artifact_id'],
                version,
                repo_index
            )

            if artifact_url:
                return artifact_url

        except Exception:
            continue

    # Fallback to direct URL construction if config system fails
    for repo_url in prioritized_repos:
        coords = JDBC_DRIVER_COORDINATES.get(db_type)
        if not coords:
            continue

        group_path = coords['group_id'].replace('.', '/')
        jar_filename = f"{coords['artifact_id']}-{version}.jar"
        download_url = f"{repo_url.rstrip('/')}/{group_path}/{coords['artifact_id']}/{version}/{jar_filename}"

        # Test if URL is accessible
        try:
            success, _ = test_repository_connectivity(repo_url)
            if success:
                return download_url
        except Exception:
            continue

    return None
