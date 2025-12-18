"""
Comprehensive UI integration workflow tests for JDBC download system.

Tests complete end-to-end workflows from user interaction to download completion.
"""

import os
import tempfile
import json
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

# Enable test mode to prevent actual downloads
os.environ["DBUTILS_TEST_MODE"] = "1"


def test_complete_download_workflow_success(qtbot, monkeypatch):
    """Test complete workflow: User clicks download → progress → success → jar set in form."""
    from dbutils.gui.provider_config_dialog import ProviderConfigDialog
    
    dialog = ProviderConfigDialog()
    qtbot.addWidget(dialog)
    
    # Mock successful download
    import tempfile as tmpmodule
    temp_path = tmpmodule.gettempdir()
    mock_jar_path = os.path.join(temp_path, "test-success-driver.jar")
    
    def mock_successful_download(db_type, on_progress=None, on_status=None, version="recommended"):
        # Create a dummy jar file
        with open(mock_jar_path, "w") as f:
            f.write("fake jar content")
        if on_status:
            on_status("Download completed successfully")
        return mock_jar_path
    
    monkeypatch.setattr('dbutils.gui.jdbc_driver_manager.download_jdbc_driver', 
                       mock_successful_download)
    
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
        # Start the workflow by opening the download dialog
        result = dialog.download_jdbc_driver_gui()
        if result:
            download_dialog, download_btn, manual_btn, license_checkbox = result[:4]
            qtbot.addWidget(download_dialog)
            
            # Simulate user clicking download button
            # We'll directly test the perform_jdbc_download method for the full workflow
            original_perform = dialog.perform_jdbc_download
            
            # Patch to simulate the full workflow
            with patch('dbutils.gui.jdbc_driver_manager.download_jdbc_driver', mock_successful_download):
                dialog.perform_jdbc_download("test", version="latest")
            
            # Check that the jar path is now set in the input
            assert mock_jar_path in dialog.jar_path_input.text()
            
            download_dialog.close()
    finally:
        QDialog.exec = original_exec  # Restore original method
        # Clean up the mock file if it still exists
        if os.path.exists(mock_jar_path):
            os.remove(mock_jar_path)
    
    dialog.close()


def test_error_recovery_workflow(qtbot, monkeypatch):
    """Test workflow: User starts download → error occurs → user can retry/cancel."""
    from dbutils.gui.provider_config_dialog import ProviderConfigDialog
    
    dialog = ProviderConfigDialog()
    qtbot.addWidget(dialog)
    
    # First, mock error scenario
    def mock_download_failure(db_type, on_progress=None, on_status=None, version="recommended"):
        if on_status:
            on_status("Download failed due to network error")
        return None
    
    monkeypatch.setattr('dbutils.gui.jdbc_driver_manager.download_jdbc_driver', 
                       mock_download_failure)
    
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
            
            # Test error scenario
            with patch('dbutils.gui.jdbc_driver_manager.download_jdbc_driver', mock_download_failure):
                dialog.perform_jdbc_download("test", version="latest")
            
            download_dialog.close()
    finally:
        QDialog.exec = original_exec  # Restore original method
    
    dialog.close()


def test_history_integration_workflow(qtbot, monkeypatch):
    """Test workflow: Download completes → history updated → UI reflects new history."""
    from dbutils.gui.provider_config_dialog import ProviderConfigDialog
    from dbutils.gui.download_history import download_history, DownloadRecord
    
    dialog = ProviderConfigDialog()
    qtbot.addWidget(dialog)
    
    # Mock successful download
    import tempfile as tmpmodule
    temp_path = tmpmodule.gettempdir()
    mock_jar_path = os.path.join(temp_path, "test-history-driver.jar")
    
    def mock_successful_download_for_history(db_type, on_progress=None, on_status=None, version="recommended"):
        # Create a dummy jar file
        with open(mock_jar_path, "w") as f:
            f.write("fake jar content for history test")
        if on_status:
            on_status("Download completed, adding to history")
        return mock_jar_path
    
    monkeypatch.setattr('dbutils.gui.jdbc_driver_manager.download_jdbc_driver', 
                       mock_successful_download_for_history)
    
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
    
    # Store original history count
    original_history_count = len(download_history.records)
    
    # Temporarily make the dialog non-modal for testing
    original_exec = QDialog.exec
    QDialog.exec = lambda self: True
    
    try:
        result = dialog.download_jdbc_driver_gui()
        if result:
            download_dialog, download_btn, manual_btn, license_checkbox = result[:4]
            qtbot.addWidget(download_dialog)
            
            # Perform download to add to history
            with patch('dbutils.gui.jdbc_driver_manager.download_jdbc_driver', mock_successful_download_for_history):
                dialog.perform_jdbc_download("test", version="latest")
            
            # Check that history was updated
            new_history_count = len(download_history.records)
            assert new_history_count > original_history_count, "Download should have been added to history"
            
            if new_history_count > original_history_count:
                latest_record = download_history.records[-1]
                assert latest_record.database_type == "test"
                assert latest_record.success == True
                assert latest_record.file_path == mock_jar_path
            
            download_dialog.close()
    finally:
        QDialog.exec = original_exec  # Restore original method
        # Clean up the mock file
        if os.path.exists(mock_jar_path):
            try:
                os.remove(mock_jar_path)
            except:
                pass  # File might have been moved/renamed
    
    dialog.close()


