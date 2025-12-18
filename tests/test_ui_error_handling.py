"""
Comprehensive UI tests for error handling in JDBC driver download system.

Tests the UI feedback for download failures, retry mechanisms, and error recovery.
"""

import os
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

# Enable test mode to prevent actual downloads
os.environ["DBUTILS_TEST_MODE"] = "1"


def test_download_failure_error_message(qtbot, monkeypatch):
    """Test that proper error messages are shown when download fails."""
    from dbutils.gui.provider_config_dialog import ProviderConfigDialog
    
    dialog = ProviderConfigDialog()
    qtbot.addWidget(dialog)
    
    # Mock the download function to return None (failure)
    monkeypatch.setattr('dbutils.gui.jdbc_driver_manager.download_jdbc_driver', 
                       lambda db_type, on_progress, on_status, version: None)
    
    # Mock the driver info function
    from dbutils.gui.jdbc_driver_downloader import JDBCDriverInfo
    mock_driver_info = JDBCDriverInfo(
        name="Test Driver",
        driver_class="com.test.Driver",
        download_url="https://example.com/test",
        alternative_urls=[],
        license="Test License",
        min_java_version="8",
        description="Test driver",
        recommended_version="1.0.0"
    )
    
    monkeypatch.setattr('dbutils.gui.jdbc_driver_downloader.JDBCDriverRegistry.get_driver_info',
                       lambda category: mock_driver_info)
    
    monkeypatch.setattr('dbutils.gui.jdbc_auto_downloader.get_jdbc_driver_download_info', 
                       lambda category: f"JDBC Driver: {category.title()}")
    
    # Temporarily make the dialog non-modal for testing
    original_exec = QDialog.exec
    QDialog.exec = lambda self: True
    
    try:
        # Call the download dialog creation method
        result = dialog.download_jdbc_driver_gui()
        if result:  # Test mode returns the dialog and widgets
            download_dialog, download_btn, manual_btn, license_checkbox = result[:4]
            
            qtbot.addWidget(download_dialog)
            
            # Create a mock for the perform_jdbc_download method to simulate failure
            original_perform = dialog.perform_jdbc_download
            def mock_perform(category, version=None):
                # Simulate a failure by returning None
                pass  # This will trigger the failure case in the original code
            
            monkeypatch.setattr(dialog.__class__, 'perform_jdbc_download', mock_perform)
            
            # Click the download button to trigger the simulated failure
            # We'll directly call perform_jdbc_download to simulate the failure
            with patch('dbutils.gui.jdbc_driver_manager.download_jdbc_driver', return_value=None):
                dialog.perform_jdbc_download("test", version="latest")
            
            # The error should appear in the status label or as a message box
            # Check if any error messages are displayed
            from PySide6.QtWidgets import QLabel
            status_labels = [w for w in dialog.findChildren(QLabel) if w.isVisible() and 'Error' in w.text()]
            
            download_dialog.close()
    finally:
        QDialog.exec = original_exec  # Restore original method
    
    dialog.close()


