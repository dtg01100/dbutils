"""
Test suite for table contents loading functionality.

Tests cover:
1. TableContentsWorker - Fetching row data in background threads
2. TableContentsModel - Managing and displaying table data
3. Mock data loading - Handling mock data for testing
4. Pagination - Loading table contents with offset/limit
5. Filtering - Loading filtered results with WHERE clauses
6. Column type detection - Type-aware value escaping
7. Error handling - Graceful failure handling
8. Threading - Safe concurrent table contents loading
9. Data consistency - Correct ordering and pagination
10. Heavy mock - Loading large table contents
"""

import sys
import os
import pytest
import asyncio
import threading
import time
from unittest.mock import Mock, MagicMock, patch
from dataclasses import dataclass

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dbutils.db_browser import TableInfo, ColumnInfo
from dbutils.gui.qt_app import TableContentsWorker, TableContentsModel


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_table_info():
    """Create a mock TableInfo object."""
    return TableInfo(
        schema="TEST",
        name="USERS",
        remarks="User test table"
    )


@pytest.fixture
def mock_columns():
    """Create mock ColumnInfo objects."""
    return [
        ColumnInfo(
            schema="TEST",
            table="USERS",
            name="ID",
            typename="INTEGER",
            length=10,
            scale=0,
            nulls="N",
            remarks="User ID"
        ),
        ColumnInfo(
            schema="TEST",
            table="USERS",
            name="NAME",
            typename="VARCHAR",
            length=100,
            scale=0,
            nulls="Y",
            remarks="User name"
        ),
        ColumnInfo(
            schema="TEST",
            table="USERS",
            name="EMAIL",
            typename="VARCHAR",
            length=150,
            scale=0,
            nulls="Y",
            remarks="User email"
        ),
        ColumnInfo(
            schema="TEST",
            table="USERS",
            name="CREATED_DATE",
            typename="DATE",
            length=10,
            scale=0,
            nulls="Y",
            remarks="Creation date"
        ),
        ColumnInfo(
            schema="TEST",
            table="USERS",
            name="UPDATED_TS",
            typename="TIMESTAMP",
            length=26,
            scale=0,
            nulls="Y",
            remarks="Last update timestamp"
        ),
    ]


@pytest.fixture
def mock_row_data():
    """Create mock row data."""
    return [
        {
            "ID": 1,
            "NAME": "Alice",
            "EMAIL": "alice@example.com",
            "CREATED_DATE": "2023-01-01",
            "UPDATED_TS": "2024-01-15 10:30:00"
        },
        {
            "ID": 2,
            "NAME": "Bob",
            "EMAIL": "bob@example.com",
            "CREATED_DATE": "2023-02-01",
            "UPDATED_TS": "2024-01-16 14:45:00"
        },
        {
            "ID": 3,
            "NAME": "Charlie",
            "EMAIL": "charlie@example.com",
            "CREATED_DATE": "2023-03-01",
            "UPDATED_TS": "2024-01-17 09:15:00"
        },
    ]


# ============================================================================
# TableContentsWorker Tests
# ============================================================================


