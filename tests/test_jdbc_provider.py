"""Unit tests for dbutils.jdbc_provider module.

Tests for:
- JDBC provider configuration and registry
- Connection management
- Query execution
- Provider persistence
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from dbutils.jdbc_provider import (
    JDBCConnection,
    JDBCProvider,
    ProviderRegistry,
    connect,
    get_registry,
)


class TestJDBCProvider:
    """Test the JDBCProvider dataclass."""

    def test_jdbc_provider_creation(self):
        """Test basic JDBCProvider creation."""
        provider = JDBCProvider(
            name="Test Provider",
            driver_class="com.test.Driver",
            jar_path="/path/to/driver.jar",
            url_template="jdbc:test://{host}:{port}/{database}",
            default_user="testuser",
            default_password="testpass",
            extra_properties={"prop1": "value1"}
        )

        assert provider.name == "Test Provider"
        assert provider.driver_class == "com.test.Driver"
        assert provider.jar_path == "/path/to/driver.jar"
        assert provider.url_template == "jdbc:test://{host}:{port}/{database}"
        assert provider.default_user == "testuser"
        assert provider.default_password == "testpass"
        assert provider.extra_properties == {"prop1": "value1"}

    def test_jdbc_provider_to_dict(self):
        """Test conversion to dictionary."""
        provider = JDBCProvider(
            name="Test Provider",
            driver_class="com.test.Driver",
            jar_path="/path/to/driver.jar",
            url_template="jdbc:test://{host}:{port}/{database}",
            default_user="testuser",
            default_password="testpass",
            extra_properties={"prop1": "value1"}
        )

        provider_dict = provider.to_dict()

        assert provider_dict["name"] == "Test Provider"
        assert provider_dict["driver_class"] == "com.test.Driver"
        assert provider_dict["jar_path"] == "/path/to/driver.jar"
        assert provider_dict["url_template"] == "jdbc:test://{host}:{port}/{database}"
        assert provider_dict["default_user"] == "testuser"
        assert provider_dict["default_password"] == "testpass"
        assert provider_dict["extra_properties"] == {"prop1": "value1"}

    def test_jdbc_provider_from_dict(self):
        """Test creation from dictionary."""
        provider_dict = {
            "name": "Test Provider",
            "driver_class": "com.test.Driver",
            "jar_path": "/path/to/driver.jar",
            "url_template": "jdbc:test://{host}:{port}/{database}",
            "default_user": "testuser",
            "default_password": "testpass",
            "extra_properties": {"prop1": "value1"}
        }

        provider = JDBCProvider.from_dict(provider_dict)

        assert provider.name == "Test Provider"
        assert provider.driver_class == "com.test.Driver"
        assert provider.jar_path == "/path/to/driver.jar"
        assert provider.url_template == "jdbc:test://{host}:{port}/{database}"
        assert provider.default_user == "testuser"
        assert provider.default_password == "testpass"
        assert provider.extra_properties == {"prop1": "value1"}

    def test_jdbc_provider_default_values(self):
        """Test provider with default values."""
        provider = JDBCProvider(
            name="Minimal Provider",
            driver_class="com.test.Driver",
            jar_path="/path/to/driver.jar",
            url_template="jdbc:test://{host}:{port}/{database}"
        )

        assert provider.default_user is None
        assert provider.default_password is None
        assert provider.extra_properties is None


class TestProviderRegistry:
    """Test the ProviderRegistry functionality."""

    def test_registry_initialization_default_config(self, temp_config_dir):
        """Test registry initialization with default config path."""
        registry = ProviderRegistry()
        assert isinstance(registry.providers, dict)
        assert len(registry.providers) > 0  # Should have example provider

    def test_registry_load_empty_config(self, temp_config_dir, tmp_path):
        """Test registry loading with empty config file."""
        # Create empty config file
        config_path = temp_config_dir.parent / "providers.json"
        with open(config_path, 'w') as f:
            json.dump([], f)

        registry = ProviderRegistry(config_path=str(config_path))
        assert len(registry.providers) == 0

    def test_registry_load_invalid_config(self, temp_config_dir, tmp_path):
        """Test registry loading with invalid config file."""
        # Create invalid config file
        config_path = temp_config_dir.parent / "providers.json"
        with open(config_path, 'w') as f:
            f.write("invalid json")

        registry = ProviderRegistry(config_path=str(config_path))
        assert len(registry.providers) == 0

    def test_add_or_update_provider(self, temp_config_dir, tmp_path):
        """Test adding or updating a provider."""
        config_path = temp_config_dir.parent / "providers.json"
        registry = ProviderRegistry(config_path=str(config_path))

        provider = JDBCProvider(
            name="New Provider",
            driver_class="com.test.Driver",
            jar_path="/path/to/driver.jar",
            url_template="jdbc:test://{host}:{port}/{database}"
        )

        registry.add_or_update(provider)
        assert "New Provider" in registry.providers
        loaded_provider = registry.providers["New Provider"]
        assert loaded_provider.name == "New Provider"
        assert loaded_provider.driver_class == "com.test.Driver"

    def test_remove_provider(self, temp_config_dir, tmp_path):
        """Test removing a provider."""
        config_path = temp_config_dir.parent / "providers.json"
        registry = ProviderRegistry(config_path=str(config_path))

        # Add a provider first
        provider = JDBCProvider(
            name="Provider to Remove",
            driver_class="com.test.Driver",
            jar_path="/path/to/driver.jar",
            url_template="jdbc:test://{host}:{port}/{database}"
        )
        registry.add_or_update(provider)

        # Verify it's there
        assert "Provider to Remove" in registry.providers

        # Remove it
        registry.remove("Provider to Remove")

        # Verify it's gone
        assert "Provider to Remove" not in registry.providers

    def test_get_provider(self, temp_config_dir, tmp_path):
        """Test getting a specific provider."""
        config_path = temp_config_dir.parent / "providers.json"
        registry = ProviderRegistry(config_path=str(config_path))

        # Add a provider
        provider = JDBCProvider(
            name="Test Get Provider",
            driver_class="com.test.Driver",
            jar_path="/path/to/driver.jar",
            url_template="jdbc:test://{host}:{port}/{database}"
        )
        registry.add_or_update(provider)

        # Get the provider
        retrieved = registry.get("Test Get Provider")
        assert retrieved is not None
        assert retrieved.name == "Test Get Provider"

    def test_get_nonexistent_provider(self, temp_config_dir, tmp_path):
        """Test getting a non-existent provider."""
        config_path = temp_config_dir.parent / "providers.json"
        registry = ProviderRegistry(config_path=str(config_path))

        retrieved = registry.get("Nonexistent Provider")
        assert retrieved is None

    def test_list_provider_names(self, temp_config_dir, tmp_path):
        """Test listing provider names."""
        config_path = temp_config_dir.parent / "providers.json"
        registry = ProviderRegistry(config_path=str(config_path))

        # Add a few providers
        providers = [
            JDBCProvider("Provider A", "driver.A", "/path/A", "url.A"),
            JDBCProvider("Provider B", "driver.B", "/path/B", "url.B"),
            JDBCProvider("Provider C", "driver.C", "/path/C", "url.C"),
        ]

        for p in providers:
            registry.add_or_update(p)

        names = registry.list_names()
        assert "Provider A" in names
        assert "Provider B" in names
        assert "Provider C" in names
        assert sorted(names) == names  # Should be sorted


class TestJDBCConnection:
    """Test the JDBCConnection functionality."""

    @patch('dbutils.jdbc_provider.jpype')
    @patch('dbutils.jdbc_provider.jaydebeapi')
    def test_jdbc_connection_creation(self, mock_jaydebeapi, mock_jpype):
        """Test basic JDBC connection creation."""
        # Setup mocks
        mock_jpype.isJVMStarted.return_value = True
        mock_conn = MagicMock()
        mock_jaydebeapi.connect.return_value = mock_conn

        provider = JDBCProvider(
            name="Test Provider",
            driver_class="com.test.Driver",
            jar_path="/path/to/driver.jar",
            url_template="jdbc:test://{host}:{port}/{database}",
            default_user="testuser",
            default_password="testpass"
        )

        # Create connection
        conn = JDBCConnection(provider, {"host": "localhost", "port": "5432", "database": "mydb"})

        # Verify properties are set
        assert conn.url == "jdbc:test://localhost:5432/mydb"
        assert conn.user == "testuser"
        assert conn.password == "testpass"

    @patch('dbutils.jdbc_provider.jpype')
    @patch('dbutils.jdbc_provider.jaydebeapi')
    def test_jdbc_connection_with_custom_credentials(self, mock_jaydebeapi, mock_jpype):
        """Test JDBC connection with custom credentials."""
        mock_jpype.isJVMStarted.return_value = True
        mock_conn = MagicMock()
        mock_jaydebeapi.connect.return_value = mock_conn

        provider = JDBCProvider(
            name="Test Provider",
            driver_class="com.test.Driver",
            jar_path="/path/to/driver.jar",
            url_template="jdbc:test://{host}:{port}/{database}",
            default_user="defaultuser",
            default_password="defaultpass"
        )

        # Create connection with custom credentials
        conn = JDBCConnection(
            provider,
            {"host": "localhost", "port": "5432", "database": "mydb"},
            user="customuser",
            password="custompass"
        )

        # Verify custom credentials override defaults
        assert conn.url == "jdbc:test://localhost:5432/mydb"
        assert conn.user == "customuser"
        assert conn.password == "custompass"

    @patch('dbutils.jdbc_provider.jpype')
    @patch('dbutils.jdbc_provider.jaydebeapi')
    def test_jdbc_connection_without_credentials(self, mock_jaydebeapi, mock_jpype):
        """Test JDBC connection without any credentials."""
        mock_jpype.isJVMStarted.return_value = True
        mock_conn = MagicMock()
        mock_jaydebeapi.connect.return_value = mock_conn

        provider = JDBCProvider(
            name="Test Provider",
            driver_class="com.test.Driver",
            jar_path="/path/to/driver.jar",
            url_template="jdbc:test://{host}:{port}/{database}"
        )

        # Create connection without credentials
        conn = JDBCConnection(provider, {"host": "localhost", "port": "5432", "database": "mydb"})

        # Should be None when no defaults and no provided
        assert conn.url == "jdbc:test://localhost:5432/mydb"
        assert conn.user is None
        assert conn.password is None

    @patch('dbutils.jdbc_provider.jpype')
    @patch('dbutils.jdbc_provider.jaydebeapi')
    def test_connect_method_success(self, mock_jaydebeapi, mock_jpype):
        """Test successful connection establishment."""
        mock_jpype.isJVMStarted.return_value = True
        mock_conn = MagicMock()
        mock_jaydebeapi.connect.return_value = mock_conn

        provider = JDBCProvider(
            name="Test Provider",
            driver_class="com.test.Driver",
            jar_path="/path/to/driver.jar",
            url_template="jdbc:test://{host}:{port}/{database}"
        )

        conn = JDBCConnection(provider, {"host": "localhost", "port": "5432", "database": "mydb"})
        result = conn.connect()

        # Verify the connection object itself is returned
        assert result == conn
        # Verify the internal connection is set
        assert conn._conn == mock_conn
        # Verify connect was called with correct parameters
        mock_jaydebeapi.connect.assert_called_once_with(
            "com.test.Driver",
            "jdbc:test://localhost:5432/mydb",
            ["", ""],  # Empty user/password since none provided in provider defaults
            "/path/to/driver.jar"
        )

    @patch('dbutils.jdbc_provider.jpype')
    @patch('dbutils.jdbc_provider.jaydebeapi')
    def test_query_method(self, mock_jaydebeapi, mock_jpype):
        """Test query execution method."""
        mock_jpype.isJVMStarted.return_value = True
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_jaydebeapi.connect.return_value = mock_conn

        # Setup cursor mock
        mock_cursor.description = [("id",), ("name",)]
        mock_cursor.fetchall.return_value = [(1, "test"), (2, "example")]

        provider = JDBCProvider(
            name="Test Provider",
            driver_class="com.test.Driver",
            jar_path="/path/to/driver.jar",
            url_template="jdbc:test://{host}:{port}/{database}"
        )

        conn = JDBCConnection(provider, {"host": "localhost", "port": "5432", "database": "mydb"})
        conn.connect()

        # Execute query
        result = conn.query("SELECT * FROM users")

        # Verify query was executed
        mock_cursor.execute.assert_called_once_with("SELECT * FROM users")
        # Verify results are formatted correctly
        assert result == [{"id": 1, "name": "test"}, {"id": 2, "name": "example"}]

    @patch('dbutils.jdbc_provider.jpype')
    @patch('dbutils.jdbc_provider.jaydebeapi')
    def test_query_method_no_columns(self, mock_jaydebeapi, mock_jpype):
        """Test query execution when cursor has no description."""
        mock_jpype.isJVMStarted.return_value = True
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_jaydebeapi.connect.return_value = mock_conn

        # Setup cursor mock with no description
        mock_cursor.description = None
        mock_cursor.fetchall.return_value = [(1, "test"), (2, "example")]

        provider = JDBCProvider(
            name="Test Provider",
            driver_class="com.test.Driver",
            jar_path="/path/to/driver.jar",
            url_template="jdbc:test://{host}:{port}/{database}"
        )

        conn = JDBCConnection(provider, {"host": "localhost", "port": "5432", "database": "mydb"})
        conn.connect()

        # Execute query
        result = conn.query("SELECT * FROM users")

        # Verify when description is None, we get empty dicts
        # The actual behavior is that when description is None, cols=[] and zip([], row) produces {}
        assert result == [{}, {}]

    @patch('dbutils.jdbc_provider.jpype')
    @patch('dbutils.jdbc_provider.jaydebeapi')
    def test_close_method(self, mock_jaydebeapi, mock_jpype):
        """Test connection close method."""
        mock_jpype.isJVMStarted.return_value = True
        mock_conn = MagicMock()
        mock_jaydebeapi.connect.return_value = mock_conn

        provider = JDBCProvider(
            name="Test Provider",
            driver_class="com.test.Driver",
            jar_path="/path/to/driver.jar",
            url_template="jdbc:test://{host}:{port}/{database}"
        )

        conn = JDBCConnection(provider, {"host": "localhost", "port": "5432", "database": "mydb"})
        conn.connect()

        # Close the connection
        conn.close()

        # Verify close was called on the internal connection
        mock_conn.close.assert_called_once()
        # Verify internal connection is set to None
        assert conn._conn is None

    @patch('dbutils.jdbc_provider.jpype')
    @patch('dbutils.jdbc_provider.jaydebeapi')
    def test_close_method_no_connection(self, mock_jaydebeapi, mock_jpype):
        """Test closing a connection that was never established."""
        provider = JDBCProvider(
            name="Test Provider",
            driver_class="com.test.Driver",
            jar_path="/path/to/driver.jar",
            url_template="jdbc:test://{host}:{port}/{database}"
        )

        conn = JDBCConnection(provider, {"host": "localhost", "port": "5432", "database": "mydb"})
        # Don't connect, just close directly

        # This should not raise an exception
        conn.close()
        assert conn._conn is None

    def test_jdbc_connection_without_libraries(self):
        """Test JDBC connection without required libraries."""
        # Temporarily remove the libraries to simulate missing dependencies
        import dbutils.jdbc_provider as jdbc_module

        original_jaydebeapi = jdbc_module.jaydebeapi
        original_jpype = jdbc_module.jpype

        try:
            jdbc_module.jaydebeapi = None
            jdbc_module.jpype = None

            provider = JDBCProvider(
                name="Test Provider",
                driver_class="com.test.Driver",
                jar_path="/path/to/driver.jar",
                url_template="jdbc:test://{host}:{port}/{database}"
            )

            with pytest.raises(RuntimeError, match="JDBC bridge libraries"):
                JDBCConnection(provider, {"host": "localhost", "port": "5432", "database": "mydb"})
        finally:
            # Restore original modules
            jdbc_module.jaydebeapi = original_jaydebeapi
            jdbc_module.jpype = original_jpype


class TestTopLevelFunctions:
    """Test the top-level convenience functions."""

    def test_get_registry_singleton(self):
        """Test registry singleton behavior."""
        registry1 = get_registry()
        registry2 = get_registry()
        assert registry1 is registry2

    @patch('dbutils.jdbc_provider.jpype')
    @patch('dbutils.jdbc_provider.jaydebeapi')
    def test_connect_function(self, mock_jaydebeapi, mock_jpype, temp_config_dir, tmp_path):
        """Test the connect function."""
        mock_jpype.isJVMStarted.return_value = True
        mock_conn = MagicMock()
        mock_jaydebeapi.connect.return_value = mock_conn

        # Create a provider registry using the temp config (which is set in the fixture)
        provider = JDBCProvider(
            name="Test Provider",
            driver_class="com.test.Driver",
            jar_path="/path/to/driver.jar",
            url_template="jdbc:test://{host}:{port}/{database}"
        )

        # Get the global registry and add our provider there
        registry = get_registry()
        # Temporarily use our custom config path
        original_config = registry.config_path
        registry.config_path = str(temp_config_dir.parent / "providers.json")

        try:
            registry.add_or_update(provider)

            # Test the connect function
            result_conn = connect("Test Provider", {"host": "localhost", "port": "5432", "database": "mydb"})

            assert isinstance(result_conn, JDBCConnection)
            assert result_conn.url == "jdbc:test://localhost:5432/mydb"
        finally:
            # Restore original config path
            registry.config_path = original_config

    def test_connect_function_unknown_provider(self):
        """Test connect function with unknown provider."""
        with pytest.raises(KeyError, match="Provider 'Unknown' not found"):
            connect("Unknown", {"host": "localhost", "port": "5432", "database": "mydb"})
