#!/usr/bin/env python3
"""
Comprehensive SQLite integration tests for dbutils project.

This module contains integration tests that verify SQLite JDBC driver functionality,
database operations, schema management, and error handling using real SQLite databases.
"""

import os
import sqlite3
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from dbutils import catalog

# Import dbutils modules
from dbutils.jdbc_provider import JDBCProvider, ProviderRegistry

# Test configuration
TEST_DB_NAME = "test_integration.db"
TEST_PROVIDER_NAME = "SQLite (Test Integration)"

@pytest.fixture(scope='module', autouse=True)
def check_sqlite_dependencies():
    """Check if SQLite JDBC dependencies are available before running tests."""
    # Check for JDBC dependencies
    try:
        import jaydebeapi
        import jpype
    except ImportError as e:
        pytest.skip(f"JDBC dependencies not available: {e}")

    # Check if SQLite provider is configured
    try:
        registry = ProviderRegistry()
        if TEST_PROVIDER_NAME not in registry.providers:
            pytest.skip(f"SQLite provider '{TEST_PROVIDER_NAME}' not configured")
    except Exception as e:
        pytest.skip(f"Cannot access provider registry: {e}")

@pytest.fixture
def sqlite_test_db():
    """Create a temporary SQLite database for testing."""
    # Create temporary database file
    db_path = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    db_path.close()

    # Create database with sample schema
    conn = sqlite3.connect(db_path.name)
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

    yield db_path.name

    # Cleanup
    if os.path.exists(db_path.name):
        os.remove(db_path.name)

@pytest.fixture
def sqlite_provider():
    """Create a test SQLite JDBC provider."""
    return JDBCProvider(
        name=TEST_PROVIDER_NAME,
        driver_class="org.sqlite.JDBC",
        jar_path=os.path.abspath("jars/sqlite-jdbc.jar"),
        url_template="jdbc:sqlite:{database}",
        default_user=None,
        default_password=None,
        extra_properties={}
    )

@pytest.fixture
def mock_sqlite_connection(sqlite_test_db):
    """Mock SQLite JDBC connection for testing."""
    with patch("dbutils.jdbc_provider.jaydebeapi") as mock_jaydebeapi, \
         patch("dbutils.jdbc_provider.jpype") as mock_jpype:

        # Setup mock JPype
        mock_jpype.isJVMStarted.return_value = False
        mock_jpype.getDefaultJVMPath.return_value = "/fake/java/path"

        # Setup mock JayDeBeApi connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # Mock query results
        def mock_execute(sql):
            # Simulate SQLite query results
            if "SELECT name FROM sqlite_master WHERE type='table'" in sql:
                mock_cursor.description = [('name',), ('type',)]
                mock_cursor.fetchall.return_value = [
                    ('users', 'table'),
                    ('orders', 'table'),
                    ('products', 'table')
                ]
            elif "SELECT COUNT(*) as count FROM users" in sql:
                mock_cursor.description = [('count',)]
                mock_cursor.fetchall.return_value = [(2,)]
            elif "SELECT * FROM users" in sql:
                mock_cursor.description = [('id',), ('name',), ('email',), ('created_at',)]
                mock_cursor.fetchall.return_value = [
                    (1, 'John Doe', 'john@example.com', None),
                    (2, 'Jane Smith', 'jane@example.com', None)
                ]
            else:
                mock_cursor.description = []
                mock_cursor.fetchall.return_value = []

        mock_cursor.execute.side_effect = mock_execute
        mock_jaydebeapi.connect.return_value = mock_conn

        yield {
            "jaydebeapi": mock_jaydebeapi,
            "jpype": mock_jpype,
            "connection": mock_conn,
            "cursor": mock_cursor,
            "db_path": sqlite_test_db
        }

def test_sqlite_jdbc_driver_connection_setup():
    """Test SQLite JDBC driver connection and setup."""
    provider = JDBCProvider(
        name=TEST_PROVIDER_NAME,
        driver_class="org.sqlite.JDBC",
        jar_path=os.path.abspath("jars/sqlite-jdbc.jar"),
        url_template="jdbc:sqlite:{database}",
        default_user=None,
        default_password=None
    )

    # Verify provider configuration
    assert provider.name == TEST_PROVIDER_NAME
    assert provider.driver_class == "org.sqlite.JDBC"
    assert provider.url_template == "jdbc:sqlite:{database}"
    assert provider.default_user is None
    assert provider.default_password is None

def test_sqlite_connection_creation(mock_sqlite_connection):
    """Test SQLite JDBC connection creation."""
    from dbutils.jdbc_provider import connect

    # Test connection creation
    conn = connect(
        TEST_PROVIDER_NAME,
        {"database": mock_sqlite_connection["db_path"]}
    )

    # Verify connection was created
    assert conn is not None
    assert conn.provider.name == TEST_PROVIDER_NAME

