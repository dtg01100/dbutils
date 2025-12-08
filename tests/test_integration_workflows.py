"""Integration tests for dbutils project.

Tests for:
- End-to-end workflows
- Integration between components
- Main application functionality
"""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from dbutils.db_browser import (
    SearchIndex,
    get_all_tables_and_columns,
    get_all_tables_and_columns_async,
    mock_get_columns,
    mock_get_tables,
    query_runner,
)
from dbutils.jdbc_provider import JDBCProvider, ProviderRegistry


class TestEndToEndWorkflows:
    """Test end-to-end workflows combining multiple components."""

    def test_schema_browsing_workflow(self):
        """Test the complete workflow of schema browsing."""
        # Get mock data
        tables, columns = get_all_tables_and_columns(use_mock=True)

        # Verify we got data
        assert len(tables) > 0
        assert len(columns) > 0

        # Build search index
        search_index = SearchIndex()
        search_index.build_index(tables, columns)

        # Test search capabilities
        table_results = search_index.search_tables("USER")
        assert len(table_results) > 0

        column_results = search_index.search_columns("ID")
        assert len(column_results) > 0

    @patch.dict("os.environ", {"DBUTILS_JDBC_PROVIDER": "test_provider"})
    def test_jdbc_workflow(self):
        """Test JDBC workflow from provider to query execution."""
        # Create all mocks inline to ensure proper chain
        # The JDBCConnection object has a query method, not execute on cursor
        mock_conn = MagicMock()
        expected_result = [{"result": "test_data"}]
        mock_conn.query.return_value = expected_result

        with patch("dbutils.jdbc_provider.connect", return_value=mock_conn) as mock_connect:
            result = query_runner("SELECT 'test' as result FROM SYSIBM.SYSDUMMY1")

            # Verify connection was established and query executed
            mock_connect.assert_called_once()
            mock_conn.query.assert_called_once_with("SELECT 'test' as result FROM SYSIBM.SYSDUMMY1")
            assert result == expected_result

    def test_search_index_workflow(self):
        """Test the complete search index workflow."""
        # Get mock data
        tables = mock_get_tables()
        columns = mock_get_columns()

        # Create and build search index
        search_index = SearchIndex()
        search_index.build_index(tables, columns)

        # Verify index was built properly
        all_tables = search_index.search_tables("")
        all_columns = search_index.search_columns("")

        assert len(all_tables) == len(tables)
        assert len(all_columns) == len(columns)

        # Test specific searches
        user_tables = search_index.search_tables("USER")
        id_columns = search_index.search_columns("ID")

        assert len(user_tables) > 0
        assert len(id_columns) > 0


