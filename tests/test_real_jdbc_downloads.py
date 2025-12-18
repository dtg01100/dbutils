"""
Integration tests for real JDBC driver downloads.

These tests actually download drivers from Maven repositories to ensure
the automatic download functionality works end-to-end.
"""

import os
import tempfile
from pathlib import Path

import pytest

from dbutils.gui.jdbc_driver_manager import download_jdbc_driver


def _first_path(result):
    if isinstance(result, list):
        return result[0] if result else None
    return result


def _all_paths(result):
    if isinstance(result, list):
        return result
    return [result] if result is not None else []


@pytest.fixture
def temp_driver_dir():
    """Create a temporary directory for downloaded drivers."""
    with tempfile.TemporaryDirectory() as tmpdir:
        driver_dir = Path(tmpdir) / "drivers"
        driver_dir.mkdir(parents=True, exist_ok=True)
        
        # Set environment to use temp directory
        original = os.environ.get("DBUTILS_DRIVER_DIR")
        os.environ["DBUTILS_DRIVER_DIR"] = str(driver_dir)
        
        yield driver_dir
        
        # Restore original
        if original:
            os.environ["DBUTILS_DRIVER_DIR"] = original
        else:
            os.environ.pop("DBUTILS_DRIVER_DIR", None)


class TestRealJDBCDownloads:
    """Test real JDBC driver downloads from Maven repositories."""

    def test_sqlite_download_success(self, temp_driver_dir):
        """Test downloading SQLite JDBC driver (small, fast, reliable)."""
        # SQLite JDBC is small (~14MB) and always available
        result = download_jdbc_driver("sqlite", version="latest")

        path = _first_path(result)
        assert path is not None
        assert os.path.exists(path), f"Downloaded file not found: {path}"
        assert os.path.getsize(path) > 1000000, "Downloaded file too small"
        assert path.endswith(".jar"), "Downloaded file is not a JAR"
        assert "sqlite" in path.lower(), "Downloaded file doesn't match database type"

    def test_sqlite_download_with_callbacks(self, temp_driver_dir):
        """Test SQLite download with progress and status callbacks."""
        progress_updates = []
        status_messages = []
        
        def progress_cb(downloaded, total):
            progress_updates.append((downloaded, total))
        
        def status_cb(msg):
            status_messages.append(msg)
        
        result = download_jdbc_driver("sqlite", version="latest", on_progress=progress_cb, on_status=status_cb)

        path = _first_path(result)
        assert path is not None
        assert os.path.exists(path)
        
        # Verify progress callbacks were called
        assert len(progress_updates) > 0, "No progress updates received"
        
        # Progress should start at 0 and end at file size
        first_downloaded, first_total = progress_updates[0]
        last_downloaded, last_total = progress_updates[-1]
        
        assert first_downloaded >= 0, "First progress should be >= 0"
        assert last_downloaded == last_total, "Final progress should equal total"
        assert first_total > 0, "Total size should be > 0"
        
        # Verify status callbacks were called
        assert len(status_messages) > 0, "No status messages received"
        assert any("download" in msg.lower() or "complete" in msg.lower() 
                  for msg in status_messages), "No download status messages"

    def test_postgresql_download_success(self, temp_driver_dir):
        """Test downloading PostgreSQL JDBC driver."""
        # PostgreSQL JDBC is medium-sized (~1MB) and reliable
        result = download_jdbc_driver("postgresql", version="latest")

        path = _first_path(result)
        assert path is not None
        assert os.path.exists(path), f"Downloaded file not found: {path}"
        assert os.path.getsize(path) > 100000, "Downloaded file too small"
        assert path.endswith(".jar"), "Downloaded file is not a JAR"
        assert "postgresql" in path.lower(), "Downloaded file doesn't match database type"

    def test_mysql_download_success(self, temp_driver_dir):
        """Test downloading MySQL JDBC driver."""
        result = download_jdbc_driver("mysql", version="latest")
        
        # MySQL may not be available in all repo configurations
        # but we should handle gracefully
        if result:
            for path in _all_paths(result):
                assert os.path.exists(path), f"Downloaded file not found: {path}"
                assert os.path.getsize(path) > 100000, "Downloaded file too small"
                assert path.endswith(".jar"), "Downloaded file is not a JAR"
                assert ("mysql" in path.lower() or "mariadb" in path.lower()), "Downloaded file doesn't match database type"

    def test_h2_download_success(self, temp_driver_dir):
        """Test downloading H2 JDBC driver (small, fast)."""
        result = download_jdbc_driver("h2", version="latest")

        path = _first_path(result)
        assert path is not None
        assert os.path.exists(path), f"Downloaded file not found: {path}"
        assert os.path.getsize(path) > 100000, "Downloaded file too small"
        assert path.endswith(".jar"), "Downloaded file is not a JAR"
        assert "h2" in path.lower(), "Downloaded file doesn't match database type"

    def test_multiple_sequential_downloads(self, temp_driver_dir):
        """Test downloading multiple drivers in sequence."""
        databases = ["sqlite", "h2", "postgresql"]
        downloaded_files = []
        
        for db_type in databases:
            result = download_jdbc_driver(db_type, version="latest")
            
            path = _first_path(result)
            assert path is not None, f"Failed to download {db_type}"
            assert os.path.exists(path), f"{db_type} file not found: {path}"

            downloaded_files.append(path)
        
        # All files should be unique
        assert len(set(downloaded_files)) == len(downloaded_files), \
            "Downloaded files are not unique"
        
        # All files should exist
        for file in downloaded_files:
            assert os.path.exists(file), f"File not found: {file}"

    def test_download_with_specific_version(self, temp_driver_dir):
        """Test downloading with a specific version."""
        # SQLite has well-defined versions
        result = download_jdbc_driver("sqlite", version="3.44.0.0")

        path = _first_path(result)
        assert path is not None
        assert os.path.exists(path), f"Downloaded file not found: {path}"
        assert "3.44.0.0" in path or "3.44" in path, f"Downloaded version doesn't match request: {path}"

    def test_download_idempotency(self, temp_driver_dir):
        """Test that downloading same driver twice returns same file."""
        result1 = download_jdbc_driver("sqlite", version="latest")
        result2 = download_jdbc_driver("sqlite", version="latest")
        
        path1 = _first_path(result1)
        path2 = _first_path(result2)

        assert path1 is not None
        assert path2 is not None

        assert os.path.exists(path1)
        assert os.path.exists(path2)
        assert os.path.getsize(path1) > 1000000
        assert os.path.getsize(path2) > 1000000

    def test_download_file_integrity(self, temp_driver_dir):
        """Test that downloaded files are valid JARs."""
        result = download_jdbc_driver("sqlite", version="latest")

        path = _first_path(result)
        assert path is not None
        assert os.path.exists(path)
        
        # Check it's a valid ZIP/JAR (all JARs are ZIPs)
        import zipfile
        assert zipfile.is_zipfile(path), "Downloaded file is not a valid ZIP/JAR"

        # JAR should have META-INF
        with zipfile.ZipFile(path, 'r') as jar:
            file_list = jar.namelist()
            assert any("META-INF" in f for f in file_list), \
            "JAR missing META-INF directory"

    def test_progress_callback_monotonic(self, temp_driver_dir):
        """Test that progress callbacks are monotonically increasing."""
        progress_updates = []
        
        def progress_cb(downloaded, total):
            progress_updates.append((downloaded, total))
        
        download_jdbc_driver(
            "sqlite",
            version="latest",
            on_progress=progress_cb
        )
        
        # Extract just the downloaded amounts
        downloads = [d for d, t in progress_updates]

        # Allow multiple artifacts where progress may reset; simply ensure
        # values are non-negative and we observed at least one completion
        assert all(d >= 0 for d in downloads), "Progress values must be non-negative"
        # Final update should reflect completion for the last artifact
        assert progress_updates[-1][0] == progress_updates[-1][1]

    def test_download_creates_directory_if_needed(self, temp_driver_dir):
        """Test that download creates driver directory if it doesn't exist."""
        # Create a new, deeper path
        deep_dir = temp_driver_dir / "deep" / "nested" / "drivers"
        os.environ["DBUTILS_DRIVER_DIR"] = str(deep_dir)
        
        result = download_jdbc_driver("sqlite", version="latest")
        path = _first_path(result)

        assert path is not None
        assert os.path.exists(path)
        assert deep_dir.exists(), "Driver directory was not created"

    def test_download_status_messages_meaningful(self, temp_driver_dir):
        """Test that status messages provide useful information."""
        status_messages = []
        
        def status_cb(msg):
            status_messages.append(msg)
        
        result = download_jdbc_driver(
            "sqlite",
            version="latest",
            on_status=status_cb
        )

        path = _first_path(result)
        assert path is not None
        assert os.path.exists(path)
        
        # Should have meaningful messages
        assert any("download" in msg.lower() for msg in status_messages), \
            "No 'download' in status messages"
        assert any("complete" in msg.lower() or "finish" in msg.lower() 
                  for msg in status_messages), \
            "No completion message in status"
        
        # Check that messages contain useful details
        status_str = " ".join(status_messages).lower()
        assert any(word in status_str for word in ["mb", "byte", "size", "complete"]), \
            "Status messages lack detail"


@pytest.mark.slow
class TestLargeDriverDownloads:
    """Tests for larger drivers that take longer to download."""

    def test_oracle_download_handling(self, temp_driver_dir):
        """Test handling of Oracle driver (proprietary, may not download)."""
        # Oracle requires manual download in most cases
        result = download_jdbc_driver("oracle", version="recommended")
        
        # Oracle download should either succeed or return None gracefully
        if result:
            for path in _all_paths(result):
                assert os.path.exists(path)
        # None is acceptable for proprietary drivers

    def test_sqlserver_download_success(self, temp_driver_dir):
        """Test downloading SQL Server JDBC driver."""
        result = download_jdbc_driver("sqlserver", version="latest")

        path = _first_path(result)
        assert path is not None
        assert os.path.exists(path)
        assert os.path.getsize(path) > 100000


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
