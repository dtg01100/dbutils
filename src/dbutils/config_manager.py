"""
Configuration Management System for JDBC Providers

This module provides a flexible configuration system that can load from:
- External configuration files
- Environment variables
- Default configurations
"""

import json
import os
import re
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

class ConfigManager:
    """Flexible configuration manager with multiple sources and fallback mechanisms."""

    def __init__(self):
        self.config_sources = []
        self.loaded_config = {}

    def add_config_source(self, source: str, source_type: str = "file"):
        """Add a configuration source to the loading hierarchy."""
        self.config_sources.append((source, source_type))

    def load_configuration(self) -> Dict[str, Any]:
        """Load configuration from all sources with proper fallback mechanisms."""
        config = {}

        # Load from each source in order (later sources override earlier ones)
        for source, source_type in self.config_sources:
            try:
                if source_type == "file":
                    source_config = self._load_from_file(source)
                elif source_type == "env":
                    source_config = self._load_from_env(source)
                else:
                    continue

                if source_config:
                    self._deep_merge(config, source_config)

            except Exception as e:
                logger.warning(f"Failed to load config from {source_type} source {source}: {e}")
                continue

        # Apply environment variable expansion and overrides
        final_config = self._apply_environment_overrides(config)

        self.loaded_config = final_config
        return final_config

    def _load_from_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Load configuration from a JSON file."""
        if not os.path.exists(file_path):
            return None

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load config file {file_path}: {e}")
            return None

    def _load_from_env(self, prefix: str = "DBUTILS") -> Dict[str, Any]:
        """Load configuration from environment variables with the given prefix."""
        config = {}
        env_vars = {}

        # Collect all environment variables with the prefix
        for key, value in os.environ.items():
            if key.startswith(prefix + "_"):
                env_key = key[len(prefix) + 1:].lower()  # Remove prefix and underscore
                env_vars[env_key] = value

        # Convert to nested structure if needed
        if env_vars:
            config["environment"] = env_vars

        return config

    def _expand_environment_variables(self, value: Any) -> Any:
        """Expand environment variables in configuration values."""
        if isinstance(value, str):
            # Handle ${VAR} and $VAR syntax
            def replace_match(match):
                var_name = match.group(1)
                return os.environ.get(var_name, match.group(0))

            # Replace ${VAR} pattern
            pattern = re.compile(r'\$\{([^}]+)\}')
            result = pattern.sub(replace_match, value)

            # Replace $VAR pattern
            pattern = re.compile(r'\$([a-zA-Z_][a-zA-Z0-9_]*)')
            result = pattern.sub(replace_match, result)

            return result
        elif isinstance(value, dict):
            return {k: self._expand_environment_variables(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._expand_environment_variables(v) for v in value]
        else:
            return value

    def _apply_environment_overrides(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment variable overrides to the configuration."""
        # Expand environment variables in all values
        expanded_config = self._expand_environment_variables(config)

        # Apply specific overrides from environment variables
        env_overrides = {}

        # Check for provider-specific overrides
        for key, value in os.environ.items():
            if key.startswith("DBUTILS_"):
                # Remove DBUTILS_ prefix
                config_key = key[8:].lower()

                # Handle nested structure
                parts = config_key.split("_")
                current = env_overrides

                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]

                current[parts[-1]] = value

        # Deep merge environment overrides
        if env_overrides:
            self._deep_merge(expanded_config, env_overrides)

        return expanded_config

    def _deep_merge(self, target: Dict, source: Dict):
        """Deep merge source dictionary into target dictionary."""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_merge(target[key], value)
            else:
                target[key] = value

    def get_jar_path(self, jar_name: str) -> Optional[str]:
        """Find JAR path using dynamic resolution with environment variable overrides."""
        # Check environment variable first
        env_var = f"DBUTILS_{jar_name.upper().replace('.', '_').replace('-', '_')}_JAR"
        if env_var in os.environ:
            return os.environ[env_var]

        # Check common locations
        search_paths = [
            os.path.join(os.path.dirname(__file__), "..", "..", "jars", f"{jar_name}.jar"),
            os.path.join(os.path.dirname(__file__), "jars", f"{jar_name}.jar"),
            os.path.join(os.getcwd(), "jars", f"{jar_name}.jar"),
            os.path.join(os.path.expanduser("~"), ".dbutils", "jars", f"{jar_name}.jar")
        ]

        # Add custom JAR search paths from environment
        extra_paths = os.environ.get("DBUTILS_JAR_SEARCH_PATHS", "")
        if extra_paths:
            for path in extra_paths.split(os.pathsep):
                search_paths.append(os.path.join(path, f"{jar_name}.jar"))

        # Find the first existing JAR
        for path in search_paths:
            if os.path.exists(path):
                return path

        return None

    def get_config(self, key: str, default: Any = None) -> Any:
        """Get a configuration value with fallback to default."""
        keys = key.split('.')
        current = self.loaded_config

        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return default

        return current

    def get_jar_path(self, jar_name: str) -> Optional[str]:
        """Find JAR path using dynamic resolution with environment variable overrides."""
        # Check environment variable first
        env_var = f"DBUTILS_{jar_name.upper().replace('.', '_').replace('-', '_')}_JAR"
        if env_var in os.environ:
            return os.environ[env_var]

        # Check common locations
        search_paths = [
            os.path.join(os.path.dirname(__file__), "..", "..", "jars", f"{jar_name}.jar"),
            os.path.join(os.path.dirname(__file__), "jars", f"{jar_name}.jar"),
            os.path.join(os.getcwd(), "jars", f"{jar_name}.jar"),
            os.path.join(os.path.expanduser("~"), ".dbutils", "jars", f"{jar_name}.jar")
        ]

        # Add custom JAR search paths from environment
        extra_paths = os.environ.get("DBUTILS_JAR_SEARCH_PATHS", "")
        if extra_paths:
            for path in extra_paths.split(os.pathsep):
                search_paths.append(os.path.join(path, f"{jar_name}.jar"))

        # Find the first existing JAR
        for path in search_paths:
            if os.path.exists(path):
                return path

        return None

