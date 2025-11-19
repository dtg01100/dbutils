#!/usr/bin/env python3
"""
Shared utilities for dbutils modules.

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


def query_runner(sql: str) -> List[Dict]:
    """Run an external `query_runner` command and return parsed results.

    Tries JSON first; if not JSON, auto-detects TSV vs CSV by inspecting the header line.
    Normalizes DictReader keys by stripping whitespace.
    """
    # Write SQL to a temp file to support larger queries and parity with other modules
    with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as f:
        f.write(sql)
        temp_file = f.name

    try:
        result = subprocess.run(["query_runner", "-t", "db2", temp_file], capture_output=True, text=True)
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
    finally:
        try:
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


def _has_exact_substring(text_lower: str, query_lower: str) -> bool:
    return query_lower in text_lower


def _word_prefix_or_edit(text_lower: str, query_lower: str) -> bool:
    words = text_lower.replace("_", " ").split()
    for word in words:
        if word.startswith(query_lower):
            return True
        if len(query_lower) >= 3 and abs(len(word) - len(query_lower)) <= 2:
            max_distance = max(1, len(query_lower) // 3)
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
