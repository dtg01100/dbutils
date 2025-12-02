# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True
# cython: nonecheck=False

"""
Fast native implementations for performance-critical dbutils operations.
"""

from libc.string cimport strlen, strstr, strcasecmp
from cpython.unicode cimport PyUnicode_AsUTF8String


def fast_string_match(str text, str query):
    """Ultra-fast case-insensitive substring matching."""
    cdef bytes text_bytes = text.encode('utf-8').lower()
    cdef bytes query_bytes = query.encode('utf-8').lower()
    return query_bytes in text_bytes


def fast_prefix_match(str text, str prefix):
    """Ultra-fast case-insensitive prefix matching."""
    cdef str text_lower = text.lower()
    cdef str prefix_lower = prefix.lower()
    return text_lower.startswith(prefix_lower)


def fast_word_prefix_match(str text, str query):
    """Check if any word in text starts with query (for underscore-separated names)."""
    cdef list words = text.lower().replace('_', ' ').split()
    cdef str query_lower = query.lower()
    cdef str word
    
    for word in words:
        if word.startswith(query_lower):
            return True
    return False


def fast_search_tables(list tables, str query):
    """Optimized table search with scoring."""
    if not query.strip():
        return [(t, 1.0) for t in tables]
    
    cdef str query_lower = query.lower()
    cdef list results = []
    cdef object table
    cdef double score
    cdef str name_lower, remarks_lower
    
    for table in tables:
        score = 0.0
        name_lower = table.name.lower()
        
        # Exact name match - highest priority
        if query_lower == name_lower:
            score = 2.0
        # Name contains query
        elif query_lower in name_lower:
            score = 1.0
        # Word in name starts with query
        elif fast_word_prefix_match(table.name, query):
            score = 0.6
        # Check remarks if available
        elif table.remarks:
            remarks_lower = table.remarks.lower()
            if query_lower in remarks_lower:
                score = 0.8
        
        if score > 0:
            results.append((table, score))
    
    # Sort by score descending
    results.sort(key=lambda x: x[1], reverse=True)
    return results


def fast_search_columns(list columns, str query):
    """Optimized column search with scoring."""
    if not query.strip():
        return [(c, 1.0) for c in columns]
    
    cdef str query_lower = query.lower()
    cdef list results = []
    cdef object col
    cdef double score
    cdef str name_lower, typename_lower, remarks_lower
    
    for col in columns:
        score = 0.0
        name_lower = col.name.lower()
        typename_lower = col.typename.lower()
        
        # Exact name match
        if query_lower == name_lower:
            score = 2.0
        # Name contains query
        elif query_lower in name_lower:
            score = 1.0
        # Type contains query
        elif query_lower in typename_lower:
            score = 0.7
        # Check remarks if available
        elif col.remarks:
            remarks_lower = col.remarks.lower()
            if query_lower in remarks_lower:
                score = 0.5
        
        if score > 0:
            results.append((col, score))
    
    # Sort by score descending
    results.sort(key=lambda x: x[1], reverse=True)
    return results


cdef class FastTrieNode:
    """Memory-efficient trie node implementation in Cython."""

    cdef public dict children
    cdef public bint is_end_of_word
    cdef public set items

    def __cinit__(self):
        self.children = {}
        self.is_end_of_word = False
        self.items = set()

    cdef inline void insert(self, str word, str item_key):
        """Insert a word into the trie with associated item key."""
        cdef FastTrieNode node = self
        cdef str char

        for char in word.lower():
            if char not in node.children:
                node.children[char] = FastTrieNode()
            node = node.children[char]

        node.is_end_of_word = True
        node.items.add(item_key)

    cdef inline set search_prefix(self, str prefix):
        """Search for all items that start with the given prefix."""
        cdef FastTrieNode node = self
        cdef str char
        cdef set result = set()

        for char in prefix.lower():
            if char not in node.children:
                return result
            node = node.children[char]

        # Collect all items from this node and all descendants
        self._collect_all_items(node, result)
        return result

    cdef inline void _collect_all_items(self, FastTrieNode node, set result):
        """Recursively collect all items from this node and descendants."""
        cdef FastTrieNode child

        if node.is_end_of_word:
            result.update(node.items)

        for child in node.children.values():
            self._collect_all_items(child, result)


cdef class FastSearchIndex:
    """High-performance search index using native trie implementation."""

    cdef public FastTrieNode table_trie
    cdef public FastTrieNode column_trie
    cdef public dict table_keys
    cdef public dict column_keys

    def __cinit__(self):
        self.table_trie = FastTrieNode()
        self.column_trie = FastTrieNode()
        self.table_keys = {}
        self.column_keys = {}

    def build_index(self, tables, columns):
        """Python wrapper for the cdef build_index method."""
        self._build_index(tables, columns)

    def search_tables(self, query):
        """Python wrapper for the cdef search_tables method."""
        return self._search_tables(query)

    def search_columns(self, query):
        """Python wrapper for the cdef search_columns method."""
        return self._search_columns(query)

    cdef inline void _build_index(self, list tables, list columns):
        """Build the search index from tables and columns."""
        cdef object table, col
        cdef str table_key, col_key, search_text

        # Clear existing index
        self.table_trie = FastTrieNode()
        self.column_trie = FastTrieNode()
        self.table_keys.clear()
        self.column_keys.clear()

        # Index tables
        for table in tables:
            table_key = f"{table.schema}.{table.name}"
            self.table_keys[table_key] = table

            # Pre-compute lowercase searchable text for each table
            search_text = f"{table.name} {table.schema} {table.remarks or ''}".lower()
            self._index_text(self.table_trie, search_text, table_key)

        # Index columns
        for col in columns:
            col_key = f"{col.schema}.{col.table}.{col.name}"
            self.column_keys[col_key] = col

            # Pre-compute lowercase searchable text for each column
            search_text = f"{col.name} {col.typename} {col.remarks or ''}".lower()
            self._index_text(self.column_trie, search_text, col_key)

    cdef inline void _index_text(self, FastTrieNode trie, str text, str item_key):
        """Index individual words from text."""
        cdef list words = text.replace('_', ' ').split()
        cdef str word

        for word in words:
            if word.strip():
                trie.insert(word.strip(), item_key)

    cdef inline list _search_tables(self, str query):
        """Fast search for tables matching the query."""
        if not query.strip():
            return list(self.table_keys.values())

        cdef str query_lower = query.lower().strip()
        cdef set matching_keys = set()
        cdef list words = query_lower.split()
        cdef str word

        if len(words) == 1:
            # Single word - use prefix search
            matching_keys = self.table_trie.search_prefix(query_lower)
        else:
            # Multi-word - find tables that match any of the words
            for word in words:
                matching_keys.update(self.table_trie.search_prefix(word))

        return [self.table_keys[key] for key in matching_keys if key in self.table_keys]

    cdef inline list _search_columns(self, str query):
        """Fast search for columns matching the query."""
        if not query.strip():
            return list(self.column_keys.values())

        cdef str query_lower = query.lower().strip()
        cdef set matching_keys = set()
        cdef list words = query_lower.split()
        cdef str word

        if len(words) == 1:
            # Single word - use prefix search
            matching_keys = self.column_trie.search_prefix(query_lower)
        else:
            # Multi-word - find columns that match any of the words
            for word in words:
                matching_keys.update(self.column_trie.search_prefix(word))

        return [self.column_keys[key] for key in matching_keys if key in self.column_keys]
