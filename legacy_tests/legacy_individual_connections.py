#!/usr/bin/env python3
"""Test individual database connections to capture detailed results."""

from tests.database_test_utils import DatabaseConnectionManager


def test_database_connections():
    """Test connections to each database type."""
    dm = DatabaseConnectionManager()
    databases = ["sqlite", "h2", "derby", "hsqldb", "duckdb"]

    results = {}

    for db_type in databases:
        print(f"Testing {db_type.upper()} connection...")
        try:
            conn = dm.get_connection(db_type)
            print(f"{db_type.upper()} connection: SUCCESS")
            results[db_type] = {"success": True, "error": None}
            conn.close()
        except Exception as e:
            print(f"{db_type.upper()} connection: FAILED - {e}")
            results[db_type] = {"success": False, "error": str(e)}

    return results


if __name__ == "__main__":
    results = test_database_connections()
    print("\n=== CONNECTION TEST RESULTS ===")
    for db_type, result in results.items():
        status = "SUCCESS" if result["success"] else "FAILED"
        print(f"{db_type.upper()}: {status}")
        if not result["success"]:
            print(f"  Error: {result['error']}")
