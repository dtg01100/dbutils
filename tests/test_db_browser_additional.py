import gzip

import pytest

from dbutils.db_browser import (
    ColumnInfo,
    SearchIndex,
    TableInfo,
    TrieNode,
    get_all_tables_and_columns_async,
    get_cache_key,
    load_from_cache,
    mock_get_columns,
    mock_get_tables,
    save_to_cache,
    schema_exists,
)


def test_get_cache_key():
    assert get_cache_key(None) == "ALL_SCHEMAS"
    assert "LIMIT5" in get_cache_key("test", 5, 2)


def test_trie_and_search_index_basic():
    node = TrieNode()
    node.insert("foobar", "k1")
    node.insert("food", "k2")
    assert "k1" in node.search_prefix("foo")

    idx = SearchIndex()
    tables = [TableInfo(schema="S", name="FOO_BAR", remarks="some stuff")]
    columns = [
        ColumnInfo(schema="S", table="FOO_BAR", name="COL1", typename="INT", length=10, scale=0, nulls="N", remarks="x")
    ]
    idx.build_index(tables, columns)
    res = idx.search_tables("foo")
    assert any("FOO_BAR" == t.name for t in res)
    cres = idx.search_columns("col")
    assert any("COL1" == c.name for c in cres)


def test_save_and_load_cache(tmp_path, monkeypatch):
    # Monkeypatch CACHE_DIR and FILE
    monkeypatch.setattr("dbutils.db_browser.CACHE_DIR", tmp_path)
    monkeypatch.setattr("dbutils.db_browser.CACHE_FILE", tmp_path / "schema_cache.pkl.gz")

    tables = mock_get_tables()
    cols = mock_get_columns()
    save_to_cache(None, tables, cols)
    loaded = load_from_cache(None)
    assert loaded is not None
    lt, lc = loaded
    assert len(lt) == len(tables)


def test_load_from_cache_corrupted(tmp_path, monkeypatch):
    monkeypatch.setattr("dbutils.db_browser.CACHE_DIR", tmp_path)
    monkeypatch.setattr("dbutils.db_browser.CACHE_FILE", tmp_path / "schema_cache.pkl.gz")
    # Write corrupted gzip pickle
    p = tmp_path / "schema_cache.pkl.gz"
    p.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(p, "wb") as f:
        f.write(b"not-a-pickle")
    assert load_from_cache(None) is None


@pytest.mark.asyncio
async def test_get_all_tables_and_columns_async_cache(tmp_path, monkeypatch):
    # Build a valid cache entry
    monkeypatch.setattr("dbutils.db_browser.CACHE_DIR", tmp_path)
    monkeypatch.setattr("dbutils.db_browser.CACHE_FILE", tmp_path / "schema_cache.pkl.gz")
    tables = mock_get_tables()
    cols = mock_get_columns()
    save_to_cache(None, tables, cols)
    # Ensure the function returns cached result
    res_tables, res_cols = await get_all_tables_and_columns_async(use_mock=False, use_cache=True)
    assert len(res_tables) == len(tables)


def test_schema_exists_mock_true():
    assert schema_exists("DACDATA", use_mock=True)
    assert not schema_exists("NOTREAL", use_mock=True)


def test_query_runner_invalid_json(monkeypatch):
    # Provide invalid JSON for URL params and ensure it falls back to {}
    monkeypatch.setenv("DBUTILS_JDBC_PROVIDER", "X")
    monkeypatch.setenv("DBUTILS_JDBC_URL_PARAMS", "notjson")

    class FakeConn:
        def query(self, sql):
            return [{"A": 1}]

        def close(self):
            pass

    def fake_connect(name, params, user=None, password=None):
        return FakeConn()

    monkeypatch.setattr("dbutils.jdbc_provider.connect", fake_connect, raising=True)
    from dbutils.db_browser import query_runner

    assert query_runner("select 1") == [{"A": 1}]


@pytest.mark.asyncio
async def test_get_all_tables_and_columns_async_query_failure(monkeypatch):
    # Simulate query_runner raising in async mode; function should handle and return empty lists
    async def fake_query(sql):
        raise RuntimeError("query failed")

    monkeypatch.setattr(
        "dbutils.db_browser.query_runner", lambda sql: (_ for _ in ()).throw(RuntimeError("query failed"))
    )
    tables, cols = await get_all_tables_and_columns_async(use_mock=False, use_cache=False)
    assert isinstance(tables, list)
    assert isinstance(cols, list)
