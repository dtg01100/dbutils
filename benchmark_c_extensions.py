#!/usr/bin/env python3
"""Benchmark C extensions vs Python implementation for search operations."""

import time
from dataclasses import dataclass
from typing import List

# Mock data structures
@dataclass
class TableInfo:
    schema: str
    name: str
    remarks: str

@dataclass
class ColumnInfo:
    schema: str
    table: str
    name: str
    typename: str
    remarks: str

def generate_test_data(n_tables=1000, n_cols_per_table=20):
    """Generate test data."""
    tables = []
    columns = []
    
    for i in range(n_tables):
        schema = f"SCHEMA{i % 10}"
        table_name = f"TABLE_{i:04d}_USER_DATA"
        tables.append(TableInfo(
            schema=schema,
            name=table_name,
            remarks=f"This is a test table for user data management system table {i}"
        ))
        
        for j in range(n_cols_per_table):
            columns.append(ColumnInfo(
                schema=schema,
                table=table_name,
                name=f"COL_{j:03d}_FIELD",
                typename="VARCHAR" if j % 2 == 0 else "INTEGER",
                remarks=f"Column {j} for data field in table {i}"
            ))
    
    return tables, columns

def python_search_tables(tables: List[TableInfo], query: str):
    """Python implementation of table search."""
    if not query.strip():
        return [(t, 1.0) for t in tables]
    
    query_lower = query.lower()
    results = []
    
    for table in tables:
        score = 0.0
        name_lower = table.name.lower()
        
        if query_lower == name_lower:
            score = 2.0
        elif query_lower in name_lower:
            score = 1.0
        elif any(word.startswith(query_lower) for word in table.name.lower().replace('_', ' ').split()):
            score = 0.6
        elif table.remarks and query_lower in table.remarks.lower():
            score = 0.8
        
        if score > 0:
            results.append((table, score))
    
    results.sort(key=lambda x: x[1], reverse=True)
    return results

def python_search_columns(columns: List[ColumnInfo], query: str):
    """Python implementation of column search."""
    if not query.strip():
        return [(c, 1.0) for c in columns]
    
    query_lower = query.lower()
    results = []
    
    for col in columns:
        score = 0.0
        name_lower = col.name.lower()
        typename_lower = col.typename.lower()
        
        if query_lower == name_lower:
            score = 2.0
        elif query_lower in name_lower:
            score = 1.0
        elif query_lower in typename_lower:
            score = 0.7
        elif col.remarks and query_lower in col.remarks.lower():
            score = 0.5
        
        if score > 0:
            results.append((col, score))
    
    results.sort(key=lambda x: x[1], reverse=True)
    return results

def main():
    print("=" * 70)
    print("C Extensions Performance Benchmark")
    print("=" * 70)
    
    # Try to import C extensions
    try:
        from dbutils.accelerated import fast_search_tables, fast_search_columns
        has_c_ext = True
        print("✓ C extensions available")
    except ImportError:
        has_c_ext = False
        print("✗ C extensions not available (run ./build_extensions.sh)")
        return
    
    print("\nGenerating test data...")
    tables, columns = generate_test_data(n_tables=2000, n_cols_per_table=25)
    print(f"  {len(tables):,} tables")
    print(f"  {len(columns):,} columns")
    
    test_queries = ["USER", "DATA", "FIELD", "VARCHAR", "TABLE_0123"]
    
    print("\n" + "=" * 70)
    print("TABLE SEARCH BENCHMARK")
    print("=" * 70)
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        
        # Python implementation
        start = time.perf_counter()
        py_results = python_search_tables(tables, query)
        py_time = time.perf_counter() - start
        
        # C implementation
        start = time.perf_counter()
        c_results = fast_search_tables(tables, query)
        c_time = time.perf_counter() - start
        
        speedup = py_time / c_time if c_time > 0 else 0
        
        print(f"  Python:  {py_time*1000:7.2f} ms ({len(py_results):,} results)")
        print(f"  C ext:   {c_time*1000:7.2f} ms ({len(c_results):,} results)")
        print(f"  Speedup: {speedup:.1f}x faster")
    
    print("\n" + "=" * 70)
    print("COLUMN SEARCH BENCHMARK")
    print("=" * 70)
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        
        # Python implementation
        start = time.perf_counter()
        py_results = python_search_columns(columns, query)
        py_time = time.perf_counter() - start
        
        # C implementation
        start = time.perf_counter()
        c_results = fast_search_columns(columns, query)
        c_time = time.perf_counter() - start
        
        speedup = py_time / c_time if c_time > 0 else 0
        
        print(f"  Python:  {py_time*1000:7.2f} ms ({len(py_results):,} results)")
        print(f"  C ext:   {c_time*1000:7.2f} ms ({len(c_results):,} results)")
        print(f"  Speedup: {speedup:.1f}x faster")
    
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print("C extensions provide significant performance improvements for")
    print("search operations, especially with large datasets.")
    print("=" * 70)

if __name__ == "__main__":
    main()
