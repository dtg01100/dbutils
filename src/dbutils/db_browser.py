#!/usr/bin/env python3
"""dbutils.db_browser - DB2 Schema Browser TUI

Interactive terminal UI for searching and browsing DB2 tables and columns.
Provides a fzf-like search experience for database schemas.
"""

import argparse
import asyncio
import csv
import io
import json
import os
import pickle
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

# Import rich for TUI
try:
    from rich.console import Console
    from rich.text import Text
    from rich.panel import Panel

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# Import Textual for advanced TUI with mouse support
try:
    from textual.app import App, ComposeResult
    from textual.containers import Container, Horizontal, Vertical
    from textual.widgets import Input, Static, DataTable, Footer, Header, Button, Label, ListView, ListItem
    from textual.binding import Binding
    from textual.screen import ModalScreen
    from textual import on

    TEXTUAL_AVAILABLE = True
except ImportError:
    TEXTUAL_AVAILABLE = False

from dataclasses import dataclass
from typing import Set

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
        """Recursively collect all items from this node and descendants."""
        if node.is_end_of_word:
            result.update(node.items)
        for child in node.children.values():
            self._collect_all_items(child, result)


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


def query_runner(sql: str) -> List[Dict]:
    """Execute SQL and return rows as list[dict].

    Priority:
    1) If environment variable DBUTILS_JDBC_PROVIDER is set, use JDBC provider via JayDeBeApi.
       Optionally pass DBUTILS_JDBC_URL_PARAMS (JSON) and DBUTILS_JDBC_USER/PASSWORD.
    2) Otherwise, fall back to the external `query_runner` command (legacy) and parse output.
    """
    # Attempt JDBC path first if configured
    provider_name = os.environ.get("DBUTILS_JDBC_PROVIDER")
    if provider_name:
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
            # Fall back to legacy path if JDBC fails, but log the reason
            try:
                sys.stderr.write(f"[db_browser] JDBC path failed, falling back to external runner: {e}\n")
                sys.stderr.flush()
            except Exception:
                pass

    # Legacy external runner path
    with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as f:
        f.write(sql)
        temp_file = f.name

    try:
        result = subprocess.run(["query_runner", "-t", "db2", temp_file], check=False, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"query_runner failed: {result.stderr}")

        # Try JSON first
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            # Assume tab-separated with header
            reader = csv.DictReader(io.StringIO(result.stdout), delimiter="\t")
            return list(reader)
    finally:
        os.unlink(temp_file)


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
            import gzip

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
        import time

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
                import gzip

                with gzip.open(CACHE_FILE, "rb") as f:
                    cache_data = pickle.load(f)
            except Exception:
                cache_data = {}

        # Update cache
        import time

        cache_key = get_cache_key(schema_filter, limit, offset)
        cache_data[cache_key] = {"timestamp": time.time(), "tables": tables, "columns": columns}

        # Save cache compressed
        import gzip

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
        print(f"Warning: Could not fetch schemas: {exc}")

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
        print(f"Warning: Could not fetch schemas: {exc}")

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
) -> tuple[List[TableInfo], List[ColumnInfo]]:
    """Async version that can run queries in parallel."""
    if use_mock:
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
        print(f"Warning: Could not fetch tables/columns: {e}")
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
) -> tuple[List[TableInfo], List[ColumnInfo]]:
    """Synchronous wrapper for get_all_tables_and_columns_async."""
    import asyncio

    try:
        # Check if there's already a running event loop
        asyncio.get_running_loop()
        # If we're in an async context, fall back to sync implementation
        return _get_all_tables_and_columns_sync(schema_filter, use_mock, use_cache, limit, offset)
    except RuntimeError:
        # No running loop, we can create one
        pass

    # Create new event loop (preferred way in Python 3.10+)
    return asyncio.run(get_all_tables_and_columns_async(schema_filter, use_mock, use_cache, limit, offset))


def _get_all_tables_and_columns_sync(
    schema_filter: Optional[str] = None,
    use_mock: bool = False,
    use_cache: bool = True,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
) -> tuple[List[TableInfo], List[ColumnInfo]]:
    """Synchronous fallback implementation with query optimizations."""
    if use_mock:
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
        print(f"Warning: Could not fetch tables/columns: {e}")
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
        print(f"Warning: Could not fetch tables: {e}")

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
        print(f"Warning: Could not fetch columns: {e}")

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

    def run_basic_interactive(self):
        """Fallback interactive mode using standard input."""
        if self.console:
            self.console.print("[yellow]Using basic command-line mode (not fully interactive)[/yellow]")
            self.console.print("For the full interactive TUI experience, run in a proper terminal.")
            self.console.print("")

        while True:
            # Display search bar
            if self.console:
                search_panel = self.render_search_bar()
                self.console.print(search_panel)

            # Display tables and columns side by side using simple text layout
            if self.console:
                table_panel = self.render_table_list()
                col_panel = self.render_column_list()

                # For basic mode, display sequentially since Rich layout doesn't work well in non-TTY
                self.console.print(table_panel)
                self.console.print("")  # Add spacing
                self.console.print(col_panel)

            try:
                # Get user command
                user_input = input("\nEnter command ([N]umber to select table, [S]earch term, [Q]uit): ").strip()

                if not user_input:
                    continue

                # Handle different input types
                if user_input.lower() in ["q", "quit", "exit"]:
                    break
                if user_input.lower() in ["s", "search"]:
                    search_term = input("Enter search term: ").strip()
                    self.search_query = search_term
                elif user_input.isdigit():
                    table_num = int(user_input) - 1
                    if 0 <= table_num < len(self.filtered_tables):
                        self.selected_table = self.filtered_tables[table_num]
                        self.selected_column_name = None
                        if self.console:
                            self.console.print(
                                f"[green]Selected: {self.selected_table.schema}.{self.selected_table.name}[/green]",
                            )
                    else:
                        if self.console:
                            self.console.print(
                                f"[red]Invalid table number. Please select 1-{len(self.filtered_tables)}[/red]",
                            )
                        continue
                elif user_input.startswith("> "):
                    self.search_query = user_input[2:]
                else:
                    # Treat as search term
                    self.search_query = user_input

            except KeyboardInterrupt:
                break
            except EOFError:
                break

    def render_search_bar(self):
        """Render the search bar."""
        if not self.console:
            return None

        if self.search_query:
            # Truncate long search queries
            search_display = self.search_query[:50]
            if len(self.search_query) > 50:
                search_display += "..."
            search_text = f"> {search_display}"
        else:
            search_text = "> (type to search)"

        return Panel(
            Text(search_text, style="bold"),
            title="Search [Enter: select table, Ctrl+C: quit]",
            border_style="cyan",
        )

    def render_table_list(self, panel_width=None):
        """Render the table list panel as formatted text."""
        if not self.console:
            return None

        self.update_filters()

        lines = []
        lines.append("Tables:")
        for i, t in enumerate(self.filtered_tables[:10]):  # Show first 10
            marker = (
                "→"
                if (
                    self.selected_table
                    and t.schema == self.selected_table.schema
                    and t.name == self.selected_table.name
                )
                else " "
            )
            table_info = f"{i + 1}. {t.schema}.{t.name}"
            lines.append(f"  {marker} {table_info}")

        content = "\n".join(lines)
        return Panel(
            Text(content),
            title=f"Tables ({len(self.filtered_tables)} total)",
            border_style="blue",
        )

    def render_column_list(self, panel_width=None):
        """Render the column list panel."""
        if not self.console:
            return None

        if not self.selected_table:
            # If there's an active search, show columns matching the query across all tables
            if self.search_query:
                # Use filtered_columns which was computed by update_filters()
                self.update_filters()
                matches = self.filtered_columns
                lines = [f"Columns matching '{self.search_query}':"]
                for i, c in enumerate(matches[:50]):
                    lines.append(f"  {i + 1}. {c.schema}.{c.table}.{c.name} ({c.typename})")

                content = "\n".join(lines)
                return Panel(Text(content), title=f"Column Matches ({len(matches)} found)", border_style="yellow")

            return Panel(
                "Select a table to see its columns\n\nUse number keys or ↑↓ arrows to select tables",
                title="Columns",
                border_style="yellow",
            )

        lines = []
        lines.append(f"Columns in {self.selected_table.schema}.{self.selected_table.name}:")

        table_key = f"{self.selected_table.schema}.{self.selected_table.name}"
        columns = self.table_columns.get(table_key, [])

        for i, c in enumerate(columns[:10]):  # Show first 10
            marker = "→" if self.selected_column_name and c.name == self.selected_column_name else " "
            lines.append(f"  {marker} {i + 1}. {c.name} ({c.typename})")

        content = "\n".join(lines)
        return Panel(
            Text(content),
            title=f"Columns ({len(columns)} total)",
            border_style="green",
        )

    def run(self):
        """Run the TUI application."""
        if self.console:
            self.console.print("DB2 Schema Browser - Interactive TUI", style="bold blue")
            self.console.print("Loading... (the interactive search bar will appear below)", style="dim")

        try:
            self.run_basic_interactive()
        except KeyboardInterrupt:
            pass


