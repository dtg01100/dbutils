"""
Test suite for automatic JDBC driver download functionality in ProviderConfigDialog.

This module tests the integration between the provider configuration dialog
and the automatic JDBC driver download system.
"""

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox, QInputDialog

from dbutils.enhanced_jdbc_provider import EnhancedProviderRegistry, JDBCProvider
from dbutils.gui.provider_config_dialog import ProviderConfigDialog


@pytest.fixture
def qapp():
    """Fixture to provide a QApplication instance for Qt tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def setup_test_environment(tmp_path, monkeypatch):
    """Set up test environment with temporary config and driver directories."""
    config_dir = tmp_path / ".config" / "dbutils"
    driver_dir = tmp_path / "drivers"
    
    monkeypatch.setenv("DBUTILS_CONFIG_DIR", str(config_dir))
    monkeypatch.setenv("DBUTILS_DRIVER_DIR", str(driver_dir))
    monkeypatch.setenv("DBUTILS_TEST_MODE", "1")
    
    config_dir.mkdir(parents=True, exist_ok=True)
    driver_dir.mkdir(parents=True, exist_ok=True)
    
    # Set up a basic providers.json file
    providers_file = config_dir / "providers.json"
    providers_file.write_text(json.dumps([]))
    
    return {"config_dir": config_dir, "driver_dir": driver_dir}


def test_download_dialog_creation(qapp, setup_test_environment):
    """Test that download dialog is created with proper structure."""
    dialog = ProviderConfigDialog()
    
    # Set category to PostgreSQL
    dialog.category_input.setCurrentText("PostgreSQL")
    
    # Call download_jdbc_driver_gui in test mode
    result = dialog.download_jdbc_driver_gui()
    
    # In test mode, this returns the dialog and controls
    assert result is not None
    assert len(result) == 4  # dialog, download_btn, manual_btn, license_checkbox
    
    download_dialog, download_btn, manual_btn, license_checkbox = result
    
    # Verify dialog structure
    assert download_dialog is not None
    assert download_btn is not None
    assert manual_btn is not None
    # PostgreSQL is open source, so no license checkbox
    assert license_checkbox is None
    
    # Verify buttons are enabled (no license required for PostgreSQL)
    assert download_btn.isEnabled()
    assert manual_btn.isEnabled()


def test_download_dialog_with_license(qapp, setup_test_environment):
    """Test download dialog for proprietary drivers that require license acceptance."""
    dialog = ProviderConfigDialog()
    
    # Set category to Oracle (proprietary)
    dialog.category_input.setCurrentText("Oracle")
    
    # Call download_jdbc_driver_gui in test mode
    result = dialog.download_jdbc_driver_gui()
    
    assert result is not None
    download_dialog, download_btn, manual_btn, license_checkbox = result[:4]
    
    # Oracle requires license, so checkbox should exist
    assert license_checkbox is not None
    
    # Buttons should be disabled until license is accepted
    assert not download_btn.isEnabled()
    assert not manual_btn.isEnabled()
    
    # Accept license
    license_checkbox.setChecked(True)
    
    # Buttons should now be enabled
    assert download_btn.isEnabled()
    assert manual_btn.isEnabled()


def test_perform_jdbc_download_success(qapp, setup_test_environment, monkeypatch):
    """Test successful JDBC driver download."""
    driver_dir = setup_test_environment["driver_dir"]
    
    dialog = ProviderConfigDialog()
    
    # Create fake jar file that will be "downloaded"
    fake_jar = driver_dir / "postgresql-42.5.0.jar"
    
    # Mock the download function to create a fake jar
    def mock_download(category, on_progress=None, on_status=None, version=None):
        fake_jar.write_text("fake jar content")
        if on_status:
            on_status(f"Downloading {category} driver...")
        if on_progress:
            on_progress(100, 100)
        return str(fake_jar)
    
    with patch("dbutils.gui.jdbc_driver_manager.download_jdbc_driver", mock_download):
        with patch.object(QMessageBox, "information") as mock_info:
            dialog.perform_jdbc_download("postgresql", version="latest")
            
            # Should show success message
            mock_info.assert_called_once()
            args = mock_info.call_args[0]
            assert "Successfully downloaded" in args[2]
            
            # Should set jar path
            assert dialog.jar_path_input.text() == str(fake_jar)


def test_perform_jdbc_download_multiple_jars(qapp, setup_test_environment):
    """Test download of drivers with multiple JAR files."""
    driver_dir = setup_test_environment["driver_dir"]
    
    dialog = ProviderConfigDialog()
    
    # Create multiple fake jars
    jar1 = driver_dir / "db2jcc.jar"
    jar2 = driver_dir / "db2jcc_license_cu.jar"
    
    def mock_download(category, on_progress=None, on_status=None, version=None):
        jar1.write_text("fake jar 1")
        jar2.write_text("fake jar 2")
        return [str(jar1), str(jar2)]
    
    with patch("dbutils.gui.jdbc_driver_manager.download_jdbc_driver", mock_download):
        with patch.object(QMessageBox, "information") as mock_info:
            dialog.perform_jdbc_download("db2", version="latest")
            
            # Should show success with both files listed
            mock_info.assert_called_once()
            args = mock_info.call_args[0]
            assert "db2jcc.jar" in args[2]
            assert "db2jcc_license_cu.jar" in args[2]
            
            # Should set first jar path
            assert dialog.jar_path_input.text() == str(jar1)


def test_perform_jdbc_download_failure(qapp, setup_test_environment):
    """Test handling of download failures."""
    dialog = ProviderConfigDialog()
    
    # Mock download to return None (failure)
    def mock_download(category, on_progress=None, on_status=None, version=None):
        return None
    
    with patch("dbutils.gui.jdbc_driver_manager.download_jdbc_driver", mock_download):
        with patch.object(QMessageBox, "warning") as mock_warning:
            dialog.perform_jdbc_download("postgresql", version="latest")
            
            # Should show warning
            mock_warning.assert_called_once()
            args = mock_warning.call_args[0]
            assert "Download Failed" in args[1]


def test_perform_jdbc_download_exception(qapp, setup_test_environment):
    """Test handling of download exceptions."""
    dialog = ProviderConfigDialog()
    
    # Mock download to raise exception
    def mock_download(category, on_progress=None, on_status=None, version=None):
        raise Exception("Network error")
    
    with patch("dbutils.gui.jdbc_driver_manager.download_jdbc_driver", mock_download):
        with patch.object(QMessageBox, "critical") as mock_critical:
            dialog.perform_jdbc_download("postgresql", version="latest")
            
            # Should show error
            mock_critical.assert_called_once()
            args = mock_critical.call_args[0]
            assert "Download Error" in args[1]
            assert "Network error" in args[2]


def test_download_with_version_selection(qapp, setup_test_environment):
    """Test download with specific version selection."""
    driver_dir = setup_test_environment["driver_dir"]
    
    dialog = ProviderConfigDialog()
    
    fake_jar = driver_dir / "postgresql-42.3.0.jar"
    
    requested_version = None
    
    def mock_download(category, on_progress=None, on_status=None, version=None):
        nonlocal requested_version
        requested_version = version
        fake_jar.write_text("fake jar")
        return str(fake_jar)
    
    with patch("dbutils.gui.jdbc_driver_manager.download_jdbc_driver", mock_download):
        with patch.object(QMessageBox, "information"):
            dialog.perform_jdbc_download("postgresql", version="42.3.0")
            
            # Should have requested specific version
            assert requested_version == "42.3.0"


def test_download_progress_callback(qapp, setup_test_environment):
    """Test that progress callbacks are properly handled."""
    dialog = ProviderConfigDialog()
    
    def mock_download(category, on_progress=None, on_status=None, version=None):
        if on_progress:
            # Simulate progress updates
            on_progress(0, 100)
            on_progress(50, 100)
            on_progress(100, 100)
            
        return "/fake/path.jar"
    
    with patch("dbutils.gui.jdbc_driver_manager.download_jdbc_driver", mock_download):
        with patch.object(QMessageBox, "information"):
            dialog.perform_jdbc_download("postgresql", version="latest")
            
            # Should have progress widget created
            assert hasattr(dialog, "download_progress")


def test_download_status_callback(qapp, setup_test_environment):
    """Test that status callbacks update the UI."""
    dialog = ProviderConfigDialog()
    
    def mock_download(category, on_progress=None, on_status=None, version=None):
        if on_status:
            on_status("Connecting to repository...")
            on_status("Downloading driver...")
            on_status("Extracting files...")
        return "/fake/path.jar"
    
    with patch("dbutils.gui.jdbc_driver_manager.download_jdbc_driver", mock_download):
        with patch.object(QMessageBox, "information"):
            dialog.perform_jdbc_download("postgresql", version="latest")
            
            # Status label should exist and have been updated
            assert hasattr(dialog, "download_status_label")


def test_open_download_page(qapp, setup_test_environment):
    """Test opening the download page for manual downloads."""
    dialog = ProviderConfigDialog()
    
    # Mock JDBCDriverRegistry
    mock_driver_info = Mock()
    mock_driver_info.download_url = "https://jdbc.postgresql.org/download.html"
    
    with patch("dbutils.gui.jdbc_driver_downloader.JDBCDriverRegistry") as mock_registry:
        mock_registry.get_driver_info.return_value = mock_driver_info
        
        # In test mode, should return URL instead of opening browser
        url = dialog.open_download_page("PostgreSQL")
        
        assert url == "https://jdbc.postgresql.org/download.html"


def test_download_integration_with_provider_save(qapp, setup_test_environment):
    """Test complete workflow: download driver and save provider."""
    driver_dir = setup_test_environment["driver_dir"]
    
    dialog = ProviderConfigDialog()
    
    # Set up provider details
    dialog.name_input.setText("Test PostgreSQL")
    dialog.category_input.setCurrentText("PostgreSQL")
    dialog.driver_class_input.setText("org.postgresql.Driver")
    dialog.url_template_input.setPlainText("jdbc:postgresql://{host}:{port}/{database}")
    dialog.host_input.setText("localhost")
    dialog.port_input.setValue(5432)  # QSpinBox uses setValue, not setText
    dialog.database_input.setText("testdb")
    
    # Mock download
    fake_jar = driver_dir / "postgresql-42.5.0.jar"
    
    def mock_download(category, on_progress=None, on_status=None, version=None):
        fake_jar.write_text("fake jar")
        return str(fake_jar)
    
    with patch("dbutils.gui.jdbc_driver_manager.download_jdbc_driver", mock_download):
        with patch.object(QMessageBox, "information"):
            dialog.perform_jdbc_download("postgresql", version="latest")
    
    # Now save the provider
    dialog.accept()
    
    # Verify provider was saved with correct jar path
    registry = EnhancedProviderRegistry()
    provider = registry.get_provider("Test PostgreSQL")
    
    assert provider is not None
    assert provider.jar_path == str(fake_jar)
    assert provider.driver_class == "org.postgresql.Driver"
    assert provider.category == "PostgreSQL"


def test_license_store_integration(qapp, setup_test_environment):
    """Test that license acceptance is properly stored and retrieved."""
    dialog = ProviderConfigDialog()
    
    # Set category to Oracle
    dialog.category_input.setCurrentText("Oracle")
    
    result = dialog.download_jdbc_driver_gui()
    download_dialog, download_btn, manual_btn, license_checkbox = result[:4]
    
    # Initially buttons should be disabled
    assert not download_btn.isEnabled()
    
    # Accept license and store it
    license_checkbox.setChecked(True)
    
    # Buttons should be enabled after accepting license
    assert download_btn.isEnabled()
    
    # Mock is_license_accepted in the license_store module to return True
    with patch("dbutils.gui.license_store.is_license_accepted", return_value=True):
        # Create new dialog - license should be remembered
        dialog2 = ProviderConfigDialog()
        dialog2.category_input.setCurrentText("Oracle")
        
        result2 = dialog2.download_jdbc_driver_gui()
        download_dialog2, download_btn2, manual_btn2, license_checkbox2 = result2[:4]
        
        # License should already be checked and buttons enabled
        assert license_checkbox2.isChecked()
        assert download_btn2.isEnabled()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
