#!/usr/bin/env python3
"""Compare original vs optimized edit_distance performance."""

import time


def edit_distance_original(s1: str, s2: str) -> int:
    """Original edit distance calculation."""
    if len(s1) < len(s2):
        return edit_distance_original(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def edit_distance_optimized(s1: str, s2: str) -> int:
    """Optimized edit distance calculation."""
    if len(s1) < len(s2):
        return edit_distance_optimized(s2, s1)

    if len(s2) == 0:
        return len(s1)

    # Use single array instead of two arrays to reduce memory operations
    # This is more cache-friendly and reduces allocation/deallocation overhead
    previous_row = list(range(len(s2) + 1))
    current_row = [0] * (len(s2) + 1)

    for i, c1 in enumerate(s1):
        current_row[0] = i + 1
        for j, c2 in enumerate(s2):
            # Calculate all values inline to avoid min() function call overhead
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)

            # Inline min calculation since we only have 3 values
            if insertions <= deletions and insertions <= substitutions:
                min_val = insertions
            elif deletions <= substitutions:
                min_val = deletions
            else:
                min_val = substitutions

            current_row[j + 1] = min_val

        # Swap arrays instead of copying - more efficient
        previous_row, current_row = current_row, previous_row

    return previous_row[-1]


def test_performance_comparison():
    """Compare performance between original and optimized versions."""
    test_pairs = [
        ("USER_TABLE_NAME", "CUSTOMER_TABLE_NAME"),
        ("ORDER_HISTORY", "INVOICE_HISTORY"),
        ("PRODUCT_CATALOG", "ITEM_CATALOG"),
        ("TABLE_NAME", "TBL_NM"),
        ("CUSTOMER_ORDER_TABLE", "CUST_ORD_TBL"),
    ]

    iterations = 5000  # Reduced for faster testing

    # Test original
    start_time = time.time()
    for _ in range(iterations):
        for s1, s2 in test_pairs:
            edit_distance_original(s1, s2)
    original_time = time.time() - start_time

    # Test optimized
    start_time = time.time()
    for _ in range(iterations):
        for s1, s2 in test_pairs:
            edit_distance_optimized(s1, s2)
    optimized_time = time.time() - start_time

    print(f"Original algorithm: {original_time:.3f}s for {iterations * len(test_pairs)} calculations")
    print(f"Optimized algorithm: {optimized_time:.3f}s for {iterations * len(test_pairs)} calculations")
    print(f"Improvement: {((original_time - optimized_time) / original_time) * 100:.1f}% faster")
    print(f"Speedup factor: {original_time / optimized_time:.2f}x")

    return original_time, optimized_time


def test_correctness():
    """Verify that both functions produce the same results."""
    test_cases = [
        ("", ""),
        ("", "a"),
        ("a", ""),
        ("a", "a"),
        ("a", "b"),
        ("ab", "a"),
        ("ab", "b"),
        ("hello", "hello"),
        ("hello", "world"),
        ("kitten", "sitting"),
        ("saturday", "sunday"),
        ("USER", "USERS"),
        ("CUSTOMER", "CUSTOMERS"),
        ("ORDERS", "ORDER"),
    ]

    print("Testing correctness...")
    for s1, s2 in test_cases:
        orig_result = edit_distance_original(s1, s2)
        opt_result = edit_distance_optimized(s1, s2)
        if orig_result != opt_result:
            print(f"ERROR: edit_distance('{s1}', '{s2}') differs: orig={orig_result}, opt={opt_result}")
            return False

    print("All correctness tests passed!")
    return True


if __name__ == "__main__":
    correctness_ok = test_correctness()
    if correctness_ok:
        print("Correctness verified. Running performance comparison...\n")
        test_performance_comparison()
    else:
        print("Correctness test failed!")
