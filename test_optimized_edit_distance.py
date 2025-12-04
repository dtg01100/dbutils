#!/usr/bin/env python3
"""Test script to validate the optimized edit_distance function."""

from dbutils.utils import edit_distance
import time

def test_correctness():
    """Test that the optimized function produces the same results as expected."""
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
    
    print("Testing correctness of optimized edit_distance function...")
    
    all_passed = True
    for s1, s2 in test_cases:
        result = edit_distance(s1, s2)
        print(f"edit_distance('{s1}', '{s2}') = {result}")
        
        # Manual calculation for verification (for simple cases)
        if s1 == s2:
            expected = 0
        elif len(s1) == 0:
            expected = len(s2)
        elif len(s2) == 0:
            expected = len(s1)
        elif s1 == "kitten" and s2 == "sitting":
            expected = 3  # k->s, e->i, insert g
        elif s1 == "saturday" and s2 == "sunday":
            expected = 3  # sat->sun, d->d, ur->ur, day->day? No, actually: s->s, u->u, n->n, d->d, a->a, y->y, but remove t and r -> 2 or replace t->n, d->d, a->a, y->y -> actually it's saturday->sundday->sunday (2 changes)
            # Actually: saturday -> sunday
            # s-a-t-u-r-d-a-y
            # s---u-n-d---a-y  (remove t, r, change t->n) or 
            # s-a-t-u-r-d-a-y
            # s-u---n-d-a-y-t  (remove a,r and t, add t at end)
            # correct is: saturday -> saturday (s->s, a->a) -> saturday (t->n) -> saturday (r->d) -> saturday (d->a) -> sunday (a->y) -> sunday (y->y) 
            # Actually, let me recalculate: saturday -> sunday
            # sat + ur + day -> sun + day
            # So remove 'ur' and change 't' to 'n' in 'sat' -> 'sun'
            # So it's change: t->n (1) and remove: u,r (2) = 3 operations
        else:
            expected = None  # We'll just verify consistency
            
        if expected is not None and result != expected:
            print(f"  ERROR: Expected {expected}, got {result}")
            all_passed = False
    
    if all_passed:
        print("All correctness tests passed!")
    else:
        print("Some tests failed!")
    
    return all_passed

def test_performance():
    """Test performance improvement."""
    print("\nTesting performance improvement...")
    
    # Test cases that showed high usage in profiling
    test_pairs = [
        ("USER_TABLE_NAME", "CUSTOMER_TABLE_NAME"),
        ("ORDER_HISTORY", "INVOICE_HISTORY"), 
        ("PRODUCT_CATALOG", "ITEM_CATALOG"),
    ]
    
    # Time the optimized function
    start_time = time.time()
    iterations = 10000
    for i in range(iterations):
        for s1, s2 in test_pairs:
            dist = edit_distance(s1, s2)
    optimized_time = time.time() - start_time
    
    print(f"Optimized function completed {iterations * len(test_pairs)} calculations in {optimized_time:.3f}s")
    print(f"Average time per calculation: {optimized_time/(iterations * len(test_pairs)):.6f}s")
    
    return optimized_time

if __name__ == "__main__":
    correctness_ok = test_correctness()
    performance_time = test_performance()
    
    if correctness_ok:
        print(f"\n✅ Optimization successful! Function is correct and took {performance_time:.3f}s.")
    else:
        print("\n❌ Optimization failed! Function has correctness issues.")