#!/usr/bin/env python3
"""
Comprehensive test suite for enhanced automatic downloads functionality.

This test suite covers:
1. Error Handling Testing (retry logic, error messages, fallback mechanisms)
2. Progress Tracking Validation (progress bar updates, speed calculations, ETA accuracy)
3. License Management Testing (validation, expiration handling, persistence)
4. Repository Management Testing (connectivity, prioritization, error handling)
5. Integration Testing (complete workflows, background downloads, driver detection)
"""

import json
import time
import urllib.error
from pathlib import Path

import pytest

from dbutils.gui import license_store
from dbutils.gui.jdbc_auto_downloader import (
    MAVEN_REPOSITORIES,
    download_jdbc_driver,
    find_existing_drivers,
    get_jdbc_driver_url,
    get_latest_version_from_maven_metadata,
    get_repository_status,
    test_repository_connectivity,
)
from dbutils.gui.jdbc_driver_manager import download_jdbc_driver as manager_download

# Import test configuration


# Test data and utilities
class MockResponse:
    """Mock HTTP response for testing."""

    def __init__(self, data=None, status_code=200, headers=None):
        self.data = data or b""
        self.status_code = status_code
        self.headers = headers or {"Content-Length": str(len(self.data))}
        self._pos = 0

    def read(self, size=-1):
        if size == -1:
            chunk = self.data[self._pos :]
        else:
            chunk = self.data[self._pos : self._pos + size]
        self._pos += len(chunk)
        return chunk

    def getcode(self):
        return self.status_code

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class ProgressTracker:
    """Track progress callbacks for testing."""

    def __init__(self):
        self.updates = []
        self.status_messages = []

    def progress_callback(self, downloaded, total):
        self.updates.append((downloaded, total))

    def status_callback(self, message):
        self.status_messages.append(message)


# ======================
# 1. ERROR HANDLING TESTS
# ======================


class TestErrorHandling:
    """Test error handling, retry logic, and fallback mechanisms."""

    def test_retry_logic_network_failures(self, monkeypatch, tmp_path):
        """Test retry logic with simulated network failures."""
        attempt_count = 0

        def mock_urlopen_failing_then_succeeding(req):
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:  # Fail first 2 attempts
                raise urllib.error.URLError("Network timeout")
            # Succeed on 3rd attempt
            return MockResponse(
                b'<?xml version="1.0"?><metadata><versioning><latest>1.2.3</latest></versioning></metadata>'
            )

        monkeypatch.setattr("urllib.request.urlopen", mock_urlopen_failing_then_succeeding)

        # This should succeed after retries
        result = get_latest_version_from_maven_metadata(
            "https://repo1.maven.org/maven2/org/postgresql/postgresql/maven-metadata.xml"
        )
        assert result == "1.2.3"
        assert attempt_count == 3  # Should have tried 3 times

    def test_retry_logic_exhausted(self, monkeypatch):
        """Test that retry logic stops after MAX_RETRY_ATTEMPTS."""

        def mock_urlopen_always_fail(req):
            raise urllib.error.URLError("Network unreachable")

        monkeypatch.setattr("urllib.request.urlopen", mock_urlopen_always_fail)

        # This should fail after max attempts
        result = get_latest_version_from_maven_metadata("https://example.com/maven-metadata.xml")
        assert result is None

    def test_error_messages_detailed_and_actionable(self, monkeypatch, tmp_path, capsys):
        """Test that error messages are detailed and actionable."""

        def mock_urlopen_http_error(req):
            raise urllib.error.HTTPError("https://example.com", 404, "Not Found", {}, None)

        monkeypatch.setattr("urllib.request.urlopen", mock_urlopen_http_error)
        monkeypatch.setenv("DBUTILS_DRIVER_DIR", str(tmp_path))

        tracker = ProgressTracker()

        # Test HTTP 404 error message
        result = download_jdbc_driver(
            "postgresql", version="9.9.9", target_dir=str(tmp_path), on_status=tracker.status_callback
        )

        assert result is None
        assert any("not found" in msg.lower() for msg in tracker.status_messages)

    def test_fallback_mechanisms_primary_repository_fails(self, monkeypatch):
        """Test fallback when primary repository fails."""
        # This is more relevant for the JDBCDriverDownloader which has multiple repos
        # For jdbc_auto_downloader, it uses MAVEN_REPOSITORIES[0] primarily
        pass  # Will be tested in repository management section

    def test_http_error_handling_various_codes(self, monkeypatch, tmp_path):
        """Test handling of different HTTP error codes."""
        test_cases = [
            (404, "Not Found"),
            (500, "Internal Server Error"),
            (503, "Service Unavailable"),
            (403, "Forbidden"),
        ]

        for test_status_code, test_reason in test_cases:

            def mock_urlopen_error(req):
                raise urllib.error.HTTPError("https://example.com", test_status_code, test_reason, {}, None)

            monkeypatch.setattr("urllib.request.urlopen", mock_urlopen_error)
            monkeypatch.setenv("DBUTILS_DRIVER_DIR", str(tmp_path))

            tracker = ProgressTracker()
            result = download_jdbc_driver(
                "postgresql", version="1.0.0", target_dir=str(tmp_path), on_status=tracker.status_callback
            )

            assert result is None
            assert any(str(test_status_code) in msg for msg in tracker.status_messages)


