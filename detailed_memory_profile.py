#!/usr/bin/env python3
"""Script to profile specific functions with memory usage tracking."""

from memory_profiler import profile

from dbutils.db_browser import SearchIndex, get_all_tables_and_columns
from dbutils.utils import edit_distance, fuzzy_match


@profile
def test_edit_distance_memory():
    """Test memory usage of edit distance function."""
    distances = []
    for _ in range(5000):
        dist = edit_distance(f"TABLE_NAME_{_}", f"TABLE_NAME_{_ + 1}")
        distances.append(dist)
    return distances


@profile
def test_fuzzy_match_memory():
    """Test memory usage of fuzzy match function."""
    results = []
    for _ in range(5000):
        fuzzy_match(f"CUSTOMER_ORDER_TABLE_{_}", "CUST")
    return results


@profile
def test_data_loading_memory():
    """Test memory usage of data loading and indexing."""
    all_data = []
    for _ in range(20):
        tables, columns = get_all_tables_and_columns(use_mock=True)
        all_data.append((tables, columns))

    search_indexes = []
    for tables, columns in all_data:
        search_index = SearchIndex()
        search_index.build_index(tables, columns)
        search_indexes.append(search_index)

    return all_data, search_indexes


def run_memory_profiling():
    """Run all memory profiling tests."""
    print("Running memory profiling tests...")

    # Test edit distance
    distances = test_edit_distance_memory()
    print(f"Calculated {len(distances)} edit distances")

    # Test fuzzy matching
    results = test_fuzzy_match_memory()
    print(f"Performed {len(results)} fuzzy matches")

    # Test data loading
    data, indexes = test_data_loading_memory()
    print(f"Loaded {len(data)} sets of data and built {len(indexes)} search indexes")


if __name__ == "__main__":
    run_memory_profiling()