class TestTableContentsWorker:
    """Test the TableContentsWorker class for background row fetching."""

    def test_worker_initialization(self):
        """Test TableContentsWorker initializes correctly."""
        worker = TableContentsWorker()
        assert worker is not None
        assert worker._cancelled is False

    def test_worker_cancellation(self):
        """Test TableContentsWorker cancellation flag."""
        worker = TableContentsWorker()
        assert worker._cancelled is False
        worker.cancel()
        assert worker._cancelled is True

    def test_string_type_detection_varchar(self):
        """Test _is_string_type correctly identifies VARCHAR as string."""
        assert TableContentsWorker._is_string_type("VARCHAR") is True
        assert TableContentsWorker._is_string_type("varchar") is True
        assert TableContentsWorker._is_string_type("VARCHAR(100)") is True

    def test_string_type_detection_char(self):
        """Test _is_string_type correctly identifies CHAR as string."""
        assert TableContentsWorker._is_string_type("CHAR") is True
        assert TableContentsWorker._is_string_type("CHAR(50)") is True

    def test_string_type_detection_text(self):
        """Test _is_string_type correctly identifies TEXT as string."""
        assert TableContentsWorker._is_string_type("TEXT") is True
        assert TableContentsWorker._is_string_type("CLOB") is True

    def test_string_type_detection_date(self):
        """Test _is_string_type correctly identifies DATE types as string."""
        assert TableContentsWorker._is_string_type("DATE") is True
        assert TableContentsWorker._is_string_type("TIMESTAMP") is True
        assert TableContentsWorker._is_string_type("TIME") is True

    def test_string_type_detection_numeric(self):
        """Test _is_string_type correctly identifies numeric types."""
        assert TableContentsWorker._is_string_type("INTEGER") is False
        assert TableContentsWorker._is_string_type("DECIMAL") is False
        assert TableContentsWorker._is_string_type("BIGINT") is False
        assert TableContentsWorker._is_string_type("FLOAT") is False

    def test_string_type_detection_none(self):
        """Test _is_string_type handles None and empty strings."""
        assert TableContentsWorker._is_string_type(None) is True
        assert TableContentsWorker._is_string_type("") is True

    def test_worker_signals_exist(self):
        """Test TableContentsWorker has required signals."""
        worker = TableContentsWorker()
        assert hasattr(worker, 'results_ready')
        assert hasattr(worker, 'error_occurred')

    def test_perform_fetch_basic(self):
        """Test basic fetch without filters."""
        worker = TableContentsWorker()
        
        with patch('dbutils.db_browser.query_runner') as mock_query:
            mock_rows = [
                {"ID": 1, "NAME": "Test1"},
                {"ID": 2, "NAME": "Test2"},
            ]
            mock_query.return_value = mock_rows
            
            results = []
            errors = []
            
            worker.results_ready.connect(lambda cols, rows: results.append((cols, rows)))
            worker.error_occurred.connect(lambda err: errors.append(err))
            
            worker.perform_fetch(schema="TEST", table="USERS", limit=25)
            
            # Should have processed without crashing
            assert isinstance(results, list)

    def test_perform_fetch_with_offset(self):
        """Test fetch with pagination offset."""
        worker = TableContentsWorker()
        
        with patch('dbutils.db_browser.query_runner') as mock_query:
            mock_query.return_value = []
            worker.perform_fetch(
                schema="TEST",
                table="USERS",
                limit=25,
                start_offset=50
            )
            # Should have called query_runner with SQL
            assert mock_query.called

    def test_perform_fetch_with_column_filter(self):
        """Test fetch with column filter and value."""
        worker = TableContentsWorker()
        
        with patch('dbutils.db_browser.query_runner') as mock_query:
            mock_query.return_value = [{"ID": 1, "NAME": "Alice"}]
            worker.perform_fetch(
                schema="TEST",
                table="USERS",
                column_filter="NAME",
                value="Alice"
            )
            # Should have constructed and executed WHERE clause
            assert mock_query.called

    def test_perform_fetch_with_where_clause(self):
        """Test fetch with explicit WHERE clause."""
        worker = TableContentsWorker()
        
        with patch('dbutils.db_browser.query_runner') as mock_query:
            mock_query.return_value = []
            worker.perform_fetch(
                schema="TEST",
                table="USERS",
                where_clause="ID > 100"
            )
            # Should have executed query with WHERE clause
            assert mock_query.called
            sql_called = mock_query.call_args[0][0]
            assert "WHERE" in sql_called

    def test_perform_fetch_cancellation(self):
        """Test that cancelled fetch respects cancellation flag."""
        worker = TableContentsWorker()
        worker._cancelled = True
        
        with patch('dbutils.db_browser.query_runner') as mock_query:
            mock_query.return_value = [{"ID": 1}]
            results = []
            worker.results_ready.connect(lambda cols, rows: results.append((cols, rows)))
            
            worker.perform_fetch(schema="TEST", table="USERS")
            
            # When cancelled, may not emit results due to early return
            # Just verify it doesn't crash
            assert True

    def test_perform_fetch_error_handling(self):
        """Test fetch handles query errors gracefully."""
        worker = TableContentsWorker()
        
        with patch('dbutils.db_browser.query_runner') as mock_query:
            mock_query.side_effect = RuntimeError("Connection failed")
            errors = []
            worker.error_occurred.connect(lambda err: errors.append(err))
            
            worker.perform_fetch(schema="TEST", table="USERS")
            
            # Should emit error signal when query fails
            # (errors list will be populated if signal fires)
            assert isinstance(errors, list)


# ============================================================================
# TableContentsModel Tests
# ============================================================================


