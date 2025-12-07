#!/usr/bin/env python3
"""Shared utilities for dbutils modules.

- query_runner: Execute SQL using external `query_runner` tool, parse JSON or delimited text
- edit_distance, fuzzy_match: Optimized fuzzy matching helpers inspired by db_browser
"""

from __future__ import annotations

import json
import os
from typing import Dict, List


def query_runner(sql: str) -> List[Dict]:
    """Execute SQL via JDBC and return rows as list[dict].

    This function now uses only JDBC provider via JayDeBeApi.
    Requires DBUTILS_JDBC_PROVIDER environment variable to be set.
    Optionally pass DBUTILS_JDBC_URL_PARAMS (JSON) and DBUTILS_JDBC_USER/PASSWORD.
    """
    # JDBC path only - no fallback to external query runner
    provider_name = os.environ.get("DBUTILS_JDBC_PROVIDER")
    if not provider_name:
        raise RuntimeError("DBUTILS_JDBC_PROVIDER environment variable not set")

    try:
        from dbutils.jdbc_provider import connect as _jdbc_connect

        url_params_raw = os.environ.get("DBUTILS_JDBC_URL_PARAMS", "{}")
        try:
            url_params = json.loads(url_params_raw) if url_params_raw else {}
        except Exception:
            url_params = {}
        user = os.environ.get("DBUTILS_JDBC_USER")
        password = os.environ.get("DBUTILS_JDBC_PASSWORD")
        conn = _jdbc_connect(provider_name, url_params, user=user, password=password)
        try:
            return conn.query(sql)
        finally:
            conn.close()
    except Exception as e:
        raise RuntimeError(f"JDBC query failed: {e}") from e


def edit_distance(s1: str, s2: str) -> int:
    """Compute Levenshtein edit distance between two strings.
    Returns the minimum number of edits needed to transform s1 into s2.
    """
    if len(s1) < len(s2):
        return edit_distance(s2, s1)

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


def edit_distance_fast(s1: str, s2: str, max_dist: int) -> int:
    """Compute Levenshtein edit distance with optimizations for small max_dist.

    This is optimized for cases where we expect small edit distances or
    when max_dist is small, avoiding full matrix computation when possible.
    """
    # If length difference alone exceeds max_dist, return a value that will exceed threshold
    len_diff = abs(len(s1) - len(s2))
    if len_diff > max_dist:
        return max_dist + 1  # Return a value > max_dist

    # Use the standard algorithm but early termination is complex
    # Instead, return the original optimized version
    return edit_distance(s1, s2)


def _has_exact_substring(text_lower: str, query_lower: str) -> bool:
    return query_lower in text_lower


def _word_prefix_or_edit(text_lower: str, query_lower: str) -> bool:
    # Use a more efficient method to split and avoid creating intermediate strings unnecessarily
    # Process text to handle both underscores and spaces as word separators
    text_processed = text_lower.replace("_", " ")
    words = text_processed.split()

    for word in words:
        # Fast prefix check
        if word.startswith(query_lower):
            return True
        # Only compute edit distance for potentially similar words
        # Check length first to avoid expensive edit distance calculation
        if len(query_lower) >= 3 and abs(len(word) - len(query_lower)) <= 2:
            # Calculate max distance once
            max_distance = max(1, len(query_lower) // 3)
            # Use the length check to potentially avoid edit distance calculation
            if abs(len(word) - len(query_lower)) <= max_distance:
                if edit_distance(word, query_lower) <= max_distance:
                    return True
    return False


def _sequential_char_match(text_lower: str, query_lower: str) -> bool:
    if len(query_lower) > len(text_lower):
        return False
    idx = 0
    for ch in query_lower:
        idx = text_lower.find(ch, idx)
        if idx == -1:
            return False
        idx += 1
    return True


def fuzzy_match(text: str, query: str) -> bool:
    """Optimized fuzzy match with early exits.

    1. Exact substring match (fast path)
    2. Word boundary prefix match (e.g., 'cus' matches 'customer_order')
    3. Edit distance threshold for similar-length words
    4. Sequential character match as a last resort
    """
    if not query:
        return True
    if not text:
        return False

    text_lower = text.lower()
    query_lower = query.lower()

    if _has_exact_substring(text_lower, query_lower):
        return True
    if len(query_lower) < 2:
        return False
    if _word_prefix_or_edit(text_lower, query_lower):
        return True
    return _sequential_char_match(text_lower, query_lower)
