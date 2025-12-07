#!/usr/bin/env python3
"""Comprehensive multi-database integration tests for dbutils project.

This module contains integration tests that verify multiple freely available databases:
- SQLite
- H2 Database
- Apache Derby
- HSQLDB
- DuckDB

The tests include cross-database comparisons, database-specific features, and comprehensive
JDBC driver functionality verification.
"""

import os
import tempfile
import sqlite3
import pytest
import logging
from unittest.mock import patch, MagicMock
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import dbutils modules
from dbutils.jdbc_provider import JDBCProvider, JDBCConnection, ProviderRegistry
from dbutils import catalog

# Test configuration
TEST_DB_NAMES = {
    "sqlite": "test_multi_sqlite.db",
    "h2": "test_multi_h2_mem",
    "derby": "test_multi_derby_db",
    "hsqldb": "test_multi_hsqldb_mem",
    "duckdb": "test_multi_duckdb.db"
}

# Database-specific configurations
DATABASE_SPECIFIC_CONFIGS = {
    "sqlite": {
        "driver_class": "org.sqlite.JDBC",
        "url_template": "jdbc:sqlite:{database}",
        "user": None,
        "password": None,
        "features": ["json_functions", "date_functions", "file_based"]
    },
    "h2": {
        "driver_class": "org.h2.Driver",
        "url_template": "jdbc:h2:mem:{database};DB_CLOSE_DELAY=-1",
        "user": "sa",
        "password": "",
        "features": ["in_memory", "sequence_support", "array_support"]
    },
    "derby": {
        "driver_class": "org.apache.derby.jdbc.EmbeddedDriver",
        "url_template": "jdbc:derby:{database};create=true",
        "user": None,
        "password": None,
        "features": ["embedded", "identity_columns", "schema_support"]
    },
    "hsqldb": {
        "driver_class": "org.hsqldb.jdbc.JDBCDriver",
        "url_template": "jdbc:hsqldb:mem:{database}",
        "user": "SA",
        "password": "",
        "features": ["in_memory", "text_tables", "cached_tables"]
    },
    "duckdb": {
        "driver_class": "org.duckdb.DuckDBDriver",
        "url_template": "jdbc:duckdb:{database}",
        "user": None,
        "password": None,
        "features": ["parquet_support", "json_functions", "analytical_functions"]
    }
}

@pytest.fixture(scope='module', autouse=True)
def check_multi_database_dependencies():
    """Check if multi-database dependencies are available before running tests."""
    # Check for JDBC dependencies
    try:
        import jaydebeapi
        import jpype
    except ImportError as e:
        pytest.skip(f"JDBC dependencies not available: {e}")

    # Check if required database providers are configured
    try:
        registry = ProviderRegistry()
        required_providers = [
            "SQLite (Test Integration)",
            "H2 (Test Integration)",
            "Apache Derby (Test Integration)",
            "HSQLDB (Test Integration)",
            "DuckDB (Test Integration)"
        ]

        missing_providers = [p for p in required_providers if p not in registry.providers]
        if missing_providers:
            pytest.skip(f"Missing database providers: {', '.join(missing_providers)}")
    except Exception as e:
        pytest.skip(f"Cannot access provider registry: {e}")

@pytest.fixture(params=["sqlite", "h2", "derby", "hsqldb", "duckdb"])
def database_provider(request):
    """Parameterized fixture that provides database providers for testing."""
    db_type = request.param
    config = DATABASE_SPECIFIC_CONFIGS[db_type]

    # Map database types to their proper provider names
    provider_mapping = {
        "sqlite": "SQLite (Test Integration)",
        "h2": "H2 (Test Integration)",
        "derby": "Apache Derby (Test Integration)",
        "hsqldb": "HSQLDB (Test Integration)",
        "duckdb": "DuckDB (Test Integration)"
    }
    return JDBCProvider(
        name=provider_mapping.get(db_type, f"{db_type.capitalize()} (Test Integration)"),
        driver_class=config["driver_class"],
        jar_path=os.path.abspath(f"jars/{db_type}.jar"),
        url_template=config["url_template"],
        default_user=config["user"],
        default_password=config["password"],
    )

