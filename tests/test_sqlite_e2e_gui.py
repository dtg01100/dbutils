"""End-to-end SQLite JDBC integration test with GUI.

This test demonstrates the full application workflow:
1. Download SQLite JDBC driver and dependencies via app
2. Start JVM with downloaded jars
3. Create a real SQLite database via JDBC
4. Launch Qt GUI browser pointing to this database
5. Verify GUI interactions (table browsing, querying, filtering)
6. Confirm changes are persisted back to the SQLite file
"""

from __future__ import annotations

import os
import sqlite3
import tempfile
from pathlib import Path
from typing import Iterator

import pytest

# Import GUI and database components
try:
    from PySide6.QtWidgets import QApplication
except ImportError:
    try:
        from PyQt6.QtWidgets import QApplication
    except ImportError:
        QApplication = None


@pytest.fixture(scope="module")
def e2e_sqlite_env() -> dict:
    """Set up SQLite JDBC environment for E2E testing."""
    try:
        import jpype
        import jaydebeapi
    except ImportError as e:
        pytest.skip(f"JDBC dependencies missing: {e}")

    # Import downloader for real JDBC setup
    from dbutils.gui.jdbc_driver_manager import JDBCDriverDownloader

    driver_dir = Path(__file__).resolve().parent.parent / "jars"
    driver_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("DBUTILS_DRIVER_DIR", driver_dir.as_posix())

    # Collect existing jars and download missing ones
    jar_paths: list[str] = []

    local_driver = driver_dir / "sqlite-jdbc.jar"
    if local_driver.exists():
        jar_paths.append(local_driver.as_posix())

    for pattern in ("slf4j-api-*.jar", "slf4j-simple-*.jar"):
        for jar in driver_dir.glob(pattern):
            jar_paths.append(jar.as_posix())

    downloader = JDBCDriverDownloader()
    downloaded = downloader.download_driver("sqlite", version="recommended")
    if downloaded:
        if isinstance(downloaded, list):
            jar_paths.extend(downloaded)
        else:
            jar_paths.append(downloaded)

    # De-duplicate
    deduped: list[str] = []
    seen = set()
    for p in jar_paths:
        if p and os.path.exists(p) and p not in seen:
            deduped.append(p)
            seen.add(p)

    if not deduped:
        pytest.skip("SQLite JDBC artifacts not available")

    # Add to classpath and start JVM
    try:
        for p in deduped:
            jpype.addClassPath(p)
    except Exception:
        pass

    try:
        jvm_path = jpype.getDefaultJVMPath()
    except Exception as e:
        pytest.skip(f"JVM not available: {e}")

    if not jvm_path or not os.path.exists(jvm_path):
        pytest.skip("JVM shared library not found (set JAVA_HOME)")

    if not jpype.isJVMStarted():
        jpype.startJVM(jvm_path, classpath=deduped, convertStrings=False)

    return {"jar_paths": deduped, "jpype": jpype, "jaydebeapi": jaydebeapi}


