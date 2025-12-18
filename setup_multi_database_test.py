#!/usr/bin/env python3
"""Comprehensive multi-database test setup for dbutils project.

This script sets up and configures multiple freely available databases for testing:
- SQLite (already configured)
- H2 Database (already configured)
- Apache Derby
- HSQLDB
- DuckDB

The script handles JDBC driver configurations, environment setup, and test database creation.
"""

import json
import logging
import os
import sqlite3
import subprocess
import sys
from typing import Any, Dict, Optional

import pytest

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configurations
DATABASE_CONFIGS = {
    "sqlite": {
        "name": "SQLite (Test Integration)",
        "driver_class": "org.sqlite.JDBC",
        "jar_path": "AUTO_DOWNLOAD_sqlite",
        "url_template": "jdbc:sqlite:{database}",
        "default_user": None,
        "default_password": None,
        "test_db": "test_integration.db",
        "description": "SQLite embedded database",
    },
    "h2": {
        "name": "H2 (Test Integration)",
        "driver_class": "org.h2.Driver",
        "jar_path": "AUTO_DOWNLOAD_h2",
        "url_template": "jdbc:h2:mem:{database};DB_CLOSE_DELAY=-1",
        "default_user": "sa",
        "default_password": "",
        "test_db": "test_h2_mem",
        "description": "H2 in-memory database",
    },
    "derby": {
        "name": "Apache Derby (Test Integration)",
        "driver_class": "org.apache.derby.jdbc.EmbeddedDriver",
        "jar_path": "AUTO_DOWNLOAD_derby",
        "url_template": "jdbc:derby:{database};create=true",
        "default_user": None,
        "default_password": None,
        "test_db": "test_derby_db",
        "description": "Apache Derby embedded database",
    },
    "hsqldb": {
        "name": "HSQLDB (Test Integration)",
        "driver_class": "org.hsqldb.jdbc.JDBCDriver",
        "jar_path": "AUTO_DOWNLOAD_hsqldb",
        "url_template": "jdbc:hsqldb:mem:{database}",
        "default_user": "SA",
        "default_password": "",
        "test_db": "test_hsqldb_mem",
        "description": "HSQLDB in-memory database",
    },
    "duckdb": {
        "name": "DuckDB (Test Integration)",
        "driver_class": "org.duckdb.DuckDBDriver",
        "jar_path": "AUTO_DOWNLOAD_duckdb",
        "url_template": "jdbc:duckdb:{database}",
        "default_user": None,
        "default_password": None,
        "test_db": "test_duckdb.db",
        "description": "DuckDB embedded database",
    },
}


def check_dependencies() -> Dict[str, bool]:
    """Check if required dependencies are installed."""
    dependencies = {"jaydebeapi": False, "jpype1": False, "PySide6": False}

    try:
        import jaydebeapi

        dependencies["jaydebeapi"] = True
    except ImportError:
        logger.warning("jaydebeapi not found - JDBC functionality will be limited")

    try:
        import jpype

        dependencies["jpype1"] = True
    except ImportError:
        logger.warning("jpype not found - JDBC functionality will be limited")

    try:
        import PySide6

        dependencies["PySide6"] = True
    except ImportError:
        logger.warning("PySide6 not found - GUI functionality will be limited")

    return dependencies


