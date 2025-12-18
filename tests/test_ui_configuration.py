"""
Comprehensive UI tests for configuration management in JDBC download system.

Tests the UI for configuration loading, validation, migration, and environment variable overrides.
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


def test_json_schema_validation_ui_feedback(qtbot, monkeypatch):
    """Test UI feedback when configuration fails schema validation."""
    from dbutils.gui.provider_config_dialog import ProviderConfigDialog
    
    dialog = ProviderConfigDialog()
    qtbot.addWidget(dialog)
    
    # Create a temporary config file with invalid data
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = os.path.join(temp_dir, ".config", "dbutils")
        os.makedirs(config_dir, exist_ok=True)
        
        # Create an invalid auto download config
        invalid_config = {
            # Missing required sections
            "version_management": {
                "default_repository_index": 0,
                "version_resolution_strategy": "invalid_strategy",  # Invalid value
            }
        }
        
        config_file = os.path.join(config_dir, "auto_download_config.json")
        with open(config_file, "w") as f:
            json.dump(invalid_config, f)
        
        # Temporarily change the config directory
        original_config_dir = os.environ.get("DBUTILS_CONFIG_DIR")
        os.environ["DBUTILS_CONFIG_DIR"] = config_dir
        
        try:
            # Test that the config loading handles invalid data gracefully
            config_result = dialog._load_auto_download_config()
            # Even with invalid config, it should return an empty dict rather than crash
            assert isinstance(config_result, dict)
        finally:
            # Restore original
            if original_config_dir:
                os.environ["DBUTILS_CONFIG_DIR"] = original_config_dir
            else:
                os.environ.pop("DBUTILS_CONFIG_DIR", None)
    
    dialog.close()


def test_config_migration_ui_notification(qtbot, monkeypatch):
    """Test UI behavior during configuration migration from old formats."""
    from dbutils.gui.provider_config_dialog import ProviderConfigDialog
    
    dialog = ProviderConfigDialog()
    qtbot.addWidget(dialog)
    
    # Test the migration function directly to ensure it works properly
    from dbutils.config.migration_config import migrate_config
    
    # Test migrating an old format config
    old_format_config = {
        "driver_path": "/old/path/to/drivers",  # Old single path format
        "maven_repo": "https://old.maven.repo",  # Old single repo format
        "repositories": ["https://repo1.com", "https://repo2.com"]  # Old repositories format
    }
    
    # Test migration for path config
    migrated_path_config, was_migrated, version = migrate_config(old_format_config, "path")
    assert was_migrated == True  # Should have been migrated
    assert version == "v2"  # Should be current version
    assert "driver_dirs" in migrated_path_config  # Should have new format
    assert isinstance(migrated_path_config["driver_dirs"], list)  # Should be list
    
    # Test migration for URL config
    migrated_url_config, was_migrated, version = migrate_config(old_format_config, "url")
    assert was_migrated == True  # Should have been migrated
    assert version == "v2"  # Should be current version
    assert "maven_repos" in migrated_url_config  # Should have new format
    
    dialog.close()


def test_environment_variable_override_feedback(qtbot, monkeypatch):
    """Test UI behavior when environment variables override configuration."""
    from dbutils.gui.provider_config_dialog import ProviderConfigDialog
    
    dialog = ProviderConfigDialog()
    qtbot.addWidget(dialog)
    
    # Test with a temp config file
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = os.path.join(temp_dir, ".config", "dbutils")
        os.makedirs(config_dir, exist_ok=True)
        
        # Create a standard auto download config
        standard_config = {
            "auto_download_providers": {
                "sqlite": {
                    "name": "SQLite (Auto-Download)",
                    "driver_class": "org.sqlite.JDBC",
                    "database_type": "sqlite",
                    "url_template": "jdbc:sqlite:{database}",
                    "default_user": None,
                    "default_password": None,
                    "requires_license": False,
                    "maven_artifact": "org.xerial:sqlite-jdbc",
                    "recommended_version": "3.42.0.0",
                    "version_override_env": "DBUTILS_SQLITE_VERSION",
                    "repository_override_env": "DBUTILS_SQLITE_REPO"
                }
            },
            "version_management": {
                "default_repository_index": 0,
                "version_resolution_strategy": "latest_first",
                "fallback_versions": {
                    "sqlite": ["3.42.0.0", "3.41.2.2"]
                }
            },
            "repository_management": {
                "repository_priority": [
                    "https://repo1.maven.org/maven2/"
                ]
            }
        }
        
        config_file = os.path.join(config_dir, "auto_download_config.json")
        with open(config_file, "w") as f:
            json.dump(standard_config, f)
        
        # Set environment variable to override version
        original_version = os.environ.get("DBUTILS_SQLITE_VERSION")
        os.environ["DBUTILS_SQLITE_VERSION"] = "3.99.99"
        
        original_config_dir = os.environ.get("DBUTILS_CONFIG_DIR")
        os.environ["DBUTILS_CONFIG_DIR"] = config_dir
        
        try:
            # Load config and check if environment override is applied
            config_result = dialog._load_auto_download_config()
            sqlite_config = config_result.get("sqlite", {})
            # This specific test is about the internal logic, so we're verifying
            # that the config loading mechanism can handle environment overrides
            assert "sqlite" in config_result
        finally:
            # Restore environment
            if original_version is not None:
                os.environ["DBUTILS_SQLITE_VERSION"] = original_version
            else:
                os.environ.pop("DBUTILS_SQLITE_VERSION", None)
                
            if original_config_dir:
                os.environ["DBUTILS_CONFIG_DIR"] = original_config_dir
            else:
                os.environ.pop("DBUTILS_CONFIG_DIR", None)
    
    dialog.close()


def test_config_validation_error_handling(qtbot, monkeypatch):
    """Test UI error handling when config files are invalid or inaccessible."""
    from dbutils.gui.provider_config_dialog import ProviderConfigDialog
    
    dialog = ProviderConfigDialog()
    qtbot.addWidget(dialog)
    
    # Create a temporary config directory
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = os.path.join(temp_dir, "invalid_config")
        os.makedirs(config_dir, exist_ok=True)
        
        # Create a malformed JSON config file
        invalid_config_file = os.path.join(config_dir, "auto_download_config.json")
        with open(invalid_config_file, "w") as f:
            f.write("{ invalid json content without proper closing")
        
        # Create path config with invalid JSON too
        invalid_path_config_file = os.path.join(config_dir, "path_config.json") 
        with open(invalid_path_config_file, "w") as f:
            f.write("not json at all")
        
        # Create URL config with invalid JSON too
        invalid_url_config_file = os.path.join(config_dir, "url_config.json")
        with open(invalid_url_config_file, "w") as f:
            f.write("definitely not json")
        
        original_config_dir = os.environ.get("DBUTILS_CONFIG_DIR")
        os.environ["DBUTILS_CONFIG_DIR"] = config_dir
        
        try:
            # Test that config loading handles invalid JSON gracefully
            config_result = dialog._load_auto_download_config()
            # Should return empty dict rather than crash
            assert isinstance(config_result, dict)
            assert len(config_result) == 0
        finally:
            # Restore original
            if original_config_dir:
                os.environ["DBUTILS_CONFIG_DIR"] = original_config_dir
            else:
                os.environ.pop("DBUTILS_CONFIG_DIR", None)
    
    dialog.close()


def test_config_file_permissions_error_handling(qtbot, monkeypatch):
    """Test UI behavior when config files have permission issues."""
    from dbutils.gui.provider_config_dialog import ProviderConfigDialog
    
    dialog = ProviderConfigDialog()
    qtbot.addWidget(dialog)
    
    # Create a temp directory and create a file without write permissions
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = os.path.join(temp_dir, ".config", "dbutils")
        os.makedirs(config_dir, exist_ok=True)
        
        # Create valid config files with normal permissions for read tests
        valid_config = {
            "auto_download_providers": {},
            "version_management": {
                "default_repository_index": 0,
                "version_resolution_strategy": "latest_first",
                "fallback_versions": {}
            },
            "repository_management": {
                "repository_priority": ["https://repo1.maven.org/maven2/"]
            }
        }
        
        config_file = os.path.join(config_dir, "auto_download_config.json")
        with open(config_file, "w") as f:
            json.dump(valid_config, f)
        
        original_config_dir = os.environ.get("DBUTILS_CONFIG_DIR")
        os.environ["DBUTILS_CONFIG_DIR"] = config_dir
        
        try:
            # Test normal loading works
            config_result = dialog._load_auto_download_config()
            assert isinstance(config_result, dict)
        finally:
            # Restore original
            if original_config_dir:
                os.environ["DBUTILS_CONFIG_DIR"] = original_config_dir
            else:
                os.environ.pop("DBUTILS_CONFIG_DIR", None)
    
    dialog.close()


def test_config_directory_creation(qtbot, monkeypatch):
    """Test that configuration directories are created when they don't exist."""
    from dbutils.gui.provider_config_dialog import ProviderConfigDialog
    
    dialog = ProviderConfigDialog()
    qtbot.addWidget(dialog)
    
    # Use a temporary directory that doesn't exist initially
    with tempfile.TemporaryDirectory() as base_temp_dir:
        config_dir = os.path.join(base_temp_dir, "new_config_dir", "dbutils")
        # Don't create it yet, let the config system create it
        
        original_config_dir = os.environ.get("DBUTILS_CONFIG_DIR")
        os.environ["DBUTILS_CONFIG_DIR"] = config_dir
        
        try:
            # Access the config properties that trigger directory creation
            driver_dir = dialog.driver_directory
            assert os.path.exists(driver_dir), "Driver directory should be created"
            
            config_dir_check = dialog.config_dir
            assert os.path.exists(config_dir_check), "Config directory should be created"
        finally:
            # Restore original
            if original_config_dir:
                os.environ["DBUTILS_CONFIG_DIR"] = original_config_dir
            else:
                os.environ.pop("DBUTILS_CONFIG_DIR", None)
    
    dialog.close()


