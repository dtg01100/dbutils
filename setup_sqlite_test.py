#!/usr/bin/env python3
"""Enhanced setup script to configure SQLite JDBC provider for testing with proper environment setup."""

import json
import os
import sqlite3
import sys
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any

def check_dependencies() -> Dict[str, bool]:
    """Check if required dependencies are installed."""
    dependencies = {
        'jaydebeapi': False,
        'jpype1': False,
        'PySide6': False
    }

    try:
        import jaydebeapi
        dependencies['jaydebeapi'] = True
    except ImportError:
        pass

    try:
        import jpype
        dependencies['jpype1'] = True
    except ImportError:
        pass

    try:
        import PySide6
        dependencies['PySide6'] = True
    except ImportError:
        pass

    return dependencies

def install_missing_dependencies() -> bool:
    """Install missing dependencies using pip."""
    try:
        # Check what's missing
        deps = check_dependencies()
        missing = [name for name, installed in deps.items() if not installed]

        if not missing:
            print("All dependencies are already installed.")
            return True

        print(f"Installing missing dependencies: {', '.join(missing)}")
        result = subprocess.run([
            sys.executable, "-m", "pip", "install",
            *missing
        ], capture_output=True, text=True)

        if result.returncode == 0:
            print("Dependencies installed successfully.")
            return True
        else:
            print(f"Failed to install dependencies: {result.stderr}")
            return False

    except Exception as e:
        print(f"Error installing dependencies: {e}")
        return False