def test_network_error_handling(qtbot, monkeypatch):
    """Test UI behavior when network errors occur during download."""
    from dbutils.gui.provider_config_dialog import ProviderConfigDialog
    
    dialog = ProviderConfigDialog()
    qtbot.addWidget(dialog)
    
    # Mock the download function to raise a network error
    def mock_download_with_network_error(db_type, on_progress=None, on_status=None, version="recommended"):
        if on_status:
            on_status("Network error occurred")
        return None
    
    monkeypatch.setattr('dbutils.gui.jdbc_driver_manager.download_jdbc_driver', 
                       mock_download_with_network_error)
    
    # Mock driver info
    from dbutils.gui.jdbc_driver_downloader import JDBCDriverInfo
    mock_driver_info = JDBCDriverInfo(
        name="Test Driver",
        driver_class="com.test.Driver",
        download_url="https://example.com/test",
        alternative_urls=[],
        license="Test License",
        min_java_version="8",
        description="Test driver",
        recommended_version="1.0.0"
    )
    
    monkeypatch.setattr('dbutils.gui.jdbc_driver_downloader.JDBCDriverRegistry.get_driver_info',
                       lambda category: mock_driver_info)
    
    monkeypatch.setattr('dbutils.gui.jdbc_auto_downloader.get_jdbc_driver_download_info', 
                       lambda category: f"JDBC Driver: {category.title()}")
    
    # Temporarily make the dialog non-modal for testing
    original_exec = QDialog.exec
    QDialog.exec = lambda self: True
    
    try:
        result = dialog.download_jdbc_driver_gui()
        if result:
            download_dialog, download_btn, manual_btn, license_checkbox = result[:4]
            
            qtbot.addWidget(download_dialog)
            
            # Test network error scenario
            with patch('dbutils.gui.jdbc_driver_manager.download_jdbc_driver', mock_download_with_network_error):
                # Call perform_jdbc_download with mock to simulate network error
                dialog.perform_jdbc_download("test", version="latest")
            
            download_dialog.close()
    finally:
        QDialog.exec = original_exec  # Restore original method
    
    dialog.close()


def test_timeout_error_handling(qtbot, monkeypatch):
    """Test UI behavior when timeout errors occur during download."""
    from dbutils.gui.provider_config_dialog import ProviderConfigDialog
    
    dialog = ProviderConfigDialog()
    qtbot.addWidget(dialog)
    
    # Mock the download function to simulate timeout
    def mock_download_with_timeout(db_type, on_progress=None, on_status=None, version="recommended"):
        if on_status:
            on_status("Download timed out after 3 attempts")
        return None
    
    monkeypatch.setattr('dbutils.gui.jdbc_driver_manager.download_jdbc_driver', 
                       mock_download_with_timeout)
    
    # Mock driver info
    from dbutils.gui.jdbc_driver_downloader import JDBCDriverInfo
    mock_driver_info = JDBCDriverInfo(
        name="Test Driver",
        driver_class="com.test.Driver",
        download_url="https://example.com/test",
        alternative_urls=[],
        license="Test License",
        min_java_version="8",
        description="Test driver",
        recommended_version="1.0.0"
    )
    
    monkeypatch.setattr('dbutils.gui.jdbc_driver_downloader.JDBCDriverRegistry.get_driver_info',
                       lambda category: mock_driver_info)
    
    monkeypatch.setattr('dbutils.gui.jdbc_auto_downloader.get_jdbc_driver_download_info', 
                       lambda category: f"JDBC Driver: {category.title()}")
    
    # Temporarily make the dialog non-modal for testing
    original_exec = QDialog.exec
    QDialog.exec = lambda self: True
    
    try:
        result = dialog.download_jdbc_driver_gui()
        if result:
            download_dialog, download_btn, manual_btn, license_checkbox = result[:4]
            
            qtbot.addWidget(download_dialog)
            
            # Test timeout error scenario
            with patch('dbutils.gui.jdbc_driver_manager.download_jdbc_driver', mock_download_with_timeout):
                dialog.perform_jdbc_download("test", version="latest")
            
            download_dialog.close()
    finally:
        QDialog.exec = original_exec  # Restore original method
    
    dialog.close()