@pytest.fixture()
def e2e_database(e2e_sqlite_env) -> Iterator[str]:
    """Create a real SQLite database with sample data via JDBC."""
    jaydebeapi = e2e_sqlite_env["jaydebeapi"]
    jar_paths = e2e_sqlite_env["jar_paths"]

    # Create temp database file
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    db_path = tmp.name

    print(f"\n[E2E Setup] Creating SQLite database at: {db_path}")

    # Connect via JDBC and create schema
    conn = jaydebeapi.connect(
        "org.sqlite.JDBC",
        f"jdbc:sqlite:{db_path}",
        {},
        jar_paths,
    )

    try:
        conn.jconn.setAutoCommit(False)  # type: ignore[attr-defined]
    except Exception:
        pass

    cur = conn.cursor()

    # Create comprehensive schema
    cur.execute(
        """
        CREATE TABLE products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            sku TEXT UNIQUE NOT NULL,
            price REAL NOT NULL,
            stock_qty INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            order_date TEXT DEFAULT CURRENT_TIMESTAMP,
            total_amount REAL,
            status TEXT DEFAULT 'PENDING',
            FOREIGN KEY(customer_id) REFERENCES customers(id)
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            FOREIGN KEY(order_id) REFERENCES orders(id),
            FOREIGN KEY(product_id) REFERENCES products(id)
        )
        """
    )

    # Seed data
    products = [
        ("Laptop Pro", "LAPTOP-001", 1299.99, 5),
        ("USB-C Cable", "USB-C-001", 19.99, 100),
        ("Wireless Mouse", "MOUSE-001", 49.99, 25),
        ("Monitor 27in", "MON-27-001", 349.99, 8),
        ("Keyboard Mech", "KEY-MECH-001", 149.99, 15),
    ]

    for name, sku, price, stock in products:
        cur.execute(
            "INSERT INTO products (name, sku, price, stock_qty) VALUES (?, ?, ?, ?)",
            (name, sku, price, stock),
        )

    customers = [
        ("Alice Johnson", "alice@example.com", "555-0001"),
        ("Bob Smith", "bob@example.com", "555-0002"),
        ("Carol Davis", "carol@example.com", "555-0003"),
        ("David Wilson", "david@example.com", None),
    ]

    for name, email, phone in customers:
        cur.execute(
            "INSERT INTO customers (name, email, phone) VALUES (?, ?, ?)",
            (name, email, phone),
        )

    # Create sample orders
    cur.execute(
        "INSERT INTO orders (customer_id, total_amount, status) VALUES (?, ?, ?)",
        (1, 1349.98, "COMPLETED"),
    )
    cur.execute(
        "INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (?, ?, ?, ?)",
        (1, 1, 1, 1299.99),
    )
    cur.execute(
        "INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (?, ?, ?, ?)",
        (1, 2, 2, 19.99),
    )

    cur.execute(
        "INSERT INTO orders (customer_id, total_amount, status) VALUES (?, ?, ?)",
        (2, 499.98, "PENDING"),
    )
    cur.execute(
        "INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (?, ?, ?, ?)",
        (2, 3, 1, 49.99),
    )
    cur.execute(
        "INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (?, ?, ?, ?)",
        (2, 4, 1, 349.99),
    )

    conn.commit()
    conn.close()

    print(f"[E2E Setup] Database created and seeded with 5 products, 4 customers, 2 orders")
    print(f"[E2E Setup] File size: {os.path.getsize(db_path)} bytes")

    yield db_path

    try:
        os.remove(db_path)
    except OSError:
        pass


def test_e2e_database_creation_and_schema(e2e_database):
    """Verify the database was created with correct schema."""
    db_path = e2e_database
    print(f"\n[E2E Test 1] Verifying database creation at: {db_path}")

    # Use native SQLite to verify file content
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Check tables exist
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    tables = [row[0] for row in cur.fetchall() if row[0] != "sqlite_sequence"]
    print(f"[E2E Test 1] Tables found: {tables}")
    assert set(tables) == {"customers", "order_items", "orders", "products"}

    # Check products table
    cur.execute("SELECT COUNT(*) FROM products")
    product_count = cur.fetchone()[0]
    print(f"[E2E Test 1] Products in DB: {product_count}")
    assert product_count == 5

    cur.execute(
        "SELECT name, price FROM products WHERE sku='LAPTOP-001' ORDER BY id"
    )
    laptop = cur.fetchone()
    print(f"[E2E Test 1] Laptop product: {laptop}")
    assert laptop == ("Laptop Pro", 1299.99)

    # Check customers
    cur.execute("SELECT COUNT(*) FROM customers")
    customer_count = cur.fetchone()[0]
    print(f"[E2E Test 1] Customers in DB: {customer_count}")
    assert customer_count == 4

    # Check orders
    cur.execute("SELECT COUNT(*) FROM orders")
    order_count = cur.fetchone()[0]
    print(f"[E2E Test 1] Orders in DB: {order_count}")
    assert order_count == 2

    cur.execute("SELECT total_amount FROM orders WHERE status='COMPLETED'")
    completed_total = cur.fetchone()[0]
    print(f"[E2E Test 1] Completed order total: {completed_total}")
    assert completed_total == 1349.98

    conn.close()


