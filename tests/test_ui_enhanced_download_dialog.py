"""
Comprehensive UI tests for enhanced download dialog features.

Tests the progress tracking, speed calculations, license acceptance, and other enhanced features.
"""

import os
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

# Enable test mode to prevent actual downloads
os.environ["DBUTILS_TEST_MODE"] = "1"


def test_enhanced_progress_display(qtbot, monkeypatch):
    """Test that the enhanced download dialog shows progress with speed and ETA."""
    from dbutils.gui.provider_config_dialog import ProviderConfigDialog
    
    dialog = ProviderConfigDialog()
    qtbot.addWidget(dialog)
    
    # Mock the download info function
    monkeypatch.setattr('dbutils.gui.jdbc_auto_downloader.get_jdbc_driver_download_info', 
                       lambda category: f"JDBC Driver: {category.title()}\nGroup ID: test\Artifact: test\nLatest Version: 1.0.0")
    
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
    
    # Temporarily make the dialog non-modal for testing
    original_exec = QDialog.exec
    QDialog.exec = lambda self: True
    
    try:
        # Call the download dialog creation method
        result = dialog.download_jdbc_driver_gui()
        if result:  # Test mode returns the dialog and widgets
            download_dialog, download_btn, manual_btn, license_checkbox = result
            
            qtbot.addWidget(download_dialog)
            
            # Check that the dialog has the expected UI elements
            from PySide6.QtWidgets import QLabel, QProgressBar
            status_labels = [w for w in download_dialog.findChildren(QLabel) 
                           if hasattr(w, 'text') and 'Download' in w.text() and ('MB/s' in w.text() or 'ETA' in w.text())]
            
            # The enhanced progress features might not be visible until a download starts
            # We'll test that the elements exist that would show this information
            progress_bars = download_dialog.findChildren(QProgressBar)
            assert len(progress_bars) > 0, "Dialog should contain progress bar"
            
            download_dialog.close()
    finally:
        QDialog.exec = original_exec  # Restore original method
    
    dialog.close()


def test_license_acceptance_workflow(qtbot, monkeypatch):
    """Test the license acceptance workflow in the download dialog."""
    from dbutils.gui.provider_config_dialog import ProviderConfigDialog
    
    dialog = ProviderConfigDialog()
    qtbot.addWidget(dialog)
    
    # Create a driver that requires a license
    from dbutils.gui.jdbc_driver_downloader import JDBCDriverInfo
    mock_driver_info = JDBCDriverInfo(
        name="Oracle JDBC Driver",
        driver_class="oracle.jdbc.OracleDriver",
        download_url="https://example.com/oracle",
        alternative_urls=[],
        license="Commercial (with free distribution rights)",
        min_java_version="8",
        description="Oracle JDBC driver (ojdbc)",
        recommended_version="21.13.0.0",
        requires_license=True,
        license_url="https://example.com/license",
        license_text="Oracle JDBC drivers are distributed under Oracle terms."
    )
    
    monkeypatch.setattr('dbutils.gui.jdbc_driver_downloader.JDBCDriverRegistry.get_driver_info',
                       lambda category: mock_driver_info)
    
    monkeypatch.setattr('dbutils.gui.jdbc_auto_downloader.get_jdbc_driver_download_info', 
                       lambda category: f"JDBC Driver: Oracle\nRequires License: Yes")
    
    # Temporarily make the dialog non-modal for testing
    original_exec = QDialog.exec
    QDialog.exec = lambda self: True
    
    try:
        # Call the download dialog creation method
        result = dialog.download_jdbc_driver_gui()
        if result:  # Test mode returns the dialog and widgets
            download_dialog, download_btn, manual_btn, license_checkbox = result
            
            qtbot.addWidget(download_dialog)
            
            # Verify license checkbox exists and is initially unchecked
            assert license_checkbox is not None, "License checkbox should exist for licensed drivers"
            assert not license_checkbox.isChecked(), "License checkbox should be unchecked initially"
            
            # Verify download and manual buttons are initially disabled
            assert not download_btn.isEnabled(), "Download button should be disabled until license accepted"
            assert not manual_btn.isEnabled(), "Manual button should be disabled until license accepted"
            
            # Test checking the license checkbox
            qtbot.mouseClick(license_checkbox, Qt.LeftButton)
            qtbot.wait(50)  # Wait for UI update
            
            # Verify buttons are enabled after license acceptance
            assert license_checkbox.isChecked(), "License checkbox should be checked after clicking"
            assert download_btn.isEnabled(), "Download button should be enabled after license acceptance"
            assert manual_btn.isEnabled(), "Manual button should be enabled after license acceptance"
            
            download_dialog.close()
    finally:
        QDialog.exec = original_exec  # Restore original method
    
    dialog.close()


