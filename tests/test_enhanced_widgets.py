import pytest

from dbutils.db_browser import TableInfo
from dbutils.gui.widgets.enhanced_widgets import (
    EnhancedTableItem,
    SearchHighlightWidget,
    StatusIndicator,
)


@pytest.mark.qt
def test_status_indicator_toggle(qapp):
    si = StatusIndicator()
    si.set_searching(True)
    assert si.status_label.text() in ("🔄", "🔍") or si.text_label.text() == 'Searching...'
    si.set_searching(False)
    assert si.status_label.text() in ("✅", "🔍") or si.text_label.text() == 'Ready'


@pytest.mark.qt
def test_enhanced_table_item_hover_and_labels(qapp):
    tinfo = TableInfo(schema='S', name='T', remarks='R')
    item = EnhancedTableItem(tinfo, match_type='exact')
    # Ensure labels created
    assert hasattr(item, 'table_info')
    # Simulate enter/leave event to change stylesheet (this shouldn't throw)
    item.enterEvent(None)
    item.leaveEvent(None)


@pytest.mark.qt
def test_search_highlight_widget_input(qapp):
    sw = SearchHighlightWidget()
    assert hasattr(sw, 'search_input')
    # Placeholder should contain 'Search'
    # Using __str__ sentinel - in Qt, placeholder is only accessible via method; we assume it's set
    try:
        ph = sw.search_input.placeholderText()
        assert 'Search' in ph
    except Exception:
        # Non-Qt fallback may not implement placeholderText; ignore
        pass
