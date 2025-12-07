#!/usr/bin/env python3
"""
Centralized test configuration management system.

This module provides a flexible and maintainable way to manage test configurations
with support for multiple sources (files, environment variables, defaults) and
proper error handling.
"""

import json
import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

# Configure logging
logger = logging.getLogger(__name__)

class ConfigSource(Enum):
    """Enumeration of configuration sources in priority order."""
    ENVIRONMENT = 1
    FILE = 2
    DEFAULT = 3

@dataclass
class TestConfig:
    """Data class to hold test configuration."""
    # Database configurations
    databases: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Test environment settings
    test_environment: Dict[str, Any] = field(default_factory=dict)

    # Network and repository settings
    network: Dict[str, Any] = field(default_factory=dict)

    # File paths and directories
    paths: Dict[str, Any] = field(default_factory=dict)

    # Test behavior flags
    behavior: Dict[str, Any] = field(default_factory=dict)

    # Custom configurations
    custom: Dict[str, Any] = field(default_factory=dict)

class TestConfigManager:
    """Centralized test configuration management system."""

    def __init__(self):
        self.config = TestConfig()
        self.config_sources = []
        self.loaded = False

    def load_configuration(self) -> None:
        """Load configuration from all sources in priority order."""
        if self.loaded:
            return

        # Load in priority order: environment -> file -> defaults
        self._load_environment_variables()
        self._load_config_files()
        self._load_defaults()

        self.loaded = True
        logger.info("Test configuration loaded successfully")

    def _load_environment_variables(self) -> None:
        """Load configuration from environment variables."""
        logger.debug("Loading configuration from environment variables")

        # Database configurations from environment
        if 'DBUTILS_TEST_DATABASES' in os.environ:
            try:
                db_config = json.loads(os.environ['DBUTILS_TEST_DATABASES'])
                self.config.databases.update(db_config)
                self.config_sources.append(ConfigSource.ENVIRONMENT)
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid JSON in DBUTILS_TEST_DATABASES: {e}")

        # Test environment settings
        if 'DBUTILS_TEST_ENV' in os.environ:
            try:
                env_config = json.loads(os.environ['DBUTILS_TEST_ENV'])
                self.config.test_environment.update(env_config)
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid JSON in DBUTILS_TEST_ENV: {e}")

        # Network settings
        if 'DBUTILS_TEST_NETWORK' in os.environ:
            try:
                network_config = json.loads(os.environ['DBUTILS_TEST_NETWORK'])
                self.config.network.update(network_config)
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid JSON in DBUTILS_TEST_NETWORK: {e}")

        # Path configurations
        if 'DBUTILS_TEST_PATHS' in os.environ:
            try:
                path_config = json.loads(os.environ['DBUTILS_TEST_PATHS'])
                self.config.paths.update(path_config)
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid JSON in DBUTILS_TEST_PATHS: {e}")

        # Behavior flags
        if 'DBUTILS_TEST_BEHAVIOR' in os.environ:
            try:
                behavior_config = json.loads(os.environ['DBUTILS_TEST_BEHAVIOR'])
                self.config.behavior.update(behavior_config)
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid JSON in DBUTILS_TEST_BEHAVIOR: {e}")

    def _load_config_files(self) -> None:
        """Load configuration from configuration files."""
        logger.debug("Loading configuration from files")

        # Try to find and load test configuration files
        config_files = self._find_config_files()

        for config_file in config_files:
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    file_config = json.load(f)
                    self._merge_file_config(file_config)
                    self.config_sources.append(ConfigSource.FILE)
                    logger.info(f"Loaded configuration from {config_file}")
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load config file {config_file}: {e}")

    def _find_config_files(self) -> List[str]:
        """Find test configuration files in various locations."""
        config_files = []

        # Check current directory
        if os.path.exists('test_config.json'):
            config_files.append('test_config.json')

        # Check tests directory
        tests_config = os.path.join('tests', 'test_config.json')
        if os.path.exists(tests_config):
            config_files.append(tests_config)

        # Check environment variable for custom config path
        if 'DBUTILS_TEST_CONFIG' in os.environ:
            custom_config = os.environ['DBUTILS_TEST_CONFIG']
            if os.path.exists(custom_config):
                config_files.append(custom_config)

        return config_files

    def _merge_file_config(self, file_config: Dict[str, Any]) -> None:
        """Merge file configuration into the current configuration."""
        # Only merge file config if environment variables haven't been loaded for that section
        # This ensures environment variables have highest priority

        if 'databases' in file_config and ConfigSource.ENVIRONMENT not in self.config_sources:
            self.config.databases.update(file_config['databases'])

        if 'test_environment' in file_config and 'DBUTILS_TEST_ENV' not in os.environ:
            self.config.test_environment.update(file_config['test_environment'])

        if 'network' in file_config and 'DBUTILS_TEST_NETWORK' not in os.environ:
            self.config.network.update(file_config['network'])

        if 'paths' in file_config and 'DBUTILS_TEST_PATHS' not in os.environ:
            self.config.paths.update(file_config['paths'])

        if 'behavior' in file_config and 'DBUTILS_TEST_BEHAVIOR' not in os.environ:
            self.config.behavior.update(file_config['behavior'])

        if 'custom' in file_config:
            self.config.custom.update(file_config['custom'])

    def _load_defaults(self) -> None:
        """Load default configuration values."""
        logger.debug("Loading default configuration")

        # Default database configurations
        default_databases = {
            'sqlite': {
                'driver_class': 'org.sqlite.JDBC',
                'jar_path': 'AUTO_DOWNLOAD_sqlite',
                'url_template': 'jdbc:sqlite:{database}',
                'default_user': None,
                'default_password': None,
                'test_db': 'test_sqlite.db'
            },
            'h2': {
                'driver_class': 'org.h2.Driver',
                'jar_path': 'AUTO_DOWNLOAD_h2',
                'url_template': 'jdbc:h2:mem:{database};DB_CLOSE_DELAY=-1',
                'default_user': 'sa',
                'default_password': '',
                'test_db': 'test_h2_db'
            },
            'derby': {
                'driver_class': 'org.apache.derby.jdbc.EmbeddedDriver',
                'jar_path': 'AUTO_DOWNLOAD_derby',
                'url_template': 'jdbc:derby:{database};create=true',
                'default_user': None,
                'default_password': None,
                'test_db': 'test_derby_db'
            }
        }

        # Default test environment settings
        default_env = {
            'debug_mode': False,
            'verbose_logging': False,
            'skip_slow_tests': False,
            'max_test_duration': 300  # 5 minutes
        }

        # Default network settings
        default_network = {
            'maven_repositories': [
                'https://repo1.maven.org/maven2/',
                'https://repo.maven.apache.org/maven2/'
            ],
            'timeout': 30,
            'retry_attempts': 3,
            'retry_delay': 1
        }

        # Default paths
        default_paths = {
            'driver_dir': '~/.config/dbutils/drivers',
            'config_dir': '~/.config/dbutils',
            'test_data_dir': 'tests/test_data',
            'log_dir': 'tests/logs'
        }

        # Default behavior
        default_behavior = {
            'auto_cleanup': True,
            'parallel_tests': False,
            'stop_on_failure': False
        }

        # Apply defaults only if not already set by higher priority sources
        if not self.config_sources or ConfigSource.ENVIRONMENT not in self.config_sources:
            self.config.databases.update({k: v for k, v in default_databases.items()
                                         if k not in self.config.databases})
            self.config.test_environment.update({k: v for k, v in default_env.items()
                                                if k not in self.config.test_environment})
            self.config.network.update({k: v for k, v in default_network.items()
                                      if k not in self.config.network})
            self.config.paths.update({k: v for k, v in default_paths.items()
                                    if k not in self.config.paths})
            self.config.behavior.update({k: v for k, v in default_behavior.items()
                                       if k not in self.config.behavior})

        self.config_sources.append(ConfigSource.DEFAULT)

    def get_database_config(self, db_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific database."""
        return self.config.databases.get(db_name)

    def get_test_environment_setting(self, key: str, default: Any = None) -> Any:
        """Get a test environment setting."""
        return self.config.test_environment.get(key, default)

    def get_network_setting(self, key: str, default: Any = None) -> Any:
        """Get a network setting."""
        return self.config.network.get(key, default)

    def get_path_setting(self, key: str, default: Any = None) -> Any:
        """Get a path setting."""
        path = self.config.paths.get(key, default)
        if path and isinstance(path, str):
            return os.path.expanduser(path)
        return path

    def get_behavior_setting(self, key: str, default: Any = None) -> Any:
        """Get a behavior setting."""
        return self.config.behavior.get(key, default)

    def get_custom_setting(self, key: str, default: Any = None) -> Any:
        """Get a custom setting."""
        return self.config.custom.get(key, default)

    def set_custom_setting(self, key: str, value: Any) -> None:
        """Set a custom configuration setting."""
        self.config.custom[key] = value

    def get_all_config(self) -> Dict[str, Any]:
        """Get the entire configuration as a dictionary."""
        return {
            'databases': self.config.databases,
            'test_environment': self.config.test_environment,
            'network': self.config.network,
            'paths': self.config.paths,
            'behavior': self.config.behavior,
            'custom': self.config.custom,
            'sources': [source.name for source in self.config_sources]
        }

    def save_configuration(self, file_path: Optional[str] = None) -> bool:
        """Save current configuration to a file."""
        if file_path is None:
            file_path = self.get_path_setting('config_dir', 'tests') + '/test_config.json'

        try:
            config_dir = os.path.dirname(file_path)
            os.makedirs(config_dir, exist_ok=True)

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.get_all_config(), f, indent=2)

            logger.info(f"Configuration saved to {file_path}")
            return True
        except IOError as e:
            logger.error(f"Failed to save configuration: {e}")
            return False

    def create_example_config(self, file_path: str = 'test_config.example.json') -> bool:
        """Create an example configuration file."""
        example_config = {
            'databases': {
                'sqlite': {
                    'driver_class': 'org.sqlite.JDBC',
                    'jar_path': 'path/to/sqlite-jdbc.jar',
                    'url_template': 'jdbc:sqlite:{database}',
                    'default_user': None,
                    'default_password': None,
                    'test_db': 'test_database.db'
                },
                'postgresql': {
                    'driver_class': 'org.postgresql.Driver',
                    'jar_path': 'path/to/postgresql-jdbc.jar',
                    'url_template': 'jdbc:postgresql://{host}:{port}/{database}',
                    'default_user': 'testuser',
                    'default_password': 'testpass',
                    'default_host': 'localhost',
                    'default_port': 5432,
                    'test_db': 'test_postgres_db'
                }
            },
            'test_environment': {
                'debug_mode': True,
                'verbose_logging': True,
                'skip_slow_tests': False,
                'max_test_duration': 600
            },
            'network': {
                'maven_repositories': [
                    'https://repo1.maven.org/maven2/',
                    'https://custom.repo.com/maven2/'
                ],
                'timeout': 60,
                'retry_attempts': 5,
                'retry_delay': 2
            },
            'paths': {
                'driver_dir': '~/.config/dbutils/drivers',
                'config_dir': '~/.config/dbutils',
                'test_data_dir': 'tests/test_data',
                'log_dir': 'tests/logs'
            },
            'behavior': {
                'auto_cleanup': True,
                'parallel_tests': False,
                'stop_on_failure': True
            }
        }

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(example_config, f, indent=2)

            logger.info(f"Example configuration created at {file_path}")
            return True
        except IOError as e:
            logger.error(f"Failed to create example configuration: {e}")
            return False

# Global test configuration manager instance
_test_config_manager = TestConfigManager()

def get_test_config_manager() -> TestConfigManager:
    """Get the global test configuration manager instance."""
    if not _test_config_manager.loaded:
        _test_config_manager.load_configuration()
    return _test_config_manager

def reload_test_config() -> None:
    """Reload test configuration from all sources."""
    global _test_config_manager
    _test_config_manager = TestConfigManager()
    _test_config_manager.load_configuration()

if __name__ == "__main__":
    # Create example configuration when run directly
    config_manager = get_test_config_manager()
    config_manager.create_example_config()
    print("Example test configuration created.")
