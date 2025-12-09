#!/usr/bin/env python3
"""
Verify SQLite integration without launching the full GUI.
Tests that the database loading functions work correctly with SQLite.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from dbutils.db_browser import get_all_tables_and_columns

def test_sqlite_loading():
    """Test loading tables and columns from SQLite database."""
    
    # Use the test database created by test_qt_with_sqlite.py
    db_path = "/tmp/dbutils_test/test_database.db"
    
    if not os.path.exists(db_path):
        print(f"❌ Test database not found: {db_path}")
        print("   Run test_qt_with_sqlite.py first to create the database.")
        return False
    
    print("="*60)
    print("SQLite Integration Verification")
    print("="*60)
    print(f"\nDatabase: {db_path}")
    
    # Load tables and columns
    print("\n1. Loading tables and columns...")
    try:
        tables, columns = get_all_tables_and_columns(db_file=db_path)
        print(f"   ✓ Loaded {len(tables)} tables")
        print(f"   ✓ Loaded {len(columns)} columns")
    except Exception as e:
        print(f"   ❌ Error loading data: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Display tables
    print("\n2. Tables found:")
    for table in sorted(tables, key=lambda t: t.name):
        print(f"   - {table.schema}.{table.name} ({table.remarks})")
    
    # Display column count per table
    print("\n3. Columns per table:")
    from collections import defaultdict
    cols_by_table = defaultdict(list)
    for col in columns:
        cols_by_table[col.table].append(col)
    
    for table_name in sorted(cols_by_table.keys()):
        cols = cols_by_table[table_name]
        print(f"   - {table_name}: {len(cols)} columns")
        for col in cols[:3]:  # Show first 3 columns
            nullable = "NULL" if col.nulls == 'Y' else "NOT NULL"
            print(f"      • {col.name} {col.typename} {nullable}")
        if len(cols) > 3:
            print(f"      ... and {len(cols) - 3} more")
    
    # Test pagination
    print("\n4. Testing pagination...")
    try:
        tables_page1, _ = get_all_tables_and_columns(db_file=db_path, limit=3, offset=0)
        tables_page2, _ = get_all_tables_and_columns(db_file=db_path, limit=3, offset=3)
        print(f"   ✓ Page 1: {len(tables_page1)} tables")
        print(f"     {[t.name for t in tables_page1]}")
        print(f"   ✓ Page 2: {len(tables_page2)} tables")
        print(f"     {[t.name for t in tables_page2]}")
    except Exception as e:
        print(f"   ❌ Pagination error: {e}")
        return False
    
    # Summary
    print("\n" + "="*60)
    print("✓ All tests passed!")
    print("="*60)
    
    return True

if __name__ == "__main__":
    success = test_sqlite_loading()
    sys.exit(0 if success else 1)
