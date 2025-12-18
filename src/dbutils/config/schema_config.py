"""
Schema Configuration Module - JSON Schema validation for configuration files.

This module provides schema validation for configuration files to ensure they follow the
expected format and contain required fields.
"""

import json
import logging
import os
from typing import Dict, Any, Tuple, Optional

# Try to import jsonschema for validation, fall back to basic validation
try:
    import jsonschema
    JSON_SCHEMA_AVAILABLE = True
except ImportError:
    JSON_SCHEMA_AVAILABLE = False

# Configure logging
logger = logging.getLogger(__name__)


def validate_path_config(config_data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validate path configuration against schema.
    
    Args:
        config_data: Dictionary containing configuration data
        
    Returns:
        Tuple of (is_valid: bool, message: str)
    """
    required_keys = ["driver_dirs", "search_paths", "custom_paths"]
    
    for key in required_keys:
        if key not in config_data:
            return False, f"Missing required key: {key}"
    
    # Validate types of each section
    if not isinstance(config_data["driver_dirs"], list):
        return False, "driver_dirs must be a list of paths"
    
    if not isinstance(config_data["search_paths"], list):
        return False, "search_paths must be a list of paths" 
    
    if not isinstance(config_data["custom_paths"], list):
        return False, "custom_paths must be a list of paths"
    
    # Validate individual path entries
    for path_list_name, path_list in [
        ("driver_dirs", config_data["driver_dirs"]),
        ("search_paths", config_data["search_paths"]), 
        ("custom_paths", config_data["custom_paths"])
    ]:
        for i, path in enumerate(path_list):
            if not isinstance(path, str):
                return False, f"{path_list_name}[{i}] must be a string, got {type(path)}"
    
    return True, "Path configuration is valid"


def validate_url_config(config_data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validate URL configuration against schema.
    
    Args:
        config_data: Dictionary containing configuration data
        
    Returns:
        Tuple of (is_valid: bool, message: str)
    """
    required_keys = ["maven_repos", "custom_repos", "url_patterns", "download_sources"]
    
    for key in required_keys:
        if key not in config_data:
            return False, f"Missing required key: {key}"
    
    # Validate types of each section
    if not isinstance(config_data["maven_repos"], list):
        return False, "maven_repos must be a list of URLs"
    
    if not isinstance(config_data["custom_repos"], list):
        return False, "custom_repos must be a list of URLs" 
    
    if not isinstance(config_data["url_patterns"], dict):
        return False, "url_patterns must be a dictionary of pattern: template pairs"
    
    if not isinstance(config_data["download_sources"], dict):
        return False, "download_sources must be a dictionary of source configurations"
    
    # Validate individual URL entries
    for url_list_name, url_list in [
        ("maven_repos", config_data["maven_repos"]),
        ("custom_repos", config_data["custom_repos"])
    ]:
        for i, url in enumerate(url_list):
            if not isinstance(url, str):
                return False, f"{url_list_name}[{i}] must be a string, got {type(url)}"
            # Basic URL validation
            if not url.startswith(("http://", "https://")):
                return False, f"{url_list_name}[{i}] must start with http:// or https://"
    
    # Validate URL patterns
    for pattern_name, pattern_value in config_data["url_patterns"].items():
        if not isinstance(pattern_name, str):
            return False, f"URL pattern key '{pattern_name}' must be a string"
        if not isinstance(pattern_value, str):
            return False, f"URL pattern '{pattern_name}' value must be a string"
    
    # Validate download sources
    for source_name, source_config in config_data["download_sources"].items():
        if not isinstance(source_name, str):
            return False, f"Download source key '{source_name}' must be a string"
        if not isinstance(source_config, dict):
            return False, f"Download source '{source_name}' value must be a dictionary"
    
    return True, "URL configuration is valid"


def validate_auto_download_config(config_data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validate auto download configuration against schema.
    
    Args:
        config_data: Dictionary containing auto download configuration data
        
    Returns:
        Tuple of (is_valid: bool, message: str)
    """
    required_keys = ["auto_download_providers", "version_management", "repository_management"]
    
    for key in required_keys:
        if key not in config_data:
            return False, f"Missing required section: {key}"
    
    # Validate auto_download_providers
    providers = config_data["auto_download_providers"]
    if not isinstance(providers, dict):
        return False, "auto_download_providers must be a dictionary"
    
    for provider_name, provider_config in providers.items():
        if not isinstance(provider_name, str):
            return False, f"Provider name '{provider_name}' must be a string"
        
        if not isinstance(provider_config, dict):
            return False, f"Provider config for '{provider_name}' must be a dictionary"
        
        required_provider_keys = ["name", "driver_class", "database_type", "url_template", "requires_license"]
        for req_key in required_provider_keys:
            if req_key not in provider_config:
                return False, f"Provider '{provider_name}' missing required key: {req_key}"
    
    # Validate version_management
    version_mgmt = config_data["version_management"]
    if not isinstance(version_mgmt, dict):
        return False, "version_management must be a dictionary"
    
    if "version_resolution_strategy" in version_mgmt:
        strategy = version_mgmt["version_resolution_strategy"]
        if strategy not in ["latest_first", "recommended_first", "env_override_first"]:
            return False, f"Invalid version_resolution_strategy: {strategy}"
    
    # Validate repository_management
    repo_mgmt = config_data["repository_management"]
    if not isinstance(repo_mgmt, dict):
        return False, "repository_management must be a dictionary"
    
    if "repository_priority" in repo_mgmt:
        if not isinstance(repo_mgmt["repository_priority"], list):
            return False, "repository_priority must be a list of URLs"
        for i, repo in enumerate(repo_mgmt["repository_priority"]):
            if not isinstance(repo, str):
                return False, f"repository_priority[{i}] must be a string"
            if not repo.startswith(("http://", "https://")):
                return False, f"repository_priority[{i}] must start with http:// or https://"
    
    if "connectivity_testing" in repo_mgmt:
        if not isinstance(repo_mgmt["connectivity_testing"], dict):
            return False, "connectivity_testing must be a dictionary"
    
    return True, "Auto download configuration is valid"


def validate_config_file(file_path: str, config_type: str) -> Tuple[bool, str]:
    """
    Validate a configuration file against the appropriate schema.
    
    Args:
        file_path: Path to the configuration file
        config_type: Type of configuration ('path', 'url', or 'auto_download')
        
    Returns:
        Tuple of (is_valid: bool, message: str)
    """
    if not os.path.exists(file_path):
        return False, f"Configuration file does not exist: {file_path}"
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON in configuration file: {e}"
    except Exception as e:
        return False, f"Error reading configuration file: {e}"
    
    if config_type == "path":
        return validate_path_config(config_data)
    elif config_type == "url":
        return validate_url_config(config_data)
    elif config_type == "auto_download":
        return validate_auto_download_config(config_data)
    else:
        return False, f"Unknown configuration type: {config_type}"


def load_and_validate_config(file_path: str, config_type: str) -> Optional[Dict[str, Any]]:
    """
    Load and validate a configuration file, returning the config if valid.
    
    Args:
        file_path: Path to the configuration file
        config_type: Type of configuration ('path', 'url', or 'auto_download')
        
    Returns:
        Configuration dictionary if valid, None otherwise
    """
    is_valid, message = validate_config_file(file_path, config_type)
    if not is_valid:
        logger.error(f"Configuration validation failed: {message}")
        return None
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading configuration file: {e}")
        return None


def get_config_schema(config_type: str) -> Optional[Dict[str, Any]]:
    """
    Get the JSON schema for a specific configuration type.
    
    Args:
        config_type: Type of configuration ('path', 'url', or 'auto_download')
        
    Returns:
        JSON schema dictionary if available, None otherwise
    """
    if not JSON_SCHEMA_AVAILABLE:
        return None
    
    schemas = {
        "path": {
            "type": "object",
            "properties": {
                "driver_dirs": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "search_paths": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "custom_paths": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            },
            "required": ["driver_dirs", "search_paths", "custom_paths"],
            "additionalProperties": False
        },
        "url": {
            "type": "object",
            "properties": {
                "maven_repos": {
                    "type": "array",
                    "items": {"type": "string", "format": "uri"}
                },
                "custom_repos": {
                    "type": "array",
                    "items": {"type": "string", "format": "uri"}
                },
                "url_patterns": {
                    "type": "object",
                    "additionalProperties": {"type": "string"}
                },
                "download_sources": {
                    "type": "object",
                    "additionalProperties": {"type": "object"}
                }
            },
            "required": ["maven_repos", "custom_repos", "url_patterns", "download_sources"],
            "additionalProperties": False
        },
        "auto_download": {
            "type": "object",
            "properties": {
                "auto_download_providers": {
                    "type": "object",
                    "additionalProperties": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "driver_class": {"type": "string"},
                            "database_type": {"type": "string"},
                            "url_template": {"type": "string"},
                            "default_user": {"type": ["string", "null"]},
                            "default_password": {"type": ["string", "null"]},
                            "requires_license": {"type": "boolean"},
                            "maven_artifact": {"type": "string"},
                            "recommended_version": {"type": "string"},
                            "version_override_env": {"type": "string"},
                            "repository_override_env": {"type": "string"}
                        },
                        "required": ["name", "driver_class", "database_type", "url_template", "requires_license"]
                    }
                },
                "version_management": {
                    "type": "object",
                    "properties": {
                        "default_repository_index": {"type": "integer"},
                        "version_resolution_strategy": {"type": "string", "enum": ["latest_first", "recommended_first", "env_override_first"]},
                        "fallback_versions": {"type": "object"}
                    },
                    "required": ["version_management"]
                },
                "repository_management": {
                    "type": "object",
                    "properties": {
                        "repository_priority": {
                            "type": "array",
                            "items": {"type": "string", "format": "uri"}
                        },
                        "connectivity_testing": {
                            "type": "object",
                            "properties": {
                                "enabled": {"type": "boolean"},
                                "timeout_seconds": {"type": "number"},
                                "retry_attempts": {"type": "integer"}
                            }
                        }
                    },
                    "required": ["repository_management"]
                }
            },
            "required": ["auto_download_providers", "version_management", "repository_management"],
            "additionalProperties": False
        }
    }
    
    return schemas.get(config_type)