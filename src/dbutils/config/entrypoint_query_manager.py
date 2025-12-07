#!/usr/bin/env python3
"""
Entrypoint Query Manager

This module provides functionality for managing default and custom entrypoint queries
for different database types. Entrypoint queries are used to discover database
schema information and validate connections.
"""

import json
import logging
import os
from dataclasses import dataclass
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

@dataclass
class EntrypointQuerySet:
    """Represents a set of entrypoint queries for a database type."""
    identity_query: str = ""
    schema_query: str = ""
    database_info_query: str = ""

    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary representation."""
        return {
            "identity_query": self.identity_query,
            "schema_query": self.schema_query,
            "database_info_query": self.database_info_query
        }

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'EntrypointQuerySet':
        """Create from dictionary data."""
        return cls(
            identity_query=data.get("identity_query", ""),
            schema_query=data.get("schema_query", ""),
            database_info_query=data.get("database_info_query", "")
        )

class EntrypointQueryManager:
    """Manages default and custom entrypoint queries for database types."""

    def __init__(self, config_path: str = None):
        """
        Initialize the Entrypoint Query Manager.

        Args:
            config_path: Path to the entrypoint queries configuration file.
                        If None, uses default path.
        """
        if config_path is None:
            config_dir = os.path.expanduser("~/.config/dbutils")
            os.makedirs(config_dir, exist_ok=True)
            config_path = os.path.join(config_dir, "entrypoint_queries.json")

        self.config_path = config_path
        self.default_queries: Dict[str, EntrypointQuerySet] = {}
        self.custom_queries: Dict[str, EntrypointQuerySet] = {}

        # Load configuration
        self._load_configuration()

    def _load_configuration(self) -> None:
        """Load entrypoint queries configuration from file."""
        try:
            # First try to load from the configuration file
            if os.path.exists(self.config_path):
                with open(self.config_path, "r", encoding="utf-8") as f:
                    config_data = json.load(f)

                # Load default queries
                default_data = config_data.get("default_entrypoint_queries", {})
                for db_type, queries in default_data.items():
                    self.default_queries[db_type] = EntrypointQuerySet.from_dict(queries)

                # Load custom queries
                custom_data = config_data.get("custom_entrypoint_queries", {})
                for query_name, queries in custom_data.items():
                    self.custom_queries[query_name] = EntrypointQuerySet.from_dict(queries)

                logger.info(f"Loaded entrypoint queries from {self.config_path}")
            else:
                # If config file doesn't exist, load from package defaults
                self._load_package_defaults()
                logger.info("Using package default entrypoint queries")

        except Exception as e:
            logger.warning(f"Failed to load entrypoint queries configuration: {e}")
            # Fallback to hardcoded defaults
            self._load_hardcoded_defaults()

    def _load_package_defaults(self) -> None:
        """Load default entrypoint queries from package configuration file."""
        try:
            # Try to load from package config file
            package_config_path = os.path.join(
                os.path.dirname(__file__), "entrypoint_queries.json"
            )

            if os.path.exists(package_config_path):
                with open(package_config_path, "r", encoding="utf-8") as f:
                    config_data = json.load(f)

                # Load default queries
                default_data = config_data.get("default_entrypoint_queries", {})
                for db_type, queries in default_data.items():
                    self.default_queries[db_type] = EntrypointQuerySet.from_dict(queries)

                logger.info("Loaded package default entrypoint queries")
            else:
                # Fallback to hardcoded defaults
                self._load_hardcoded_defaults()

        except Exception as e:
            logger.warning(f"Failed to load package default entrypoint queries: {e}")
            self._load_hardcoded_defaults()

    def _load_hardcoded_defaults(self) -> None:
        """Load hardcoded default entrypoint queries as fallback."""
        # Define hardcoded defaults for all supported database types
        hardcoded_defaults = {
            "PostgreSQL": {
                "identity_query": "SELECT CURRENT_TIMESTAMP as current_timestamp",
                "schema_query": (
                    "SELECT table_schema, table_name FROM information_schema.tables "
                    "WHERE table_schema NOT IN ('pg_catalog', 'information_schema')"
                ),
                "database_info_query": "SELECT version() as database_version"
            },
            "MySQL": {
                "identity_query": "SELECT NOW() as current_timestamp",
                "schema_query": (
                    "SELECT table_schema, table_name FROM information_schema.tables "
                    "WHERE table_schema NOT IN ('information_schema', 'mysql', 'performance_schema', 'sys')"
                ),
                "database_info_query": "SELECT VERSION() as database_version"
            },
            "MariaDB": {
                "identity_query": "SELECT NOW() as current_timestamp",
                "schema_query": (
                    "SELECT table_schema, table_name FROM information_schema.tables "
                    "WHERE table_schema NOT IN ('information_schema', 'mysql', 'performance_schema', 'sys')"
                ),
                "database_info_query": "SELECT VERSION() as database_version"
            },
            "Oracle": {
                "identity_query": "SELECT SYSTIMESTAMP as current_timestamp FROM dual",
                "schema_query": (
                    "SELECT owner, table_name FROM all_tables "
                    "WHERE owner NOT IN ('SYS', 'SYSTEM')"
                ),
                "database_info_query": (
                    "SELECT banner as database_version FROM v$version "
                    "WHERE rownum = 1"
                )
            },
            "SQL Server": {
                "identity_query": "SELECT GETDATE() as current_timestamp",
                "schema_query": (
                    "SELECT table_schema, table_name FROM information_schema.tables "
                    "WHERE table_schema NOT IN ('sys', 'INFORMATION_SCHEMA')"
                ),
                "database_info_query": "SELECT @@VERSION as database_version"
            },
            "DB2": {
                "identity_query": "SELECT CURRENT_TIMESTAMP as current_timestamp FROM SYSIBM.SYSDUMMY1",
                "schema_query": (
                    "SELECT table_schema, table_name FROM syscat.tables "
                    "WHERE table_schema NOT IN ('SYS', 'SYSCAT', 'SYSTOOLS')"
                ),
                "database_info_query": "SELECT service_level as database_version FROM sysibm.sysversions"
            },
            "SQLite": {
                "identity_query": "SELECT datetime('now') as current_timestamp",
                "schema_query": (
                    "SELECT name as table_name FROM sqlite_master "
                    "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                ),
                "database_info_query": "SELECT sqlite_version() as database_version"
            },
            "H2": {
                "identity_query": "SELECT CURRENT_TIMESTAMP as current_timestamp",
                "schema_query": (
                    "SELECT table_schema, table_name FROM information_schema.tables "
                    "WHERE table_schema NOT IN ('INFORMATION_SCHEMA', 'PUBLIC')"
                ),
                "database_info_query": "SELECT H2VERSION() as database_version"
            }
        }

        for db_type, queries in hardcoded_defaults.items():
            self.default_queries[db_type] = EntrypointQuerySet.from_dict(queries)

        logger.info("Loaded hardcoded default entrypoint queries")

    def save_configuration(self) -> None:
        """Save current configuration to file."""
        try:
            config_data = {
                "default_entrypoint_queries": {},
                "custom_entrypoint_queries": {}
            }

            # Save default queries
            for db_type, query_set in self.default_queries.items():
                config_data["default_entrypoint_queries"][db_type] = query_set.to_dict()

            # Save custom queries
            for query_name, query_set in self.custom_queries.items():
                config_data["custom_entrypoint_queries"][query_name] = query_set.to_dict()

            # Create config directory if it doesn't exist
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)

            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2)

            logger.info(f"Saved entrypoint queries configuration to {self.config_path}")

        except Exception as e:
            logger.error(f"Failed to save entrypoint queries configuration: {e}")
            raise

    def get_query_set(self, db_type: str, custom_name: str = None) -> Optional[EntrypointQuerySet]:
        """
        Get entrypoint query set for a database type.

        Args:
            db_type: The database type (e.g., "PostgreSQL", "MySQL")
            custom_name: Optional custom query set name to use instead of default

        Returns:
            EntrypointQuerySet if found, None otherwise
        """
        if custom_name:
            # Try custom queries first
            return self.custom_queries.get(custom_name)

        # Try default queries for the database type
        return self.default_queries.get(db_type)

    def get_query_set_or_default(self, db_type: str, custom_name: str = None) -> EntrypointQuerySet:
        """
        Get entrypoint query set for a database type, falling back to a generic set.

        Args:
            db_type: The database type
            custom_name: Optional custom query set name

        Returns:
            EntrypointQuerySet (never None - falls back to generic)
        """
        query_set = self.get_query_set(db_type, custom_name)

        if query_set:
            return query_set

        # Fallback to generic queries if specific database type not found
        generic_set = EntrypointQuerySet(
            identity_query="SELECT CURRENT_TIMESTAMP as current_timestamp",
            schema_query="SELECT table_schema, table_name FROM information_schema.tables",
            database_info_query="SELECT version() as database_version"
        )

        logger.warning(f"No entrypoint queries found for database type '{db_type}', using generic fallback")
        return generic_set

    def add_custom_query_set(self, name: str, query_set: EntrypointQuerySet) -> bool:
        """
        Add a custom entrypoint query set.

        Args:
            name: Name for the custom query set
            query_set: EntrypointQuerySet to add

        Returns:
            True if added successfully, False if name already exists
        """
        if name in self.custom_queries:
            return False

        self.custom_queries[name] = query_set
        self.save_configuration()
        return True

    def update_custom_query_set(self, name: str, query_set: EntrypointQuerySet) -> bool:
        """
        Update an existing custom entrypoint query set.

        Args:
            name: Name of the custom query set to update
            query_set: New EntrypointQuerySet

        Returns:
            True if updated successfully, False if name doesn't exist
        """
        if name not in self.custom_queries:
            return False

        self.custom_queries[name] = query_set
        self.save_configuration()
        return True

    def remove_custom_query_set(self, name: str) -> bool:
        """
        Remove a custom entrypoint query set.

        Args:
            name: Name of the custom query set to remove

        Returns:
            True if removed successfully, False if name doesn't exist
        """
        if name not in self.custom_queries:
            return False

        del self.custom_queries[name]
        self.save_configuration()
        return True

    def list_custom_query_sets(self) -> List[str]:
        """List all custom query set names."""
        return list(self.custom_queries.keys())

    def list_supported_database_types(self) -> List[str]:
        """List all supported database types with default queries."""
        return list(self.default_queries.keys())

    def get_identity_query(self, db_type: str, custom_name: str = None) -> str:
        """Get the identity query for a database type."""
        query_set = self.get_query_set_or_default(db_type, custom_name)
        return query_set.identity_query

    def get_schema_query(self, db_type: str, custom_name: str = None) -> str:
        """Get the schema query for a database type."""
        query_set = self.get_query_set_or_default(db_type, custom_name)
        return query_set.schema_query

    def get_database_info_query(self, db_type: str, custom_name: str = None) -> str:
        """Get the database info query for a database type."""
        query_set = self.get_query_set_or_default(db_type, custom_name)
        return query_set.database_info_query

def get_default_entrypoint_query_manager() -> EntrypointQueryManager:
    """Get the default entrypoint query manager instance."""
    return EntrypointQueryManager()
