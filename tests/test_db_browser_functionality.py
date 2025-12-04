"""Unit tests for dbutils.db_browser module.

Tests for core functionality including:
- Data structures (TableInfo, ColumnInfo) 
- Search index and trie functionality
- Database schema loading functions
- Fuzzy matching algorithms
- Mock data generation
"""

import pytest
from unittest.mock import patch, MagicMock, mock_open
import json
import pickle
import gzip
from pathlib import Path

from dbutils.db_browser import (
    TableInfo,
    ColumnInfo,
    TrieNode,
    SearchIndex,
    get_all_tables_and_columns,
    get_all_tables_and_columns_async,
    mock_get_tables,
    mock_get_columns,
    query_runner,
    intern_string,
    humanize_schema_name,
    schema_exists,
    schema_exists_async,
    get_available_schemas,
    get_available_schemas_async,
    get_cache_key,
    load_from_cache,
    save_to_cache,
)
from dbutils.utils import (
    fuzzy_match,
    edit_distance,
)
from dbutils.gui.qt_app import (
    highlight_text_as_html,
)


class TestTableInfo:
    """Test the TableInfo dataclass."""

    def test_table_info_creation(self):
        """Test basic TableInfo creation and initialization."""
        table = TableInfo(
            schema="TEST", 
            name="USERS", 
            remarks="User information table"
        )
        assert table.schema == "TEST"
        assert table.name == "USERS"
        assert table.remarks == "User information table"

    def test_string_interning(self):
        """Test that strings are properly interned."""
        table = TableInfo(
            schema="TEST", 
            name="USERS", 
            remarks="User information table"
        )
        
        # Check that interned strings are the same object
        assert table.schema is intern_string("TEST")
        assert table.name is intern_string("USERS")
        assert table.remarks is intern_string("User information table")


class TestColumnInfo:
    """Test the ColumnInfo dataclass."""

    def test_column_info_creation(self):
        """Test basic ColumnInfo creation and initialization."""
        column = ColumnInfo(
            schema="TEST",
            table="USERS",
            name="ID",
            typename="INTEGER",
            length=10,
            scale=0,
            nulls="N",
            remarks="User identifier"
        )
        assert column.schema == "TEST"
        assert column.table == "USERS"
        assert column.name == "ID"
        assert column.typename == "INTEGER"
        assert column.length == 10
        assert column.scale == 0
        assert column.nulls == "N"
        assert column.remarks == "User identifier"

    def test_string_interning(self):
        """Test that strings are properly interned."""
        column = ColumnInfo(
            schema="TEST",
            table="USERS",
            name="ID",
            typename="INTEGER",
            length=10,
            scale=0,
            nulls="N",
            remarks="User identifier"
        )
        
        # Check that interned strings are the same object
        assert column.schema is intern_string("TEST")
        assert column.table is intern_string("USERS")
        assert column.name is intern_string("ID")
        assert column.typename is intern_string("INTEGER")
        assert column.nulls is intern_string("N")
        assert column.remarks is intern_string("User identifier")


class TestTrieNode:
    """Test the TrieNode functionality."""

    def test_basic_insert_and_search(self):
        """Test basic insert and search functionality."""
        trie = TrieNode()
        trie.insert("test", "item1")
        trie.insert("testing", "item2")
        
        matches = trie.search_prefix("test")
        assert "item1" in matches
        assert "item2" in matches
        
        matches = trie.search_prefix("tes")
        assert len(matches) >= 1  # Should contain at least "test"
    
    def test_case_insensitive_search(self):
        """Test that search is case insensitive."""
        trie = TrieNode()
        trie.insert("Test", "item1")
        
        matches = trie.search_prefix("test")
        assert "item1" in matches
        
        matches = trie.search_prefix("TEST")
        assert "item1" in matches
    
    def test_no_matches(self):
        """Test search for non-existent prefix."""
        trie = TrieNode()
        trie.insert("test", "item1")
        
        matches = trie.search_prefix("xyz")
        assert len(matches) == 0


class TestSearchIndex:
    """Test the SearchIndex functionality."""

    def test_build_index(self):
        """Test building search index from tables and columns."""
        from dbutils.db_browser import TableInfo, ColumnInfo
        
        tables = [
            TableInfo(schema="TEST", name="USERS", remarks="User table"),
            TableInfo(schema="TEST", name="ORDERS", remarks="Order table"),
        ]
        columns = [
            ColumnInfo(
                schema="TEST",
                table="USERS",
                name="ID",
                typename="INTEGER",
                length=10,
                scale=0,
                nulls="N",
                remarks="User identifier"
            ),
            ColumnInfo(
                schema="TEST",
                table="USERS",
                name="NAME",
                typename="VARCHAR",
                length=100,
                scale=0,
                nulls="N",
                remarks="User name"
            ),
        ]
        
        index = SearchIndex()
        index.build_index(tables, columns)
        
        # Test table search
        table_results = index.search_tables("user")
        assert len(table_results) == 1
        assert table_results[0].name == "USERS"
        
        # Test column search
        column_results = index.search_columns("name")
        assert len(column_results) == 1
        assert column_results[0].name == "NAME"
    
    def test_search_empty_query(self):
        """Test searching with empty query returns all items."""
        from dbutils.db_browser import TableInfo, ColumnInfo
        
        tables = [TableInfo(schema="TEST", name="USERS", remarks="User table")]
        columns = [
            ColumnInfo(
                schema="TEST",
                table="USERS",
                name="ID",
                typename="INTEGER",
                length=10,
                scale=0,
                nulls="N",
                remarks="User identifier"
            ),
        ]
        
        index = SearchIndex()
        index.build_index(tables, columns)
        
        assert len(index.search_tables("")) == 1
        assert len(index.search_columns("")) == 1


