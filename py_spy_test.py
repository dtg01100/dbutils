#!/usr/bin/env python3
"""Long-running script for py-spy profiling."""

import time

from dbutils.utils import edit_distance, fuzzy_match


def long_running_string_operations():
    """Perform string operations for an extended period for py-spy to analyze."""
    print("Starting intensive string operations for py-spy profiling...")

    iteration = 0
    start_time = time.time()

    while time.time() - start_time < 10:  # Run for 10 seconds
        # Perform intensive string operations
        for _ in range(1000):
            edit_distance('USER_TABLE_NAME', 'CUSTOMER_TABLE_NAME')
            edit_distance('ORDER_HISTORY', 'INVOICE_HISTORY')
            edit_distance('PRODUCT_CATALOG', 'ITEM_CATALOG')
            fuzzy_match('CUSTOMER_ORDER_TABLE', 'CUST')
            fuzzy_match('USER_PROFILE_INFO', 'USER')
            fuzzy_match('PRODUCT_DESCRIPTION', 'PROD')

        iteration += 1
        if iteration % 10 == 0:
            elapsed = time.time() - start_time
            print(f"Completed {iteration} iterations in {elapsed:.2f}s")

    print("String operations completed.")

if __name__ == "__main__":
    long_running_string_operations()
