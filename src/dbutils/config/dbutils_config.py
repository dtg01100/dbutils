"""
DBUtils Configuration Module - Unified configuration management.

This module provides a comprehensive configuration system that combines
path management, URL configuration, and other settings with environment
variable support and configuration file management.
"""

import json
import os
from typing import List, Optional, Tuple

from .path_config import PathConfig, find_driver_jar, get_best_driver_path, get_driver_directory
from .url_config import URLConfig, construct_maven_artifact_url, construct_metadata_url, get_maven_repositories


class DBUtilsConfig:
    """Unified configuration manager for DBUtils."""

    def __init__(self):
        self.path_config = PathConfig()
        self.url_config = URLConfig()

    def get_driver_directory(self) -> str:
        """Get the primary directory where JDBC drivers should be stored."""
        return self.path_config.get_driver_directory()

    def find_driver_jar(self, database_type: str) -> List[str]:
        """Find JAR files that likely contain drivers for a specific database type."""
        return self.path_config.find_driver_jar(database_type)

    def get_best_driver_path(self, database_type: str) -> Optional[str]:
        """Get the most likely JAR file path for a specific database type."""
        return self.path_config.get_best_driver_path(database_type)

    def get_maven_repositories(self) -> List[str]:
        """Get all configured Maven repository URLs."""
        return self.url_config.get_maven_repositories()

    def construct_maven_artifact_url(
        self, group_id: str, artifact_id: str, version: str, repo_index: int = 0, packaging: str = "jar"
    ) -> Optional[str]:
        """Construct a Maven artifact URL from coordinates."""
        return self.url_config.construct_maven_artifact_url(group_id, artifact_id, version, repo_index, packaging)

    def construct_metadata_url(self, group_id: str, artifact_id: str, repo_index: int = 0) -> Optional[str]:
        """Construct a Maven metadata URL for version discovery."""
        return self.url_config.construct_metadata_url(group_id, artifact_id, repo_index)

    def add_maven_repository(self, url: str) -> bool:
        """Add a Maven repository URL to the configuration."""
        return self.url_config.add_maven_repository(url)

    def add_custom_repository(self, url: str) -> bool:
        """Add a custom repository URL (higher priority than Maven repos)."""
        return self.url_config.add_custom_repository(url)

    def add_search_path(self, path: str) -> bool:
        """Add a custom path to search for JAR files."""
        return self.path_config.add_custom_path(path)

    def get_all_search_paths(self) -> List[str]:
        """Get all configured search paths for JAR discovery."""
        return self.path_config.get_all_search_paths()

    def validate_url(self, url: str) -> Tuple[bool, str]:
        """Validate a URL format and basic connectivity."""
        return self.url_config.validate_url(url)

    def validate_path(self, path: str) -> bool:
        """Validate that a path exists and is accessible."""
        return self.path_config.validate_path(path)

    def save_configuration(self) -> bool:
        """Save the current configuration to files."""
        path_success = self.path_config._save_config()
        url_success = self.url_config._save_config()
        return path_success and url_success

    def load_configuration(self) -> None:
        """Reload configuration from files and environment."""
        self.path_config = PathConfig()
        self.url_config = URLConfig()


# Global instance for convenience
config = DBUtilsConfig()


def get_driver_directory() -> str:
    """Get the primary driver directory."""
    # Respect explicit environment override at call time for dynamic testability and flexibility
    env_dir = os.environ.get("DBUTILS_DRIVER_DIR")
    if env_dir:
        os.makedirs(env_dir, exist_ok=True)
        return env_dir
    return config.get_driver_directory()


def find_driver_jar(database_type: str) -> List[str]:
    """Find JAR files for a specific database type."""
    return config.find_driver_jar(database_type)


def get_best_driver_path(database_type: str) -> Optional[str]:
    """Get the best driver path for a specific database type."""
    return config.get_best_driver_path(database_type)


def get_maven_repositories() -> List[str]:
    """Get all configured Maven repository URLs."""
    # Allow overriding via environment variable for tests and runtime configuration
    env_repos = os.environ.get("DBUTILS_MAVEN_REPOS")
    if env_repos:
        try:
            # Try JSON array first
            parsed = json.loads(env_repos)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            # Fallback to comma-separated list
            return [r.strip() for r in env_repos.split(",") if r.strip()]
    return config.get_maven_repositories()


def construct_maven_artifact_url(
    group_id: str, artifact_id: str, version: str, repo_index: int = 0, packaging: str = "jar"
) -> Optional[str]:
    """Construct a Maven artifact URL from coordinates."""
    return config.construct_maven_artifact_url(group_id, artifact_id, version, repo_index, packaging)


def construct_metadata_url(group_id: str, artifact_id: str, repo_index: int = 0) -> Optional[str]:
    """Construct a Maven metadata URL."""
    return config.construct_metadata_url(group_id, artifact_id, repo_index)


def add_maven_repository(url: str) -> bool:
    """Add a Maven repository URL."""
    return config.add_maven_repository(url)


def add_custom_repository(url: str) -> bool:
    """Add a custom repository URL."""
    return config.add_custom_repository(url)


def add_search_path(path: str) -> bool:
    """Add a custom path to search for JAR files."""
    return config.add_search_path(path)


def get_all_search_paths() -> List[str]:
    """Get all configured search paths for JAR discovery."""
    return config.get_all_search_paths()


def validate_url(url: str) -> Tuple[bool, str]:
    """Validate a URL format and basic connectivity."""
    return config.validate_url(url)


def validate_path(path: str) -> bool:
    """Validate that a path exists and is accessible."""
    return config.validate_path(path)


def save_configuration() -> bool:
    """Save the current configuration to files."""
    return config.save_configuration()


def load_configuration() -> None:
    """Reload configuration from files and environment."""
    config.load_configuration()
