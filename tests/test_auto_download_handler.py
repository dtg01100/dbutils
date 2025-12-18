"""
Test the handle_missing_jdbc_driver_auto_download function.
"""

import os
import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock


@pytest.mark.skipif(os.environ.get("QT_QPA_PLATFORM") == "offscreen", reason="Qt GUI not available in headless mode")
def test_handle_missing_jdbc_driver_no_qt():
    """Test that handle_missing_jdbc_driver_auto_download returns False when Qt is not available."""
    from dbutils.gui.provider_config_dialog import handle_missing_jdbc_driver_auto_download

    # Test with Qt unavailable
    result = handle_missing_jdbc_driver_auto_download("SQLite (Test Integration)", parent_widget=None)
    
    # Should return False because Qt bindings likely aren't available in this test context
    # or the provider won't be found
    assert result is False


def test_handle_missing_jdbc_driver_provider_not_found():
    """Test that handle_missing_jdbc_driver_auto_download handles missing provider gracefully."""
    from dbutils.gui.provider_config_dialog import handle_missing_jdbc_driver_auto_download

    # Test with a nonexistent provider
    result = handle_missing_jdbc_driver_auto_download("NonexistentProvider", parent_widget=None)
    
    # Should return False because provider won't be found
    assert result is False


def test_missing_driver_detection_workflow(mock_jdbc_connection):
    """Test the complete workflow of detecting missing driver and triggering download."""
    from dbutils.jdbc_provider import JDBCConnection, JDBCProvider, MissingJDBCDriverError
    
    # Create a provider with empty jar_path
    provider = JDBCProvider(
        name="Test SQLite",
        driver_class="org.sqlite.JDBC",
        jar_path="",  # Missing jar
        url_template="jdbc:sqlite:{database}",
    )
    
    # Create connection (with mocked jpype/jaydebeapi from fixture)
    conn = JDBCConnection(provider, {"database": ":memory:"})
    
    # Verify that attempting to connect raises MissingJDBCDriverError
    with pytest.raises(MissingJDBCDriverError) as exc_info:
        conn.connect()
    
    # Verify error has the provider name for auto-download handler
    error = exc_info.value
    assert hasattr(error, "provider_name")
    assert error.provider_name == "Test SQLite"
    assert hasattr(error, "jar_path")


if __name__ == "__main__":
    pytest.main([__file__, "-xvs"])
