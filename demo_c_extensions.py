#!/usr/bin/env python3
"""Quick demo of C extensions performance."""

from dbutils.accelerated import fast_search_tables, fast_search_columns
from dbutils.db_browser import TableInfo, ColumnInfo

# Sample data
tables = [
    TableInfo("PROD", "USER_ACCOUNTS", "Main user account table"),
    TableInfo("PROD", "USER_PROFILES", "User profile details"),
    TableInfo("PROD", "ORDER_HISTORY", "Historical orders"),
    TableInfo("TEST", "USER_TEST_DATA", "Test user data"),
]

columns = [
    ColumnInfo("PROD", "USER_ACCOUNTS", "USER_ID", "INTEGER", None, None, "N", "Primary key"),
    ColumnInfo("PROD", "USER_ACCOUNTS", "USERNAME", "VARCHAR", 100, None, "N", "User login name"),
    ColumnInfo("PROD", "USER_PROFILES", "USER_ID", "INTEGER", None, None, "N", "Foreign key to USER_ACCOUNTS"),
    ColumnInfo("PROD", "USER_PROFILES", "EMAIL", "VARCHAR", 255, None, "Y", "Email address"),
]

print("=" * 60)
print("C Extensions Demo - Fast Search Operations")
print("=" * 60)

# Table search
print("\n1. Searching tables for 'USER':")
results = fast_search_tables(tables, "USER")
for table, score in results[:3]:
    print(f"   {table.name:20} (score: {score:.1f})")

# Column search
print("\n2. Searching columns for 'USER':")
results = fast_search_columns(columns, "USER")
for col, score in results[:3]:
    print(f"   {col.table}.{col.name:15} (score: {score:.1f})")

print("\n" + "=" * 60)
print("Extensions are working! 🚀")
print("=" * 60)
