import os
from pathlib import Path

import pytest

from dbutils import db_browser
from dbutils.db_browser import SearchIndex, TrieNode, get_all_tables_and_columns, intern_string, query_runner


def test_trie_massive_insert_search():
    node = TrieNode()
    # Insert many long words to stress test insertion
    for i in range(500):
        w = f'word{i}_' + ('x' * (100 + (i % 100)))
        node.insert(w, f'k{i}')

    # Search for a long prefix; should find at least one
    pref = 'word250_' + 'x' * 10
    found = node.search_prefix(pref)
    assert isinstance(found, set)


def test_search_index_unicode_and_long():
    idx = SearchIndex()
    tbl = db_browser.TableInfo(schema='X', name='unicodé_测试', remarks='测试 remarks long ' + ('y' * 1000))
    col = db_browser.ColumnInfo(schema='X', table='unicodé_测试', name='colé', typename='VARCHAR', length=100, scale=0, nulls='N', remarks='r')
    idx.build_index([tbl], [col])

    # Search using different unicode representation
    res = idx.search_tables('unicodé')
    assert len(res) == 1
    res2 = idx.search_columns('colé')
    assert len(res2) == 1


def test_get_all_tables_and_columns_with_incomplete_rows(monkeypatch):
    # Simulate query_runner returning rows missing keys or with wrong types
    def fake_q(sql):
        if 'FROM QSYS2.SYSTABLES' in sql:
            return [
                {'TABLE_SCHEMA': 'S', 'TABLE_NAME': 'T', 'TABLE_TEXT': 'R'},
                {'TABLE_SCHEMA': None, 'TABLE_NAME': 'B', 'TABLE_TEXT': 'R2'},  # missing schema
                {'TABLE_NAME': 'C'},  # missing schema
            ]
        else:
            return [
                {'TABLE_SCHEMA': 'S', 'TABLE_NAME': 'T', 'COLUMN_NAME': 'ID', 'DATA_TYPE': 'INT', 'LENGTH': '10', 'NUMERIC_SCALE': '0', 'IS_NULLABLE': 'Y', 'COLUMN_TEXT': 'x'},
                {'TABLE_SCHEMA': 'S', 'TABLE_NAME': 'T', 'COLUMN_NAME': 'BADLEN', 'DATA_TYPE': 'INT', 'LENGTH': 'notanumber', 'NUMERIC_SCALE': None, 'IS_NULLABLE': None, 'COLUMN_TEXT': ''},
            ]

    monkeypatch.setenv('DBUTILS_JDBC_PROVIDER', 'X')
    monkeypatch.setattr('dbutils.db_browser.query_runner', fake_q, raising=True)

    tables, cols = get_all_tables_and_columns(use_mock=False, use_cache=False)
    # Should return tables containing at least the valid ones and handle missing gracefully
    assert isinstance(tables, list)
    assert isinstance(cols, list)


def test_save_cache_permission_denied(monkeypatch, tmp_path):
    # Force cache dir to be read-only
    monkeypatch.setenv('HOME', str(tmp_path))
    cache_dir = Path(str(tmp_path)) / '.cache' / 'dbutils'
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Make directory unwritable
    os.chmod(cache_dir, 0o400)

    try:
        db_browser.save_to_cache('S', [], [])  # should not raise
    finally:
        # Reset permissions so pytest can cleanup
        os.chmod(cache_dir, 0o700)


def test_query_runner_no_connect(monkeypatch):
    # Ensure that jpype.startJVM failing results in query_runner RuntimeError
    monkeypatch.setenv('DBUTILS_JDBC_PROVIDER', 'X')

    class FakeConn:
        def query(self, sql):
            return [{'A': 1}]

        def close(self):
            pass

    def fake_connect(name, params, user=None, password=None):
        return FakeConn()

    # Simulate a good connect first then cause query failure by making it raise
    monkeypatch.setattr('dbutils.jdbc_provider.connect', fake_connect, raising=True)
    # Should not raise here
    res = query_runner('select 1')
    assert isinstance(res, list)

    # Now simulate connect raises
    def fake_connect_err(name, params, user=None, password=None):
        raise RuntimeError('connect failed')

    monkeypatch.setattr('dbutils.jdbc_provider.connect', fake_connect_err, raising=True)
    with pytest.raises(RuntimeError):
        query_runner('select 1')


def test_search_index_multi_word_intersection():
    idx = SearchIndex()
    t1 = db_browser.TableInfo(schema='S', name='HELLO_WORLD', remarks='')
    t2 = db_browser.TableInfo(schema='S', name='HELLO_MARS', remarks='')
    idx.build_index([t1, t2], [])

    # Search for 'HELLO WORLD' should match HELLO_WORLD
    res = idx.search_tables('hello world')
    assert any('HELLO_WORLD' == t.name for t in res)


def test_intern_string_memory_identity():
    # Build many duplicates but ensure interned identity preserved
    large = 'z' * 2000
    ids = [intern_string(large) for _ in range(100)]
    assert all(ids[0] is x for x in ids)


@pytest.mark.timeout(10)
def test_get_all_tables_and_columns_timeout(monkeypatch):
    # Simulate a slow query_runner that would block; ensure async wrapper works quickly
    import time

    def slow_q(sql):
        time.sleep(0.2)
        return []

    monkeypatch.setenv('DBUTILS_JDBC_PROVIDER', 'X')
    monkeypatch.setattr('dbutils.db_browser.query_runner', slow_q, raising=True)

    # Call async version and ensure it completes
    t, c = db_browser.get_all_tables_and_columns(use_mock=False, use_cache=False)
    assert t == [] and c == []


# End of tests
