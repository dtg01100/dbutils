#!/usr/bin/env python3
"""Setup script to configure SQLite JDBC provider for testing."""

import json
import os
import sqlite3
from pathlib import Path

# Create a sample SQLite database with some test data
def create_sample_database():
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

def setup_sqlite_provider():
    """Setup SQLite JDBC provider configuration."""
    config_dir = os.path.expanduser("~/.config/dbutils")
    providers_file = os.path.join(config_dir, "providers.json")
    
    # Create config directory if it doesn't exist
    os.makedirs(config_dir, exist_ok=True)
    
    # SQLite provider configuration
    sqlite_provider = {
        "name": "SQLite (Test)",
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
    providers = [p for p in providers if p.get("name") != "SQLite (Test)"]
    providers.append(sqlite_provider)
    
    # Save providers
    with open(providers_file, 'w') as f:
        json.dump(providers, f, indent=2)
    
    print(f"Setup SQLite provider: {providers_file}")
    return sqlite_provider

def test_sqlite_connection():
    """Test the SQLite JDBC connection."""
    import sys
    sys.path.insert(0, 'src')
    
    try:
        from dbutils.jdbc_provider import connect
        
        # Test connection
        conn = connect(
            "SQLite (Test)", 
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

if __name__ == "__main__":
    print("Setting up SQLite JDBC provider for testing...")
    
    # Create sample database
    db_path = create_sample_database()
    
    # Setup provider
    provider = setup_sqlite_provider()
    
    # Test connection
    success = test_sqlite_connection()
    
    if success:
        print("\nTo use the SQLite provider, set these environment variables:")
        print(f"export DBUTILS_JDBC_PROVIDER=\"SQLite (Test)\"")
        print(f"export DBUTILS_JDBC_URL_PARAMS='{{\"database\":\"{os.path.abspath(db_path)}\"}}'")
        print("\nThen run:")
        print("uvx . db-browser --mock")
    else:
        print("\nSetup failed. Please check the error messages above.")