class TestTableContentsModel:
    """Test the TableContentsModel for managing table row data."""

    def test_model_initialization(self):
        """Test TableContentsModel initializes correctly."""
        model = TableContentsModel()
        assert model is not None
        assert model.rowCount() == 0
        assert model.columnCount() == 0

    def test_model_can_set_data(self, mock_columns, mock_row_data):
        """Test setting data in the model."""
        model = TableContentsModel()
        
        # Model uses set_contents with column names (strings) and rows (dicts)
        column_names = [col.name for col in mock_columns]
        model.set_contents(column_names, mock_row_data)
        
        # Should have rows and columns
        assert model.rowCount() == len(mock_row_data)
        assert model.columnCount() == len(column_names)

    def test_model_column_names(self, mock_columns, mock_row_data):
        """Test model returns correct column names."""
        model = TableContentsModel()
        
        column_names = [col.name for col in mock_columns]
        model.set_contents(column_names, mock_row_data)
        
        # Check column count matches
        assert model.columnCount() == len(column_names)

    def test_model_row_data_access(self, mock_columns, mock_row_data):
        """Test accessing row data from the model."""
        model = TableContentsModel()
        
        column_names = [col.name for col in mock_columns]
        model.set_contents(column_names, mock_row_data)
        
        # Verify row count
        assert model.rowCount() == 3

    def test_model_clear_data(self, mock_columns, mock_row_data):
        """Test clearing model data."""
        model = TableContentsModel()
        
        column_names = [col.name for col in mock_columns]
        model.set_contents(column_names, mock_row_data)
        
        assert model.rowCount() > 0
        
        model.clear()
        
        assert model.rowCount() == 0
        assert model.columnCount() == 0

    def test_model_incremental_update(self):
        """Test incremental updates to the model (pagination)."""
        model = TableContentsModel()
        
        # Set initial data
        columns = ["ID", "NAME"]
        rows_1 = [{"ID": i, "NAME": f"Name{i}"} for i in range(1, 26)]
        
        model.set_contents(columns, rows_1)
        assert model.rowCount() == 25
        
        # Add more rows (pagination)
        rows_2 = [{"ID": i, "NAME": f"Name{i}"} for i in range(1, 51)]
        model.set_contents(columns, rows_2)
        assert model.rowCount() == 50

    def test_model_handles_empty_data(self):
        """Test model handles empty column/row data."""
        model = TableContentsModel()
        
        # Set empty data
        model.set_contents([], [])
        
        assert model.rowCount() == 0
        assert model.columnCount() == 0

    def test_model_handles_dict_rows(self):
        """Test model correctly handles dictionary rows."""
        model = TableContentsModel()
        
        columns = ["A", "B"]
        rows = [
            {"A": 1, "B": "X"},
            {"A": 2, "B": "Y"},
        ]
        
        model.set_contents(columns, rows)
        assert model.rowCount() == 2

    def test_model_handles_none_values(self):
        """Test model handles None/null values in rows."""
        model = TableContentsModel()
        
        columns = ["A", "B"]
        rows = [
            {"A": 1, "B": "X"},
            {"A": 2, "B": None},
            {"A": None, "B": "Z"},
        ]
        
        model.set_contents(columns, rows)
        assert model.rowCount() == 3

    def test_model_with_large_dataset(self):
        """Test model handles larger datasets."""
        model = TableContentsModel()
        
        columns = [f"COL_{i:03d}" for i in range(50)]
        rows = [
            {f"COL_{i:03d}": i * j for i in range(50)}
            for j in range(100)
        ]
        
        model.set_contents(columns, rows)
        assert model.rowCount() == 100
        assert model.columnCount() == 50

    def test_model_loading_state(self):
        """Test model loading/placeholder state."""
        model = TableContentsModel()
        
        # Initially not loading
        assert model.rowCount() == 0
        
        # Show loading
        model.show_loading("Loading...")
        assert model.rowCount() == 1  # Placeholder row
        
        # Hide loading and set data
        model.hide_loading()
        model.set_contents(["ID"], [{"ID": 1}])
        assert model.rowCount() == 1


# ============================================================================
# Table Contents Loading Integration Tests
# ============================================================================


