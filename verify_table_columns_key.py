#!/usr/bin/env python3
"""Test that table_columns dictionary key lookup works correctly in async path."""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from dbutils.db_browser import ColumnInfo

# Simulate the table_columns dictionary as it's built in the GUI
table_columns = {}

# This is how columns are added (line 2394 in qt_app.py)
schema = "PUBLIC"
table = "USERS"
table_key = f"{schema}.{table}"  # String key format

col1 = ColumnInfo(schema=schema, table=table, name="ID", typename="INTEGER", 
                  length=None, scale=None, nulls="N", remarks="")
col2 = ColumnInfo(schema=schema, table=table, name="NAME", typename="VARCHAR", 
                  length=100, scale=None, nulls="Y", remarks="")

if table_key not in table_columns:
    table_columns[table_key] = []
table_columns[table_key].append(col1)
table_columns[table_key].append(col2)

print("Dictionary keys:", list(table_columns.keys()))
print()

# OLD INCORRECT LOOKUP (tuple key)
print("❌ OLD INCORRECT LOOKUP:")
cols_tuple = table_columns.get((schema, table), [])
print(f"  table_columns.get(({schema!r}, {table!r}), []) = {cols_tuple}")
print(f"  Length: {len(cols_tuple)}")
print()

# NEW CORRECT LOOKUP (string key)
print("✅ NEW CORRECT LOOKUP:")
cols_string = table_columns.get(f"{schema}.{table}", [])
print(f"  table_columns.get(f\"{{{schema!r}}}.{{{table!r}}}\", []) = {cols_string}")
print(f"  Length: {len(cols_string)}")
if cols_string:
    print(f"  Columns: {[c.name for c in cols_string]}")
print()

if len(cols_string) > 0:
    print("✅ FIX VERIFIED: String key lookup works correctly")
    sys.exit(0)
else:
    print("❌ FIX FAILED: Still getting empty list")
    sys.exit(1)