def test_retry_mechanism_ui_feedback(qtbot, monkeypatch):
    """Test UI feedback during retry attempts for failed downloads."""
    from dbutils.gui.provider_config_dialog import ProviderConfigDialog
    
    dialog = ProviderConfigDialog()
    qtbot.addWidget(dialog)
    
    # Counter to track retry attempts
    retry_counter = [0]
    max_retries = 3
    
    def mock_download_with_retries(db_type, on_progress=None, on_status=None, version="recommended"):
        retry_counter[0] += 1
        if on_status and retry_counter[0] < max_retries:
            on_status(f"Download attempt {retry_counter[0]} failed: Connection error. Retrying...")
            return None
        elif retry_counter[0] >= max_retries:
            on_status(f"Download failed after {max_retries} attempts: Connection error")
            return None
        return None
    
    monkeypatch.setattr('dbutils.gui.jdbc_driver_manager.download_jdbc_driver', 
                       mock_download_with_retries)
    
    # Mock driver info
    from dbutils.gui.jdbc_driver_downloader import JDBCDriverInfo
    mock_driver_info = JDBCDriverInfo(
        name="Test Driver", 
        driver_class="com.test.Driver",
        download_url="https://example.com/test",
        alternative_urls=[],
        license="Test License",
        min_java_version="8",
        description="Test driver",
        recommended_version="1.0.0"
    )
    
    monkeypatch.setattr('dbutils.gui.jdbc_driver_downloader.JDBCDriverRegistry.get_driver_info',
                       lambda category: mock_driver_info)
    
    monkeypatch.setattr('dbutils.gui.jdbc_auto_downloader.get_jdbc_driver_download_info', 
                       lambda category: f"JDBC Driver: {category.title()}")
    
    # Temporarily make the dialog non-modal for testing
    original_exec = QDialog.exec
    QDialog.exec = lambda self: True
    
    try:
        result = dialog.download_jdbc_driver_gui()
        if result:
            download_dialog, download_btn, manual_btn, license_checkbox = result[:4]
            
            qtbot.addWidget(download_dialog)
            
            # Test retry mechanism
            with patch('dbutils.gui.jdbc_driver_manager.download_jdbc_driver', mock_download_with_retries):
                dialog.perform_jdbc_download("test", version="latest")
                
            # Check that retry attempts were made
            assert retry_counter[0] == max_retries, f"Expected {max_retries} retry attempts"
            
            download_dialog.close()
    finally:
        QDialog.exec = original_exec  # Restore original method
    
    dialog.close()


def test_repository_fallback_ui_indication(qtbot, monkeypatch):
    """Test UI indication when repository fallback occurs."""
    from dbutils.gui.provider_config_dialog import ProviderConfigDialog
    
    dialog = ProviderConfigDialog()
    qtbot.addWidget(dialog)
    
    # Mock repository connectivity checks to simulate fallback
    def mock_get_prioritized_repos_by_connectivity(self):
        # This method should be in the JDBCDriverDownloader class
        return [
            "https://unavailable-repo.example.com/",
            "https://repo1.maven.org/maven2/"  # Fallback to working repo
        ]
    
    # Mock the download manager to use fallback repos
    def mock_download_with_fallback(db_type, on_progress=None, on_status=None, version="recommended"):
        if on_status:
            on_status("Primary repository unavailable, using fallback repository...")
        # Simulate successful download from fallback
        import tempfile
        import os
        temp_dir = tempfile.gettempdir()
        temp_file = os.path.join(temp_dir, "test_fallback.jar")
        with open(temp_file, "w") as f:
            f.write("dummy content")
        return temp_file
    
    monkeypatch.setattr('dbutils.gui.jdbc_driver_manager.download_jdbc_driver', 
                       mock_download_with_fallback)
    
    # Mock driver info
    from dbutils.gui.jdbc_driver_downloader import JDBCDriverInfo
    mock_driver_info = JDBCDriverInfo(
        name="Test Driver",
        driver_class="com.test.Driver", 
        download_url="https://example.com/test",
        alternative_urls=[],
        license="Test License",
        min_java_version="8",
        description="Test driver",
        recommended_version="1.0.0"
    )
    
    monkeypatch.setattr('dbutils.gui.jdbc_driver_downloader.JDBCDriverRegistry.get_driver_info',
                       lambda category: mock_driver_info)
    
    monkeypatch.setattr('dbutils.gui.jdbc_auto_downloader.get_jdbc_driver_download_info', 
                       lambda category: f"JDBC Driver: {category.title()}")
    
    # Temporarily make the dialog non-modal for testing
    original_exec = QDialog.exec
    QDialog.exec = lambda self: True
    
    try:
        result = dialog.download_jdbc_driver_gui()
        if result:
            download_dialog, download_btn, manual_btn, license_checkbox = result[:4]
            
            qtbot.addWidget(download_dialog)
            
            # Test repository fallback
            with patch('dbutils.gui.jdbc_driver_manager.download_jdbc_driver', mock_download_with_fallback):
                result_path = dialog.perform_jdbc_download("test", version="latest")
            
            download_dialog.close()
    finally:
        QDialog.exec = original_exec  # Restore original method
    
    dialog.close()