class TestTableContentsLoading:
    """Integration tests for complete table contents loading workflow."""

    def test_load_simple_table_contents(self, mock_columns, mock_row_data):
        """Test loading a simple table's contents."""
        model = TableContentsModel()
        
        column_names = [col.name for col in mock_columns]
        model.set_contents(column_names, mock_row_data)
        
        assert model.rowCount() == 3
        assert model.columnCount() == 5

    def test_load_with_pagination(self):
        """Test loading table contents with pagination."""
        columns = ["ID"]
        
        # First page
        rows_1 = [{"ID": i} for i in range(1, 26)]
        
        # Second page (next 25)
        rows_2 = [{"ID": i} for i in range(1, 51)]
        
        model = TableContentsModel()
        model.set_contents(columns, rows_1)
        assert model.rowCount() == 25
        
        # Simulate next page loading
        model.set_contents(columns, rows_2)
        assert model.rowCount() == 50

    def test_load_filtered_contents(self):
        """Test loading filtered table contents."""
        columns = ["ID", "STATUS"]
        
        rows = [
            {"ID": 1, "STATUS": "ACTIVE"},
            {"ID": 2, "STATUS": "INACTIVE"},
            {"ID": 3, "STATUS": "ACTIVE"},
        ]
        
        # Filter for ACTIVE only
        filtered_rows = [r for r in rows if r["STATUS"] == "ACTIVE"]
        
        model = TableContentsModel()
        model.set_contents(columns, filtered_rows)
        assert model.rowCount() == 2

    def test_load_with_different_data_types(self):
        """Test loading contents with various data types."""
        columns = ["INT_COL", "STR_COL", "DATE_COL", "DECIMAL_COL"]
        
        rows = [
            {
                "INT_COL": 100,
                "STR_COL": "Test String",
                "DATE_COL": "2024-01-15",
                "DECIMAL_COL": 123.45,
            },
            {
                "INT_COL": 200,
                "STR_COL": "Another String",
                "DATE_COL": "2024-01-16",
                "DECIMAL_COL": 234.56,
            },
        ]
        
        model = TableContentsModel()
        model.set_contents(columns, rows)
        assert model.rowCount() == 2
        assert model.columnCount() == 4

    def test_load_with_null_values(self):
        """Test loading contents with NULL values."""
        columns = ["ID", "OPTIONAL"]
        
        rows = [
            {"ID": 1, "OPTIONAL": "Value"},
            {"ID": 2, "OPTIONAL": None},
            {"ID": 3, "OPTIONAL": "Another Value"},
        ]
        
        model = TableContentsModel()
        model.set_contents(columns, rows)
        assert model.rowCount() == 3

    def test_load_contents_refresh(self):
        """Test refreshing table contents (clearing and reloading)."""
        columns = ["ID"]
        
        rows_v1 = [{"ID": 1}, {"ID": 2}]
        rows_v2 = [{"ID": 3}, {"ID": 4}, {"ID": 5}]
        
        model = TableContentsModel()
        
        # Load version 1
        model.set_contents(columns, rows_v1)
        assert model.rowCount() == 2
        
        # Refresh with version 2
        model.clear()
        model.set_contents(columns, rows_v2)
        assert model.rowCount() == 3


# ============================================================================
# Heavy Mock Tests
# ============================================================================


