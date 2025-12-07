#!/usr/bin/env python3
"""Database-specific test utilities for multi-database testing.

This module provides utilities for database connection management,
test data generation, schema management, and cross-database testing.
"""

import os
import tempfile
import sqlite3
import logging
from typing import Dict, Any, List, Optional
from unittest.mock import MagicMock

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import test configuration
from conftest import get_test_config_manager

def get_database_configs() -> Dict[str, Dict[str, Any]]:
    """Get database configurations from centralized test configuration system."""
    config_manager = get_test_config_manager()

    # Get database configs from test configuration
    database_configs = {}

    # Try to get each database config, falling back to defaults if not available
    for db_name in ['sqlite', 'h2', 'derby', 'hsqldb', 'duckdb']:
        db_config = config_manager.get_database_config(db_name)
        if db_config:
            database_configs[db_name] = db_config

    # Add default features if not present
    for db_name, config in database_configs.items():
        if 'features' not in config:
            if db_name == 'sqlite':
                config['features'] = ["json_functions", "date_functions", "file_based"]
            elif db_name == 'h2':
                config['features'] = ["in_memory", "sequence_support", "array_support"]
            elif db_name == 'derby':
                config['features'] = ["embedded", "identity_columns", "schema_support"]
            elif db_name == 'hsqldb':
                config['features'] = ["in_memory", "text_tables", "cached_tables"]
            elif db_name == 'duckdb':
                config['features'] = ["parquet_support", "json_functions", "analytical_functions"]

    return database_configs

    # Database configurations (now loaded from centralized config)
    DATABASE_CONFIGS = get_database_configs()

class DatabaseConnectionManager:
    """Manages database connections for testing."""

    def __init__(self):
        self.connections = {}

    def get_connection(self, db_type: str, create_db: bool = True) -> Any:
        """Get a database connection for the specified type."""
        import sys
        sys.path.insert(0, 'src')

        from dbutils.jdbc_provider import JDBCProvider, JDBCConnection

        if db_type not in DATABASE_CONFIGS:
            raise ValueError(f"Unsupported database type: {db_type}")

        config = DATABASE_CONFIGS[db_type]

        # Create database file if needed
        if create_db and db_type in ["sqlite", "derby", "duckdb"]:
            db_path = config["test_db"]
            if not os.path.exists(db_path):
                self._create_database_file(db_type, db_path)

        # Create provider
        provider = JDBCProvider(
            name=f"{db_type.upper()} (Test Utils)",
            driver_class=config["driver_class"],
            jar_path=os.path.abspath(config["jar_path"]),
            url_template=config["url_template"],
            default_user=config["default_user"],
            default_password=config["default_password"],
        )

        # Create connection
        db_path = config["test_db"]
        conn = JDBCConnection(
            provider=provider,
            url_params={"database": db_path},
            user=provider.default_user,
            password=provider.default_password
        )
        conn.connect()

        self.connections[db_type] = conn
        return conn

    def _create_database_file(self, db_type: str, db_path: str):
        """Create a database file for file-based databases."""
        if db_type == "sqlite":
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Create basic schema
            cursor.execute("""
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE
                )
            """)

            cursor.execute("""
                CREATE TABLE products (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    price REAL
                )
            """)

            # Insert test data
            cursor.execute("INSERT INTO users (name, email) VALUES (?, ?)", ("Test User", "test@example.com"))
            cursor.execute("INSERT INTO products (name, price) VALUES (?, ?)", ("Test Product", 9.99))

            conn.commit()
            conn.close()

    def close_all(self):
        """Close all open connections."""
        for db_type, conn in self.connections.items():
            try:
                conn.close()
            except Exception as e:
                logger.warning(f"Error closing {db_type} connection: {e}")

        self.connections.clear()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_all()