# Textual-based TUI with keyboard and mouse support
if TEXTUAL_AVAILABLE:

    class SettingsScreen(ModalScreen):
        """A modal screen for settings configuration."""

        CSS = """
        SettingsScreen {
            align: center middle;
        }

        #settings-dialog {
            width: 70;
            height: auto;
            max-height: 90%;
            border: thick $background 80%;
            background: $surface;
            padding: 1 2;
        }

        #settings-title {
            width: 100%;
            text-align: center;
            color: $accent;
            text-style: bold;
            margin-bottom: 1;
        }

        .settings-section {
            margin: 1 0;
        }

        .settings-label {
            color: $text;
            text-style: bold;
            margin: 1 0 0 0;
        }

        #schema-list {
            height: 20;
            border: solid $primary;
            margin: 1 0;
        }

        .help-text {
            color: $text-muted;
            text-style: italic;
            margin: 0 0 1 0;
        }

        #loading-text {
            color: $warning;
            text-style: italic;
            text-align: center;
        }

        #buttons-container {
            layout: horizontal;
            width: 100%;
            height: auto;
            align: center middle;
            margin-top: 1;
        }

        #buttons-container Button {
            margin: 0 1;
        }
        """

        BINDINGS = [
            Binding("escape", "dismiss(None)", "Cancel"),
        ]

        def __init__(self, current_schema: Optional[str] = None, use_mock: bool = False):
            super().__init__()
            self.current_schema = current_schema or ""
            self.use_mock = use_mock
            self.schemas: List[SchemaInfo] = []
            self.selected_schema: Optional[str] = None

        def compose(self) -> ComposeResult:
            """Compose the settings dialog."""
            with Container(id="settings-dialog"):
                yield Label("Select Schema", id="settings-title")

                with Container(classes="settings-section"):
                    yield Label("Available Schemas:", classes="settings-label")
                    yield Label("Loading schemas...", id="loading-text")
                    yield ListView(id="schema-list")
                    yield Label(
                        "Select a schema to filter tables, or choose 'All Schemas' to search everything.",
                        classes="help-text",
                    )

                with Horizontal(id="buttons-container"):
                    yield Button("Select", variant="primary", id="select-button")
                    yield Button("Cancel", variant="default", id="cancel-button")

        async def on_mount(self) -> None:
            """Load schemas when mounted."""
            # Load schemas in background
            asyncio.create_task(self.load_schemas())

        async def load_schemas(self) -> None:
            """Load available schemas."""
            try:
                # Fetch schemas using async version to avoid blocking
                self.schemas = await get_available_schemas_async(self.use_mock)

                # Update UI
                loading_label = self.query_one("#loading-text", Label)
                loading_label.display = False

                schema_list = self.query_one("#schema-list", ListView)

                # Add "All Schemas" option
                all_item = ListItem(Label("[All Schemas] (all tables)"))
                all_item.add_class("schema-all")
                schema_list.append(all_item)

                # Add individual schemas
                for schema in self.schemas:
                    # Humanize display label: show readable name and table count
                    display_name = humanize_schema_name(schema.name)
                    item_label = f"{display_name} ({schema.table_count} table{'s' if schema.table_count != 1 else ''})"
                    item = ListItem(Label(item_label))
                    if schema.name == self.current_schema:
                        schema_list.index = len(schema_list) - 1 + 1  # Will select after append
                    schema_list.append(item)

                # Set initial selection
                if self.current_schema:
                    # Find and select current schema
                    for idx, schema in enumerate(self.schemas):
                        if schema.name == self.current_schema:
                            schema_list.index = idx + 1  # +1 for "All Schemas" option
                            break
                else:
                    # Select "All Schemas"
                    schema_list.index = 0

            except Exception as e:
                loading_label = self.query_one("#loading-text", Label)
                loading_label.update(f"Error loading schemas: {e}")

        @on(ListView.Selected, "#schema-list")
        def schema_selected(self, event: ListView.Selected) -> None:
            """Handle schema selection from list."""
            index = event.list_view.index
            if index == 0:
                # "All Schemas" selected
                self.selected_schema = None
            else:
                # Individual schema selected
                schema_idx = index - 1
                if 0 <= schema_idx < len(self.schemas):
                    self.selected_schema = self.schemas[schema_idx].name

        @on(Button.Pressed, "#select-button")
        def select_schema(self) -> None:
            """Select the highlighted schema and close."""
            schema_list = self.query_one("#schema-list", ListView)
            index = schema_list.index

            if index is None or index < 0:
                # Nothing selected, use current
                self.dismiss(self.current_schema if self.current_schema else None)
                return

            if index == 0:
                # "All Schemas" selected
                self.dismiss(None)
            else:
                # Individual schema selected
                schema_idx = index - 1
                if 0 <= schema_idx < len(self.schemas):
                    self.dismiss(self.schemas[schema_idx].name)
                else:
                    self.dismiss(None)

        @on(Button.Pressed, "#cancel-button")
        def cancel_settings(self) -> None:
            """Cancel and close."""
            self.dismiss(None)

    class DBBrowserApp(App):
        """A Textual app for browsing DB2 schemas with keyboard and mouse support."""

        CSS = """
        Screen {
            layout: vertical;
        }

        #search-container {
            height: auto;
            layout: horizontal;
            background: $surface;
            border: solid $primary;
            padding: 1;
            align: center middle;
        }

        #search-input {
            width: 1fr;
            margin: 0;
            color: white;
            background: black;
        }

        #search-input:focus {
            background: #111111;
        }

        #search-input > .input--placeholder {
            color: gray;
        }

        #search-mode-label {
            width: auto;
            min-width: 20;
            margin: 0 1 0 0;
        }

        Button#search-mode-label {
            width: auto;
            min-width: 20;
        }

        #main-container {
            layout: horizontal;
            height: 1fr;
        }

        #tables-container {
            width: 1fr;
            border: solid $accent;
        }

        #columns-container {
            width: 2fr;
            border: solid $success;
        }

        DataTable {
            height: 1fr;
        }

        DataTable > .datatable--cursor {
            background: $accent 50%;
        }

        DataTable > .datatable--hover {
            background: $accent 30%;
        }

        .info-text {
            color: $text-muted;
            padding: 1;
        }

        .search-mode {
            color: $accent;
            text-style: bold;
            background: $panel;
            border: solid $accent;
            padding: 0 1;
        }
        """

        BINDINGS = [
            Binding("q", "quit", "Quit"),
            Binding("ctrl+c", "quit", "Quit"),
            Binding("escape", "clear_search", "Clear Search"),
            Binding("f1", "help", "Help", show=False),
            Binding("/", "focus_search", "Search"),
            Binding("tab", "toggle_search_mode", "Toggle Search Mode"),
            Binding("s", "open_settings", "Settings"),
            Binding("l", "load_more", "Load More Tables"),
            Binding("ctrl+l", "load_all_results", "Load All Results"),
            Binding("h", "toggle_non_matching", "Show/Hide Non-Matching"),
            Binding("x", "toggle_stream_search", "Toggle Streaming Search"),
        ]

        def __init__(
            self,
            schema_filter: Optional[str] = None,
            use_mock: bool = False,
            use_cache: bool = True,
            initial_load_limit: int = 100,
        ):
            super().__init__()
            self.schema_filter = schema_filter
            self.use_mock = use_mock
            self.use_cache = use_cache
            self.initial_load_limit = initial_load_limit
            self.tables: List[TableInfo] = []
            self.columns: List[ColumnInfo] = []
            self.table_columns: Dict[str, List[ColumnInfo]] = {}
            self.search_query = ""
            self.search_mode = "tables"  # "tables" or "columns"
            # Lazy loading state
            self.all_tables_loaded = False
            self.current_offset = 0
            self.total_tables_estimate = None
            # Multi-level caching system
            self._search_cache: Dict[str, Dict[str, Any]] = {}  # Search results cache
            self._ui_cache: Dict[str, Any] = {}  # UI rendering cache
            self._last_search_query = ""
            self._last_search_mode = ""
            self._debounce_timer: Optional[asyncio.Task] = None
            self._cache_timestamp = 0  # Timestamp for cache invalidation
            # Result limiting for performance
            self.max_displayed_results = 200  # Maximum rows to display in tables
            self.search_debounce_delay = 0.2  # Search debounce delay in seconds
            # Scroll-based loading state
            self._scroll_load_triggered = False
            self._current_displayed_count = 0
            self._total_available_results = 0
            # Fast search index using trie
            self.search_index = SearchIndex()
            # Pre-computed lowercase fields for faster searching (fallback)
            self._table_search_data: Dict[str, str] = {}  # table_key -> lowercase searchable text
            self._column_search_data: Dict[str, str] = {}  # column_key -> lowercase searchable text
            # Column search display options
            self.show_non_matching_tables = True  # Toggle to show/hide tables without matching columns
            # Streaming search results
            self._stream_search_enabled = True  # Enable streaming search results
            self._current_stream_task: Optional[asyncio.Task] = None  # Current streaming task
            self._streamed_results: List = []  # Results found so far in current search

        # -----------------------------
        # Search caching & debounce utils
        # -----------------------------
        def _cache_key(self, mode: str, query: str) -> str:
            return f"{mode}|{(query or '').lower()}"

        def _get_cached(self, mode: str, query: str) -> Optional[Dict[str, Any]]:
            return self._search_cache.get(self._cache_key(mode, query))

        def _set_cached(self, mode: str, query: str, value: Dict[str, Any]) -> None:
            self._search_cache[self._cache_key(mode, query)] = value

        def _clear_search_cache(self) -> None:
            """Clear search result cache."""
            self._search_cache.clear()
            self._last_search_query = ""
            self._last_search_mode = ""

        def _clear_ui_cache(self) -> None:
            """Clear UI rendering cache."""
            self._ui_cache.clear()

        def _invalidate_all_caches(self) -> None:
            """Invalidate all caches when data changes."""
            self._clear_search_cache()
            self._clear_ui_cache()
            self._cache_timestamp = asyncio.get_event_loop().time() if asyncio.get_event_loop() else 0

        def _get_cached_ui_render(self, cache_key: str) -> Optional[Any]:
            """Get cached UI render result if still valid."""
            if cache_key in self._ui_cache:
                cached_item = self._ui_cache[cache_key]
                # Check if cache is still valid (same data timestamp)
                if cached_item.get("timestamp", 0) >= self._cache_timestamp:
                    return cached_item["data"]
            return None

        def _set_cached_ui_render(self, cache_key: str, data: Any) -> None:
            """Cache UI render result with memory-efficient storage."""
            # Compress data by removing redundant information
            compressed_data = self._compress_ui_data(data)

            self._ui_cache[cache_key] = {
                "data": compressed_data,
                "timestamp": self._cache_timestamp,
                "access_count": 0,  # For LRU tracking
            }

            # Limit UI cache size to prevent memory bloat (more aggressive limit)
            if len(self._ui_cache) > 30:  # Keep last 30 UI renders
                # Remove least recently used entries
                lru_entries = sorted(self._ui_cache.items(), key=lambda x: (x[1]["access_count"], x[1]["timestamp"]))[
                    :10
                ]  # Remove 10 LRU entries
                for key, _ in lru_entries:
                    del self._ui_cache[key]

        def _compress_ui_data(self, data: Dict) -> Dict:
            """Compress UI data to reduce memory usage."""
            compressed = data.copy()

            # Compress table rows by using tuples instead of dicts where possible
            if "table_rows" in compressed:
                compressed["table_rows"] = [(row["args"], row.get("key")) for row in compressed["table_rows"]]

            # Compress columns data
            if compressed.get("columns_data"):
                cols_data = compressed["columns_data"]
                if "rows" in cols_data:
                    cols_data["rows"] = [(row["args"], row.get("key")) for row in cols_data["rows"]]

            return compressed

        def _get_cached_ui_render(self, cache_key: str) -> Optional[Any]:
            """Get cached UI render result if still valid (with LRU tracking)."""
            if cache_key in self._ui_cache:
                cached_item = self._ui_cache[cache_key]
                # Check if cache is still valid (same data timestamp)
                if cached_item.get("timestamp", 0) >= self._cache_timestamp:
                    # Update access count for LRU
                    cached_item["access_count"] += 1
                    # Decompress data
                    return self._decompress_ui_data(cached_item["data"])
            return None

        def _decompress_ui_data(self, compressed_data: Dict) -> Dict:
            """Decompress UI data back to original format."""
            data = compressed_data.copy()

            # Decompress table rows
            if "table_rows" in data:
                data["table_rows"] = [{"args": args, "key": key} for args, key in data["table_rows"]]

            # Decompress columns data
            if data.get("columns_data"):
                cols_data = data["columns_data"]
                if "rows" in cols_data:
                    cols_data["rows"] = [{"args": args, "key": key} for args, key in cols_data["rows"]]

            return data

        def _apply_search_update(self) -> None:
            """Apply current search query/mode to UI."""
            self.update_tables_display()
            # If a table is selected, update columns display too
            try:
                tables_table = self.query_one("#tables-table", DataTable)
                if tables_table.cursor_row >= 0:
                    row = tables_table.get_row_at(tables_table.cursor_row)
                    if row:
                        self.update_columns_display(str(row[0]))
            except Exception:
                pass

        async def _debounced_apply(self, expected_query: str, expected_mode: str) -> None:
            try:
                await asyncio.sleep(0.2)
            except Exception:
                return
            # Only apply if state hasn't changed since timer was scheduled
            if self.search_query == expected_query and self.search_mode == expected_mode:
                self._apply_search_update()

        def compose(self) -> ComposeResult:
            """Create child widgets for the app."""
            yield Header()
            with Container(id="search-container"):
                yield Button("📋 Search Tables", id="search-mode-label", variant="default")
                yield Input(placeholder="Type to search tables by name or description...", id="search-input")
            with Horizontal(id="main-container"):
                with Vertical(id="tables-container"):
                    yield Static("Tables", classes="info-text")
                    yield DataTable(id="tables-table", cursor_type="row")
                with Vertical(id="columns-container"):
                    yield Static("Columns (select a table)", classes="info-text")
                    yield DataTable(id="columns-table", cursor_type="row")
            yield Footer()

        async def on_mount(self) -> None:
            """Load data when the app starts."""
            # Set the app title to show database and schema
            if self.schema_filter:
                self.title = f"DB Browser [S782c451] - Schema: {self.schema_filter}"
                self.sub_title = "Press 'S' to change schema"
            else:
                self.title = "DB Browser [S782c451] - All Schemas"
                self.sub_title = "Press 'S' to filter by schema"

            # Setup tables table FIRST (before showing loading message)
            tables_table = self.query_one("#tables-table", DataTable)
            tables_table.add_columns("Table", "Info")
            tables_table.cursor_type = "row"
            tables_table.zebra_stripes = True

            # Setup columns table FIRST (before showing loading message)
            columns_table = self.query_one("#columns-table", DataTable)
            columns_table.add_columns("Column", "Type", "Nulls", "Description")
            columns_table.cursor_type = "row"
            columns_table.zebra_stripes = True

            # Update info text to show loading
            tables_info = self.query_one("#tables-container .info-text", Static)
            tables_info.update("Loading tables...")

            # Show loading notification and start loading data after UI is ready
            self.call_after_refresh(self.start_loading)

        def start_loading(self) -> None:
            """Start loading data after UI is rendered."""
            # Show loading notification
            if self.use_mock:
                self.notify("Loading mock data...", timeout=1)
            elif self.schema_filter:
                self.notify(f"Loading schema: {self.schema_filter}... This may take a moment.", timeout=3)
            else:
                self.notify("Loading all database schemas... This may take a moment.", timeout=3)

            # Load data asynchronously to not block UI
            # Run the query in a worker to keep UI responsive
            self.run_worker(self.load_data, exclusive=True)

        async def load_data(self) -> None:
            """Load initial batch of data from database in background."""
            try:
                # Load initial batch of tables and columns (using async version for parallel queries)
                self.tables, self.columns = await get_all_tables_and_columns_async(
                    self.schema_filter,
                    self.use_mock,
                    self.use_cache,
                    limit=self.initial_load_limit,
                    offset=0,
                )

                # Check if we got fewer results than requested (indicates all data loaded)
                if len(self.tables) < self.initial_load_limit:
                    self.all_tables_loaded = True
                else:
                    # Estimate total tables for progress indication
                    await self._estimate_total_tables()

                # Build table-columns mapping and search index
                self.table_columns = {}
                self._table_search_data = {}
                self._column_search_data = {}

                for table in self.tables:
                    table_key = f"{table.schema}.{table.name}"
                    # Pre-compute lowercase searchable text for each table (fallback)
                    search_text = f"{table.name} {table.schema} {table.remarks or ''}".lower()
                    self._table_search_data[table_key] = search_text

                for col in self.columns:
                    if col.schema and col.table:
                        table_key = f"{col.schema}.{col.table}"
                        if table_key not in self.table_columns:
                            self.table_columns[table_key] = []
                        self.table_columns[table_key].append(col)

                        # Pre-compute lowercase searchable text for each column (fallback)
                        col_key = f"{col.schema}.{col.table}.{col.name}"
                        search_text = f"{col.name} {col.typename} {col.remarks or ''}".lower()
                        self._column_search_data[col_key] = search_text

                # Build fast search index
                self.search_index.build_index(self.tables, self.columns)

                # Update cache timestamp and clear caches
                self._invalidate_all_caches()

                # Populate tables
                self.update_tables_display()

                # Focus search input
                self.query_one("#search-input", Input).focus()

                # Show success message
                table_count = len(self.tables)
                column_count = len(self.columns)

                if table_count == 0:
                    if self.schema_filter:
                        self.notify(
                            f"⚠️ No tables found in schema '{self.schema_filter}'. Try Settings (S) to change schema.",
                            severity="warning",
                            timeout=8,
                        )
                    else:
                        self.notify("⚠️ No tables loaded! Check database connection.", severity="warning", timeout=5)
                else:
                    load_msg = f"✓ Loaded {table_count} tables"
                    if self.schema_filter:
                        load_msg += f" from '{self.schema_filter}'"
                    load_msg += f" ({column_count} columns)"

                    if not self.all_tables_loaded and self.total_tables_estimate:
                        load_msg += f" - {self.total_tables_estimate} total estimated"
                    elif not self.all_tables_loaded:
                        load_msg += " - more available"

                    self.notify(load_msg, severity="information", timeout=4)
            except Exception as e:
                self.notify(f"❌ Error loading schema: {e}", severity="error", timeout=10)
                self.tables, self.columns = [], []
                self.update_tables_display()

        async def _estimate_total_tables(self):
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

                # Run the query in an executor to avoid blocking
                loop = asyncio.get_event_loop()
                count_result = await loop.run_in_executor(None, query_runner, count_sql)
                if count_result and count_result[0].get("TOTAL_COUNT"):
                    self.total_tables_estimate = int(count_result[0]["TOTAL_COUNT"])
            except Exception:
                # If count fails, use a rough estimate
                self.total_tables_estimate = len(self.tables) * 2

        async def load_more_tables(self, additional_limit: int = 100) -> bool:
            """Load additional tables and their columns. Returns True if more data was loaded."""
            if self.all_tables_loaded:
                return False

            try:
                new_offset = len(self.tables)
                new_tables, new_columns = await get_all_tables_and_columns_async(
                    self.schema_filter,
                    self.use_mock,
                    self.use_cache,
                    limit=additional_limit,
                    offset=new_offset,
                )

                if not new_tables:
                    self.all_tables_loaded = True
                    return False

                # Add new tables and columns
                self.tables.extend(new_tables)
                self.columns.extend(new_columns)

                # Update table columns mapping and search data for new data
                for table in new_tables:
                    table_key = f"{table.schema}.{table.name}"
                    # Pre-compute lowercase searchable text for each table
                    search_text = f"{table.name} {table.schema} {table.remarks or ''}".lower()
                    self._table_search_data[table_key] = search_text

                for col in new_columns:
                    if col.schema and col.table:
                        table_key = f"{col.schema}.{col.table}"
                        if table_key not in self.table_columns:
                            self.table_columns[table_key] = []
                        self.table_columns[table_key].append(col)

                        # Pre-compute lowercase searchable text for each column
                        col_key = f"{col.schema}.{col.table}.{col.name}"
                        search_text = f"{col.name} {col.typename} {col.remarks or ''}".lower()
                        self._column_search_data[col_key] = search_text

                # Update offset
                self.current_offset = new_offset + len(new_tables)

                # Check if this was the last batch
                if len(new_tables) < additional_limit:
                    self.all_tables_loaded = True

                # Rebuild search index with new data
                self.search_index.build_index(self.tables, self.columns)

                # Update cache timestamp and clear caches
                self._invalidate_all_caches()

                # Refresh display with new data
                self.update_tables_display()

                # Show success message
                table_count = len(self.tables)
                load_msg = f"✓ Loaded {len(new_tables)} additional tables ({table_count} total)"
                if not self.all_tables_loaded and self.total_tables_estimate:
                    remaining = self.total_tables_estimate - table_count
                    load_msg += f" - {remaining} remaining"
                self.notify(load_msg, severity="information", timeout=3)

                return True

            except Exception as e:
                self.notify(f"❌ Error loading additional data: {e}", severity="error", timeout=5)
                self.all_tables_loaded = True
                return False

        def update_tables_display(self) -> None:
            """Update the tables display based on current search mode with caching."""
            # Create cache key for this display state
            cache_key = f"tables_display_{self.search_mode}_{self.search_query}_{len(self.tables)}_{self._cache_timestamp}_{id(self)}"

            # Try to get cached display data
            cached_display = self._get_cached_ui_render(cache_key)
            if cached_display:
                # Apply cached display data
                tables_table = self.query_one("#tables-table", DataTable)
                tables_table.clear()
                for row_data in cached_display["table_rows"]:
                    tables_table.add_row(*row_data["args"], key=row_data.get("key"))

                # Update info texts
                info = self.query_one("#tables-container .info-text", Static)
                info.update(cached_display["tables_info"])

                if cached_display.get("columns_data"):
                    columns_table = self.query_one("#columns-table", DataTable)
                    columns_table.clear()
                    for row_data in cached_display["columns_data"]["rows"]:
                        columns_table.add_row(*row_data["args"], key=row_data.get("key"))
                    info = self.query_one("#columns-container .info-text", Static)
                    info.update(cached_display["columns_data"]["info"])

                # Restore cursor position
                if cached_display.get("cursor_row") is not None:
                    tables_table.cursor_row = cached_display["cursor_row"]

                return

            # Cache miss - compute display data
            tables_table = self.query_one("#tables-table", DataTable)
            tables_table.clear()

            display_data = {"table_rows": [], "tables_info": "", "cursor_row": None}

            if self.search_mode == "tables":
                # Standard table search - filter tables by name/description
                if not self.search_query:
                    filtered_tables = self.tables
                else:
                    cached = self._get_cached("tables", self.search_query)
                    if cached and "filtered_tables" in cached:
                        filtered_tables = cached["filtered_tables"]
                    else:
                        filtered_tables = self.filter_tables(self.tables, self.search_query)
                        self._set_cached("tables", self.search_query, {"filtered_tables": filtered_tables})

                # Determine how many results to display
                total_available_results = len(filtered_tables)

                # If we have a small result set that fits comfortably on screen, load everything
                small_result_threshold = 50  # If <= 50 results, load all available
                if (
                    total_available_results <= small_result_threshold
                    and not self.all_tables_loaded
                    and self.search_query
                ):
                    # Load all available data for small result sets
                    self._background_load_task = asyncio.create_task(self._load_all_for_small_search(self.search_query))
                    # For now, show what we have
                    displayed_tables = filtered_tables
                    has_more_results = False
                else:
                    # Use normal display limit
                    displayed_tables = filtered_tables[: self.max_displayed_results]
                    has_more_results = len(filtered_tables) > self.max_displayed_results

                # Add rows
                for table in displayed_tables:
                    tables_table.add_row(table.name, table.remarks or "", key=f"{table.schema}.{table.name}")

                # Store information for scroll-based loading
                self._current_displayed_count = len(displayed_tables)
                self._total_available_results = total_available_results

                # Show loading indicator if background load is in progress
                if (
                    hasattr(self, "_background_load_task")
                    and self._background_load_task
                    and not self._background_load_task.done()
                ):
                    tables_table.add_row(
                        "🔄 Loading more results...",
                        f"Searching {len(self.tables)} tables loaded so far",
                        key="loading_indicator",
                    )
                    display_data["tables_info"] = f"Tables ({len(displayed_tables)} matching, searching more data...)"
                elif has_more_results:
                    # Fallback to manual load option if background loading not available
                    remaining = len(filtered_tables) - self.max_displayed_results
                    tables_table.add_row(
                        f"... and {remaining} more tables",
                        "Press Ctrl+L to load all results",
                        key=f"load_more_tables_{self.search_mode}",
                    )
                    display_data["tables_info"] = (
                        f"Tables ({len(displayed_tables)}+ matching, {remaining} more available)"
                    )
                else:
                    display_data["tables_info"] = f"Tables ({len(filtered_tables)} matching)"
                info = self.query_one("#tables-container .info-text", Static)
                info.update(display_data["tables_info"])

            # Column-focused search - find tables that contain matching columns
            elif not self.search_query:
                # Show all tables when no search
                for table in self.tables:
                    row_data = {"args": (table.name, table.remarks or ""), "key": f"{table.schema}.{table.name}"}
                    display_data["table_rows"].append(row_data)
                    tables_table.add_row(*row_data["args"], key=row_data["key"])
                display_data["tables_info"] = f"Tables ({len(self.tables)} total)"
                info = self.query_one("#tables-container .info-text", Static)
                info.update(display_data["tables_info"])
            else:
                # Try cache first
                cached = self._get_cached("columns", self.search_query)
                if cached and "matching_table_counts" in cached and "matching_columns" in cached:
                    matching_table_counts = cached["matching_table_counts"]
                    matching_columns = cached["matching_columns"]
                else:
                    # Optimized column search with table-level aggregation
                    matching_table_counts: Dict[str, int] = {}
                    matching_columns = []
                    q = self.search_query

                    # Pre-compute query lower for performance
                    q_lower = q.lower()

                    for col in self.columns:
                        # Fast pre-computed data check first
                        col_key = f"{col.schema}.{col.table}.{col.name}"
                        search_text = self._column_search_data.get(col_key, "")

                        # Quick substring check
                        matches = False
                        if q_lower in search_text:
                            matches = True
                        else:
                            # Fall back to fuzzy matching only if needed
                            matches = (
                                self.fuzzy_match(col.name, q)
                                or self.fuzzy_match(col.typename, q)
                                or self.fuzzy_match(col.remarks or "", q)
                            )

                        if matches:
                            t_key = f"{col.schema}.{col.table}"
                            matching_table_counts[t_key] = matching_table_counts.get(t_key, 0) + 1
                            matching_columns.append(col)

                    self._set_cached(
                        "columns",
                        self.search_query,
                        {
                            "matching_table_counts": matching_table_counts,
                            "matching_columns": matching_columns,
                        },
                    )

                # Display ALL tables with their matching column counts
                tables_with_matches = []
                tables_without_matches = []
                columns_data = {"rows": [], "info": ""}

                for table in self.tables:
                    table_key = f"{table.schema}.{table.name}"
                    match_count = matching_table_counts.get(table_key, 0)

                    if match_count > 0:
                        # Tables with matching columns - always show
                        info_text = table.remarks or ""
                        if info_text:
                            info_text = f"{info_text} — {match_count} matching column(s)"
                        else:
                            info_text = f"{match_count} matching column(s)"
                        row_data = {"args": (table.name, info_text), "key": table_key}
                        display_data["table_rows"].append(row_data)
                        tables_table.add_row(*row_data["args"], key=row_data["key"])
                        tables_with_matches.append(table)
                    elif self.show_non_matching_tables:
                        # Tables without matching columns - only show if option is enabled
                        info_text = table.remarks or "No matching columns"
                        if info_text and info_text != "No matching columns":
                            info_text = f"{info_text} — no matching columns"
                        else:
                            info_text = "no matching columns"
                        row_data = {"args": (f"· {table.name}", info_text), "key": table_key}
                        display_data["table_rows"].append(row_data)
                        tables_table.add_row(*row_data["args"], key=row_data["key"])
                        tables_without_matches.append(table)

                # Store information for scroll-based loading
                self._current_displayed_count = len(matching_columns)
                self._total_available_results = len(matching_columns)

                # Show loading indicator if background load is in progress
                if (
                    hasattr(self, "_background_load_task")
                    and self._background_load_task
                    and not self._background_load_task.done()
                ):
                    # Add loading indicator to table display
                    tables_table.add_row(
                        "🔄 Loading more results...",
                        f"Searching {len(self.tables)} tables loaded so far",
                        key="loading_indicator",
                    )
                    total_tables = len(tables_with_matches) + len(tables_without_matches)
                    total_matching_columns = len(matching_columns)

                    if self.show_non_matching_tables:
                        display_data["tables_info"] = (
                            f"Tables ({total_tables} total, {len(tables_with_matches)} with matches, {total_matching_columns} matching columns, searching more data...)"
                        )
                    else:
                        display_data["tables_info"] = (
                            f"Tables ({len(tables_with_matches)} with matches, {total_matching_columns} matching columns, searching more data... [H: toggle non-matching]"
                        )
                else:
                    total_tables = len(tables_with_matches) + len(tables_without_matches)
                    total_matching_columns = len(matching_columns)

                    if self.show_non_matching_tables:
                        display_data["tables_info"] = (
                            f"Tables ({total_tables} total, {len(tables_with_matches)} with matches, {total_matching_columns} matching columns total)"
                        )
                    else:
                        display_data["tables_info"] = (
                            f"Tables ({len(tables_with_matches)} with matches, {total_matching_columns} matching columns) [H: toggle non-matching]"
                        )
                info = self.query_one("#tables-container .info-text", Static)
                info.update(display_data["tables_info"])

                # Populate the columns panel with limited matches across tables
                columns_table = self.query_one("#columns-table", DataTable)
                columns_table.clear()

                # Limit displayed columns for performance
                displayed_columns = matching_columns[: self.max_displayed_results]
                has_more_columns = len(matching_columns) > self.max_displayed_results

                for col in displayed_columns:
                    col_key = f"{col.schema}.{col.table}.{col.name}"
                    type_str = f"{col.typename}"
                    if col.length:
                        type_str += f"({col.length}"
                        if col.scale:
                            type_str += f",{col.scale}"
                        type_str += ")"
                    row_data = {
                        "args": (f"{col.schema}.{col.table}.{col.name}", type_str, col.nulls, col.remarks or ""),
                        "key": col_key,
                    }
                    columns_data["rows"].append(row_data)
                    columns_table.add_row(*row_data["args"], key=row_data["key"])

                # Add indicator for more results if needed
                if has_more_columns:
                    remaining = len(matching_columns) - self.max_displayed_results
                    columns_table.add_row(
                        f"... and {remaining} more columns",
                        "",
                        "",
                        "Press Ctrl+L to load all results",
                        key=f"load_more_columns_{self.search_mode}",
                    )

                if has_more_columns:
                    columns_data["info"] = (
                        f"Column matches across tables ({len(displayed_columns)}+ found, {remaining} more available)"
                    )
                else:
                    columns_data["info"] = f"Column matches across tables ({len(matching_columns)} found)"
                info = self.query_one("#columns-container .info-text", Static)
                info.update(columns_data["info"])
                display_data["columns_data"] = columns_data

            # Set cursor position for selected table
            try:
                if self.selected_table:
                    for idx in range(tables_table.row_count):
                        row = tables_table.get_row_at(idx)
                        if row and row[0] == self.selected_table.name:
                            tables_table.cursor_row = idx
                            display_data["cursor_row"] = idx
                            break
            except Exception:
                pass

            # Cache the display data
            self._set_cached_ui_render(cache_key, display_data)

        def column_matches_query(self, col: ColumnInfo, query: str) -> bool:
            """Check if a column matches the search query using pre-computed data and fuzzy matching."""
            if not query:
                return True

            col_key = f"{col.schema}.{col.table}.{col.name}"
            search_text = self._column_search_data.get(col_key, "")
            query_lower = query.lower()

            # Fast substring check first using pre-computed data
            if query_lower in search_text:
                return True

            # Fall back to fuzzy matching
            return (
                self.fuzzy_match(col.name, query)
                or self.fuzzy_match(col.typename, query)
                or self.fuzzy_match(col.remarks or "", query)
            )

        def update_columns_display(self, table_key: Optional[str] = None) -> None:
            """Update the columns display for selected table."""
            columns_table = self.query_one("#columns-table", DataTable)
            columns_table.clear()

            if not table_key:
                info = self.query_one("#columns-container .info-text", Static)
                info.update("Columns (select a table)")
                return

            # Get columns for this table
            columns = self.table_columns.get(table_key, [])

            # In column search mode with a query, show all columns but dim non-matches
            show_all_with_dimming = self.search_mode == "columns" and self.search_query

            if show_all_with_dimming:
                # Show all columns, marking which ones match
                matching_count = 0
                for col in columns:
                    type_str = f"{col.typename}"
                    if col.length:
                        type_str += f"({col.length}"
                        if col.scale:
                            type_str += f",{col.scale}"
                        type_str += ")"

                    # Use full key including schema.table.column so we can map selection back
                    col_key = f"{col.schema}.{col.table}.{col.name}"

                    # Check if this column matches the search query
                    matches = self.column_matches_query(col, self.search_query)
                    if matches:
                        matching_count += 1
                        # Matching columns shown normally
                        columns_table.add_row(col.name, type_str, col.nulls, col.remarks or "", key=col_key)
                    else:
                        # Non-matching columns shown with prefix indicator
                        dim_name = f"· {col.name}"
                        columns_table.add_row(dim_name, type_str, col.nulls, col.remarks or "", key=col_key)

                # Update info text with match count
                info = self.query_one("#columns-container .info-text", Static)
                schema, table = table_key.split(".", 1)
                info.update(f"Columns in {schema}.{table} ({matching_count} matching, {len(columns)} total)")
            else:
                # Standard mode: filter columns if there's a search query in table mode
                if self.search_query and self.search_mode == "tables":
                    columns = self.filter_columns(columns, self.search_query)

                # Add rows
                for col in columns:
                    type_str = f"{col.typename}"
                    if col.length:
                        type_str += f"({col.length}"
                        if col.scale:
                            type_str += f",{col.scale}"
                        type_str += ")"

                    # Use full key including schema.table.column so we can map selection back
                    col_key = f"{col.schema}.{col.table}.{col.name}"
                    columns_table.add_row(col.name, type_str, col.nulls, col.remarks or "", key=col_key)

                # Update info text
                info = self.query_one("#columns-container .info-text", Static)
                schema, table = table_key.split(".", 1)
                info.update(f"Columns in {schema}.{table} ({len(columns)} total)")

            # If a column was previously selected, focus/highlight it now
            if hasattr(self, "selected_column_key") and self.selected_column_key:
                try:
                    # Find the selected column in the columns table and set the cursor
                    sel_col = self.selected_column_key
                    sel_col_name = sel_col.split(".")[-1]
                    for idx in range(columns_table.row_count):
                        row = columns_table.get_row_at(idx)
                        if row:
                            # Handle both normal and dimmed column names
                            col_display_name = str(row[0])
                            actual_col_name = col_display_name.lstrip("· ")
                            if actual_col_name == sel_col_name:
                                columns_table.cursor_row = idx
                                break
                except Exception:
                    pass

        def edit_distance(self, s1: str, s2: str) -> int:
            """Calculate Levenshtein distance between two strings.
            Returns the minimum number of edits needed to transform s1 into s2.
            """
            if len(s1) < len(s2):
                return self.edit_distance(s2, s1)

            if len(s2) == 0:
                return len(s1)

            previous_row = range(len(s2) + 1)
            for i, c1 in enumerate(s1):
                current_row = [i + 1]
                for j, c2 in enumerate(s2):
                    # Cost of insertions, deletions, or substitutions
                    insertions = previous_row[j + 1] + 1
                    deletions = current_row[j] + 1
                    substitutions = previous_row[j] + (c1 != c2)
                    current_row.append(min(insertions, deletions, substitutions))
                previous_row = current_row

            return previous_row[-1]

        def fuzzy_match(self, text: str, query: str) -> bool:
            """Highly optimized fuzzy match with multiple strategies and early exits.
            Prioritizes speed over perfect accuracy for better UX.
            """
            if not query:
                return True
            if not text:
                return False

            text_lower = text.lower()
            query_lower = query.lower()
            query_len = len(query_lower)
            text_len = len(text_lower)

            # Strategy 1: Exact substring match (fastest) - early exit
            if query_lower in text_lower:
                return True

            # For very short queries, only check exact matches
            if query_len < 2:
                return False

            # Strategy 2: Word boundary prefix match (fast and intuitive)
            # Split by common separators and check if query matches start of any word
            words = text_lower.replace("_", " ").replace("-", " ").split()
            for word in words:
                word_len = len(word)
                # Check prefix match
                if word.startswith(query_lower):
                    return True
                # For longer queries, check if word contains query as prefix
                if word_len >= query_len and word[:query_len] == query_lower:
                    return True

            # Strategy 3: Character-based approximate matching
            # Only for reasonable length queries to avoid performance issues
            if query_len <= 20 and text_len >= query_len:
                # Fast sequential character match (allows skips)
                text_idx = 0
                match_count = 0
                for char in query_lower:
                    found_idx = text_lower.find(char, text_idx)
                    if found_idx == -1:
                        # Allow some character skips for fuzzy matching
                        if match_count >= max(1, query_len - 2):  # Allow up to 2 misses
                            return True
                        return False
                    text_idx = found_idx + 1
                    match_count += 1

                # If we matched most characters, consider it a match
                if match_count >= max(1, query_len - 1):
                    return True

            # Strategy 4: Edit distance for similar short words (most expensive, used sparingly)
            if query_len >= 3 and query_len <= 10:
                # Only check edit distance for words of similar length
                words = text_lower.replace("_", " ").split()
                for word in words:
                    word_len = len(word)
                    if abs(word_len - query_len) <= 2 and word_len >= 3:
                        # Use optimized edit distance with early exit
                        distance = self._fast_edit_distance(word, query_lower)
                        max_allowed = max(1, query_len // 4)  # More lenient for longer queries
                        if distance <= max_allowed:
                            return True

            return False

        def _fast_edit_distance(self, s1: str, s2: str) -> int:
            """Fast edit distance calculation with optimizations for fuzzy search.
            Returns early if distance exceeds reasonable threshold.
            """
            len1, len2 = len(s1), len(s2)

            # Ensure s1 is the shorter string
            if len1 > len2:
                s1, s2 = s2, s1
                len1, len2 = len2, len1

            # Early exit for very different lengths
            if len2 - len1 > 2:
                return len2 - len1

            # Use a simple approach for short strings
            if len1 <= 3:
                return sum(c1 != c2 for c1, c2 in zip(s1, s2)) + abs(len1 - len2)

            # Dynamic programming with space optimization
            prev_row = list(range(len1 + 1))
            for i, c2 in enumerate(s2):
                curr_row = [i + 1]
                min_val = i + 1

                for j, c1 in enumerate(s1):
                    cost = 0 if c1 == c2 else 1
                    curr_row.append(
                        min(
                            prev_row[j + 1] + 1,  # deletion
                            curr_row[j] + 1,  # insertion
                            prev_row[j] + cost,  # substitution
                        ),
                    )
                    min_val = min(min_val, curr_row[-1])

                # Early exit if minimum possible distance is too high
                if min_val > 2:
                    return min_val

                prev_row = curr_row

            return prev_row[-1]

        def filter_tables(self, tables: List[TableInfo], query: str) -> List[TableInfo]:
            """Filter tables using fast trie-based search with progressive enhancement."""
            if not query:
                return tables

            query = query.strip()
            if not query:
                return tables

            results = []

            # Phase 1: Fast trie-based exact/prefix matches
            try:
                trie_matches = self.search_index.search_tables(query)
                # Filter to only include tables that are in our current tables list
                table_keys = {f"{t.schema}.{t.name}" for t in tables}
                results.extend([t for t in trie_matches if f"{t.schema}.{t.name}" in table_keys])
            except Exception:
                pass  # Continue to fallback

            # Phase 2: Add fuzzy matches for better coverage (only if query is substantial)
            if len(query) >= 2:
                try:
                    fuzzy_matches = self._filter_tables_fallback(tables, query)
                    # Add fuzzy matches that aren't already in results
                    existing_keys = {f"{t.schema}.{t.name}" for t in results}
                    for table in fuzzy_matches:
                        table_key = f"{table.schema}.{table.name}"
                        if table_key not in existing_keys:
                            results.append(table)
                            existing_keys.add(table_key)
                except Exception:
                    pass

            return results

        def _filter_tables_fallback(self, tables: List[TableInfo], query: str) -> List[TableInfo]:
            """Fallback table filtering using fuzzy search."""
            if not query:
                return tables

            query_lower = query.lower()
            filtered = []

            # Use pre-computed search data for faster matching
            for table in tables:
                table_key = f"{table.schema}.{table.name}"
                search_text = self._table_search_data.get(table_key, "")

                # Fast substring check first (most common case)
                if (
                    query_lower in search_text
                    or self.fuzzy_match(table.name, query)
                    or self.fuzzy_match(table.remarks or "", query)
                ):
                    filtered.append(table)

            return filtered

        def filter_columns(self, columns: List[ColumnInfo], query: str) -> List[ColumnInfo]:
            """Filter columns using fast trie-based search with progressive enhancement."""
            if not query:
                return columns

            query = query.strip()
            if not query:
                return columns

            results = []

            # Phase 1: Fast trie-based exact/prefix matches
            try:
                trie_matches = self.search_index.search_columns(query)
                # Filter to only include columns that are in our current columns list
                column_keys = {f"{c.schema}.{c.table}.{c.name}" for c in columns}
                results.extend([c for c in trie_matches if f"{c.schema}.{c.table}.{c.name}" in column_keys])
            except Exception:
                pass  # Continue to fallback

            # Phase 2: Add fuzzy matches for better coverage (only if query is substantial)
            if len(query) >= 2:
                try:
                    fuzzy_matches = self._filter_columns_fallback(columns, query)
                    # Add fuzzy matches that aren't already in results
                    existing_keys = {f"{c.schema}.{c.table}.{c.name}" for c in results}
                    for col in fuzzy_matches:
                        col_key = f"{col.schema}.{col.table}.{col.name}"
                        if col_key not in existing_keys:
                            results.append(col)
                            existing_keys.add(col_key)
                except Exception:
                    pass

            return results

        def _filter_columns_fallback(self, columns: List[ColumnInfo], query: str) -> List[ColumnInfo]:
            """Fallback column filtering using fuzzy search."""
            if not query:
                return columns

            query_lower = query.lower()
            filtered = []

            # Use pre-computed search data for faster matching
            for col in columns:
                col_key = f"{col.schema}.{col.table}.{col.name}"
                search_text = self._column_search_data.get(col_key, "")

                # Fast substring check first (most common case)
                if (
                    query_lower in search_text
                    or self.fuzzy_match(col.name, query)
                    or self.fuzzy_match(col.typename, query)
                ):
                    filtered.append(col)

            return filtered

        @on(Input.Changed, "#search-input")
        def on_search_changed(self, event: Input.Changed) -> None:
            """Handle search input changes with streaming results."""
            self.search_query = event.value

            # Cancel any pending search update
            if hasattr(self, "_search_update_task") and self._search_update_task:
                try:
                    self._search_update_task.cancel()
                except Exception:
                    pass

            # Cancel any background loading for previous search
            if hasattr(self, "_background_load_task") and self._background_load_task:
                try:
                    self._background_load_task.cancel()
                    self._background_load_task = None
                except Exception:
                    pass

            # Cancel current streaming task
            if hasattr(self, "_current_stream_task") and self._current_stream_task:
                try:
                    self._current_stream_task.cancel()
                    self._current_stream_task = None
                except Exception:
                    pass

            # Reset scroll loading state
            if not hasattr(self, "_scroll_load_triggered"):
                self._scroll_load_triggered = False
            self._scroll_load_triggered = False

            # Start streaming search immediately (no debounce for streaming)
            if self._stream_search_enabled and self.search_query:
                self._current_stream_task = asyncio.create_task(self._stream_search_results())
            else:
                # Fall back to debounced search for non-streaming mode
                self._search_update_task = asyncio.create_task(self._debounced_search_update())

        def _check_scroll_loading(self) -> None:
            """Check if we should trigger scroll-based loading."""
            if not self.search_query or self.all_tables_loaded:
                return

            try:
                tables_table = self.query_one("#tables-table", DataTable)
                if tables_table.row_count == 0:
                    return

                # Check if cursor is near the end (last 3 rows)
                cursor_near_end = tables_table.cursor_row >= tables_table.row_count - 3

                # Check if we have more results available
                has_more_available = (
                    hasattr(self, "_total_available_results")
                    and hasattr(self, "_current_displayed_count")
                    and self._total_available_results > self._current_displayed_count
                )

                # Trigger loading if cursor is near end and more data available
                if (
                    cursor_near_end
                    and has_more_available
                    and not getattr(self, "_scroll_load_triggered", False)
                    and not hasattr(self, "_background_load_task")
                ) or (
                    hasattr(self, "_background_load_task")
                    and (self._background_load_task is None or self._background_load_task.done())
                ):
                    self._scroll_load_triggered = True
                    self._background_load_task = asyncio.create_task(self._load_more_for_scroll(self.search_query))

            except Exception:
                pass  # Ignore errors in scroll checking

        @on(DataTable.CellSelected, "#tables-table")
        def on_table_cursor_changed(self, event: DataTable.CellSelected) -> None:
            """Handle table cursor movement for scroll loading."""
            self._check_scroll_loading()

        async def _debounced_search_update(self) -> None:
            """Debounced search update to avoid excessive UI updates."""
            try:
                await asyncio.sleep(self.search_debounce_delay)
                self._apply_search_update()
            except asyncio.CancelledError:
                # Search was cancelled, exit gracefully
                pass
            except Exception as e:
                # Log error but don't crash
                self.notify(f"Search error: {e}", severity="error", timeout=3)

        async def _load_more_for_search(self, search_query: str, current_result_count: int) -> None:
            """Load additional data in background to find more search results."""
            try:
                # Load more tables in chunks
                load_chunk_size = 200  # Load 200 more tables at a time
                tables_loaded = 0

                while (
                    not self.all_tables_loaded
                    and tables_loaded < 1000  # Don't load too much at once
                    and search_query == self.search_query
                ):  # Search query hasn't changed
                    # Load more data
                    loaded = await self.load_more_tables(load_chunk_size)
                    if not loaded:
                        break  # No more data to load

                    tables_loaded += load_chunk_size

                    # Re-run search with the new data
                    if self.search_mode == "tables":
                        filtered_tables = self.filter_tables(self.tables, search_query)
                        new_result_count = len(filtered_tables)

                        # If we found significantly more results, update the display
                        if new_result_count > current_result_count + 10:  # Found at least 10 more results
                            # Update the cache with new results
                            self._set_cached("tables", search_query, {"filtered_tables": filtered_tables})
                            # Update display
                            self._apply_search_update()
                            break  # Stop loading for now

                    elif self.search_mode == "columns":
                        # For column search, we need to rebuild the column matches
                        matching_table_counts = {}
                        matching_columns = []
                        q = search_query
                        for col in self.columns:
                            if self.column_matches_query(col, q):
                                t_key = f"{col.schema}.{col.table}"
                                matching_table_counts[t_key] = matching_table_counts.get(t_key, 0) + 1
                                matching_columns.append(col)

                        # Cache the updated results
                        self._set_cached(
                            "columns",
                            search_query,
                            {
                                "matching_table_counts": matching_table_counts,
                                "matching_columns": matching_columns,
                            },
                        )

                        # Update display if we found more results
                        if len(matching_columns) > current_result_count + 10:
                            self._apply_search_update()
                            break

                    # Small delay to prevent overwhelming the system
                    await asyncio.sleep(0.1)

            except Exception as e:
                # Log error but don't crash the background task
                print(f"Background search loading error: {e}")
            finally:
                # Clear the background task reference
                self._background_load_task = None

        async def _load_all_for_small_search(self, search_query: str) -> None:
            """Load all available data for small search result sets."""
            try:
                # Keep loading until all data is loaded or search changes
                while not self.all_tables_loaded and search_query == self.search_query:
                    loaded = await self.load_more_tables(500)  # Load in larger chunks
                    if not loaded:
                        break

                    # Re-run search with all the new data
                    if self.search_mode == "tables":
                        filtered_tables = self.filter_tables(self.tables, search_query)
                        # Update cache with complete results
                        self._set_cached("tables", search_query, {"filtered_tables": filtered_tables})
                        # Update display
                        self._apply_search_update()

                    elif self.search_mode == "columns":
                        # Rebuild column matches with all data
                        matching_table_counts = {}
                        matching_columns = []
                        q = search_query
                        for col in self.columns:
                            if self.column_matches_query(col, q):
                                t_key = f"{col.schema}.{col.table}"
                                matching_table_counts[t_key] = matching_table_counts.get(t_key, 0) + 1
                                matching_columns.append(col)

                        # Update cache
                        self._set_cached(
                            "columns",
                            search_query,
                            {
                                "matching_table_counts": matching_table_counts,
                                "matching_columns": matching_columns,
                            },
                        )
                        # Update display
                        self._apply_search_update()

            except Exception as e:
                print(f"Background complete loading error: {e}")
            finally:
                self._background_load_task = None

        async def _load_more_for_scroll(self, search_query: str) -> None:
            """Load more data triggered by scrolling to the end."""
            try:
                # Load one chunk of data
                loaded = await self.load_more_tables(100)  # Smaller chunks for scroll loading
                if loaded and search_query == self.search_query:
                    # Update the search results with new data
                    if self.search_mode == "tables":
                        filtered_tables = self.filter_tables(self.tables, search_query)
                        self._set_cached("tables", search_query, {"filtered_tables": filtered_tables})
                        self._apply_search_update()

                    elif self.search_mode == "columns":
                        matching_table_counts = {}
                        matching_columns = []
                        q = search_query
                        for col in self.columns:
                            if self.column_matches_query(col, q):
                                t_key = f"{col.schema}.{col.table}"
                                matching_table_counts[t_key] = matching_table_counts.get(t_key, 0) + 1
                                matching_columns.append(col)

                        self._set_cached(
                            "columns",
                            search_query,
                            {
                                "matching_table_counts": matching_table_counts,
                                "matching_columns": matching_columns,
                            },
                        )
                        self._apply_search_update()

            except Exception as e:
                print(f"Scroll loading error: {e}")
            finally:
                self._background_load_task = None
                self._scroll_load_triggered = False

        @on(DataTable.RowSelected, "#tables-table")
        def on_table_selected(self, event: DataTable.RowSelected) -> None:
            """Handle table selection."""
            if event.row_key:
                # Clear prior column selection when a table is directly selected
                self.selected_column_key = None
                self.update_columns_display(event.row_key.value)

        @on(DataTable.RowSelected, "#columns-table")
        def on_column_selected(self, event: DataTable.RowSelected) -> None:
            """When a column is selected, switch to the table containing it and
            highlight the clicked column.
            """
            try:
                if event.row_key:
                    col_key = event.row_key.value  # e.g. DACDATA.CUSTOMERS.CUST_ID
                    parts = col_key.split(".")
                    if len(parts) >= 3:
                        table_key = f"{parts[0]}.{parts[1]}"
                        # Remember selected column so we can highlight it after re-render
                        self.selected_column_key = col_key

                        # Find and set the TableInfo as selected
                        for t in self.tables:
                            if f"{t.schema}.{t.name}" == table_key:
                                self.selected_table = t
                                break

                        # Update displays to focus the table and then the column
                        self.update_tables_display()
                        self.update_columns_display(table_key)
            except Exception:
                pass

        @on(DataTable.RowHighlighted, "#tables-table")
        def on_table_highlighted(self, event: DataTable.RowHighlighted) -> None:
            """Handle table highlighting (keyboard navigation or mouse hover)."""
            if event.row_key:
                table_key = event.row_key.value
                self.update_columns_display(table_key)
                # Show IBM i path for the highlighted table
                try:
                    # Find the TableInfo (path display removed)
                    for t in self.tables:
                        if f"{t.schema}.{t.name}" == table_key:
                            break
                except Exception:
                    pass

        @on(Button.Pressed, "#search-mode-label")
        def on_search_mode_button_pressed(self) -> None:
            """Handle search mode button click."""
            self.action_toggle_search_mode()

        def action_focus_search(self) -> None:
            """Focus the search input."""
            self.query_one("#search-input", Input).focus()

        def action_clear_search(self) -> None:
            """Clear the search."""
            search_input = self.query_one("#search-input", Input)
            search_input.value = ""
            search_input.focus()

        def action_toggle_search_mode(self) -> None:
            """Toggle between table search and column search modes."""
            # Remember current table selection before switching
            current_table_key = None
            try:
                tables_table = self.query_one("#tables-table", DataTable)
                if tables_table.cursor_row >= 0:
                    row = tables_table.get_row_at(tables_table.cursor_row)
                    if row:
                        # Get the row key which is schema.table
                        current_table_key = list(tables_table.rows.keys())[tables_table.cursor_row]
            except Exception:
                pass

            if self.search_mode == "tables":
                self.search_mode = "columns"
                mode_button = self.query_one("#search-mode-label", Button)
                mode_button.label = "🔍 Search Columns"
                search_input = self.query_one("#search-input", Input)
                search_input.placeholder = "Type to search columns by name, type, or description..."
                self.notify(
                    "🔍 COLUMN SEARCH MODE: Find tables with matching columns (H: show/hide non-matching)",
                    severity="information",
                    timeout=4,
                )
            else:
                self.search_mode = "tables"
                mode_button = self.query_one("#search-mode-label", Button)
                mode_button.label = "📋 Search Tables"
                search_input = self.query_one("#search-input", Input)
                search_input.placeholder = "Type to search tables by name or description..."
                self.notify("📋 TABLE SEARCH MODE: Filter by table name/description", severity="information", timeout=4)

            # Clear UI cache and reset display when switching modes to prevent stale data and key conflicts
            self._clear_ui_cache()

            # Clear the tables display to ensure clean state
            try:
                tables_table = self.query_one("#tables-table", DataTable)
                tables_table.clear()
                columns_table = self.query_one("#columns-table", DataTable)
                columns_table.clear()
            except Exception:
                pass  # UI might not be ready yet

            # Re-run search with new mode (force update even with empty query)
            self._apply_search_update()

            # Restore table selection and update columns display
            if current_table_key:
                try:
                    tables_table = self.query_one("#tables-table", DataTable)
                    # Find the row with matching key
                    for idx, key in enumerate(tables_table.rows.keys()):
                        if key == current_table_key:
                            tables_table.cursor_row = idx
                            # Update columns display for the selected table
                            self.update_columns_display(str(current_table_key))
                            break
                except Exception:
                    pass

        def action_open_settings(self) -> None:
            """Open the settings dialog."""

            def handle_settings_result(new_schema: Optional[str]) -> None:
                """Handle the result from settings dialog."""
                if new_schema is not None:
                    # Schema was changed
                    old_schema = self.schema_filter
                    self.schema_filter = new_schema

                    # Show notification about schema change
                    if new_schema:
                        self.notify(f"Schema filter changed to: {new_schema}", severity="information", timeout=3)
                    else:
                        self.notify("Schema filter cleared - searching all schemas", severity="information", timeout=3)

                    # Only reload if schema actually changed
                    if old_schema != new_schema:
                        self.notify("Reloading data with new schema filter...", timeout=2)
                        self.run_worker(self.reload_data, exclusive=True)

            self.push_screen(SettingsScreen(self.schema_filter, self.use_mock), handle_settings_result)

        async def reload_data(self) -> None:
            """Reload data with new settings."""
            try:
                # Verify schema exists before loading - helpful if DACDATA is missing
                if self.schema_filter:
                    if not await schema_exists_async(self.schema_filter, self.use_mock):
                        self.notify(
                            f"Schema '{self.schema_filter}' not found in current database. Try settings (S) to select a different schema.",
                            severity="warning",
                            timeout=6,
                        )
                        # Clear existing data and return
                        self.tables, self.columns = [], []
                        self.update_tables_display()
                        return
                # Update title to reflect new schema
                if self.schema_filter:
                    self.title = f"DB Browser [S782c451] - Schema: {self.schema_filter}"
                    self.sub_title = "Press 'S' to change schema"
                else:
                    self.title = "DB Browser [S782c451] - All Schemas"
                    self.sub_title = "Press 'S' to filter by schema"

                # Clear existing data
                self.tables = []
                self.columns = []
                self.table_columns = {}
                self._table_search_data = {}
                self._column_search_data = {}

                # Clear displays
                tables_table = self.query_one("#tables-table", DataTable)
                tables_table.clear()
                columns_table = self.query_one("#columns-table", DataTable)
                columns_table.clear()

                # Reload data using async version to avoid blocking
                self.tables, self.columns = await get_all_tables_and_columns_async(
                    self.schema_filter,
                    self.use_mock,
                    self.use_cache,
                )

                # Rebuild table-columns mapping and pre-computed search data
                for table in self.tables:
                    table_key = f"{table.schema}.{table.name}"
                    # Pre-compute lowercase searchable text for each table
                    search_text = f"{table.name} {table.schema} {table.remarks or ''}".lower()
                    self._table_search_data[table_key] = search_text

                for col in self.columns:
                    if col.schema and col.table:
                        table_key = f"{col.schema}.{col.table}"
                        if table_key not in self.table_columns:
                            self.table_columns[table_key] = []
                        self.table_columns[table_key].append(col)

                        # Pre-compute lowercase searchable text for each column
                        col_key = f"{col.schema}.{col.table}.{col.name}"
                        search_text = f"{col.name} {col.typename} {col.remarks or ''}".lower()
                        self._column_search_data[col_key] = search_text

                # Update display
                self.update_tables_display()
                # Invalidate search cache after reload
                self._clear_search_cache()

                # Show result message
                table_count = len(self.tables)
                if table_count == 0:
                    if self.schema_filter:
                        self.notify(
                            f"⚠️ No tables found in schema '{self.schema_filter}'",
                            severity="warning",
                            timeout=5,
                        )
                    else:
                        self.notify("⚠️ No tables found", severity="warning", timeout=5)
                elif self.schema_filter:
                    self.notify(
                        f"✓ Loaded {table_count} tables from '{self.schema_filter}'",
                        severity="information",
                        timeout=2,
                    )
                else:
                    self.notify(
                        f"✓ Loaded {table_count} tables from all schemas",
                        severity="information",
                        timeout=2,
                    )
            except Exception as e:
                self.notify(f"Error reloading data: {e!s}", severity="error", timeout=5)

        def action_help(self) -> None:
            """Show help information."""
            help_text = (
                "Navigation: ↑↓/mouse | Search: type | Tab: toggle mode | S: settings | /: focus | Esc: clear | Q: quit"
            )
            help_text += " | Scroll to bottom: load more results"
            if not self.all_tables_loaded:
                help_text += " | L: load more tables"
            help_text += " | Ctrl+L: show all current results"
            if self.search_mode == "columns":
                help_text += " | H: show/hide non-matching tables"
            if self._stream_search_enabled:
                help_text += " | X: toggle streaming search"
            self.notify(help_text, timeout=5)

        def action_copy_table_path(self) -> None:
            """Copy the currently highlighted table's IBM i path to clipboard."""
            # Path copying was removed; show help about keybindings instead
            self.notify("Copy Table Path is not available in this build", severity="warning", timeout=3)

        def _show_load_more_binding(self) -> bool:
            """Show the load more binding only when there are more tables to load."""
            return not self.all_tables_loaded

        def action_load_more(self) -> None:
            """Load more tables from the database."""
            if self.all_tables_loaded:
                self.notify("All tables already loaded", timeout=2)
                return

            self.notify("Loading more tables...", timeout=1)
            self.run_worker(self.load_more_tables, exclusive=True)

        def action_load_all_results(self) -> None:
            """Temporarily increase the display limit to show all current results."""
            if (
                hasattr(self, "_background_load_task")
                and self._background_load_task
                and not self._background_load_task.done()
            ):
                self.notify("Background loading already in progress", timeout=2)
                return

            old_limit = self.max_displayed_results
            self.max_displayed_results = max(len(self.tables), len(self.columns)) + 100  # Show all current results
            self._invalidate_all_caches()  # Force UI refresh
            self.update_tables_display()
            self.notify(f"Showing all {len(self.tables)} tables and {len(self.columns)} columns", timeout=3)

            # Reset limit after a delay
            async def reset_limit():
                await asyncio.sleep(30)  # Reset after 30 seconds
                self.max_displayed_results = old_limit
                self._invalidate_all_caches()
                self.update_tables_display()

            asyncio.create_task(reset_limit())

        def action_toggle_stream_search(self) -> None:
            """Toggle streaming search results on/off."""
            self._stream_search_enabled = not self._stream_search_enabled

            # Cancel current streaming task if active
            if hasattr(self, "_current_stream_task") and self._current_stream_task:
                try:
                    self._current_stream_task.cancel()
                    self._current_stream_task = None
                except Exception:
                    pass

            # Clear streamed results
            self._streamed_results = []

            # Show notification
            if self._stream_search_enabled:
                self.notify("🔄 Streaming search ENABLED - Results appear as found", severity="information", timeout=3)
            else:
                self.notify("⏸️ Streaming search DISABLED - Using batch search", severity="information", timeout=3)

            # Re-run search with new mode if there's a query
            if self.search_query:
                if self._stream_search_enabled:
                    self._current_stream_task = asyncio.create_task(self._stream_search_results())
                else:
                    self._search_update_task = asyncio.create_task(self._debounced_search_update())

        def get_bindings(self) -> list[Binding]:
            """Override to dynamically show/hide the load more binding."""
            bindings = super().get_bindings()
            # Filter out the load_more binding if all tables are loaded
            if self.all_tables_loaded:
                bindings = [b for b in bindings if b.key != "l"]
            return bindings


def search_and_output(query, schema_filter=None, limit=10, output_format="table", use_mock=False):
    """Perform a search and output results directly without TUI."""
    # For one-shot search, load all data (no lazy loading)
    tables, columns = get_all_tables_and_columns(schema_filter, use_mock)

    # Simple filtering for demo
    filtered_tables = [
        t for t in tables if query.lower() in t.name.lower() or query.lower() in (t.remarks or "").lower()
    ]
    filtered_columns = [
        c for c in columns if query.lower() in c.name.lower() or query.lower() in (c.remarks or "").lower()
    ]

    # Take top N results
    top_tables = filtered_tables[:limit]
    top_columns = filtered_columns[:limit]

    if output_format == "json":
        result = {
            "query": query,
            "tables": [{"schema": t.schema, "name": t.name, "remarks": t.remarks} for t in top_tables],
            "columns": [
                {"schema": c.schema, "table": c.table, "name": c.name, "typename": c.typename, "remarks": c.remarks}
                for c in top_columns
            ],
        }
        print(json.dumps(result, indent=2))
    elif output_format == "table":
        print(f"Tables matching '{query}':")
        print("-" * 80)
        for table in top_tables:
            print(f"{table.schema}.{table.name:<30} {table.remarks or '(no description)'}")

        print(f"\nColumns matching '{query}':")
        print("-" * 80)
        for col in top_columns:
            print(f"{col.schema}.{col.table}.{col.name:<40} [{col.typename}] {col.remarks or '(no description)'}")
    elif output_format == "csv":
        print("type,schema,table,column,typename,remarks")
        for table in top_tables:
            remarks = (table.remarks or "").replace('"', '""')
            print(f'table,"{table.schema}","{table.name}","","","{remarks}"')
        for col in top_columns:
            remarks = (col.remarks or "").replace('"', '""')
            print(f'column,"{col.schema}","{col.table}","{col.name}","{col.typename}","{remarks}"')


def main():
    parser = argparse.ArgumentParser(description="Interactive DB2 Schema Browser TUI")
    parser.add_argument("--schema", help="Filter by specific schema (default: DACDATA)", default="DACDATA")
    parser.add_argument("--search", "-s", help="Search query (activates one-shot mode)")
    parser.add_argument(
        "--limit",
        "-l",
        type=int,
        default=10,
        help="Limit number of results in one-shot mode (default: 10)",
    )
    parser.add_argument(
        "--format",
        choices=["table", "json", "csv"],
        default="table",
        help="Output format for one-shot mode (default: table)",
    )
    parser.add_argument("--mock", action="store_true", help="Use mock data for testing")
    parser.add_argument("--install-deps", action="store_true", help="Show required dependencies")
    parser.add_argument("--basic", action="store_true", help="Use basic mode (no Textual TUI)")
    parser.add_argument("--no-cache", action="store_true", help="Disable caching of database schema")
    parser.add_argument(
        "--initial-load-limit",
        type=int,
        default=100,
        help="Initial number of tables to load (default: 100)",
    )
    parser.add_argument(
        "--max-display-results",
        type=int,
        default=200,
        help="Maximum results to display in UI (default: 200)",
    )
    parser.add_argument(
        "--search-debounce",
        type=float,
        default=0.2,
        help="Search debounce delay in seconds (default: 0.2)",
    )
    parser.add_argument(
        "--stream-search",
        action="store_true",
        default=True,
        help="Enable streaming search results (default: enabled)",
    )
    parser.add_argument("--no-stream-search", action="store_true", help="Disable streaming search results")

    args = parser.parse_args()

    if args.install_deps:
        print("This tool can use multiple TUI libraries:")
        print("- Rich (basic display): pip install rich")
        print("- Textual (full TUI with mouse/keyboard): pip install textual")
        print("\nRecommended: pip install rich textual")
        return

    # If search is provided, run in one-shot mode
    if args.search:
        if not RICH_AVAILABLE:
            print("Error: Search output requires the 'rich' library.")
            print("Please install it with: pip install rich")
            return
        search_and_output(args.search, args.schema, args.limit, args.format, args.mock)
    # Interactive mode - prefer Textual if available
    elif TEXTUAL_AVAILABLE and not args.basic:
        # Configure streaming search
        stream_enabled = args.stream_search and not args.no_stream_search

        app = DBBrowserApp(
            schema_filter=args.schema,
            use_mock=args.mock,
            use_cache=not args.no_cache,
            initial_load_limit=args.initial_load_limit,
        )
        # Configure performance settings
        app.max_displayed_results = args.max_display_results
        app.search_debounce_delay = args.search_debounce
        app._stream_search_enabled = stream_enabled
        app.run()
    elif RICH_AVAILABLE:
        if not TEXTUAL_AVAILABLE:
            print("[Note: For full keyboard/mouse support, install Textual: pip install textual]")
            print()
        browser = DBBrowserTUI(
            schema_filter=args.schema,
            use_mock=args.mock,
            initial_load_limit=args.initial_load_limit,
        )
        browser.run()
    else:
        print("Error: This tool requires either 'rich' or 'textual' library.")
        print("Please install with: pip install rich textual")
        return


if __name__ == "__main__":
    # Check if we should use smart launcher
    if len(sys.argv) == 1 or (len(sys.argv) > 1 and not sys.argv[1].startswith("-")):
        # Use smart launcher for default behavior
        from .main_launcher import main as smart_launcher

        smart_launcher()
    else:
        # Use direct main for specific arguments or legacy behavior
        main()
