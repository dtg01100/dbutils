import os
import sys

# Ensure src is on path when running tests without installing package
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from dbutils.db_browser import ColumnInfo, TableInfo  # noqa: E402
from dbutils.gui.qt_app import DatabaseModel, QtDBBrowser, SearchResult  # noqa: E402


def make_table(schema: str, name: str, remarks: str = ""):
    return TableInfo(schema=schema, name=name, remarks=remarks)


def make_column(
    schema: str,
    table: str,
    name: str,
    typename: str = "VARCHAR",
    remarks: str = "",
) -> ColumnInfo:
    return ColumnInfo(
        schema=schema,
        table=table,
        name=name,
        typename=typename,
        length=None,
        scale=None,
        nulls="N",
        remarks=remarks,
    )


def test_database_model_set_data_and_rowcount():
    m = DatabaseModel()
    tables = [make_table("S", "T1"), make_table("S", "T2")]
    cols = {"S.T1": [make_column("S", "T1", "c1"), make_column("S", "T1", "c2")], "S.T2": []}

    m.set_data(tables, cols)
    assert m.rowCount() == 2


def test_database_model_search_results_override_rows():
    m = DatabaseModel()
    tables = [make_table("S", "T1")]
    cols = {}
    m.set_data(tables, cols)
    # search results override rows
    sr = SearchResult(item=tables[0], match_type="exact", relevance_score=1.0, table_key="S.T1")
    m.set_search_results([sr])
    assert m.rowCount() == 1


def test_database_model_active_empty_search_hides_rows():
    m = DatabaseModel()
    tables = [make_table("S", "T1"), make_table("S", "T2")]
    cols = {"S.T1": [], "S.T2": []}

    m.set_data(tables, cols)

    # Active search with no matches should show zero rows when using the
    # sentinel None to indicate an active search that found no results.
    m.set_search_results(None)
    assert m.rowCount() == 0


def test_database_model_clear_search_shows_all_rows():
    m = DatabaseModel()
    tables = [make_table("S", "T1"), make_table("S", "T2")]
    cols = {"S.T1": [], "S.T2": []}

    m.set_data(tables, cols)

    # Clearing search with an empty list should show the full table list
    m.set_search_results([])
    assert m.rowCount() == 2


def test_database_model_shows_aggregated_table_for_column_matches():
    """When a TableInfo SearchResult is created as an aggregate of column
    matches (match_type 'column'), the model should show the table and
    annotate the description with the number of matching columns."""
    from dbutils.gui.qt_app import Qt, SearchResult

    m = DatabaseModel()
    t1 = make_table("S", "T1", remarks="User table")
    tables = [t1]
    cols = {"S.T1": [make_column("S", "T1", "c1"), make_column("S", "T1", "c2")]}

    m.set_data(tables, cols)

    # Aggregate entry indicating two matching columns
    agg = SearchResult(item=t1, match_type="column", relevance_score=2.0, table_key="S.T1")
    m.set_search_results([agg])

    assert m.rowCount() == 1

    # Create a tiny fake index object compatible with DatabaseModel.data
    class _Idx:
        def __init__(self, r, c):
            self._r = r
            self._c = c

        def isValid(self):
            return True

        def row(self):
            return self._r

        def column(self):
            return self._c

    desc = m.data(_Idx(0, 1), role=Qt.DisplayRole)
    assert "matching column" in (desc or ""), f"expected matching column hint in '{desc}'"


