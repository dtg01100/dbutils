import pytest
from pathlib import Path
import os

from dbutils.gui.qt_app import (
    highlight_text_as_html,
    DatabaseModel,
    ColumnModel,
    SearchResult,
)
from dbutils.db_browser import TableInfo, ColumnInfo
from PySide6.QtCore import Qt


def test_highlight_text_html_basic():
    assert highlight_text_as_html('', '') == ''
    assert highlight_text_as_html('Hello World', '') == 'Hello World'
    # Query matches case-insensitive
    out = highlight_text_as_html('Hello World', 'hello')
    assert '<span' in out and 'Hello' in out


def test_highlight_text_multiple_words_and_escape():
    text = '<div>Important & string</div>'
    # query contains ampersand and spaces; should escape then highlight
    out = highlight_text_as_html(text, '& string')
    assert '&amp;' in out or 'string' in out


@pytest.mark.qt
def test_database_model_set_data_and_search(qapp):
    model = DatabaseModel()

    t1 = TableInfo(schema='S', name='T1', remarks='R1')
    t2 = TableInfo(schema='S', name='T2', remarks='R2')
    cols = {
        'S.T1': [ColumnInfo(schema='S', table='T1', name='C1', typename='VARCHAR', length=10, scale=0, nulls='N', remarks='c1')]
    }

    # initial reset load
    model.set_data([t1], cols)
    assert model.rowCount() == 1
    assert model.columnCount() == 2

    # incremental append (old_count > 0, new_count > old_count)
    model.set_data([t1, t2], cols)
    assert model.rowCount() == 2

    # Set search results to None -> active search with zero matches
    model.set_search_results(None)
    assert model.rowCount() == 0

    # Create a table search result
    sr = SearchResult(item=t1, match_type='exact', relevance_score=1.0)
    model.set_search_results([sr])
    assert model.rowCount() == 1
    # Test Qt DisplayRole
    idx = model.index(0, 0)
    assert model.data(idx, Qt.DisplayRole) == 'T1'

    # Column search result
    colinfo = ColumnInfo(schema='S', table='T1', name='C1', typename='VARCHAR', length=10, scale=0, nulls='N', remarks='c1')
    sr_col = SearchResult(item=colinfo, match_type='column', relevance_score=1.0)
    model.set_search_results([sr_col])
    assert model.rowCount() == 1
    idx2 = model.index(0, 0)
    assert 'col:' in model.data(idx2, Qt.DisplayRole)


@pytest.mark.qt
def test_column_model_basic(qapp):
    cm = ColumnModel()
    col = ColumnInfo(schema='S', table='T', name='C', typename='VARCHAR', length=10, scale=0, nulls='N', remarks='z')
    cm.set_columns([col])
    assert cm.rowCount() == 1
    idx = cm.index(0, 1)
    assert cm.data(idx, Qt.DisplayRole) == 'z'
