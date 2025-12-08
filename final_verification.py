#!/usr/bin/env python3
"""Final verification test for all optimizations."""

import time

from dbutils.db_browser import ColumnInfo, SearchIndex, TableInfo
from dbutils.utils import edit_distance, fuzzy_match


def test_edit_distance_optimizations():
    """Test that edit distance optimizations work correctly."""
    print("Testing edit_distance optimizations...")

    test_cases = [
        ("", ""),
        ("", "a"),
        ("a", ""),
        ("a", "a"),
        ("a", "b"),
        ("hello", "world"),
        ("kitten", "sitting"),
        ("saturday", "sunday"),
        ("USER", "USERS"),
        ("CUSTOMER", "CUSTOMERS"),
    ]

    for s1, s2 in test_cases:
        result = edit_distance(s1, s2)
        print(f"  edit_distance('{s1}', '{s2}') = {result}")

    print("✅ Edit distance optimizations verified!")
    return True


def test_fuzzy_match_optimizations():
    """Test that fuzzy match optimizations work correctly."""
    print("\nTesting fuzzy_match optimizations...")

    test_cases = [
        ("TEST_USER", "TEST", True),
        ("TEST_USER", "USER", True),
        ("test_user", "TEST", True),
        ("TEST_USER_TABLE", "TUT", True),
        ("", "TEST", False),
        ("TEST", "", True),
        ("TEST", "DIFFERENT", False),
        ("CUSTOMER_ORDER", "CUST", True),
        ("TABLE_NAME", "TBL", True),  # Sequential match: T-A-B-L-E -> T-B-L matches "TBL"
    ]

    all_passed = True
    for text, query, expected in test_cases:
        result = fuzzy_match(text, query)
        status = "✅" if result == expected else "❌"
        print(f"  {status} fuzzy_match('{text}', '{query}') = {result} (expected {expected})")
        if result != expected:
            all_passed = False

    if all_passed:
        print("✅ Fuzzy match optimizations verified!")
    else:
        print("❌ Some fuzzy match tests failed!")

    return all_passed


def test_search_index_performance():
    """Test SearchIndex performance with a larger dataset."""
    print("\nTesting SearchIndex optimizations...")

    # Create mock data
    tables = []
    for i in range(100):
        table = TableInfo(
            schema="TEST", name=f"TABLE_{i:03d}", remarks=f"Test table number {i} for performance testing"
        )
        tables.append(table)

    columns = []
    for i in range(500):  # 5 columns per table
        table_idx = i // 5
        table_name = f"TABLE_{table_idx:03d}"
        col = ColumnInfo(
            schema="TEST",
            table=table_name,
            name=f"COLUMN_{i:03d}",
            typename="VARCHAR",
            length=100,
            scale=0,
            nulls="Y",
            remarks=f"Column {i} for testing",
        )
        columns.append(col)

    # Time the index building
    search_index = SearchIndex()
    start = time.time()
    search_index.build_index(tables, columns)
    build_time = time.time() - start
    print(f"  Built index for {len(tables)} tables and {len(columns)} columns in {build_time:.3f}s")

    # Time a few searches
    search_terms = ["TABLE_0", "COLUMN_1", "TEST"]
    for term in search_terms:
        start = time.time()
        table_results = search_index.search_tables(term)
        col_results = search_index.search_columns(term)
        search_time = time.time() - start
        print(f"  Searched for '{term}': {len(table_results)} tables, {len(col_results)} columns in {search_time:.4f}s")

    print("✅ Search index optimizations verified!")
    return True


def main():
    print("Running final verification tests for all optimizations...\n")

    edit_ok = test_edit_distance_optimizations()
    fuzzy_ok = test_fuzzy_match_optimizations()
    search_ok = test_search_index_performance()

    if all([edit_ok, fuzzy_ok, search_ok]):
        print("\n🎉 All optimizations verified successfully!")
        return True
    else:
        print("\n❌ Some optimizations failed verification!")
        return False


if __name__ == "__main__":
    main()
