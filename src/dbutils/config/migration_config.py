"""
Configuration Migration Module - Handles configuration format migration.

This module provides utilities to migrate configuration from older formats to
the current format, ensuring backward compatibility.
"""

import json
import logging
import os
from typing import Dict, Any, Optional, Tuple

# Configure logging
logger = logging.getLogger(__name__)


def migrate_path_config(old_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Migrate old path configuration format to current format.
    
    Args:
        old_config: Old configuration dictionary
        
    Returns:
        Migrated configuration dictionary
    """
    new_config = {
        "driver_dirs": [],
        "search_paths": [],
        "custom_paths": []
    }
    
    # Handle old format where paths might be stored differently
    if "driver_directory" in old_config:
        # Old single driver directory format
        new_config["driver_dirs"] = [old_config["driver_directory"]]
    elif "driver_dirs" in old_config:
        # Already in new format but maybe needs validation
        if isinstance(old_config["driver_dirs"], list):
            new_config["driver_dirs"] = old_config["driver_dirs"]
    elif "driver_path" in old_config:
        # Very old format
        new_config["driver_dirs"] = [old_config["driver_path"]]
    
    if "search_paths" in old_config:
        if isinstance(old_config["search_paths"], list):
            new_config["search_paths"] = old_config["search_paths"]
    
    if "custom_paths" in old_config:
        if isinstance(old_config["custom_paths"], list):
            new_config["custom_paths"] = old_config["custom_paths"]
    
    # Handle old format with single path as string instead of list
    for key in ["driver_dirs", "search_paths", "custom_paths"]:
        if key in old_config and isinstance(old_config[key], str):
            new_config[key] = [old_config[key]]
    
    return new_config


def migrate_url_config(old_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Migrate old URL configuration format to current format.
    
    Args:
        old_config: Old configuration dictionary
        
    Returns:
        Migrated configuration dictionary
    """
    new_config = {
        "maven_repos": [],
        "custom_repos": [],
        "url_patterns": {},
        "download_sources": {}
    }
    
    # Handle old format with repositories
    if "maven_repositories" in old_config:
        if isinstance(old_config["maven_repositories"], list):
            new_config["maven_repos"] = old_config["maven_repositories"]
    elif "maven_repo" in old_config:
        # Old single repo format
        new_config["maven_repos"] = [old_config["maven_repo"]]
    elif "maven_repos" in old_config:
        if isinstance(old_config["maven_repos"], list):
            new_config["maven_repos"] = old_config["maven_repos"]
    
    if "custom_repos" in old_config:
        if isinstance(old_config["custom_repos"], list):
            new_config["custom_repos"] = old_config["custom_repos"]
    
    if "url_patterns" in old_config:
        if isinstance(old_config["url_patterns"], dict):
            new_config["url_patterns"] = old_config["url_patterns"]
    
    if "download_sources" in old_config:
        if isinstance(old_config["download_sources"], dict):
            new_config["download_sources"] = old_config["download_sources"]
    
    # Handle old format with single URL as string instead of list
    for key in ["maven_repos", "custom_repos"]:
        if key in old_config and isinstance(old_config[key], str):
            new_config[key] = [old_config[key]]
    
    # Handle old "repositories" key that might contain different repo types
    if "repositories" in old_config and isinstance(old_config["repositories"], list):
        # Try to determine if these are maven or custom repos
        for repo in old_config["repositories"]:
            if isinstance(repo, str):
                if any(maven_indicator in repo.lower() for maven_indicator in ["maven", "repo1", "repo.maven"]):
                    if repo not in new_config["maven_repos"]:
                        new_config["maven_repos"].append(repo)
                else:
                    if repo not in new_config["custom_repos"]:
                        new_config["custom_repos"].append(repo)
    
    return new_config


def migrate_auto_download_config(old_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Migrate old auto-download configuration format to current format.
    
    Args:
        old_config: Old auto-download configuration dictionary
        
    Returns:
        Migrated configuration dictionary
    """
    new_config = {
        "auto_download_providers": {},
        "version_management": {
            "default_repository_index": 0,
            "version_resolution_strategy": "latest_first",
            "fallback_versions": {}
        },
        "repository_management": {
            "repository_priority": [
                "https://repo1.maven.org/maven2/",
                "https://repo.maven.apache.org/maven2/",
                "https://maven.aliyun.com/repository/central/"
            ],
            "connectivity_testing": {
                "enabled": True,
                "timeout_seconds": 5,
                "retry_attempts": 2
            }
        }
    }
    
    # Handle old provider format
    if "providers" in old_config:
        if isinstance(old_config["providers"], dict):
            new_config["auto_download_providers"] = old_config["providers"]
    
    if "auto_download_providers" in old_config:
        if isinstance(old_config["auto_download_providers"], dict):
            new_config["auto_download_providers"] = old_config["auto_download_providers"]
    
    # Handle old version management settings
    if "version_management" in old_config:
        if isinstance(old_config["version_management"], dict):
            new_config["version_management"].update(old_config["version_management"])
    
    # Handle old repository settings
    if "repository_management" in old_config:
        if isinstance(old_config["repository_management"], dict):
            new_config["repository_management"].update(old_config["repository_management"])
    
    # Handle old fallback versions
    if "fallback_versions" in old_config:
        if isinstance(old_config["fallback_versions"], dict):
            new_config["version_management"]["fallback_versions"] = old_config["fallback_versions"]
    
    # Handle older configuration structure that might have been flattened
    if "repository_priority" in old_config and "repository_management" not in new_config:
        new_config["repository_management"]["repository_priority"] = old_config["repository_priority"]
    
    return new_config


def detect_config_version(config: Dict[str, Any]) -> str:
    """
    Detect the configuration format version based on its structure.
    
    Args:
        config: Configuration dictionary to analyze
        
    Returns:
        Version string ("v1", "v2", "unknown")
    """
    # Check for new format features
    if "auto_download_providers" in config and "version_management" in config:
        return "v2"
    if "driver_dirs" in config and "search_paths" in config:
        return "v2"
    if "maven_repos" in config and "custom_repos" in config:
        return "v2"
    
    # Check for old format features
    if "driver_directory" in config or "driver_path" in config:
        return "v1"
    if "maven_repositories" in config or "maven_repo" in config:
        return "v1"
    if "repositories" in config:
        return "v1"
    
    return "unknown"


def migrate_config(config: Dict[str, Any], config_type: str) -> Tuple[bool, Dict[str, Any], str]:
    """
    Migrate configuration from old format to current format.
    
    Args:
        config: Configuration dictionary to migrate
        config_type: Type of configuration ('path', 'url', 'auto_download')
        
    Returns:
        Tuple of (was_migrated: bool, migrated_config: dict, version: str)
    """
    original_version = detect_config_version(config)
    
    if original_version == "v2":
        # Already current format
        return False, config, "v2"
    
    if original_version == "unknown":
        logger.warning("Could not determine configuration version, using as-is")
        return False, config, "unknown"
    
    logger.info(f"Migrating configuration from {original_version} to current format")
    
    if config_type == "path":
        migrated = migrate_path_config(config)
    elif config_type == "url":
        migrated = migrate_url_config(config)
    elif config_type == "auto_download":
        migrated = migrate_auto_download_config(config)
    else:
        logger.error(f"Unknown configuration type: {config_type}")
        return False, config, original_version
    
    return True, migrated, "v2"


def load_and_migrate_config_file(file_path: str, config_type: str) -> Optional[Dict[str, Any]]:
    """
    Load a configuration file and migrate it if necessary.
    
    Args:
        file_path: Path to the configuration file
        config_type: Type of configuration ('path', 'url', 'auto_download')
        
    Returns:
        Migrated configuration dictionary, or None if loading failed
    """
    if not os.path.exists(file_path):
        logger.warning(f"Configuration file does not exist: {file_path}")
        return None
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in configuration file {file_path}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error reading configuration file {file_path}: {e}")
        return None
    
    # Migrate if necessary
    was_migrated, migrated_config, version = migrate_config(config, config_type)
    
    if was_migrated:
        logger.info(f"Configuration file {file_path} was migrated to current format")
        # Optionally save the migrated configuration back to file
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(migrated_config, f, indent=2)
            logger.info(f"Migrated configuration saved to {file_path}")
        except Exception as e:
            logger.error(f"Failed to save migrated configuration to {file_path}: {e}")
    
    return migrated_config