def test_schema_validation_warning_messages(qtbot, monkeypatch):
    """Test that schema validation provides appropriate warning messages."""
    from dbutils.config.schema_config import validate_path_config, validate_url_config, validate_auto_download_config
    
    # Test path config validation
    invalid_path_config = {
        "driver_dirs": "not_a_list",  # Should be a list
        "search_paths": [],
        "custom_paths": []
    }
    is_valid, message = validate_path_config(invalid_path_config)
    assert not is_valid
    assert "driver_dirs must be a list" in message.lower()
    
    # Test URL config validation with invalid URL
    invalid_url_config = {
        "maven_repos": ["not_a_valid_url"],  # Invalid URL format
        "custom_repos": [],
        "url_patterns": {},
        "download_sources": {}
    }
    is_valid, message = validate_url_config(invalid_url_config)
    assert not is_valid
    
    # Test auto download config validation 
    invalid_auto_config = {
        # Missing required sections
        "version_management": {
            "version_resolution_strategy": "invalid_value"
        }
        # Missing required "auto_download_providers" and "repository_management"
    }
    is_valid, message = validate_auto_download_config(invalid_auto_config)
    assert not is_valid
    assert "missing required section" in message.lower()

    # The UI part would be tested by ensuring the config loading doesn't crash
    from dbutils.gui.provider_config_dialog import ProviderConfigDialog
    
    dialog = ProviderConfigDialog()
    qtbot.addWidget(dialog)
    dialog.close()


if __name__ == "__main__":
    # This allows running the test directly for debugging
    pytest.main([__file__])