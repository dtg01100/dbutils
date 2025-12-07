"""
Path Configuration Module - Dynamic path resolution and management.

This module provides a comprehensive system for discovering and managing
JAR file paths, driver directories, and other file system locations.
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

# Configure logging
logger = logging.getLogger(__name__)

class PathConfig:
    """Manages dynamic path resolution and discovery for JDBC drivers and related files."""

    def __init__(self):
        self._config = self._load_config()

    def _load_config(self) -> Dict:
        """Load path configuration from environment variables and config files."""
        config = {
            'driver_dirs': [],
            'search_paths': [],
            'custom_paths': []
        }

        # Load from environment variables
        self._load_from_environment(config)

        # Load from configuration file
        self._load_from_config_file(config)

        return config

    def _load_from_environment(self, config: Dict) -> None:
        """Load path configuration from environment variables."""
        # Primary driver directory
        driver_dir = os.environ.get("DBUTILS_DRIVER_DIR")
        if driver_dir:
            config['driver_dirs'].append(driver_dir)

        # Additional search paths
        search_paths = os.environ.get("DBUTILS_JAR_SEARCH_PATHS")
        if search_paths:
            for path in search_paths.split(':'):
                if path.strip():
                    config['search_paths'].append(path.strip())

        # Custom paths
        custom_paths = os.environ.get("DBUTILS_CUSTOM_JAR_PATHS")
        if custom_paths:
            try:
                parsed_paths = json.loads(custom_paths)
                if isinstance(parsed_paths, list):
                    config['custom_paths'].extend(parsed_paths)
            except json.JSONDecodeError:
                # Fallback to comma-separated
                config['custom_paths'].extend([p.strip() for p in custom_paths.split(',') if p.strip()])

    def _load_from_config_file(self, config: Dict) -> None:
        """Load path configuration from JSON config file."""
        config_file = self._get_config_file_path()
        if not config_file or not os.path.exists(config_file):
            return

        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                file_config = json.load(f)

                if 'driver_dirs' in file_config and isinstance(file_config['driver_dirs'], list):
                    config['driver_dirs'].extend(file_config['driver_dirs'])

                if 'search_paths' in file_config and isinstance(file_config['search_paths'], list):
                    config['search_paths'].extend(file_config['search_paths'])

                if 'custom_paths' in file_config and isinstance(file_config['custom_paths'], list):
                    config['custom_paths'].extend(file_config['custom_paths'])

        except Exception as e:
            logger.warning(f"Error loading path config from {config_file}: {e}")

    def _get_config_file_path(self) -> Optional[str]:
        """Get the path to the path configuration file."""
        config_dir = os.environ.get('DBUTILS_CONFIG_DIR', os.path.expanduser('~/.config/dbutils'))
        os.makedirs(config_dir, exist_ok=True)
        return os.path.join(config_dir, 'path_config.json')

    def get_driver_directory(self) -> str:
        """Get the primary directory where JDBC drivers should be stored.

        Returns:
            Path to the primary driver directory
        """
        # Use first configured driver directory, or default
        if self._config['driver_dirs']:
            driver_dir = self._config['driver_dirs'][0]
        else:
            driver_dir = os.path.expanduser("~/.config/dbutils/drivers")

        # Ensure directory exists
        os.makedirs(driver_dir, exist_ok=True)
        return driver_dir

    def get_all_search_paths(self) -> List[str]:
        """Get all configured search paths for JAR discovery.

        Returns:
            List of all search paths including driver directories, search paths, and custom paths
        """
        paths = []

        # Refresh from environment in case tests or runtime changed them dynamically
        env_driver_dir = os.environ.get('DBUTILS_DRIVER_DIR')
        if env_driver_dir and env_driver_dir not in self._config['driver_dirs']:
            # Prepend environment driver dir to give it priority
            paths.append(env_driver_dir)

        # Add driver directories from loaded config
        if self._config['driver_dirs']:
            paths.extend(self._config['driver_dirs'])

        # Add search paths
        if self._config['search_paths']:
            paths.extend(self._config['search_paths'])
        # Also include environment search paths if set (colon-delimited)
        env_search_paths = os.environ.get('DBUTILS_JAR_SEARCH_PATHS')
        if env_search_paths:
            for p in env_search_paths.split(':'):
                p = p.strip()
                if p and p not in paths:
                    paths.append(p)

        # Add custom paths
        if self._config['custom_paths']:
            paths.extend(self._config['custom_paths'])
        # Also include environment custom paths as JSON or comma separated list
        env_custom_paths = os.environ.get('DBUTILS_CUSTOM_JAR_PATHS')
        if env_custom_paths:
            try:
                parsed = json.loads(env_custom_paths)
                if isinstance(parsed, list):
                    for p in parsed:
                        if p not in paths:
                            paths.append(p)
            except Exception:
                for p in env_custom_paths.split(','):
                    p = p.strip()
                    if p and p not in paths:
                        paths.append(p)

        # Add standard default locations
        default_paths = [
            os.path.expanduser("~/.config/dbutils/drivers"),
            os.path.expanduser("~/dbutils/drivers"),
            os.path.expanduser("~/drivers"),
            os.path.expanduser("~/.m2/repository"),
            "/usr/share/java",
            "/usr/local/share/java"
        ]

        # Add defaults that aren't already in the list
        for default_path in default_paths:
            if default_path not in paths:
                paths.append(default_path)

        return [str(Path(p).expanduser().resolve()) for p in paths]

    def find_jar_files(self, pattern: str = "*.jar") -> List[str]:
        """Find JAR files matching a pattern across all search paths.

        Args:
            pattern: File pattern to match (default: "*.jar")

        Returns:
            List of paths to matching JAR files
        """
        found_files = []

        for search_path in self.get_all_search_paths():
            if not os.path.exists(search_path):
                continue

            try:
                for file_path in Path(search_path).rglob(pattern):
                    if file_path.is_file():
                        found_files.append(str(file_path))
            except Exception as e:
                logger.debug(f"Error searching {search_path}: {e}")
                continue

        return found_files

    def find_driver_jar(self, database_type: str) -> List[str]:
        """Find JAR files that likely contain drivers for a specific database type.

        Args:
            database_type: Type of database (e.g., 'postgresql', 'mysql')

        Returns:
            List of paths to JAR files that likely contain the driver
        """
        if not database_type:
            return []

        found_files = []
        search_patterns = self._get_search_patterns(database_type)

        for search_path in self.get_all_search_paths():
            if not os.path.exists(search_path):
                continue

            try:
                for file_path in Path(search_path).rglob("*.jar"):
                    if file_path.is_file():
                        filename_lower = file_path.name.lower()
                        if any(pattern.lower() in filename_lower for pattern in search_patterns):
                            found_files.append(str(file_path))
            except Exception as e:
                logger.debug(f"Error searching {search_path} for {database_type}: {e}")
                continue

        return found_files

    def _get_search_patterns(self, database_type: str) -> List[str]:
        """Get search patterns for a specific database type."""
        db_type = database_type.lower()
        patterns = [db_type, "jdbc"]

        # Add common variations and aliases
        if db_type == "postgresql":
            patterns.extend(["postgres", "pg"])
        elif db_type == "sqlserver":
            patterns.extend(["mssql", "sqlserver", "microsoft"])
        elif db_type == "mariadb":
            patterns.extend(["maria", "mariadb"])
        elif db_type == "oracle":
            patterns.extend(["ojdbc", "oracle"])
        elif db_type == "db2":
            patterns.extend(["db2", "ibm"])
        elif db_type == "jt400":
            patterns.extend(["jt400", "jtopen", "ibm", "as400"])

        return patterns

    def validate_path(self, path: str) -> bool:
        """Validate that a path exists and is accessible.

        Args:
            path: Path to validate

        Returns:
            True if path exists and is accessible, False otherwise
        """
        try:
            return os.path.exists(path) and os.access(path, os.R_OK)
        except Exception:
            return False

    def get_best_driver_path(self, database_type: str) -> Optional[str]:
        """Get the most likely JAR file path for a specific database type.

        Args:
            database_type: Type of database

        Returns:
            Path to the most likely JAR file, or None if not found
        """
        candidates = self.find_driver_jar(database_type)

        if not candidates:
            return None

        # Simple heuristic: prefer files with version numbers, then alphabetical
        candidates.sort(key=lambda x: (
            "latest" not in x.lower(),
            os.path.getsize(x),
            x.lower()
        ), reverse=True)

        return candidates[0] if candidates else None

    def add_custom_path(self, path: str) -> bool:
        """Add a custom path to the configuration.

        Args:
            path: Path to add

        Returns:
            True if path was added successfully, False otherwise
        """
        if not path or not isinstance(path, str):
            return False

        expanded_path = str(Path(path).expanduser().resolve())

        if expanded_path in self._config['custom_paths']:
            return True

        self._config['custom_paths'].append(expanded_path)
        return self._save_config()

    def _save_config(self) -> bool:
        """Save the current configuration to file.

        Returns:
            True if save was successful, False otherwise
        """
        config_file = self._get_config_file_path()
        if not config_file:
            return False

        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'driver_dirs': self._config['driver_dirs'],
                    'search_paths': self._config['search_paths'],
                    'custom_paths': self._config['custom_paths']
                }, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving path config to {config_file}: {e}")
            return False

# Global instance for convenience
path_config = PathConfig()

def get_driver_directory() -> str:
    """Get the primary driver directory."""
    return path_config.get_driver_directory()

def find_jar_files(pattern: str = "*.jar") -> List[str]:
    """Find JAR files matching a pattern."""
    return path_config.find_jar_files(pattern)

def find_driver_jar(database_type: str) -> List[str]:
    """Find JAR files for a specific database type."""
    return path_config.find_driver_jar(database_type)

def get_best_driver_path(database_type: str) -> Optional[str]:
    """Get the best driver path for a specific database type."""
    return path_config.get_best_driver_path(database_type)

def add_custom_path(path: str) -> bool:
    """Add a custom path to search for JAR files."""
    return path_config.add_custom_path(path)
