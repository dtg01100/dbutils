"""Global test configuration for dbutils project.

This file contains pytest configuration and fixtures used across all test modules.
"""
import logging

# Configure logging for test debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# Import test configuration manager
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "tests"))
from test_config_manager import get_test_config_manager

# Add src directory to path so we can import dbutils
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


@pytest.fixture
def mock_jdbc_connection():
    """Mock JDBC connection for testing without actual database."""
    with patch("dbutils.jdbc_provider.jaydebeapi") as mock_jaydebeapi, \
         patch("dbutils.jdbc_provider.jpype") as mock_jpype:
        
        # Setup mock JPype
        mock_jpype.isJVMStarted.return_value = False
        mock_jpype.getDefaultJVMPath.return_value = "/fake/java/path"
        
        # Setup mock JayDeBeApi connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        
        mock_jaydebeapi.connect.return_value = mock_conn
        
        yield {
            "jaydebeapi": mock_jaydebeapi,
            "jpype": mock_jpype,
            "connection": mock_conn,
            "cursor": mock_cursor
        }


@pytest.fixture
def mock_db_data():
    """Provide mock database schema data for testing."""
    from dbutils.db_browser import TableInfo, ColumnInfo
    
    tables = [
        TableInfo(schema="TEST", name="USERS", remarks="User information table"),
        TableInfo(schema="TEST", name="ORDERS", remarks="Order records table"),
        TableInfo(schema="TEST", name="PRODUCTS", remarks="Product catalog table"),
        TableInfo(schema="DACDATA", name="CUSTOMERS", remarks="Customer data"),
        TableInfo(schema="DACDATA", name="INVOICES", remarks="Invoice records"),
    ]
    
    columns = [
        ColumnInfo(
            schema="TEST",
            table="USERS",
            name="ID",
            typename="INTEGER",
            length=10,
            scale=0,
            nulls="N",
            remarks="User identifier",
        ),
        ColumnInfo(
            schema="TEST",
            table="USERS",
            name="NAME",
            typename="VARCHAR",
            length=100,
            scale=0,
            nulls="N",
            remarks="User name",
        ),
        ColumnInfo(
            schema="TEST",
            table="USERS",
            name="EMAIL",
            typename="VARCHAR",
            length=255,
            scale=0,
            nulls="Y",
            remarks="User email address",
        ),
        ColumnInfo(
            schema="TEST",
            table="ORDERS",
            name="ID",
            typename="INTEGER",
            length=10,
            scale=0,
            nulls="N",
            remarks="Order identifier",
        ),
        ColumnInfo(
            schema="TEST",
            table="ORDERS",
            name="USER_ID",
            typename="INTEGER",
            length=10,
            scale=0,
            nulls="N",
            remarks="Foreign key to USERS",
        ),
    ]
    
    return {"tables": tables, "columns": columns}


@pytest.fixture
def temp_config_dir(tmp_path):
    """Provide a temporary directory for config files during testing."""
    config_dir = tmp_path / ".config" / "dbutils"
    config_dir.mkdir(parents=True)
    with patch.dict(os.environ, {"DBUTILS_CONFIG_DIR": str(config_dir)}):
        yield config_dir


@pytest.fixture(scope='session', autouse=True)
def enable_test_mode_env():
    """Set an environment variable so the GUI code can avoid blocking modal dialogs
    and other real UI interactions during automated tests.
    """
    with patch.dict(os.environ, {"DBUTILS_TEST_MODE": "1"}):
        yield

@pytest.fixture(scope='session', autouse=True)
def setup_sqlite_provider_for_tests():
    """Setup SQLite JDBC provider configuration for testing."""
    import json
    from dbutils.jdbc_provider import JDBCProvider, ProviderRegistry

    # Set up test-specific config directory
    test_config_dir = os.path.join(os.path.dirname(__file__), "test_config")
    os.makedirs(test_config_dir, exist_ok=True)

    # Set environment variable to use test config directory
    with patch.dict(os.environ, {
        "DBUTILS_CONFIG_DIR": test_config_dir,
        "DBUTILS_JDBC_PROVIDER": "SQLite (Test Integration)"
    }):
        # Create a test provider registry
        registry = ProviderRegistry()

        # Ensure SQLite provider exists
        if "SQLite (Test Integration)" not in registry.providers:
            sqlite_provider = JDBCProvider(
                name="SQLite (Test Integration)",
                driver_class="org.sqlite.JDBC",
                jar_path="AUTO_DOWNLOAD_sqlite",
                url_template="jdbc:sqlite:{database}",
                default_user=None,
                default_password=None,
            )
            registry.add_or_update(sqlite_provider)

        yield

        # Cleanup: remove test config directory
        try:
            import shutil
            if os.path.exists(test_config_dir):
                shutil.rmtree(test_config_dir)
        except Exception:
            pass