def create_sample_database() -> str:
    """Create a sample SQLite database with test schema."""
    db_path = "test_sample.db"

    # Remove existing database if it exists
    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create sample tables
    cursor.execute("""
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY,
            customer_id INTEGER,
            total_amount DECIMAL(10,2),
            order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
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

    cursor.execute("""
        CREATE TABLE order_items (
            id INTEGER PRIMARY KEY,
            order_id INTEGER,
            product_id INTEGER,
            quantity INTEGER,
            unit_price DECIMAL(10,2),
            FOREIGN KEY (order_id) REFERENCES orders(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    """)

    # Insert sample data
    cursor.execute("INSERT INTO customers (name, email) VALUES (?, ?)", ("John Doe", "john@example.com"))
    cursor.execute("INSERT INTO customers (name, email) VALUES (?, ?)", ("Jane Smith", "jane@example.com"))

    cursor.execute("INSERT INTO products (name, price, category) VALUES (?, ?, ?)", ("Laptop", 999.99, "Electronics"))
    cursor.execute("INSERT INTO products (name, price, category) VALUES (?, ?, ?)", ("Book", 19.99, "Books"))

    cursor.execute("INSERT INTO orders (customer_id, total_amount) VALUES (?, ?)", (1, 1019.98))
    cursor.execute("INSERT INTO orders (customer_id, total_amount) VALUES (?, ?)", (2, 19.99))

    cursor.execute("INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (?, ?, ?, ?)",
                   (1, 1, 1, 999.99))
    cursor.execute("INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (?, ?, ?, ?)",
                   (1, 2, 1, 19.99))
    cursor.execute("INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (?, ?, ?, ?)",
                   (2, 2, 1, 19.99))

    conn.commit()
    conn.close()
    print(f"Created sample database: {db_path}")
    return db_path

def setup_sqlite_provider(config_dir: Optional[str] = None) -> Dict[str, Any]:
    """Setup SQLite JDBC provider configuration."""
    if config_dir is None:
        config_dir = os.path.expanduser("~/.config/dbutils")

    providers_file = os.path.join(config_dir, "providers.json")

    # Create config directory if it doesn't exist
    os.makedirs(config_dir, exist_ok=True)

    # SQLite provider configuration for testing
    sqlite_provider = {
        "name": "SQLite (Test Integration)",
        "driver_class": "org.sqlite.JDBC",
        "jar_path": os.path.abspath("jars/sqlite-jdbc.jar"),
        "url_template": "jdbc:sqlite:{database}",
        "default_user": None,
        "default_password": None,
        "extra_properties": {}
    }

    # Load existing providers or create new list
    providers = []
    if os.path.exists(providers_file):
        try:
            with open(providers_file, 'r') as f:
                providers = json.load(f)
        except Exception as e:
            print(f"Error loading existing providers: {e}")

    # Add or update SQLite provider
    providers = [p for p in providers if p.get("name") != "SQLite (Test Integration)"]
    providers.append(sqlite_provider)

    # Save providers
    with open(providers_file, 'w') as f:
        json.dump(providers, f, indent=2)

    print(f"Setup SQLite provider: {providers_file}")
    return sqlite_provider

def setup_test_environment() -> Dict[str, str]:
    """Set up environment variables for testing."""
    env_vars = {}

    # Set JDBC provider environment variable
    env_vars["DBUTILS_JDBC_PROVIDER"] = "SQLite (Test Integration)"

    # Set config directory to use test-specific location
    test_config_dir = os.path.join(os.path.dirname(__file__), "test_config")
    os.makedirs(test_config_dir, exist_ok=True)
    env_vars["DBUTILS_CONFIG_DIR"] = test_config_dir

    # Set test mode to avoid UI popups
    env_vars["DBUTILS_TEST_MODE"] = "1"

    # Apply environment variables
    for key, value in env_vars.items():
        os.environ[key] = value

    print("Environment variables set:")
    for key, value in env_vars.items():
        print(f"  {key}={value}")

    return env_vars

def test_sqlite_connection() -> bool:
    """Test the SQLite JDBC connection."""
    import sys
    sys.path.insert(0, 'src')

    try:
        from dbutils.jdbc_provider import connect

        # Test connection
        conn = connect(
            "SQLite (Test Integration)",
            {"database": os.path.abspath("test_sample.db")}
        )

        # Test a simple query
        result = conn.query("SELECT name FROM sqlite_master WHERE type='table'")
        print("Tables in database:")
        for row in result:
            print(f"  - {row.get('name', 'N/A')}")

        # Test a more complex query
        result = conn.query("SELECT COUNT(*) as count FROM customers")
        print(f"Customers count: {result[0].get('count', 0) if result else 'N/A'}")

        conn.close()
        print("SQLite JDBC connection test successful!")
        return True

    except Exception as e:
        print(f"SQLite JDBC connection test failed: {e}")
        return False

def cleanup_test_environment():
    """Clean up test environment."""
    test_config_dir = os.path.join(os.path.dirname(__file__), "test_config")
    try:
        if os.path.exists(test_config_dir):
            import shutil
            shutil.rmtree(test_config_dir)
            print(f"Cleaned up test config directory: {test_config_dir}")
    except Exception as e:
        print(f"Error cleaning up test environment: {e}")

def main():
    """Main setup function."""
    print("Setting up SQLite JDBC provider for testing...")

    # Check and install dependencies
    print("\nChecking dependencies...")
    deps = check_dependencies()
    for name, installed in deps.items():
        print(f"  {name}: {'✓' if installed else '✗'}")

    if not all(deps.values()):
        print("\nInstalling missing dependencies...")
        if not install_missing_dependencies():
            print("Warning: Some dependencies could not be installed. Tests may fail.")

    # Create sample database
    print("\nCreating sample database...")
    db_path = create_sample_database()

    # Setup test environment
    print("\nSetting up test environment...")
    setup_test_environment()

    # Setup provider
    print("\nSetting up SQLite provider...")
    provider = setup_sqlite_provider()

    # Test connection
    print("\nTesting SQLite JDBC connection...")
    success = test_sqlite_connection()

    if success:
        print("\n" + "="*60)
        print("SETUP COMPLETE!")
        print("="*60)
        print("To run tests, use:")
        print("  pytest tests/test_sqlite_integration.py")
        print("\nEnvironment variables are already set for this session.")
        print("If running in a new terminal, set these variables:")
        print(f"  export DBUTILS_JDBC_PROVIDER=\"SQLite (Test Integration)\"")
        print(f"  export DBUTILS_CONFIG_DIR=\"{os.path.abspath('test_config')}\"")
        print(f"  export DBUTILS_TEST_MODE=\"1\"")
    else:
        print("\nSetup failed. Please check the error messages above.")
        cleanup_test_environment()

if __name__ == "__main__":
    main()