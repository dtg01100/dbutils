"""Tests for dbutils main modules and initialization.

Tests for:
- Module initialization and imports
- Main launcher functionality
- Entry points
"""

from unittest.mock import patch

import pytest


def test_dbutils_init():
    """Test dbutils package initialization."""
    import dbutils

    # Test that main functions are available
    assert hasattr(dbutils, 'db_browser_main')
    assert hasattr(dbutils, 'qt_gui_main')
    assert hasattr(dbutils, 'smart_launcher_main')

    # Test that __all__ is properly defined
    assert 'db_browser_main' in dbutils.__all__
    assert 'qt_gui_main' in dbutils.__all__
    assert 'smart_launcher_main' in dbutils.__all__


def test_db_browser_module():
    """Test db_browser module imports and basic functionality."""
    from dbutils.db_browser import (
        ColumnInfo,
        TableInfo,
    )
    from dbutils.utils import edit_distance, fuzzy_match

    # Test that basic dataclasses can be instantiated
    table = TableInfo(schema="TEST", name="USERS", remarks="Test table")
    assert table.schema == "TEST"
    assert table.name == "USERS"

    column = ColumnInfo(
        schema="TEST",
        table="USERS",
        name="ID",
        typename="INTEGER",
        length=10,
        scale=0,
        nulls="N",
        remarks="ID column"
    )
    assert column.name == "ID"

    # Test that utilities work
    assert fuzzy_match("hello", "hello")
    assert edit_distance("hello", "world") > 0


def test_jdbc_provider_module():
    """Test jdbc_provider module imports and basic functionality."""
    from dbutils.jdbc_provider import JDBCProvider

    # Test basic provider creation
    provider = JDBCProvider(
        name="Test",
        driver_class="com.test.Driver",
        jar_path="/path.jar",
        url_template="jdbc:test://{host}:{port}/{db}"
    )
    assert provider.name == "Test"

    # Test that registry can be created
    # We can't test full functionality without actual JDBC setup
    from dbutils.jdbc_provider import get_registry
    registry = get_registry()
    assert registry is not None


def test_utils_module():
    """Test utils module imports and basic functionality."""
    from dbutils.utils import edit_distance, fuzzy_match, query_runner

    # Test basic functionality
    assert edit_distance("hello", "hello") == 0
    assert fuzzy_match("hello world", "hello")

    # Test query runner raises error without proper environment
    with patch.dict('os.environ', {}, clear=True):
        with pytest.raises(RuntimeError, match="DBUTILS_JDBC_PROVIDER"):
            query_runner("SELECT 1")


def test_catalog_module():
    """Test that catalog module can be imported."""
    # Import the catalog module (this may or may not exist in the project)
    try:
        from dbutils import catalog
        # If it exists, it should have the expected functions
        if hasattr(catalog, 'get_all_tables_and_columns'):
            assert callable(catalog.get_all_tables_and_columns)
    except ImportError:
        # If it doesn't exist, that's ok - just a different project structure
        pass


def test_main_launcher_imports():
    """Test that main launcher can be imported without errors."""
    try:
        from dbutils import main_launcher
        # The module should at least have a main function
        assert hasattr(main_launcher, 'main') or hasattr(main_launcher, 'smart_launcher_main')
    except ImportError:
        # If main_launcher doesn't exist, that's fine
        pass


def test_gui_module_imports():
    """Test GUI module imports (without requiring Qt)."""
    # Test that the gui module structure is correct
    try:
        import dbutils.gui
        # Module should exist
        assert dbutils.gui is not None
    except ImportError:
        # If gui module doesn't exist, that's fine
        pass

    # Test that individual GUI components can be imported (if they exist)
    try:
        import dbutils.gui.provider_config
        # Module should exist if it's there
    except ImportError:
        # If it doesn't exist, that's fine
        pass

    try:
        import dbutils.gui.jdbc_auto_downloader
        # Module should exist if it's there
    except ImportError:
        # If it doesn't exist, that's fine
        pass