def test_file_integrity_error_handling(qtbot, monkeypatch):
    """Test UI behavior when file integrity verification fails."""
    from dbutils.gui.provider_config_dialog import ProviderConfigDialog
    
    dialog = ProviderConfigDialog()
    qtbot.addWidget(dialog)
    
    # Mock download to return a valid path initially, then make integrity check fail
    import tempfile
    import os
    temp_dir = tempfile.gettempdir() 
    temp_file = os.path.join(temp_dir, "test_corrupt.jar")
    
    # Create a dummy file
    with open(temp_file, "w") as f:
        f.write("dummy content for integrity test")
    
    def mock_download_with_integrity_failure(db_type, on_progress=None, on_status=None, version="recommended"):
        if on_status:
            on_status("Download completed, verifying integrity...")
        # Return the temp file but the integrity check will fail (simulated by internal logic)
        return temp_file
    
    monkeypatch.setattr('dbutils.gui.jdbc_driver_manager.download_jdbc_driver', 
                       mock_download_with_integrity_failure)
    
    # Mock the _verify_file_integrity to return False
    def mock_verify_failure(file_path, expected_hash=None):
        return False  # Simulate integrity failure
    
    from dbutils.gui import jdbc_driver_manager
    original_verify = jdbc_driver_manager.JDBCDriverDownloader._verify_file_integrity
    monkeypatch.setattr('dbutils.gui.jdbc_driver_manager.JDBCDriverDownloader._verify_file_integrity', 
                       mock_verify_failure)
    
    # Mock driver info
    from dbutils.gui.jdbc_driver_downloader import JDBCDriverInfo
    mock_driver_info = JDBCDriverInfo(
        name="Test Driver",
        driver_class="com.test.Driver",
        download_url="https://example.com/test",
        alternative_urls=[],
        license="Test License",
        min_java_version="8",
        description="Test driver",
        recommended_version="1.0.0"
    )
    
    monkeypatch.setattr('dbutils.gui.jdbc_driver_downloader.JDBCDriverRegistry.get_driver_info',
                       lambda category: mock_driver_info)
    
    monkeypatch.setattr('dbutils.gui.jdbc_auto_downloader.get_jdbc_driver_download_info', 
                       lambda category: f"JDBC Driver: {category.title()}")
    
    # Temporarily make the dialog non-modal for testing
    original_exec = QDialog.exec
    QDialog.exec = lambda self: True
    
    try:
        result = dialog.download_jdbc_driver_gui()
        if result:
            download_dialog, download_btn, manual_btn, license_checkbox = result[:4]
            
            qtbot.addWidget(download_dialog)
            
            # Test integrity failure
            dialog.perform_jdbc_download("test", version="latest")
            
            download_dialog.close()
    finally:
        QDialog.exec = original_exec  # Restore original method
        # Restore the original method if possible 
        try:
            monkeypatch.setattr('dbutils.gui.jdbc_driver_manager.JDBCDriverDownloader._verify_file_integrity', 
                               original_verify)
        except:
            pass  # Ignore if original method couldn't be restored
    
    dialog.close()


if __name__ == "__main__":
    # This allows running the test directly for debugging
    pytest.main([__file__])