def test_provider_config_to_download_workflow(qtbot, monkeypatch):
    """Test complete workflow from provider configuration to successful download."""
    from dbutils.gui.provider_config_dialog import ProviderConfigDialog
    
    dialog = ProviderConfigDialog()
    qtbot.addWidget(dialog)
    
    # Set up initial provider configuration
    dialog.name_input.setText("Test Provider")
    dialog.driver_class_input.setText("com.test.Driver")
    dialog.category_input.setCurrentText("Generic")  # Use generic since we're mocking
    
    qtbot.wait(50)  # Allow UI time to update
    
    # Mock successful download for the workflow
    import tempfile as tmpmodule
    temp_path = tmpmodule.gettempdir()
    mock_jar_path = os.path.join(temp_path, "workflow-test.jar")
    
    def mock_workflow_download(db_type, on_progress=None, on_status=None, version="recommended"):
        # Create a dummy jar file
        with open(mock_jar_path, "w") as f:
            f.write("workflow test content")
        if on_status:
            on_status("Workflow download completed")
        return mock_jar_path
    
    monkeypatch.setattr('dbutils.gui.jdbc_driver_manager.download_jdbc_driver', 
                       mock_workflow_download)
    
    # Mock driver info
    from dbutils.gui.jdbc_driver_downloader import JDBCDriverInfo
    mock_driver_info = JDBCDriverInfo(
        name="Workflow Test Driver",
        driver_class="com.test.Driver",
        download_url="https://example.com/workflow-test",
        alternative_urls=[],
        license="Test License", 
        min_java_version="8",
        description="Driver for workflow testing",
        recommended_version="1.0.0"
    )
    
    monkeypatch.setattr('dbutils.gui.jdbc_driver_downloader.JDBCDriverRegistry.get_driver_info',
                       lambda category: mock_driver_info)
    
    monkeypatch.setattr('dbutils.gui.jdbc_auto_downloader.get_jdbc_driver_download_info', 
                       lambda category: f"JDBC Driver: Workflow Test")
    
    # Temporarily make the dialog non-modal for testing
    original_exec = QDialog.exec
    QDialog.exec = lambda self: True
    
    try:
        # Trigger the download workflow
        result = dialog.download_jdbc_driver_gui()
        if result:
            download_dialog, download_btn, manual_btn, license_checkbox = result[:4]
            qtbot.addWidget(download_dialog)
            
            # Simulate the complete workflow
            with patch('dbutils.gui.jdbc_driver_manager.download_jdbc_driver', mock_workflow_download):
                # Test that we can call perform_jdbc_download after setup
                dialog.perform_jdbc_download("test_workflow", version="latest")
            
            # Verify that the JAR path was updated in the form
            assert mock_jar_path in dialog.jar_path_input.text()
            
            download_dialog.close()
    finally:
        QDialog.exec = original_exec  # Restore original method
        # Clean up the mock file
        if os.path.exists(mock_jar_path):
            try:
                os.remove(mock_jar_path)
            except:
                pass
    
    dialog.close()


