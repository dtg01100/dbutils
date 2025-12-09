"""
Test auto-download feature when JDBC driver is missing.
"""

import os
import pytest
import json
import tempfile
from pathlib import Path


def test_missing_jdbc_driver_error_raised():
    """Test that MissingJDBCDriverError is raised when jar_path is empty."""
    from dbutils.jdbc_provider import JDBCConnection, JDBCProvider, MissingJDBCDriverError

    # Create a provider with empty jar_path
    provider = JDBCProvider(
        name="Test Provider",
        driver_class="org.sqlite.JDBC",
        jar_path="",  # Missing jar
        url_template="jdbc:sqlite:{database}",
    )

    # Create a connection
    conn = JDBCConnection(provider, {"database": ":memory:"})

    # Attempting to connect should raise MissingJDBCDriverError
    with pytest.raises(MissingJDBCDriverError) as exc_info:
        conn.connect()

    assert exc_info.value.provider_name == "Test Provider"
    assert "not set" in str(exc_info.value)


def test_missing_jdbc_driver_error_nonexistent_file():
    """Test that MissingJDBCDriverError is raised when jar_path file doesn't exist."""
    from dbutils.jdbc_provider import JDBCConnection, JDBCProvider, MissingJDBCDriverError

    # Create a provider with nonexistent jar_path
    provider = JDBCProvider(
        name="Test Provider",
        driver_class="org.sqlite.JDBC",
        jar_path="/nonexistent/path/to/sqlite-jdbc.jar",
        url_template="jdbc:sqlite:{database}",
    )

    # Create a connection
    conn = JDBCConnection(provider, {"database": ":memory:"})

    # Attempting to connect should raise MissingJDBCDriverError
    with pytest.raises(MissingJDBCDriverError) as exc_info:
        conn.connect()

    assert exc_info.value.provider_name == "Test Provider"
    assert "/nonexistent/path/to/sqlite-jdbc.jar" in str(exc_info.value)


def test_query_runner_passes_through_missing_driver_error():
    """Test that query_runner passes through MissingJDBCDriverError without wrapping."""
    from dbutils.jdbc_provider import MissingJDBCDriverError
    from dbutils.db_browser import query_runner
    import os

    # Set up environment with a provider that has no jar
    os.environ["DBUTILS_JDBC_PROVIDER"] = "Test Provider"
    os.environ["DBUTILS_JDBC_URL_PARAMS"] = '{"database": ":memory:"}'

    # Create a temporary providers.json with a provider that has empty jar_path
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ["DBUTILS_CONFIG_DIR"] = tmpdir
        
        # Create providers.json
        config_path = Path(tmpdir) / "providers.json"
        providers = [
            {
                "name": "Test Provider",
                "driver_class": "org.sqlite.JDBC",
                "jar_path": "",
                "url_template": "jdbc:sqlite:{database}",
                "default_user": None,
                "default_password": None,
                "extra_properties": {}
            }
        ]
        with open(config_path, "w") as f:
            json.dump(providers, f)

        # Attempting to run a query should raise MissingJDBCDriverError
        with pytest.raises(MissingJDBCDriverError):
            query_runner("SELECT 1")


def test_missing_jdbc_driver_error_has_attributes():
    """Test that MissingJDBCDriverError has expected attributes for auto-download."""
    from dbutils.jdbc_provider import MissingJDBCDriverError

    error = MissingJDBCDriverError("SQLite (Test Integration)", "/path/to/sqlite-jdbc.jar")
    
    assert error.provider_name == "SQLite (Test Integration)"
    assert error.jar_path == "/path/to/sqlite-jdbc.jar"
    assert "SQLite (Test Integration)" in str(error)


if __name__ == "__main__":
    pytest.main([__file__, "-xvs"])