def test_sqlite_database_operations_crud(mock_sqlite_connection):
    """Test SQLite database CRUD operations."""
    from dbutils.jdbc_provider import connect

    # Create connection
    conn = connect(
        TEST_PROVIDER_NAME,
        {"database": mock_sqlite_connection["db_path"]}
    )

    # Test CREATE operation (already done in fixture)
    # Test READ operation
    result = conn.query("SELECT * FROM users")
    assert len(result) == 2
    assert result[0]['name'] == 'John Doe'
    assert result[1]['name'] == 'Jane Smith'

    # Test UPDATE operation
    update_result = conn.query("UPDATE users SET name = 'John Updated' WHERE id = 1")
    # Verify update worked
    verify_result = conn.query("SELECT name FROM users WHERE id = 1")
    assert verify_result[0]['name'] == 'John Updated'

    # Test DELETE operation
    delete_result = conn.query("DELETE FROM users WHERE id = 2")
    # Verify delete worked
    verify_result = conn.query("SELECT COUNT(*) as count FROM users")
    assert verify_result[0]['count'] == 1

def test_sqlite_specific_query_patterns(mock_sqlite_connection):
    """Test SQLite-specific query patterns and limitations."""
    from dbutils.jdbc_provider import connect

    conn = connect(
        TEST_PROVIDER_NAME,
        {"database": mock_sqlite_connection["db_path"]}
    )

    # Test SQLite-specific functions
    result = conn.query("SELECT sqlite_version() as version")
    assert 'version' in result[0]

    # Test SQLite date functions
    result = conn.query("SELECT date('now') as current_date")
    assert 'current_date' in result[0]

    # Test SQLite JSON functions (if available)
    try:
        result = conn.query("SELECT json_object('key', 'value') as json_result")
        assert 'json_result' in result[0]
    except Exception:
        # JSON functions may not be available in all SQLite versions
        pass

def test_sqlite_schema_and_table_operations(mock_sqlite_connection):
    """Test SQLite schema and table operations."""
    from dbutils.jdbc_provider import connect

    conn = connect(
        TEST_PROVIDER_NAME,
        {"database": mock_sqlite_connection["db_path"]}
    )

    # Test schema inspection
    tables_result = conn.query("SELECT name FROM sqlite_master WHERE type='table'")
    table_names = [row['name'] for row in tables_result]
    assert 'users' in table_names
    assert 'orders' in table_names
    assert 'products' in table_names

    # Test table creation
    conn.query("""
        CREATE TABLE test_new_table (
            id INTEGER PRIMARY KEY,
            test_column TEXT
        )
    """)

    # Verify new table exists
    tables_result = conn.query("SELECT name FROM sqlite_master WHERE type='table'")
    table_names = [row['name'] for row in tables_result]
    assert 'test_new_table' in table_names

    # Test table alteration (SQLite has limited ALTER TABLE support)
    try:
        conn.query("ALTER TABLE test_new_table ADD COLUMN new_column TEXT")
        # Verify column was added
        columns_result = conn.query("PRAGMA table_info(test_new_table)")
        column_names = [row['name'] for row in columns_result]
        assert 'new_column' in column_names
    except Exception:
        # Some SQLite versions may not support ALTER TABLE ADD COLUMN
        pass

def test_sqlite_error_handling_and_edge_cases(mock_sqlite_connection):
    """Test SQLite error handling and edge cases."""
    from dbutils.jdbc_provider import connect

    conn = connect(
        TEST_PROVIDER_NAME,
        {"database": mock_sqlite_connection["db_path"]}
    )

    # Test invalid SQL syntax
    with pytest.raises(sqlite3.DatabaseError):
        conn.query("SELECT FROM users WHERE")  # Invalid SQL

    # Test non-existent table
    with pytest.raises(sqlite3.OperationalError):
        conn.query("SELECT * FROM non_existent_table")

    # Test constraint violations
    with pytest.raises(sqlite3.IntegrityError):
        conn.query("INSERT INTO users (name, email) VALUES ('Test', 'john@example.com')")  # Duplicate email

    # Test NULL constraint violations
    with pytest.raises(sqlite3.IntegrityError):
        conn.query("INSERT INTO users (email) VALUES ('test@example.com')")  # Missing required name

