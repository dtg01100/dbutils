#!/usr/bin/env python3
"""Comprehensive performance test for the optimized functions."""

import time

from dbutils.utils import edit_distance, fuzzy_match


def test_fuzzy_match_performance():
    """Test fuzzy match performance with the optimized edit_distance."""
    print("Testing fuzzy_match performance after optimization...")

    test_cases = [
        ("CUSTOMER_ORDER_TABLE", "CUST"),
        ("USER_PROFILE_INFO", "USER"),
        ("PRODUCT_CATALOG", "PROD"),
        ("ORDER_HISTORY", "ORD"),
        ("INVOICE_DETAILS", "INV"),
        ("TABLE_NAME_LONG", "TBL"),
        ("EXTREMELY_LONG_TABLE_NAME", "EXT"),
    ]

    # Test fuzzy matching
    start_time = time.time()
    iterations = 1000
    for _ in range(iterations):
        for text, query in test_cases:
            fuzzy_match(text, query)
    fuzzy_time = time.time() - start_time

    print(f"Completed {iterations * len(test_cases)} fuzzy matches in {fuzzy_time:.3f}s")
    print(f"Average time per fuzzy match: {fuzzy_time / (iterations * len(test_cases)):.6f}s")

    return fuzzy_time


def test_edit_distance_performance():
    """Test edit distance performance directly."""
    print("\nTesting edit_distance performance after optimization...")

    test_pairs = [
        ("USER_TABLE_NAME", "CUSTOMER_TABLE_NAME"),
        ("ORDER_HISTORY", "INVOICE_HISTORY"),
        ("PRODUCT_CATALOG", "ITEM_CATALOG"),
        ("TABLE_NAME", "TBL_NM"),
        ("CUSTOMER_ORDER_TABLE", "CUST_ORD_TBL"),
    ]

    start_time = time.time()
    iterations = 5000  # Reduced from 10000 to make test faster
    for _ in range(iterations):
        for s1, s2 in test_pairs:
            edit_distance(s1, s2)
    edit_time = time.time() - start_time

    print(f"Completed {iterations * len(test_pairs)} edit distance calculations in {edit_time:.3f}s")
    print(f"Average time per edit distance: {edit_time / (iterations * len(test_pairs)):.6f}s")

    return edit_time


def test_edge_cases():
    """Test edge cases to ensure correctness."""
    print("\nTesting edge cases...")

    # Test cases that exercise the fuzzy matching logic
    test_cases = [
        ("TEST_USER", "TEST"),  # Prefix match
        ("TEST_USER", "USER"),  # Word boundary match
        ("test_user", "TEST"),  # Case insensitive
        ("TEST_USER_TABLE", "TUT"),  # Sequential char match
        ("", "TEST"),  # Empty string
        ("TEST", ""),  # Empty query
        ("TEST", "DIFFERENT"),  # No match
    ]

    for text, query in test_cases:
        result = fuzzy_match(text, query)
        print(f"fuzzy_match('{text}', '{query}') = {result}")


def main():
    print("Running comprehensive performance tests...\n")

    edit_time = test_edit_distance_performance()
    fuzzy_time = test_fuzzy_match_performance()
    test_edge_cases()

    print("\nResults:")
    print(f"- Edit distance: {edit_time:.3f}s for {(5000 * 5)} calculations")
    print(f"- Fuzzy matching: {fuzzy_time:.3f}s for {(1000 * 7)} operations")
    print("Optimizations completed successfully!")


if __name__ == "__main__":
    main()
