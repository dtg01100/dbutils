#!/usr/bin/env python3
"""
Test suite for the centralized test configuration system.

This test suite validates:
1. Configuration loading from multiple sources
2. Environment variable support
3. Backward compatibility with existing test infrastructure
4. Configuration management functionality
"""

import os
import json
import tempfile
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from test_config_manager import TestConfigManager, get_test_config_manager, reload_test_config

class TestConfigManagerInitialization:
    """Test initialization and basic functionality of the config manager."""

    def test_config_manager_creation(self):
        """Test that config manager can be created."""
        config_manager = TestConfigManager()
        assert config_manager is not None
        assert config_manager.config is not None
        assert not config_manager.loaded

    def test_config_manager_singleton(self):
        """Test that get_test_config_manager returns a working instance."""
        config_manager = get_test_config_manager()
        assert config_manager is not None
        assert config_manager.loaded

    def test_config_manager_reload(self):
        """Test that config manager can be reloaded."""
        # Get initial instance
        config_manager1 = get_test_config_manager()
        original_config = config_manager1.get_all_config()

        # Reload configuration
        reload_test_config()
        config_manager2 = get_test_config_manager()

        # Should have same structure but potentially different data
        new_config = config_manager2.get_all_config()
        assert 'databases' in new_config
        assert 'network' in new_config

class TestConfigurationLoading:
    """Test configuration loading from different sources."""

    def test_default_configuration_loading(self, tmp_path):
        """Test loading of default configuration."""
        # Clear any environment variables that might affect loading
        with patch.dict(os.environ, {}, clear=False):
            config_manager = TestConfigManager()
            config_manager.load_configuration()

            # Should have default values
            assert 'sqlite' in config_manager.config.databases
            assert 'h2' in config_manager.config.databases
            assert 'derby' in config_manager.config.databases

            # Check default network settings
            network_settings = config_manager.config.network
            assert 'maven_repositories' in network_settings
            assert len(network_settings['maven_repositories']) > 0

    def test_file_configuration_loading(self, tmp_path):
        """Test loading configuration from file."""
        # Create a test config file
        test_config = {
            "databases": {
                "test_db": {
                    "driver_class": "org.test.Driver",
                    "jar_path": "/test/path.jar",
                    "url_template": "jdbc:test://{host}",
                    "test_db": "test_database.db"
                }
            },
            "network": {
                "maven_repositories": ["https://test.repo.com/maven2/"],
                "timeout": 60
            }
        }

        config_file = tmp_path / "test_config.json"
        with open(config_file, 'w') as f:
            json.dump(test_config, f)

        # Set environment to use this config file
        with patch.dict(os.environ, {'DBUTILS_TEST_CONFIG': str(config_file)}):
            config_manager = TestConfigManager()
            config_manager.load_configuration()

            # Should have loaded from file
            assert 'test_db' in config_manager.config.databases
            assert config_manager.config.databases['test_db']['driver_class'] == "org.test.Driver"

            # Should have network settings from file
            assert config_manager.config.network['timeout'] == 60

    def test_environment_variable_loading(self, tmp_path):
        """Test loading configuration from environment variables."""
        # Set environment variables
        env_config = {
            "DBUTILS_TEST_DATABASES": json.dumps({
                "env_db": {
                    "driver_class": "org.env.Driver",
                    "jar_path": "/env/path.jar",
                    "url_template": "jdbc:env://{host}",
                    "test_db": "env_database.db"
                }
            }),
            "DBUTILS_TEST_NETWORK": json.dumps({
                "timeout": 120,
                "retry_attempts": 5
            })
        }

        with patch.dict(os.environ, env_config):
            config_manager = TestConfigManager()
            config_manager.load_configuration()

            # Should have loaded from environment
            assert 'env_db' in config_manager.config.databases
            assert config_manager.config.databases['env_db']['driver_class'] == "org.env.Driver"

            # Should have network settings from environment
            assert config_manager.config.network['timeout'] == 120
            assert config_manager.config.network['retry_attempts'] == 5

    def test_configuration_priority(self, tmp_path):
        """Test that configuration sources are prioritized correctly."""
        # Create config file
        file_config = {
            "databases": {
                "priority_test": {
                    "driver_class": "org.file.Driver",
                    "test_source": "file"
                }
            },
            "network": {
                "timeout": 30,
                "source": "file"
            }
        }

        config_file = tmp_path / "priority_config.json"
        with open(config_file, 'w') as f:
            json.dump(file_config, f)

        # Set environment variables (higher priority than file)
        env_config = {
            "DBUTILS_TEST_CONFIG": str(config_file),
            "DBUTILS_TEST_DATABASES": json.dumps({
                "priority_test": {
                    "driver_class": "org.env.Driver",
                    "test_source": "env"
                }
            }),
            "DBUTILS_TEST_NETWORK": json.dumps({
                "timeout": 60,
                "source": "env"
            })
        }

        with patch.dict(os.environ, env_config):
            config_manager = TestConfigManager()
            config_manager.load_configuration()

            # Environment should override file
            assert config_manager.config.databases['priority_test']['driver_class'] == "org.env.Driver"
            assert config_manager.config.databases['priority_test']['test_source'] == "env"
            assert config_manager.config.network['timeout'] == 60
            assert config_manager.config.network['source'] == "env"