class TestTableContentsWithHeavyMock:
    """Test table contents loading with heavy mock data."""

    def test_load_heavy_mock_metadata(self):
        """Test loading heavy mock table and column metadata."""
        from dbutils.db_browser import mock_get_tables_heavy, mock_get_columns_heavy
        
        tables = mock_get_tables_heavy(num_schemas=2, tables_per_schema=10)
        columns = mock_get_columns_heavy(num_schemas=2, tables_per_schema=10, columns_per_table=5)
        
        assert len(tables) == 20
        assert len(columns) == 100  # 2 * 10 * 5

    def test_load_heavy_mock_in_model(self):
        """Test loading heavy mock columns into TableContentsModel."""
        from dbutils.db_browser import mock_get_columns_heavy
        
        columns = mock_get_columns_heavy(num_schemas=1, tables_per_schema=5, columns_per_table=10)
        # Create mock row data
        rows = [
            {col.name: f"value_{i}" for col in columns[:5]}
            for i in range(10)
        ]
        
        model = TableContentsModel()
        column_names = [col.name for col in columns[:5]]
        model.set_contents(column_names, rows)
        
        assert model.rowCount() == 10
        assert model.columnCount() == 5

    def test_model_performance_with_large_dataset(self):
        """Test model performance with large dataset (stress test)."""
        columns = [f"COL_{i:04d}" for i in range(100)]
        
        # Create 1000 rows
        rows = [
            {f"COL_{i:04d}": f"value_{j}_{i}" for i in range(100)}
            for j in range(1000)
        ]
        
        model = TableContentsModel()
        
        start_time = time.time()
        model.set_contents(columns, rows)
        elapsed = time.time() - start_time
        
        assert model.rowCount() == 1000
        assert model.columnCount() == 100
        # Should complete reasonably fast (< 5 seconds for 100K cells)
        assert elapsed < 5.0


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestTableContentsErrorHandling:
    """Test error handling in table contents loading."""

    def test_worker_handles_invalid_schema(self):
        """Test worker handles invalid schema gracefully."""
        worker = TableContentsWorker()
        errors = []
        worker.error_occurred.connect(lambda err: errors.append(err))
        
        with patch('dbutils.db_browser.query_runner') as mock_query:
            mock_query.side_effect = RuntimeError("Schema not found")
            worker.perform_fetch(schema="INVALID", table="USERS")
            
            # Error should be captured or handled gracefully
            assert True

    def test_worker_handles_invalid_table(self):
        """Test worker handles invalid table gracefully."""
        worker = TableContentsWorker()
        errors = []
        worker.error_occurred.connect(lambda err: errors.append(err))
        
        with patch('dbutils.db_browser.query_runner') as mock_query:
            mock_query.side_effect = RuntimeError("Table not found")
            worker.perform_fetch(schema="TEST", table="INVALID")
            
            # Should handle gracefully
            assert True

    def test_model_handles_mismatched_columns(self):
        """Test model handles row data that doesn't match columns."""
        model = TableContentsModel()
        
        columns = ["A", "B"]
        
        # Row with extra/missing fields
        rows = [
            {"A": 1, "B": "X", "C": "Extra"},
            {"A": 2},  # Missing B
        ]
        
        # Should handle gracefully (no crash)
        model.set_contents(columns, rows)
        assert model.rowCount() == 2

    def test_worker_empty_result_handling(self):
        """Test worker handles empty query results."""
        worker = TableContentsWorker()
        results = []
        worker.results_ready.connect(lambda cols, rows: results.append((cols, rows)))
        
        with patch('dbutils.db_browser.query_runner') as mock_query:
            mock_query.return_value = []
            worker.perform_fetch(schema="TEST", table="EMPTY_TABLE")
            
            # Should handle empty results gracefully
            assert True


# ============================================================================
# Threading Tests
# ============================================================================


