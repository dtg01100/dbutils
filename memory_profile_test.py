#!/usr/bin/env python3
"""Script to profile memory usage."""

from dbutils.db_browser import get_all_tables_and_columns, SearchIndex
from dbutils.utils import edit_distance
import time

def profile_memory_intensive_operations():
    """Profile memory usage of intensive operations."""
    print("Starting memory profiling...")
    
    # Load data multiple times to see memory patterns
    all_data = []
    for i in range(50):
        tables, columns = get_all_tables_and_columns(use_mock=True)
        all_data.append((tables, columns))
        print(f"Loaded iteration {i+1}")
    
    # Build search indexes 
    search_indexes = []
    for i, (tables, columns) in enumerate(all_data):
        search_index = SearchIndex()
        search_index.build_index(tables, columns)
        search_indexes.append(search_index)
        print(f"Built search index {i+1}")
    
    # Perform many edit distance calculations (known CPU/Memory intensive)
    distances = []
    for i in range(1000):
        dist = edit_distance(f"TABLE_NAME_{i}", f"TABLE_NAME_{i+1}")
        distances.append(dist)
        if i % 200 == 0:
            print(f"Completed {i} edit distance calculations")
    
    print(f"Stored {len(distances)} distances in memory")
    print("Memory profiling completed.")

if __name__ == "__main__":
    profile_memory_intensive_operations()