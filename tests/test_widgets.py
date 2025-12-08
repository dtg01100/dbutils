from PySide6.QtWidgets import QWidget

from dbutils.db_browser import TableInfo
from dbutils.gui.widgets.enhanced_widgets import (
    BusyOverlay,
    CollapsiblePanel,
    EnhancedTableItem,
    ProgressBar,
    SearchHighlightWidget,
    StatusIndicator,
)


def test_status_indicator_searching(qapp):
    s = StatusIndicator()
    s.set_searching(True)
    assert s.status_label.text() == "🔄"
    s.animate_progress()
    s.set_searching(False)
    assert s.status_label.text() == "✅"


def test_enhanced_table_item(qapp):
    t = TableInfo(schema="TEST", name="USERS", remarks="")
    item = EnhancedTableItem(t, match_type="exact")
    assert "USERS" in item.table_info.name

    # hover events
    item.enterEvent(None)
    item.leaveEvent(None)


def test_search_highlight_and_progress(qapp):
    sh = SearchHighlightWidget()
    sh.set_search_text("Hello")
    sh.clear_search()
    assert sh.search_text == ""

    p = ProgressBar()
    p.set_maximum(200)
    p.set_value(50)
    assert p.value == 50
    p.set_value(9999)
    assert p.value == p.maximum


def test_collapsible_panel(qapp):
    panel = CollapsiblePanel("Title", collapsed=True)
    assert panel.is_collapsed
    panel.toggle_collapse()
    assert not panel.is_collapsed
    # Add widget
    panel.add_widget(QWidget())


def test_busy_overlay(qapp):
    overlay = BusyOverlay(None, message="Loading")
    overlay.set_message("Hi")
    overlay.show_with_message("Test")
    overlay._tick()
    overlay.hideEvent(None)

    # paintEvent triggered by update; call paintEvent with a dummy event
    class DummyEvent:
        pass

    overlay.paintEvent(DummyEvent())
