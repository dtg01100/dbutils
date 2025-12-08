"""Comprehensive tests for TableContentsModel functionality."""

from PySide6.QtCore import Qt

from dbutils.db_browser import ColumnInfo
from dbutils.gui.qt_app import TableContentsModel


class TestTableContentsModel:
    """Test the TableContentsModel class."""

    def test_table_contents_model_initialization(self):
        """Test TableContentsModel initialization."""
        model = TableContentsModel()

        assert model._columns == []
        assert model._rows == []
        assert model._display_columns == []
        assert not model._is_loading
        assert model._loading_message == ""

    def test_table_contents_model_set_contents(self):
        """Test setting contents in TableContentsModel."""
        model = TableContentsModel()

        columns = ["id", "name", "email"]
        rows = [
            {"id": 1, "name": "John", "email": "john@example.com"},
            {"id": 2, "name": "Jane", "email": "jane@example.com"},
        ]

        model.set_contents(columns, rows)

        assert model._columns == columns
        assert model._rows == rows
        assert model._display_columns == columns
        assert not model._is_loading

    def test_table_contents_model_clear(self):
        """Test clearing contents in TableContentsModel."""
        model = TableContentsModel()

        # Set some content first
        model.set_contents(["col1"], [{"col1": "val1"}])

        # Clear
        model.clear()

        assert model._columns == []
        assert model._rows == []
        assert model._display_columns == []
        assert not model._is_loading
        assert model._loading_message == ""

    def test_table_contents_model_show_loading(self):
        """Test showing loading state in TableContentsModel."""
        model = TableContentsModel()

        model.show_loading("Loading table contents...")

        assert model._is_loading
        assert model._loading_message == "Loading table contents..."
        assert model._columns == []
        assert model._rows == []

    def test_table_contents_model_hide_loading(self):
        """Test hiding loading state in TableContentsModel."""
        model = TableContentsModel()

        # Show loading first
        model.show_loading("Loading...")
        assert model._is_loading

        # Hide loading
        model.hide_loading()
        assert not model._is_loading
        assert model._loading_message == ""

    def test_table_contents_model_row_count(self):
        """Test row count functionality."""
        model = TableContentsModel()

        # Empty model
        assert model.rowCount() == 0

        # Set some content
        model.set_contents(["col1"], [{"col1": "val1"}, {"col1": "val2"}])
        assert model.rowCount() == 2

        # Loading state
        model.show_loading()
        assert model.rowCount() == 1  # Should show 1 placeholder row

    def test_table_contents_model_column_count(self):
        """Test column count functionality."""
        model = TableContentsModel()

        # Empty model
        assert model.columnCount() == 0

        # Set some content
        model.set_contents(["col1", "col2", "col3"], [])
        assert model.columnCount() == 3

        # Loading state
        model.show_loading()
        assert model.columnCount() == 1  # Should show 1 placeholder column

    def test_table_contents_model_data(self):
        """Test data retrieval functionality."""
        model = TableContentsModel()

        # Set some content
        columns = ["id", "name"]
        rows = [{"id": 1, "name": "John"}, {"id": 2, "name": "Jane"}]
        model.set_contents(columns, rows)

        # Test valid data retrieval
        index = model.index(0, 0)  # First row, first column
        assert model.data(index, Qt.DisplayRole) == "1"

        index = model.index(1, 1)  # Second row, second column
        assert model.data(index, Qt.DisplayRole) == "Jane"

        # Test invalid index
        invalid_index = model.index(10, 10)  # Out of bounds
        assert model.data(invalid_index, Qt.DisplayRole) is None

    def test_table_contents_model_data_loading_state(self):
        """Test data retrieval during loading state."""
        model = TableContentsModel()

        # Show loading
        model.show_loading("Loading data...")

        # Test loading message data
        index = model.index(0, 0)  # Only row/column during loading
        assert model.data(index, Qt.DisplayRole) == "Loading data..."

        # Test alignment during loading
        assert model.data(index, Qt.TextAlignmentRole) == Qt.AlignCenter

        # Test foreground color during loading
        foreground = model.data(index, Qt.ForegroundRole)
        assert foreground is not None

    def test_table_contents_model_header_data(self):
        """Test header data functionality."""
        model = TableContentsModel()

        # Set some content
        columns = ["id", "name", "email"]
        rows = [{"id": 1, "name": "John", "email": "john@example.com"}]
        model.set_contents(columns, rows)

        # Test header data
        header_index = model.index(0, 0)  # Not used, but needed for method signature
        assert model.headerData(0, Qt.Horizontal, Qt.DisplayRole) == "id"
        assert model.headerData(1, Qt.Horizontal, Qt.DisplayRole) == "name"
        assert model.headerData(2, Qt.Horizontal, Qt.DisplayRole) == "email"

        # Test invalid section
        assert model.headerData(10, Qt.Horizontal, Qt.DisplayRole) is None

    def test_table_contents_model_header_data_loading_state(self):
        """Test header data during loading state."""
        model = TableContentsModel()

        # Show loading
        model.show_loading()

        # Should return None for headers during loading
        assert model.headerData(0, Qt.Horizontal, Qt.DisplayRole) is None

    def test_table_contents_model_set_header_display_mode(self):
        """Test setting header display mode."""
        model = TableContentsModel()

        # Set some content
        columns = ["id", "name", "email"]
        rows = [{"id": 1, "name": "John", "email": "john@example.com"}]
        model.set_contents(columns, rows)

        # Create column metadata
        column_meta = [
            ColumnInfo(
                schema="TEST",
                table="USERS",
                name="id",
                typename="INTEGER",
                length=10,
                scale=0,
                nulls="N",
                remarks="User ID",
            ),
            ColumnInfo(
                schema="TEST",
                table="USERS",
                name="name",
                typename="VARCHAR",
                length=50,
                scale=0,
                nulls="Y",
                remarks="User name",
            ),
            ColumnInfo(
                schema="TEST",
                table="USERS",
                name="email",
                typename="VARCHAR",
                length=100,
                scale=0,
                nulls="Y",
                remarks="User email",
            ),
        ]

        # Test name mode (default)
        model.set_header_display_mode("name", column_meta)
        assert model._display_columns == ["id", "name", "email"]

        # Test description mode
        model.set_header_display_mode("description", column_meta)
        assert model._display_columns == ["User ID", "User name", "User email"]

        # Test fallback to name when description not available
        column_meta_no_desc = [
            ColumnInfo(
                schema="TEST", table="USERS", name="id", typename="INTEGER", length=10, scale=0, nulls="N", remarks=""
            ),
            ColumnInfo(
                schema="TEST",
                table="USERS",
                name="name",
                typename="VARCHAR",
                length=50,
                scale=0,
                nulls="Y",
                remarks=None,
            ),
        ]
        model.set_contents(["id", "name"], [])
        model.set_header_display_mode("description", column_meta_no_desc)
        assert model._display_columns == ["id", "name"]  # Should fall back to names

    def test_table_contents_model_incremental_update(self):
        """Test incremental update functionality."""
        model = TableContentsModel()

        # Initial content
        model.set_contents(["id", "name"], [{"id": 1, "name": "John"}])
        assert len(model._rows) == 1

        # Incremental update - should append
        new_rows = [{"id": 2, "name": "Jane"}, {"id": 3, "name": "Bob"}]
        model.set_contents(
            ["id", "name"], [{"id": 1, "name": "John"}, {"id": 2, "name": "Jane"}, {"id": 3, "name": "Bob"}]
        )

        assert len(model._rows) == 3
        assert model._rows[1]["name"] == "Jane"
        assert model._rows[2]["name"] == "Bob"

    def test_table_contents_model_empty_content(self):
        """Test handling of empty content."""
        model = TableContentsModel()

        # Set empty content
        model.set_contents([], [])
        assert model._columns == []
        assert model._rows == []
        assert model.rowCount() == 0
        assert model.columnCount() == 0

    def test_table_contents_model_none_content(self):
        """Test handling of None content."""
        model = TableContentsModel()

        # Set None content (should handle gracefully)
        model.set_contents(None, None)
        assert model._columns == []
        assert model._rows == []

        # Should still work
        assert model.rowCount() == 0
        assert model.columnCount() == 0