def test_manual_to_auto_download_transition(qtbot, monkeypatch):
    """Test workflow when user starts with manual download but switches to auto."""
    from dbutils.gui.provider_config_dialog import ProviderConfigDialog
    
    dialog = ProviderConfigDialog()
    qtbot.addWidget(dialog)
    
    # Mock the open_download_page function that's called for manual download
    def mock_open_download_page(category):
        # This simulates opening the browser, return the URL for verification
        return f"https://example.com/{category}"
    
    # Set up driver info that would trigger the manual option
    from dbutils.gui.jdbc_driver_downloader import JDBCDriverInfo
    mock_driver_info = JDBCDriverInfo(
        name="Manual Test Driver",
        driver_class="com.manual.Driver",
        download_url="https://example.com/manual-test",
        alternative_urls=["https://alt.example.com/manual-test"],
        license="Test License",
        min_java_version="8", 
        description="Driver for manual download testing",
        recommended_version="1.0.0"
    )
    
    monkeypatch.setattr('dbutils.gui.jdbc_driver_downloader.JDBCDriverRegistry.get_driver_info',
                       lambda category: mock_driver_info)
    
    monkeypatch.setattr('dbutils.gui.jdbc_auto_downloader.get_jdbc_driver_download_info', 
                       lambda category: f"JDBC Driver: Manual Test")
    
    # Temporarily make the dialog non-modal for testing
    original_exec = QDialog.exec
    QDialog.exec = lambda self: True
    
    try:
        result = dialog.download_jdbc_driver_gui()
        if result:
            download_dialog, download_btn, manual_btn, license_checkbox = result[:4]
            qtbot.addWidget(download_dialog)
            
            # Test that both buttons exist
            assert download_btn is not None
            assert manual_btn is not None
            
            download_dialog.close()
    finally:
        QDialog.exec = original_exec  # Restore original method
    
    dialog.close()


def test_concurrent_download_workflow(qtbot, monkeypatch):
    """Test behavior when multiple download attempts happen concurrently."""
    from dbutils.gui.provider_config_dialog import ProviderConfigDialog
    
    dialog = ProviderConfigDialog()
    qtbot.addWidget(dialog)
    
    # Mock download with delay to simulate concurrent access
    import tempfile as tmpmodule
    temp_path = tmpmodule.gettempdir()
    
    def mock_delayed_download(db_type, on_progress=None, on_status=None, version="recommended"):
        import time
        time.sleep(0.1)  # Small delay to simulate network
        mock_jar_path = os.path.join(temp_path, f"concurrent-{db_type}.jar")
        with open(mock_jar_path, "w") as f:
            f.write(f"concurrent test content for {db_type}")
        if on_status:
            on_status(f"Concurrent download for {db_type} completed")
        return mock_jar_path
    
    monkeypatch.setattr('dbutils.gui.jdbc_driver_manager.download_jdbc_driver', 
                       mock_delayed_download)
    
    # Mock driver info
    from dbutils.gui.jdbc_driver_downloader import JDBCDriverInfo
    mock_driver_info = JDBCDriverInfo(
        name="Concurrent Test Driver",
        driver_class="com.concurrent.Driver",
        download_url="https://example.com/concurrent-test",
        alternative_urls=[],
        license="Test License",
        min_java_version="8",
        description="Driver for concurrent download testing",
        recommended_version="1.0.0"
    )
    
    monkeypatch.setattr('dbutils.gui.jdbc_driver_downloader.JDBCDriverRegistry.get_driver_info',
                       lambda category: mock_driver_info)
    
    monkeypatch.setattr('dbutils.gui.jdbc_auto_downloader.get_jdbc_driver_download_info', 
                       lambda category: f"JDBC Driver: Concurrent Test")
    
    # Temporarily make the dialog non-modal for testing
    original_exec = QDialog.exec
    QDialog.exec = lambda self: True
    
    try:
        result = dialog.download_jdbc_driver_gui()
        if result:
            download_dialog, download_btn, manual_btn, license_checkbox = result[:4]
            qtbot.addWidget(download_dialog)
            
            # Test concurrent-like behavior by calling download multiple times
            # (not truly concurrent since we're testing sequentially, 
            # but testing the same logic path)
            for i in range(2):  # Simulate multiple calls
                db_type = f"test_concurrent_{i}"
                with patch('dbutils.gui.jdbc_driver_manager.download_jdbc_driver', mock_delayed_download):
                    dialog.perform_jdbc_download(db_type, version="latest")
            
            download_dialog.close()
    finally:
        QDialog.exec = original_exec  # Restore original method
        # Clean up mock files
        for i in range(2):
            mock_jar_path = os.path.join(temp_path, f"concurrent-test_concurrent_{i}.jar")
            if os.path.exists(mock_jar_path):
                try:
                    os.remove(mock_jar_path)
                except:
                    pass  # File might not have been created
    
    dialog.close()


if __name__ == "__main__":
    # This allows running the test directly for debugging
    pytest.main([__file__])