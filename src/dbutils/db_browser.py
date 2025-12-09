#!/usr/bin/env python3
"""dbutils.db_browser - DB2 Schema Browser Backend

Core functionality for searching and browsing DB2 tables and columns.
Provides data structures and methods used by the Qt GUI browser.
"""

import asyncio
import gzip
import json
import logging
import os
import pickle
import time
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
from typing import Set

logger = logging.getLogger(__name__)

# Import rich for TUI
try:
    from rich.console import Console
    from rich.text import Text
    from rich.panel import Panel

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# Textual support removed — keep a single flag for compatibility
TEXTUAL_AVAILABLE = False

# String interning for memory optimization
_string_cache: Dict[str, str] = {}


def intern_string(s: str) -> str:
    """Intern a string to reduce memory usage for repeated strings."""
    if s in _string_cache:
        return _string_cache[s]
    _string_cache[s] = s
    return s


@dataclass
class ColumnInfo:
    """Represents a column in the database."""

    schema: str
    table: str
    name: str
    typename: str
    length: Optional[int]
    scale: Optional[int]
    nulls: str
    remarks: str

    def __post_init__(self):
        """Intern strings to reduce memory usage."""
        self.schema = intern_string(self.schema)
        self.table = intern_string(self.table)
        self.name = intern_string(self.name)
        self.typename = intern_string(self.typename)
        self.nulls = intern_string(self.nulls)
        if self.remarks:
            self.remarks = intern_string(self.remarks)


@dataclass
class TableInfo:
    """Represents a table in the database."""

    schema: str
    name: str
    remarks: str

    def __post_init__(self):
        """Intern strings to reduce memory usage."""
        self.schema = intern_string(self.schema)
        self.name = intern_string(self.name)
        if self.remarks:
            self.remarks = intern_string(self.remarks)


class TrieNode:
    """A memory-optimized node in the trie data structure for fast prefix matching."""

    __slots__ = ("children", "is_end_of_word", "items")

    def __init__(self):
        self.children: Dict[str, TrieNode] = {}
        self.is_end_of_word = False
        self.items: Set[str] = set()  # Store item keys that end at this node

    def insert(self, word: str, item_key: str) -> None:
        """Insert a word into the trie with associated item key."""
        node = self
        for char in word.lower():
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
        node.is_end_of_word = True
        node.items.add(item_key)

    def search_prefix(self, prefix: str) -> Set[str]:
        """Search for all items that start with the given prefix."""
        node = self
        for char in prefix.lower():
            if char not in node.children:
                return set()
            node = node.children[char]

        # Collect all items from this node and all descendants
        result = set()
        self._collect_all_items(node, result)
        return result

    def _collect_all_items(self, node: "TrieNode", result: Set[str]) -> None:
        """Iteratively collect all items from this node and descendants using a stack.

        This prevents potential stack overflow for very deep tries.
        """
        # Use iterative approach with a stack to avoid recursion depth issues
        stack = [node]
        while stack:
            current = stack.pop()
            if current.is_end_of_word:
                result.update(current.items)
            # Add all children to the stack for processing
            stack.extend(current.children.values())


class SearchIndex:
    """Fast search index using trie data structure."""

    def __init__(self):
        self.table_trie = TrieNode()
        self.column_trie = TrieNode()
        self.table_keys: Dict[str, TableInfo] = {}
        self.column_keys: Dict[str, ColumnInfo] = {}

    def build_index(self, tables: List[TableInfo], columns: List[ColumnInfo]) -> None:
        """Build the search index from tables and columns."""
        # Clear existing index
        self.table_trie = TrieNode()
        self.column_trie = TrieNode()
        self.table_keys.clear()
        self.column_keys.clear()

        # Index tables
        for table in tables:
            table_key = f"{table.schema}.{table.name}"
            self.table_keys[table_key] = table

            # Index by name, schema, and remarks
            search_terms = [table.name, table.schema]
            if table.remarks:
                search_terms.append(table.remarks)

            for term in search_terms:
                # Split compound terms and index each word
                words = term.replace("_", " ").split()
                for word in words:
                    if word.strip():
                        self.table_trie.insert(word.strip(), table_key)

        # Index columns
        for col in columns:
            col_key = f"{col.schema}.{col.table}.{col.name}"
            self.column_keys[col_key] = col

            # Index by name, type, and remarks
            search_terms = [col.name, col.typename]
            if col.remarks:
                search_terms.append(col.remarks)

            for term in search_terms:
                # Split compound terms and index each word
                words = term.replace("_", " ").split()
                for word in words:
                    if word.strip():
                        self.column_trie.insert(word.strip(), col_key)

    def search_tables(self, query: str) -> List[TableInfo]:
        """Fast search for tables matching the query."""
        if not query.strip():
            return list(self.table_keys.values())

        query_lower = query.lower().strip()
        matching_keys = set()

        # For multi-word queries, find intersection of all prefix matches
        words = query_lower.split()
        if len(words) == 1:
            # Single word - use prefix search
            matching_keys = self.table_trie.search_prefix(query_lower)
        else:
            # Multi-word - find tables that match any of the words
            for word in words:
                word_matches = self.table_trie.search_prefix(word)
                matching_keys.update(word_matches)

        return [self.table_keys[key] for key in matching_keys if key in self.table_keys]

    def search_columns(self, query: str) -> List[ColumnInfo]:
        """Fast search for columns matching the query."""
        if not query.strip():
            return list(self.column_keys.values())

        query_lower = query.lower().strip()
        matching_keys = set()

        # For multi-word queries, find intersection of all prefix matches
        words = query_lower.split()
        if len(words) == 1:
            # Single word - use prefix search
            matching_keys = self.column_trie.search_prefix(query_lower)
        else:
            # Multi-word - find columns that match any of the words
            for word in words:
                word_matches = self.column_trie.search_prefix(word)
                matching_keys.update(word_matches)

        return [self.column_keys[key] for key in matching_keys if key in self.column_keys]


