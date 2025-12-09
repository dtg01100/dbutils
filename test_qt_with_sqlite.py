#!/usr/bin/env python3
"""
Test Qt Browser with a generated SQLite database.
Creates a sample database with realistic data and launches the Qt browser.
"""

import sqlite3
import os
import sys
import subprocess
from pathlib import Path

def create_test_database(db_path: str):
    """Create a test SQLite database with sample data."""
    
    # Remove existing database if it exists
    if os.path.exists(db_path):
        os.remove(db_path)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print(f"Creating test database: {db_path}")
    
    # Create Customers table
    cursor.execute("""
        CREATE TABLE customers (
            customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT,
            created_date TEXT DEFAULT CURRENT_TIMESTAMP,
            status TEXT CHECK(status IN ('active', 'inactive', 'suspended'))
        )
    """)
    
    # Create Products table
    cursor.execute("""
        CREATE TABLE products (
            product_id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL CHECK(price >= 0),
            stock_quantity INTEGER DEFAULT 0,
            description TEXT,
            created_date TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create Orders table
    cursor.execute("""
        CREATE TABLE orders (
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            order_date TEXT DEFAULT CURRENT_TIMESTAMP,
            total_amount REAL NOT NULL CHECK(total_amount >= 0),
            status TEXT CHECK(status IN ('pending', 'processing', 'shipped', 'delivered', 'cancelled')),
            shipping_address TEXT,
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        )
    """)
    
    # Create OrderItems table
    cursor.execute("""
        CREATE TABLE order_items (
            order_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL CHECK(quantity > 0),
            unit_price REAL NOT NULL CHECK(unit_price >= 0),
            FOREIGN KEY (order_id) REFERENCES orders(order_id),
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        )
    """)
    
    # Create Employees table
    cursor.execute("""
        CREATE TABLE employees (
            employee_id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            department TEXT,
            hire_date TEXT DEFAULT CURRENT_TIMESTAMP,
            salary REAL CHECK(salary > 0),
            manager_id INTEGER,
            FOREIGN KEY (manager_id) REFERENCES employees(employee_id)
        )
    """)
    
    # Insert sample customers
    customers = [
        ('John', 'Doe', 'john.doe@email.com', '555-0101', 'active'),
        ('Jane', 'Smith', 'jane.smith@email.com', '555-0102', 'active'),
        ('Bob', 'Johnson', 'bob.johnson@email.com', '555-0103', 'active'),
        ('Alice', 'Williams', 'alice.williams@email.com', '555-0104', 'inactive'),
        ('Charlie', 'Brown', 'charlie.brown@email.com', '555-0105', 'active'),
        ('Diana', 'Davis', 'diana.davis@email.com', '555-0106', 'suspended'),
        ('Edward', 'Miller', 'edward.miller@email.com', '555-0107', 'active'),
        ('Fiona', 'Wilson', 'fiona.wilson@email.com', '555-0108', 'active'),
        ('George', 'Moore', 'george.moore@email.com', '555-0109', 'active'),
        ('Hannah', 'Taylor', 'hannah.taylor@email.com', '555-0110', 'inactive'),
    ]
    
    cursor.executemany(
        "INSERT INTO customers (first_name, last_name, email, phone, status) VALUES (?, ?, ?, ?, ?)",
        customers
    )
    
    # Insert sample products
    products = [
        ('Laptop Pro 15', 'Electronics', 1299.99, 25, 'High-performance laptop'),
        ('Wireless Mouse', 'Electronics', 29.99, 150, 'Ergonomic wireless mouse'),
        ('USB-C Cable', 'Accessories', 12.99, 300, 'Fast charging USB-C cable'),
        ('Office Chair', 'Furniture', 249.99, 45, 'Ergonomic office chair'),
        ('Standing Desk', 'Furniture', 499.99, 20, 'Adjustable standing desk'),
        ('Monitor 27"', 'Electronics', 349.99, 60, '4K UHD monitor'),
        ('Keyboard Mechanical', 'Electronics', 89.99, 80, 'RGB mechanical keyboard'),
        ('Webcam HD', 'Electronics', 79.99, 100, '1080p webcam'),
        ('Desk Lamp', 'Accessories', 39.99, 120, 'LED desk lamp'),
        ('Notebook Pack', 'Office Supplies', 9.99, 500, 'Pack of 5 notebooks'),
        ('Pen Set', 'Office Supplies', 14.99, 200, 'Professional pen set'),
        ('External SSD 1TB', 'Electronics', 149.99, 75, 'Fast portable SSD'),
    ]
    
    cursor.executemany(
        "INSERT INTO products (product_name, category, price, stock_quantity, description) VALUES (?, ?, ?, ?, ?)",
        products
    )
    
    # Insert sample orders
    orders = [
        (1, '2024-01-15 10:30:00', 1329.98, 'delivered', '123 Main St, City, State 12345'),
        (2, '2024-01-16 14:20:00', 279.98, 'delivered', '456 Oak Ave, Town, State 67890'),
        (3, '2024-02-01 09:15:00', 749.98, 'shipped', '789 Pine Rd, Village, State 13579'),
        (1, '2024-02-10 11:45:00', 89.99, 'delivered', '123 Main St, City, State 12345'),
        (4, '2024-02-15 16:30:00', 42.98, 'cancelled', '321 Elm St, City, State 24680'),
        (5, '2024-03-01 13:00:00', 1949.96, 'processing', '654 Maple Dr, Town, State 35791'),
        (6, '2024-03-05 10:20:00', 349.99, 'pending', '987 Cedar Ln, Village, State 46802'),
        (7, '2024-03-10 15:45:00', 169.98, 'shipped', '147 Birch Ct, City, State 57913'),
    ]
    
    cursor.executemany(
        "INSERT INTO orders (customer_id, order_date, total_amount, status, shipping_address) VALUES (?, ?, ?, ?, ?)",
        orders
    )
    
    # Insert sample order items
    order_items = [
        (1, 1, 1, 1299.99),  # Order 1: Laptop
        (1, 2, 1, 29.99),    # Order 1: Mouse
        (2, 4, 1, 249.99),   # Order 2: Office Chair
        (2, 2, 1, 29.99),    # Order 2: Mouse
        (3, 5, 1, 499.99),   # Order 3: Standing Desk
        (3, 4, 1, 249.99),   # Order 3: Office Chair
        (4, 7, 1, 89.99),    # Order 4: Keyboard
        (5, 3, 2, 12.99),    # Order 5: USB Cables (2)
        (5, 9, 2, 39.99),    # Order 5: Desk Lamps (2)
        (6, 1, 1, 1299.99),  # Order 6: Laptop
        (6, 5, 1, 499.99),   # Order 6: Standing Desk
        (6, 8, 2, 79.99),    # Order 6: Webcams (2)
        (7, 6, 1, 349.99),   # Order 7: Monitor
        (8, 12, 1, 149.99),  # Order 8: SSD
        (8, 10, 2, 9.99),    # Order 8: Notebook Packs (2)
    ]
    
    cursor.executemany(
        "INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (?, ?, ?, ?)",
        order_items
    )
    
    # Insert sample employees
    employees = [
        ('Michael', 'Scott', 'michael.scott@company.com', 'Management', '2020-01-15', 95000.00, None),
        ('Jim', 'Halpert', 'jim.halpert@company.com', 'Sales', '2020-03-01', 65000.00, 1),
        ('Pam', 'Beesly', 'pam.beesly@company.com', 'Reception', '2020-03-15', 45000.00, 1),
        ('Dwight', 'Schrute', 'dwight.schrute@company.com', 'Sales', '2020-02-01', 70000.00, 1),
        ('Angela', 'Martin', 'angela.martin@company.com', 'Accounting', '2020-04-01', 55000.00, 1),
        ('Kevin', 'Malone', 'kevin.malone@company.com', 'Accounting', '2020-05-01', 48000.00, 5),
        ('Oscar', 'Martinez', 'oscar.martinez@company.com', 'Accounting', '2020-04-15', 58000.00, 5),
    ]
    
    cursor.executemany(
        "INSERT INTO employees (first_name, last_name, email, department, hire_date, salary, manager_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
        employees
    )
    
    # Create some indexes for better performance
    cursor.execute("CREATE INDEX idx_customers_email ON customers(email)")
    cursor.execute("CREATE INDEX idx_orders_customer ON orders(customer_id)")
    cursor.execute("CREATE INDEX idx_order_items_order ON order_items(order_id)")
    cursor.execute("CREATE INDEX idx_order_items_product ON order_items(product_id)")
    cursor.execute("CREATE INDEX idx_employees_department ON employees(department)")
    
    # Create a view
    cursor.execute("""
        CREATE VIEW customer_order_summary AS
        SELECT 
            c.customer_id,
            c.first_name || ' ' || c.last_name AS customer_name,
            c.email,
            COUNT(o.order_id) AS total_orders,
            COALESCE(SUM(o.total_amount), 0) AS total_spent,
            MAX(o.order_date) AS last_order_date
        FROM customers c
        LEFT JOIN orders o ON c.customer_id = o.customer_id
        GROUP BY c.customer_id, c.first_name, c.last_name, c.email
    """)
    
    conn.commit()
    
    # Print summary
    print(f"\n✓ Created database with:")
    print(f"  - {len(customers)} customers")
    print(f"  - {len(products)} products")
    print(f"  - {len(orders)} orders")
    print(f"  - {len(order_items)} order items")
    print(f"  - {len(employees)} employees")
    print(f"  - 5 tables")
    print(f"  - 4 indexes")
    print(f"  - 1 view")
    
    conn.close()
    return db_path

def launch_qt_browser(db_path: str):
    """Launch the Qt browser with the SQLite database."""
    
    print(f"\n{'='*60}")
    print("Launching Qt Browser with SQLite database...")
    print(f"{'='*60}\n")
    
    # Use subprocess to run the Qt browser
    cmd = [
        sys.executable,
        "./run_qt_browser.py",
        "--db-file",
        db_path
    ]
    
    print(f"Running: {' '.join(cmd)}\n")
    
    result = subprocess.run(cmd, cwd="/workspaces/dbutils")
    
    return result.returncode

def main():
    """Main function."""
    
    # Create test database path
    db_dir = Path("/tmp/dbutils_test")
    db_dir.mkdir(exist_ok=True)
    db_path = str(db_dir / "test_database.db")
    
    print("="*60)
    print("Qt Browser SQLite Test")
    print("="*60)
    
    # Create the database
    create_test_database(db_path)
    
    # Launch the browser
    exit_code = launch_qt_browser(db_path)
    
    print(f"\nQt Browser exited with code: {exit_code}")
    
    return exit_code

if __name__ == "__main__":
    sys.exit(main())