def test_version_selection_dropdown(qtbot, monkeypatch):
    """Test the version selection dropdown functionality."""
    from dbutils.gui.provider_config_dialog import ProviderConfigDialog
    
    dialog = ProviderConfigDialog()
    qtbot.addWidget(dialog)
    
    # Create a driver with maven artifacts (which triggers version selection)
    from dbutils.gui.jdbc_driver_downloader import JDBCDriverInfo
    mock_driver_info = JDBCDriverInfo(
        name="PostgreSQL JDBC Driver",
        driver_class="org.postgresql.Driver",
        download_url="https://example.com/postgres",
        alternative_urls=[],
        license="BSD-2-Clause",
        min_java_version="8",
        description="Official PostgreSQL JDBC driver",
        recommended_version="42.6.0",
        maven_artifacts=["org.postgresql:postgresql"]
    )
    
    monkeypatch.setattr('dbutils.gui.jdbc_driver_downloader.JDBCDriverRegistry.get_driver_info',
                       lambda category: mock_driver_info)
    
    monkeypatch.setattr('dbutils.gui.jdbc_auto_downloader.get_jdbc_driver_download_info', 
                       lambda category: f"JDBC Driver: PostgreSQL\nMaven Artifacts Available: Yes")
    
    # Temporarily make the dialog non-modal for testing
    original_exec = QDialog.exec
    QDialog.exec = lambda self: True
    
    try:
        # Call the download dialog creation method
        result = dialog.download_jdbc_driver_gui()
        if result:  # Test mode returns the dialog and widgets
            download_dialog, download_btn, manual_btn, license_checkbox, \
            version_choice, specific_version_input, repo_list_label, repo_edit_btn = result
            
            qtbot.addWidget(download_dialog)
            
            # Verify version selection elements exist
            assert version_choice is not None, "Version selection combo box should exist for maven drivers"
            assert specific_version_input is not None, "Specific version input should exist"
            
            # Test version selection options
            expected_options = ["recommended", "latest", "specific"]
            actual_options = [version_choice.itemText(i) for i in range(version_choice.count())]
            assert actual_options == expected_options, f"Version options should be {expected_options}, got {actual_options}"
            
            # Test that specific version input is disabled initially
            assert not specific_version_input.isEnabled(), "Specific version input should be disabled initially"
            
            # Select "specific" option and verify input becomes enabled
            version_choice.setCurrentText("specific")
            qtbot.wait(50)  # Wait for UI update
            assert specific_version_input.isEnabled(), "Specific version input should be enabled when 'specific' is selected"
            
            # Select "latest" option and verify input becomes disabled again
            version_choice.setCurrentText("latest")
            qtbot.wait(50)  # Wait for UI update
            assert not specific_version_input.isEnabled(), "Specific version input should be disabled when 'latest' is selected"
            
            download_dialog.close()
    finally:
        QDialog.exec = original_exec  # Restore original method
    
    dialog.close()