class TestQueryRunner:
    """Test the query_runner function."""

    @patch.dict('os.environ', {'DBUTILS_JDBC_PROVIDER': 'test_provider'})
    def test_query_runner_with_jdbc(self):
        """Test query runner with JDBC provider."""
        # Create all mocks inline to ensure proper chain
        # The JDBCConnection object has a query method, not execute on cursor
        mock_conn = MagicMock()
        expected_result = [{'col1': 'value1', 'col2': 'value2'}]
        mock_conn.query.return_value = expected_result

        with patch('dbutils.jdbc_provider.connect', return_value=mock_conn) as mock_connect:
            result = query_runner("SELECT * FROM TEST")

            # Verify connection was established and query executed
            mock_connect.assert_called_once()
            mock_conn.query.assert_called_once_with("SELECT * FROM TEST")
            assert result == expected_result
    
    def test_query_runner_no_provider(self):
        """Test query runner without provider raises error."""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(RuntimeError, match="DBUTILS_JDBC_PROVIDER"):
                query_runner("SELECT * FROM TEST")


class TestMockData:
    """Test the mock data functions."""

    def test_mock_get_tables(self):
        """Test mock_get_tables returns expected data."""
        tables = mock_get_tables()
        assert len(tables) > 0
        assert all(isinstance(t, TableInfo) for t in tables)
        assert any(t.name == "USERS" for t in tables)

    def test_mock_get_columns(self):
        """Test mock_get_columns returns expected data."""
        columns = mock_get_columns()
        assert len(columns) > 0
        assert all(isinstance(c, ColumnInfo) for c in columns)
        assert any(c.name == "ID" for c in columns)


class TestFuzzyMatch:
    """Test the fuzzy matching functions."""

    def test_fuzzy_match_exact(self):
        """Test exact matches work."""
        assert fuzzy_match("hello", "hello") is True
        assert fuzzy_match("hello", "HELLO") is True

    def test_fuzzy_match_substring(self):
        """Test substring matches work."""
        assert fuzzy_match("hello world", "hello") is True
        assert fuzzy_match("hello world", "world") is True

    def test_fuzzy_match_word_boundaries(self):
        """Test word boundary matching."""
        assert fuzzy_match("user_name", "name") is True
        assert fuzzy_match("customer_order", "cus") is True
        assert fuzzy_match("testTable", "test") is True

    def test_fuzzy_match_no_match(self):
        """Test non-matches return False."""
        assert fuzzy_match("hello", "xyz") is False
        assert fuzzy_match("", "hello") is False
        assert fuzzy_match("hello", "") is True  # Empty query should match anything


class TestEditDistance:
    """Test the edit distance function."""

    def test_edit_distance_identical(self):
        """Test identical strings have distance 0."""
        assert edit_distance("hello", "hello") == 0

    def test_edit_distance_single_char_diff(self):
        """Test single character difference."""
        assert edit_distance("hello", "hallo") == 1

    def test_edit_distance_insertion_deletion(self):
        """Test insertion and deletion operations."""
        assert edit_distance("hello", "helo") == 1  # deletion
        assert edit_distance("hello", "helllo") == 1  # insertion
        assert edit_distance("hello", "jello") == 1  # substitution

    def test_edit_distance_symmetric(self):
        """Test that edit distance is symmetric."""
        assert edit_distance("abc", "def") == edit_distance("def", "abc")


class TestHighlightTextAsHtml:
    """Test the highlight text as HTML function."""

    def test_highlight_exact_match(self):
        """Test exact match highlighting."""
        result = highlight_text_as_html("hello world", "hello")
        assert "hello" in result
        assert "background-color:#fffb8f" in result

    def test_highlight_case_insensitive(self):
        """Test case-insensitive highlighting."""
        result = highlight_text_as_html("Hello World", "hello")
        assert "Hello" in result
        assert "background-color:#fffb8f" in result

    def test_highlight_multiple_words(self):
        """Test multiple word highlighting."""
        result = highlight_text_as_html("hello beautiful world", "hello world")
        assert "hello" in result
        assert "world" in result
        assert result.count("background-color:#fffb8f") >= 2

    def test_highlight_no_query(self):
        """Test no query returns original text."""
        result = highlight_text_as_html("hello world", "")
        assert result == "hello world"