def query_runner(sql: str, timeout: int = 30) -> List[Dict]:
    """Execute SQL via JDBC and return rows as list[dict].

    This function now uses only JDBC provider via JayDeBeApi.
    Requires DBUTILS_JDBC_PROVIDER environment variable to be set.
    Optionally pass DBUTILS_JDBC_URL_PARAMS (JSON) and DBUTILS_JDBC_USER/PASSWORD.
    Added timeout parameter to prevent hanging queries.
    """
    # JDBC path only - no fallback to external query runner
    provider_name = os.environ.get("DBUTILS_JDBC_PROVIDER")
    if not provider_name:
        raise RuntimeError("DBUTILS_JDBC_PROVIDER environment variable not set")

    try:
        from dbutils.jdbc_provider import connect as _jdbc_connect, MissingJDBCDriverError

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
        # Let MissingJDBCDriverError pass through without wrapping so the Qt app can handle it
        if e.__class__.__name__ == "MissingJDBCDriverError":
            raise
        raise RuntimeError(f"JDBC query failed: {e}") from e


def mock_get_tables() -> List[TableInfo]:
    """Mock data for testing."""
    return [
        TableInfo(schema="TEST", name="USERS", remarks="User information table"),
        TableInfo(schema="TEST", name="ORDERS", remarks="Order records table"),
        TableInfo(schema="TEST", name="PRODUCTS", remarks="Product catalog table"),
        TableInfo(schema="DACDATA", name="CUSTOMERS", remarks="Customer data"),
        TableInfo(schema="DACDATA", name="INVOICES", remarks="Invoice records"),
        TableInfo(schema="DACDATA", name="OHHST", remarks="OH HST master history table"),
    ]


def mock_get_columns() -> List[ColumnInfo]:
    """Mock data for testing."""
    return [
        ColumnInfo(
            schema="TEST",
            table="USERS",
            name="ID",
            typename="INTEGER",
            length=10,
            scale=0,
            nulls="N",
            remarks="User identifier",
        ),
        ColumnInfo(
            schema="TEST",
            table="USERS",
            name="NAME",
            typename="VARCHAR",
            length=100,
            scale=0,
            nulls="N",
            remarks="User name",
        ),
        ColumnInfo(
            schema="TEST",
            table="USERS",
            name="EMAIL",
            typename="VARCHAR",
            length=255,
            scale=0,
            nulls="Y",
            remarks="User email address",
        ),
        ColumnInfo(
            schema="TEST",
            table="ORDERS",
            name="ID",
            typename="INTEGER",
            length=10,
            scale=0,
            nulls="N",
            remarks="Order identifier",
        ),
        ColumnInfo(
            schema="TEST",
            table="ORDERS",
            name="USER_ID",
            typename="INTEGER",
            length=10,
            scale=0,
            nulls="N",
            remarks="Foreign key to USERS",
        ),
        ColumnInfo(
            schema="TEST",
            table="ORDERS",
            name="PRODUCT_ID",
            typename="INTEGER",
            length=10,
            scale=0,
            nulls="N",
            remarks="Foreign key to PRODUCTS",
        ),
        ColumnInfo(
            schema="TEST",
            table="ORDERS",
            name="ORDER_DATE",
            typename="DATE",
            length=10,
            scale=0,
            nulls="N",
            remarks="Date of order",
        ),
        ColumnInfo(
            schema="TEST",
            table="PRODUCTS",
            name="ID",
            typename="INTEGER",
            length=10,
            scale=0,
            nulls="N",
            remarks="Product identifier",
        ),
        ColumnInfo(
            schema="TEST",
            table="PRODUCTS",
            name="NAME",
            typename="VARCHAR",
            length=200,
            scale=0,
            nulls="N",
            remarks="Product name",
        ),
        ColumnInfo(
            schema="TEST",
            table="PRODUCTS",
            name="PRICE",
            typename="DECIMAL",
            length=10,
            scale=2,
            nulls="N",
            remarks="Product price",
        ),
        ColumnInfo(
            schema="DACDATA",
            table="CUSTOMERS",
            name="CUST_ID",
            typename="INTEGER",
            length=10,
            scale=0,
            nulls="N",
            remarks="Customer identifier",
        ),
        ColumnInfo(
            schema="DACDATA",
            table="CUSTOMERS",
            name="CUST_NAME",
            typename="VARCHAR",
            length=150,
            scale=0,
            nulls="N",
            remarks="Customer name",
        ),
        ColumnInfo(
            schema="DACDATA",
            table="INVOICES",
            name="INV_ID",
            typename="INTEGER",
            length=10,
            scale=0,
            nulls="N",
            remarks="Invoice identifier",
        ),
        ColumnInfo(
            schema="DACDATA",
            table="INVOICES",
            name="CUST_ID",
            typename="INTEGER",
            length=10,
            scale=0,
            nulls="N",
            remarks="Foreign key to CUSTOMERS",
        ),
        ColumnInfo(
            schema="DACDATA",
            table="INVOICES",
            name="INV_DATE",
            typename="DATE",
            length=10,
            scale=0,
            nulls="N",
            remarks="Invoice date",
        ),
    ]


def mock_get_tables_heavy(num_schemas: int = 5, tables_per_schema: int = 50) -> List[TableInfo]:
    """Generate heavy mock data for stress testing.
    
    Args:
        num_schemas: Number of schemas to generate (default 5)
        tables_per_schema: Number of tables per schema (default 50)
    
    Returns:
        List of TableInfo objects representing a large dataset.
    """
    tables = []
    schema_names = [f"SCHEMA_{i:03d}" for i in range(num_schemas)]
    table_types = ["USER", "ORDER", "PRODUCT", "INVOICE", "CUSTOMER", "TRANSACTION", 
                   "ACCOUNT", "HISTORY", "LOG", "ARCHIVE"]
    
    for schema_idx, schema in enumerate(schema_names):
        for table_idx in range(tables_per_schema):
            table_type = table_types[table_idx % len(table_types)]
            table_name = f"{table_type}_{table_idx:04d}"
            tables.append(
                TableInfo(
                    schema=schema,
                    name=table_name,
                    remarks=f"Stress test table {table_idx} in {schema} - Type: {table_type}"
                )
            )
    
    return tables


