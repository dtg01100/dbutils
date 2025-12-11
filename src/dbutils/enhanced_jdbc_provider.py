"""
Enhanced JDBC Provider Registry with Qt Integration

This module enhances the JDBC provider system with Qt-specific optimizations
and DBeaver-like user experience features.
"""

import json
import logging
import os
from dataclasses import dataclass
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    import jaydebeapi
    import jpype

    HAVE_JDBC = True
except ImportError:
    HAVE_JDBC = False
    jaydebeapi = None
    jpype = None

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWidgets import QMessageBox

# Define standard categories that match common database types
STANDARD_CATEGORIES = [
    "Generic",
    "PostgreSQL",
    "MySQL",
    "MariaDB",
    "Oracle",
    "SQL Server",
    "DB2 LUW",
    "DB2 z/OS",
    "DB2 for i",
    "SQLite",
    "H2",
    "Apache Derby",
    "Firebird",
    "Informix",
    "Sybase",
    "Custom",
]

# Import configuration manager
from dbutils.config.entrypoint_query_manager import EntrypointQueryManager, get_default_entrypoint_query_manager
from dbutils.config_manager import ConfigManager, get_default_config_manager


@dataclass
class JDBCProvider:
    """Enhanced JDBC provider with Qt-friendly attributes."""

    name: str
    category: str = "Generic"
    driver_class: str = ""
    jar_path: str = ""
    url_template: str = ""  # e.g., "jdbc:db2://{host}:{port}/{database}"

    # Simplified attributes for common usage
    default_host: str = "localhost"
    default_port: int = 0  # Use 0 for no default
    default_database: str = ""
    default_user: Optional[str] = None
    default_password: Optional[str] = None

    # Advanced attributes for power users
    extra_properties: Optional[Dict[str, str]] = None

    # Entrypoint query configuration
    custom_entrypoint_query_set: Optional[str] = None


class PredefinedProviderTemplates:
    """Collection of templates for common database providers loaded from configuration."""

    # NOTE: The templates API provides convenience class methods (get_categories,
    # get_template, create_provider_from_template) so callers can use the class
    # directly (e.g., PredefinedProviderTemplates.get_categories()) for
    # backward-compatibility with previous usage patterns.

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        self.config_manager = config_manager or get_default_config_manager()
        self._templates = self._load_templates()

    def _load_templates(self) -> Dict[str, Dict]:
        """Load templates from configuration with fallback to defaults."""
        try:
            config = self.config_manager.load_configuration()
            templates = config.get("provider_templates", {})
            if templates:
                return templates
        except Exception as e:
            logger.warning(f"Failed to load provider templates from config: {e}")

        # Fallback to hardcoded defaults if config loading fails
        return {
            "PostgreSQL": {
                "driver_class": "org.postgresql.Driver",
                "url_template": "jdbc:postgresql://{host}:{port}/{database}",
                "default_port": 5432,
                "description": "PostgreSQL database connection",
            },
            "MySQL": {
                "driver_class": "com.mysql.cj.jdbc.Driver",
                "url_template": "jdbc:mysql://{host}:{port}/{database}",
                "default_port": 3306,
                "description": "MySQL database connection",
            },
            "MariaDB": {
                "driver_class": "org.mariadb.jdbc.Driver",
                "url_template": "jdbc:mariadb://{host}:{port}/{database}",
                "default_port": 3306,
                "description": "MariaDB database connection",
            },
            "Oracle": {
                "driver_class": "oracle.jdbc.OracleDriver",
                "url_template": "jdbc:oracle:thin:@//{host}:{port}/{database}",
                "default_port": 1521,
                "description": "Oracle database connection",
            },
            "SQL Server": {
                "driver_class": "com.microsoft.sqlserver.jdbc.SQLServerDriver",
                "url_template": "jdbc:sqlserver://{host}:{port};databaseName={database}",
                "default_port": 1433,
                "description": "Microsoft SQL Server connection",
            },
            "DB2 LUW": {
                "driver_class": "com.ibm.db2.jcc.DB2Driver",
                "url_template": "jdbc:db2://{host}:{port}/{database}",
                "default_port": 50000,
                "description": "IBM DB2 for Linux/Unix/Windows",
            },
            "DB2 z/OS": {
                "driver_class": "com.ibm.db2.jcc.DB2Driver",
                "url_template": "jdbc:db2://{host}:{port}/{database}",
                "default_port": 446,
                "description": "IBM DB2 for z/OS (Mainframe)",
            },
            "DB2 for i": {
                "driver_class": "com.ibm.as400.access.AS400JDBCDriver",
                "url_template": "jdbc:as400://{host}/{database}",
                "default_port": 0,
                "description": "IBM DB2 for i (AS/400, iSeries)",
            },
            "SQLite": {
                "driver_class": "org.sqlite.JDBC",
                "url_template": "jdbc:sqlite:{database}",
                "default_port": 0,
                "description": "SQLite file-based database",
            },
            "H2": {
                "driver_class": "org.h2.Driver",
                "url_template": "jdbc:h2:tcp://{host}:{port}/{database}",
                "default_port": 9092,
                "description": "H2 database connection",
            },
            "Custom": {
                "driver_class": "",
                "url_template": "jdbc:{custom}://{host}:{port}/{database}",
                "default_port": 0,
                "description": "Custom JDBC provider - configure all parameters manually",
            },
        }

    @classmethod
    def get_template(cls, category: str) -> Optional[Dict]:
        """Get a template for a specific category."""
        return cls()._templates.get(category)

    @classmethod
    def get_categories(cls) -> List[str]:
        """Get all available category names as a classmethod for backward compatibility."""
        return list(cls()._templates.keys())

    @classmethod
    def create_provider_from_template(
        cls, category: str, name: str, host: str = "localhost", database: str = ""
    ) -> Optional[JDBCProvider]:
        """Create a provider instance from a template."""
        template = cls.get_template(category)
        if not template:
            return None

        return JDBCProvider(
            name=name,
            category=category,
            driver_class=template["driver_class"],
            jar_path="",  # User needs to provide this
            url_template=template["url_template"],
            default_host=host,
            default_port=template["default_port"],
            default_database=database,
            extra_properties={},
        )