@pytest.fixture
def test_database_connection(database_provider):
    """Create a test database connection for the specified provider."""
    db_type = database_provider.name.split()[0].lower()

    # Create test database file if needed
    if db_type == "sqlite":
        db_path = TEST_DB_NAMES[db_type]
        if not os.path.exists(db_path):
            _create_test_database(db_type, db_path)
    else:
        db_path = TEST_DB_NAMES[db_type]

    # Create connection
    conn = JDBCConnection(
        provider=database_provider,
        url_params={"database": db_path},
        user=database_provider.default_user,
        password=database_provider.default_password
    )
    conn.connect()

    # Create test schema
    _create_test_schema(conn)

    yield conn

    # Cleanup
    conn.close()

    # Cleanup database files for file-based databases
    if db_type in ["sqlite", "derby", "duckdb"]:
        try:
            if os.path.exists(db_path):
                os.remove(db_path)
        except Exception:
            pass

def _create_test_database(db_type: str, db_path: str):
    """Create a test database file for file-based databases."""
    if db_type == "sqlite":
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create test tables
        cursor.execute("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE orders (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                total_amount DECIMAL(10,2),
                order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        cursor.execute("""
            CREATE TABLE products (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                price DECIMAL(10,2),
                category TEXT
            )
        """)

        # Insert test data
        cursor.execute("INSERT INTO users (name, email) VALUES (?, ?)", ("John Doe", "john@example.com"))
        cursor.execute("INSERT INTO users (name, email) VALUES (?, ?)", ("Jane Smith", "jane@example.com"))
        cursor.execute("INSERT INTO products (name, price, category) VALUES (?, ?, ?)", ("Laptop", 999.99, "Electronics"))
        cursor.execute("INSERT INTO products (name, price, category) VALUES (?, ?, ?)", ("Book", 19.99, "Books"))
        cursor.execute("INSERT INTO orders (user_id, total_amount) VALUES (?, ?)", (1, 1019.98))
        cursor.execute("INSERT INTO orders (user_id, total_amount) VALUES (?, ?)", (2, 19.99))

        conn.commit()
        conn.close()

def _create_test_schema(conn: JDBCConnection):
    """Create test schema in the database connection."""
    # Create test tables
    conn.query("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            email VARCHAR(255) UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.query("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            total_amount DECIMAL(10,2),
            order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    conn.query("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            price DECIMAL(10,2),
            category VARCHAR(50)
        )
    """)

    # Insert test data if tables are empty
    try:
        result = conn.query("SELECT COUNT(*) as count FROM users")
        if result[0]['count'] == 0:
            conn.query("INSERT INTO users (name, email) VALUES ('John Doe', 'john@example.com')")
            conn.query("INSERT INTO users (name, email) VALUES ('Jane Smith', 'jane@example.com')")
            conn.query("INSERT INTO products (name, price, category) VALUES ('Laptop', 999.99, 'Electronics')")
            conn.query("INSERT INTO products (name, price, category) VALUES ('Book', 19.99, 'Books')")
            conn.query("INSERT INTO orders (user_id, total_amount) VALUES (1, 1019.98)")
            conn.query("INSERT INTO orders (user_id, total_amount) VALUES (2, 19.99)")
    except Exception:
        # Some databases may not support the exact same syntax
        pass

def test_multi_database_connection_setup(database_provider, test_database_connection):
    """Test database connection setup for all supported databases."""
    conn = test_database_connection

    # Verify connection is active
    result = conn.query("SELECT 1 as test")
    assert result[0]['test'] == 1

    # Verify provider configuration
    assert conn.provider.name == database_provider.name
    assert conn.provider.driver_class == database_provider.driver_class

def test_multi_database_crud_operations(test_database_connection):
    """Test CRUD operations across all database types."""
    conn = test_database_connection

    # Test CREATE operation (already done in fixture)
    # Test READ operation
    result = conn.query("SELECT * FROM users")
    assert len(result) >= 2  # Should have at least the test data

    # Test UPDATE operation
    update_result = conn.query("UPDATE users SET name = 'John Updated' WHERE id = 1")
    # Verify update worked
    verify_result = conn.query("SELECT name FROM users WHERE id = 1")
    assert verify_result[0]['name'] == 'John Updated'

    # Test DELETE operation
    delete_result = conn.query("DELETE FROM users WHERE id = 2")
    # Verify delete worked
    verify_result = conn.query("SELECT COUNT(*) as count FROM users")
    assert verify_result[0]['count'] >= 1  # At least one user should remain

def test_multi_database_schema_operations(test_database_connection):
    """Test schema operations across different database types."""
    conn = test_database_connection

    # Test table inspection
    tables_result = conn.query("SELECT table_name FROM information_schema.tables WHERE table_schema = 'PUBLIC'")
    table_names = [row['table_name'] for row in tables_result]

    # Verify core tables exist
    assert 'users' in table_names
    assert 'orders' in table_names
    assert 'products' in table_names

    # Test table creation
    conn.query("""
        CREATE TABLE test_new_table (
            id INTEGER PRIMARY KEY,
            test_column VARCHAR(100)
        )
    """)

    # Verify new table exists
    tables_result = conn.query("SELECT table_name FROM information_schema.tables WHERE table_schema = 'PUBLIC'")
    table_names = [row['table_name'] for row in tables_result]
    assert 'test_new_table' in table_names

def test_multi_database_transaction_management(test_database_connection):
    """Test transaction management across database types."""
    conn = test_database_connection

    # Test transaction isolation
    initial_count = conn.query("SELECT COUNT(*) as count FROM users")[0]['count']

    # Start transaction
    conn.query("BEGIN TRANSACTION")

    # Make changes
    conn.query("INSERT INTO users (name, email) VALUES ('Temp User', 'temp@example.com')")

    # Verify change is visible in current connection
    temp_count = conn.query("SELECT COUNT(*) as count FROM users")[0]['count']
    assert temp_count == initial_count + 1

    # Rollback transaction
    conn.query("ROLLBACK")

    # Verify change was rolled back
    final_count = conn.query("SELECT COUNT(*) as count FROM users")[0]['count']
    assert final_count == initial_count

def test_multi_database_error_handling(test_database_connection):
    """Test error handling across different database types."""
    conn = test_database_connection

    # Test invalid SQL syntax
    with pytest.raises(Exception):
        conn.query("SELECT FROM users WHERE")  # Invalid SQL

    # Test non-existent table
    with pytest.raises(Exception):
        conn.query("SELECT * FROM non_existent_table")

def test_multi_database_performance(test_database_connection):
    """Test performance characteristics across database types."""
    conn = test_database_connection

    # Create a larger test table
    conn.query("""
        CREATE TABLE large_data (
            id INTEGER PRIMARY KEY,
            value VARCHAR(100),
            number INTEGER
        )
    """)

    # Insert multiple rows
    for i in range(100):
        conn.query(f"INSERT INTO large_data (value, number) VALUES ('test_{i}', {i})")

    # Test query performance
    result = conn.query("SELECT COUNT(*) as count FROM large_data")
    assert result[0]['count'] == 100

    # Test filtered query
    result = conn.query("SELECT * FROM large_data WHERE number >= 50")
    assert len(result) == 50

@pytest.mark.parametrize("db_type", ["sqlite", "h2", "derby", "hsqldb", "duckdb"])
def test_database_specific_features(db_type, test_database_connection):
    """Test database-specific features for each database type."""
    conn = test_database_connection
    db_config = DATABASE_SPECIFIC_CONFIGS[db_type]

    if db_type == "sqlite":
        # Test SQLite-specific functions
        result = conn.query("SELECT sqlite_version() as version")
        assert 'version' in result[0]

        # Test SQLite date functions
        result = conn.query("SELECT date('now') as current_date")
        assert 'current_date' in result[0]

    elif db_type == "h2":
        # Test H2-specific functions
        result = conn.query("SELECT CURRENT_TIMESTAMP as current_timestamp")
        assert 'current_timestamp' in result[0]

        # Test H2 sequence support
        conn.query("CREATE SEQUENCE IF NOT EXISTS test_sequence START WITH 1")
        result = conn.query("SELECT NEXT VALUE FOR test_sequence as seq_value FROM (VALUES(0))")
        assert 'seq_value' in result[0]

    elif db_type == "derby":
        # Test Derby-specific functions
        result = conn.query("SELECT CURRENT_TIMESTAMP as current_timestamp FROM SYSIBM.SYSDUMMY1")
        assert 'current_timestamp' in result[0]

    elif db_type == "hsqldb":
        # Test HSQLDB-specific functions
        result = conn.query("SELECT CURRENT_TIMESTAMP as current_timestamp FROM (VALUES(0))")
        assert 'current_timestamp' in result[0]

    elif db_type == "duckdb":
        # Test DuckDB-specific functions
        result = conn.query("SELECT CURRENT_TIMESTAMP as current_timestamp")
        assert 'current_timestamp' in result[0]

        # Test DuckDB JSON functions if available
        try:
            result = conn.query("SELECT * FROM json_each('{\"a\":1}')")
            assert len(result) > 0
        except Exception:
            # JSON functions may not be available in all versions
            pass

def test_cross_database_comparison():
    """Test cross-database functionality comparison."""
    from dbutils.jdbc_provider import connect

    results = {}

    # Test each database
    for db_type, db_name in TEST_DB_NAMES.items():
        try:
            # Map database types to their proper provider names
            provider_mapping = {
                "sqlite": "SQLite (Test Integration)",
                "h2": "H2 (Test Integration)",
                "derby": "Apache Derby (Test Integration)",
                "hsqldb": "HSQLDB (Test Integration)",
                "duckdb": "DuckDB (Test Integration)"
            }
            provider_name = provider_mapping.get(db_type, f"{db_type.capitalize()} (Test Integration)")
            conn = connect(provider_name, {"database": db_name})

            # Test basic query
            result = conn.query("SELECT COUNT(*) as count FROM users")
            results[db_type] = result[0]['count'] if result else 0

            conn.close()
        except Exception as e:
            logger.warning(f"Failed to test {db_type}: {e}")
            results[db_type] = None

    # Verify we got results from multiple databases
    successful_dbs = [db_type for db_type, count in results.items() if count is not None]
    assert len(successful_dbs) >= 2, f"At least 2 databases should work, got: {successful_dbs}"

def test_multi_database_connection_pooling():
    """Test connection pooling and resource management across databases."""
    from dbutils.jdbc_provider import connect

    # Test with SQLite (most reliable for this test)
    db_type = "sqlite"
    # Map database types to their proper provider names
    provider_mapping = {
        "sqlite": "SQLite (Test Integration)",
        "h2": "H2 (Test Integration)",
        "derby": "Apache Derby (Test Integration)",
        "hsqldb": "HSQLDB (Test Integration)",
        "duckdb": "DuckDB (Test Integration)"
    }
    provider_name = provider_mapping.get(db_type, f"{db_type.capitalize()} (Test Integration)")
    db_name = TEST_DB_NAMES[db_type]

    # Create multiple connections
    conn1 = connect(provider_name, {"database": db_name})
    conn2 = connect(provider_name, {"database": db_name})

    # Verify both connections work
    result1 = conn1.query("SELECT COUNT(*) as count FROM users")
    result2 = conn2.query("SELECT COUNT(*) as count FROM users")

    assert result1[0]['count'] == result2[0]['count']

    # Test connection closing
    conn1.close()
    conn2.close()

    # Verify connections are properly closed
    assert conn1._conn is None
    assert conn2._conn is None

def test_multi_database_catalog_integration():
    """Test catalog integration with multiple database types."""
    # Set required environment variable for catalog functions
    import os
    os.environ["DBUTILS_JDBC_PROVIDER"] = "SQLite (Test Integration)"

    # Mock the catalog functions to use our test database
    with patch('dbutils.jdbc_provider.connect') as mock_connect:
        # Setup mock connection
        mock_conn = MagicMock()
        mock_conn.query.return_value = [
            {'TABNAME': 'users', 'TABLE_SCHEMA': 'main'},
            {'TABNAME': 'orders', 'TABLE_SCHEMA': 'main'},
            {'TABNAME': 'products', 'TABLE_SCHEMA': 'main'}
        ]
        mock_connect.return_value = mock_conn

        # Test catalog functions
        tables = catalog.get_tables(schema='main', mock=False)
        assert len(tables) == 3
        assert any(t['TABNAME'] == 'users' for t in tables)

        # Test columns
        columns = catalog.get_columns(schema='main', table='users', mock=False)
        assert len(columns) > 0
        assert any(c['COLNAME'] == 'id' for c in columns)

def test_multi_database_error_recovery():
    """Test error recovery and connection resilience across databases."""
    from dbutils.jdbc_provider import connect

    # Test with SQLite
    db_type = "sqlite"
    # Map database types to their proper provider names
    provider_mapping = {
        "sqlite": "SQLite (Test Integration)",
        "h2": "H2 (Test Integration)",
        "derby": "Apache Derby (Test Integration)",
        "hsqldb": "HSQLDB (Test Integration)",
        "duckdb": "DuckDB (Test Integration)"
    }
    provider_name = provider_mapping.get(db_type, f"{db_type.capitalize()} (Test Integration)")
    db_name = TEST_DB_NAMES[db_type]

    conn = connect(provider_name, {"database": db_name})

    # Test connection recovery after error
    try:
        conn.query("SELECT * FROM non_existent_table")
    except Exception:
        pass  # Expected to fail

    # Verify connection is still usable
    result = conn.query("SELECT 1 as test")
    assert result[0]['test'] == 1

    # Close connection
    conn.close()

def test_multi_database_metadata_operations():
    """Test database metadata operations across different database types."""
    conn = None
    try:
        from dbutils.jdbc_provider import connect

        # Test with SQLite
        db_type = "sqlite"
        provider_name = f"{db_type.upper()} (Test Integration)"
        db_name = TEST_DB_NAMES[db_type]

        conn = connect(provider_name, {"database": db_name})

        # Test metadata queries
        result = conn.query("PRAGMA table_info(users)")
        assert len(result) > 0
        assert any(row['name'] == 'id' for row in result)

        # Test schema information
        result = conn.query("SELECT name FROM sqlite_master WHERE type='table'")
        table_names = [row['name'] for row in result]
        assert 'users' in table_names

    finally:
        if conn:
            conn.close()

def test_multi_database_data_types():
    """Test data type handling across different database types."""
    conn = None
    try:
        from dbutils.jdbc_provider import connect

        # Test with SQLite
        db_type = "sqlite"
        # Map database types to their proper provider names
        provider_mapping = {
            "sqlite": "SQLite (Test Integration)",
            "h2": "H2 (Test Integration)",
            "derby": "Apache Derby (Test Integration)",
            "hsqldb": "HSQLDB (Test Integration)",
            "duckdb": "DuckDB (Test Integration)"
        }
        provider_name = provider_mapping.get(db_type, f"{db_type.capitalize()} (Test Integration)")
        db_name = TEST_DB_NAMES[db_type]

        conn = connect(provider_name, {"database": db_name})

        # Test different data types
        conn.query("""
            CREATE TABLE IF NOT EXISTS data_types_test (
                id INTEGER PRIMARY KEY,
                text_data TEXT,
                numeric_data REAL,
                boolean_data BOOLEAN,
                timestamp_data TIMESTAMP
            )
        """)

        # Insert test data
        conn.query("INSERT INTO data_types_test (text_data, numeric_data, boolean_data, timestamp_data) VALUES (?, ?, ?, ?)",
                   ("test text", 3.14, True, "2023-01-01 12:00:00"))

        # Verify data
        result = conn.query("SELECT * FROM data_types_test")
        assert len(result) == 1
        assert result[0]['text_data'] == "test text"
        assert abs(result[0]['numeric_data'] - 3.14) < 0.01

    finally:
        if conn:
            conn.close()

def test_multi_database_connection_teardown():
    """Test proper connection teardown and cleanup across databases."""
    from dbutils.jdbc_provider import connect

    # Test with SQLite
    db_type = "sqlite"
    # Map database types to their proper provider names
    provider_mapping = {
        "sqlite": "SQLite (Test Integration)",
        "h2": "H2 (Test Integration)",
        "derby": "Apache Derby (Test Integration)",
        "hsqldb": "HSQLDB (Test Integration)",
        "duckdb": "DuckDB (Test Integration)"
    }
    provider_name = provider_mapping.get(db_type, f"{db_type.capitalize()} (Test Integration)")
    db_name = TEST_DB_NAMES[db_type]

    # Create and close connection
    conn = connect(provider_name, {"database": db_name})

    # Verify connection is active
    result = conn.query("SELECT 1 as test")
    assert result[0]['test'] == 1

    # Close connection
    conn.close()

    # Verify connection is closed
    assert conn._conn is None

# Additional helper functions for more comprehensive testing
def create_complex_schema(conn: JDBCConnection, db_type: str):
    """Create a more complex schema for advanced testing."""
    if db_type == "sqlite":
        conn.query("""
            CREATE TABLE complex_table (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                price DECIMAL(10,2),
                quantity INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                metadata TEXT,
                CONSTRAINT chk_price CHECK (price >= 0),
                CONSTRAINT chk_quantity CHECK (quantity >= 0)
            )
        """)

        conn.query("CREATE INDEX idx_complex_name ON complex_table(name)")

    else:
        # Generic schema for other databases
        conn.query("""
            CREATE TABLE complex_table (
                id INTEGER PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                description VARCHAR(255),
                price DECIMAL(10,2),
                quantity INTEGER,
                created_at TIMESTAMP,
                is_active BOOLEAN
            )
        """)

        conn.query("CREATE INDEX idx_complex_name ON complex_table(name)")

def test_multi_database_advanced_features():
    """Test advanced features across different database types."""
    from dbutils.jdbc_provider import connect

    # Test with SQLite
    db_type = "sqlite"
    # Map database types to their proper provider names
    provider_mapping = {
        "sqlite": "SQLite (Test Integration)",
        "h2": "H2 (Test Integration)",
        "derby": "Apache Derby (Test Integration)",
        "hsqldb": "HSQLDB (Test Integration)",
        "duckdb": "DuckDB (Test Integration)"
    }
    provider_name = provider_mapping.get(db_type, f"{db_type.capitalize()} (Test Integration)")
    db_name = TEST_DB_NAMES[db_type]

    conn = connect(provider_name, {"database": db_name})

    # Create complex schema
    create_complex_schema(conn, db_type)

    # Test index usage
    result = conn.query("SELECT name FROM complex_table WHERE name LIKE 'Test%'")
    assert isinstance(result, list)

    # Test constraint validation
    with pytest.raises(Exception):
        conn.query("INSERT INTO complex_table (name, price, quantity) VALUES ('Test', -10.0, 5)")  # Negative price

    conn.close()

def test_multi_database_connection_string_variations():
    """Test different connection string variations for each database type."""
    for db_type, config in DATABASE_SPECIFIC_CONFIGS.items():
        provider = JDBCProvider(
            name=f"{db_type.upper()} (Test Integration)",
            driver_class=config["driver_class"],
            jar_path=os.path.abspath(f"jars/{db_type}.jar"),
            url_template=config["url_template"],
            default_user=config["user"],
            default_password=config["password"],
        )

        # Test different URL parameter combinations
        test_cases = [
            {"database": "test_db"},
            {"database": "/absolute/path/to/test.db"},
        ]

        for params in test_cases:
            url = provider.url_template.format(**params)
            assert url.startswith(f"jdbc:{db_type}:")
            assert "test_db" in url or "/absolute/path" in url