def mock_get_columns_heavy(num_schemas: int = 5, tables_per_schema: int = 50, 
                           columns_per_table: int = 20) -> List[ColumnInfo]:
    """Generate heavy mock data for stress testing.
    
    Args:
        num_schemas: Number of schemas (default 5)
        tables_per_schema: Number of tables per schema (default 50)
        columns_per_table: Number of columns per table (default 20)
    
    Returns:
        List of ColumnInfo objects representing a large dataset.
    """
    columns = []
    schema_names = [f"SCHEMA_{i:03d}" for i in range(num_schemas)]
    table_types = ["USER", "ORDER", "PRODUCT", "INVOICE", "CUSTOMER", "TRANSACTION",
                   "ACCOUNT", "HISTORY", "LOG", "ARCHIVE"]
    column_types = ["INTEGER", "VARCHAR", "DATE", "TIMESTAMP", "DECIMAL", "BOOLEAN",
                    "BIGINT", "SMALLINT", "REAL", "DOUBLE", "CHAR", "TEXT", "CLOB",
                    "BLOB", "JSON", "UUID", "TIME", "INTERVAL"]
    
    for schema_idx, schema in enumerate(schema_names):
        for table_idx in range(tables_per_schema):
            table_type = table_types[table_idx % len(table_types)]
            table_name = f"{table_type}_{table_idx:04d}"
            
            for col_idx in range(columns_per_table):
                col_type = column_types[col_idx % len(column_types)]
                is_nullable = col_idx > 0  # First column is non-nullable (usually PK)
                
                # Realistic column sizing based on type
                length = 10
                scale = 0
                if col_type == "VARCHAR":
                    length = 100 + (col_idx * 5)
                elif col_type == "DECIMAL":
                    length = 15
                    scale = 2
                elif col_type in ["DATE", "TIME"]:
                    length = 10
                elif col_type == "TIMESTAMP":
                    length = 26
                
                columns.append(
                    ColumnInfo(
                        schema=schema,
                        table=table_name,
                        name=f"COL_{col_idx:03d}",
                        typename=col_type,
                        length=length,
                        scale=scale,
                        nulls="Y" if is_nullable else "N",
                        remarks=f"Column {col_idx} ({col_type}) in {table_name}"
                    )
                )
    
    return columns


# Cache configuration
CACHE_DIR = Path.home() / ".cache" / "dbutils"
CACHE_FILE = CACHE_DIR / "schema_cache.pkl.gz"


def get_cache_key(schema_filter: Optional[str], limit: Optional[int] = None, offset: Optional[int] = None) -> str:
    """Generate a cache key based on schema filter and pagination."""
    base_key = schema_filter.upper() if schema_filter else "ALL_SCHEMAS"
    if limit is not None or offset is not None:
        pagination = f"_LIMIT{limit or 0}_OFFSET{offset or 0}"
        return f"{base_key}{pagination}"
    return base_key


def load_from_cache(
    schema_filter: Optional[str],
    limit: Optional[int] = None,
    offset: Optional[int] = None,
) -> Optional[tuple[List[TableInfo], List[ColumnInfo]]]:
    """Load tables and columns from cache if available and recent."""
    if not CACHE_FILE.exists():
        # Backward compatibility: try old uncompressed cache
        legacy = CACHE_DIR / "schema_cache.pkl"
        if not legacy.exists():
            return None
        cache_path = legacy
        is_gzip = False
    else:
        cache_path = CACHE_FILE
        is_gzip = True

    try:
        if is_gzip:
            with gzip.open(cache_path, "rb") as f:
                cache_data = pickle.load(f)
        else:
            with open(cache_path, "rb") as f:
                cache_data = pickle.load(f)

        cache_key = get_cache_key(schema_filter, limit, offset)
        if cache_key not in cache_data:
            return None

        cached_item = cache_data[cache_key]
        # Check if cache is less than 1 hour old
        if time.time() - cached_item["timestamp"] > 3600:
            return None

        return cached_item["tables"], cached_item["columns"]
    except Exception:
        return None


def save_to_cache(
    schema_filter: Optional[str],
    tables: List[TableInfo],
    columns: List[ColumnInfo],
    limit: Optional[int] = None,
    offset: Optional[int] = None,
) -> None:
    """Save tables and columns to cache (compressed)."""
    try:
        # Create cache directory if it doesn't exist
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

        # Load existing cache or create new
        cache_data = {}
        if CACHE_FILE.exists():
            try:
                with gzip.open(CACHE_FILE, "rb") as f:
                    cache_data = pickle.load(f)
            except Exception:
                cache_data = {}

        # Update cache
        cache_key = get_cache_key(schema_filter, limit, offset)
        cache_data[cache_key] = {"timestamp": time.time(), "tables": tables, "columns": columns}

        # Save cache compressed
        with gzip.open(CACHE_FILE, "wb", compresslevel=5) as f:
            pickle.dump(cache_data, f)
    except Exception:
        # Silently fail - caching is optional
        pass


@dataclass
class SchemaInfo:
    """Represents a schema with table count."""

    name: str
    table_count: int


def get_available_schemas(use_mock: bool = False) -> List[SchemaInfo]:
    """Fetch list of available schemas with table counts."""
    if use_mock:
        return [
            SchemaInfo(name="DACDATA", table_count=15),
            SchemaInfo(name="TEST", table_count=8),
            SchemaInfo(name="QGPL", table_count=23),
            SchemaInfo(name="PRODUCTION", table_count=42),
        ]

    # Query for schemas with table counts
    schemas_sql = """
        SELECT
            TABLE_SCHEMA,
            COUNT(*) AS TABLE_COUNT
        FROM QSYS2.SYSTABLES
        WHERE TABLE_TYPE IN ('T', 'P')
        AND SYSTEM_TABLE = 'N'
        GROUP BY TABLE_SCHEMA
        ORDER BY TABLE_COUNT DESC, TABLE_SCHEMA
    """

    schemas = []
    try:
        schema_data = query_runner(schemas_sql)
        for row in schema_data:
            schemas.append(SchemaInfo(name=row.get("TABLE_SCHEMA", ""), table_count=int(row.get("TABLE_COUNT", 0))))
    except Exception as exc:
        # If query fails, return empty list
        logger.warning(f"Could not fetch schemas: {exc}")

    return schemas