class JDBCConnection(QObject):
    """Enhanced JDBC connection with Qt async support."""

    # Qt signals for asynchronous operations
    connected = Signal()
    disconnected = Signal()
    error_occurred = Signal(str)  # Error message
    query_finished = Signal(list)  # Query results

    def __init__(self, provider: JDBCProvider, username: Optional[str] = None, password: Optional[str] = None):
        super().__init__()

        self.provider = provider
        self.username = username or provider.default_user
        self.password = password or provider.default_password
        self._connection = None

    def connect(self) -> bool:
        """Establish connection to database."""
        try:
            if not jpype or not jpype.isJVMStarted():
                # Start JVM with proper classpath
                jvm_path = jpype.getDefaultJVMPath()
                classpath = f"{self.provider.jar_path}"
                extra_cp = os.environ.get("DBUTILS_JDBC_CLASSPATH", "")
                if extra_cp:
                    classpath = f"{classpath}:{extra_cp}"

                jpype.startJVM(jvm_path, f"-Djava.class.path={classpath}")

            # Format connection URL
            url_params = {
                "host": self.provider.default_host,
                "port": self.provider.default_port,
                "database": self.provider.default_database,
            }
            url = self.provider.url_template.format(**url_params)

            # Create connection with properties
            props = {"user": self.username or "", "password": self.password or ""}
            if self.provider.extra_properties:
                props.update(self.provider.extra_properties)

            self._connection = jaydebeapi.connect(self.provider.driver_class, url, props)

            self.connected.emit()
            return True

        except Exception as e:
            error_msg = f"Connection failed: {str(e)}"
            self.error_occurred.emit(error_msg)
            return False

    def disconnect(self):
        """Close the database connection."""
        if self._connection:
            try:
                self._connection.close()
            except Exception:
                pass
            self._connection = None
            self.disconnected.emit()

    def execute_query_async(self, sql: str):
        """Execute query asynchronously using a worker thread."""
        worker = QueryWorker(self._connection, sql)
        worker.query_finished.connect(self.query_finished)
        worker.error_occurred.connect(self.error_occurred)

        thread = QThread()
        worker.moveToThread(thread)

        def cleanup():
            thread.quit()
            thread.wait()
            thread.deleteLater()
            worker.deleteLater()

        thread.started.connect(worker.run)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.finished.connect(cleanup)

        thread.start()

        # Store references to prevent garbage collection during operation
        if not hasattr(self, "_active_threads"):
            self._active_threads = []
        self._active_threads.append((thread, worker))