@pytest.fixture(scope='session', autouse=True)
def setup_multi_database_providers_for_tests():
    """Setup all multi-database JDBC providers for testing."""
    from dbutils.jdbc_provider import JDBCProvider, ProviderRegistry

    # Set up test-specific config directory
    test_config_dir = os.path.join(os.path.dirname(__file__), "test_config")
    os.makedirs(test_config_dir, exist_ok=True)

    # Set environment variable to use test config directory
    with patch.dict(os.environ, {
        "DBUTILS_CONFIG_DIR": test_config_dir,
    }):
        # Create a test provider registry
        registry = ProviderRegistry()

        # Ensure all required providers exist
        required_providers = [
            JDBCProvider(
                name="SQLite (Test Integration)",
                driver_class="org.sqlite.JDBC",
                jar_path="AUTO_DOWNLOAD_sqlite",
                url_template="jdbc:sqlite:{database}",
                default_user=None,
                default_password=None,
            ),
            JDBCProvider(
                name="H2 (Test Integration)",
                driver_class="org.h2.Driver",
                jar_path="AUTO_DOWNLOAD_h2",
                url_template="jdbc:h2:mem:{database};DB_CLOSE_DELAY=-1",
                default_user="sa",
                default_password="",
            ),
            JDBCProvider(
                name="Apache Derby (Test Integration)",
                driver_class="org.apache.derby.jdbc.EmbeddedDriver",
                jar_path="AUTO_DOWNLOAD_derby",
                url_template="jdbc:derby:{database};create=true",
                default_user=None,
                default_password=None,
            ),
            JDBCProvider(
                name="HSQLDB (Test Integration)",
                driver_class="org.hsqldb.jdbc.JDBCDriver",
                jar_path="AUTO_DOWNLOAD_hsqldb",
                url_template="jdbc:hsqldb:mem:{database}",
                default_user="SA",
                default_password="",
            ),
            JDBCProvider(
                name="DuckDB (Test Integration)",
                driver_class="org.duckdb.DuckDBDriver",
                jar_path="AUTO_DOWNLOAD_duckdb",
                url_template="jdbc:duckdb:{database}",
                default_user=None,
                default_password=None,
            )
        ]

        for provider in required_providers:
            if provider.name not in registry.providers:
                registry.add_or_update(provider)

        yield

        # Cleanup: remove test config directory
        try:
            import shutil
            if os.path.exists(test_config_dir):
                shutil.rmtree(test_config_dir)
        except Exception:
            pass


@pytest.fixture(autouse=True)
def disable_qt_message_boxes(monkeypatch):
    """Patch QMessageBox functions to avoid UI popups during tests.
    Returns default values where appropriate and avoids blocking dialogs.
    """
    try:
        from PySide6.QtWidgets import QMessageBox, QFileDialog, QInputDialog
        import webbrowser

        monkeypatch.setattr(QMessageBox, 'question', lambda *args, **kwargs: QMessageBox.StandardButton.Yes)
        monkeypatch.setattr(QMessageBox, 'information', lambda *args, **kwargs: None)
        monkeypatch.setattr(QMessageBox, 'warning', lambda *args, **kwargs: None)
        monkeypatch.setattr(QMessageBox, 'critical', lambda *args, **kwargs: None)

        # Avoid any blocking native file-open dialogs during tests
        monkeypatch.setattr(QFileDialog, 'getOpenFileName', lambda *args, **kwargs: ('', ''))
        # Avoid selection dialogs and return no selection by default
        monkeypatch.setattr(QInputDialog, 'getItem', lambda *args, **kwargs: ('', False))
        # Prevent tests from launching a real web browser; return False to indicate not opened
        monkeypatch.setattr(webbrowser, 'open', lambda *args, **kwargs: False)
        monkeypatch.setattr(webbrowser, 'open_new', lambda *args, **kwargs: False)
        monkeypatch.setattr(webbrowser, 'open_new_tab', lambda *args, **kwargs: False)
    except Exception:
        # If Qt bindings aren't available (some test environments), ignore gracefully
        pass
    yield


