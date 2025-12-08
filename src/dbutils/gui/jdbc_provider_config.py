#!/usr/bin/env python3
"""
JDBC Provider Configuration - Auto-download enabled provider setup.

This module provides functionality to configure JDBC providers using the
auto-download system instead of manual JAR file references.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import the auto-download system
from .jdbc_auto_downloader import download_jdbc_driver, find_existing_drivers, list_installed_drivers
from .license_store import is_license_accepted

# Import the new configuration system
try:
    from ...config.dbutils_config import construct_maven_artifact_url, construct_metadata_url, get_maven_repositories
    from ...config.dbutils_config import get_driver_directory as config_get_driver_directory
    from ...config.path_config import PathConfig
    from ...config.url_config import URLConfig
except ImportError:
    from dbutils.config.dbutils_config import get_driver_directory as config_get_driver_directory
    from dbutils.config.path_config import PathConfig
    from dbutils.config.url_config import URLConfig


class AutoDownloadProviderConfig:
    """Configure JDBC providers using auto-download system."""

    def __init__(self):
        self.driver_directory = config_get_driver_directory()
        self.config_dir = os.environ.get("DBUTILS_CONFIG_DIR", os.path.expanduser("~/.config/dbutils"))
        self.providers_file = os.path.join(self.config_dir, "providers.json")

        # Initialize configuration systems
        self.url_config = URLConfig()
        self.path_config = PathConfig()

        # Create directories if they don't exist
        os.makedirs(self.driver_directory, exist_ok=True)
        os.makedirs(self.config_dir, exist_ok=True)

    def _load_auto_download_config(self) -> Dict[str, Dict[str, Any]]:
        """Load auto-download configuration from JSON file with environment overrides."""
        config_file = os.path.join(os.path.dirname(__file__), "..", "..", "config", "auto_download_config.json")

        try:
            with open(config_file, "r") as f:
                config_data = json.load(f)
        except Exception as e:
            logger.warning(f"Could not load auto-download config from file: {e}")
            return {}

        auto_download_providers = config_data.get("auto_download_providers", {})

        # Apply environment variable overrides
        for db_type, provider_config in auto_download_providers.items():
            version_env_var = provider_config.get("version_override_env")
            if version_env_var and version_env_var in os.environ:
                provider_config["recommended_version"] = os.environ[version_env_var]

            repo_env_var = provider_config.get("repository_override_env")
            if repo_env_var and repo_env_var in os.environ:
                # This would override the repository for this specific provider
                pass  # Repository override handled in URL construction

        return auto_download_providers

    def get_auto_download_configs(self) -> Dict[str, Dict[str, Any]]:
        """Get configuration for auto-download enabled providers using dynamic loading."""
        # Try to load from configuration file first
        file_configs = self._load_auto_download_config()

        if file_configs:
            return file_configs

        # Fallback to hardcoded defaults if config file not available
        return {
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
            },
            "h2": {
                "name": "H2 Database (Auto-Download)",
                "driver_class": "org.h2.Driver",
                "database_type": "h2",
                "url_template": "jdbc:h2:mem:{database};DB_CLOSE_DELAY=-1",
                "default_user": "sa",
                "default_password": "",
                "requires_license": False,
                "maven_artifact": "com.h2database:h2",
                "recommended_version": "2.2.224",
            },
            "derby": {
                "name": "Apache Derby (Auto-Download)",
                "driver_class": "org.apache.derby.jdbc.EmbeddedDriver",
                "database_type": "derby",
                "url_template": "jdbc:derby:{database};create=true",
                "default_user": None,
                "default_password": None,
                "requires_license": False,
                "maven_artifact": "org.apache.derby:derby",
                "recommended_version": "10.15.2.0",
            },
            "hsqldb": {
                "name": "HSQLDB (Auto-Download)",
                "driver_class": "org.hsqldb.jdbc.JDBCDriver",
                "database_type": "hsqldb",
                "url_template": "jdbc:hsqldb:mem:{database}",
                "default_user": "SA",
                "default_password": "",
                "requires_license": False,
                "maven_artifact": "org.hsqldb:hsqldb",
                "recommended_version": "2.7.2",
            },
            "duckdb": {
                "name": "DuckDB (Auto-Download)",
                "driver_class": "org.duckdb.DuckDBDriver",
                "database_type": "duckdb",
                "url_template": "jdbc:duckdb:{database}",
                "default_user": None,
                "default_password": None,
                "requires_license": False,
                "maven_artifact": "org.duckdb:duckdb_jdbc",
                "recommended_version": "0.10.2",
            },
        }

    def setup_auto_download_providers(self) -> Dict[str, Any]:
        """Setup JDBC providers using auto-download system."""
        auto_configs = self.get_auto_download_configs()
        providers = []

        # Load existing providers if they exist
        if os.path.exists(self.providers_file):
            try:
                with open(self.providers_file, "r") as f:
                    existing_providers = json.load(f)
                    # Remove existing auto-download providers to avoid duplicates
                    existing_providers = [
                        p
                        for p in existing_providers
                        if not any(p.get("name", "") == auto_config["name"] for auto_config in auto_configs.values())
                    ]
                    providers.extend(existing_providers)
            except Exception as e:
                logger.warning(f"Error loading existing providers: {e}")

        # Add auto-download providers
        for db_type, config in auto_configs.items():
            provider_config = {
                "name": config["name"],
                "driver_class": config["driver_class"],
                "database_type": config["database_type"],
                "url_template": config["url_template"],
                "default_user": config["default_user"],
                "default_password": config["default_password"],
                "auto_download": True,
                "maven_artifact": config["maven_artifact"],
                "recommended_version": config["recommended_version"],
                "requires_license": config["requires_license"],
            }
            providers.append(provider_config)

        # Save the updated providers
        with open(self.providers_file, "w") as f:
            json.dump(providers, f, indent=2)

        logger.info(f"Configured {len(auto_configs)} auto-download providers")
        return {"providers": providers, "config_file": self.providers_file}

    def get_driver_path_for_type(self, db_type: str) -> Optional[str]:
        """Get the path to a downloaded driver for the specified database type."""
        # First check if we already have the driver
        existing_drivers = find_existing_drivers(db_type)
        if existing_drivers:
            return existing_drivers[0]

        # If not, try to download it
        return self.download_driver_for_type(db_type)

    def download_driver_for_type(self, db_type: str) -> Optional[str]:
        """Download a JDBC driver for the specified database type using new configuration system."""
        try:
            # Check license requirements
            if db_type in ["oracle", "db2", "jt400"]:
                license_key = f"jdbc_driver_{db_type}"
                if not is_license_accepted(license_key):
                    logger.warning(f"License not accepted for {db_type}. Please accept license before downloading.")
                    return None

            # Get version from environment variable or use recommended
            version = self._get_version_for_type(db_type)

            # Use the auto-downloader to get the driver with new configuration
            result = download_jdbc_driver(db_type=db_type, version=version, target_dir=self.driver_directory)

            if result:
                logger.info(f"Successfully downloaded {db_type} driver to: {result}")
                return result
            else:
                logger.warning(f"Failed to download {db_type} driver automatically")
                return None

        except Exception as e:
            logger.error(f"Error downloading {db_type} driver: {e}")
            return None

    def _get_version_for_type(self, db_type: str) -> str:
        """Get the appropriate version for a database type with environment variable override support."""
        auto_configs = self.get_auto_download_configs()
        if db_type not in auto_configs:
            return "recommended"

        config = auto_configs[db_type]

        # Check for environment variable override
        version_env_var = config.get("version_override_env")
        if version_env_var and version_env_var in os.environ:
            return os.environ[version_env_var]

        # Return recommended version from config
        return config.get("recommended_version", "recommended")

    def _get_repository_for_type(self, db_type: str) -> Optional[str]:
        """Get the appropriate repository URL for a database type with environment variable override support."""
        auto_configs = self.get_auto_download_configs()
        if db_type not in auto_configs:
            return None

        config = auto_configs[db_type]

        # Check for environment variable override
        repo_env_var = config.get("repository_override_env")
        if repo_env_var and repo_env_var in os.environ:
            return os.environ[repo_env_var]

        return None

    def get_version_resolution_strategy(self) -> str:
        """Get the version resolution strategy from configuration."""
        config_file = os.path.join(os.path.dirname(__file__), "..", "..", "config", "auto_download_config.json")

        try:
            with open(config_file, "r") as f:
                config_data = json.load(f)
            return config_data.get("version_management", {}).get("version_resolution_strategy", "latest_first")
        except Exception:
            return "latest_first"

    def get_fallback_versions(self, db_type: str) -> List[str]:
        """Get fallback versions for a database type from configuration."""
        config_file = os.path.join(os.path.dirname(__file__), "..", "..", "config", "auto_download_config.json")

        try:
            with open(config_file, "r") as f:
                config_data = json.load(f)
            return config_data.get("version_management", {}).get("fallback_versions", {}).get(db_type, [])
        except Exception:
            return []

    def get_repository_priority(self) -> List[str]:
        """Get repository priority list from configuration."""
        config_file = os.path.join(os.path.dirname(__file__), "..", "..", "config", "auto_download_config.json")

        try:
            with open(config_file, "r") as f:
                config_data = json.load(f)
            return config_data.get("repository_management", {}).get("repository_priority", [])
        except Exception:
            return []

    def get_all_available_drivers(self) -> List[str]:
        """Get all available JDBC drivers in the driver directory."""
        return list_installed_drivers()

    def ensure_driver_available(self, db_type: str) -> bool:
        """Ensure a JDBC driver is available, downloading if necessary."""
        # Check if driver already exists
        existing_drivers = find_existing_drivers(db_type)
        if existing_drivers:
            logger.info(f"Driver for {db_type} already available: {existing_drivers[0]}")
            return True

        # Try to download the driver
        logger.info(f"No existing driver found for {db_type}, attempting download...")
        result = self.download_driver_for_type(db_type)

        if result:
            logger.info(f"Successfully ensured {db_type} driver is available")
            return True
        else:
            logger.warning(f"Could not ensure {db_type} driver availability")
            return False

    def get_provider_config_for_auto_download(self, db_type: str) -> Optional[Dict[str, Any]]:
        """Get provider configuration for auto-download setup."""
        auto_configs = self.get_auto_download_configs()
        if db_type in auto_configs:
            config = auto_configs[db_type]

            # Ensure driver is available
            driver_path = self.get_driver_path_for_type(db_type)
            if not driver_path:
                logger.warning(f"Driver not available for {db_type}")
                return None

            return {
                "name": config["name"],
                "driver_class": config["driver_class"],
                "jar_path": driver_path,
                "url_template": config["url_template"],
                "default_user": config["default_user"],
                "default_password": config["default_password"],
                "auto_download": True,
                "database_type": db_type,
            }
        else:
            logger.warning(f"No auto-download configuration found for {db_type}")
            return None


def setup_auto_download_infrastructure():
    """Setup the complete auto-download infrastructure."""
    config = AutoDownloadProviderConfig()

    # Setup auto-download providers
    setup_result = config.setup_auto_download_providers()

    # Ensure drivers are available for common databases
    common_databases = ["sqlite", "h2", "derby", "hsqldb", "duckdb"]
    for db_type in common_databases:
        config.ensure_driver_available(db_type)

    logger.info("Auto-download infrastructure setup complete")
    return setup_result


def get_auto_download_provider_config(db_type: str) -> Optional[Dict[str, Any]]:
    """Get auto-download provider configuration for a specific database type."""
    config = AutoDownloadProviderConfig()
    return config.get_provider_config_for_auto_download(db_type)


def ensure_all_drivers_available() -> Dict[str, bool]:
    """Ensure all common JDBC drivers are available."""
    config = AutoDownloadProviderConfig()
    common_databases = ["sqlite", "h2", "derby", "hsqldb", "duckdb"]

    results = {}
    for db_type in common_databases:
        results[db_type] = config.ensure_driver_available(db_type)

    return results


# Convenience function for direct use
def get_configured_provider(db_type: str) -> Optional[Dict[str, Any]]:
    """Get a fully configured provider with auto-download support."""
    return get_auto_download_provider_config(db_type)


if __name__ == "__main__":
    # Example usage
    setup_auto_download_infrastructure()
    print("Auto-download infrastructure setup complete!")