class QueryWorker(QObject):
    """Worker for executing database queries in background thread."""

    query_finished = Signal(list)  # Results
    error_occurred = Signal(str)  # Error message
    finished = Signal()

    def __init__(self, connection, sql: str):
        super().__init__()
        self.connection = connection
        self.sql = sql
        self._cancelled = False

    def cancel(self):
        """Request cancellation of the query."""
        self._cancelled = True

    def run(self):
        """Execute the query."""
        if self._cancelled:
            self.finished.emit()
            return

        try:
            if not self.connection:
                raise RuntimeError("No active database connection")

            cursor = self.connection.cursor()
            cursor.execute(self.sql)

            # Get column info
            columns = [desc[0] for desc in cursor.description] if cursor.description else []

            # Fetch all results
            rows = cursor.fetchall()

            # Convert to list of dictionaries
            results = []
            for row in rows:
                if self._cancelled:
                    break
                result_dict = {}
                for i, col_name in enumerate(columns):
                    result_dict[col_name] = row[i] if i < len(row) else None
                results.append(result_dict)

            if not self._cancelled:
                self.query_finished.emit(results)
        except Exception as e:
            if not self._cancelled:
                self.error_occurred.emit(str(e))
        finally:
            try:
                cursor.close()
            except Exception:
                pass
            self.finished.emit()


_REGISTRY_INSTANCES = []