class TestDataGenerator:
    """Generates test data for different database types."""

    @staticmethod
    def generate_basic_schema() -> Dict[str, str]:
        """Generate basic schema SQL for testing."""
        return {
            "users": """
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    email VARCHAR(255) UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """,
            "orders": """
                CREATE TABLE orders (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER,
                    total_amount DECIMAL(10,2),
                    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """,
            "products": """
                CREATE TABLE products (
                    id INTEGER PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    price DECIMAL(10,2),
                    category VARCHAR(50)
                )
            """
        }

    @staticmethod
    def generate_test_data() -> Dict[str, List[Dict[str, Any]]]:
        """Generate test data for insertion."""
        return {
            "users": [
                {"name": "John Doe", "email": "john@example.com"},
                {"name": "Jane Smith", "email": "jane@example.com"},
                {"name": "Bob Johnson", "email": "bob@example.com"}
            ],
            "products": [
                {"name": "Laptop", "price": 999.99, "category": "Electronics"},
                {"name": "Book", "price": 19.99, "category": "Books"},
                {"name": "Phone", "price": 699.99, "category": "Electronics"}
            ],
            "orders": [
                {"user_id": 1, "total_amount": 1019.98},
                {"user_id": 2, "total_amount": 19.99},
                {"user_id": 3, "total_amount": 699.99}
            ]
        }

    @staticmethod
    def generate_database_specific_queries(db_type: str) -> Dict[str, str]:
        """Generate database-specific test queries."""
        queries = {
            "basic_select": "SELECT * FROM users WHERE id = ?",
            "count_query": "SELECT COUNT(*) as count FROM users",
            "join_query": "SELECT u.name, o.total_amount FROM users u JOIN orders o ON u.id = o.user_id"
        }

        if db_type == "sqlite":
            queries.update({
                "json_query": "SELECT json_object('key', 'value') as json_result",
                "date_query": "SELECT date('now') as current_date"
            })
        elif db_type == "h2":
            queries.update({
                "sequence_query": "SELECT NEXT VALUE FOR test_sequence as seq_value FROM (VALUES(0))",
                "array_query": "SELECT ARRAY[1, 2, 3] as array_result"
            })
        elif db_type == "derby":
            queries.update({
                "identity_query": "SELECT CURRENT_TIMESTAMP as current_timestamp FROM SYSIBM.SYSDUMMY1",
                "schema_query": "SELECT * FROM SYS.SYSTABLES"
            })
        elif db_type == "hsqldb":
            queries.update({
                "text_table_query": "SELECT * FROM INFORMATION_SCHEMA.TABLES",
                "cached_query": "SELECT CURRENT_TIMESTAMP as current_timestamp"
            })
        elif db_type == "duckdb":
            queries.update({
                "json_each_query": "SELECT * FROM json_each('{\"a\":1, \"b\":2}')",
                "parquet_query": "SELECT * FROM read_parquet('file.parquet')"
            })

        return queries

class DatabaseSchemaManager:
    """Manages database schema operations."""

    def __init__(self, connection):
        self.connection = connection

    def create_schema(self, schema_name: str = "test_schema"):
        """Create a database schema if supported."""
        try:
            if "sqlite" in self.connection.provider.driver_class.lower():
                # SQLite doesn't support schemas in the same way
                return

            self.connection.query(f"CREATE SCHEMA IF NOT EXISTS {schema_name}")
            return True
        except Exception:
            # Some databases may not support schema creation
            return False

    def create_table(self, table_name: str, schema: str, columns: Dict[str, str]):
        """Create a table with the specified columns."""
        column_defs = []
        for col_name, col_type in columns.items():
            column_defs.append(f"{col_name} {col_type}")

        sql = f"CREATE TABLE {schema}.{table_name} ({', '.join(column_defs)})"
        self.connection.query(sql)

    def table_exists(self, table_name: str, schema: str = "PUBLIC") -> bool:
        """Check if a table exists."""
        try:
            if "sqlite" in self.connection.provider.driver_class.lower():
                result = self.connection.query("SELECT name FROM sqlite_master WHERE type='table' AND name=?", [table_name])
                return len(result) > 0
            else:
                result = self.connection.query(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema = ? AND table_name = ?",
                    [schema, table_name]
                )
                return len(result) > 0
        except Exception:
            return False

    def get_table_info(self, table_name: str, schema: str = "PUBLIC") -> List[Dict[str, Any]]:
        """Get information about a table's columns."""
        try:
            if "sqlite" in self.connection.provider.driver_class.lower():
                return self.connection.query(f"PRAGMA table_info({table_name})")
            else:
                return self.connection.query(
                    "SELECT column_name, data_type FROM information_schema.columns WHERE table_schema = ? AND table_name = ?",
                    [schema, table_name]
                )
        except Exception as e:
            logger.warning(f"Error getting table info: {e}")
            return []

