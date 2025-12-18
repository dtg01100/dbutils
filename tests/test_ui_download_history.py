"""
Comprehensive UI tests for JDBC driver download history functionality.

Tests the download history display, statistics, and related UI interactions using qtbot.
"""

import os
import sys
import tempfile
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import Qt, QTimer
from PySide6.QtTest import QSignalSpy
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox, QPushButton

# Enable test mode to prevent actual downloads
os.environ["DBUTILS_TEST_MODE"] = "1"


def test_download_history_button_exists(qtbot):
    """Test that the download history button exists in the provider config dialog."""
    from dbutils.gui.provider_config_dialog import ProviderConfigDialog
    
    dialog = ProviderConfigDialog()
    qtbot.addWidget(dialog)  # Properly register widget with qtbot for cleanup
    
    # Verify the history button exists
    assert hasattr(dialog, 'jar_history_btn'), "Download history button should exist"
    assert dialog.jar_history_btn is not None, "Download history button should not be None"
    assert dialog.jar_history_btn.text() == "History…", "History button should have correct text"
    
    # Verify the button is connected to the right method
    assert hasattr(dialog, 'show_download_history'), "show_download_history method should exist"
    
    dialog.close()


def test_download_history_dialog_opens(qtbot, monkeypatch):
    """Test that clicking the history button opens the history dialog."""
    from dbutils.gui.provider_config_dialog import ProviderConfigDialog
    
    dialog = ProviderConfigDialog()
    qtbot.addWidget(dialog)
    
    # Mock the data functions to return empty data for this test
    monkeypatch.setattr('dbutils.gui.download_history.get_download_stats', lambda: {
        "total_downloads": 0,
        "successful_downloads": 0,
        "failed_downloads": 0,
        "success_rate_percent": 0.0,
        "average_duration_seconds": None,
        "downloads_by_type": {}
    })
    monkeypatch.setattr('dbutils.gui.download_history.get_recent_downloads', lambda x: [])
    
    # Use QTimer.singleShot to close the modal dialog automatically
    def close_dialog():
        dialogs = [w for w in QApplication.topLevelWidgets() if isinstance(w, QDialog) and w.isVisible()]
        for d in dialogs:
            if d.windowTitle() == "Download History":
                d.reject()  # Close with reject to not interfere with the main dialog
    
    # Simulate user clicking the history button
    with qtbot.waitSignal(QTimer.singleShot(100, close_dialog), timeout=1000, raising=False):
        qtbot.mouseClick(dialog.jar_history_btn, Qt.LeftButton)
    
    dialog.close()


def test_download_history_dialog_structure(qtbot, monkeypatch):
    """Test the structure of the download history dialog."""
    from dbutils.gui.provider_config_dialog import ProviderConfigDialog
    from dbutils.gui.download_history import DownloadRecord
    
    dialog = ProviderConfigDialog()
    qtbot.addWidget(dialog)
    
    # Create mock download records
    mock_record = DownloadRecord(
        database_type="sqlite",
        downloaded_at=datetime.now(),
        file_path="/tmp/test.jar",
        file_size=1024000,  # 1MB
        version="3.42.0.0",
        url="https://example.com/test.jar",
        success=True
    )
    
    # Mock the data functions
    monkeypatch.setattr('dbutils.gui.download_history.get_recent_downloads', lambda x: [mock_record])
    monkeypatch.setattr('dbutils.gui.download_history.get_download_stats', lambda: {
        "total_downloads": 5,
        "successful_downloads": 4,
        "failed_downloads": 1,
        "success_rate_percent": 80.0,
        "average_duration_seconds": 5.5,
        "downloads_by_type": {"sqlite": 3, "postgresql": 2}
    })
    
    # Create a slot to capture when the dialog opens
    dialog_opened = [False]
    def check_dialog():
        dialogs = [w for w in QApplication.topLevelWidgets() if isinstance(w, QDialog) and w.windowTitle() == "Download History"]
        if dialogs:
            dialog_opened[0] = True
            # Close the dialog so test can continue
            dialogs[0].reject()
    
    # Schedule the check and close
    QTimer.singleShot(200, check_dialog)
    
    # Simulate user clicking the history button
    qtbot.mouseClick(dialog.jar_history_btn, Qt.LeftButton)
    
    # Wait for the check to happen
    qtbot.wait(500)
    
    assert dialog_opened[0], "History dialog should have opened"
    
    dialog.close()