def humanize_schema_name(raw: str) -> str:
    """Return a human-friendly schema label for use in UI displays.

    This is purely cosmetic and must not change the underlying schema
    identifier used for filtering/selection.
    """
    if not raw:
        return ""
    # Replace multiple underscores with a single space and split/join to remove empties
    return " ".join(part for part in raw.replace("__", "_").split("_") if part)


async def get_available_schemas_async(use_mock: bool = False) -> List[SchemaInfo]:
    """Async version of get_available_schemas that doesn't block the UI."""
    if use_mock:
        return [
            SchemaInfo(name="DACDATA", table_count=15),
            SchemaInfo(name="TEST", table_count=8),
            SchemaInfo(name="QGPL", table_count=23),
            SchemaInfo(name="PRODUCTION", table_count=42),
        ]

    # Query for schemas with table counts
    schemas_sql = """
        SELECT
            TABLE_SCHEMA,
            COUNT(*) AS TABLE_COUNT
        FROM QSYS2.SYSTABLES
        WHERE TABLE_TYPE IN ('T', 'P')
        AND SYSTEM_TABLE = 'N'
        GROUP BY TABLE_SCHEMA
        ORDER BY TABLE_COUNT DESC, TABLE_SCHEMA
    """

    schemas = []
    try:
        loop = asyncio.get_event_loop()
        schema_data = await loop.run_in_executor(None, query_runner, schemas_sql)
        for row in schema_data:
            schemas.append(SchemaInfo(name=row.get("TABLE_SCHEMA", ""), table_count=int(row.get("TABLE_COUNT", 0))))
    except Exception as exc:
        # If query fails, return empty list
        logger.warning(f"Could not fetch schemas: {exc}")

    return schemas


def schema_exists(schema: str, use_mock: bool = False) -> bool:
    """Check whether a schema (library) exists by detecting at least one table in it.

    Returns True if QSYS2.SYSTABLES reports at least one table for this schema.
    When use_mock=True, returns True only for known mock schemas (DACDATA).
    """
    if use_mock:
        # Mock datasets include DACDATA
        return schema.upper() == "DACDATA"

    sql = f"SELECT 1 FROM QSYS2.SYSTABLES WHERE TABLE_SCHEMA = '{schema.upper()}' AND TABLE_TYPE IN ('T','P') AND SYSTEM_TABLE='N' FETCH FIRST 1 ROWS ONLY"
    try:
        data = query_runner(sql)
        if not data:
            return False
        # If multiple formats, check for truthy results
        return len(data) > 0
    except Exception:
        return False


async def schema_exists_async(schema: str, use_mock: bool = False) -> bool:
    """Async version of schema_exists that doesn't block the UI."""
    if use_mock:
        # Mock datasets include DACDATA
        return schema.upper() == "DACDATA"

    sql = f"SELECT 1 FROM QSYS2.SYSTABLES WHERE TABLE_SCHEMA = '{schema.upper()}' AND TABLE_TYPE IN ('T','P') AND SYSTEM_TABLE='N' FETCH FIRST 1 ROWS ONLY"
    try:
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, query_runner, sql)
        if not data:
            return False
        # If multiple formats, check for truthy results
        return len(data) > 0
    except Exception:
        return False


