#!/usr/bin/env python3
"""
Simple SQLite JDBC verification using jdbc_provider.JDBCConnection.

This script uses the bundled sqlite-jdbc.jar (jars/sqlite-jdbc.jar) and
JPype + JayDeBeApi to create an in-memory SQLite database, create a table,
insert rows, enumerate tables via sqlite_master, and introspect columns via PRAGMA.
"""

import os
import sys
from pathlib import Path

# Ensure local src is available for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dbutils.jdbc_provider import JDBCProvider, JDBCConnection


def main():
    print("=== SQLite JDBC Smoke Test ===\n")

    jar_path = Path("jars/sqlite-jdbc.jar").absolute()
    if not jar_path.exists():
        print(f"✗ sqlite-jdbc.jar not found at: {jar_path}")
        return 1

    print(f"Using SQLite JDBC JAR: {jar_path}")

    provider = JDBCProvider(
        name="SQLite (JDBC)",
        driver_class="org.sqlite.JDBC",
        jar_path=str(jar_path),
        url_template="jdbc:sqlite:{database}",
        default_user=None,
        default_password=None,
    )

    # Create a connection to an in-memory database
    # Use :memory: for in-memory DB that lives only in connection session
    try:
        conn = JDBCConnection(provider, {"database": ":memory:"})
        conn.connect()
        print("✓ Connected to in-memory SQLite via JDBC")

        # Create a test table and insert rows
        conn.query("CREATE TABLE IF NOT EXISTS test_table (id INTEGER PRIMARY KEY, name TEXT)")
        print("✓ Created test_table")
        conn.query("INSERT INTO test_table (name) VALUES ('alice')")
        print("✓ Inserted row 1")
        conn.query("INSERT INTO test_table (name) VALUES ('bob')")
        print("✓ Inserted row 2")
        conn.query("INSERT INTO test_table (name) VALUES ('charlie')")
        print("✓ Inserted row 3")

        # List tables using sqlite_master
        tables = conn.query("SELECT name, type, sql FROM sqlite_master WHERE type='table'")
        print(f"✓ sqlite_master returned {len(tables)} row(s)")
        for t in tables:
            print(f"  - {t.get('name')} (type={t.get('type')})")

        # Inspect columns for the test table using PRAGMA table_info
        cols = conn.query("PRAGMA table_info('test_table')")
        if not cols:
            print("✗ PRAGMA table_info returned no columns for 'test_table'")
            return 1

        print(f"✓ test_table has {len(cols)} column(s)")
        for c in cols:
            print(f"  - {c.get('name')} ({c.get('type')}) pk={c.get('pk')}")

        # Select rows to ensure data roundtrips
        rows = conn.query("SELECT id, name FROM test_table ORDER BY id")
        print(f"✓ Selected {len(rows)} rows from test_table")
        for r in rows:
            print(f"  - id={r.get('id')}, name={r.get('name')}")

    except Exception as e:
        import traceback
        print(f"✗ SQLite JDBC smoke test failed: {e}")
        print("Traceback:")
        traceback.print_exc()
        return 1
    finally:
        try:
            conn.close()
        except Exception:
            pass

    print("\n🎉 SQLite JDBC smoke test passed")
    return 0


if __name__ == '__main__':
    sys.exit(main())