def test_on_search_results_synthesizes_aggregates_for_column_only_results():
    """QtDBBrowser.on_search_results should synthesize table-level aggregates
    when interim streaming results contain only ColumnInfo items so tables
    with matching columns appear as indirect matches.
    """
    # Local test: use SimpleNamespace and top-level imports

    # Prepare fake browser object with current dataset
    from types import SimpleNamespace

    obj = SimpleNamespace()
    t1 = make_table("S", "T1")
    t2 = make_table("S", "T2")
    obj.tables = [t1, t2]
    obj.table_columns = {
        "S.T1": [make_column("S", "T1", "c1"), make_column("S", "T1", "c2")],
        "S.T2": [make_column("S", "T2", "c3")],
    }
    obj.tables_model = DatabaseModel()
    # Ensure model holds the data so it can find table objects by key
    obj.tables_model.set_data(obj.tables, obj.table_columns)

    # Streaming/interim results - only columns (no aggregated table entries)
    col1 = obj.table_columns["S.T1"][0]
    col2 = obj.table_columns["S.T1"][1]
    col3 = obj.table_columns["S.T2"][0]

    results = [
        SearchResult(item=col1, match_type="exact", relevance_score=1.0, table_key="S.T1"),
        SearchResult(item=col2, match_type="exact", relevance_score=1.0, table_key="S.T1"),
        SearchResult(item=col3, match_type="exact", relevance_score=1.0, table_key="S.T2"),
    ]

    # Setup search state and lightweight progress/status attributes used by handler
    obj.search_mode = "columns"
    obj.search_query = "c"
    obj.show_non_matching = True
    obj.search_progress = SimpleNamespace(setValue=lambda v: None)
    obj.status_label = SimpleNamespace(setText=lambda t: None)

    # Call unbound handler (cast to bypass static typing in tests)
    from typing import cast

    QtDBBrowser.on_search_results(cast(QtDBBrowser, obj), results)

    # The model should have aggregated table entries first (T1 with count=2, then T2)
    sr_list = obj.tables_model._search_results
    assert len(sr_list) >= 2
    agg1 = sr_list[0]
    agg2 = sr_list[1]
    assert isinstance(agg1.item, type(t1)) and agg1.table_key == "S.T1"
    assert int(agg1.relevance_score) == 2
    assert isinstance(agg2.item, type(t2)) and agg2.table_key == "S.T2"


def test_on_search_results_with_empty_columns_hides_rows_when_non_matching_disabled():
    # Local test: SimpleNamespace and QtDBBrowser imported at top

    from types import SimpleNamespace

    obj = SimpleNamespace()
    t1 = make_table("S", "T1")
    t2 = make_table("S", "T2")
    obj.tables = [t1, t2]
    obj.table_columns = {"S.T1": [], "S.T2": []}
    obj.tables_model = DatabaseModel()
    obj.tables_model.set_data(obj.tables, obj.table_columns)

    obj.search_mode = "columns"
    obj.search_query = "no-match"
    obj.show_non_matching = False
    obj.search_progress = SimpleNamespace(setValue=lambda v: None)
    obj.status_label = SimpleNamespace(setText=lambda t: None)

    from typing import cast

    QtDBBrowser.on_search_results(cast(QtDBBrowser, obj), [])

    # Active-empty sentinel should cause model to present zero rows
    assert obj.tables_model.rowCount() == 0


def test_table_contents_model_basic():
    from dbutils.gui.qt_app import Qt, TableContentsModel

    m = TableContentsModel()
    cols = ["id", "name"]
    rows = [{"id": 1, "name": "alice"}, {"id": 2, "name": "bob"}]

    m.set_contents(cols, rows)
    assert m.rowCount() == 2
    assert m.columnCount() == 2

    class _Idx:
        def __init__(self, r, c):
            self._r = r
            self._c = c

        def isValid(self):
            return True

        def row(self):
            return self._r

        def column(self):
            return self._c

    # Validate display formatting
    assert m.data(_Idx(0, 0), role=Qt.DisplayRole) == "1"
    assert m.data(_Idx(1, 1), role=Qt.DisplayRole) == "bob"

    def test_table_contents_model_header_display_modes():
        """Header labels should toggle between names and descriptions when requested."""
        from dbutils.db_browser import ColumnInfo
        from dbutils.gui.qt_app import Qt, TableContentsModel

        m = TableContentsModel()
        cols = ["id", "name"]
        rows = [{"id": 1, "name": "alice"}]
        m.set_contents(cols, rows)

        # Default shows names
        assert m.headerData(0, Qt.Horizontal, role=Qt.DisplayRole) == "id"

        # Toggle to descriptions using metadata
        meta = [
            ColumnInfo(
                schema="S",
                table="T1",
                name="id",
                typename="INTEGER",
                length=None,
                scale=None,
                nulls="N",
                remarks="Identifier",
            ),
            ColumnInfo(
                schema="S",
                table="T1",
                name="name",
                typename="VARCHAR",
                length=None,
                scale=None,
                nulls="N",
                remarks="Full Name",
            ),
        ]

        m.set_header_display_mode("description", meta)
        assert m.headerData(0, Qt.Horizontal, role=Qt.DisplayRole) == "Identifier"
        assert m.headerData(1, Qt.Horizontal, role=Qt.DisplayRole) == "Full Name"


