# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False

"""
Fast native implementations for performance-critical dbutils operations.
"""

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