async def get_all_tables_and_columns_async(
    schema_filter: Optional[str] = None,
    use_mock: bool = False,
    use_cache: bool = True,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    use_heavy_mock: bool = False,
    db_file: Optional[str] = None,
) -> tuple[List[TableInfo], List[ColumnInfo]]:
    """Async version that can run queries in parallel."""
    # For SQLite, use sync implementation (SQLite doesn't benefit from async here)
    if db_file:
        return _get_all_tables_and_columns_sync(schema_filter, use_mock, use_cache, limit, offset, use_heavy_mock, db_file)
    
    if use_mock:
        if use_heavy_mock:
            # Heavy mock for stress testing: 5 schemas, 50 tables each, 20 columns each
            tables = mock_get_tables_heavy(num_schemas=5, tables_per_schema=50)
            columns = mock_get_columns_heavy(num_schemas=5, tables_per_schema=50, columns_per_table=20)
        else:
            # Regular mock data
            tables = mock_get_tables()
            columns = mock_get_columns()

        # Apply schema filter to mock data if needed
        if schema_filter:
            tables = [t for t in tables if t.schema.upper() == schema_filter.upper()]
            columns = [c for c in columns if c.schema.upper() == schema_filter.upper()]

        # Apply pagination to mock data
        if limit is not None:
            tables = tables[offset or 0 : offset or 0 + limit]
            # For columns, only include those for the paginated tables
            table_keys = {(t.schema, t.name) for t in tables}
            columns = [c for c in columns if (c.schema, c.table) in table_keys]

        return tables, columns

    # Try to load from cache first
    if use_cache:
        cached_data = load_from_cache(schema_filter, limit, offset)
        if cached_data:
            return cached_data

    # Build schema filter clause
    schema_clause = ""
    if schema_filter:
        schema_clause = f"AND TABLE_SCHEMA = '{schema_filter.upper()}'"

    # Build pagination clause (DB2 for i syntax)
    pagination_clause = ""
    if limit is not None:
        if offset is not None and offset > 0:
            # DB2 for i requires OFFSET before FETCH
            pagination_clause = f"OFFSET {offset} ROWS FETCH FIRST {limit} ROWS ONLY"
        else:
            pagination_clause = f"FETCH FIRST {limit} ROWS ONLY"

    # Query for tables (DB2 for i uses QSYS2.SYSTABLES instead of SYSCAT.TABLES)
    tables_sql = f"""
        SELECT
            TABLE_SCHEMA,
            TABLE_NAME,
            TABLE_TEXT
        FROM QSYS2.SYSTABLES
        WHERE TABLE_TYPE IN ('T', 'P')
        AND SYSTEM_TABLE = 'N'
        {schema_clause}
        ORDER BY TABLE_SCHEMA, TABLE_NAME
        {pagination_clause}
    """

    # Run both queries in parallel
    import asyncio

    async def run_query_async(sql: str) -> List[Dict]:
        """Run a query asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, query_runner, sql)

    try:
        # Start both queries concurrently
        tables_task = run_query_async(tables_sql)
        tables_data = await tables_task

        tables = []
        for row in tables_data:
            tables.append(
                TableInfo(
                    schema=row.get("TABLE_SCHEMA", ""),
                    name=row.get("TABLE_NAME", ""),
                    remarks=row.get("TABLE_TEXT", ""),
                ),
            )

        # Query for columns based on loaded tables
        if tables:
            # Build IN clause for the specific tables we loaded
            table_conditions = []
            for table in tables:
                table_conditions.append(f"(c.TABLE_SCHEMA = '{table.schema}' AND c.TABLE_NAME = '{table.name}')")
            tables_in_clause = " OR ".join(table_conditions)

            columns_sql = f"""
                SELECT
                    c.TABLE_SCHEMA,
                    c.TABLE_NAME,
                    c.COLUMN_NAME,
                    c.DATA_TYPE,
                    c.LENGTH,
                    c.NUMERIC_SCALE,
                    c.IS_NULLABLE,
                    c.COLUMN_TEXT
                FROM QSYS2.SYSCOLUMNS c
                WHERE ({tables_in_clause})
                ORDER BY c.TABLE_SCHEMA, c.TABLE_NAME, c.ORDINAL_POSITION
            """
        else:
            # Fallback if no tables loaded - use JOIN instead of subquery for better performance
            columns_sql = f"""
                SELECT
                    c.TABLE_SCHEMA,
                    c.TABLE_NAME,
                    c.COLUMN_NAME,
                    c.DATA_TYPE,
                    c.LENGTH,
                    c.NUMERIC_SCALE,
                    c.IS_NULLABLE,
                    c.COLUMN_TEXT
                FROM QSYS2.SYSCOLUMNS c
                INNER JOIN QSYS2.SYSTABLES t ON
                    c.TABLE_SCHEMA = t.TABLE_SCHEMA AND
                    c.TABLE_NAME = t.TABLE_NAME
                WHERE t.TABLE_TYPE IN ('T', 'P')
                    AND t.SYSTEM_TABLE = 'N' {schema_clause}
                ORDER BY c.TABLE_SCHEMA, c.TABLE_NAME, c.ORDINAL_POSITION
            """

        columns_task = run_query_async(columns_sql)
        columns_data = await columns_task

        columns = []
        for row in columns_data:
            # Handle numeric fields that might be strings
            length = row.get("LENGTH")
            scale = row.get("NUMERIC_SCALE")

            # Convert to int if they're strings
            if isinstance(length, str):
                length = int(length) if length and length.isdigit() else None
            if isinstance(scale, str):
                scale = int(scale) if scale and scale.isdigit() else None

            # Map IS_NULLABLE to Y/N format
            nulls = "Y" if row.get("IS_NULLABLE") == "Y" else "N"

            columns.append(
                ColumnInfo(
                    schema=row.get("TABLE_SCHEMA", ""),
                    table=row.get("TABLE_NAME", ""),
                    name=row.get("COLUMN_NAME", ""),
                    typename=row.get("DATA_TYPE", ""),
                    length=length,
                    scale=scale,
                    nulls=nulls,
                    remarks=row.get("COLUMN_TEXT", ""),
                ),
            )

    except Exception as e:
        # If query fails, return empty list (graceful degradation)
        logger.warning(f"Could not fetch tables/columns: {e}")
        tables, columns = [], []

    # Save to cache if we got data
    if use_cache and (tables or columns):
        save_to_cache(schema_filter, tables, columns, limit, offset)

    return tables, columns


def get_all_tables_and_columns(
    schema_filter: Optional[str] = None,
    use_mock: bool = False,
    use_cache: bool = True,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    use_heavy_mock: bool = False,
    db_file: Optional[str] = None,
) -> tuple[List[TableInfo], List[ColumnInfo]]:
    """Synchronous wrapper for get_all_tables_and_columns_async."""
    import asyncio

    try:
        # Check if there's already a running event loop
        asyncio.get_running_loop()
        # If we're in an async context, fall back to sync implementation
        return _get_all_tables_and_columns_sync(schema_filter, use_mock, use_cache, limit, offset, use_heavy_mock, db_file)
    except RuntimeError:
        # No running loop, we can create one
        pass

    # Create new event loop (preferred way in Python 3.10+)
    return asyncio.run(get_all_tables_and_columns_async(schema_filter, use_mock, use_cache, limit, offset, use_heavy_mock, db_file))


def _get_all_tables_and_columns_sync(
    schema_filter: Optional[str] = None,
    use_mock: bool = False,
    use_cache: bool = True,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    use_heavy_mock: bool = False,
    db_file: Optional[str] = None,
) -> tuple[List[TableInfo], List[ColumnInfo]]:
    """Synchronous fallback implementation with query optimizations."""
    # Handle SQLite database file if provided
    if db_file:
        import sqlite3
        
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # Get list of tables
        cursor.execute("""
            SELECT name, type 
            FROM sqlite_master 
            WHERE type IN ('table', 'view')
            AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """)
        
        tables = []
        columns = []
        
        for row in cursor.fetchall():
            table_name = row[0]
            table_type = row[1]
            
            # Create TableInfo (SQLite doesn't have schemas, use 'main')
            table_info = TableInfo(
                schema='main',
                name=table_name,
                remarks=f"SQLite {table_type}"
            )
            tables.append(table_info)
            
            # Get columns for this table
            cursor.execute(f"PRAGMA table_info({table_name})")
            col_rows = cursor.fetchall()
            
            for col_row in col_rows:
                col_info = ColumnInfo(
                    schema='main',
                    table=table_name,
                    name=col_row[1],  # name
                    typename=col_row[2],  # type
                    length=None,
                    scale=None,
                    nulls='Y' if col_row[3] == 0 else 'N',  # notnull
                    remarks=f"{'PRIMARY KEY' if col_row[5] else ''}"  # pk
                )
                columns.append(col_info)
        
        conn.close()
        
        # Apply pagination if requested
        if limit is not None:
            start = offset or 0
            tables = tables[start:start + limit]
            # Filter columns to only include those for paginated tables
            table_names = {t.name for t in tables}
            columns = [c for c in columns if c.table in table_names]
        
        return tables, columns
    
    if use_mock:
        if use_heavy_mock:
            # Heavy mock for stress testing: 5 schemas, 50 tables each, 20 columns each
            tables = mock_get_tables_heavy(num_schemas=5, tables_per_schema=50)
            columns = mock_get_columns_heavy(num_schemas=5, tables_per_schema=50, columns_per_table=20)
        else:
            # Regular mock data
            tables = mock_get_tables()
            columns = mock_get_columns()

        # Apply schema filter to mock data if needed
        if schema_filter:
            tables = [t for t in tables if t.schema.upper() == schema_filter.upper()]
            columns = [c for c in columns if c.schema.upper() == schema_filter.upper()]

        # Apply pagination to mock data
        if limit is not None:
            tables = tables[offset or 0 : offset or 0 + limit]
            # For columns, only include those for the paginated tables
            table_keys = {(t.schema, t.name) for t in tables}
            columns = [c for c in columns if (c.schema, c.table) in table_keys]

        return tables, columns

    # Try to load from cache first
    if use_cache:
        cached_data = load_from_cache(schema_filter, limit, offset)
        if cached_data:
            return cached_data

    # Build schema filter clause
    schema_clause = ""
    if schema_filter:
        schema_clause = f"AND TABLE_SCHEMA = '{schema_filter.upper()}'"

    # Build pagination clause (DB2 for i syntax)
    pagination_clause = ""
    if limit is not None:
        if offset is not None and offset > 0:
            # DB2 for i requires OFFSET before FETCH
            pagination_clause = f"OFFSET {offset} ROWS FETCH FIRST {limit} ROWS ONLY"
        else:
            pagination_clause = f"FETCH FIRST {limit} ROWS ONLY"

    # Query for tables (DB2 for i uses QSYS2.SYSTABLES instead of SYSCAT.TABLES)
    tables_sql = f"""
        SELECT
            TABLE_SCHEMA,
            TABLE_NAME,
            TABLE_TEXT
        FROM QSYS2.SYSTABLES
        WHERE TABLE_TYPE IN ('T', 'P')
        AND SYSTEM_TABLE = 'N'
        {schema_clause}
        ORDER BY TABLE_SCHEMA, TABLE_NAME
        {pagination_clause}
    """

    try:
        tables_data = query_runner(tables_sql)
        tables = []
        for row in tables_data:
            tables.append(
                TableInfo(
                    schema=row.get("TABLE_SCHEMA", ""),
                    name=row.get("TABLE_NAME", ""),
                    remarks=row.get("TABLE_TEXT", ""),
                ),
            )

        # Query for columns based on loaded tables
        if tables:
            # Build IN clause for the specific tables we loaded
            table_conditions = []
            for table in tables:
                table_conditions.append(f"(c.TABLE_SCHEMA = '{table.schema}' AND c.TABLE_NAME = '{table.name}')")
            tables_in_clause = " OR ".join(table_conditions)

            columns_sql = f"""
                SELECT
                    c.TABLE_SCHEMA,
                    c.TABLE_NAME,
                    c.COLUMN_NAME,
                    c.DATA_TYPE,
                    c.LENGTH,
                    c.NUMERIC_SCALE,
                    c.IS_NULLABLE,
                    c.COLUMN_TEXT
                FROM QSYS2.SYSCOLUMNS c
                WHERE ({tables_in_clause})
                ORDER BY c.TABLE_SCHEMA, c.TABLE_NAME, c.ORDINAL_POSITION
            """
        else:
            # Fallback if no tables loaded - use JOIN instead of subquery for better performance
            columns_sql = f"""
                SELECT
                    c.TABLE_SCHEMA,
                    c.TABLE_NAME,
                    c.COLUMN_NAME,
                    c.DATA_TYPE,
                    c.LENGTH,
                    c.NUMERIC_SCALE,
                    c.IS_NULLABLE,
                    c.COLUMN_TEXT
                FROM QSYS2.SYSCOLUMNS c
                INNER JOIN QSYS2.SYSTABLES t ON
                    c.TABLE_SCHEMA = t.TABLE_SCHEMA AND
                    c.TABLE_NAME = t.TABLE_NAME
                WHERE t.TABLE_TYPE IN ('T', 'P')
                    AND t.SYSTEM_TABLE = 'N' {schema_clause}
                ORDER BY c.TABLE_SCHEMA, c.TABLE_NAME, c.ORDINAL_POSITION
            """

        columns_data = query_runner(columns_sql)
        columns = []
        for row in columns_data:
            # Handle numeric fields that might be strings
            length = row.get("LENGTH")
            scale = row.get("NUMERIC_SCALE")

            # Convert to int if they're strings
            if isinstance(length, str):
                length = int(length) if length and length.isdigit() else None
            if isinstance(scale, str):
                scale = int(scale) if scale and scale.isdigit() else None

            # Map IS_NULLABLE to Y/N format
            nulls = "Y" if row.get("IS_NULLABLE") == "Y" else "N"

            columns.append(
                ColumnInfo(
                    schema=row.get("TABLE_SCHEMA", ""),
                    table=row.get("TABLE_NAME", ""),
                    name=row.get("COLUMN_NAME", ""),
                    typename=row.get("DATA_TYPE", ""),
                    length=length,
                    scale=scale,
                    nulls=nulls,
                    remarks=row.get("COLUMN_TEXT", ""),
                ),
            )
    except Exception as e:
        # If query fails, return empty list (graceful degradation)
        logger.warning(f"Could not fetch tables/columns: {e}")
        tables, columns = [], []

    # Save to cache if we got data
    if use_cache and (tables or columns):
        save_to_cache(schema_filter, tables, columns, limit, offset)

    return tables, columns
    """Fetch all tables and columns from the database."""
    if use_mock:
        tables = mock_get_tables()
        columns = mock_get_columns()

        # Apply schema filter to mock data if needed
        if schema_filter:
            tables = [t for t in tables if t.schema.upper() == schema_filter.upper()]
            columns = [c for c in columns if c.schema.upper() == schema_filter.upper()]

        return tables, columns

    # Try to load from cache first
    if use_cache:
        cached_data = load_from_cache(schema_filter, limit, offset)
        if cached_data:
            return cached_data

    # Real database implementation
    tables = []
    columns = []

    # Build schema filter clause
    schema_clause = ""
    if schema_filter:
        schema_clause = f"AND TABLE_SCHEMA = '{schema_filter.upper()}'"

    # Build pagination clause (DB2 for i syntax)
    pagination_clause = ""
    if limit is not None:
        if offset is not None and offset > 0:
            # DB2 for i requires OFFSET before FETCH
            pagination_clause = f"OFFSET {offset} ROWS FETCH FIRST {limit} ROWS ONLY"
        else:
            pagination_clause = f"FETCH FIRST {limit} ROWS ONLY"

    # Query for tables (DB2 for i uses QSYS2.SYSTABLES instead of SYSCAT.TABLES)
    tables_sql = f"""
        SELECT
            TABLE_SCHEMA,
            TABLE_NAME,
            TABLE_TEXT
        FROM QSYS2.SYSTABLES
        WHERE TABLE_TYPE IN ('T', 'P')
        AND SYSTEM_TABLE = 'N'
        {schema_clause}
        ORDER BY TABLE_SCHEMA, TABLE_NAME
        {pagination_clause}
    """

    try:
        tables_data = query_runner(tables_sql)
        for row in tables_data:
            tables.append(
                TableInfo(
                    schema=row.get("TABLE_SCHEMA", ""),
                    name=row.get("TABLE_NAME", ""),
                    remarks=row.get("TABLE_TEXT", ""),
                ),
            )
    except Exception as e:
        # If query fails, return empty list (graceful degradation)
        logger.warning(f"Could not fetch tables: {e}")

    # Query for columns (DB2 for i uses QSYS2.SYSCOLUMNS instead of SYSCAT.COLUMNS)
    # Only load columns for tables that were actually loaded (important for pagination)
    if tables:
        # Build IN clause for the specific tables we loaded
        table_conditions = []
        for table in tables:
            table_conditions.append(f"(c.TABLE_SCHEMA = '{table.schema}' AND c.TABLE_NAME = '{table.name}')")
        tables_in_clause = " OR ".join(table_conditions)

        columns_sql = f"""
            SELECT
                c.TABLE_SCHEMA,
                c.TABLE_NAME,
                c.COLUMN_NAME,
                c.DATA_TYPE,
                c.LENGTH,
                c.NUMERIC_SCALE,
                c.IS_NULLABLE,
                c.COLUMN_TEXT
            FROM QSYS2.SYSCOLUMNS c
            WHERE ({tables_in_clause})
            ORDER BY c.TABLE_SCHEMA, c.TABLE_NAME, c.ORDINAL_POSITION
        """
    else:
        # Fallback if no tables loaded - use JOIN instead of subquery for better performance
        columns_sql = f"""
            SELECT
                c.TABLE_SCHEMA,
                c.TABLE_NAME,
                c.COLUMN_NAME,
                c.DATA_TYPE,
                c.LENGTH,
                c.NUMERIC_SCALE,
                c.IS_NULLABLE,
                c.COLUMN_TEXT
            FROM QSYS2.SYSCOLUMNS c
            INNER JOIN QSYS2.SYSTABLES t ON
                c.TABLE_SCHEMA = t.TABLE_SCHEMA AND
                c.TABLE_NAME = t.TABLE_NAME
            WHERE t.TABLE_TYPE IN ('T', 'P')
                AND t.SYSTEM_TABLE = 'N' {schema_clause}
            ORDER BY c.TABLE_SCHEMA, c.TABLE_NAME, c.ORDINAL_POSITION
        """

    try:
        columns_data = query_runner(columns_sql)
        for row in columns_data:
            # Handle numeric fields that might be strings
            length = row.get("LENGTH")
            scale = row.get("NUMERIC_SCALE")

            # Convert to int if they're strings
            if isinstance(length, str):
                length = int(length) if length and length.isdigit() else None
            if isinstance(scale, str):
                scale = int(scale) if scale and scale.isdigit() else None

            # Map IS_NULLABLE to Y/N format
            nulls = "Y" if row.get("IS_NULLABLE") == "Y" else "N"

            columns.append(
                ColumnInfo(
                    schema=row.get("TABLE_SCHEMA", ""),
                    table=row.get("TABLE_NAME", ""),
                    name=row.get("COLUMN_NAME", ""),
                    typename=row.get("DATA_TYPE", ""),
                    length=length,
                    scale=scale,
                    nulls=nulls,
                    remarks=row.get("COLUMN_TEXT", ""),
                ),
            )
    except Exception as e:
        # If query fails, return what we have so far
        logger.warning(f"Could not fetch columns: {e}")

    # Save to cache if we got data
    if use_cache and (tables or columns):
        save_to_cache(schema_filter, tables, columns, limit, offset)

    return tables, columns


class DBBrowserTUI:
    """TUI for browsing DB2 schemas with search functionality."""

    def __init__(self, schema_filter: Optional[str] = None, use_mock: bool = False, initial_load_limit: int = 100):
        self.console = Console() if RICH_AVAILABLE else None
        self.schema_filter = schema_filter
        self.use_mock = use_mock
        self.initial_load_limit = initial_load_limit

        # Lazy loading state
        self.all_tables_loaded = False
        self.current_offset = 0
        self.total_tables_estimate = None

        # Show loading message
        if self.console:
            if use_mock:
                self.console.print("[dim]Loading mock data...[/dim]")
            else:
                self.console.print("[dim]Loading database schema... This may take a moment.[/dim]")

        # Load initial batch of data
        self._load_initial_data()

        # Initialize state
        self.search_query = ""
        self.selected_table = None
        self.selected_column_name: Optional[str] = None
        self.filtered_tables = self.tables
        self.filtered_columns = []

    def _load_initial_data(self):
        """Load the initial batch of tables and their columns."""
        try:
            self.tables, self.columns = get_all_tables_and_columns(
                self.schema_filter,
                self.use_mock,
                limit=self.initial_load_limit,
                offset=0,
            )
            if self.console:
                self.console.print(f"[green]✓ Loaded {len(self.tables)} tables and {len(self.columns)} columns[/green]")

            # Check if we got fewer results than requested (indicates all data loaded)
            if len(self.tables) < self.initial_load_limit:
                self.all_tables_loaded = True
            else:
                # Estimate total tables (rough approximation)
                self._estimate_total_tables()

        except Exception as e:
            if self.console:
                self.console.print(f"[red]Error loading database schema: {e}[/red]")
            self.tables, self.columns = [], []
            self.all_tables_loaded = True

        # Precompute table columns mapping for performance
        self.table_columns = {}
        for col in self.columns:
            if col.schema and col.table:  # Ensure not None
                table_key = f"{col.schema}.{col.table}"
                if table_key not in self.table_columns:
                    self.table_columns[table_key] = []
                self.table_columns[table_key].append(col)

    def _estimate_total_tables(self):
        """Estimate total number of tables for progress indication."""
        if self.use_mock:
            self.total_tables_estimate = len(self.tables)  # Mock data is complete
            return

        try:
            # Quick count query to estimate total
            count_sql = f"""
                SELECT COUNT(*) as TOTAL_COUNT
                FROM QSYS2.SYSTABLES
                WHERE TABLE_TYPE IN ('T', 'P')
                AND SYSTEM_TABLE = 'N'
                {"AND TABLE_SCHEMA = '" + self.schema_filter.upper() + "'" if self.schema_filter else ""}
            """
            count_result = query_runner(count_sql)
            if count_result and count_result[0].get("TOTAL_COUNT"):
                self.total_tables_estimate = int(count_result[0]["TOTAL_COUNT"])
        except Exception:
            # If count fails, use a rough estimate
            self.total_tables_estimate = len(self.tables) * 2

    def load_more_tables(self, additional_limit: int = 100) -> bool:
        """Load additional tables and their columns. Returns True if more data was loaded."""
        if self.all_tables_loaded:
            return False

        try:
            new_offset = self.current_offset + len(self.tables)
            new_tables, new_columns = get_all_tables_and_columns(
                self.schema_filter,
                self.use_mock,
                limit=additional_limit,
                offset=new_offset,
            )

            if not new_tables:
                self.all_tables_loaded = True
                return False

            # Add new tables and columns
            self.tables.extend(new_tables)
            self.columns.extend(new_columns)

            # Update table columns mapping for new data
            for col in new_columns:
                if col.schema and col.table:
                    table_key = f"{col.schema}.{col.table}"
                    if table_key not in self.table_columns:
                        self.table_columns[table_key] = []
                    self.table_columns[table_key].append(col)

            # Update offset
            self.current_offset = new_offset + len(new_tables)

            # Check if this was the last batch
            if len(new_tables) < additional_limit:
                self.all_tables_loaded = True

            if self.console:
                self.console.print(
                    f"[green]✓ Loaded {len(new_tables)} additional tables ({len(self.tables)} total)[/green]",
                )

            return True

        except Exception as e:
            if self.console:
                self.console.print(f"[red]Error loading additional data: {e}[/red]")
            self.all_tables_loaded = True
            return False

    def select_column(self, column: ColumnInfo) -> None:
        """Select a column in the basic TUI: sets the table and shows all columns
        for that table, with the clicked column highlighted. This mirrors the
        behavior in the Textual TUI's column selection.
        """
        if not column or not column.schema or not column.table:
            return

        table_key = f"{column.schema}.{column.table}"
        # Find and set the TableInfo
        for t in self.tables:
            if f"{t.schema}.{t.name}" == table_key:
                self.selected_table = t
                break
        # Set selected column name so render will highlight it
        self.selected_column_name = column.name
        # Update filtered columns in case search query or selection changed
        self.update_filters()

    def filter_items(self, items, query):
        """Filter items based on search query (case-insensitive partial match)."""
        if not query:
            return items

        query_lower = query.lower()
        filtered = []

        for item in items:
            # Check different fields for the query term
            name_match = query_lower in (getattr(item, "name", "") or "").lower()
            remarks_match = query_lower in (getattr(item, "remarks", "") or "").lower()
            type_match = query_lower in (getattr(item, "typename", "") or "").lower()

            if name_match or remarks_match or type_match:
                filtered.append(item)

        return filtered

    def update_filters(self):
        """Update filtered lists based on current search query."""
        self.filtered_tables = self.filter_items(self.tables, self.search_query)

        if self.selected_table:
            table_key = f"{self.selected_table.schema}.{self.selected_table.name}"
            if table_key in self.table_columns:
                # Show all columns of selected table, don't filter by search query
                self.filtered_columns = self.table_columns[table_key]
            else:
                self.filtered_columns = []
        else:
            # No table selected, show columns that match search
            self.filtered_columns = self.filter_items(self.columns, self.search_query)

    # Interactive TUI/CLI code removed. DBBrowserTUI is a non-UI backend
    # model used by the GUI and tests. UI responsibilities moved to the
    # Qt GUI (src/dbutils/gui/qt_app.py).
    # One-shot CLI/console search removed — db_browser is GUI-only.


def main() -> None:
    """GUI-only entry point for the DB Browser package.

    Delegates to the Qt-only launcher (main_launcher.main). Running this
    module or calling dbutils.db_browser.main() will launch the Qt GUI.
    """
    from . import main_launcher as _ml

    return _ml.main()


if __name__ == "__main__":
    # Always launch the GUI when executing this module directly
    main()
