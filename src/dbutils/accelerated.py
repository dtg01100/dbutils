"""Fast operations module with Cython acceleration.

This module provides high-performance implementations of performance-critical
operations using Cython. If the Cython extensions are not available, it falls
back to pure Python implementations.
"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# Global variable to track Cython availability
HAS_CYTHON = False

# Try to import the fast Cython version
try:
    from .fast_ops import (
        FastSearchIndex as _FastSearchIndex,
    )

    HAS_CYTHON = True
    logger.info("Using Cython-accelerated fast operations")

    def fast_intern_string(s: str) -> str:
        """Fast string interning using Cython."""
        return s  # TODO: Implement in Cython

    def fast_string_normalize(text: str) -> str:
        """Fast string normalization using Cython."""
        if not text:
            return ""
        return text.lower().replace("_", " ")

    def fast_split_words(text: str) -> list:
        """Fast word splitting using Cython."""
        return [word.strip() for word in text.split() if word.strip()]

    def create_fast_search_index():
        """Create a Cython-accelerated search index."""
        return _FastSearchIndex()

except ImportError:
    HAS_CYTHON = False
    logger.info("Cython extensions not available, using pure Python fallback")

    # Fallback implementations
    from .db_browser import SearchIndex as _PureSearchIndex

    def fast_intern_string(s: str) -> str:
        """Pure Python string interning fallback."""
        return s

    def fast_string_normalize(text: str) -> str:
        """Pure Python string normalization fallback."""
        if not text:
            return ""
        return text.lower().replace("_", " ")

    def fast_string_normalize(text: str) -> str:
        """Pure Python string normalization fallback."""
        if not text:
            return ""
        return text.lower().replace("_", " ")

    def fast_split_words(text: str) -> list:
        """Pure Python word splitting fallback."""
        return [word.strip() for word in text.split() if word.strip()]

    def create_fast_search_index():
        """Pure Python search index fallback."""
        return _PureSearchIndex()


class AcceleratedSearchIndex:
    """Search index that uses Cython acceleration when available.

    This class provides the same interface as the pure Python SearchIndex
    but uses optimized Cython implementations for better performance.
    """

    def __init__(self):
        if HAS_CYTHON:
            self._index = create_fast_search_index()
        else:
            from .db_browser import SearchIndex

            self._index = SearchIndex()

    def build_index(self, tables: List, columns: List) -> None:
        """Build the search index from tables and columns."""
        self._index.build_index(tables, columns)

    def search_tables(self, query: str) -> List:
        """Search for tables matching the query."""
        return self._index.search_tables(query)

    def search_columns(self, query: str) -> List:
        """Search for columns matching the query."""
        return self._index.search_columns(query)


# Convenience functions
def create_accelerated_search_index():
    """Create an accelerated search index."""
    return AcceleratedSearchIndex()


def get_acceleration_status() -> Dict[str, Any]:
    """Get the status of acceleration features."""
    return {
        "cython_available": HAS_CYTHON,
        "accelerated_search": HAS_CYTHON,
        "accelerated_strings": False,  # Not implemented yet
        "performance_level": "high" if HAS_CYTHON else "standard",
    }


# Export the accelerated versions
SearchIndex = AcceleratedSearchIndex