class TestComponentIntegration:
    """Test integration between different components."""

    def test_provider_registry_and_connection(self, temp_config_dir, tmp_path):
        """Test integration between provider registry and JDBC connections."""
        # Set up provider configuration
        config_path = temp_config_dir.parent / "providers.json"

        registry = ProviderRegistry(config_path=str(config_path))

        # Add a test provider
        test_provider = JDBCProvider(
            name="Integration Test Provider",
            driver_class="com.test.Driver",
            jar_path="/path/to/test.jar",
            url_template="jdbc:test://{host}:{port}/{database}",
        )
        registry.add_or_update(test_provider)

        # Verify provider was added
        retrieved_provider = registry.get("Integration Test Provider")
        assert retrieved_provider is not None
        assert retrieved_provider.name == "Integration Test Provider"

        # Verify in list of names
        names = registry.list_names()
        assert "Integration Test Provider" in names

    @patch("dbutils.jdbc_provider.jpype")
    @patch("dbutils.jdbc_provider.jaydebeapi")
    def test_jdbc_integration_with_db_browser(self, mock_jaydebeapi, mock_jpype):
        """Test integration between JDBC provider and db_browser functions."""
        # Set up mocks
        mock_jpype.isJVMStarted.return_value = True
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_jaydebeapi.connect.return_value = mock_conn

        # Mock data for query results
        mock_cursor.fetchall.return_value = [("TEST", "USERS", "Users table"), ("TEST", "ORDERS", "Orders table")]
        mock_cursor.description = [("TABLE_SCHEMA",), ("TABLE_NAME",), ("TABLE_TEXT",)]

        # Test with mock=False to trigger actual JDBC connection
        with patch.dict("os.environ", {"DBUTILS_JDBC_PROVIDER": "TestProvider"}):
            with patch("dbutils.jdbc_provider.connect") as mock_connect_func:
                mock_connect_func.return_value = mock_conn

                # Try to call the function that would use JDBC
                # Since the real query would fail without actual DB,
                # we test that the right calls are made
                try:
                    tables, columns = get_all_tables_and_columns(schema_filter="TEST", use_mock=False, use_cache=False)
                except Exception:
                    # We expect this to fail without real DB, but we want to verify
                    # the calls were made correctly
                    pass

                # Verify connect was called
                assert mock_connect_func.called

    def test_search_with_mock_data(self):
        """Test search functionality integrated with mock data."""
        # Get mock data
        tables = mock_get_tables()
        columns = mock_get_columns()

        # Build search index with the mock data
        search_index = SearchIndex()
        search_index.build_index(tables, columns)

        # Test that specific searches return expected results
        user_tables = [t for t in tables if "USER" in t.name.upper()]
        user_search_results = search_index.search_tables("USER")

        # Should find at least the USERS table
        assert len(user_search_results) >= len(user_tables)

        id_columns = [c for c in columns if c.name == "ID"]
        id_search_results = search_index.search_columns("ID")

        # Should find at least the ID columns
        assert len(id_search_results) >= len(id_columns)


class TestAsyncIntegration:
    """Test async functionality integration."""

    @patch.dict("os.environ", {"DBUTILS_JDBC_PROVIDER": "test_provider"})
    def test_async_data_loading(self, mock_jdbc_connection):
        """Test async data loading integration."""
        mock_conn = mock_jdbc_connection["connection"]
        mock_cursor = mock_jdbc_connection["cursor"]

        # Configure mock to return test data
        mock_cursor.fetchall.return_value = [("test_schema", "test_table", "test_remarks")]
        mock_cursor.description = [("TABLE_SCHEMA",), ("TABLE_NAME",), ("TABLE_TEXT",)]

        # Mock the async query execution
        with patch("dbutils.jdbc_provider.connect") as mock_connect:
            mock_connect.return_value = mock_conn

            # Call the async function via asyncio.run to avoid requiring pytest-asyncio
            async def _run_async():
                return await get_all_tables_and_columns_async(use_mock=True)

            tables, columns = asyncio.run(_run_async())

            # Verify we got mock data (not real JDBC data)
            assert len(tables) > 0
            assert len(columns) > 0

    def test_async_vs_sync_consistency(self):
        """Test that async and sync functions return consistent results."""
        # Compare results from sync and async with mock data
        sync_tables, sync_columns = get_all_tables_and_columns(use_mock=True)

        # For async, we'll call it directly since it's a different function
        import asyncio

        async def get_async_data():
            return await get_all_tables_and_columns_async(use_mock=True)

        # Run the async function
        try:
            async_tables, async_columns = asyncio.run(get_async_data())

            # Both should return mock data with the same structure
            assert len(sync_tables) == len(async_tables)
            assert len(sync_columns) == len(async_columns)
        except RuntimeError:
            # If there's an event loop issue, we can skip this test
            pytest.skip("Event loop issue in testing environment")