@pytest.fixture
def sample_sql_query():
    """Provide sample SQL query for testing."""
    return "SELECT * FROM TEST.TABLE WHERE ID = 123"

@pytest.fixture(autouse=True)
def check_dependencies_and_skip(request):
    """Check for required dependencies and skip tests if they're missing."""
    import pytest

    # Check for JDBC dependencies
    try:
        import jaydebeapi
        import jpype
    except ImportError as e:
        logger.warning(f"JDBC dependencies missing: {e}")
        if "test_sqlite_integration" in str(request.node.nodeid):
            pytest.skip("JDBC dependencies (jaydebeapi/jpype) not available")

    # Check for GUI dependencies (PySide6)
    try:
        import PySide6
    except ImportError:
        logger.warning("PySide6 not available - GUI tests will be skipped")
        if "test_provider_config_dialog" in str(request.node.nodeid) or "test_widgets" in str(request.node.nodeid):
            pytest.skip("PySide6 not available for GUI tests")

def pytest_collection_modifyitems(items):
    """Modify test collection to skip GUI tests if PySide6 is not available."""
    try:
        import PySide6
    except ImportError:
        for item in items:
            if "gui" in str(item.nodeid).lower() or "widget" in str(item.nodeid).lower():
                item.add_marker(pytest.mark.skip(reason="PySide6 not available"))

def pytest_runtest_setup(item):
    """Setup for each test - check dependencies and environment."""
    # Check if this is a SQLite integration test
    if "test_sqlite_integration" in str(item.nodeid):
        # Check if JDBC dependencies are available
        try:
            import jaydebeapi
            import jpype
        except ImportError:
            pytest.skip("JDBC dependencies not available for SQLite integration tests")

        # Check if SQLite provider is configured
        try:
            from dbutils.jdbc_provider import get_registry
            registry = get_registry()
            if "SQLite (Test Integration)" not in registry.providers:
                pytest.skip("SQLite (Test Integration) provider not configured")
        except Exception as e:
            pytest.skip(f"Cannot access provider registry: {e}")

@pytest.fixture(scope='session')
def multi_database_providers():
    """Provide configurations for all supported test databases."""
    from dbutils.jdbc_provider import JDBCProvider

    # Database configurations for testing
    databases = {
        "sqlite": JDBCProvider(
            name="SQLite (Test Integration)",
            driver_class="org.sqlite.JDBC",
            jar_path="AUTO_DOWNLOAD_sqlite",
            url_template="jdbc:sqlite:{database}",
            default_user=None,
            default_password=None,
        ),
        "h2": JDBCProvider(
            name="H2 (Test Integration)",
            driver_class="org.h2.Driver",
            jar_path="AUTO_DOWNLOAD_h2",
            url_template="jdbc:h2:mem:{database};DB_CLOSE_DELAY=-1",
            default_user="sa",
            default_password="",
        ),
        "derby": JDBCProvider(
            name="Apache Derby (Test Integration)",
            driver_class="org.apache.derby.jdbc.EmbeddedDriver",
            jar_path="AUTO_DOWNLOAD_derby",
            url_template="jdbc:derby:{database};create=true",
            default_user=None,
            default_password=None,
        ),
        "hsqldb": JDBCProvider(
            name="HSQLDB (Test Integration)",
            driver_class="org.hsqldb.jdbc.JDBCDriver",
            jar_path="AUTO_DOWNLOAD_hsqldb",
            url_template="jdbc:hsqldb:mem:{database}",
            default_user="SA",
            default_password="",
        ),
        "duckdb": JDBCProvider(
            name="DuckDB (Test Integration)",
            driver_class="org.duckdb.DuckDBDriver",
            jar_path="AUTO_DOWNLOAD_duckdb",
            url_template="jdbc:duckdb:{database}",
            default_user=None,
            default_password=None,
        )
    }

    return databases