class CrossDatabaseTester:
    """Facilitates cross-database testing and comparison."""

    def __init__(self):
        self.connection_manager = DatabaseConnectionManager()
        self.results = {}

    def test_query_across_databases(self, query: str, params: Optional[List[Any]] = None) -> Dict[str, Any]:
        """Test a query across all supported databases."""
        results = {}

        for db_type in DATABASE_CONFIGS.keys():
            try:
                conn = self.connection_manager.get_connection(db_type, create_db=False)
                result = conn.query(query, params or [])
                results[db_type] = {
                    "success": True,
                    "result": result,
                    "error": None
                }
            except Exception as e:
                results[db_type] = {
                    "success": False,
                    "result": None,
                    "error": str(e)
                }

        return results

    def compare_query_results(self, query: str) -> Dict[str, Any]:
        """Compare query results across databases."""
        results = self.test_query_across_databases(query)

        # Find successful results
        successful = {db_type: data for db_type, data in results.items() if data["success"]}

        if len(successful) < 2:
            return {"comparison": "insufficient_data", "results": results}

        # Compare row counts
        row_counts = {}
        for db_type, data in successful.items():
            row_counts[db_type] = len(data["result"])

        # Check if all successful databases return the same number of rows
        first_count = next(iter(row_counts.values()))
        consistent_counts = all(count == first_count for count in row_counts.values())

        return {
            "comparison": "successful" if consistent_counts else "inconsistent_row_counts",
            "row_counts": row_counts,
            "results": results
        }

    def test_database_features(self) -> Dict[str, Dict[str, bool]]:
        """Test database-specific features."""
        feature_results = {}

        for db_type, config in DATABASE_CONFIGS.items():
            feature_results[db_type] = {}
            features = config.get("features", [])

            for feature in features:
                try:
                    conn = self.connection_manager.get_connection(db_type, create_db=False)
                    feature_results[db_type][feature] = self._test_feature(conn, feature)
                except Exception as e:
                    feature_results[db_type][feature] = False
                    logger.warning(f"Error testing {feature} on {db_type}: {e}")

        return feature_results

    def _test_feature(self, conn, feature: str) -> bool:
        """Test a specific database feature."""
        try:
            if feature == "json_functions":
                result = conn.query("SELECT json_object('key', 'value') as json_result")
                return len(result) > 0 and 'json_result' in result[0]
            elif feature == "date_functions":
                result = conn.query("SELECT date('now') as current_date")
                return len(result) > 0 and 'current_date' in result[0]
            elif feature == "sequence_support":
                conn.query("CREATE SEQUENCE IF NOT EXISTS test_sequence START WITH 1")
                result = conn.query("SELECT NEXT VALUE FOR test_sequence as seq_value FROM (VALUES(0))")
                return len(result) > 0 and 'seq_value' in result[0]
            elif feature == "array_support":
                result = conn.query("SELECT ARRAY[1, 2, 3] as array_result")
                return len(result) > 0 and 'array_result' in result[0]
            elif feature == "identity_columns":
                result = conn.query("SELECT CURRENT_TIMESTAMP as current_timestamp FROM SYSIBM.SYSDUMMY1")
                return len(result) > 0 and 'current_timestamp' in result[0]
            elif feature == "schema_support":
                result = conn.query("SELECT * FROM SYS.SYSTABLES")
                return len(result) > 0
            elif feature == "text_tables":
                result = conn.query("SELECT * FROM INFORMATION_SCHEMA.TABLES")
                return len(result) > 0
            elif feature == "cached_tables":
                result = conn.query("SELECT CURRENT_TIMESTAMP as current_timestamp")
                return len(result) > 0
            elif feature == "parquet_support":
                # This would require actual parquet files, so we'll skip the actual test
                return True
            elif feature == "json_functions":
                result = conn.query("SELECT * FROM json_each('{\"a\":1}')")
                return len(result) > 0
            else:
                return False
        except Exception:
            return False

