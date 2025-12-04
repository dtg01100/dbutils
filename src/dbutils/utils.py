#!/usr/bin/env python3
"""Shared utilities for dbutils modules.

- query_runner: Execute SQL using external `query_runner` tool, parse JSON or delimited text
- edit_distance, fuzzy_match: Optimized fuzzy matching helpers inspired by db_browser
"""

from __future__ import annotations

import csv
import io
import json
import os
import subprocess
import tempfile
from typing import Dict, List


def query_runner(sql: str, timeout: int = 30) -> List[Dict]:
    """Run an external `query_runner` command and return parsed results.

    Tries JSON first; if not JSON, auto-detects TSV vs CSV by inspecting the header line.
    Normalizes DictReader keys by stripping whitespace.
    Added timeout parameter to prevent hanging queries.
    """
    # Write SQL to a temp file to support larger queries and parity with other modules
    with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as f:
        f.write(sql)
        temp_file = f.name

    try:
        # Use timeout to prevent hanging queries
        result = subprocess.run(
            ["query_runner", "-t", "db2", temp_file],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout  # Add timeout to prevent blocking
        )
        if result.returncode != 0:
            raise RuntimeError(f"query_runner failed: {result.stderr}")

        stdout = result.stdout or ""
        # Try JSON first
        try:
            parsed = json.loads(stdout)
            # Ensure we always return a list of dicts
            if isinstance(parsed, list):
                return parsed
            if isinstance(parsed, dict):
                return [parsed]
            return []
        except json.JSONDecodeError:
            # Fallback: delimited text with header (TSV or CSV)
            text = stdout.strip()
            if not text:
                return []
            first_line = text.splitlines()[0]
            delimiter = "\t" if "\t" in first_line else ","
            reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
            rows: List[Dict] = []
            for r in reader:
                if r is None:
                    continue
                # Normalize keys (strip whitespace)
                normalized = {(k.strip() if isinstance(k, str) else k): v for k, v in r.items()}
                rows.append(normalized)
            return rows
    except subprocess.TimeoutExpired:
        # Clean up the temp file if timeout occurs
        try:
            os.unlink(temp_file)
        except Exception:
            pass
        raise RuntimeError(f"query_runner timed out after {timeout} seconds")
    finally:
        try:
            # Only try to delete if we haven't already (in timeout case)
            if os.path.exists(temp_file):
                os.unlink(temp_file)
        except Exception:
            pass


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
