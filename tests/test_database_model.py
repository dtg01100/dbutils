import os
import sys

# Ensure src is on path when running tests without installing package
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SRC = os.path.join(ROOT, 'src')
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from dbutils.gui.qt_app import DatabaseModel, SearchResult
from dbutils.db_browser import TableInfo, ColumnInfo


def make_table(schema: str, name: str, remarks: str = ""):
    return TableInfo(schema=schema, name=name, remarks=remarks)


def make_column(schema: str, table: str, name: str, typename: str = "VARCHAR", remarks: str = ""):
    return ColumnInfo(schema=schema, table=table, name=name, typename=typename, length=None, scale=None, nulls='N', remarks=remarks)


def test_database_model_set_data_and_rowcount():
    m = DatabaseModel()
    tables = [make_table('S', 'T1'), make_table('S', 'T2')]
    cols = { 'S.T1': [make_column('S', 'T1', 'c1'), make_column('S', 'T1', 'c2')], 'S.T2': [] }

    m.set_data(tables, cols)
    assert m.rowCount() == 2


def test_database_model_search_results_override_rows():
    m = DatabaseModel()
    tables = [make_table('S', 'T1')]
    cols = {}
    m.set_data(tables, cols)
    # search results override rows
    sr = SearchResult(item=tables[0], match_type='exact', relevance_score=1.0, table_key='S.T1')
    m.set_search_results([sr])
    assert m.rowCount() == 1