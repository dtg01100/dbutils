import pytest
from dbutils.catalog import (
    get_tables,
    get_columns,
    get_primary_keys,
    get_indexes,
    get_table_sizes,
    get_foreign_keys,
)


def test_get_tables_mock():
    tables = get_tables(mock=True)
    assert isinstance(tables, list) and len(tables) >= 1
    for t in tables:
        assert 'TABSCHEMA' in t and 'TABNAME' in t


def test_get_columns_mock():
    cols = get_columns(mock=True)
    assert any(c.get('COLNAME') == 'ID' for c in cols)


def test_get_primary_keys_mock():
    pks = get_primary_keys(mock=True)
    assert isinstance(pks, list) and len(pks) >= 1


def test_get_indexes_mock():
    idx = get_indexes(mock=True)
    assert any('INDEX_NAME' in i for i in idx)


def test_get_table_sizes_mock():
    sz = get_table_sizes(mock=True)
    assert isinstance(sz, list) and 'ROWCOUNT' in sz[0]


def test_get_foreign_keys_mock():
    fk = get_foreign_keys(mock=True)
    assert isinstance(fk, list)


def test_catalog_empty_query_monkeypatch(monkeypatch):
    # When query_runner returns empty, functions should return [] gracefully
    monkeypatch.setattr('dbutils.catalog.query_runner', lambda *args, **kwargs: [], raising=True)
    assert get_tables(mock=False) == []
    assert get_columns(mock=False) == []
    assert get_primary_keys(mock=False) == []
    assert get_indexes(mock=False) == []
    assert get_table_sizes(mock=False) == []
    assert get_foreign_keys(mock=False) == []