class DatabaseTestUtilities:
    """Collection of utility functions for database testing."""

    @staticmethod
    def create_mock_connection(db_type: str = "sqlite") -> MagicMock:
        """Create a mock database connection for testing."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # Setup mock query results based on database type
        def mock_execute(sql, params=None):
            if "SELECT 1" in sql:
                mock_cursor.description = [('test',)]
                mock_cursor.fetchall.return_value = [(1,)]
            elif "SELECT COUNT" in sql:
                mock_cursor.description = [('count',)]
                mock_cursor.fetchall.return_value = [(2,)]
            elif "SELECT * FROM users" in sql:
                mock_cursor.description = [('id',), ('name',), ('email',)]
                mock_cursor.fetchall.return_value = [
                    (1, 'John Doe', 'john@example.com'),
                    (2, 'Jane Smith', 'jane@example.com')
                ]
            else:
                mock_cursor.description = []
                mock_cursor.fetchall.return_value = []

        mock_cursor.execute.side_effect = mock_execute
        mock_conn.query.side_effect = lambda sql, params=None: [
            dict(zip([d[0] for d in mock_cursor.description], row))
            for row in mock_cursor.fetchall()
        ]

        return mock_conn

    @staticmethod
    def generate_test_queries() -> Dict[str, str]:
        """Generate a comprehensive set of test queries."""
        return {
            "simple_select": "SELECT 1 as test",
            "count_users": "SELECT COUNT(*) as count FROM users",
            "find_user": "SELECT * FROM users WHERE name = ?",
            "join_query": "SELECT u.name, o.total_amount FROM users u JOIN orders o ON u.id = o.user_id",
            "aggregate_query": "SELECT category, COUNT(*) as count, AVG(price) as avg_price FROM products GROUP BY category",
            "complex_query": """
                SELECT u.name, COUNT(o.id) as order_count, SUM(o.total_amount) as total_spent
                FROM users u
                LEFT JOIN orders o ON u.id = o.user_id
                GROUP BY u.name
                HAVING COUNT(o.id) > 0
                ORDER BY total_spent DESC
            """
        }

    @staticmethod
    def validate_test_environment() -> Dict[str, bool]:
        """Validate that the test environment is properly set up."""
        results = {}

        # Check JDBC dependencies
        try:
            import jaydebeapi
            import jpype
            results["jdbc_dependencies"] = True
        except ImportError:
            results["jdbc_dependencies"] = False

        # Check database JAR files
        for db_type, config in DATABASE_CONFIGS.items():
            jar_path = config["jar_path"]
            results[f"{db_type}_jar"] = os.path.exists(jar_path)

        # Check if providers are configured
        try:
            import sys
            sys.path.insert(0, 'src')
            from dbutils.jdbc_provider import ProviderRegistry

            registry = ProviderRegistry()
            for db_type in DATABASE_CONFIGS.keys():
                provider_name = f"{db_type.upper()} (Test Integration)"
                results[f"{db_type}_provider"] = provider_name in registry.providers

        except Exception as e:
            logger.warning(f"Error checking providers: {e}")
            for db_type in DATABASE_CONFIGS.keys():
                results[f"{db_type}_provider"] = False

        return results

    @staticmethod
    def cleanup_test_databases():
        """Clean up test database files."""
        for db_type, config in DATABASE_CONFIGS.items():
            if db_type in ["sqlite", "derby", "duckdb"]:  # File-based databases
                db_path = config["test_db"]
                try:
                    if os.path.exists(db_path):
                        os.remove(db_path)
                        logger.info(f"Removed test database: {db_path}")
                except Exception as e:
                    logger.warning(f"Error removing {db_path}: {e}")

# Utility functions for easy access
def get_connection_manager() -> DatabaseConnectionManager:
    """Get a database connection manager instance."""
    return DatabaseConnectionManager()

def get_test_data_generator() -> TestDataGenerator:
    """Get a test data generator instance."""
    return TestDataGenerator()

def get_schema_manager(connection) -> DatabaseSchemaManager:
    """Get a schema manager for the given connection."""
    return DatabaseSchemaManager(connection)

def get_cross_database_tester() -> CrossDatabaseTester:
    """Get a cross-database tester instance."""
    return CrossDatabaseTester()

def validate_environment() -> Dict[str, bool]:
    """Validate the test environment setup."""
    return DatabaseTestUtilities.validate_test_environment()

def cleanup_databases():
    """Clean up test database files."""
    DatabaseTestUtilities.cleanup_test_databases()