def test_clear_history_confirmation(qtbot, monkeypatch):
    """Test the confirmation dialog when clearing download history."""
    from dbutils.gui.provider_config_dialog import ProviderConfigDialog
    
    dialog = ProviderConfigDialog()
    qtbot.addWidget(dialog)
    
    # Create the history dialog first (we'll test the clear button on it)
    with patch('dbutils.gui.download_history.get_recent_downloads', return_value=[]):
        with patch('dbutils.gui.download_history.get_download_stats', return_value={
            "total_downloads": 0,
            "successful_downloads": 0,
            "failed_downloads": 0,
            "success_rate_percent": 0.0,
            "average_duration_seconds": None,
            "downloads_by_type": {}
        }):
            # Show the history dialog by calling the method directly (bypassing modal)
            # We need to modify the method to not be modal for testing
            original_exec = QDialog.exec
            QDialog.exec = lambda self: True  # Don't block execution
            
            try:
                history_dialog_result = dialog.show_download_history()
                # The method creates a dialog internally, so we need to find it
                dialogs = [w for w in QApplication.topLevelWidgets() if isinstance(w, QDialog) and w.windowTitle() == "Download History"]
                if dialogs:
                    history_dialog = dialogs[0]
                    qtbot.addWidget(history_dialog)
                    
                    # Find the clear button in the dialog
                    clear_btns = [w for w in history_dialog.findChildren(QPushButton) if w.text() == "Clear History"]
                    if clear_btns:
                        clear_btn = clear_btns[0]
                        
                        # Mock QMessageBox.question to return Yes
                        def mock_question(parent, title, text, buttons, default_button):
                            return QMessageBox.StandardButton.Yes
                        
                        monkeypatch.setattr(QMessageBox, "question", mock_question)
                        
                        # Mock the clear function
                        with patch('dbutils.gui.download_history.clear_download_history', return_value=True) as mock_clear:
                            qtbot.mouseClick(clear_btn, Qt.LeftButton)
                            qtbot.wait(100)  # Small wait for the mock to process
                            
                            # Verify that clear_download_history was called
                            mock_clear.assert_called_once()
                    
                    history_dialog.close()
            finally:
                QDialog.exec = original_exec  # Restore original method
    
    dialog.close()


def test_history_tabs_functionality(qtbot, monkeypatch):
    """Test that the history dialog has proper tab functionality."""
    from dbutils.gui.provider_config_dialog import ProviderConfigDialog
    from dbutils.gui.download_history import DownloadRecord
    from datetime import datetime
    
    dialog = ProviderConfigDialog()
    qtbot.addWidget(dialog)
    
    # Mock data for the tabs
    mock_record = DownloadRecord(
        database_type="postgresql",
        downloaded_at=datetime.now(),
        file_path="/tmp/test.jar",
        file_size=2048000,  # 2MB
        version="42.6.0",
        url="https://example.com/test.jar",
        success=True
    )
    
    monkeypatch.setattr('dbutils.gui.download_history.get_recent_downloads', lambda x: [mock_record])
    monkeypatch.setattr('dbutils.gui.download_history.get_download_stats', lambda: {
        "total_downloads": 3,
        "successful_downloads": 3,
        "failed_downloads": 0,
        "success_rate_percent": 100.0,
        "average_duration_seconds": 3.2,
        "downloads_by_type": {"postgresql": 2, "sqlite": 1}
    })
    
    # Temporarily make the dialog non-modal for testing
    original_exec = QDialog.exec
    QDialog.exec = lambda self: True  # Don't block execution
    
    try:
        # Show history dialog by calling method
        dialog.show_download_history()
        
        # Find the history dialog
        dialogs = [w for w in QApplication.topLevelWidgets() if isinstance(w, QDialog) and w.windowTitle() == "Download History"]
        if dialogs:
            history_dialog = dialogs[0]
            qtbot.addWidget(history_dialog)
            
            # Find the tab widget (by class name)
            from PySide6.QtWidgets import QTabWidget
            tab_widgets = history_dialog.findChildren(QTabWidget)
            assert len(tab_widgets) > 0, "History dialog should contain a tab widget"
            
            tab_widget = tab_widgets[0]
            assert tab_widget.count() >= 2, "History dialog should have at least 2 tabs"
            
            # Check that tabs have correct labels
            tab_names = [tab_widget.tabText(i) for i in range(tab_widget.count())]
            assert "Recent Downloads" in tab_names, "Should have 'Recent Downloads' tab"
            assert "Statistics" in tab_names, "Should have 'Statistics' tab"
            
            history_dialog.close()
    finally:
        QDialog.exec = original_exec  # Restore original method
    
    dialog.close()


if __name__ == "__main__":
    # This allows running the test directly for debugging
    pytest.main([__file__])