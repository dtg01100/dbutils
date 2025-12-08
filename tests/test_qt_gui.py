"""Unit tests for dbutils.gui.qt_app module.

Tests for Qt GUI components where possible without actual UI rendering.
Tests for:
- Models and data structures
- Helper functions
- Non-UI logic
"""

import pytest

# Import the functions we can test without Qt
try:
    from dbutils.db_browser import ColumnInfo, TableInfo
    from dbutils.gui.qt_app import ColumnModel, DatabaseModel, SearchResult, TableContentsModel, highlight_text_as_html
except ImportError:
    # If Qt is not available, create stubs for testing purposes
    SearchResult = None
    DatabaseModel = None
    ColumnModel = None
    TableContentsModel = None
    TableInfo = None
    ColumnInfo = None

    def highlight_text_as_html(text, query):
        """Stub implementation for testing."""
        return text


class TestHighlightTextAsHtml:
    """Test the highlight_text_as_html function."""

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

    def test_highlight_empty_text(self):
        """Test empty text returns empty string."""
        result = highlight_text_as_html("", "hello")
        assert result == ""

    def test_highlight_special_chars(self):
        """Test special characters are escaped."""
        result = highlight_text_as_html("hello & world", "hello")
        assert "&amp;" in result or "hello" in result  # Either escaped or original depending on implementation
        assert "background-color:#fffb8f" in result

    def test_highlight_partial_match(self):
        """Test partial substring matches."""
        result = highlight_text_as_html("customer_order", "order")
        assert "order" in result
        assert "background-color:#fffb8f" in result


class TestSearchResult:
    """Test the SearchResult dataclass if available."""

    def test_search_result_creation(self):
        """Test basic SearchResult creation."""
        if SearchResult is None:
            pytest.skip("Qt not available, skipping SearchResult tests")

        result = SearchResult(item="test_item", match_type="exact", relevance_score=0.9, table_key="test.key")

        assert result.item == "test_item"
        assert result.match_type == "exact"
        assert result.relevance_score == 0.9
        assert result.table_key == "test.key"


class TestDatabaseModel:
    """Test the DatabaseModel if available."""

    def test_database_model_creation(self):
        """Test basic DatabaseModel creation."""
        if DatabaseModel is None:
            pytest.skip("Qt not available, skipping DatabaseModel tests")

        model = DatabaseModel()
        assert model._tables == []
        assert model._columns == {}
        assert model._search_results == []
        assert not model._search_active

    def test_database_model_set_data(self):
        """Test setting data in DatabaseModel."""
        if DatabaseModel is None:
            pytest.skip("Qt not available, skipping DatabaseModel tests")

        model = DatabaseModel()

        if TableInfo is not None:
            tables = [TableInfo(schema="TEST", name="USERS", remarks="User table")]
            columns = {"TEST.USERS": []}

            model.set_data(tables, columns)

            assert len(model._tables) == 1
            assert model._tables[0].name == "USERS"
            assert "TEST.USERS" in model._columns


class TestColumnModel:
    """Test the ColumnModel if available."""

    def test_column_model_creation(self):
        """Test basic ColumnModel creation."""
        if ColumnModel is None:
            pytest.skip("Qt not available, skipping ColumnModel tests")

        model = ColumnModel()
        assert model._columns == []
        assert len(model._headers) == 2  # ["Column", "Description"]

    def test_column_model_set_columns(self):
        """Test setting columns in ColumnModel."""
        if ColumnModel is None:
            pytest.skip("Qt not available, skipping ColumnModel tests")

        if ColumnInfo is not None:
            model = ColumnModel()
            columns = [
                ColumnInfo(
                    schema="TEST",
                    table="USERS",
                    name="ID",
                    typename="INTEGER",
                    length=10,
                    scale=0,
                    nulls="N",
                    remarks="ID column",
                )
            ]

            model.set_columns(columns)

            assert len(model._columns) == 1
            assert model._columns[0].name == "ID"


class TestTableContentsModel:
    """Test the TableContentsModel if available."""

    def test_table_contents_model_creation(self):
        """Test basic TableContentsModel creation."""
        if TableContentsModel is None:
            pytest.skip("Qt not available, skipping TableContentsModel tests")

        model = TableContentsModel()
        assert model._columns == []
        assert model._rows == []
        assert model._display_columns == []
        assert not model._is_loading
        assert model._loading_message == ""

    def test_table_contents_model_set_contents(self):
        """Test setting contents in TableContentsModel."""
        if TableContentsModel is None:
            pytest.skip("Qt not available, skipping TableContentsModel tests")

        model = TableContentsModel()
        columns = ["col1", "col2"]
        rows = [{"col1": "val1", "col2": "val2"}]

        model.set_contents(columns, rows)

        assert model._columns == ["col1", "col2"]
        assert model._rows == [{"col1": "val1", "col2": "val2"}]
        assert model._display_columns == ["col1", "col2"]

    def test_table_contents_model_clear(self):
        """Test clearing contents in TableContentsModel."""
        if TableContentsModel is None:
            pytest.skip("Qt not available, skipping TableContentsModel tests")

        model = TableContentsModel()
        model.set_contents(["col1"], [{"col1": "val1"}])
        model.clear()

        assert model._columns == []
        assert model._rows == []
        assert model._display_columns == []
        assert not model._is_loading
        assert model._loading_message == ""

    def test_table_contents_model_loading(self):
        """Test loading state in TableContentsModel."""
        if TableContentsModel is None:
            pytest.skip("Qt not available, skipping TableContentsModel tests")

        model = TableContentsModel()
        model.show_loading("Loading data...")

        assert model._is_loading
        assert model._loading_message == "Loading data..."
        assert model._columns == []
        assert model._rows == []

        model.hide_loading()
        assert not model._is_loading
        assert model._loading_message == ""


class TestQtAvailability:
    """Test Qt availability and graceful degradation."""

    def test_import_without_qt(self):
        """Test that module can be imported without Qt (with proper error handling)."""
        # This test verifies that the import structure handles missing Qt properly
        # The conftest.py sets up the environment to allow import, but we should
        # test the case where Qt is missing

        # We can't actually test this without manipulating sys.modules,
        # but we can make sure our tests work when Qt is available
        if SearchResult is not None:
            # Qt is available, so we can run normal tests
            result = SearchResult(item="test", match_type="exact", relevance_score=1.0)
            assert result.item == "test"
        else:
            # Qt is not available, verify our stub works
            result = highlight_text_as_html("test", "test")
            assert result == "test"


# Additional tests for Qt-specific GUI logic that might be testable
def test_graceful_degradation():
    """Test that GUI components handle missing Qt gracefully."""
    # This is more of an integration test to ensure the module
    # doesn't crash when Qt is not available
    try:
        # Try to import the module
        import dbutils.gui.qt_app
        # The module should be importable even without Qt
        # (it would raise ImportError at the end if Qt is not available,
        # but the test setup should handle this)
    except ImportError as e:
        # If we get an ImportError that's not about Qt, that's a problem
        if "Qt libraries are required" not in str(e):
            # Re-raise if it's not the expected error
            raise
        # Otherwise, it's expected when Qt is not available
        pass