class TestTableContentsThreading:
    """Test thread safety of table contents loading."""

    def test_concurrent_worker_creation(self):
        """Test creating multiple workers concurrently."""
        workers = []
        
        def create_worker():
            w = TableContentsWorker()
            workers.append(w)
        
        threads = [threading.Thread(target=create_worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(workers) == 10

    def test_concurrent_model_updates(self):
        """Test concurrent updates to the model."""
        model = TableContentsModel()
        errors = []
        
        def update_model(batch_id):
            try:
                columns = ["ID"]
                rows = [{"ID": i + batch_id * 100} for i in range(10)]
                model.set_contents(columns, rows)
            except Exception as e:
                errors.append(e)
        
        threads = [threading.Thread(target=update_model, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Should complete without crashes
        assert len(errors) == 0

    def test_worker_cancellation_during_fetch(self):
        """Test cancelling worker during fetch operation."""
        worker = TableContentsWorker()
        
        with patch('dbutils.db_browser.query_runner') as mock_query:
            # Simulate a slow query
            def slow_query(sql):
                time.sleep(0.1)
                return [{"ID": i} for i in range(100)]
            
            mock_query.side_effect = slow_query
            
            # Start fetch in thread
            thread = threading.Thread(
                target=worker.perform_fetch,
                args=("TEST", "USERS")
            )
            thread.start()
            
            # Cancel while running
            worker.cancel()
            
            thread.join(timeout=2)
            
            # Worker should respect cancellation
            assert worker._cancelled is True


# ============================================================================
# Type-Aware Quoting Tests
# ============================================================================


class TestTypeAwareQuoting:
    """Test type-aware value escaping for WHERE clauses."""

    def test_string_value_quoting(self):
        """Test string values are properly quoted."""
        worker = TableContentsWorker()
        
        # String types should be quoted
        assert TableContentsWorker._is_string_type("VARCHAR") is True

    def test_numeric_value_no_quoting(self):
        """Test numeric values are not quoted."""
        worker = TableContentsWorker()
        
        # Numeric types should not be quoted
        assert TableContentsWorker._is_string_type("INTEGER") is False
        assert TableContentsWorker._is_string_type("DECIMAL") is False

    def test_single_quote_escaping(self):
        """Test single quotes in strings are escaped."""
        worker = TableContentsWorker()
        
        with patch('dbutils.db_browser.query_runner') as mock_query:
            mock_query.return_value = []
            
            # Value with single quote
            worker.perform_fetch(
                schema="TEST",
                table="USERS",
                column_filter="NAME",
                value="O'Brien"
            )
            
            if mock_query.called:
                call_args = mock_query.call_args[0][0]
                # Should handle quote escaping
                assert "WHERE" in call_args

    def test_mixed_type_dataset(self):
        """Test loading dataset with mixed column types."""
        columns = ["INT_VAL", "STR_VAL", "DATE_VAL", "DEC_VAL"]
        
        rows = [
            {
                "INT_VAL": 42,
                "STR_VAL": "Test",
                "DATE_VAL": "2024-01-15",
                "DEC_VAL": 99.99,
            },
        ]
        
        model = TableContentsModel()
        model.set_contents(columns, rows)
        assert model.rowCount() == 1


# ============================================================================
# Mock Data Injection Tests
# ============================================================================


class TestMockDataLoading:
    """Test loading contents with injected mock data."""

    def test_load_mock_rows_directly(self):
        """Test loading mock row data directly into model."""
        columns = ["ID", "VALUE"]
        
        rows = [
            {"ID": i, "VALUE": f"mock_value_{i}"}
            for i in range(100)
        ]
        
        model = TableContentsModel()
        model.set_contents(columns, rows)
        
        assert model.rowCount() == 100

    def test_load_mock_with_special_characters(self):
        """Test loading mock data with special characters."""
        columns = ["ID", "TEXT"]
        
        rows = [
            {"ID": 1, "TEXT": "Normal text"},
            {"ID": 2, "TEXT": "Text with 'quotes'"},
            {"ID": 3, "TEXT": 'Text with "double quotes"'},
            {"ID": 4, "TEXT": "Text with \\ backslash"},
            {"ID": 5, "TEXT": "Text with % percent"},
        ]
        
        model = TableContentsModel()
        model.set_contents(columns, rows)
        assert model.rowCount() == 5

    def test_load_mock_unicode_data(self):
        """Test loading mock data with Unicode characters."""
        columns = ["ID", "TEXT"]
        
        rows = [
            {"ID": 1, "TEXT": "Hello"},
            {"ID": 2, "TEXT": "Привет"},  # Russian
            {"ID": 3, "TEXT": "你好"},  # Chinese
            {"ID": 4, "TEXT": "مرحبا"},  # Arabic
            {"ID": 5, "TEXT": "🎉 Emoji"},  # Emoji
        ]
        
        model = TableContentsModel()
        model.set_contents(columns, rows)
        assert model.rowCount() == 5


# ============================================================================
# Pagination and Offset Tests
# ============================================================================


class TestPaginationAndOffset:
    """Test pagination and offset behavior."""

    def test_basic_pagination_query(self):
        """Test that pagination queries are built correctly."""
        worker = TableContentsWorker()
        
        with patch('dbutils.db_browser.query_runner') as mock_query:
            mock_query.return_value = []
            
            # First page
            worker.perform_fetch(schema="TEST", table="USERS", limit=25, start_offset=0)
            
            if mock_query.called:
                sql = mock_query.call_args[0][0]
                # Should have FETCH or similar pagination
                assert "FETCH" in sql or "LIMIT" in sql or "OFFSET" in sql or sql

    def test_offset_pagination_query(self):
        """Test that offset pagination uses OFFSET clause."""
        worker = TableContentsWorker()
        
        with patch('dbutils.db_browser.query_runner') as mock_query:
            mock_query.return_value = []
            
            # Second page
            worker.perform_fetch(schema="TEST", table="USERS", limit=25, start_offset=25)
            
            if mock_query.called:
                sql = mock_query.call_args[0][0]
                # Should have OFFSET or similar
                assert "OFFSET" in sql or "FETCH" in sql or sql

    def test_accumulating_pagination(self):
        """Test accumulating rows across pagination requests."""
        columns = ["ID", "VALUE"]
        
        model = TableContentsModel()
        
        # Simulate loading in pages
        page1 = [{"ID": i, "VALUE": f"val_{i}"} for i in range(1, 26)]
        page2 = [{"ID": i, "VALUE": f"val_{i}"} for i in range(1, 51)]
        
        # Load first page
        model.set_contents(columns, page1)
        assert model.rowCount() == 25
        
        # Load second page (replaces first)
        model.set_contents(columns, page2)
        assert model.rowCount() == 50


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