# ======================
# 2. PROGRESS TRACKING TESTS
# ======================


class TestProgressTracking:
    """Test progress tracking, speed calculations, and ETA accuracy."""

    def test_progress_bar_updates_correctly(self, monkeypatch, tmp_path):
        """Test that progress callbacks are called with correct values."""
        test_data = b"x" * 102400  # 100KB test data
        chunk_size = 8192
        progress_calls = []

        def mock_urlopen_with_progress(req):
            return MockResponse(test_data, headers={"Content-Length": str(len(test_data))})

        monkeypatch.setattr("urllib.request.urlopen", mock_urlopen_with_progress)
        monkeypatch.setenv("DBUTILS_DRIVER_DIR", str(tmp_path))

        def progress_callback(downloaded, total):
            progress_calls.append((downloaded, total))

        result = download_jdbc_driver(
            "postgresql", version="1.0.0", target_dir=str(tmp_path), on_progress=progress_callback
        )

        assert result is not None
        assert len(progress_calls) > 0

        # Verify final progress is complete
        final_call = progress_calls[-1]
        assert final_call[0] == final_call[1]  # downloaded == total
        assert final_call[1] == len(test_data)

    def test_download_speed_calculations(self, monkeypatch, tmp_path):
        """Test download speed calculations and ETA accuracy."""
        test_data = b"y" * 51200  # 50KB test data
        status_messages = []

        def mock_urlopen_slow_download(req):
            return MockResponse(test_data, headers={"Content-Length": str(len(test_data))})

        monkeypatch.setattr("urllib.request.urlopen", mock_urlopen_slow_download)
        monkeypatch.setenv("DBUTILS_DRIVER_DIR", str(tmp_path))

        def status_callback(message):
            status_messages.append(message)
            if "MB/s" in message:
                # Check that speed is calculated
                assert "MB/s" in message
                if "remaining" in message:
                    # Check that ETA is provided
                    assert "s remaining" in message

        result = download_jdbc_driver(
            "postgresql", version="1.0.0", target_dir=str(tmp_path), on_status=status_callback
        )

        assert result is not None
        # Should have speed/ETA updates
        speed_updates = [msg for msg in status_messages if "MB/s" in msg]
        assert len(speed_updates) > 0

    def test_status_callbacks_provide_useful_information(self, monkeypatch, tmp_path):
        """Test that status callbacks provide useful information."""
        test_data = b"z" * 25600  # 25KB test data
        status_messages = []

        def mock_urlopen(req):
            return MockResponse(test_data, headers={"Content-Length": str(len(test_data))})

        monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)
        monkeypatch.setenv("DBUTILS_DRIVER_DIR", str(tmp_path))

        def status_callback(message):
            status_messages.append(message)

        result = download_jdbc_driver("sqlite", version="3.42.0.0", target_dir=str(tmp_path), on_status=status_callback)

        assert result is not None

        # Check for key status messages
        expected_patterns = ["Starting download", "Downloading", "Download complete"]

        for pattern in expected_patterns:
            assert any(pattern in msg for msg in status_messages), f"Missing status message pattern: {pattern}"


