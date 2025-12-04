"""
Enhanced JDBC Provider Registry with Qt Integration

This module enhances the JDBC provider system with Qt-specific optimizations
and DBeaver-like user experience features.
"""

import json
import os
from dataclasses import dataclass
from typing import Dict, List, Optional

try:
    import jaydebeapi
    import jpype
    HAVE_JDBC = True
except ImportError:
    HAVE_JDBC = False
    jaydebeapi = None
    jpype = None

from PySide6.QtCore import QObject, Signal, QThread
from PySide6.QtWidgets import QMessageBox


# Define standard categories that match common database types
STANDARD_CATEGORIES = [
    "Generic",
    "PostgreSQL",
    "MySQL",
    "MariaDB", 
    "Oracle",
    "SQL Server",
    "DB2",
    "SQLite",
    "H2",
    "Apache Derby",
    "Firebird",
    "Informix",
    "Sybase"
]


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


class PredefinedProviderTemplates:
    """Collection of templates for common database providers."""
    
    TEMPLATES = {
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
        "MariaDB": {
            "driver_class": "org.mariadb.jdbc.Driver",
            "url_template": "jdbc:mariadb://{host}:{port}/{database}",
            "default_port": 3306,
            "description": "MariaDB database connection"
        },
        "Oracle": {
            "driver_class": "oracle.jdbc.OracleDriver",
            "url_template": "jdbc:oracle:thin:@//{host}:{port}/{database}",
            "default_port": 1521,
            "description": "Oracle database connection"
        },
        "SQL Server": {
            "driver_class": "com.microsoft.sqlserver.jdbc.SQLServerDriver",
            "url_template": "jdbc:sqlserver://{host}:{port};databaseName={database}",
            "default_port": 1433,
            "description": "Microsoft SQL Server connection"
        },
        "DB2": {
            "driver_class": "com.ibm.db2.jcc.DB2Driver",
            "url_template": "jdbc:db2://{host}:{port}/{database}",
            "default_port": 50000,
            "description": "IBM DB2 database connection"
        },
        "SQLite": {
            "driver_class": "org.sqlite.JDBC",
            "url_template": "jdbc:sqlite:{database}",
            "default_port": 0,
            "description": "SQLite file-based database"
        },
        "H2": {
            "driver_class": "org.h2.Driver",
            "url_template": "jdbc:h2:tcp://{host}:{port}/{database}",
            "default_port": 9092,
            "description": "H2 database connection"
        }
    }

    @classmethod
    def get_template(cls, category: str) -> Optional[Dict]:
        """Get a template for a specific category."""
        return cls.TEMPLATES.get(category)
    
    @classmethod
    def get_categories(cls) -> List[str]:
        """Get all available category names."""
        return list(cls.TEMPLATES.keys())
    
    @classmethod
    def create_provider_from_template(cls, category: str, name: str, host: str = "localhost", 
                                     database: str = "") -> Optional[JDBCProvider]:
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
            extra_properties={}
        )


class JDBCConnection(QObject):
    """Enhanced JDBC connection with Qt async support."""
    
    # Qt signals for asynchronous operations
    connected = Signal()
    disconnected = Signal()
    error_occurred = Signal(str)  # Error message
    query_finished = Signal(list)  # Query results
    
    def __init__(self, provider: JDBCProvider, username: Optional[str] = None, 
                 password: Optional[str] = None):
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
                'host': self.provider.default_host,
                'port': self.provider.default_port,
                'database': self.provider.default_database
            }
            url = self.provider.url_template.format(**url_params)
            
            # Create connection with properties
            props = {"user": self.username or "", "password": self.password or ""}
            if self.provider.extra_properties:
                props.update(self.provider.extra_properties)
            
            self._connection = jaydebeapi.connect(
                self.provider.driver_class,
                url,
                props
            )
            
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
        if not hasattr(self, '_active_threads'):
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


class EnhancedProviderRegistry(QObject):
    """Enhanced registry with Qt integration and DBeaver-like features."""
    
    # Signal emitted when providers are modified
    providers_changed = Signal()
    
    def __init__(self, config_path: str = None):
        super().__init__()
        
        # Default config path
        if config_path is None:
            config_dir = os.path.expanduser("~/.config/dbutils")
            os.makedirs(config_dir, exist_ok=True)
            config_path = os.path.join(config_dir, "jdbc_providers.json")
        
        self.config_path = config_path
        self.providers: Dict[str, JDBCProvider] = {}
        
        self._load_providers()
    
    def _load_providers(self):
        """Load providers from configuration file."""
        try:
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
                            extra_properties=provider_data.get("extra_properties", {})
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
                            extra_properties=provider_data.get("extra_properties", {})
                        )
                        self.providers[name] = provider
        except Exception as e:
            # If config loading fails, initialize with empty providers
            print(f"Warning: Could not load JDBC providers from {self.config_path}: {e}")
            self._initialize_default_providers()
    
    def _initialize_default_providers(self):
        """Initialize with sensible default providers."""
        # Add a default SQLite provider for basic functionality
        sqlite_provider = JDBCProvider(
            name="SQLite Local",
            category="SQLite",
            driver_class="org.sqlite.JDBC",
            jar_path="",  # Will need to be set by user
            url_template="jdbc:sqlite:{database}",
            default_database="sample.db",
            extra_properties={}
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
            extra_properties={"securityMechanism": "3"}  # Example property
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
                    "extra_properties": provider.extra_properties or {}
                }
            
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
                
            self.providers_changed.emit()
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
    
    def get_providers_by_category(self, category: str) -> List[JDBCProvider]:
        """Get all providers of a specific category."""
        return [p for p in self.providers.values() if p.category == category]
    
    def create_connection(self, provider_name: str, username: str = None, 
                         password: str = None) -> Optional[JDBCConnection]:
        """Create a connection object for a provider."""
        provider = self.get_provider(provider_name)
        if not provider:
            return None
            
        return JDBCConnection(provider, username, password)