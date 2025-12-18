"""
URL Configuration Module - Dynamic URL pattern management.

This module provides configurable URL patterns for Maven repositories,
download URLs, and other web resources with environment variable support.
"""

import json
import logging
import os
import urllib.parse
from typing import Dict, List, Optional, Tuple

from .schema_config import validate_url_config

# Configure logging
logger = logging.getLogger(__name__)


class URLConfig:
    """Manages dynamic URL configuration for Maven repositories and download sources."""

    def __init__(self):
        self._config = self._load_config()

    def _load_config(self) -> Dict:
        """Load URL configuration from environment variables and config files."""
        config = {"maven_repos": [], "custom_repos": [], "url_patterns": {}, "download_sources": {}}

        # Load from environment variables
        self._load_from_environment(config)

        # Load from configuration file
        self._load_from_config_file(config)

        # Add defaults if not configured
        self._add_defaults(config)

        return config

    def _load_from_environment(self, config: Dict) -> None:
        """Load URL configuration from environment variables."""
        # Maven repositories from environment
        maven_repos = os.environ.get("DBUTILS_MAVEN_REPOS")
        if maven_repos:
            try:
                parsed_repos = json.loads(maven_repos)
                if isinstance(parsed_repos, list):
                    config["maven_repos"].extend(parsed_repos)
            except json.JSONDecodeError:
                # Fallback to comma-separated
                config["maven_repos"].extend([r.strip() for r in maven_repos.split(",") if r.strip()])

        # Custom repositories
        custom_repos = os.environ.get("DBUTILS_CUSTOM_REPOS")
        if custom_repos:
            try:
                parsed_repos = json.loads(custom_repos)
                if isinstance(parsed_repos, list):
                    config["custom_repos"].extend(parsed_repos)
            except json.JSONDecodeError:
                config["custom_repos"].extend([r.strip() for r in custom_repos.split(",") if r.strip()])

    def _load_from_config_file(self, config: Dict) -> None:
        """Load URL configuration from JSON config file."""
        config_file = self._get_config_file_path()
        if not config_file or not os.path.exists(config_file):
            return

        try:
            # First validate the configuration file
            is_valid, validation_msg = validate_url_config(config_file)
            if not is_valid:
                logger.error(f"URL configuration validation failed: {validation_msg}")
                # Only warn and continue, don't fail completely to maintain backward compatibility
                logger.warning(f"Loading config from {config_file} without validation")

            with open(config_file, "r", encoding="utf-8") as f:
                file_config = json.load(f)

                # Additional in-code validation to ensure required fields are present
                required_keys = ["maven_repos", "custom_repos", "url_patterns", "download_sources"]
                for key in required_keys:
                    if key not in file_config:
                        logger.warning(f"Missing required key '{key}' in {config_file}, using defaults")
                        if key in ["maven_repos", "custom_repos"]:
                            file_config[key] = []
                        elif key in ["url_patterns", "download_sources"]:
                            file_config[key] = {}

                if "maven_repos" in file_config and isinstance(file_config["maven_repos"], list):
                    config["maven_repos"].extend(file_config["maven_repos"])

                if "custom_repos" in file_config and isinstance(file_config["custom_repos"], list):
                    config["custom_repos"].extend(file_config["custom_repos"])

                if "url_patterns" in file_config and isinstance(file_config["url_patterns"], dict):
                    config["url_patterns"].update(file_config["url_patterns"])

                if "download_sources" in file_config and isinstance(file_config["download_sources"], dict):
                    config["download_sources"].update(file_config["download_sources"])

        except Exception as e:
            logger.warning(f"Error loading URL config from {config_file}: {e}")

    def _add_defaults(self, config: Dict) -> None:
        """Add default Maven repositories if none are configured."""
        default_repos = [
            "https://repo1.maven.org/maven2/",
            "https://repo.maven.apache.org/maven2/",
            "https://maven.aliyun.com/repository/central/",
            "https://maven.google.com/",
        ]

        # Add defaults that aren't already in the list
        for repo in default_repos:
            if repo not in config["maven_repos"]:
                config["maven_repos"].append(repo)

    def _get_config_file_path(self) -> Optional[str]:
        """Get the path to the URL configuration file."""
        config_dir = os.environ.get("DBUTILS_CONFIG_DIR", os.path.expanduser("~/.config/dbutils"))
        os.makedirs(config_dir, exist_ok=True)
        return os.path.join(config_dir, "url_config.json")

    def get_maven_repositories(self) -> List[str]:
        """Get all configured Maven repository URLs.

        Returns:
            List of Maven repository URLs in priority order
        """
        repos = []

        # Add custom repos first (highest priority)
        repos.extend(self._config["custom_repos"])

        # Add configured Maven repos
        repos.extend(self._config["maven_repos"])

        # Remove duplicates while preserving order
        seen = set()
        unique_repos = []
        for repo in repos:
            if repo not in seen:
                seen.add(repo)
                unique_repos.append(repo)

        return unique_repos

    def get_repository_url(self, repo_index: int = 0) -> Optional[str]:
        """Get a specific Maven repository URL by index.

        Args:
            repo_index: Index of repository to get (default: 0)

        Returns:
            Repository URL or None if index is out of range
        """
        repos = self.get_maven_repositories()
        if 0 <= repo_index < len(repos):
            return repos[repo_index]
        return None

    def add_maven_repository(self, url: str) -> bool:
        """Add a Maven repository URL to the configuration.

        Args:
            url: Repository URL to add

        Returns:
            True if repository was added successfully, False otherwise
        """
        if not url or not isinstance(url, str):
            return False

        # Basic URL validation
        if not (url.startswith("http://") or url.startswith("https://")):
            return False

        normalized_url = url.rstrip("/")

        if normalized_url in self._config["maven_repos"]:
            return True

        self._config["maven_repos"].append(normalized_url)
        return self._save_config()

    def add_custom_repository(self, url: str) -> bool:
        """Add a custom repository URL (higher priority than Maven repos).

        Args:
            url: Repository URL to add

        Returns:
            True if repository was added successfully, False otherwise
        """
        if not url or not isinstance(url, str):
            return False

        # Basic URL validation
        if not (url.startswith("http://") or url.startswith("https://")):
            return False

        normalized_url = url.rstrip("/")

        if normalized_url in self._config["custom_repos"]:
            return True

        self._config["custom_repos"].append(normalized_url)
        return self._save_config()

    def get_url_pattern(self, pattern_name: str) -> Optional[str]:
        """Get a configured URL pattern by name.

        Args:
            pattern_name: Name of the URL pattern

        Returns:
            URL pattern string or None if not found
        """
        return self._config["url_patterns"].get(pattern_name)

    def set_url_pattern(self, pattern_name: str, pattern: str) -> bool:
        """Set a URL pattern in the configuration.

        Args:
            pattern_name: Name of the URL pattern
            pattern: URL pattern string

        Returns:
            True if pattern was set successfully, False otherwise
        """
        if not pattern_name or not pattern:
            return False

        self._config["url_patterns"][pattern_name] = pattern
        return self._save_config()

    def get_download_source(self, source_name: str) -> Optional[Dict]:
        """Get a configured download source by name.

        Args:
            source_name: Name of the download source

        Returns:
            Download source configuration dict or None if not found
        """
        return self._config["download_sources"].get(source_name)

    def set_download_source(self, source_name: str, source_config: Dict) -> bool:
        """Set a download source configuration.

        Args:
            source_name: Name of the download source
            source_config: Configuration dictionary

        Returns:
            True if source was set successfully, False otherwise
        """
        if not source_name or not source_config:
            return False

        self._config["download_sources"][source_name] = source_config
        return self._save_config()

    def construct_maven_artifact_url(
        self, group_id: str, artifact_id: str, version: str, repo_index: int = 0, packaging: str = "jar"
    ) -> Optional[str]:
        """Construct a Maven artifact URL from coordinates.

        Args:
            group_id: Maven group ID
            artifact_id: Maven artifact ID
            version: Artifact version
            repo_index: Index of repository to use
            packaging: Packaging type (default: "jar")

        Returns:
            Constructed Maven artifact URL or None if construction failed
        """
        repo_url = self.get_repository_url(repo_index)
        if not repo_url:
            return None

        # Normalize group ID (replace dots with slashes)
        group_path = group_id.replace(".", "/")

        # Construct the artifact URL
        filename = f"{artifact_id}-{version}.{packaging}"
        artifact_url = f"{repo_url.rstrip('/')}/{group_path}/{artifact_id}/{version}/{filename}"

        return artifact_url

    def construct_metadata_url(self, group_id: str, artifact_id: str, repo_index: int = 0) -> Optional[str]:
        """Construct a Maven metadata URL for version discovery.

        Args:
            group_id: Maven group ID
            artifact_id: Maven artifact ID
            repo_index: Index of repository to use

        Returns:
            Constructed Maven metadata URL or None if construction failed
        """
        repo_url = self.get_repository_url(repo_index)
        if not repo_url:
            return None

        # Normalize group ID (replace dots with slashes)
        group_path = group_id.replace(".", "/")

        # Construct the metadata URL
        metadata_url = f"{repo_url.rstrip('/')}/{group_path}/{artifact_id}/maven-metadata.xml"

        return metadata_url

    def validate_url(self, url: str) -> Tuple[bool, str]:
        """Validate a URL format and basic connectivity.

        Args:
            url: URL to validate

        Returns:
            Tuple of (is_valid: bool, message: str)
        """
        if not url or not isinstance(url, str):
            return False, "URL cannot be empty"

        try:
            result = urllib.parse.urlparse(url)
            if not result.scheme or not result.netloc:
                return False, "Invalid URL format"

            if result.scheme not in ("http", "https"):
                return False, "URL must use http:// or https://"

            return True, "URL format is valid"

        except Exception as e:
            return False, f"URL validation error: {str(e)}"

    def _save_config(self) -> bool:
        """Save the current configuration to file.

        Returns:
            True if save was successful, False otherwise
        """
        config_file = self._get_config_file_path()
        if not config_file:
            return False

        try:
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "maven_repos": self._config["maven_repos"],
                        "custom_repos": self._config["custom_repos"],
                        "url_patterns": self._config["url_patterns"],
                        "download_sources": self._config["download_sources"],
                    },
                    f,
                    indent=2,
                )
            return True
        except Exception as e:
            logger.error(f"Error saving URL config to {config_file}: {e}")
            return False