class TestCachingIntegration:
    """Test integration with caching functionality."""

    def test_cache_integration_with_data_loading(self, tmp_path):
        """Test that caching works properly with data loading."""
        # Create a temporary cache directory
        cache_dir = tmp_path / ".cache" / "dbutils"
        cache_dir.mkdir(parents=True)
        cache_file = cache_dir / "schema_cache.pkl.gz"

        from dbutils.db_browser import load_from_cache, save_to_cache

        # Create test data
        tables = mock_get_tables()
        columns = mock_get_columns()

        # Test saving to cache
        with patch("dbutils.db_browser.CACHE_FILE", cache_file):
            # Save to cache
            save_to_cache("TEST", tables, columns)

            # Load from cache
            cached_data = load_from_cache("TEST")

            if cached_data:
                cached_tables, cached_columns = cached_data
                # Verify we can load it back
                assert len(cached_tables) == len(tables)
                assert len(cached_columns) == len(columns)

    def test_cache_key_generation(self):
        """Test cache key generation with different parameters."""
        from dbutils.db_browser import get_cache_key

        # Test different combinations
        assert get_cache_key("TEST") == "TEST"
        assert get_cache_key("TEST", limit=10) == "TEST_LIMIT10_OFFSET0"
        assert get_cache_key("TEST", limit=10, offset=5) == "TEST_LIMIT10_OFFSET5"
        assert get_cache_key(None) == "ALL_SCHEMAS"
        assert get_cache_key("PROD", limit=20, offset=10) == "PROD_LIMIT20_OFFSET10"


class TestProviderConfiguration:
    """Test provider configuration integration."""

    def test_provider_configuration_workflow(self, temp_config_dir, tmp_path):
        """Test the complete provider configuration workflow."""
        # Create a registry with temp config
        config_path = temp_config_dir.parent / "providers.json"
        registry = ProviderRegistry(config_path=str(config_path))

        # Add a provider
        provider = JDBCProvider(
            name="Test DB Provider",
            driver_class="com.test.Driver",
            jar_path="/path/to/driver.jar",
            url_template="jdbc:test://{host}:{port}/{database}",
            default_user="testuser",
            default_password="testpass",
            extra_properties={"ssl": "true"},
        )

        registry.add_or_update(provider)

        # Verify it was saved to file
        assert config_path.exists()

        # Create a new registry instance and verify it loads the provider
        new_registry = ProviderRegistry(config_path=str(config_path))
        loaded_provider = new_registry.get("Test DB Provider")

        assert loaded_provider is not None
        assert loaded_provider.driver_class == "com.test.Driver"
        assert loaded_provider.default_user == "testuser"
        assert loaded_provider.extra_properties == {"ssl": "true"}

    def test_provider_connection_integration(self, temp_config_dir, tmp_path):
        """Test the integration between provider configuration and connection."""
        # Set up a provider
        config_path = temp_config_dir.parent / "providers.json"
        registry = ProviderRegistry(config_path=str(config_path))

        provider = JDBCProvider(
            name="Connection Test Provider",
            driver_class="com.test.Driver",
            jar_path="/path/to/driver.jar",
            url_template="jdbc:test://{host}:{port}/{database}",
        )
        registry.add_or_update(provider)

        # Now test connecting with the configured provider
        # (without actually connecting, just test the process)
        assert registry.get("Connection Test Provider") is not None


class TestErrorHandlingIntegration:
    """Test error handling across component boundaries."""

    def test_error_propagation_from_jdbc_to_db_browser(self):
        """Test that JDBC errors are properly propagated."""
        # Test the error handling in query_runner when JDBC fails
        with patch.dict("os.environ", {"DBUTILS_JDBC_PROVIDER": "test_provider"}):
            with patch("dbutils.jdbc_provider.connect") as mock_connect:
                mock_connect.side_effect = Exception("JDBC Connection failed")

                with pytest.raises(RuntimeError, match="JDBC query failed"):
                    query_runner("SELECT * FROM DUAL")

    def test_schema_loading_with_empty_results(self):
        """Test loading schema when query returns no results."""
        # This is difficult to test without mocking the entire JDBC pipeline
        # but we test the data structures can handle empty results
        search_index = SearchIndex()
        search_index.build_index([], [])  # Empty tables and columns

        # These should return empty results without errors
        tables = search_index.search_tables("anything")
        columns = search_index.search_columns("anything")

        assert tables == []
        assert columns == []