class TestHumanizeSchemaName:
    """Test the humanize schema name function."""

    def test_humanize_basic(self):
        """Test basic schema name humanization."""
        assert humanize_schema_name("TEST_SCHEMA") == "TEST SCHEMA"
        assert humanize_schema_name("DACDATA") == "DACDATA"

    def test_humanize_with_underscores(self):
        """Test schema names with multiple underscores."""
        assert humanize_schema_name("TEST__SCHEMA") == "TEST SCHEMA"
        assert humanize_schema_name("MY_LONG_NAME") == "MY LONG NAME"

    def test_humanize_empty(self):
        """Test empty schema name."""
        assert humanize_schema_name("") == ""


class TestSchemaExists:
    """Test the schema exists functions."""

    def test_schema_exists_with_mock(self):
        """Test schema_exists with mock data."""
        # This function with use_mock=True should return True for DACDATA
        result = schema_exists("DACDATA", use_mock=True)
        assert result is True

        # And should return False for non-DACDATA schema
        result = schema_exists("NOT_DACDATA", use_mock=True)
        assert result is False

    def test_schema_exists_with_empty_mock(self):
        """Test schema_exists with mock for non-DACDATA schema."""
        # Should return False for non-DACDATA schema with mock
        assert schema_exists("NOT_DACDATA", use_mock=True) is False


class TestGetAvailableSchemas:
    """Test the get_available_schemas functions."""

    def test_get_available_schemas_mock(self):
        """Test getting available schemas with mock."""
        from dbutils.db_browser import SchemaInfo
        schemas = get_available_schemas(use_mock=True)
        
        assert len(schemas) > 0
        assert all(isinstance(s, SchemaInfo) for s in schemas)
        assert any(s.name == "DACDATA" for s in schemas)

    def test_get_available_schemas_async_mock(self):
        """Test getting available schemas async with mock."""
        import asyncio
        from dbutils.db_browser import SchemaInfo

        async def run_async():
            return await get_available_schemas_async(use_mock=True)

        schemas = asyncio.run(run_async())

        assert len(schemas) > 0
        assert all(isinstance(s, SchemaInfo) for s in schemas)
        assert any(s.name == "DACDATA" for s in schemas)


class TestCacheFunctions:
    """Test the caching functions."""

    def test_get_cache_key(self):
        """Test cache key generation."""
        assert get_cache_key("TEST") == "TEST"
        assert get_cache_key("TEST", 10) == "TEST_LIMIT10_OFFSET0"
        assert get_cache_key("TEST", 10, 5) == "TEST_LIMIT10_OFFSET5"
        assert get_cache_key(None) == "ALL_SCHEMAS"

    def test_cache_operations(self, tmp_path):
        """Test saving and loading from cache."""
        cache_dir = tmp_path / ".cache" / "dbutils"
        cache_dir.mkdir(parents=True)
        cache_file = cache_dir / "schema_cache.pkl.gz"
        
        # Mock data
        tables = [TableInfo(schema="TEST", name="USERS", remarks="Users")]
        columns = [
            ColumnInfo(
                schema="TEST",
                table="USERS",
                name="ID",
                typename="INTEGER",
                length=10,
                scale=0,
                nulls="N",
                remarks="ID"
            )
        ]
        
        with patch('dbutils.db_browser.CACHE_FILE', cache_file):
            # Save to cache
            save_to_cache("TEST", tables, columns)
            
            # Load from cache
            loaded = load_from_cache("TEST")
            
            if loaded:
                loaded_tables, loaded_columns = loaded
                assert len(loaded_tables) == 1
                assert len(loaded_columns) == 1
                assert loaded_tables[0].name == "USERS"


class TestGetAllTablesAndColumns:
    """Test the get_all_tables_and_columns functions."""

    def test_get_all_tables_and_columns_mock(self):
        """Test getting all tables and columns with mock data."""
        tables, columns = get_all_tables_and_columns(use_mock=True)
        
        assert len(tables) > 0
        assert len(columns) > 0
        assert all(isinstance(t, TableInfo) for t in tables)
        assert all(isinstance(c, ColumnInfo) for c in columns)

    def test_get_all_tables_and_columns_with_schema_filter(self):
        """Test filtering by schema."""
        tables, columns = get_all_tables_and_columns(use_mock=True, schema_filter="TEST")
        
        assert all(t.schema == "TEST" for t in tables)
        assert all(c.schema == "TEST" for c in columns)

    def test_get_all_tables_and_columns_async_mock(self):
        """Test async function with mock data."""
        import asyncio

        async def run_async():
            return await get_all_tables_and_columns_async(use_mock=True)

        tables, columns = asyncio.run(run_async())

        assert len(tables) > 0
        assert len(columns) > 0
        assert all(isinstance(t, TableInfo) for t in tables)
        assert all(isinstance(c, ColumnInfo) for c in columns)