def get_default_config_manager() -> ConfigManager:
    """Create a default configuration manager with standard sources."""
    manager = ConfigManager()

    # Add configuration sources in order of precedence
    # 1. Environment variables (highest priority)
    manager.add_config_source("DBUTILS", "env")

    # 2. User-specific configuration
    user_config = os.path.expanduser("~/.config/dbutils/jdbc_config.json")
    manager.add_config_source(user_config, "file")

    # 3. Project configuration
    project_config = os.path.join(os.path.dirname(__file__), "config", "jdbc_config.json")
    manager.add_config_source(project_config, "file")

    # 4. Default templates
    default_templates = os.path.join(os.path.dirname(__file__), "config", "jdbc_templates.json")
    manager.add_config_source(default_templates, "file")

    return manager

class ConfigurationLoader:
    """High-level configuration loader with comprehensive fallback mechanisms."""

    def __init__(self):
        self.config_manager = get_default_config_manager()
        self.loaded_config = None

    def load_all_configurations(self) -> Dict[str, Any]:
        """Load all configurations with comprehensive fallback mechanisms."""
        try:
            # Load main configuration
            config = self.config_manager.load_configuration()

            # Apply additional fallback mechanisms
            self._apply_fallback_mechanisms(config)

            self.loaded_config = config
            return config

        except Exception as e:
            logger.error(f"Configuration loading failed: {e}")
            # Return minimal fallback configuration
            return self._get_minimal_fallback_config()

    def _apply_fallback_mechanisms(self, config: Dict[str, Any]):
        """Apply comprehensive fallback mechanisms to ensure configuration completeness."""
        # Ensure provider templates exist
        if "provider_templates" not in config:
            config["provider_templates"] = self._get_default_provider_templates()

        # Ensure default providers exist
        if "default_providers" not in config:
            config["default_providers"] = self._get_default_providers()

        # Ensure environment overrides are processed
        self._process_environment_overrides(config)

    def _get_default_provider_templates(self) -> Dict[str, Dict]:
        """Get default provider templates as fallback."""
        return {
            "PostgreSQL": {
                "driver_class": "org.postgresql.Driver",
                "url_template": "jdbc:postgresql://{host}:{port}/{database}",
                "default_port": 5432,
                "description": "PostgreSQL database connection"
            },
            "MySQL": {
                "driver_class": "com.mysql.cj.jdbc.Driver",
                "url_template": "jdbc:mysql://{host}:{port}/{database}",
                "default_port": 3306,
                "description": "MySQL database connection"
            },
            "SQLite": {
                "driver_class": "org.sqlite.JDBC",
                "url_template": "jdbc:sqlite:{database}",
                "default_port": 0,
                "description": "SQLite file-based database"
            },
            "Custom": {
                "driver_class": "",
                "url_template": "jdbc:{custom}://{host}:{port}/{database}",
                "default_port": 0,
                "description": "Custom JDBC provider - configure all parameters manually"
            }
        }

    def _get_default_providers(self) -> Dict[str, Dict]:
        """Get default providers as fallback."""
        return {
            "SQLite Local": {
                "category": "SQLite",
                "driver_class": "org.sqlite.JDBC",
                "jar_path": "",
                "url_template": "jdbc:sqlite:{database}",
                "default_database": "sample.db",
                "extra_properties": {}
            }
        }

    def _process_environment_overrides(self, config: Dict[str, Any]):
        """Process environment variable overrides with comprehensive fallback."""
        # Handle JAR path overrides
        for template_name, template_data in config.get("provider_templates", {}).items():
            if "driver_class" in template_data:
                env_var = f"DBUTILS_{template_name.upper()}_DRIVER_CLASS"
                if env_var in os.environ:
                    template_data["driver_class"] = os.environ[env_var]

            if "url_template" in template_data:
                env_var = f"DBUTILS_{template_name.upper()}_URL_TEMPLATE"
                if env_var in os.environ:
                    template_data["url_template"] = os.environ[env_var]

    def _get_minimal_fallback_config(self) -> Dict[str, Any]:
        """Get minimal fallback configuration when all else fails."""
        return {
            "provider_templates": self._get_default_provider_templates(),
            "default_providers": self._get_default_providers(),
            "fallback_mode": True
        }

    def get_provider_template(self, category: str) -> Optional[Dict]:
        """Get a provider template with fallback mechanisms."""
        if not self.loaded_config:
            self.load_all_configurations()

        template = self.loaded_config.get("provider_templates", {}).get(category)

        if not template:
            # Try to find a similar template
            category_lower = category.lower()
            for name, tpl in self.loaded_config.get("provider_templates", {}).items():
                if name.lower() == category_lower:
                    return tpl

            # Return generic template as last resort
            return {
                "driver_class": "",
                "url_template": "jdbc:{category}://{host}:{port}/{database}",
                "default_port": 0,
                "description": f"{category} database connection"
            }

        return template

    def get_jar_path_with_fallback(self, jar_name: str) -> str:
        """Get JAR path with comprehensive fallback mechanisms."""
        # Try config manager first
        jar_path = self.config_manager.get_jar_path(jar_name)
        if jar_path:
            return jar_path

        # Try environment variable
        env_var = f"DBUTILS_{jar_name.upper().replace('.', '_').replace('-', '_')}_JAR"
        if env_var in os.environ:
            return os.environ[env_var]

        # Try common fallback locations
        fallback_locations = [
            os.path.join(os.path.dirname(__file__), "..", "..", "jars", f"{jar_name}.jar"),
            os.path.join(os.path.dirname(__file__), "jars", f"{jar_name}.jar"),
            os.path.join(os.getcwd(), "jars", f"{jar_name}.jar"),
            os.path.join(os.path.expanduser("~"), ".dbutils", "jars", f"{jar_name}.jar")
        ]

        for location in fallback_locations:
            if os.path.exists(location):
                return location

        # Return empty string as last resort (user will need to configure)
        return ""

