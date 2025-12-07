import os
import json
import gzip
import pickle
import time
from pathlib import Path

import pytest

from dbutils import db_browser
from dbutils.db_browser import (
    get_cache_key,
    load_from_cache,
    save_to_cache,
    mock_get_tables,
    mock_get_columns,
    SearchIndex,
    TrieNode,
    intern_string,
    query_runner,
)


def test_get_cache_key_variants():
    assert get_cache_key(None) == 'ALL_SCHEMAS'
    assert get_cache_key('test') == 'TEST'
    assert get_cache_key('test', limit=10) == 'TEST_LIMIT10_OFFSET0'
    assert get_cache_key('X', limit=0, offset=5) == 'X_LIMIT0_OFFSET5'


def test_save_and_load_cache(tmp_path, monkeypatch):
    # Use a temp cache dir
    monkeypatch.setenv('HOME', str(tmp_path))
    cache_dir = Path(str(tmp_path)) / '.cache' / 'dbutils'
    if cache_dir.exists():
        for p in cache_dir.iterdir():
            p.unlink()

    tables = mock_get_tables()
    columns = mock_get_columns()

    # Save to cache
    save_to_cache('TEST', tables, columns, limit=10, offset=0)

    # Load from cache
    data = load_from_cache('TEST', limit=10, offset=0)
    assert data is not None
    tlist, clist = data
    assert len(tlist) == len(tables)
    assert len(clist) == len(columns)

    # Ensure expired cache returns None
    # Manipulate timestamp inside cache file
    cache_file = db_browser.CACHE_FILE
    assert cache_file.exists()

    with gzip.open(cache_file, 'rb') as f:
        cache_data = pickle.load(f)

    # Mark the cache as old
    for k in cache_data.keys():
        cache_data[k]['timestamp'] = time.time() - 3600 * 2

    with gzip.open(cache_file, 'wb', compresslevel=5) as f:
        pickle.dump(cache_data, f)

    assert load_from_cache('TEST', limit=10, offset=0) is None


def test_load_from_corrupted_cache(tmp_path, monkeypatch):
    monkeypatch.setenv('HOME', str(tmp_path))
    cache_dir = Path(str(tmp_path)) / '.cache' / 'dbutils'
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / 'schema_cache.pkl.gz'
    # Write invalid gzip content
    cache_file.write_bytes(b'invaliddata')

    assert load_from_cache('ANY') is None


def test_query_runner_no_provider_env(monkeypatch):
    # Ensure temp environment has no DBUTILS_JDBC_PROVIDER
    monkeypatch.delenv('DBUTILS_JDBC_PROVIDER', raising=False)
    with pytest.raises(RuntimeError, match='DBUTILS_JDBC_PROVIDER'):
        query_runner('SELECT 1')


def test_query_runner_jdbc_failure(monkeypatch):
    # Simulate DB provider env but underlying JDBC connect fails
    monkeypatch.setenv('DBUTILS_JDBC_PROVIDER', 'X')

    class FakeConn:
        def __init__(self):
            pass

        def query(self, sql):
            raise RuntimeError('query failed')

        def close(self):
            pass

    def fake_connect(provider_name, params, user=None, password=None):
        return FakeConn()

    monkeypatch.setattr('dbutils.jdbc_provider.connect', fake_connect, raising=True)

    with pytest.raises(RuntimeError, match='JDBC query failed'):
        query_runner('SELECT 1')


def test_search_index_edge_cases():
    idx = SearchIndex()

    # Test empty index returns empty lists when query blank
    assert idx.search_tables('') == []
    assert idx.search_columns('') == []

    # Build with some unusual data: names with underscores and numbers
    tables = [
        db_browser.TableInfo(schema='S', name='A_B', remarks='desc'),
        db_browser.TableInfo(schema='S', name='123TABLE', remarks='numbers'),
    ]
    columns = [
        db_browser.ColumnInfo(schema='S', table='A_B', name='ID', typename='INT', length=4, scale=0, nulls='N', remarks=''),
    ]

    idx.build_index(tables, columns)

    # Case-insensitive and partial matches
    # Searching for 'a_b' doesn't match due to replacement of '_' with space.
    # Single-word 'a' should match the table name 'A_B'
    res = idx.search_tables('a')
    assert len(res) >= 1
    res_2 = idx.search_tables('a b')
    assert len(res_2) >= 1
    res2 = idx.search_tables('123')
    assert len(res2) >= 1

    # Test a very deep trie insertion (no recursion overflow)
    long_word = 'a' * 5000
    node = TrieNode()
    node.insert(long_word, 'k')
    found = node.search_prefix('a' * 4000)
    assert 'k' in found


def test_intern_string_unchanged_for_unusual_inputs():
    # Very long strings preserve identity
    s = 'x' * 10000
    s2 = intern_string(s)
    s3 = intern_string(s)
    assert s2 is s3


def test_get_all_tables_and_columns_failure(monkeypatch):
    # Simulate query_runner exception and ensure get_all_tables_and_columns handles gracefully
    def fake_q(sql):
        raise RuntimeError('boom')

    monkeypatch.setenv('DBUTILS_JDBC_PROVIDER', 'X')
    monkeypatch.setattr('dbutils.db_browser.query_runner', fake_q, raising=True)

    tables, cols = db_browser.get_all_tables_and_columns(use_mock=False, use_cache=False)
    assert tables == []
    assert cols == []


def test_get_available_schemas_failure(monkeypatch):
    def fake_q(sql):
        raise RuntimeError('boom')

    monkeypatch.setattr('dbutils.db_browser.query_runner', fake_q, raising=True)
    schemas = db_browser.get_available_schemas(use_mock=False)
    assert schemas == []


def test_schema_exists_failure(monkeypatch):
    def fake_q(sql):
        raise RuntimeError('boom')

    monkeypatch.setenv('DBUTILS_JDBC_PROVIDER', 'X')
    monkeypatch.setattr('dbutils.db_browser.query_runner', fake_q, raising=True)

    assert not db_browser.schema_exists('DACDATA')

