"""
JDBC Driver Manager - Download and manage JDBC driver JAR files.

Provides functionality to download JDBC driver files based on database type
and place them in the appropriate directory for the dbutils application.
"""

import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Callable, List, Optional, Union
import urllib.request
import urllib.parse
import urllib.error


# Import needed items from jdbc_driver_downloader
from .jdbc_driver_downloader import JDBCDriverRegistry
import json

# Default Maven repositories (in descending priority)
DEFAULT_MAVEN_REPOS = [
    "https://repo1.maven.org/maven2/",
    "https://repo.maven.apache.org/maven2/",
]


class JDBCDriverDownloader:
    """Handles downloading JDBC drivers from official sources."""
    
    def __init__(self):
        self.downloads_dir = self._get_driver_directory()
        # Create downloads directory if it doesn't exist
        Path(self.downloads_dir).mkdir(parents=True, exist_ok=True)

    def _get_driver_directory(self) -> str:
        """Get the directory where JDBC drivers should be stored."""
        driver_dir = os.environ.get("DBUTILS_DRIVER_DIR", os.path.expanduser("~/.config/dbutils/drivers"))
        os.makedirs(driver_dir, exist_ok=True)
        return driver_dir

    def _suggest_jar_filename(self, db_type: str, version: str = "latest") -> str:
        """Suggest a filename for a downloaded JAR based on database type."""
        if db_type == "postgresql":
            return f"postgresql-{version}.jar" if version != "latest" else "postgresql-latest.jar"
        elif db_type == "mysql":
            return f"mysql-connector-java-{version}.jar" if version != "latest" else "mysql-connector-java-latest.jar"
        elif db_type == "mariadb":
            return f"mariadb-java-client-{version}.jar" if version != "latest" else "mariadb-java-client-latest.jar"
        elif db_type == "oracle":
            return f"ojdbc{version.replace('.', '')}.jar" if version != "latest" else "ojdbc-latest.jar"
        elif db_type == "sqlserver":
            return f"mssql-jdbc-{version}.jar" if version != "latest" else "mssql-jdbc-latest.jar"
        elif db_type == "db2":
            return f"db2jcc-{version}.jar" if version != "latest" else "db2jcc-latest.jar"
        elif db_type == "jt400":
            return f"jtopen-{version}.jar" if version != "latest" else "jtopen-latest.jar"
        elif db_type == "sqlite":
            return f"sqlite-jdbc-{version}.jar" if version != "latest" else "sqlite-jdbc-latest.jar"
        elif db_type == "h2":
            return f"h2-{version}.jar" if version != "latest" else "h2-latest.jar"
        else:
            return f"{db_type}-jdbc-driver.jar"
        
    def download_driver(
        self, 
        database_type: str, 
        on_progress: Optional[Callable[[int, int], None]] = None,
        version: str = "recommended"
    ) -> Optional[str]:
        """
        Download a JDBC driver JAR file for the specified database type.
        
        Args:
            database_type: Type of database (e.g., 'postgresql', 'mysql', 'oracle')
            on_progress: Optional callback function to report progress (bytes_downloaded, total_bytes)
            version: Version to download ('recommended', 'latest', or specific version string)
            
        Returns:
            Path to downloaded JAR file, or None if download failed
        """
        driver_info = JDBCDriverRegistry.DRIVERS.get(database_type)
        if not driver_info:
            return None
            
        # Determine download URL(s) based on version preference
        download_url = self._get_download_url_for_version(driver_info, version)
        if not download_url:
            # If we can't determine the specific version, try the main download page
            download_url = driver_info.download_url
        
        # Suggest filename(s)
        if version == "recommended":
            if isinstance(download_url, list):
                jar_filename = [self._suggest_jar_filename(database_type, driver_info.recommended_version) for _ in download_url]
            else:
                jar_filename = self._suggest_jar_filename(database_type, driver_info.recommended_version)
        else:
            if isinstance(download_url, list):
                jar_filename = [self._suggest_jar_filename(database_type, version) for _ in download_url]
            else:
                jar_filename = self._suggest_jar_filename(database_type, version)

        if isinstance(jar_filename, list):
            # When multiple artifacts are returned, prefer using the JAR name from the URL
            if isinstance(download_url, list):
                jar_filename = [os.path.basename(url) for url in download_url]
            target_path = [os.path.join(self.downloads_dir, fn) for fn in jar_filename]
        else:
            target_path = os.path.join(self.downloads_dir, jar_filename)
        
        try:
            # First, try to download directly if download_url points to a JAR file
            # If download_url is a list, treat as multiple artifact JAR urls
            if isinstance(download_url, list):
                results = []
                for url, tpath in zip(download_url, target_path):
                    if self._is_jar_url(url):
                        res = self._download_single_file(url, tpath, on_progress)
                        results.append(res)
                    else:
                        # fallback: manual instructions for non-jar pages
                        results.append(self._handle_complex_download(url, tpath, database_type, driver_info, on_progress))

                # Normalize return: single path string when one artifact, list when multiple
                if len(results) == 1:
                    return results[0]
                return results

            # Single URL
            if self._is_jar_url(download_url):
                return self._download_single_file(download_url, target_path, on_progress)
            else:
                # For pages that require manual download or have complex download processes,
                # we'll handle them specially
                return self._handle_complex_download(
                    download_url, target_path, database_type, driver_info, on_progress
                )
        except Exception as e:
            print(f"Download failed for {database_type}: {e}")
            return None
    
    def _get_download_url_for_version(self, driver_info, version: str) -> Optional[str]:
        """Get the appropriate download URL for a specific version."""
        # If the driver defines maven_artifacts, prefer constructing maven artifact URLs
        if getattr(driver_info, 'maven_artifacts', None):
            # Get maven repositories from environment or defaults
            repos = self._get_maven_repos()

            urls = []
            for coord in driver_info.maven_artifacts:
                group, artifact = coord.split(':', 1)
                if version == 'recommended':
                    ver = driver_info.recommended_version
                elif version == 'latest':
                    # Try to fetch latest from metadata for each repo until we succeed
                    ver = self._get_latest_version_from_maven(group, artifact, repos)
                    if not ver:
                        ver = driver_info.recommended_version
                else:
                    ver = version

                # Construct primary jar URL for this artifact/version
                # simple pattern: {repo}{group_path}/{artifact}/{version}/{artifact}-{version}.jar
                group_path = group.replace('.', '/')
                jar_filename = f"{artifact}-{ver}.jar"
                # Use first repo that appears to have the artifact; we'll construct full list
                for repo in repos:
                    urls.append(f"{repo.rstrip('/')}/{group_path}/{artifact}/{ver}/{jar_filename}")

            # We built URLs by trying all repos for every artifact - prefer first repo's entry per artifact
            # Reduce to per-artifact first-url
            filtered = []
            seen_artifact = set()
            for u in urls:
                # extract artifact/version portion
                parts = u.split('/')
                if len(parts) < 4:
                    continue
                art = parts[-3]
                if art in seen_artifact:
                    continue
                seen_artifact.add(art)
                filtered.append(u)

            return filtered if filtered else None

        # No maven artifacts configured - fall back to download_url or alternative URLs
        if version == "recommended":
            return driver_info.download_url
        elif version == "latest":
            # Try to get the latest version URL from alternatives if possible
            if driver_info.alternative_urls:
                for alt_url in driver_info.alternative_urls:
                    if "maven" in alt_url or "repo1.maven.org" in alt_url:
                        # Maven central typically has versioned JARs
                        continue  # For now, use main page
            return driver_info.download_url
        else:
            return driver_info.download_url

    def _get_maven_repos(self) -> List[str]:
        """Get list of Maven repos from environment variable DBUTILS_MAVEN_REPOS or defaults.

        DBUTILS_MAVEN_REPOS supports a JSON array string or a comma-separated string.
        """
        raw = os.environ.get('DBUTILS_MAVEN_REPOS')
        if not raw:
            return DEFAULT_MAVEN_REPOS

        try:
            val = json.loads(raw)
            if isinstance(val, list):
                return val
        except Exception:
            # Fall back to comma-separated
            return [p.strip() for p in raw.split(',') if p.strip()]

        return DEFAULT_MAVEN_REPOS

    def _get_latest_version_from_maven(self, group: str, artifact: str, repos: List[str]) -> Optional[str]:
        """Query repositories for maven-metadata and return latest or release version.

        Returns first found version from repositories tried in order.
        """
        for repo in repos:
            metadata_url = f"{repo.rstrip('/')}/{group.replace('.', '/')}/{artifact}/maven-metadata.xml"
            try:
                req = urllib.request.Request(metadata_url)
                req.add_header('User-Agent', 'dbutils-jdbc-downloader/1.0')
                with urllib.request.urlopen(req) as resp:
                    xml = resp.read().decode('utf-8')
                    # naive parse for <latest> or <release>
                    if '<latest>' in xml:
                        start = xml.find('<latest>') + len('<latest>')
                        end = xml.find('</latest>', start)
                        if end > start:
                            return xml[start:end].strip()
                    if '<release>' in xml:
                        start = xml.find('<release>') + len('<release>')
                        end = xml.find('</release>', start)
                        if end > start:
                            return xml[start:end].strip()
                    # fallback: pick last <version> in <versions>
                    if '<versions>' in xml:
                        ver_block_start = xml.find('<versions>')
                        ver_block_end = xml.find('</versions>', ver_block_start)
                        if ver_block_start != -1 and ver_block_end != -1:
                            block = xml[ver_block_start:ver_block_end]
                            versions = [v for v in block.split('<version>') if '</version>' in v]
                            if versions:
                                last = versions[-1]
                                end = last.find('</version>')
                                if end != -1:
                                    return last[:end].strip()
            except Exception:
                continue

        return None
    
    def _is_jar_url(self, url: str) -> bool:
        """Check if the URL points directly to a JAR file."""
        parsed = urllib.parse.urlparse(url)
        return parsed.path.lower().endswith('.jar')
    
    def _download_single_file(
        self,
        url: str,
        target_path: str,
        on_progress: Optional[Callable[[int, int], None]] = None
    ) -> Optional[str]:
        """Download a single JAR file from a direct URL."""
        temp_path = None
        try:
            # Create a temporary file for download
            temp_fd, temp_path = tempfile.mkstemp(suffix='.jar', dir=self.downloads_dir)

            with os.fdopen(temp_fd, 'wb') as temp_file:
                # Create request with user agent to avoid blocking by some servers
                req = urllib.request.Request(url)
                req.add_header('User-Agent', 'dbutils-jdbc-downloader/1.0')

                # Open the URL
                with urllib.request.urlopen(req) as response:
                    total_size = int(response.headers.get('Content-Length', 0))
                    downloaded = 0

                    # Download in chunks
                    chunk_size = 8192
                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break

                        temp_file.write(chunk)
                        downloaded += len(chunk)

                        # Report progress if callback provided
                        if on_progress:
                            on_progress(downloaded, total_size)

            # Move temp file to target location
            if temp_path and os.path.exists(temp_path):
                shutil.move(temp_path, target_path)
            return target_path

        except Exception as e:
            # Clean up temp file if download failed
            try:
                if temp_path and os.path.exists(temp_path):
                    os.unlink(temp_path)
            except:
                pass
            print(f"Error downloading JAR: {e}")
            return None
    
    def _handle_complex_download(
        self,
        download_page_url: str,
        target_path: str,
        database_type: str,
        driver_info,
        on_progress: Optional[Callable[[int, int], None]] = None
    ) -> Optional[str]:
        """
        Handle complex downloads where the URL is a web page that requires manual navigation.
        
        For many commercial databases, we can't directly download JARs programmatically
        due to licensing, login requirements, or complex version selectors. In these cases,
        we'll return information for the user instead of automating download.
        """
        # For complex downloads, we'll provide the download page and let the user download manually
        # This is often necessary for Oracle, DB2, and other commercial databases
        print(f"Navigate to: {download_page_url}")
        print(f"Download the JDBC driver for {database_type}")
        print(f"Save to: {target_path}")
        return None  # Indicate that manual download is needed
    
    def get_download_instructions(self, database_type: str) -> Optional[str]:
        """Get human-readable download instructions for a database type."""
        driver_info = JDBCDriverRegistry.DRIVERS.get(database_type)
        if not driver_info:
            return None
            
        instructions = []
        instructions.append(f"JDBC Driver: {driver_info.name}")
        instructions.append(f"Driver Class: {driver_info.driver_class}")
        instructions.append(f"License: {driver_info.license}")
        instructions.append(f"Minimum Java: {driver_info.min_java_version}")
        instructions.append(f"Recommended Version: {driver_info.recommended_version}")
        instructions.append("")
        instructions.append(f"Primary download: {driver_info.download_url}")
        
        if driver_info.alternative_urls:
            instructions.append("Alternative sources:")
            for alt_url in driver_info.alternative_urls:
                instructions.append(f"  - {alt_url}")
        
        instructions.append("")
        instructions.append(f"Save JAR to: {self.downloads_dir}")
        instructions.append("Then configure in the provider settings")
        
        return "\n".join(instructions)
    
    def find_existing_drivers(self, database_type: str) -> list:
        """Find existing driver JAR files that match the specified database type."""
        driver_files = []
        # Look for files containing the database type name
        for file_path in Path(self.downloads_dir).glob(f"*.jar"):
            filename_lower = file_path.name.lower()
            if database_type.lower() in filename_lower or "jdbc" in filename_lower:
                driver_files.append(str(file_path))
        
        return driver_files

    def list_available_drivers(self) -> List[str]:
        """List all available driver JARs in the driver directory."""
        driver_files = []
        for file_path in Path(self.downloads_dir).glob("*.jar"):
            driver_files.append(file_path.name)
        return driver_files


# Convenience function for direct downloads
def download_jdbc_driver(
    database_type: str, 
    on_progress: Optional[Callable[[int, int], None]] = None,
    version: str = "recommended"
) -> Optional[str]:
    """
    Convenience function to download a JDBC driver.
    
    Args:
        database_type: Type of database (e.g., 'postgresql', 'mysql', 'oracle')
        on_progress: Optional callback to report download progress
        version: Version to download ('recommended', 'latest', or specific version)
        
    Returns:
        Path to downloaded JAR file, or None if failed
    """
    downloader = JDBCDriverDownloader()
    return downloader.download_driver(database_type, on_progress, version)


def get_jdbc_driver_download_info(database_type: str) -> Optional[str]:
    """Get download information/instructions for a specific database type."""
    downloader = JDBCDriverDownloader()
    return downloader.get_download_instructions(database_type)


def find_existing_jdbc_drivers(database_type: str) -> list:
    """Find existing JDBC driver JARs for a specific database type."""
    downloader = JDBCDriverDownloader()
    return downloader.find_existing_drivers(database_type)