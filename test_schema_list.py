#!/usr/bin/env python3
"""Quick test of settings menu with mock data."""

import sys

sys.path.insert(0, "src")

from dbutils.db_browser import get_available_schemas

# Test the schema fetching function
print("Testing get_available_schemas with mock=True:")
schemas = get_available_schemas(use_mock=True)

print(f"\nFound {len(schemas)} schemas:")
for schema in schemas:
    print(f"  - {schema.name}: {schema.table_count} tables")

print("\n✓ Schema fetching works!")