def install_missing_dependencies() -> bool:
    """Install missing dependencies using pip with graceful fallback."""
    try:
        # Check what's missing
        deps = check_dependencies()
        missing = [name for name, installed in deps.items() if not installed]

        if not missing:
            logger.info("All dependencies are already installed.")
            return True

        logger.info(f"Installing missing dependencies: {', '.join(missing)}")
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", *missing], capture_output=True, text=True, timeout=300
            )

            if result.returncode == 0:
                logger.info("Dependencies installed successfully.")
                return True
            else:
                logger.warning(f"Failed to install dependencies: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.warning("Dependency installation timed out")
            return False
        except Exception as e:
            logger.warning(f"Error installing dependencies: {e}")
            return False

    except Exception as e:
        logger.error(f"Unexpected error in dependency installation: {e}")
        return False


def create_test_database(db_type: str, db_path: str) -> bool:
    """Create a test database with sample schema for the specified database type."""
    try:
        if db_type == "sqlite":
            # SQLite uses native Python driver for setup
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
        else:
            # For other databases, we'll use JDBC connections
            # This will be handled by the test fixtures
            logger.info(f"Skipping direct database creation for {db_type} - will use JDBC")
            return True

        # Create sample tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                total_amount DECIMAL(10,2),
                order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                price DECIMAL(10,2),
                category TEXT
            )
        """)

        # Insert test data
        cursor.execute("INSERT INTO users (name, email) VALUES (?, ?)", ("John Doe", "john@example.com"))
        cursor.execute("INSERT INTO users (name, email) VALUES (?, ?)", ("Jane Smith", "jane@example.com"))
        cursor.execute(
            "INSERT INTO products (name, price, category) VALUES (?, ?, ?)", ("Laptop", 999.99, "Electronics")
        )
        cursor.execute("INSERT INTO products (name, price, category) VALUES (?, ?, ?)", ("Book", 19.99, "Books"))
        cursor.execute("INSERT INTO orders (user_id, total_amount) VALUES (?, ?)", (1, 1019.98))
        cursor.execute("INSERT INTO orders (user_id, total_amount) VALUES (?, ?)", (2, 19.99))

        conn.commit()
        conn.close()
        return True

    except Exception as e:
        logger.error(f"Failed to create test database for {db_type}: {e}")
        return False


def setup_database_providers(config_dir: Optional[str] = None) -> Dict[str, Any]:
    """Setup JDBC providers for all supported databases."""
    if config_dir is None:
        config_dir = os.path.expanduser("~/.config/dbutils")

    providers_file = os.path.join(config_dir, "providers.json")

    # Create config directory if it doesn't exist
    os.makedirs(config_dir, exist_ok=True)

    # Load existing providers or create new list
    providers = []
    if os.path.exists(providers_file):
        try:
            with open(providers_file, "r") as f:
                providers = json.load(f)
        except Exception as e:
            logger.warning(f"Error loading existing providers: {e}")

    # Add or update providers for all database types
    for db_type, config in DATABASE_CONFIGS.items():
        # Remove existing provider with same name
        providers = [p for p in providers if p.get("name") != config["name"]]

        # Add new provider
        provider_config = {
            "name": config["name"],
            "driver_class": config["driver_class"],
            "jar_path": os.path.abspath(config["jar_path"]),
            "url_template": config["url_template"],
            "default_user": config["default_user"],
            "default_password": config["default_password"],
            "extra_properties": {},
        }
        providers.append(provider_config)

    # Save providers
    with open(providers_file, "w") as f:
        json.dump(providers, f, indent=2)

    logger.info(f"Setup database providers: {providers_file}")
    return {db_type: config for db_type, config in DATABASE_CONFIGS.items()}


def setup_test_environment() -> Dict[str, str]:
    """Set up environment variables for multi-database testing."""
    env_vars = {}

    # Set test mode to avoid UI popups
    env_vars["DBUTILS_TEST_MODE"] = "1"

    # Set config directory to use test-specific location
    test_config_dir = os.path.join(os.path.dirname(__file__), "test_config")
    os.makedirs(test_config_dir, exist_ok=True)
    env_vars["DBUTILS_CONFIG_DIR"] = test_config_dir

    # Apply environment variables
    for key, value in env_vars.items():
        os.environ[key] = value

    logger.info("Environment variables set:")
    for key, value in env_vars.items():
        logger.info(f"  {key}={value}")

    return env_vars


@pytest.mark.timeout(120)
def test_database_connections() -> Dict[str, bool]:
    """Test JDBC connections for all configured databases with graceful fallback."""
    import sys

    sys.path.insert(0, "src")

    results = {}

    try:
        from dbutils.jdbc_provider import connect

        for db_type, config in DATABASE_CONFIGS.items():
            try:
                logger.info(f"Testing {db_type} connection...")

                # Check if JAR file exists
                jar_path = config["jar_path"]
                if not os.path.exists(jar_path):
                    logger.warning(f"JAR file not found for {db_type}: {jar_path}")
                    results[db_type] = False
                    continue

                # Create test database file if needed
                if db_type == "sqlite":
                    db_path = config["test_db"]
                    if not os.path.exists(db_path):
                        if not create_test_database(db_type, db_path):
                            logger.warning(f"Failed to create test database for {db_type}")
                            results[db_type] = False
                            continue
                elif db_type == "derby":
                    db_path = config["test_db"]
                    # Derby will create the database automatically
                else:
                    # In-memory databases don't need file creation
                    db_path = config["test_db"]

                # Test connection
                conn = connect(config["name"], {"database": db_path})

                # Test a simple query
                result = conn.query("SELECT 1 as test")
                logger.info(f"{db_type} connection successful: {result[0] if result else 'No result'}")
                conn.close()

                results[db_type] = True

            except ImportError as e:
                logger.warning(f"{db_type} connection test skipped due to missing dependencies: {e}")
                results[db_type] = False
            except Exception as e:
                logger.error(f"{db_type} connection test failed: {e}")
                results[db_type] = False

    except ImportError as e:
        logger.warning(f"JDBC provider module not available: {e}")
        for db_type in DATABASE_CONFIGS.keys():
            results[db_type] = False
    except Exception as e:
        logger.error(f"Database connection testing failed: {e}")
        for db_type in DATABASE_CONFIGS.keys():
            results[db_type] = False

    return results


def cleanup_test_environment():
    """Clean up test environment."""
    test_config_dir = os.path.join(os.path.dirname(__file__), "test_config")
    try:
        if os.path.exists(test_config_dir):
            import shutil

            shutil.rmtree(test_config_dir)
            logger.info(f"Cleaned up test config directory: {test_config_dir}")
    except Exception as e:
        logger.error(f"Error cleaning up test environment: {e}")


def create_database_specific_test_data(db_type: str) -> Dict[str, Any]:
    """Create database-specific test data and configurations."""
    test_data = {
        "schema": {
            "users": ["id", "name", "email", "created_at"],
            "orders": ["id", "user_id", "total_amount", "order_date"],
            "products": ["id", "name", "price", "category"],
        },
        "sample_queries": {
            "count_users": "SELECT COUNT(*) as count FROM users",
            "find_user": "SELECT * FROM users WHERE name LIKE ?",
            "join_query": "SELECT u.name, o.total_amount FROM users u JOIN orders o ON u.id = o.user_id",
        },
        "expected_results": {"user_count": 2, "product_count": 2, "order_count": 2},
    }

    # Database-specific configurations
    if db_type == "sqlite":
        test_data["specific_features"] = {
            "json_support": "SELECT json_object('key', 'value') as json_result",
            "date_functions": "SELECT date('now') as current_date",
        }
    elif db_type == "h2":
        test_data["specific_features"] = {
            "sequence_support": "NEXT VALUE FOR SEQUENCE_NAME",
            "array_support": "ARRAY[1, 2, 3]",
        }
    elif db_type == "derby":
        test_data["specific_features"] = {
            "identity_columns": "GENERATED ALWAYS AS IDENTITY",
            "schema_support": "CREATE SCHEMA TEST_SCHEMA",
        }
    elif db_type == "hsqldb":
        test_data["specific_features"] = {"text_tables": "CREATE TEXT TABLE", "cached_tables": "CREATE CACHED TABLE"}
    elif db_type == "duckdb":
        test_data["specific_features"] = {
            "parquet_support": "SELECT * FROM read_parquet('file.parquet')",
            "json_functions": "SELECT * FROM json_each('{\"a\":1}')",
        }

    return test_data


def main():
    """Main setup function for multi-database testing."""
    print("Setting up multi-database JDBC providers for testing...")
    print("=" * 60)

    # Check and install dependencies
    print("\nChecking dependencies...")
    deps = check_dependencies()
    for name, installed in deps.items():
        print(f"  {name}: {'✓' if installed else '✗'}")

    if not all(deps.values()):
        print("\nInstalling missing dependencies...")
        if not install_missing_dependencies():
            print("Warning: Some dependencies could not be installed. Tests may fail.")

    # Setup test environment
    print("\nSetting up test environment...")
    setup_test_environment()

    # Setup database providers
    print("\nSetting up database providers...")
    providers = setup_database_providers()

    # Test connections
    print("\nTesting database connections...")
    connection_results = test_database_connections()

    # Summary
    print("\n" + "=" * 60)
    print("SETUP SUMMARY")
    print("=" * 60)

    success_count = sum(1 for result in connection_results.values() if result)
    total_count = len(connection_results)

    print(f"Databases configured: {success_count}/{total_count}")
    for db_type, success in connection_results.items():
        status = "✓" if success else "✗"
        print(f"  {db_type.upper()}: {status}")

    if success_count > 0:
        print("\n" + "=" * 60)
        print("SETUP COMPLETE!")
        print("=" * 60)
        print("To run multi-database tests, use:")
        print("  pytest tests/test_multi_database_integration.py")
        print("\nEnvironment variables are already set for this session.")
        print("If running in a new terminal, set these variables:")
        print('  export DBUTILS_TEST_MODE="1"')
        print(f'  export DBUTILS_CONFIG_DIR="{os.path.abspath("test_config")}"')
    else:
        print("\nSetup failed. Please check the error messages above.")
        cleanup_test_environment()


if __name__ == "__main__":
    main()