@pytest.fixture
def database_test_data():
    """Provide standardized test data for database testing."""
    return {
        "schema": {
            "users": ["id", "name", "email", "created_at"],
            "orders": ["id", "user_id", "total_amount", "order_date"],
            "products": ["id", "name", "price", "category"]
        },
        "sample_queries": {
            "count_users": "SELECT COUNT(*) as count FROM users",
            "find_user": "SELECT * FROM users WHERE name LIKE ?",
            "join_query": "SELECT u.name, o.total_amount FROM users u JOIN orders o ON u.id = o.user_id"
        },
        "expected_results": {
            "user_count": 2,
            "product_count": 2,
            "order_count": 2
        },
        "database_specific": {
            "sqlite": {
                "json_support": "SELECT json_object('key', 'value') as json_result",
                "date_functions": "SELECT date('now') as current_date"
            },
            "h2": {
                "sequence_support": "NEXT VALUE FOR SEQUENCE_NAME",
                "array_support": "ARRAY[1, 2, 3]"
            },
            "derby": {
                "identity_columns": "GENERATED ALWAYS AS IDENTITY",
                "schema_support": "CREATE SCHEMA TEST_SCHEMA"
            },
            "hsqldb": {
                "text_tables": "CREATE TEXT TABLE",
                "cached_tables": "CREATE CACHED TABLE"
            },
            "duckdb": {
                "parquet_support": "SELECT * FROM read_parquet('file.parquet')",
                "json_functions": "SELECT * FROM json_each('{\"a\":1}')"
            }
        }
    }

@pytest.fixture
def create_test_database(request):
    """Create a test database for the specified database type."""
    import tempfile
    import sqlite3

    db_type = request.param
    db_name = f"test_{db_type}_db"

    if db_type == "sqlite":
        # Create SQLite database using native Python driver
        db_path = f"{db_name}.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create test schema
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

        yield db_path

        # Cleanup
        if os.path.exists(db_path):
            os.remove(db_path)

    else:
        # For other databases, yield the database name for JDBC connection
        yield db_name

@pytest.fixture
def database_connection(request, multi_database_providers):
    """Create a JDBC connection to the specified database type."""
    from dbutils.jdbc_provider import JDBCConnection

    db_type = request.param
    provider = multi_database_providers[db_type]

    # Create test database if needed
    if db_type == "sqlite":
        db_path = "test_sqlite_db.db"
        if not os.path.exists(db_path):
            create_test_database(pytest.param(db_type, marks=pytest.mark.sqlite))
    else:
        db_path = f"test_{db_type}_db"

    # Create connection
    conn = JDBCConnection(
        provider=provider,
        url_params={"database": db_path},
        user=provider.default_user,
        password=provider.default_password
    )
    conn.connect()

    yield conn

    # Cleanup
    conn.close()

    # Check if this is a multi-database integration test
    if "test_multi_database_integration" in str(item.nodeid):
        # Check if JDBC dependencies are available
        try:
            import jaydebeapi
            import jpype
        except ImportError:
            pytest.skip("JDBC dependencies not available for multi-database integration tests")

        # Check if required database providers are configured
        try:
            from dbutils.jdbc_provider import get_registry
            registry = get_registry()
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

@pytest.fixture(scope='session')
def test_config():
    """Provide centralized test configuration management."""
    config_manager = get_test_config_manager()
    return config_manager

@pytest.fixture
def test_db_config(test_config):
    """Provide database configuration from centralized test config."""
    return test_config.get_database_config

@pytest.fixture
def test_network_config(test_config):
    """Provide network configuration from centralized test config."""
    return test_config.get_network_setting

@pytest.fixture
def test_path_config(test_config):
    """Provide path configuration from centralized test config."""
    return test_config.get_path_setting

@pytest.fixture
def test_behavior_config(test_config):
    """Provide behavior configuration from centralized test config."""
    return test_config.get_behavior_setting