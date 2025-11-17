#!/usr/bin/env python3
"""Test DACDATA schema queries to see what works."""

import subprocess
import tempfile
import json
import csv
import io
import os


def query_runner(sql: str):
    """Run an external query_runner command and return parsed results."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as f:
        f.write(sql)
        temp_file = f.name

    try:
        result = subprocess.run(["query_runner", "-t", "db2", temp_file], capture_output=True, text=True)
        print(f"Return code: {result.returncode}")
        print(f"STDOUT:\n{result.stdout[:500]}")
        if result.stderr:
            print(f"STDERR:\n{result.stderr[:500]}")

        if result.returncode != 0:
            return None

        # Try JSON first
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            # Assume tab-separated with header
            reader = csv.DictReader(io.StringIO(result.stdout), delimiter="\t")
            return list(reader)
    finally:
        os.unlink(temp_file)


# Test 1: Query tables in DACDATA
print("=" * 70)
print("Test 1: Query QSYS2.SYSTABLES for DACDATA schema")
print("=" * 70)
sql1 = """
SELECT
    TABLE_SCHEMA,
    TABLE_NAME,
    TABLE_TEXT
FROM QSYS2.SYSTABLES
WHERE TABLE_TYPE = 'T'
AND SYSTEM_TABLE = 'N'
AND TABLE_SCHEMA = 'DACDATA'
ORDER BY TABLE_NAME
FETCH FIRST 5 ROWS ONLY
"""
result1 = query_runner(sql1)
if result1:
    print(f"\nFound {len(result1)} tables:")
    for row in result1:
        print(f"  - {row}")
else:
    print("Query failed or returned no results")

# Test 2: Query columns in DACDATA
print("\n" + "=" * 70)
print("Test 2: Query QSYS2.SYSCOLUMNS for DACDATA schema")
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
WHERE TABLE_SCHEMA = 'DACDATA'
ORDER BY TABLE_NAME, ORDINAL_POSITION
FETCH FIRST 10 ROWS ONLY
"""
result2 = query_runner(sql2)
if result2:
    print(f"\nFound {len(result2)} columns:")
    for row in result2:
        print(f"  - {row}")
else:
    print("Query failed or returned no results")

# Test 3: Count tables
print("\n" + "=" * 70)
print("Test 3: Count tables in DACDATA")
print("=" * 70)
sql3 = """
SELECT COUNT(*) as TABLE_COUNT
FROM QSYS2.SYSTABLES
WHERE TABLE_TYPE = 'T'
AND SYSTEM_TABLE = 'N'
AND TABLE_SCHEMA = 'DACDATA'
"""
result3 = query_runner(sql3)
if result3:
    print(f"\nTable count result:")
    for row in result3:
        print(f"  - {row}")
else:
    print("Query failed or returned no results")

# Test 4: Try without schema filter to see what's available
print("\n" + "=" * 70)
print("Test 4: Sample schemas available")
print("=" * 70)
sql4 = """
SELECT DISTINCT TABLE_SCHEMA
FROM QSYS2.SYSTABLES
WHERE TABLE_TYPE = 'T'
AND SYSTEM_TABLE = 'N'
ORDER BY TABLE_SCHEMA
FETCH FIRST 20 ROWS ONLY
"""
result4 = query_runner(sql4)
if result4:
    print(f"\nFound {len(result4)} schemas:")
    for row in result4:
        print(f"  - {row.get('TABLE_SCHEMA', row)}")
else:
    print("Query failed or returned no results")