# Global instance for convenience
url_config = URLConfig()


def get_maven_repositories() -> List[str]:
    """Get all configured Maven repository URLs."""
    return url_config.get_maven_repositories()


def get_repository_url(repo_index: int = 0) -> Optional[str]:
    """Get a specific Maven repository URL by index."""
    return url_config.get_repository_url(repo_index)


def add_maven_repository(url: str) -> bool:
    """Add a Maven repository URL."""
    return url_config.add_maven_repository(url)


def add_custom_repository(url: str) -> bool:
    """Add a custom repository URL."""
    return url_config.add_custom_repository(url)


def construct_maven_artifact_url(
    group_id: str, artifact_id: str, version: str, repo_index: int = 0, packaging: str = "jar"
) -> Optional[str]:
    """Construct a Maven artifact URL from coordinates."""
    return url_config.construct_maven_artifact_url(group_id, artifact_id, version, repo_index, packaging)


def construct_metadata_url(group_id: str, artifact_id: str, repo_index: int = 0) -> Optional[str]:
    """Construct a Maven metadata URL."""
    return url_config.construct_metadata_url(group_id, artifact_id, repo_index)


def validate_url(url: str) -> Tuple[bool, str]:
    """Validate a URL format and basic connectivity."""
    return url_config.validate_url(url)
