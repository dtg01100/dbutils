#!/usr/bin/env python3
"""Script to profile intensive operations in dbutils for performance analysis."""

import time
from dbutils.db_browser import get_all_tables_and_columns, SearchIndex
from dbutils.map_db import infer_relationships
from dbutils.utils import edit_distance, fuzzy_match

def profile_data_loading():
    """Profile data loading operations."""
    print("Profiling data loading...")
    start_time = time.time()
    
    # Load mock data multiple times to get better profiling data
    for i in range(10):
        tables, columns = get_all_tables_and_columns(use_mock=True)
        print(f"Iteration {i+1}: Loaded {len(tables)} tables, {len(columns)} columns")
    
    elapsed = time.time() - start_time
    print(f"Data loading completed in {elapsed:.3f}s")
    return tables, columns

def profile_search_indexing(tables, columns):
    """Profile search index building and searching."""
    print("\nProfiling search indexing...")
    start_time = time.time()
    
    # Build search index
    search_index = SearchIndex()
    search_index.build_index(tables, columns)
    
    elapsed = time.time() - start_time
    print(f"Search index built in {elapsed:.3f}s")
    
    # Perform multiple searches
    search_terms = ["user", "customer", "order", "product", "id"]
    for term in search_terms:
        start_search = time.time()
        table_results = search_index.search_tables(term)
        column_results = search_index.search_columns(term)
        search_elapsed = time.time() - start_search
        print(f"Search for '{term}': {len(table_results)} tables, {len(column_results)} columns in {search_elapsed:.3f}s")

def profile_string_operations():
    """Profile string operations that might be bottlenecks."""
    print("\nProfiling string operations...")
    start_time = time.time()
    
    # Test edit distance calculations
    test_pairs = [
        ("USER", "USERS"),
        ("CUSTOMER", "CUSTOMERS"),
        ("ORDERS", "ORDER"),
        ("PRODUCT", "PRODUCTS"),
        ("TABLE_NAME", "TABLE_NAME_LONG"),
    ]
    
    for s1, s2 in test_pairs:
        for _ in range(1000):  # Repeat to get better profiling data
            dist = edit_distance(s1, s2)
    
    # Test fuzzy matching
    text_samples = [
        ("CUSTOMER_ORDER_TABLE", "CUST"),
        ("USER_PROFILE_INFO", "USER"),
        ("PRODUCT_CATALOG", "PROD"),
        ("ORDER_HISTORY", "ORD"),
        ("INVOICE_DETAILS", "INV"),
    ]
    
    for text, query in text_samples:
        for _ in range(1000):  # Repeat to get better profiling data
            match = fuzzy_match(text, query)
    
    elapsed = time.time() - start_time
    print(f"String operations completed in {elapsed:.3f}s")

def profile_relationship_inference(tables, columns):
    """Profile relationship inference logic."""
    print("\nProfiling relationship inference...")
    start_time = time.time()
    
    # Mock primary keys for relationship inference
    pks = []
    for table in tables:
        pks.append({
            "TABSCHEMA": table.schema,
            "TABNAME": table.name,
            "COLNAME": "ID",
            "TYPENAME": "INTEGER"
        })
    
    # Run inference multiple times
    for _ in range(100):
        relationships = infer_relationships(tables, columns, pks)
    
    elapsed = time.time() - start_time
    print(f"Relationship inference completed in {elapsed:.3f}s with {len(relationships)} relationships")

def main():
    """Run all profiling tests."""
    print("Starting comprehensive dbutils profiling...")
    
    # Profile data loading
    tables, columns = profile_data_loading()
    
    # Profile search functionality
    profile_search_indexing(tables, columns)
    
    # Profile string operations
    profile_string_operations()
    
    # Profile relationship inference if possible
    try:
        profile_relationship_inference(tables, columns)
    except Exception as e:
        print(f"Relationship inference profiling skipped: {e}")
    
    print("\nProfiling completed!")

if __name__ == "__main__":
    main()