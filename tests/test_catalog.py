import importlib
from pathlib import Path

import pytest


from dbutils import catalog


def test_get_tables_mock():
    tables = catalog.get_tables(mock=True)
    assert isinstance(tables, list)
    assert len(tables) >= 1
    assert all('TABNAME' in t for t in tables)


def test_get_columns_mock():
    cols = catalog.get_columns(mock=True)
    assert isinstance(cols, list)
    assert len(cols) >= 1
    assert all('COLNAME' in c for c in cols)


def test_get_primary_keys_mock():
    pk = catalog.get_primary_keys(mock=True)
    assert isinstance(pk, list)
    assert any(d.get('CONSTRAINT_NAME') for d in pk)


def test_get_indexes_mock():
    idx = catalog.get_indexes(mock=True)
    assert isinstance(idx, list)
    assert any('INDEX_NAME' in i for i in idx)


def test_get_table_sizes_mock():
    ts = catalog.get_table_sizes(mock=True)
    assert isinstance(ts, list)
    assert any('ROWCOUNT' in t for t in ts)


def test_foreign_keys_mock():
    fk = catalog.get_foreign_keys(mock=True)
    assert isinstance(fk, list)
    assert fk == []


def test_get_all_tables_and_columns_calls_db_browser(monkeypatch):
    fake_called = {'called': False}

    def fake_browser(schema_filter, use_mock, use_cache, limit, offset):
        fake_called['called'] = True
        return ([{'TABNAME': 'A'}], [{'COLNAME': 'C'}])

    import dbutils.db_browser as dbb
    monkeypatch.setattr(dbb, 'get_all_tables_and_columns', fake_browser, raising=True)

    # Re-import may not be necessary but call the wrapper function
    res = catalog.get_all_tables_and_columns('TEST', use_mock=True)
    assert fake_called['called']
    assert isinstance(res, tuple)
    assert len(res) == 2


def test_get_tables_queries_query_runner(monkeypatch):
    called = {'sql': None}

    def fake_q(sql):
        called['sql'] = sql
        return [{'TABNAME': 'X'}]

    monkeypatch.setattr(catalog, 'query_runner', fake_q, raising=True)
    res = catalog.get_tables(schema='MYSCHEMA', mock=False)
    assert res and isinstance(res, list)
    assert "TABLE_SCHEMA = 'MYSCHEMA'" in called['sql']


def test_get_columns_queries_query_runner(monkeypatch):
    called = {'sql': None}

    def fake_q(sql):
        called['sql'] = sql
        return [{'COLNAME': 'C'}]

    monkeypatch.setattr(catalog, 'query_runner', fake_q, raising=True)
    res = catalog.get_columns(schema='MYSCHEMA', table='USERS', mock=False)
    assert res and isinstance(res, list)
    assert "TABLE_SCHEMA = 'MYSCHEMA'" in called['sql']
    assert "TABLE_NAME = 'USERS'" in called['sql']