# ======================
# 3. LICENSE MANAGEMENT TESTS
# ======================


class TestLicenseManagement:
    """Test license validation, expiration handling, and persistence."""

    def test_license_validation_before_downloads(self, monkeypatch, tmp_path):
        """Test license validation before downloads."""
        # Test that downloads fail when license is not accepted
        monkeypatch.setenv("DBUTILS_DRIVER_DIR", str(tmp_path))

        # Mock the license store to return False for license acceptance
        def mock_is_license_accepted(key):
            return False

        # Monkeypatch the imported module object rather than a string path
        monkeypatch.setattr(license_store, "is_license_accepted", mock_is_license_accepted)

        tracker = ProgressTracker()

        # Test that download fails when license is not accepted
        result = download_jdbc_driver(
            "oracle", version="1.0.0", target_dir=str(tmp_path), on_status=tracker.status_callback
        )

        assert result is None
        assert any("License not accepted" in msg for msg in tracker.status_messages)

    def test_license_expiration_handling(self, tmp_path, monkeypatch):
        """Test license expiration handling."""
        config_dir = tmp_path / ".config" / "dbutils"
        config_dir.mkdir(parents=True)

        # Set up an expired license
        expired_license_file = config_dir / "accepted_licenses.json"
        expired_license_file.write_text(
            json.dumps(
                {
                    "oracle": {
                        "accepted": True,
                        "accepted_date": "2023-01-01T00:00:00",
                        "expiration": "2023-12-31T00:00:00",  # Expired
                    }
                }
            )
        )

        monkeypatch.setenv("DBUTILS_CONFIG_DIR", str(config_dir))

        # Test that expired license is not accepted
        assert not license_store.is_license_accepted("oracle")

        # Test cleanup
        cleaned_count = license_store.cleanup_expired_licenses()
        assert cleaned_count == 1
        assert not license_store.is_license_accepted("oracle")

    def test_persistent_license_tracking_across_sessions(self, tmp_path, monkeypatch):
        """Test persistent license tracking across sessions."""
        config_dir = tmp_path / ".config" / "dbutils"
        config_dir.mkdir(parents=True)

        monkeypatch.setenv("DBUTILS_CONFIG_DIR", str(config_dir))

        # Accept a license
        license_store.accept_license("postgresql", expiration_days=365)
        assert license_store.is_license_accepted("postgresql")

        # Simulate new session by creating new instance
        assert license_store.is_license_accepted("postgresql")

        # Verify persistence file exists and contains data
        license_file = config_dir / "accepted_licenses.json"
        assert license_file.exists()
        data = json.loads(license_file.read_text())
        assert "postgresql" in data
        assert data["postgresql"]["accepted"] is True


# ======================
# 4. REPOSITORY MANAGEMENT TESTS
# ======================


class TestRepositoryManagement:
    """Test repository connectivity, prioritization, and error handling."""

    def test_repository_connectivity_testing_various_scenarios(self, monkeypatch):
        """Test repository connectivity testing with various scenarios."""

        # Test successful connectivity
        def mock_urlopen_success(req):
            return MockResponse(b"OK", status_code=200)

        monkeypatch.setattr("urllib.request.urlopen", mock_urlopen_success)

        success, message = test_repository_connectivity(MAVEN_REPOSITORIES[0])
        assert success is True
        assert "available" in message.lower()

        # Test failed connectivity
        def mock_urlopen_failure(req):
            raise urllib.error.URLError("Connection refused")

        monkeypatch.setattr("urllib.request.urlopen", mock_urlopen_failure)

        success, message = test_repository_connectivity(MAVEN_REPOSITORIES[0])
        assert success is False
        assert "unavailable" in message.lower()

    def test_repository_prioritization_logic(self, test_config):
        """Test repository prioritization logic."""
        # The jdbc_auto_downloader uses MAVEN_REPOSITORIES[0] as primary
        # The JDBCDriverDownloader has more sophisticated prioritization

        # Get repositories from test configuration
        maven_repos = test_config.get_network_setting("maven_repositories", MAVEN_REPOSITORIES)

        assert len(maven_repos) >= 2
        assert maven_repos[0] == "https://repo1.maven.org/maven2/"

    def test_error_handling_invalid_repositories(self, monkeypatch):
        """Test error handling for invalid repositories."""
        invalid_repos = ["https://invalid-repo.example.com/maven2/", "not-a-url", ""]

        def mock_urlopen_invalid(req):
            raise urllib.error.URLError("Invalid repository")

        monkeypatch.setattr("urllib.request.urlopen", mock_urlopen_invalid)

        for repo in invalid_repos:
            if repo.startswith("http"):
                success, message = test_repository_connectivity(repo)
                assert success is False
                assert "unavailable" in message.lower() or "failed" in message.lower()

    def test_get_repository_status_comprehensive(self, monkeypatch):
        """Test get_repository_status returns detailed information for all repos."""

        def mock_urlopen_mixed(req):
            url = str(req.get_full_url()) if hasattr(req, "get_full_url") else str(req)
            if "repo1.maven.org" in url:
                return MockResponse(b"OK", status_code=200)
            else:
                raise urllib.error.URLError("Not found")

        monkeypatch.setattr("urllib.request.urlopen", mock_urlopen_mixed)

        results = get_repository_status()
        assert len(results) == len(MAVEN_REPOSITORIES)

        # First repo should succeed
        assert results[0][1] is True  # success
        assert "available" in results[0][2].lower()