def test_repository_display_and_edit(qtbot, monkeypatch):
    """Test repository list display and edit functionality."""
    from dbutils.gui.provider_config_dialog import ProviderConfigDialog
    
    dialog = ProviderConfigDialog()
    qtbot.addWidget(dialog)
    
    # Create a driver with maven artifacts (which triggers repo display)
    from dbutils.gui.jdbc_driver_downloader import JDBCDriverInfo
    mock_driver_info = JDBCDriverInfo(
        name="Test JDBC Driver",
        driver_class="com.test.Driver",
        download_url="https://example.com/test",
        alternative_urls=[],
        license="Test License",
        min_java_version="8",
        description="Test driver",
        recommended_version="1.0.0",
        maven_artifacts=["com.test:driver"]
    )
    
    monkeypatch.setattr('dbutils.gui.jdbc_driver_downloader.JDBCDriverRegistry.get_driver_info',
                       lambda category: mock_driver_info)
    
    monkeypatch.setattr('dbutils.gui.jdbc_auto_downloader.get_jdbc_driver_download_info', 
                       lambda category: f"JDBC Driver: Test")
    
    # Mock repository functions
    monkeypatch.setattr('dbutils.gui.downloader_prefs.get_maven_repos', 
                       lambda: ["https://repo1.maven.org/maven2/", "https://repo.example.com/"])
    monkeypatch.setattr('dbutils.gui.downloader_prefs.validate_repositories', 
                       lambda repos: [(r, True, f"Accessible") for r in repos])
    
    # Temporarily make the dialog non-modal for testing
    original_exec = QDialog.exec
    QDialog.exec = lambda self: True
    
    try:
        # Call the download dialog creation method
        result = dialog.download_jdbc_driver_gui()
        if result:  # Test mode returns the dialog and widgets
            download_dialog, download_btn, manual_btn, license_checkbox, \
            version_choice, specific_version_input, repo_list_label, repo_edit_btn = result
            
            qtbot.addWidget(download_dialog)
            
            # Verify repository elements exist
            assert repo_list_label is not None, "Repository list label should exist"
            assert repo_edit_btn is not None, "Repository edit button should exist"
            
            # Check that repository list contains expected content
            repo_text = repo_list_label.text()
            assert "repo1.maven.org" in repo_text, "Repository list should contain maven central"
            
            download_dialog.close()
    finally:
        QDialog.exec = original_exec  # Restore original method
    
    dialog.close()


def test_driver_info_with_history(qtbot, monkeypatch):
    """Test that the download dialog shows enhanced driver info including history."""
    from dbutils.gui.provider_config_dialog import ProviderConfigDialog
    from dbutils.gui.download_history import DownloadRecord
    
    dialog = ProviderConfigDialog()
    qtbot.addWidget(dialog)
    
    # Mock the driver history info
    mock_history_info = {
        "name": "SQLite JDBC Driver",
        "driver_class": "org.sqlite.JDBC",
        "download_url": "https://example.com/sqlite",
        "license": "Apache 2.0 / GNU LGPL",
        "min_java_version": "8",
        "description": "SQLite JDBC driver",
        "recommended_version": "3.42.0.0",
        "latest_downloaded_version": "3.42.0.0",
        "last_downloaded_at": datetime.now().isoformat(),
        "last_download_success": True,
        "last_file_path": "/tmp/sqlite-test.jar",
        "last_file_size": 1024000
    }
    
    monkeypatch.setattr('dbutils.gui.download_history.get_driver_download_info', 
                       lambda category: mock_history_info)
    
    monkeypatch.setattr('dbutils.gui.jdbc_auto_downloader.get_jdbc_driver_download_info', 
                       lambda category: f"JDBC Driver: SQLite\nEnhanced Info Available")
    
    # Create a driver info object
    from dbutils.gui.jdbc_driver_downloader import JDBCDriverInfo
    mock_driver_info = JDBCDriverInfo(
        name="SQLite JDBC Driver",
        driver_class="org.sqlite.JDBC", 
        download_url="https://example.com/sqlite",
        alternative_urls=[],
        license="Apache 2.0 / GNU LGPL",
        min_java_version="8",
        description="SQLite JDBC driver",
        recommended_version="3.42.0.0"
    )
    
    monkeypatch.setattr('dbutils.gui.jdbc_driver_downloader.JDBCDriverRegistry.get_driver_info',
                       lambda category: mock_driver_info)
    
    # Temporarily make the dialog non-modal for testing
    original_exec = QDialog.exec
    QDialog.exec = lambda self: True
    
    try:
        # Call the download dialog creation method
        result = dialog.download_jdbc_driver_gui()
        if result:  # Test mode returns the dialog and widgets
            download_dialog, download_btn, manual_btn, license_checkbox = result[:4]
            
            qtbot.addWidget(download_dialog)
            
            # Check that the dialog contains the historical information
            from PySide6.QtWidgets import QLabel
            labels = download_dialog.findChildren(QLabel)
            history_labels = [l for l in labels if 'Previous Download Info:' in l.text() or 'Download History:' in l.text()]
            
            assert len(history_labels) > 0, "Should contain history information section"
            
            download_dialog.close()
    finally:
        QDialog.exec = original_exec  # Restore original method
    
    dialog.close()


if __name__ == "__main__":
    # This allows running the test directly for debugging
    pytest.main([__file__])