class TestConfigurationAccess:
    """Test accessing configuration values."""

    def test_database_config_access(self):
        """Test accessing database configurations."""
        config_manager = get_test_config_manager()

        # Test getting existing database config
        sqlite_config = config_manager.get_database_config('sqlite')
        assert sqlite_config is not None
        assert 'driver_class' in sqlite_config

        # Test getting non-existent database config
        unknown_config = config_manager.get_database_config('unknown_db')
        assert unknown_config is None

    def test_network_config_access(self):
        """Test accessing network configurations."""
        config_manager = get_test_config_manager()

        # Test getting network settings
        timeout = config_manager.get_network_setting('timeout')
        assert timeout is not None
        assert isinstance(timeout, int)

        # Test getting non-existent setting with default
        unknown_setting = config_manager.get_network_setting('unknown', 999)
        assert unknown_setting == 999

    def test_path_config_access(self):
        """Test accessing path configurations."""
        config_manager = get_test_config_manager()

        # Test getting path settings
        driver_dir = config_manager.get_path_setting('driver_dir')
        assert driver_dir is not None
        assert isinstance(driver_dir, str)

        # Test path expansion
        assert '~' not in driver_dir  # Should be expanded

    def test_behavior_config_access(self):
        """Test accessing behavior configurations."""
        config_manager = get_test_config_manager()

        # Test getting behavior settings
        auto_cleanup = config_manager.get_behavior_setting('auto_cleanup')
        assert auto_cleanup is not None
        assert isinstance(auto_cleanup, bool)

class TestConfigurationPersistence:
    """Test saving and loading configuration."""

    def test_configuration_saving(self, tmp_path):
        """Test saving configuration to file."""
        config_manager = TestConfigManager()
        config_manager.load_configuration()

        # Add some custom data
        config_manager.set_custom_setting('test_key', 'test_value')

        # Save to file
        save_path = tmp_path / "saved_config.json"
        result = config_manager.save_configuration(str(save_path))

        assert result is True
        assert save_path.exists()

        # Verify saved content
        with open(save_path, 'r') as f:
            saved_config = json.load(f)

        assert 'custom' in saved_config
        assert saved_config['custom']['test_key'] == 'test_value'

    def test_example_config_creation(self, tmp_path):
        """Test creating example configuration file."""
        config_manager = TestConfigManager()

        example_path = tmp_path / "example_config.json"
        result = config_manager.create_example_config(str(example_path))

        assert result is True
        assert example_path.exists()

        # Verify example content
        with open(example_path, 'r') as f:
            example_config = json.load(f)

        assert 'databases' in example_config
        assert 'network' in example_config
        assert 'paths' in example_config
        assert 'behavior' in example_config

class TestBackwardCompatibility:
    """Test backward compatibility with existing test infrastructure."""

    def test_existing_database_configs_still_work(self):
        """Test that existing database configurations still work."""
        # Import the updated database_test_utils
        from tests.database_test_utils import get_database_configs

        # Get the database configs using the function
        DATABASE_CONFIGS = get_database_configs()

        # Should still have the expected databases
        assert 'sqlite' in DATABASE_CONFIGS
        assert 'h2' in DATABASE_CONFIGS
        assert 'derby' in DATABASE_CONFIGS

        # Check that configs have expected structure
        sqlite_config = DATABASE_CONFIGS['sqlite']
        assert 'driver_class' in sqlite_config
        assert 'jar_path' in sqlite_config
        assert 'url_template' in sqlite_config

    def test_existing_fixtures_still_work(self, test_config):
        """Test that existing test fixtures still work with new config system."""
        # Test that we can get database config through fixture
        sqlite_config = test_config.get_database_config('sqlite')
        assert sqlite_config is not None

        # Test network config
        maven_repos = test_config.get_network_setting('maven_repositories')
        assert maven_repos is not None
        assert isinstance(maven_repos, list)

    def test_environment_variable_fallback(self, tmp_path):
        """Test that environment variables can override config file settings."""
        # Create a config file
        file_config = {
            "databases": {
                "sqlite": {
                    "driver_class": "org.sqlite.JDBC",
                    "jar_path": "file_path.jar"
                }
            }
        }

        config_file = tmp_path / "test_config.json"
        with open(config_file, 'w') as f:
            json.dump(file_config, f)

        # Set environment variable to override
        env_config = {
            "DBUTILS_TEST_CONFIG": str(config_file),
            "DBUTILS_TEST_DATABASES": json.dumps({
                "sqlite": {
                    "driver_class": "org.sqlite.JDBC",
                    "jar_path": "env_path.jar"
                }
            })
        }

        with patch.dict(os.environ, env_config):
            config_manager = TestConfigManager()
            config_manager.load_configuration()

            # Environment should override file
            sqlite_config = config_manager.get_database_config('sqlite')
            assert sqlite_config['jar_path'] == "env_path.jar"

class TestErrorHandling:
    """Test error handling in configuration system."""

    def test_corrupted_config_file_handling(self, tmp_path):
        """Test handling of corrupted configuration files."""
        # Create corrupted config file
        config_file = tmp_path / "corrupted_config.json"
        config_file.write_text("not valid json content")

        with patch.dict(os.environ, {'DBUTILS_TEST_CONFIG': str(config_file)}):
            config_manager = TestConfigManager()
            config_manager.load_configuration()

            # Should fall back to defaults
            assert 'sqlite' in config_manager.config.databases

    def test_missing_config_file_handling(self, tmp_path):
        """Test handling when config file doesn't exist."""
        # Set environment to point to non-existent file
        with patch.dict(os.environ, {'DBUTILS_TEST_CONFIG': '/non/existent/file.json'}):
            config_manager = TestConfigManager()
            config_manager.load_configuration()

            # Should fall back to defaults
            assert 'sqlite' in config_manager.config.databases

    def test_invalid_json_in_environment(self, tmp_path):
        """Test handling of invalid JSON in environment variables."""
        # Set invalid JSON in environment
        with patch.dict(os.environ, {'DBUTILS_TEST_DATABASES': 'invalid json content'}):
            config_manager = TestConfigManager()
            config_manager.load_configuration()

            # Should fall back to defaults
            assert 'sqlite' in config_manager.config.databases

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])