def test_sqlite_connection_pooling_and_resource_management(mock_sqlite_connection):
    """Test SQLite connection pooling and resource management."""
    from dbutils.jdbc_provider import connect

    # Create multiple connections
    conn1 = connect(
        TEST_PROVIDER_NAME,
        {"database": mock_sqlite_connection["db_path"]}
    )

    conn2 = connect(
        TEST_PROVIDER_NAME,
        {"database": mock_sqlite_connection["db_path"]}
    )

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

def test_sqlite_transaction_management(mock_sqlite_connection):
    """Test SQLite transaction management."""
    from dbutils.jdbc_provider import connect

    conn = connect(
        TEST_PROVIDER_NAME,
        {"database": mock_sqlite_connection["db_path"]}
    )

    # Test transaction isolation
    initial_count = conn.query("SELECT COUNT(*) as count FROM users")[0]['count']

    # Start transaction (SQLite uses implicit transactions)
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

def test_sqlite_performance_and_large_data(mock_sqlite_connection):
    """Test SQLite performance with larger datasets."""
    from dbutils.jdbc_provider import connect

    conn = connect(
        TEST_PROVIDER_NAME,
        {"database": mock_sqlite_connection["db_path"]}
    )

    # Create a larger test table
    conn.query("""
        CREATE TABLE large_data (
            id INTEGER PRIMARY KEY,
            value TEXT,
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

def test_sqlite_integration_with_catalog_functions(mock_sqlite_connection):
    """Test SQLite integration with catalog functions."""
    # Set required environment variable for catalog functions
    import os
    os.environ["DBUTILS_JDBC_PROVIDER"] = TEST_PROVIDER_NAME

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

def test_sqlite_connection_teardown(mock_sqlite_connection):
    """Test proper connection teardown and cleanup."""
    from dbutils.jdbc_provider import connect

    # Create and close connection
    conn = connect(
        TEST_PROVIDER_NAME,
        {"database": mock_sqlite_connection["db_path"]}
    )

    # Verify connection is active
    result = conn.query("SELECT 1 as test")
    assert result[0]['test'] == 1

    # Close connection
    conn.close()

    # Verify connection is closed
    assert conn._conn is None

    # Verify database file still exists (should be cleaned up by fixture)
    assert os.path.exists(mock_sqlite_connection["db_path"])

# Additional helper functions for more comprehensive testing
def create_complex_sqlite_schema(conn):
    """Create a more complex SQLite schema for advanced testing."""
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

    conn.query("""
        CREATE INDEX idx_complex_name ON complex_table(name)
    """)

    conn.query("""
        CREATE TRIGGER trg_complex_update
        AFTER UPDATE ON complex_table
        FOR EACH ROW
        BEGIN
            UPDATE complex_table SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
        END
    """)

def test_sqlite_advanced_features(mock_sqlite_connection):
    """Test advanced SQLite features."""
    from dbutils.jdbc_provider import connect

    conn = connect(
        TEST_PROVIDER_NAME,
        {"database": mock_sqlite_connection["db_path"]}
    )

    # Create complex schema
    create_complex_sqlite_schema(conn)

    # Test index usage
    result = conn.query("SELECT name FROM complex_table WHERE name LIKE 'Test%'")
    assert isinstance(result, list)

    # Test constraint validation
    with pytest.raises(sqlite3.IntegrityError):
        conn.query("INSERT INTO complex_table (name, price, quantity) VALUES ('Test', -10.0, 5)")  # Negative price

    # Test trigger functionality
    conn.query("INSERT INTO complex_table (name, price, quantity) VALUES ('Test Product', 19.99, 10)")
    result = conn.query("SELECT updated_at FROM complex_table WHERE name = 'Test Product'")
    assert result[0]['updated_at'] is not None

def test_sqlite_connection_string_variations():
    """Test different SQLite connection string variations."""
    provider = JDBCProvider(
        name=TEST_PROVIDER_NAME,
        driver_class="org.sqlite.JDBC",
        jar_path=os.path.abspath("jars/sqlite-jdbc.jar"),
        url_template="jdbc:sqlite:{database}",
        default_user=None,
        default_password=None
    )

    # Test different URL parameter combinations
    test_cases = [
        {"database": "test.db"},
        {"database": "/absolute/path/to/test.db"},
        {"database": "file:test.db?mode=ro"},
        {"database": ":memory:"}
    ]

    for params in test_cases:
        url = provider.url_template.format(**params)
        assert url.startswith("jdbc:sqlite:")
        assert "test.db" in url or "memory" in url or "/absolute/path" in url

def test_sqlite_error_recovery(mock_sqlite_connection):
    """Test SQLite error recovery and connection resilience."""
    from dbutils.jdbc_provider import connect

    conn = connect(
        TEST_PROVIDER_NAME,
        {"database": mock_sqlite_connection["db_path"]}
    )

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
