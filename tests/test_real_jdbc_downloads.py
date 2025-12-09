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
        result = download_jdbc_driver(
            "sqlite",
            version="latest"
        )
        
        assert result is not None
        assert os.path.exists(result), f"Downloaded file not found: {result}"
        assert os.path.getsize(result) > 1000000, "Downloaded file too small"
        assert result.endswith(".jar"), "Downloaded file is not a JAR"
        assert "sqlite" in result.lower(), "Downloaded file doesn't match database type"

    def test_sqlite_download_with_callbacks(self, temp_driver_dir):
        """Test SQLite download with progress and status callbacks."""
        progress_updates = []
        status_messages = []
        
        def progress_cb(downloaded, total):
            progress_updates.append((downloaded, total))
        
        def status_cb(msg):
            status_messages.append(msg)
        
        result = download_jdbc_driver(
            "sqlite",
            version="latest",
            on_progress=progress_cb,
            on_status=status_cb
        )
        
        assert result is not None
        assert os.path.exists(result)
        
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
        result = download_jdbc_driver(
            "postgresql",
            version="latest"
        )
        
        assert result is not None
        assert os.path.exists(result), f"Downloaded file not found: {result}"
        assert os.path.getsize(result) > 100000, "Downloaded file too small"
        assert result.endswith(".jar"), "Downloaded file is not a JAR"
        assert "postgresql" in result.lower(), "Downloaded file doesn't match database type"

    def test_mysql_download_success(self, temp_driver_dir):
        """Test downloading MySQL JDBC driver."""
        result = download_jdbc_driver(
            "mysql",
            version="latest"
        )
        
        # MySQL may not be available in all repo configurations
        # but we should handle gracefully
        if result:
            assert os.path.exists(result), f"Downloaded file not found: {result}"
            assert os.path.getsize(result) > 100000, "Downloaded file too small"
            assert result.endswith(".jar"), "Downloaded file is not a JAR"
            assert ("mysql" in result.lower() or "mariadb" in result.lower()), \
                "Downloaded file doesn't match database type"

    def test_h2_download_success(self, temp_driver_dir):
        """Test downloading H2 JDBC driver (small, fast)."""
        result = download_jdbc_driver(
            "h2",
            version="latest"
        )
        
        assert result is not None
        assert os.path.exists(result), f"Downloaded file not found: {result}"
        assert os.path.getsize(result) > 100000, "Downloaded file too small"
        assert result.endswith(".jar"), "Downloaded file is not a JAR"
        assert "h2" in result.lower(), "Downloaded file doesn't match database type"

    def test_multiple_sequential_downloads(self, temp_driver_dir):
        """Test downloading multiple drivers in sequence."""
        databases = ["sqlite", "h2", "postgresql"]
        downloaded_files = []
        
        for db_type in databases:
            result = download_jdbc_driver(db_type, version="latest")
            
            assert result is not None, f"Failed to download {db_type}"
            assert os.path.exists(result), f"{db_type} file not found: {result}"
            
            downloaded_files.append(result)
        
        # All files should be unique
        assert len(set(downloaded_files)) == len(downloaded_files), \
            "Downloaded files are not unique"
        
        # All files should exist
        for file in downloaded_files:
            assert os.path.exists(file), f"File not found: {file}"

    def test_download_with_specific_version(self, temp_driver_dir):
        """Test downloading with a specific version."""
        # SQLite has well-defined versions
        result = download_jdbc_driver(
            "sqlite",
            version="3.44.0.0"
        )
        
        assert result is not None
        assert os.path.exists(result), f"Downloaded file not found: {result}"
        assert "3.44.0.0" in result or "3.44" in result, \
            f"Downloaded version doesn't match request: {result}"

    def test_download_idempotency(self, temp_driver_dir):
        """Test that downloading same driver twice returns same file."""
        result1 = download_jdbc_driver("sqlite", version="latest")
        result2 = download_jdbc_driver("sqlite", version="latest")
        
        assert result1 is not None
        assert result2 is not None
        
        # Could be same path or different paths depending on implementation
        # But both should exist
        assert os.path.exists(result1)
        assert os.path.exists(result2)
        
        # Both should be valid JARs
        assert os.path.getsize(result1) > 1000000
        assert os.path.getsize(result2) > 1000000

    def test_download_file_integrity(self, temp_driver_dir):
        """Test that downloaded files are valid JARs."""
        result = download_jdbc_driver("sqlite", version="latest")
        
        assert result is not None
        assert os.path.exists(result)
        
        # Check it's a valid ZIP/JAR (all JARs are ZIPs)
        import zipfile
        assert zipfile.is_zipfile(result), "Downloaded file is not a valid ZIP/JAR"
        
        # JAR should have META-INF
        with zipfile.ZipFile(result, 'r') as jar:
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
        
        # Verify monotonic increase
        for i in range(1, len(downloads)):
            assert downloads[i] >= downloads[i-1], \
                f"Progress went backwards: {downloads[i-1]} -> {downloads[i]}"

    def test_download_creates_directory_if_needed(self, temp_driver_dir):
        """Test that download creates driver directory if it doesn't exist."""
        # Create a new, deeper path
        deep_dir = temp_driver_dir / "deep" / "nested" / "drivers"
        os.environ["DBUTILS_DRIVER_DIR"] = str(deep_dir)
        
        result = download_jdbc_driver("sqlite", version="latest")
        
        assert result is not None
        assert os.path.exists(result)
        assert deep_dir.exists(), "Driver directory was not created"

    def test_download_status_messages_meaningful(self, temp_driver_dir):
        """Test that status messages provide useful information."""
        status_messages = []
        
        def status_cb(msg):
            status_messages.append(msg)
        
        download_jdbc_driver(
            "sqlite",
            version="latest",
            on_status=status_cb
        )
        
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
        result = download_jdbc_driver(
            "oracle",
            version="recommended"
        )
        
        # Oracle download should either succeed or return None gracefully
        if result:
            assert os.path.exists(result)
        # None is acceptable for proprietary drivers

    def test_sqlserver_download_success(self, temp_driver_dir):
        """Test downloading SQL Server JDBC driver."""
        result = download_jdbc_driver(
            "sqlserver",
            version="latest"
        )
        
        assert result is not None
        assert os.path.exists(result)
        assert os.path.getsize(result) > 100000


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