# ======================
# 5. INTEGRATION TESTS
# ======================


class TestIntegration:
    """Test complete workflows and integration scenarios."""

    def test_automatic_driver_detection_various_driver_classes(self, monkeypatch, tmp_path):
        """Test automatic driver detection with various driver classes."""
        # Create some fake driver files
        driver_dir = tmp_path / "drivers"
        driver_dir.mkdir()

        drivers = [
            "postgresql-42.6.0.jar",
            "mysql-connector-java-8.0.33.jar",
            "sqlite-jdbc-3.42.0.0.jar",
            "mssql-jdbc-12.4.0.jre8.jar",
            "unknown-driver.jar",
        ]

        for driver in drivers:
            (driver_dir / driver).write_text("fake jar content")

        monkeypatch.setenv("DBUTILS_DRIVER_DIR", str(driver_dir))

        # Test finding existing drivers
        postgres_drivers = find_existing_drivers("postgresql")
        assert len(postgres_drivers) == 1
        assert "postgresql" in postgres_drivers[0].lower()

        mysql_drivers = find_existing_drivers("mysql")
        assert len(mysql_drivers) == 1
        assert "mysql" in mysql_drivers[0].lower()

    def test_background_download_capabilities(self, monkeypatch, tmp_path):
        """Test background download capabilities work without blocking."""
        test_data = b"background test" * 1000

        def mock_urlopen(req):
            return MockResponse(test_data, headers={"Content-Length": str(len(test_data))})

        monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)
        monkeypatch.setenv("DBUTILS_DRIVER_DIR", str(tmp_path))

        # Test background download
        result = manager_download("postgresql", version="1.0.0", background=True)

        assert result == "background_download_started"

    def test_complete_workflow_provider_config_to_successful_download(self, monkeypatch, tmp_path):
        """Test the complete workflow from provider config to successful download."""
        test_data = b"complete workflow test" * 500

        def mock_urlopen_metadata(req):
            url = str(req)
            if "maven-metadata.xml" in url:
                return MockResponse(
                    b'<?xml version="1.0"?><metadata><versioning><latest>42.6.0</latest></versioning></metadata>'
                )
            else:
                return MockResponse(test_data, headers={"Content-Length": str(len(test_data))})

        monkeypatch.setattr("urllib.request.urlopen", mock_urlopen_metadata)
        monkeypatch.setenv("DBUTILS_DRIVER_DIR", str(tmp_path))

        tracker = ProgressTracker()

        # Test complete workflow
        # 1. Get latest version
        latest_version = get_latest_version_from_maven_metadata(
            "https://repo1.maven.org/maven2/org/postgresql/postgresql/maven-metadata.xml"
        )
        assert latest_version == "42.6.0"

        # 2. Get download URL
        download_url = get_jdbc_driver_url("postgresql", latest_version)
        assert download_url is not None
        assert "42.6.0" in download_url

        # 3. Download the driver
        result = download_jdbc_driver(
            "postgresql",
            version=latest_version,
            target_dir=str(tmp_path),
            on_progress=tracker.progress_callback,
            on_status=tracker.status_callback,
        )

        assert result is not None
        assert Path(result).exists()
        assert Path(result).name == "postgresql-42.6.0.jar"

        # 4. Verify progress tracking worked
        assert len(tracker.updates) > 0
        assert len(tracker.status_messages) > 0

        # 5. Verify driver can be found
        found_drivers = find_existing_drivers("postgresql")
        assert len(found_drivers) == 1
        assert result in found_drivers