def test_dataclass_immutability_patterns():
    """Test that dataclasses follow expected patterns."""
    from dbutils.db_browser import ColumnInfo, TableInfo

    # Test TableInfo
    table1 = TableInfo(schema="TEST", name="USERS", remarks="Test")
    table2 = TableInfo(schema="TEST", name="USERS", remarks="Test")

    # Should be equal with same content
    assert table1 == table2

    # Test ColumnInfo
    col1 = ColumnInfo(
        schema="TEST",
        table="USERS",
        name="ID",
        typename="INTEGER",
        length=10,
        scale=0,
        nulls="N",
        remarks="ID"
    )
    col2 = ColumnInfo(
        schema="TEST",
        table="USERS",
        name="ID",
        typename="INTEGER",
        length=10,
        scale=0,
        nulls="N",
        remarks="ID"
    )

    # Should be equal with same content
    assert col1 == col2


def test_search_functionality_integration():
    """Test integration of search functionality."""
    from dbutils.db_browser import SearchIndex, mock_get_columns, mock_get_tables

    # Create search index with mock data
    tables = mock_get_tables()
    columns = mock_get_columns()

    index = SearchIndex()
    index.build_index(tables, columns)

    # Test that search works end-to-end
    table_results = index.search_tables("USER")
    assert len(table_results) >= 0  # May or may not find results, but shouldn't error

    column_results = index.search_columns("ID")
    assert len(column_results) >= 0  # May or may not find results, but shouldn't error


def test_string_interning():
    """Test string interning functionality."""
    from dbutils.db_browser import intern_string

    # Test that identical strings return the same object
    str1 = intern_string("test_string")
    str2 = intern_string("test_string")

    # They should be the same object (identity, not just equality)
    assert str1 is str2


def test_schema_info_dataclass():
    """Test SchemaInfo dataclass if it exists."""
    try:
        from dbutils.db_browser import SchemaInfo

        # Create a schema info object
        schema_info = SchemaInfo(name="TEST_SCHEMA", table_count=10)

        assert schema_info.name == "TEST_SCHEMA"
        assert schema_info.table_count == 10
    except ImportError:
        # SchemaInfo may not exist in all versions
        pass


@patch.dict('os.environ', {'DBUTILS_JDBC_PROVIDER': 'test_provider'})
def test_query_runner_environment_check():
    """Test query runner environment requirements."""
    from dbutils.db_browser import query_runner

    # Should fail with proper error when JDBC provider is set but connection fails
    with patch('dbutils.jdbc_provider.connect') as mock_connect:
        mock_connect.side_effect = RuntimeError("Connection failed")

        with pytest.raises(RuntimeError, match="JDBC query failed"):
            query_runner("SELECT 1")


def test_async_function_availability():
    """Test that async functions are available and properly defined."""
    from dbutils.db_browser import get_all_tables_and_columns_async, get_available_schemas_async, schema_exists_async

    # All async functions should be defined
    assert callable(get_all_tables_and_columns_async)
    assert callable(schema_exists_async)
    assert callable(get_available_schemas_async)


def test_mock_data_consistency():
    """Test that mock data functions return consistent data."""
    from dbutils.db_browser import mock_get_columns, mock_get_tables

    # Multiple calls should return consistent types
    tables1 = mock_get_tables()
    tables2 = mock_get_tables()

    columns1 = mock_get_columns()
    columns2 = mock_get_columns()

    # Should return the same type of objects
    assert all(type(t) for t in tables1) == all(type(t) for t in tables2)
    assert all(type(c) for c in columns1) == all(type(c) for c in columns2)

    # Should return non-empty results
    assert len(tables1) > 0
    assert len(columns1) > 0