class ConfigurationLoader:
    """High-level configuration loader with comprehensive fallback mechanisms."""

    def __init__(self):
        self.config_manager = get_default_config_manager()
        self.loaded_config = None

    def load_all_configurations(self) -> Dict[str, Any]:
        """Load all configurations with comprehensive fallback mechanisms."""
        try:
            # Load main configuration
            config = self.config_manager.load_configuration()

            # Apply additional fallback mechanisms
            self._apply_fallback_mechanisms(config)

            self.loaded_config = config
            return config

        except Exception as e:
            logger.error(f"Configuration loading failed: {e}")
            # Return minimal fallback configuration
            return self._get_minimal_fallback_config()

    def _apply_fallback_mechanisms(self, config: Dict[str, Any]):
        """Apply comprehensive fallback mechanisms to ensure configuration completeness."""
        # Ensure provider templates exist
        if "provider_templates" not in config:
            config["provider_templates"] = self._get_default_provider_templates()

        # Ensure default providers exist
        if "default_providers" not in config:
            config["default_providers"] = self._get_default_providers()

        # Ensure environment overrides are processed
        self._process_environment_overrides(config)

    def _get_default_provider_templates(self) -> Dict[str, Dict]:
        """Get default provider templates as fallback."""
        return {
            "PostgreSQL": {
                "driver_class": "org.postgresql.Driver",
                "url_template": "jdbc:postgresql://{host}:{port}/{database}",
                "default_port": 5432,
                "description": "PostgreSQL database connection"
            },
            "MySQL": {
                "driver_class": "com.mysql.cj.jdbc.Driver",
                "url_template": "jdbc:mysql://{host}:{port}/{database}",
                "default_port": 3306,
                "description": "MySQL database connection"
            },
            "SQLite": {
                "driver_class": "org.sqlite.JDBC",
                "url_template": "jdbc:sqlite:{database}",
                "default_port": 0,
                "description": "SQLite file-based database"
            }
        }

    def _get_default_providers(self) -> Dict[str, Dict]:
        """Get default providers as fallback."""
        return {
            "SQLite Local": {
                "category": "SQLite",
                "driver_class": "org.sqlite.JDBC",
                "jar_path": "",
                "url_template": "jdbc:sqlite:{database}",
                "default_database": "sample.db",
                "extra_properties": {}
            }
        }

    def _process_environment_overrides(self, config: Dict[str, Any]):
        """Process environment variable overrides with comprehensive fallback."""
        # Handle JAR path overrides
        for template_name, template_data in config.get("provider_templates", {}).items():
            if "driver_class" in template_data:
                env_var = f"DBUTILS_{template_name.upper()}_DRIVER_CLASS"
                if env_var in os.environ:
                    template_data["driver_class"] = os.environ[env_var]

            if "url_template" in template_data:
                env_var = f"DBUTILS_{template_name.upper()}_URL_TEMPLATE"
                if env_var in os.environ:
                    template_data["url_template"] = os.environ[env_var]

    def _get_minimal_fallback_config(self) -> Dict[str, Any]:
        """Get minimal fallback configuration when all else fails."""
        return {
            "provider_templates": self._get_default_provider_templates(),
            "default_providers": self._get_default_providers(),
            "fallback_mode": True
        }

    def get_provider_template(self, category: str) -> Optional[Dict]:
        """Get a provider template with fallback mechanisms."""
        if not self.loaded_config:
            self.load_all_configurations()

        template = self.loaded_config.get("provider_templates", {}).get(category)

        if not template:
            # Try to find a similar template
            category_lower = category.lower()
            for name, tpl in self.loaded_config.get("provider_templates", {}).items():
                if name.lower() == category_lower:
                    return tpl

            # Return generic template as last resort
            return {
                "driver_class": "",
                "url_template": "jdbc:{category}://{host}:{port}/{database}",
                "default_port": 0,
                "description": f"{category} database connection"
            }

        return template

    def get_jar_path_with_fallback(self, jar_name: str) -> str:
        """Get JAR path with comprehensive fallback mechanisms."""
        # Try config manager first
        jar_path = self.config_manager.get_jar_path(jar_name)
        if jar_path:
            return jar_path

        # Try environment variable
        env_var = f"DBUTILS_{jar_name.upper().replace('.', '_').replace('-', '_')}_JAR"
        if env_var in os.environ:
            return os.environ[env_var]

        # Try common fallback locations
        fallback_locations = [
            os.path.join(os.path.dirname(__file__), "..", "..", "jars", f"{jar_name}.jar"),
            os.path.join(os.path.dirname(__file__), "jars", f"{jar_name}.jar"),
            os.path.join(os.getcwd(), "jars", f"{jar_name}.jar"),
            os.path.join(os.path.expanduser("~"), ".dbutils", "jars", f"{jar_name}.jar")
        ]

        for location in fallback_locations:
            if os.path.exists(location):
                return location

        # Return empty string as last resort (user will need to configure)
        return ""