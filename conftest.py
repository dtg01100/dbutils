"""Global test configuration for dbutils project.

This file contains pytest configuration and fixtures used across all test modules.
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# Add src directory to path so we can import dbutils
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


@pytest.fixture
def mock_jdbc_connection():
    """Mock JDBC connection for testing without actual database."""
    with patch("dbutils.jdbc_provider.jaydebeapi") as mock_jaydebeapi, \
         patch("dbutils.jdbc_provider.jpype") as mock_jpype:
        
        # Setup mock JPype
        mock_jpype.isJVMStarted.return_value = False
        mock_jpype.getDefaultJVMPath.return_value = "/fake/java/path"
        
        # Setup mock JayDeBeApi connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        
        mock_jaydebeapi.connect.return_value = mock_conn
        
        yield {
            "jaydebeapi": mock_jaydebeapi,
            "jpype": mock_jpype,
            "connection": mock_conn,
            "cursor": mock_cursor
        }


@pytest.fixture
def mock_db_data():
    """Provide mock database schema data for testing."""
    from dbutils.db_browser import TableInfo, ColumnInfo
    
    tables = [
        TableInfo(schema="TEST", name="USERS", remarks="User information table"),
        TableInfo(schema="TEST", name="ORDERS", remarks="Order records table"),
        TableInfo(schema="TEST", name="PRODUCTS", remarks="Product catalog table"),
        TableInfo(schema="DACDATA", name="CUSTOMERS", remarks="Customer data"),
        TableInfo(schema="DACDATA", name="INVOICES", remarks="Invoice records"),
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
    ]
    
    return {"tables": tables, "columns": columns}


@pytest.fixture
def temp_config_dir(tmp_path):
    """Provide a temporary directory for config files during testing."""
    config_dir = tmp_path / ".config" / "dbutils"
    config_dir.mkdir(parents=True)
    with patch.dict(os.environ, {"DBUTILS_CONFIG_DIR": str(config_dir)}):
        yield config_dir


@pytest.fixture
def sample_sql_query():
    """Provide sample SQL query for testing."""
    return "SELECT * FROM TEST.TABLE WHERE ID = 123"