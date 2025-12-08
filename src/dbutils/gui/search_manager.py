#!/usr/bin/env python3
"""
Search Manager Module

Centralized search functionality for the database browser application.
This module consolidates all search-related operations including:
- Streaming search
- Cached search results
- Search result management
- Search state tracking

This addresses the redundant search implementations found throughout the codebase.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple

# Local imports
from dbutils.db_browser import ColumnInfo, TableInfo
from dbutils.gui.qt_app import SearchResult


class SearchMode(Enum):
    """Search modes supported by the application."""

    TABLES = auto()
    COLUMNS = auto()
    ADVANCED = auto()


class SearchState(Enum):
    """Current state of search operations."""

    IDLE = auto()
    ACTIVE = auto()
    COMPLETED = auto()
    CANCELLED = auto()
    ERROR = auto()


@dataclass
class SearchContext:
    """Context for search operations including state and configuration."""

    mode: SearchMode = SearchMode.TABLES
    query: str = ""
    show_non_matching: bool = True
    inline_highlight: bool = True
    streaming_enabled: bool = True
    max_results: int = 1000
    debounce_delay: int = 150  # milliseconds


class SearchManager:
    """Centralized search manager for database browser operations.

    This class consolidates all search functionality that was previously
    scattered across multiple methods in the main Qt application.
    """

    def __init__(self):
        self._search_state = SearchState.IDLE
        self._current_context = SearchContext()
        self._result_cache: Dict[str, Tuple[float, List[SearchResult]]] = {}
        self._cache_ttl = 3600  # 1 hour cache TTL
        self._lock = threading.RLock()
        self._last_search_time = 0.0
        self._search_worker = None
        self._search_thread = None
        self._cancel_requested = False

        # Performance metrics
        self._search_count = 0
        self._cache_hits = 0
        self._cache_misses = 0

    def set_context(self, context: SearchContext):
        """Update the search context with new parameters."""
        with self._lock:
            self._current_context = context

    def get_state(self) -> SearchState:
        """Get current search state."""
        with self._lock:
            return self._search_state

    def set_state(self, state: SearchState):
        """Update search state."""
        with self._lock:
            self._search_state = state

    def cancel_search(self):
        """Cancel any ongoing search operation."""
        with self._lock:
            self._cancel_requested = True
            if self._search_state == SearchState.ACTIVE:
                self.set_state(SearchState.CANCELLED)

            # Cancel worker thread if active
            if self._search_worker:
                try:
                    self._search_worker.cancel_search()
                except Exception:
                    pass

            self._cleanup_worker_resources()

    def _cleanup_worker_resources(self):
        """Clean up search worker resources."""
        if self._search_thread and self._search_thread.is_alive():
            try:
                self._search_thread.join(timeout=0.1)
            except Exception:
                pass

        self._search_worker = None
        self._search_thread = None
        self._cancel_requested = False

    def _generate_cache_key(self, query: str, mode: SearchMode) -> str:
        """Generate a cache key for search results."""
        return f"{mode.name.lower()}:{query.lower().strip()}"

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached results are still valid."""
        if cache_key not in self._result_cache:
            return False

        cached_time, _ = self._result_cache[cache_key]
        return (time.time() - cached_time) < self._cache_ttl

    def _get_cached_results(self, query: str, mode: SearchMode) -> Optional[List[SearchResult]]:
        """Retrieve cached search results if available and valid."""
        cache_key = self._generate_cache_key(query, mode)

        with self._lock:
            if self._is_cache_valid(cache_key):
                self._cache_hits += 1
                _, results = self._result_cache[cache_key]
                return results.copy()
            else:
                self._cache_misses += 1
                return None

    def _cache_results(self, query: str, mode: SearchMode, results: List[SearchResult]):
        """Cache search results for future use."""
        cache_key = self._generate_cache_key(query, mode)

        with self._lock:
            self._result_cache[cache_key] = (time.time(), results.copy())

    def clear_cache(self):
        """Clear all cached search results."""
        with self._lock:
            self._result_cache.clear()
            self._cache_hits = 0
            self._cache_misses = 0

    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache performance statistics."""
        with self._lock:
            return {
                "cache_hits": self._cache_hits,
                "cache_misses": self._cache_misses,
                "cache_size": len(self._result_cache),
                "search_count": self._search_count,
            }

    def perform_search(
        self,
        tables: List[TableInfo],
        columns: List[ColumnInfo],
        query: str,
        mode: SearchMode = SearchMode.TABLES,
        use_cache: bool = True,
    ) -> List[SearchResult]:
        """Perform a search operation with caching and debouncing.

        This consolidates the previously scattered search implementations.
        """
        # Normalize query
        query = query.strip()
        if not query:
            return []

        # Check cache first
        if use_cache:
            cached_results = self._get_cached_results(query, mode)
            if cached_results is not None:
                return cached_results

        # Update search count
        self._search_count += 1

        # Perform the actual search based on mode
        if mode == SearchMode.TABLES:
            results = self._search_tables(tables, query)
        elif mode == SearchMode.COLUMNS:
            results = self._search_columns(columns, query)
        else:
            results = self._search_advanced(tables, columns, query)

        # Cache results if successful
        if results and use_cache:
            self._cache_results(query, mode, results)

        return results

    def _search_tables(self, tables: List[TableInfo], query: str) -> List[SearchResult]:
        """Search tables using optimized algorithm."""
        query_lower = query.lower()
        results = []

        for table in tables:
            if self._cancel_requested:
                break

            # Check for matches in table name, schema, and remarks
            name_match = query_lower in table.name.lower()
            schema_match = query_lower in table.schema.lower()
            remarks_match = table.remarks and query_lower in table.remarks.lower()

            if name_match or schema_match or remarks_match:
                # Calculate relevance score
                score = self._calculate_relevance_score(name_match, schema_match, remarks_match)
                match_type = "exact" if name_match else "fuzzy"

                result = SearchResult(
                    item=table, match_type=match_type, relevance_score=score, table_key=f"{table.schema}.{table.name}"
                )
                results.append(result)

        # Sort by relevance score
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        return results

    def _search_columns(self, columns: List[ColumnInfo], query: str) -> List[SearchResult]:
        """Search columns using optimized algorithm."""
        query_lower = query.lower()
        results = []
        table_aggregates = {}  # For aggregating column matches by table

        for col in columns:
            if self._cancel_requested:
                break

            # Check for matches in column name, type, and remarks
            name_match = query_lower in col.name.lower()
            type_match = query_lower in col.typename.lower()
            remarks_match = col.remarks and query_lower in col.remarks.lower()

            if name_match or type_match or remarks_match:
                # Calculate relevance score
                score = self._calculate_relevance_score(name_match, type_match, remarks_match)
                match_type = "exact" if name_match else "fuzzy"

                result = SearchResult(
                    item=col, match_type=match_type, relevance_score=score, table_key=f"{col.schema}.{col.table}"
                )
                results.append(result)

                # Aggregate by table for "show non-matching" functionality
                table_key = f"{col.schema}.{col.table}"
                if table_key not in table_aggregates:
                    table_aggregates[table_key] = []
                table_aggregates[table_key].append(result)

        # Create table aggregate results for UI display
        aggregate_results = self._create_table_aggregates(table_aggregates, columns)

        # Combine and sort results
        combined = aggregate_results + results
        combined.sort(key=lambda x: x.relevance_score, reverse=True)

        return combined

    def _create_table_aggregates(
        self, table_aggregates: Dict[str, List[SearchResult]], columns: List[ColumnInfo]
    ) -> List[SearchResult]:
        """Create aggregate search results for tables containing matching columns."""
        aggregate_results = []

        for table_key, col_results in table_aggregates.items():
            # Find the table object for this key
            schema, table_name = table_key.split(".", 1)
            table_obj = next((t for t in self._get_all_tables() if t.schema == schema and t.name == table_name), None)

            if table_obj:
                # Count of matching columns as relevance score
                count = len(col_results)
                aggregate_results.append(
                    SearchResult(item=table_obj, match_type="column", relevance_score=float(count), table_key=table_key)
                )

        return aggregate_results

    def _calculate_relevance_score(self, *matches: bool) -> float:
        """Calculate relevance score based on match types."""
        # Exact matches get higher scores
        exact_matches = sum(1.0 for match in matches if match)
        fuzzy_matches = len(matches) - exact_matches

        # Weight exact matches more heavily
        return exact_matches * 1.0 + fuzzy_matches * 0.3

    def _get_all_tables(self) -> List[TableInfo]:
        """Get all tables from the application context."""
        # This would be connected to the main application's data model
        # For now, return empty list as placeholder
        return []

    def _search_advanced(self, tables: List[TableInfo], columns: List[ColumnInfo], query: str) -> List[SearchResult]:
        """Advanced search combining table and column searches."""
        # Combine results from both table and column searches
        table_results = self._search_tables(tables, query)
        column_results = self._search_columns(columns, query)

        # Merge and deduplicate results
        combined = table_results + column_results

        # Remove duplicates by table_key
        seen_keys = set()
        unique_results = []
        for result in combined:
            if result.table_key not in seen_keys:
                seen_keys.add(result.table_key)
                unique_results.append(result)

        return unique_results

    def get_search_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for search operations."""
        return {
            "search_count": self._search_count,
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "cache_efficiency": self._cache_hits / max(1, self._search_count),
            "average_search_time": 0.0,  # Would be tracked in actual implementation
        }

    def __del__(self):
        """Clean up resources when search manager is destroyed."""
        self.cancel_search()
        self.clear_cache()


# Singleton instance for easy access
_search_manager_instance = None


def get_search_manager() -> SearchManager:
    """Get the singleton search manager instance."""
    global _search_manager_instance
    if _search_manager_instance is None:
        _search_manager_instance = SearchManager()
    return _search_manager_instance