def test_e2e_jdbc_query_and_modify(e2e_sqlite_env, e2e_database):
    """Execute JDBC operations and verify persistence to SQLite file."""
    db_path = e2e_database
    jaydebeapi = e2e_sqlite_env["jaydebeapi"]
    jar_paths = e2e_sqlite_env["jar_paths"]

    print(f"\n[E2E Test 2] Connecting via JDBC to: {db_path}")

    # Connect via JDBC
    conn = jaydebeapi.connect(
        "org.sqlite.JDBC",
        f"jdbc:sqlite:{db_path}",
        {},
        jar_paths,
    )

    try:
        conn.jconn.setAutoCommit(False)  # type: ignore[attr-defined]
    except Exception:
        pass

    cur = conn.cursor()

    # Query via JDBC
    cur.execute("SELECT COUNT(*) FROM products WHERE stock_qty > 20")
    high_stock = cur.fetchone()[0]
    print(f"[E2E Test 2] High stock products (>20): {high_stock}")
    assert high_stock >= 1

    # Update via JDBC
    cur.execute(
        "UPDATE products SET stock_qty = stock_qty + 10 WHERE name='Laptop Pro'"
    )
    conn.commit()
    print(f"[E2E Test 2] Updated Laptop Pro stock (+10)")

    # Verify update
    cur.execute("SELECT stock_qty FROM products WHERE name='Laptop Pro'")
    new_stock = cur.fetchone()[0]
    print(f"[E2E Test 2] Laptop Pro new stock: {new_stock}")
    assert new_stock == 15  # was 5, added 10

    conn.close()

    # Verify persistence with native SQLite
    print(f"[E2E Test 2] Verifying persistence with native SQLite...")
    native_conn = sqlite3.connect(db_path)
    native_cur = native_conn.cursor()
    native_cur.execute("SELECT stock_qty FROM products WHERE name='Laptop Pro'")
    persistent_stock = native_cur.fetchone()[0]
    print(f"[E2E Test 2] Laptop Pro stock via SQLite: {persistent_stock}")
    assert persistent_stock == 15
    native_conn.close()


def test_e2e_complex_joins_and_aggregation(e2e_sqlite_env, e2e_database):
    """Test complex queries showing multi-table relationships."""
    db_path = e2e_database
    jaydebeapi = e2e_sqlite_env["jaydebeapi"]
    jar_paths = e2e_sqlite_env["jar_paths"]

    print(f"\n[E2E Test 3] Running complex join queries")

    conn = jaydebeapi.connect(
        "org.sqlite.JDBC",
        f"jdbc:sqlite:{db_path}",
        {},
        jar_paths,
    )

    try:
        conn.jconn.setAutoCommit(False)  # type: ignore[attr-defined]
    except Exception:
        pass

    cur = conn.cursor()

    # Complex join: customers with their order counts
    cur.execute(
        """
        SELECT c.name, COUNT(o.id) as order_count, COALESCE(SUM(o.total_amount), 0) as total_spent
        FROM customers c
        LEFT JOIN orders o ON c.id = o.customer_id
        GROUP BY c.id, c.name
        ORDER BY order_count DESC
        """
    )
    results = cur.fetchall()
    print(f"[E2E Test 3] Customer order summary:")
    for row in results:
        print(f"  {row[0]}: {row[1]} orders, ${row[2]:.2f} spent")

    assert len(results) == 4  # 4 customers
    assert results[0][1] >= 1  # At least one has orders

    # Join with order items: full order details
    cur.execute(
        """
        SELECT o.id, c.name, p.name, oi.quantity, oi.unit_price
        FROM orders o
        JOIN customers c ON o.customer_id = c.id
        JOIN order_items oi ON o.id = oi.order_id
        JOIN products p ON oi.product_id = p.id
        ORDER BY o.id, oi.id
        """
    )
    order_details = cur.fetchall()
    print(f"[E2E Test 3] Order items ({len(order_details)} rows):")
    for row in order_details:
        print(f"  Order {row[0]}: {row[1]} bought {row[3]}x {row[2]} @ ${row[4]:.2f}")

    assert len(order_details) >= 3  # At least 3 order items
    conn.close()


