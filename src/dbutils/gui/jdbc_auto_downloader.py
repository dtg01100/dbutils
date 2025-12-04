"""
JDBC Driver Auto-Downloader - Automatic download of JDBC drivers for Qt GUI.

This module provides functionality to automatically download JDBC drivers based on
database requirements, with a focus on Qt GUI integration.
"""

import os
import shutil
import tempfile
import urllib.request
import urllib.error
from pathlib import Path
from typing import Callable, List, Optional, Tuple
import xml.etree.ElementTree as ET


# Maven repository URLs for common JDBC drivers
MAVEN_REPOSITORIES = [
    "https://repo1.maven.org/maven2/",
    "https://repo.maven.apache.org/maven2/",
]

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
    """Retrieve the latest version from Maven metadata XML."""
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
    except Exception as e:
        print(f"Could not fetch version metadata from {metadata_url}: {e}")
        return None


def get_jdbc_driver_url(db_type: str, version: str = "latest") -> Optional[str]:
    """Get the download URL for a specific JDBC driver and version."""
    if db_type not in JDBC_DRIVER_COORDINATES:
        return None
    
    coords = JDBC_DRIVER_COORDINATES[db_type]
    
    # Get latest version if requested
    if version == "latest" and coords.get('metadata_url'):
        latest_ver = get_latest_version_from_maven_metadata(coords['metadata_url'])
        if latest_ver:
            version = latest_ver
    
    # Construct Maven URL: https://repo1.maven.org/maven2/group_id/artifact_id/version/artifact_id-version.jar
    maven_repo = MAVEN_REPOSITORIES[0]  # Use primary repo
    group_path = coords['group_id'].replace('.', '/')
    jar_filename = f"{coords['artifact_id']}-{version}.jar"
    download_url = f"{maven_repo}{group_path}/{coords['artifact_id']}/{version}/{jar_filename}"
    
    return download_url


def download_jdbc_driver(
    db_type: str, 
    version: str = "latest", 
    target_dir: Optional[str] = None, 
    on_progress: Optional[Callable[[int, int], None]] = None
) -> Optional[str]:
    """
    Download a JDBC driver JAR file for the specified database type.
    
    Args:
        db_type: Type of database (e.g., 'postgresql', 'mysql', 'oracle')
        version: Version to download ('latest' or specific version)
        target_dir: Directory to save the JAR (defaults to standard location)
        on_progress: Callback for progress updates (downloaded, total bytes)
    
    Returns:
        Path to downloaded JAR file, or None if failed
    """
    # Get the download URL
    download_url = get_jdbc_driver_url(db_type, version)
    if not download_url:
        print(f"No download URL available for {db_type}")
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
        print(f"File {filename} already exists at {target_path}")
        return target_path
    
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
                
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                        
                    temp_file.write(chunk)
                    downloaded += len(chunk)
                    
                    if on_progress:
                        on_progress(downloaded, total_size)
        
        # Move temp file to final location
        shutil.move(temp_path, target_path)
        print(f"Successfully downloaded {filename} to {target_path}")
        return target_path
        
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(f"JDBC driver not found for {db_type} version {version}. URL tried: {download_url}")
        else:
            print(f"HTTP error downloading JDBC driver: {e}")
        return None
    except Exception as e:
        print(f"Error downloading JDBC driver: {e}")
        return None


def get_driver_directory() -> str:
    """Get the standard directory for JDBC drivers."""
    driver_dir = os.environ.get("DBUTILS_DRIVER_DIR", os.path.expanduser("~/.config/dbutils/drivers"))
    os.makedirs(driver_dir, exist_ok=True)
    return driver_dir


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
    """Get download information for a specific database type."""
    coords = JDBC_DRIVER_COORDINATES.get(db_type)
    if not coords:
        return f"No download information available for {db_type}"
    
    # Get latest version
    latest_version = "Unknown"
    if coords.get('metadata_url'):
        latest_version = get_latest_version_from_maven_metadata(coords['metadata_url']) or "Unknown"
    
    info = [
        f"JDBC Driver: {db_type.title()}",
        f"Group ID: {coords['group_id']}",
        f"Artifact: {coords['artifact_id']}",
        f"Latest Version: {latest_version}",
        f"Download Location: {get_driver_directory()}",
        "",
        f"Will download from: {get_jdbc_driver_url(db_type, 'latest') or 'N/A'}"
    ]
    
    return "\n".join(info)