def test_load_table_contents_uses_query_runner(monkeypatch):
    # Use a simple fake object that mimics necessary attributes
    from types import SimpleNamespace

    from dbutils.db_browser import TableInfo
    from dbutils.gui.qt_app import QtDBBrowser, TableContentsModel

    t = TableInfo(schema="S", name="T1", remarks="r")
    obj = SimpleNamespace()
    obj.tables = [t]
    obj.table_columns = {"S.T1": []}
    obj.contents_model = TableContentsModel()

    # Patch query_runner to return sample rows
    import dbutils.db_browser as dbb

    def fake_runner(sql):
        return [{"id": 1, "name": "one"}, {"id": 2, "name": "two"}]

    monkeypatch.setattr(dbb, "query_runner", fake_runner)

    # Call the unbound method on our simple obj
    QtDBBrowser.load_table_contents(obj, "S.T1", limit=2)

    assert obj.contents_model.rowCount() == 2
    assert obj.contents_model.columnCount() == 2


def test_table_contents_worker_builds_string_filter_sql(monkeypatch):
    from dbutils.gui.qt_app import TableContentsWorker

    captured = {}

    def fake_query_runner(sql):
        captured["sql"] = sql
        return [{"id": 1, "name": "o'reilly"}]

    monkeypatch.setattr("dbutils.db_browser.query_runner", fake_query_runner)

    # Patch catalog metadata so worker treats 'name' as string
    def fake_get_columns(schema, table):
        return [{"COLNAME": "id", "TYPENAME": "INTEGER"}, {"COLNAME": "name", "TYPENAME": "VARCHAR(100)"}]

    monkeypatch.setattr("dbutils.catalog.get_columns", fake_get_columns)

    w = TableContentsWorker()
    w.perform_fetch("S", "T1", limit=10, column_filter="name", value="o'reilly")

    assert "sql" in captured
    assert "WHERE name = 'o''reilly'" in captured["sql"]
    assert "FETCH FIRST 10 ROWS ONLY" in captured["sql"]


def test_table_contents_worker_builds_numeric_filter_sql(monkeypatch):
    from dbutils.gui.qt_app import TableContentsWorker

    captured = {}

    def fake_query_runner(sql):
        captured["sql"] = sql
        return [{"id": 42, "name": "hey"}]

    monkeypatch.setattr("dbutils.db_browser.query_runner", fake_query_runner)

    def fake_get_columns(schema, table):
        return [{"COLNAME": "id", "TYPENAME": "INTEGER"}, {"COLNAME": "name", "TYPENAME": "VARCHAR(100)"}]

    monkeypatch.setattr("dbutils.catalog.get_columns", fake_get_columns)

    w = TableContentsWorker()
    w.perform_fetch("S", "T1", limit=5, column_filter="id", value="42")

    assert "sql" in captured
    assert "WHERE id = 42" in captured["sql"]
    assert "FETCH FIRST 5 ROWS ONLY" in captured["sql"]


def test_table_contents_worker_builds_offset_sql(monkeypatch):
    from dbutils.gui.qt_app import TableContentsWorker

    captured = {}

    def fake_query_runner(sql):
        captured["sql"] = sql
        return [{"id": 100, "name": "last"}]

    monkeypatch.setattr("dbutils.db_browser.query_runner", fake_query_runner)

    w = TableContentsWorker()
    # Request with an offset - SQL should include OFFSET clause
    w.perform_fetch("S", "T1", limit=10, start_offset=50)

    assert "sql" in captured
    assert "OFFSET 50 ROWS" in captured["sql"]
    assert "FETCH FIRST 10 ROWS ONLY" in captured["sql"]
