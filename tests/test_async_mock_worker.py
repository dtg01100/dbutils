"""Test async worker mock data generation."""
import pytest
from unittest.mock import MagicMock, patch
from PySide6.QtCore import QThread
from dbutils.gui.qt_app import TableContentsWorker
from dbutils.db_browser import ColumnInfo


def test_async_worker_mock_mode_generates_data():
    """Test that async worker generates mock rows when query_runner fails in mock mode."""
    worker = TableContentsWorker()
    
    # Create mock columns
    cols = [
        ColumnInfo(schema="PUBLIC", table="USERS", name="id", typename="INTEGER", length=None, scale=None, nulls="N", remarks=""),
        ColumnInfo(schema="PUBLIC", table="USERS", name="amount", typename="DECIMAL", length=None, scale=None, nulls="N", remarks=""),
        ColumnInfo(schema="PUBLIC", table="USERS", name="birth_date", typename="DATE", length=None, scale=None, nulls="Y", remarks=""),
        ColumnInfo(schema="PUBLIC", table="USERS", name="description", typename="VARCHAR", length=None, scale=None, nulls="Y", remarks=""),
    ]
    
    # Mock query_runner to raise an exception
    def mock_query_runner(sql):
        raise RuntimeError("DBUTILS_JDBC_PROVIDER not set")
    
    # Capture results
    captured_results = {"columns": None, "rows": None, "error": None}
    
    def on_results(columns, rows):
        captured_results["columns"] = columns
        captured_results["rows"] = rows
    
    def on_error(msg):
        captured_results["error"] = msg
    
    # Connect signals
    worker.results_ready.connect(on_results)
    worker.error_occurred.connect(on_error)
    
    # Test mock mode generates rows
    with patch('dbutils.db_browser.query_runner', side_effect=mock_query_runner):
        worker.perform_fetch(
            schema="PUBLIC",
            table="USERS",
            limit=5,
            start_offset=0,
            use_mock=True,
            table_columns=cols,
        )
    
    # Verify rows were generated
    assert captured_results["rows"] is not None, "Should generate rows in mock mode"
    assert len(captured_results["rows"]) == 5, f"Should generate 5 rows, got {len(captured_results['rows'])}"
    
    # Verify data types
    first_row = captured_results["rows"][0]
    assert isinstance(first_row["id"], int), "id should be int"
    assert isinstance(first_row["amount"], float), "amount should be float"
    assert isinstance(first_row["birth_date"], str), "birth_date should be string"
    assert isinstance(first_row["description"], str), "description should be string"
    
    # Verify no error was emitted
    assert captured_results["error"] is None, f"Should not emit error in mock mode, got: {captured_results['error']}"


def test_async_worker_non_mock_mode_reports_error():
    """Test that non-mock mode reports error when query_runner fails."""
    worker = TableContentsWorker()
    
    # Create mock columns
    cols = [
        ColumnInfo(schema="PUBLIC", table="USERS", name="id", typename="INTEGER", length=None, scale=None, nulls="N", remarks=""),
        ColumnInfo(schema="PUBLIC", table="USERS", name="description", typename="VARCHAR", length=None, scale=None, nulls="Y", remarks=""),
    ]
    
    # Mock query_runner to raise an exception
    def mock_query_runner(sql):
        raise RuntimeError("Connection failed")
    
    # Capture results
    captured_results = {"columns": None, "rows": None, "error": None}
    
    def on_results(columns, rows):
        captured_results["columns"] = columns
        captured_results["rows"] = rows
    
    def on_error(msg):
        captured_results["error"] = msg
    
    # Connect signals
    worker.results_ready.connect(on_results)
    worker.error_occurred.connect(on_error)
    
    # Test non-mock mode reports error
    with patch('dbutils.db_browser.query_runner', side_effect=mock_query_runner):
        worker.perform_fetch(
            schema="PUBLIC",
            table="USERS",
            limit=5,
            start_offset=0,
            use_mock=False,  # Not in mock mode
            table_columns=cols,
        )
    
    # Verify error was emitted
    assert captured_results["error"] is not None, "Should emit error in non-mock mode"
    assert "Connection failed" in captured_results["error"], f"Error should contain 'Connection failed', got: {captured_results['error']}"
    
    # Verify no rows were returned
    assert captured_results["rows"] is None or len(captured_results["rows"]) == 0, "Should not generate rows in non-mock mode"


def test_async_worker_mock_mode_with_offset():
    """Test that mock mode respects pagination offset."""
    worker = TableContentsWorker()
    
    # Create mock columns
    cols = [
        ColumnInfo(schema="PUBLIC", table="USERS", name="id", typename="INTEGER", length=None, scale=None, nulls="N", remarks=""),
        ColumnInfo(schema="PUBLIC", table="USERS", name="name", typename="VARCHAR", length=None, scale=None, nulls="Y", remarks=""),
    ]
    
    # Mock query_runner to raise an exception
    def mock_query_runner(sql):
        raise RuntimeError("DBUTILS_JDBC_PROVIDER not set")
    
    # Capture results
    captured_results = {"columns": None, "rows": None, "error": None}
    
    def on_results(columns, rows):
        captured_results["columns"] = columns
        captured_results["rows"] = rows
    
    def on_error(msg):
        captured_results["error"] = msg
    
    # Connect signals
    worker.results_ready.connect(on_results)
    worker.error_occurred.connect(on_error)
    
    # Test with offset
    with patch('dbutils.db_browser.query_runner', side_effect=mock_query_runner):
        worker.perform_fetch(
            schema="PUBLIC",
            table="USERS",
            limit=3,
            start_offset=10,  # Offset by 10
            use_mock=True,
            table_columns=cols,
        )
    
    # Verify rows were generated starting at offset
    assert captured_results["rows"] is not None, "Should generate rows with offset"
    assert len(captured_results["rows"]) == 3, f"Should generate 3 rows, got {len(captured_results['rows'])}"
    
    # Verify offset is reflected in IDs
    first_id = captured_results["rows"][0]["id"]
    assert first_id == 10 * 100, f"First ID should be 1000 (10*100), got {first_id}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
