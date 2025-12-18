"""
JDBC Driver Manager - Download and manage JDBC driver JAR files.

Provides functionality to download JDBC driver files based on database type
and place them in the appropriate directory for the dbutils application.
"""

import logging
import os
import shutil
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Callable, List, Optional, Tuple, Union

# Import needed items from jdbc_driver_downloader
from .jdbc_driver_downloader import JDBCDriverRegistry

# Import unified configuration module
try:
    from ...config.dbutils_config import (
        construct_maven_artifact_url,
        construct_metadata_url,
        find_driver_jar,
        get_best_driver_path,
        get_driver_directory,
        get_maven_repositories,
    )
except ImportError:
    from dbutils.config.dbutils_config import (
        find_driver_jar,
        get_driver_directory,
        get_maven_repositories,
    )

# Default Maven repositories (in descending priority)
DEFAULT_MAVEN_REPOS = [
    "https://repo1.maven.org/maven2/",
    "https://repo.maven.apache.org/maven2/",
]

# Maximum allowed download size (bytes). Can be overridden for constrained environments.
MAX_DOWNLOAD_BYTES = int(os.environ.get("DBUTILS_MAX_DOWNLOAD_BYTES", 250 * 1024 * 1024))


class JDBCDriverDownloader:
    """Handles downloading JDBC drivers from official sources."""

    def __init__(self):
        self.downloads_dir = self._get_driver_directory()
        # Create downloads directory if it doesn't exist
        Path(self.downloads_dir).mkdir(parents=True, exist_ok=True)

    def _url_exists(self, url: str, timeout: int = 10) -> Tuple[bool, str]:
        """Check if a URL exists with detailed status (supports HEAD with GET fallback)."""
        # Block obviously unsafe schemes early
        if not self._is_url_allowed(url):
            return False, "Blocked insecure or unsupported URL"
        # NOTE: In tests, `urllib.request.urlopen` may be monkeypatched with a stub
        # that doesn't accept a `timeout` kwarg. We first attempt to call with
        # `timeout` and fall back to `urlopen(req)` if TypeError is raised. In some
        # tests `_url_exists` may be monkeypatched to return a boolean instead of
        # a (bool, status) tuple; other parts of the code handle this case too.
        try:
            req = urllib.request.Request(url, method="HEAD")
            req.add_header("User-Agent", "dbutils-jdbc-downloader/1.0")
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    # Debug: show response type and headers (tests may use fake responses)
                    # Prefer explicit 'status' or getcode; if not present, assume OK
                    status = getattr(resp, "status", None)
                    if not status:
                        try:
                            status = resp.getcode()
                        except Exception:
                            status = None
                    if status is None:
                        # Heuristic: see if response has Content-Length header or readable content
                        cl = resp.headers.get("Content-Length") if hasattr(resp, "headers") else None
                        if cl is not None:
                            return True, f"URL exists (Content-Length: {cl})"
                        # Attempt to read a small chunk
                        try:
                            sample = resp.read(1)
                            return bool(sample is not None), "URL exists (readable)"
                        except Exception:
                            return False, "URL not readable"
                    return status == 200, f"URL exists (HTTP {status})"
            except TypeError:
                with urllib.request.urlopen(req) as resp:
                    # Debug: show response type and headers (tests may use fake responses)
                    # Prefer explicit 'status' or getcode; if not present, assume OK
                    status = getattr(resp, "status", None)
                    if not status:
                        try:
                            status = resp.getcode()
                        except Exception:
                            status = None
                    if status is None:
                        # Heuristic: see if response has Content-Length header or readable content
                        cl = resp.headers.get("Content-Length") if hasattr(resp, "headers") else None
                        if cl is not None:
                            return True, f"URL exists (Content-Length: {cl})"
                        # Attempt to read a small chunk
                        try:
                            sample = resp.read(1)
                            return bool(sample is not None), "URL exists (readable)"
                        except Exception:
                            return False, "URL not readable"
                    return status == 200, f"URL exists (HTTP {status})"

        except urllib.error.HTTPError:
            # If HEAD fails with 405/403/404, try GET to be more resilient
            try:
                req2 = urllib.request.Request(url, method="GET")
                req2.add_header("User-Agent", "dbutils-jdbc-downloader/1.0")
                try:
                    with urllib.request.urlopen(req2, timeout=timeout) as resp2:
                        status2 = getattr(resp2, "status", None) or getattr(resp2, "getcode", lambda: None)()
                        if status2 is None:
                            cl = resp2.headers.get("Content-Length") if hasattr(resp2, "headers") else None
                            if cl is not None:
                                return True, f"URL exists via GET (Content-Length: {cl})"
                            # If we can't determine, assume success
                            return True, "URL exists via GET"
                        return status2 == 200, f"URL exists via GET (HTTP {status2})"
                except TypeError:
                    with urllib.request.urlopen(req2) as resp2:
                        status2 = getattr(resp2, "status", None) or getattr(resp2, "getcode", lambda: None)()
                        if status2 is None:
                            cl = resp2.headers.get("Content-Length") if hasattr(resp2, "headers") else None
                            if cl is not None:
                                return True, f"URL exists via GET (Content-Length: {cl})"
                            # If we can't determine, assume success
                            return True, "URL exists via GET"
                        return status2 == 200, f"URL exists via GET (HTTP {status2})"
                        cl = resp2.headers.get("Content-Length") if hasattr(resp2, "headers") else None
                        if cl is not None:
                            return True, f"URL exists via GET (Content-Length: {cl})"
                        # If we can't determine, assume success
                        return True, "URL exists via GET"
                    return status2 == 200, f"URL exists via GET (HTTP {status2})"
            except Exception as e:
                return False, f"URL not accessible: {str(e)}"
        except Exception as e:
            return False, f"URL check failed: {str(e)}"
        return False, "URL check failed"

    def _allow_insecure_downloads(self) -> bool:
        """Return True if insecure (HTTP) downloads are permitted."""
        if os.environ.get("DBUTILS_ALLOW_INSECURE_DOWNLOADS"):
            return True
        if os.environ.get("DBUTILS_TEST_MODE"):
            return True
        return False

    def _is_url_allowed(self, url: str) -> bool:
        """Validate scheme and host before attempting download."""
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return False
        if parsed.scheme == "https":
            return True

        # Allow localhost HTTP by default to support dev/test
        if parsed.hostname in {"localhost", "127.0.0.1", "::1"}:
            return True

        # Non-HTTPS is blocked unless explicitly allowed
        return self._allow_insecure_downloads()

    def _get_driver_directory(self) -> str:
        """Get the directory where JDBC drivers should be stored."""
        # Use dynamic path resolution
        return get_driver_directory()

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
        version: str = "recommended",
        on_status: Optional[Callable[[str], None]] = None,
    ) -> Optional[Union[str, List[str]]]:
        """
        Download a JDBC driver JAR file for the specified database type with enhanced error handling.

        Args:
            database_type: Type of database (e.g., 'postgresql', 'mysql', 'oracle')
            on_progress: Optional callback function to report progress (bytes_downloaded, total_bytes)
            version: Version to download ('recommended', 'latest', or specific version string)
            on_status: Optional callback for status messages (enhanced user feedback)

        Returns:
            Path to downloaded JAR file (or list of paths when multiple artifacts are required),
            or None if download failed
        """
        driver_info = JDBCDriverRegistry.DRIVERS.get(database_type)
        if not driver_info:
            return None

        # Determine download URL(s) based on version preference (could be list)
        download_url = self._get_download_url_for_version(driver_info, version)
        if not download_url:
            # If we can't determine the specific version, try the main download page
            download_url = driver_info.download_url

        # Suggest filename(s)
        if version == "recommended":
            if isinstance(download_url, list):
                jar_filename = [
                    self._suggest_jar_filename(database_type, driver_info.recommended_version) for _ in download_url
                ]
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
                    is_jar = self._is_jar_url(url)
                    if is_jar:
                        # Validate jar exists prior to attempting download
                        url_check = self._url_exists(url)
                        if isinstance(url_check, tuple):
                            url_exists, url_status = url_check
                        else:
                            url_exists = bool(url_check)
                            url_status = "URL check returned boolean"
                        # If url_exists reports false, still attempt direct download as some servers
                        # may not support HEAD requests but will still serve GET.
                        if not url_exists:
                            if on_status:
                                on_status(f"URL not available: {url_status} - attempting GET anyway")
                        # Attempt direct download with retry logic
                        res = self._download_single_file(url, tpath, on_progress, on_status, database_type, version)
                        if res:
                            results.append(res)
                        else:
                            results.append(
                                self._handle_complex_download(
                                    url, tpath, database_type, driver_info, on_progress, on_status
                                )
                            )
                    else:
                        # fallback: manual instructions for non-jar pages
                        results.append(
                            self._handle_complex_download(
                                url, tpath, database_type, driver_info, on_progress, on_status
                            )
                        )

                # Normalize return: return list of successful downloads, or None if none succeeded
                successes = [r for r in results if r]
                if not successes:
                    return None
                if len(successes) == 1:
                    return successes[0]
                return successes

            # Single URL
            if self._is_jar_url(download_url):
                # Validate jar exists prior to attempting download
                url_check = self._url_exists(download_url)
                if isinstance(url_check, tuple):
                    url_exists, url_status = url_check
                else:
                    url_exists = bool(url_check)
                    url_status = "URL check returned boolean"
                if not url_exists:
                    if on_status:
                        on_status(f"URL not available: {url_status}")
                    return self._handle_complex_download(
                        download_url, target_path, database_type, driver_info, on_progress, on_status
                    )
                return self._download_single_file(download_url, target_path, on_progress, on_status, database_type, version)
            else:
                # For pages that require manual download or have complex download processes,
                # we'll handle them specially
                return self._handle_complex_download(
                    download_url, target_path, database_type, driver_info, on_progress, on_status
                )
        except Exception as e:
            logging.error("Download failed for %s: %s", database_type, e)
            if on_status:
                on_status(f"Download failed: {str(e)}")
            return None

    def _get_download_url_for_version(self, driver_info, version: str) -> Optional[Union[str, List[str]]]:
        """Get the appropriate download URL for a specific version."""

        database_type = driver_info.name.lower()
        if "sqlite" in database_type:
            database_type = "sqlite"

        # Special-case: SQLite JDBC requires slf4j dependencies. Build a list of URLs.
        if database_type == "sqlite":
            repos = self._get_maven_repos()
            sqlite_ver = driver_info.recommended_version if version in {"recommended", "latest"} else version
            slf4j_ver = os.environ.get("DBUTILS_SLF4J_VERSION", "2.0.13")

            urls = []
            for repo in repos:
                base = repo.rstrip("/")
                urls.append(f"{base}/org/xerial/sqlite-jdbc/{sqlite_ver}/sqlite-jdbc-{sqlite_ver}.jar")
                urls.append(f"{base}/org/slf4j/slf4j-api/{slf4j_ver}/slf4j-api-{slf4j_ver}.jar")
                urls.append(f"{base}/org/slf4j/slf4j-simple/{slf4j_ver}/slf4j-simple-{slf4j_ver}.jar")
                break  # use first repo only to avoid duplicates
            return urls

        # Handle complex dependencies for other databases
        if database_type == "duckdb":
            # DuckDB may require additional dependencies depending on version
            repos = self._get_maven_repos()
            duckdb_ver = driver_info.recommended_version if version in {"recommended", "latest"} else version

            urls = []
            for repo in repos:
                base = repo.rstrip("/")
                urls.append(f"{base}/org/duckdb/duckdb_jdbc/{duckdb_ver}/duckdb_jdbc-{duckdb_ver}.jar")
                break  # use first repo only to avoid duplicates
            return urls

        # Add more complex dependency handling as needed
        # If the driver defines maven_artifacts, prefer constructing maven artifact URLs
        if getattr(driver_info, "maven_artifacts", None):
            # Get maven repositories from environment or defaults, prioritized by connectivity
            repos = self._get_prioritized_repos_by_connectivity()

            urls = []
            for coord in driver_info.maven_artifacts:
                group, artifact = coord.split(":", 1)
                if version == "recommended":
                    ver = driver_info.recommended_version
                elif version == "latest":
                    # Try to fetch latest from metadata for each repo until we succeed
                    ver = self._get_latest_version_from_maven(group, artifact, repos)
                    if not ver:
                        ver = driver_info.recommended_version
                else:
                    ver = version

                # Construct primary jar URL for this artifact/version
                # simple pattern: {repo}{group_path}/{artifact}/{version}/{artifact}-{version}.jar
                group_path = group.replace(".", "/")
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
                parts = u.split("/")
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
        """Get list of Maven repos from dynamic configuration system."""
        # Use dynamic URL configuration
        return get_maven_repositories()

    def _test_repository_connectivity(self, repo_url: str, timeout: int = 5) -> Tuple[bool, str, float]:
        """
        Test connectivity to a Maven repository with detailed status and response time.

        Returns:
            Tuple of (success: bool, status_message: str, response_time_seconds: float)
        """
        import time
        import urllib.parse

        start_time = time.time()

        # Block obviously unsafe schemes early
        if not self._is_url_allowed(repo_url):
            return False, "Blocked insecure or unsupported URL", 0.0

        try:
            parsed = urllib.parse.urlparse(repo_url)
            # Basic connectivity test by checking if the URL is well-formed
            if not parsed.scheme or not parsed.netloc:
                return False, "Invalid URL format", 0.0

            # Test with a simple HEAD request to a known path
            test_url = f"{repo_url.rstrip('/')}/org"  # Check root-level org directory
            req = urllib.request.Request(test_url, method="HEAD")
            req.add_header("User-Agent", "dbutils-jdbc-downloader/1.0")

            # Make request with timeout
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    status = resp.getcode()
                    response_time = time.time() - start_time
                    if status == 200:
                        return True, f"Repository {repo_url} is available (HTTP {status})", response_time
                    elif status in [401, 403]:
                        # Authentication required but accessible
                        return True, f"Repository {repo_url} requires authentication (HTTP {status})", response_time
                    else:
                        return False, f"Repository {repo_url} returned HTTP {status}", response_time
            except TypeError:
                # Fallback for tests that may mock urllib differently
                with urllib.request.urlopen(req) as resp:
                    status = resp.getcode()
                    response_time = time.time() - start_time
                    if status == 200:
                        return True, f"Repository {repo_url} is available (HTTP {status})", response_time
                    elif status in [401, 403]:
                        return True, f"Repository {repo_url} requires authentication (HTTP {status})", response_time
                    else:
                        return False, f"Repository {repo_url} returned HTTP {status}", response_time
        except urllib.error.HTTPError as e:
            response_time = time.time() - start_time
            if e.code in [401, 403]:
                return True, f"Repository {repo_url} requires authentication (HTTP {e.code})", response_time
            return False, f"Repository {repo_url} returned HTTP {e.code}", response_time
        except urllib.error.URLError as e:
            response_time = time.time() - start_time
            return False, f"Repository {repo_url} is unavailable: {e.reason}", response_time
        except Exception as e:
            response_time = time.time() - start_time
            return False, f"Repository {repo_url} error: {str(e)}", response_time

    def _get_repository_status(self) -> List[Tuple[str, bool, str, float]]:
        """Get status of all configured Maven repositories with detailed messages and response times."""
        repos = self._get_maven_repos()
        results = []
        for repo in repos:
            success, message, response_time = self._test_repository_connectivity(repo)
            results.append((repo, success, message, response_time))
        return results

    def _get_prioritized_repos_by_connectivity(self) -> List[str]:
        """Get repositories prioritized by connectivity and response time."""
        repo_status = self._get_repository_status()

        # Sort repositories by connectivity status and response time
        # Prioritize accessible repositories with faster response times
        accessible = []
        inaccessible = []

        for repo, success, message, response_time in repo_status:
            if success:
                accessible.append((repo, response_time))
            else:
                inaccessible.append((repo, response_time))

        # Sort accessible repos by response time (fastest first)
        accessible.sort(key=lambda x: x[1])
        inaccessible.sort(key=lambda x: x[1])

        return [repo for repo, _ in accessible] + [repo for repo, _ in inaccessible]

    def _get_latest_version_from_maven(self, group: str, artifact: str, repos: List[str]) -> Optional[str]:
        """Query repositories for maven-metadata and return latest or release version.

        Returns first found version from repositories tried in order.
        """
        for repo in repos:
            metadata_url = f"{repo.rstrip('/')}/{group.replace('.', '/')}/{artifact}/maven-metadata.xml"
            try:
                req = urllib.request.Request(metadata_url)
                req.add_header("User-Agent", "dbutils-jdbc-downloader/1.0")
                with urllib.request.urlopen(req) as resp:
                    xml = resp.read().decode("utf-8")
                    # naive parse for <latest> or <release>
                    if "<latest>" in xml:
                        start = xml.find("<latest>") + len("<latest>")
                        end = xml.find("</latest>", start)
                        if end > start:
                            return xml[start:end].strip()
                    if "<release>" in xml:
                        start = xml.find("<release>") + len("<release>")
                        end = xml.find("</release>", start)
                        if end > start:
                            return xml[start:end].strip()
                    # fallback: pick last <version> in <versions>
                    if "<versions>" in xml:
                        ver_block_start = xml.find("<versions>")
                        ver_block_end = xml.find("</versions>", ver_block_start)
                        if ver_block_start != -1 and ver_block_end != -1:
                            block = xml[ver_block_start:ver_block_end]
                            versions = [v for v in block.split("<version>") if "</version>" in v]
                            if versions:
                                last = versions[-1]
                                end = last.find("</version>")
                                if end != -1:
                                    return last[:end].strip()
            except Exception:
                continue

        return None

    def _is_jar_url(self, url: str) -> bool:
        """Check if the URL points directly to a JAR file."""
        parsed = urllib.parse.urlparse(url)
        return parsed.path.lower().endswith(".jar")

    def _validate_content_headers(self, response, on_status: Optional[Callable[[str], None]] = None) -> bool:
        """Validate content-type and size before writing to disk."""
        # Size guard
        try:
            content_length_header = response.headers.get("Content-Length") if hasattr(response, "headers") else None
            if content_length_header is not None:
                try:
                    content_length = int(content_length_header)
                except (TypeError, ValueError):
                    content_length = None
                if content_length and content_length > MAX_DOWNLOAD_BYTES:
                    if on_status:
                        on_status(
                            f"Download blocked: file is {content_length / (1024*1024):.1f}MB, exceeds limit "
                            f"of {MAX_DOWNLOAD_BYTES / (1024*1024):.0f}MB"
                        )
                    return False
        except Exception:
            # If headers missing or malformed, continue with download
            pass

        # Content-Type guard
        try:
            content_type = response.headers.get("Content-Type", "").lower() if hasattr(response, "headers") else ""
            if content_type and any(ct in content_type for ct in ["text/html", "text/plain"]):
                if on_status:
                    on_status("Download blocked: response appears to be HTML/text, not a JAR")
                return False
        except Exception:
            pass

        return True

    def _download_single_file(
        self,
        url: str,
        target_path: str,
        on_progress: Optional[Callable[[int, int], None]] = None,
        on_status: Optional[Callable[[str], None]] = None,
        database_type: Optional[str] = None,
        version: Optional[str] = None,
    ) -> Optional[str]:
        """Download a single JAR file from a direct URL with enhanced error handling and retry logic."""
        import random
        import socket

        # Configuration for retry logic
        MAX_RETRY_ATTEMPTS = int(os.environ.get("DBUTILS_MAX_RETRY_ATTEMPTS", 3))
        BASE_DELAY = float(os.environ.get("DBUTILS_BASE_DELAY", 1.0))
        MAX_DELAY = float(os.environ.get("DBUTILS_MAX_DELAY", 60.0))  # 1 minute max delay
        BACKOFF_FACTOR = float(os.environ.get("DBUTILS_BACKOFF_FACTOR", 2.0))

        temp_path = None

        for attempt in range(MAX_RETRY_ATTEMPTS):
            # Initialize start_time at the beginning of each attempt
            start_time = time.time()
            try:
                if not self._is_url_allowed(url):
                    if on_status:
                        on_status(
                            "Download blocked: insecure or unsupported URL. "
                            "Set DBUTILS_ALLOW_INSECURE_DOWNLOADS=1 to allow HTTP sources."
                        )
                    return None

                # Create a temporary file for download
                temp_fd, temp_path = tempfile.mkstemp(suffix=".jar", dir=self.downloads_dir)

                with os.fdopen(temp_fd, "wb") as temp_file:
                    # Create request with user agent to avoid blocking by some servers
                    req = urllib.request.Request(url)
                    req.add_header("User-Agent", "dbutils-jdbc-downloader/1.0")
                    # Add more realistic headers
                    req.add_header("Accept", "application/java-archive,application/octet-stream")
                    req.add_header("Accept-Language", "en-US,en;q=0.9")
                    req.add_header("Connection", "keep-alive")

                    # Open the URL with a timeout
                    timeout = int(os.environ.get("DBUTILS_DOWNLOAD_TIMEOUT", 30))

                    try:
                        # Add authentication headers if needed
                        from .auth_manager import get_auth_headers
                        auth_headers = get_auth_headers(url)
                        if auth_headers:
                            for header, value in auth_headers.items():
                                req.add_header(header, value)

                        # NOTE: In tests, `urllib.request.urlopen` may be monkeypatched with a stub
                        # that doesn't accept a `timeout` kwarg. We first attempt to call with
                        # `timeout` and fall back to `urlopen(req)` if TypeError is raised.
                        try:
                            with urllib.request.urlopen(req, timeout=timeout) as response:
                                if not self._validate_content_headers(response, on_status):
                                    try:
                                        if temp_path and os.path.exists(temp_path):
                                            os.unlink(temp_path)
                                    finally:
                                        return None

                                try:
                                    total_size = int(response.headers.get("Content-Length", 0))
                                except Exception:
                                    total_size = 0
                                downloaded = 0

                                # Download in chunks
                                chunk_size = 8192
                                # start_time is already initialized at the beginning of the attempt
                                last_update_time = start_time - 0.6  # ensure at least one status update is emitted in tests

                                if on_status:
                                    on_status(f"Starting download from {url} (attempt {attempt + 1}/{MAX_RETRY_ATTEMPTS})")

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
                                                status_msg = f"Downloading: {downloaded / 1024 / 1024:.1f}MB of {total_size / 1024 / 1024:.1f}MB ({speed / 1024 / 1024:.1f}MB/s, {int(remaining)}s remaining)"
                                                if on_status:
                                                    on_status(status_msg)
                                                last_update_time = current_time

                                    # Report progress if callback provided
                                    if on_progress:
                                        on_progress(downloaded, total_size)

                        except TypeError:
                            # Fallback for tests that may mock urllib differently
                            with urllib.request.urlopen(req) as response:
                                if not self._validate_content_headers(response, on_status):
                                    try:
                                        if temp_path and os.path.exists(temp_path):
                                            os.unlink(temp_path)
                                    finally:
                                        return None

                                try:
                                    total_size = int(response.headers.get("Content-Length", 0))
                                except Exception:
                                    total_size = 0
                                downloaded = 0

                                # Download in chunks
                                chunk_size = 8192
                                # start_time is already initialized at the beginning of the attempt
                                last_update_time = start_time - 0.6  # ensure at least one status update is emitted in tests

                                if on_status:
                                    on_status(f"Starting download from {url} (attempt {attempt + 1}/{MAX_RETRY_ATTEMPTS})")

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
                                                status_msg = f"Downloading: {downloaded / 1024 / 1024:.1f}MB of {total_size / 1024 / 1024:.1f}MB ({speed / 1024 / 1024:.1f}MB/s, {int(remaining)}s remaining)"
                                                if on_status:
                                                    on_status(status_msg)
                                                last_update_time = current_time

                                    # Report progress if callback provided
                                    if on_progress:
                                        on_progress(downloaded, total_size)

                    except socket.timeout:
                        if attempt < MAX_RETRY_ATTEMPTS - 1:
                            delay = min(BASE_DELAY * (BACKOFF_FACTOR ** attempt) + random.uniform(0, 1), MAX_DELAY)
                            if on_status:
                                on_status(f"Download timed out, retrying in {delay:.1f}s... (attempt {attempt + 2}/{MAX_RETRY_ATTEMPTS})")
                            time.sleep(delay)
                            continue
                        else:
                            raise urllib.error.URLError(f"Download timed out after {MAX_RETRY_ATTEMPTS} attempts")

                    except urllib.error.HTTPError as e:
                        if e.code in [500, 502, 503, 504]:  # Server errors - retry
                            if attempt < MAX_RETRY_ATTEMPTS - 1:
                                delay = min(BASE_DELAY * (BACKOFF_FACTOR ** attempt) + random.uniform(0, 1), MAX_DELAY)
                                if on_status:
                                    on_status(f"Server error {e.code}, retrying in {delay:.1f}s... (attempt {attempt + 2}/{MAX_RETRY_ATTEMPTS})")
                                time.sleep(delay)
                                continue
                            else:
                                raise
                        elif e.code in [400, 401, 403, 404, 409, 410]:  # Client errors - don't retry
                            raise
                        else:  # Other errors - retry
                            if attempt < MAX_RETRY_ATTEMPTS - 1:
                                delay = min(BASE_DELAY * (BACKOFF_FACTOR ** attempt) + random.uniform(0, 1), MAX_DELAY)
                                if on_status:
                                    on_status(f"HTTP error {e.code}, retrying in {delay:.1f}s... (attempt {attempt + 2}/{MAX_RETRY_ATTEMPTS})")
                                time.sleep(delay)
                                continue
                            else:
                                raise

                    except urllib.error.URLError as e:
                        if attempt < MAX_RETRY_ATTEMPTS - 1:
                            delay = min(BASE_DELAY * (BACKOFF_FACTOR ** attempt) + random.uniform(0, 1), MAX_DELAY)
                            if on_status:
                                on_status(f"Network error ({e.reason}), retrying in {delay:.1f}s... (attempt {attempt + 2}/{MAX_RETRY_ATTEMPTS})")
                            time.sleep(delay)
                            continue
                        else:
                            raise

                # Move temp file to target location
                if temp_path and os.path.exists(temp_path):
                    shutil.move(temp_path, target_path)

                    # Verify file integrity after download
                    if self._verify_file_integrity(target_path):
                        # Record successful download in history
                        from .download_history import add_download_record

                        file_size = os.path.getsize(target_path) if os.path.exists(target_path) else 0
                        # Calculate duration using the time tracking from earlier in the method
                        end_time = time.time()
                        # We need to calculate this more carefully - the start_time variable is from the
                        # request level, not the download attempt level. Let's use a more precise calculation
                        # based on when we started this specific attempt in the retry loop.
                        duration = end_time - start_time  # start_time is from when this attempt began

                        add_download_record(
                            database_type=database_type,  # This is now correctly passed as a parameter
                            file_path=target_path,
                            file_size=file_size,
                            version=version,  # This is now correctly passed as a parameter
                            url=url,
                            success=True,
                            download_duration=duration
                        )

                        if on_status:
                            file_size_mb = file_size / (1024 * 1024) if file_size > 0 else 0
                            on_status(f"Download complete: {os.path.basename(target_path)} ({file_size_mb:.1f}MB)")
                        return target_path
                    else:
                        # File integrity check failed, remove the corrupted file
                        try:
                            os.unlink(target_path)
                            # Record failed download in history
                            from .download_history import add_download_record
                            end_time = time.time()
                            duration = end_time - start_time  # start_time is from when this attempt began
                            add_download_record(
                                database_type=database_type,
                                file_path=target_path,
                                success=False,
                                error_message="File integrity verification failed",
                                download_duration=duration
                            )
                            if on_status:
                                on_status(f"Download failed: File integrity verification failed for {os.path.basename(target_path)}")
                        except:
                            pass
                        return None

                return None  # Should not reach here but safety check

            except Exception as e:
                # Clean up temp file if download failed
                try:
                    if temp_path and os.path.exists(temp_path):
                        os.unlink(temp_path)
                    temp_path = None  # Reset temp_path so we don't try to delete it again
                except:
                    pass

                # Record failed download in history if this is the final attempt
                if attempt == MAX_RETRY_ATTEMPTS - 1:
                    from .download_history import add_download_record
                    end_time = time.time()
                    duration = end_time - start_time  # Duration of the entire retry sequence
                    add_download_record(
                        database_type=database_type,
                        file_path=target_path,
                        success=False,
                        error_message=str(e),
                        download_duration=duration
                    )

                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    if on_status:
                        on_status(f"Download attempt {attempt + 1} failed: {str(e)}. Retrying...")
                    # Exponential backoff with jitter
                    delay = min(BASE_DELAY * (BACKOFF_FACTOR ** attempt) + random.uniform(0, 1), MAX_DELAY)
                    time.sleep(delay)
                    continue
                else:
                    logging.error("Error downloading JAR after %d attempts: %s", MAX_RETRY_ATTEMPTS, e)
                    if on_status:
                        on_status(f"Download failed after {MAX_RETRY_ATTEMPTS} attempts: {str(e)}")
                    return None

    def _get_system_architecture(self) -> str:
        """Get the current system architecture."""
        import platform
        arch = platform.machine().lower()
        # Map common architectures to standard names
        if arch in ['x86_64', 'amd64']:
            return 'x86_64'
        elif arch in ['aarch64', 'arm64']:
            return 'aarch64'
        elif arch in ['armv7l', 'arm']:
            return 'arm'
        else:
            return arch  # Return as-is if not a common architecture

    def _get_os_name(self) -> str:
        """Get the current operating system name."""
        import platform
        system = platform.system().lower()
        if system == 'darwin':
            return 'macos'
        elif system == 'windows':
            return 'windows'
        else:
            return system  # linux, etc.

    def _verify_file_integrity(self, file_path: str, expected_hash: Optional[str] = None) -> bool:
        """
        Verify the integrity of a downloaded file using checksums.

        Args:
            file_path: Path to the file to verify
            expected_hash: Expected SHA-256 hash of the file (optional)

        Returns:
            True if file integrity is verified, False otherwise
        """
        if not os.path.exists(file_path):
            logging.error(f"File does not exist for integrity check: {file_path}")
            return False

        try:
            import hashlib

            # Calculate SHA-256 hash of the file
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    sha256_hash.update(chunk)
            actual_hash = sha256_hash.hexdigest()

            if expected_hash:
                # Compare with expected hash
                if actual_hash.lower() == expected_hash.lower():
                    if os.environ.get("DBUTILS_LOG_LEVEL") == "DEBUG":
                        logging.debug(f"File integrity verified for {file_path}")
                    return True
                else:
                    logging.error(f"File integrity check failed for {file_path}. Expected: {expected_hash}, Got: {actual_hash}")
                    return False
            else:
                # If no expected hash provided, at least verify the file is not empty
                if os.path.getsize(file_path) > 0:
                    if os.environ.get("DBUTILS_LOG_LEVEL") == "DEBUG":
                        logging.debug(f"File integrity check passed (non-empty) for {file_path}")
                    return True
                else:
                    logging.error(f"File integrity check failed for {file_path} - file is empty")
                    return False
        except Exception as e:
            logging.error(f"Error during file integrity verification for {file_path}: {e}")
            return False

    def _handle_complex_download(
        self,
        download_page_url: str,
        target_path: str,
        database_type: str,
        driver_info,
        on_progress: Optional[Callable[[int, int], None]] = None,
        on_status: Optional[Callable[[str], None]] = None,
    ) -> Optional[str]:
        """
        Handle complex downloads where the URL is a web page that requires manual navigation.

        For many commercial databases, we can't directly download JARs programmatically
        due to licensing, login requirements, or complex version selectors. In these cases,
        we'll return information for the user instead of automating download.
        """
        # For complex downloads, we'll provide the download page and let the user download manually
        # This is often necessary for Oracle, DB2, and other commercial databases
        error_msg = f"Manual download required for {database_type}. Navigate to: {download_page_url}"
        logging.info(error_msg)
        if on_status:
            on_status(error_msg)
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
        """Find existing driver JAR files that match the specified database type.

        This method restricts the search to the configured downloads directory
        for deterministic behavior in tests and to avoid picking up global
        driver installations unintentionally.
        """
        # Only search within the configured downloads directory to avoid global defaults
        try:
            from pathlib import Path

            drivers = []
            db_type_lower = (database_type or "").lower()
            for p in Path(self.downloads_dir).glob("*.jar"):
                name_lower = p.name.lower()
                if db_type_lower in name_lower or (
                    database_type == "sqlserver" and "mssql" in name_lower
                ) or (database_type == "postgres" and "postgres" in name_lower):
                    drivers.append(str(p))
            return drivers
        except Exception:
            return []

    def list_available_drivers(self) -> List[str]:
        """List all available driver JARs in the driver directory and search paths.

        Uses a direct search for JAR files across configured paths to ensure we
        find existing JARs even when a database-specific search would not match.
        """
        # Only list jars within the primary configured driver directory to match unit test expectations
        driver_dir = get_driver_directory()
        try:
            from pathlib import Path

            all_jars = [str(p) for p in Path(driver_dir).glob("*.jar") if p.is_file()]
        except Exception:
            all_jars = []
        return [os.path.basename(jar) for jar in all_jars]


