import os
import sys
from types import SimpleNamespace

# Ensure 'src' package dir is importable during tests when running in CI/env
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from dbutils.db_browser import TableInfo
from dbutils.gui.qt_app import QtDBBrowser


class FakeComboBox:
    def __init__(self):
        self.items = []  # list of (text, data)
        self._blocked = False
        self._current = 0

    def blockSignals(self, v: bool):
        self._blocked = bool(v)

    def clear(self):
        self.items.clear()

    def addItem(self, text, userData=None):
        self.items.append({"text": text, "data": userData})

    def findData(self, val):
        for i, it in enumerate(self.items):
            if it["data"] == val:
                return i
        return -1

    def setCurrentIndex(self, idx: int):
        self._current = int(idx)

    def currentIndex(self):
        return self._current

    def itemData(self, idx: int):
        if 0 <= idx < len(self.items):
            return self.items[idx]["data"]
        return None


def test_update_schema_combo_and_restore_selection():
    # Arrange fake db browser-like object
    obj = SimpleNamespace()
    obj.schema_combo = FakeComboBox()
    # Two schemas A and B, with A containing two tables
    obj.tables = [
        TableInfo(schema="A", name="t1", remarks=""),
        TableInfo(schema="B", name="t2", remarks=""),
        TableInfo(schema="A", name="t3", remarks=""),
    ]
    obj.all_schemas = ["A", "B"]
    obj.schema_filter = "A"

    # Act - call the unbound method with our fake object
    QtDBBrowser.update_schema_combo(obj)

    # Assert - combo contains All Schemas plus two schemas
    assert len(obj.schema_combo.items) == 3
    assert obj.schema_combo.items[0]["text"] == "All Schemas"
    # Index 1 is A
    assert obj.schema_combo.items[1]["text"].startswith("A (")
    assert obj.schema_combo.items[1]["data"] == "A"
    # Index 2 is B
    assert obj.schema_combo.items[2]["text"].startswith("B (")
    assert obj.schema_combo.items[2]["data"] == "B"

    # Current index should have been restored to the 'A' entry
    assert obj.schema_combo._current == obj.schema_combo.findData("A")


def test_on_schema_changed_uses_itemdata():
    obj = SimpleNamespace()
    obj.schema_combo = FakeComboBox()
    # Build a few items
    obj.schema_combo.addItem("All Schemas", None)
    obj.schema_combo.addItem("X (1 table)", "X")
    obj.schema_combo.addItem("Y (2 tables)", "Y")

    # Simulate selecting 'Y'
    obj.schema_combo.setCurrentIndex(2)
    obj.schema_filter = None
    # The handler calls load_data() - provide a no-op for tests
    obj.load_data = lambda: None

    # Call handler
    QtDBBrowser.on_schema_changed(obj, "")

    assert obj.schema_filter == "Y"

    # Simulate selecting All Schemas
    obj.schema_combo.setCurrentIndex(0)
    QtDBBrowser.on_schema_changed(obj, "All Schemas")
    assert obj.schema_filter is None


def test_update_schema_combo_uses_provided_counts():
    obj = SimpleNamespace()
    obj.schema_combo = FakeComboBox()
    obj.tables = []  # no table data available
    # all_schemas provided as dicts with counts (streaming loader payload)
    obj.all_schemas = [{"name": "SCHEMA_X", "count": 5}, {"name": "SCHEMA_Y", "count": 1}]
    obj.schema_filter = None

    # Call update
    QtDBBrowser.update_schema_combo(obj)

    # Expect the labels to include counts pulled from payload
    assert obj.schema_combo.items[1]["text"] == "SCHEMA_X (5 tables)"
    assert obj.schema_combo.items[2]["text"] == "SCHEMA_Y (1 table)"


def test_zero_count_is_omitted():
    obj = SimpleNamespace()
    obj.schema_combo = FakeComboBox()
    obj.tables = []
    obj.all_schemas = [{"name": "EMPTY_SCHEMA", "count": 0}]
    obj.schema_filter = None

    QtDBBrowser.update_schema_combo(obj)

    # Should not show '(0 tables)'
    assert obj.schema_combo.items[1]["text"] == "EMPTY_SCHEMA"


def test_update_schema_combo_with_strings_and_no_tables_shows_no_zero():
    obj = SimpleNamespace()
    obj.schema_combo = FakeComboBox()
    # No tables loaded yet
    obj.tables = []
    obj.all_schemas = ["A", "B"]
    obj.schema_filter = None

    QtDBBrowser.update_schema_combo(obj)

    # Should show only the name (no '0 tables')
    assert obj.schema_combo.items[1]["text"] == "A"
    assert obj.schema_combo.items[2]["text"] == "B"