class EnhancedProviderRegistry(QObject):
    """Enhanced registry with Qt integration and DBeaver-like features."""

    # Signal emitted when providers are modified
    providers_changed = Signal()

    def __init__(
        self,
        config_path: str = None,
        config_manager: Optional[ConfigManager] = None,
        entrypoint_query_manager: Optional[EntrypointQueryManager] = None,
    ):
        super().__init__()

        # Initialize configuration manager
        self.config_manager = config_manager or get_default_config_manager()

        # Initialize entrypoint query manager
        self.entrypoint_query_manager = entrypoint_query_manager or get_default_entrypoint_query_manager()

        # Default config path (allow env override for testability)
        if config_path is None:
            config_dir = os.environ.get("DBUTILS_CONFIG_DIR", os.path.expanduser("~/.config/dbutils"))
            os.makedirs(config_dir, exist_ok=True)
            config_path = os.path.join(config_dir, "jdbc_providers.json")

        self.config_path = config_path
        self.providers: Dict[str, JDBCProvider] = {}

        self._load_providers()
        # register this instance for cross-instance synchronization
        _REGISTRY_INSTANCES.append(self)

    def _load_providers(self):
        """Load providers from configuration file."""
        try:
            # Reset providers to ensure we load the file as the current source of truth
            self.providers = {}
            if os.path.exists(self.config_path):
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Convert from list/dict format to our provider dict
                if isinstance(data, list):
                    # Old format: list of provider dicts
                    for provider_data in data:
                        provider = JDBCProvider(
                            name=provider_data.get("name", "Unnamed"),
                            category=provider_data.get("category", "Generic"),
                            driver_class=provider_data.get("driver_class", ""),
                            jar_path=provider_data.get("jar_path", ""),
                            url_template=provider_data.get("url_template", ""),
                            default_host=provider_data.get("default_host", "localhost"),
                            default_port=provider_data.get("default_port", 0),
                            default_database=provider_data.get("default_database", ""),
                            default_user=provider_data.get("default_user"),
                            default_password=provider_data.get("default_password"),
                            extra_properties=provider_data.get("extra_properties", {}),
                            custom_entrypoint_query_set=provider_data.get("custom_entrypoint_query_set"),
                        )
                        self.providers[provider.name] = provider
                else:
                    # New format: dict with provider name as key
                    for name, provider_data in data.items():
                        provider = JDBCProvider(
                            name=name,
                            category=provider_data.get("category", "Generic"),
                            driver_class=provider_data.get("driver_class", ""),
                            jar_path=provider_data.get("jar_path", ""),
                            url_template=provider_data.get("url_template", ""),
                            default_host=provider_data.get("default_host", "localhost"),
                            default_port=provider_data.get("default_port", 0),
                            default_database=provider_data.get("default_database", ""),
                            default_user=provider_data.get("default_user"),
                            default_password=provider_data.get("default_password"),
                            extra_properties=provider_data.get("extra_properties", {}),
                            custom_entrypoint_query_set=provider_data.get("custom_entrypoint_query_set"),
                        )
                        self.providers[name] = provider
        except Exception as e:
            # If config loading fails, initialize with empty providers
            logger.warning(f"Could not load JDBC providers from {self.config_path}: {e}")
            self._initialize_default_providers()

    def _initialize_default_providers(self):
        """Initialize with sensible default providers from configuration."""
        try:
            config = self.config_manager.load_configuration()
            default_providers = config.get("default_providers", {})

            if default_providers:
                # Load from configuration
                for name, provider_data in default_providers.items():
                    provider = JDBCProvider(
                        name=name,
                        category=provider_data.get("category", "Generic"),
                        driver_class=provider_data.get("driver_class", ""),
                        jar_path=provider_data.get("jar_path", ""),
                        url_template=provider_data.get("url_template", ""),
                        default_host=provider_data.get("default_host", "localhost"),
                        default_port=provider_data.get("default_port", 0),
                        default_database=provider_data.get("default_database", ""),
                        default_user=provider_data.get("default_user"),
                        default_password=provider_data.get("default_password"),
                        extra_properties=provider_data.get("extra_properties", {}),
                        custom_entrypoint_query_set=provider_data.get("custom_entrypoint_query_set"),
                    )
                    self.providers[provider.name] = provider
            else:
                # Fallback to hardcoded defaults if config loading fails
                # Add a default SQLite provider for basic functionality
                sqlite_provider = JDBCProvider(
                    name="SQLite Local",
                    category="SQLite",
                    driver_class="org.sqlite.JDBC",
                    jar_path="",  # Will need to be set by user
                    url_template="jdbc:sqlite:{database}",
                    default_database="sample.db",
                    extra_properties={},
                )
                self.providers[sqlite_provider.name] = sqlite_provider

                # Add example for user convenience
                example_provider = JDBCProvider(
                    name="Example DB2",
                    category="DB2",
                    driver_class="com.ibm.db2.jcc.DB2Driver",
                    jar_path="/path/to/db2jcc.jar",
                    url_template="jdbc:db2://{host}:{port}/{database}",
                    default_host="localhost",
                    default_port=50000,
                    default_database="SAMPLE",
                    extra_properties={"securityMechanism": "3"},  # Example property
                )
                self.providers[example_provider.name] = example_provider

        except Exception as e:
            logger.warning(f"Failed to load default providers from config: {e}")
            # Fallback to hardcoded defaults if config loading fails
            # Add a default SQLite provider for basic functionality
            sqlite_provider = JDBCProvider(
                name="SQLite Local",
                category="SQLite",
                driver_class="org.sqlite.JDBC",
                jar_path="",  # Will need to be set by user
                url_template="jdbc:sqlite:{database}",
                default_database="sample.db",
                extra_properties={},
                custom_entrypoint_query_set=None,
            )
            self.providers[sqlite_provider.name] = sqlite_provider

            # Add example for user convenience
            example_provider = JDBCProvider(
                name="Example DB2",
                category="DB2",
                driver_class="com.ibm.db2.jcc.DB2Driver",
                jar_path="/path/to/db2jcc.jar",
                url_template="jdbc:db2://{host}:{port}/{database}",
                default_host="localhost",
                default_port=50000,
                default_database="SAMPLE",
                extra_properties={"securityMechanism": "3"},  # Example property
                custom_entrypoint_query_set=None,
            )
            self.providers[example_provider.name] = example_provider

    def save_providers(self):
        """Save providers to configuration file."""
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)

            # Convert to dict format for saving
            data = {}
            for name, provider in self.providers.items():
                data[name] = {
                    "name": provider.name,
                    "category": provider.category,
                    "driver_class": provider.driver_class,
                    "jar_path": provider.jar_path,
                    "url_template": provider.url_template,
                    "default_host": provider.default_host,
                    "default_port": provider.default_port,
                    "default_database": provider.default_database,
                    "default_user": provider.default_user,
                    "default_password": provider.default_password,
                    "extra_properties": provider.extra_properties or {},
                    "custom_entrypoint_query_set": provider.custom_entrypoint_query_set,
                }

            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            self.providers_changed.emit()
            # Notify and reload other registry instances to keep them in sync
            for inst in _REGISTRY_INSTANCES:
                try:
                    if inst is not self:
                        inst._load_providers()
                except Exception:
                    pass
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Failed to save providers: {e}")

    def add_provider(self, provider: JDBCProvider) -> bool:
        """Add a new provider."""
        if provider.name in self.providers:
            return False  # Provider already exists

        self.providers[provider.name] = provider
        self.save_providers()
        return True

    def update_provider(self, provider: JDBCProvider) -> bool:
        """Update an existing provider."""
        if provider.name not in self.providers:
            return False  # Provider doesn't exist

        self.providers[provider.name] = provider
        self.save_providers()
        return True

    def remove_provider(self, name: str) -> bool:
        """Remove a provider by name."""
        if name in self.providers:
            del self.providers[name]
            self.save_providers()
            return True
        return False

    def get_provider(self, name: str) -> Optional[JDBCProvider]:
        """Get a provider by name."""
        return self.providers.get(name)

    def list_providers(self) -> List[JDBCProvider]:
        """Get all providers."""
        return list(self.providers.values())

    def list_names(self) -> List[str]:
        """Get list of provider names for compatibility with older code/tests."""
        return list(self.providers.keys())

    def get_providers_by_category(self, category: str) -> List[JDBCProvider]:
        """Get all providers of a specific category."""
        return [p for p in self.providers.values() if p.category == category]

    def create_connection(
        self, provider_name: str, username: str = None, password: str = None
    ) -> Optional[JDBCConnection]:
        """Create a connection object for a provider."""
        provider = self.get_provider(provider_name)
        if not provider:
            return None

        return JDBCConnection(provider, username, password)

    def get_entrypoint_query_set(self, provider_name: str) -> Optional[Dict[str, str]]:
        """
        Get the entrypoint query set for a provider.

        Args:
            provider_name: Name of the provider

        Returns:
            Dictionary with entrypoint queries or None if provider not found
        """
        provider = self.get_provider(provider_name)
        if not provider:
            return None

        # Get the appropriate query set based on provider category and custom settings
        query_set = self.entrypoint_query_manager.get_query_set_or_default(
            provider.category, provider.custom_entrypoint_query_set
        )

        return query_set.to_dict()

    def get_identity_query(self, provider_name: str) -> Optional[str]:
        """Get the identity query for a provider."""
        query_set = self.get_entrypoint_query_set(provider_name)
        return query_set["identity_query"] if query_set else None

    def get_schema_query(self, provider_name: str) -> Optional[str]:
        """Get the schema query for a provider."""
        query_set = self.get_entrypoint_query_set(provider_name)
        return query_set["schema_query"] if query_set else None

    def get_database_info_query(self, provider_name: str) -> Optional[str]:
        """Get the database info query for a provider."""
        query_set = self.get_entrypoint_query_set(provider_name)
        return query_set["database_info_query"] if query_set else None

    def list_available_entrypoint_query_sets(self) -> List[str]:
        """List all available entrypoint query sets (default + custom)."""
        default_sets = self.entrypoint_query_manager.list_supported_database_types()
        custom_sets = self.entrypoint_query_manager.list_custom_query_sets()
        return default_sets + custom_sets

    def add_custom_entrypoint_query_set(self, name: str, query_set: Dict[str, str]) -> bool:
        """
        Add a custom entrypoint query set.

        Args:
            name: Name for the custom query set
            query_set: Dictionary with identity_query, schema_query, database_info_query

        Returns:
            True if added successfully, False if name already exists
        """
        from dbutils.config.entrypoint_query_manager import EntrypointQuerySet

        query_set_obj = EntrypointQuerySet.from_dict(query_set)
        return self.entrypoint_query_manager.add_custom_query_set(name, query_set_obj)

    def update_custom_entrypoint_query_set(self, name: str, query_set: Dict[str, str]) -> bool:
        """
        Update an existing custom entrypoint query set.

        Args:
            name: Name of the custom query set to update
            query_set: New dictionary with query definitions

        Returns:
            True if updated successfully, False if name doesn't exist
        """
        from dbutils.config.entrypoint_query_manager import EntrypointQuerySet

        query_set_obj = EntrypointQuerySet.from_dict(query_set)
        return self.entrypoint_query_manager.update_custom_query_set(name, query_set_obj)

    def remove_custom_entrypoint_query_set(self, name: str) -> bool:
        """
        Remove a custom entrypoint query set.

        Args:
            name: Name of the custom query set to remove

        Returns:
            True if removed successfully, False if name doesn't exist
        """
        return self.entrypoint_query_manager.remove_custom_query_set(name)