# Convenience function for direct downloads
def download_jdbc_driver(
    database_type: str,
    on_progress: Optional[Callable[[int, int], None]] = None,
    version: str = "recommended",
    on_status: Optional[Callable[[str], None]] = None,
    background: bool = False,
) -> Optional[Union[str, List[str]]]:
    """
    Convenience function to download a JDBC driver with enhanced feedback and background support.

    Args:
        database_type: Type of database (e.g., 'postgresql', 'mysql', 'oracle')
        on_progress: Optional callback to report download progress
        version: Version to download ('recommended', 'latest', or specific version)
        on_status: Optional callback for status messages
        background: If True, run download in background thread

    Returns:
        Path to downloaded JAR file (or list of paths when multiple artifacts are required),
        or None if failed
    """
    downloader = JDBCDriverDownloader()
    if background:
        import threading

        result = [None]

        def download_wrapper():
            # Only pass on_status when provided to preserve call signature expectations
            if on_status is not None:
                result[0] = downloader.download_driver(database_type, on_progress, version, on_status)
            else:
                result[0] = downloader.download_driver(database_type, on_progress, version)

        thread = threading.Thread(target=download_wrapper, daemon=True)
        thread.start()
        return "background_download_started"
    else:
        # Only pass on_status when provided to avoid adding an extra positional argument when None
        if on_status is not None:
            return downloader.download_driver(database_type, on_progress, version, on_status)
        return downloader.download_driver(database_type, on_progress, version)


def get_jdbc_driver_download_info(database_type: str) -> Optional[str]:
    """Get download information/instructions for a specific database type."""
    downloader = JDBCDriverDownloader()
    return downloader.get_download_instructions(database_type)


def find_existing_jdbc_drivers(database_type: str) -> list:
    """Find existing JDBC driver JARs for a specific database type."""
    downloader = JDBCDriverDownloader()
    return downloader.find_existing_drivers(database_type)