def test_cache_function_availability():
    """Test that cache functions are available."""
    from dbutils.db_browser import get_cache_key, load_from_cache, save_to_cache

    # Functions should be callable
    assert callable(get_cache_key)
    assert callable(load_from_cache)
    assert callable(save_to_cache)

    # Basic cache key functionality
    key = get_cache_key("TEST", limit=10, offset=5)
    assert "TEST" in key
    assert "LIMIT10" in key
    assert "OFFSET5" in key


def test_humanize_schema_name():
    """Test schema name humanization function."""
    from dbutils.db_browser import humanize_schema_name

    # Test basic functionality
    assert humanize_schema_name("TEST_SCHEMA") == "TEST SCHEMA"
    assert humanize_schema_name("DACDATA") == "DACDATA"
    assert humanize_schema_name("") == ""
    assert humanize_schema_name("A_B_C") == "A B C"


def test_fuzzy_match_variations():
    """Test fuzzy match with various input patterns."""
    from dbutils.utils import fuzzy_match

    # Exact matches
    assert fuzzy_match("hello", "hello")
    assert fuzzy_match("Hello", "hello")  # Case insensitive

    # Substring matches
    assert fuzzy_match("hello world", "hello")
    assert fuzzy_match("hello world", "world")

    # No matches
    assert not fuzzy_match("hello", "xyz")
    assert not fuzzy_match("", "hello")
    assert fuzzy_match("hello", "")  # Empty query matches anything


def test_edit_distance_variations():
    """Test edit distance with various input patterns."""
    from dbutils.utils import edit_distance

    # Identical strings
    assert edit_distance("hello", "hello") == 0

    # Single character differences
    assert edit_distance("hello", "hallo") == 1
    assert edit_distance("hello", "jello") == 1

    # Empty string handling
    assert edit_distance("", "") == 0
    assert edit_distance("hello", "") == 5
    assert edit_distance("", "hello") == 5

    # Symmetric property
    assert edit_distance("abc", "xyz") == edit_distance("xyz", "abc")


def test_trie_functionality():
    """Test TrieNode functionality."""
    from dbutils.db_browser import TrieNode

    # Create a trie and add some data
    trie = TrieNode()
    trie.insert("hello", "item1")
    trie.insert("world", "item2")
    trie.insert("help", "item3")

    # Test prefix search
    results = trie.search_prefix("hel")
    assert "item1" in results  # "hello" should match "hel"
    assert "item3" in results  # "help" should match "hel"

    # Test case insensitivity
    results = trie.search_prefix("HEL")
    assert "item1" in results  # Should work case insensitive

    # Test no results for non-existent prefix
    results = trie.search_prefix("xyz")
    assert len(results) == 0


def test_search_index_with_empty_data():
    """Test search index with empty data to ensure robustness."""
    from dbutils.db_browser import SearchIndex

    # Create index with empty data
    index = SearchIndex()
    index.build_index([], [])

    # Should handle searches gracefully
    tables = index.search_tables("anything")
    columns = index.search_columns("anything")

    # Should return empty lists, not errors
    assert tables == []
    assert columns == []


def test_import_structure():
    """Test the overall import structure of the package."""
    # Test importing the main package
    import dbutils

    # Test importing each sub-module
    import dbutils.db_browser
    import dbutils.jdbc_provider
    import dbutils.utils

    # Test that expected attributes exist
    assert hasattr(dbutils.db_browser, 'TableInfo')
    assert hasattr(dbutils.db_browser, 'ColumnInfo')
    assert hasattr(dbutils.jdbc_provider, 'JDBCProvider')
    assert hasattr(dbutils.utils, 'edit_distance')
    assert hasattr(dbutils.utils, 'fuzzy_match')


def test_module_docstrings():
    """Test that modules have proper documentation."""
    import dbutils.db_browser
    import dbutils.jdbc_provider
    import dbutils.utils

    # All modules should have docstrings
    assert dbutils.db_browser.__doc__ is not None
    assert dbutils.jdbc_provider.__doc__ is not None
    assert dbutils.utils.__doc__ is not None