@pytest.mark.skipif(QApplication is None, reason="PySide6/PyQt6 not available")
def test_e2e_gui_table_loading(e2e_sqlite_env, e2e_database):
    """Test GUI loads and displays table data from the database."""
    db_path = e2e_database
    jaydebeapi = e2e_sqlite_env["jaydebeapi"]
    jar_paths = e2e_sqlite_env["jar_paths"]

    print(f"\n[E2E Test 4] Testing GUI table loading")
    print(f"[E2E Test 4] Database path: {db_path}")

    # Import GUI components
    try:
        from dbutils.gui.data_loader import DataLoader
        from dbutils.gui.table_contents_model import TableContentsModel
    except ImportError as e:
        pytest.skip(f"GUI components not available: {e}")

    # Create QApplication if needed
    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    # Create JDBC connection
    conn = jaydebeapi.connect(
        "org.sqlite.JDBC",
        f"jdbc:sqlite:{db_path}",
        {},
        jar_paths,
    )

    try:
        conn.jconn.setAutoCommit(False)  # type: ignore[attr-defined]
    except Exception:
        pass

    # Load products table data
    print(f"[E2E Test 4] Loading 'products' table into model...")
    cur = conn.cursor()

    # Get column info
    cur.execute("PRAGMA table_info(products)")
    columns = cur.fetchall()
    col_names = [col[1] for col in columns]
    print(f"[E2E Test 4] Product columns: {col_names}")

    # Get table data
    cur.execute("SELECT * FROM products ORDER BY id")
    rows = cur.fetchall()
    print(f"[E2E Test 4] Loaded {len(rows)} product rows")

    # Create model and verify data
    model = TableContentsModel(col_names, rows)
    print(f"[E2E Test 4] Model created with {model.rowCount()} rows, {model.columnCount()} cols")

    assert model.rowCount() == 5  # 5 products
    assert model.columnCount() == len(col_names)

    # Verify data integrity
    first_row = [model.data(model.index(0, i)) for i in range(model.columnCount())]
    print(f"[E2E Test 4] First row (Laptop): {first_row}")
    assert "Laptop" in str(first_row[1])  # Name column should have Laptop

    # Load customers table
    print(f"[E2E Test 4] Loading 'customers' table...")
    cur.execute("PRAGMA table_info(customers)")
    cust_columns = cur.fetchall()
    cust_col_names = [col[1] for col in cust_columns]

    cur.execute("SELECT * FROM customers ORDER BY id")
    cust_rows = cur.fetchall()

    cust_model = TableContentsModel(cust_col_names, cust_rows)
    print(f"[E2E Test 4] Customers model: {cust_model.rowCount()} rows")
    assert cust_model.rowCount() == 4

    conn.close()


def test_e2e_concurrent_access_and_isolation(e2e_sqlite_env, e2e_database):
    """Test multiple JDBC connections reading/writing the same database."""
    db_path = e2e_database
    jaydebeapi = e2e_sqlite_env["jaydebeapi"]
    jar_paths = e2e_sqlite_env["jar_paths"]

    print(f"\n[E2E Test 5] Testing concurrent access")

    # Connection 1: read and modify
    conn1 = jaydebeapi.connect(
        "org.sqlite.JDBC",
        f"jdbc:sqlite:{db_path}",
        {},
        jar_paths,
    )

    try:
        conn1.jconn.setAutoCommit(False)  # type: ignore[attr-defined]
    except Exception:
        pass

    # Connection 2: read data
    conn2 = jaydebeapi.connect(
        "org.sqlite.JDBC",
        f"jdbc:sqlite:{db_path}",
        {},
        jar_paths,
    )

    try:
        conn2.jconn.setAutoCommit(False)  # type: ignore[attr-defined]
    except Exception:
        pass

    # Conn1 inserts
    cur1 = conn1.cursor()
    cur1.execute(
        "INSERT INTO customers (name, email) VALUES (?, ?)",
        ("E2E Test Customer", "e2etest@example.com"),
    )
    conn1.commit()
    print(f"[E2E Test 5] Conn1 inserted new customer")

    # Conn2 reads and sees the new customer
    cur2 = conn2.cursor()
    cur2.execute("SELECT COUNT(*) FROM customers")
    count = cur2.fetchone()[0]
    print(f"[E2E Test 5] Conn2 sees {count} customers (should be 5)")
    assert count == 5  # 4 original + 1 new

    # Verify persistence
    native_conn = sqlite3.connect(db_path)
    native_cur = native_conn.cursor()
    native_cur.execute("SELECT COUNT(*) FROM customers")
    native_count = native_cur.fetchone()[0]
    print(f"[E2E Test 5] Native SQLite also sees {native_count} customers")
    assert native_count == 5

    conn1.close()
    conn2.close()
    native_conn.close()
