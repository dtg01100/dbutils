#!/usr/bin/env python3
"""Test with actual schemas that exist."""

import csv
import io
import json
import os
import subprocess
import tempfile


def query_runner(sql: str):
    """Run an external query_runner command and return parsed results."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as f:
        f.write(sql)
        temp_file = f.name

    try:
        result = subprocess.run(["query_runner", "-t", "db2", temp_file], capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            print(f"Error: {result.stderr}")
            return None

        # Try JSON first
        try:
            data = json.loads(result.stdout)
            return data
        except json.JSONDecodeError:
            # Assume tab-separated with header
            reader = csv.DictReader(io.StringIO(result.stdout), delimiter="\t")
            return list(reader)
    except Exception as e:
        print(f"Exception: {e}")
        return None
    finally:
        if os.path.exists(temp_file):
            os.unlink(temp_file)


# Test with QGPL schema (which we know exists)
print("=" * 70)
print("Test: Query tables in QGPL schema")
print("=" * 70)
sql = """
SELECT
    TABLE_SCHEMA,
    TABLE_NAME,
    TABLE_TEXT
FROM QSYS2.SYSTABLES
WHERE TABLE_TYPE = 'T'
AND SYSTEM_TABLE = 'N'
AND TABLE_SCHEMA = 'QGPL'
ORDER BY TABLE_NAME
FETCH FIRST 10 ROWS ONLY
"""
result = query_runner(sql)
if result:
    print(f"\nFound {len(result)} tables in QGPL:")
    for i, row in enumerate(result, 1):
        schema = row.get("TABLE_SCHEMA", "N/A")
        name = row.get("TABLE_NAME", "N/A")
        text = row.get("TABLE_TEXT", "N/A")
        print(f"{i}. {schema}.{name} - {text}")
else:
    print("No tables found or query failed")

# Test columns for QGPL
print("\n" + "=" * 70)
print("Test: Query columns in QGPL schema")
print("=" * 70)
sql2 = """
SELECT
    TABLE_SCHEMA,
    TABLE_NAME,
    COLUMN_NAME,
    DATA_TYPE,
    LENGTH,
    SCALE,
    IS_NULLABLE,
    COLUMN_TEXT
FROM QSYS2.SYSCOLUMNS
WHERE TABLE_SCHEMA = 'QGPL'
ORDER BY TABLE_NAME, ORDINAL_POSITION
FETCH FIRST 15 ROWS ONLY
"""
result2 = query_runner(sql2)
if result2:
    print(f"\nFound {len(result2)} columns in QGPL:")
    for i, row in enumerate(result2, 1):
        table = row.get("TABLE_NAME", "N/A")
        col = row.get("COLUMN_NAME", "N/A")
        dtype = row.get("DATA_TYPE", "N/A")
        length = row.get("LENGTH", "N/A")
        nullable = row.get("IS_NULLABLE", "N/A")
        text = row.get("COLUMN_TEXT", "")
        print(f"{i}. {table}.{col} ({dtype}({length}), nullable={nullable}) - {text}")
else:
    print("No columns found or query failed")

# List all user schemas with table counts
print("\n" + "=" * 70)
print("Test: List all schemas with their table counts")
print("=" * 70)
sql3 = """
SELECT 
    TABLE_SCHEMA,
    COUNT(*) AS TABLE_COUNT
FROM QSYS2.SYSTABLES
WHERE TABLE_TYPE = 'T'
AND SYSTEM_TABLE = 'N'
AND TABLE_SCHEMA NOT LIKE 'Q%'
AND TABLE_SCHEMA NOT LIKE 'SYS%'
GROUP BY TABLE_SCHEMA
ORDER BY TABLE_COUNT DESC, TABLE_SCHEMA
FETCH FIRST 20 ROWS ONLY
"""
result3 = query_runner(sql3)
if result3:
    print(f"\nFound {len(result3)} user schemas:")
    for i, row in enumerate(result3, 1):
        schema = row.get("TABLE_SCHEMA", "N/A")
        count = row.get("TABLE_COUNT", "N/A")
        print(f"{i}. {schema}: {count} tables")
else:
    print("No schemas found or query failed")