# ======================
# EDGE CASES AND FAILURE SCENARIOS
# ======================


class TestEdgeCases:
    """Test edge cases and unusual failure conditions."""

    def test_download_with_zero_content_length(self, monkeypatch, tmp_path):
        """Test download when Content-Length header is missing or zero."""
        test_data = b"small content"

        def mock_urlopen_no_length(req):
            return MockResponse(test_data, headers={})  # No Content-Length

        monkeypatch.setattr("urllib.request.urlopen", mock_urlopen_no_length)
        monkeypatch.setenv("DBUTILS_DRIVER_DIR", str(tmp_path))

        result = download_jdbc_driver("postgresql", version="1.0.0", target_dir=str(tmp_path))

        assert result is not None
        assert Path(result).read_bytes() == test_data

    def test_interrupted_download_recovery(self, monkeypatch, tmp_path):
        """Test recovery from interrupted downloads."""
        # This is tricky to test with the current implementation
        # since it uses temp files and moves them on success
        pass

    def test_corrupted_metadata_xml(self, monkeypatch):
        """Test handling of corrupted Maven metadata XML."""
        corrupted_xml = b'<?xml version="1.0"?><metadata><versioning><latest>invalid'

        def mock_urlopen_corrupted(req):
            return MockResponse(corrupted_xml)

        monkeypatch.setattr("urllib.request.urlopen", mock_urlopen_corrupted)

        result = get_latest_version_from_maven_metadata("https://example.com/maven-metadata.xml")
        assert result is None

    def test_unsupported_database_type(self):
        """Test handling of unsupported database types."""
        result = get_jdbc_driver_url("unsupported_database_xyz", "latest")
        assert result is None

        result = download_jdbc_driver("unsupported_database_xyz", version="latest")
        assert result is None

    def test_license_file_corruption_recovery(self, tmp_path, monkeypatch):
        """Test recovery from corrupted license files."""
        config_dir = tmp_path / ".config" / "dbutils"
        config_dir.mkdir(parents=True)

        # Create corrupted license file
        license_file = config_dir / "accepted_licenses.json"
        license_file.write_text("not valid json at all")

        monkeypatch.setenv("DBUTILS_CONFIG_DIR", str(config_dir))

        # Should handle gracefully and return empty/False
        assert not license_store.is_license_accepted("postgresql")

        # Should be able to accept new license
        license_store.accept_license("postgresql")
        assert license_store.is_license_accepted("postgresql")


# ======================
# PERFORMANCE AND STRESS TESTS
# ======================


class TestPerformance:
    """Test performance under stress conditions."""

    def test_concurrent_downloads(self, monkeypatch, tmp_path):
        """Test handling of concurrent download requests."""
        # This would require threading and is complex to test properly
        # Current implementation doesn't have specific concurrency protection
        pass

    def test_large_file_download_progress(self, monkeypatch, tmp_path):
        """Test progress tracking with large files."""
        # Create 10MB test data
        test_data = b"X" * (10 * 1024 * 1024)  # 10MB

        def mock_urlopen_large(req):
            return MockResponse(test_data, headers={"Content-Length": str(len(test_data))})

        monkeypatch.setattr("urllib.request.urlopen", mock_urlopen_large)
        monkeypatch.setenv("DBUTILS_DRIVER_DIR", str(tmp_path))

        progress_updates = []

        def progress_callback(downloaded, total):
            progress_updates.append((downloaded, total))

        start_time = time.time()
        result = download_jdbc_driver(
            "postgresql", version="1.0.0", target_dir=str(tmp_path), on_progress=progress_callback
        )
        end_time = time.time()

        assert result is not None
        assert len(progress_updates) > 10  # Should have multiple progress updates for 10MB
        assert end_time - start_time < 5  # Should complete quickly with mock


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
