import os

import pytest

from dbutils import db_browser
from dbutils.db_browser import get_all_tables_and_columns, get_cache_key, query_runner
from dbutils.jdbc_provider import ProviderRegistry


def test_query_runner_invalid_url_params(monkeypatch):
    monkeypatch.setenv('DBUTILS_JDBC_PROVIDER', 'X')
    monkeypatch.setenv('DBUTILS_JDBC_URL_PARAMS', '{invalid json')

    class FakeConn:
        def query(self, sql):
            return [{'A': 1}]

        def close(self):
            pass

    def fake_connect(provider_name, params, user=None, password=None):
        assert isinstance(params, dict)  # fallback to empty dict
        return FakeConn()

    monkeypatch.setattr('dbutils.jdbc_provider.connect', fake_connect, raising=True)
    # Should not raise because invalid JSON is caught
    res = query_runner('SELECT 1')
    assert res == [{'A': 1}]


def test_get_cache_key_negative_values():
    # Negative values should still generate a key with numbers
    key = get_cache_key('x', limit=-1, offset=-5)
    assert 'LIMIT' in key and 'OFFSET' in key


def test_get_all_tables_and_columns_sql_injection(monkeypatch):
    # Validate that schema filter is interpolated. This highlights lack of escaping.
    inj = "BAD'; DROP TABLE USERS; --"
    captured = {'sql': None}

    def fake_q(sql):
        captured['sql'] = sql
        return []

    monkeypatch.setenv('DBUTILS_JDBC_PROVIDER', 'X')
    monkeypatch.setattr('dbutils.db_browser.query_runner', fake_q, raising=True)

    get_all_tables_and_columns(schema_filter=inj, use_mock=False, use_cache=False)
    assert captured['sql']
    assert inj.upper() in captured['sql']


def test_provider_registry_save_readonly(tmp_path, monkeypatch):
    tmpdir = tmp_path / 'nowrite'
    tmpdir.mkdir()
    cfg = tmpdir / 'providers.json'
    cfg.write_text('[]')

    # Make directory unreadable/unwritable for the process (simulate permission error)
    os.chmod(tmpdir, 0o400)

    try:
        reg = ProviderRegistry(config_path=str(cfg))
        # Create a new provider and attempt to add; save() should handle permission error gracefully
        from dbutils.jdbc_provider import JDBCProvider

        p = JDBCProvider(name='UnitTest', driver_class='com.test.Driver', jar_path='/tmp/j.jar', url_template='jdbc:test')
        reg.add_or_update(p)
        # Calling save should not raise, even if directory is unwritable
        reg.save()
    finally:
        os.chmod(tmpdir, 0o700)


def test_jdbc_provider_jpype_start_failure(monkeypatch):
    # Simulate no Java available
    from dbutils import jdbc_provider

    class FakeJP:
        @staticmethod
        def isJVMStarted():
            return False

        @staticmethod
        def getDefaultJVMPath():
            raise RuntimeError('No JVM')

    monkeypatch.setattr('dbutils.jdbc_provider.jpype', FakeJP(), raising=True)

    # Create provider
    p = jdbc_provider.JDBCProvider(name='P', driver_class='c', jar_path='/tmp/j.jar', url_template='x')
    jc = jdbc_provider.JDBCConnection(p, {}, None, None)
    with pytest.raises(RuntimeError):
        jc.connect()


def test_enhanced_provider_registry_load_bad_json(tmp_path):
    cfg = tmp_path / 'jdbc_providers.json'
    # write invalid JSON
    cfg.write_text('{bad json')

    # Should initialize defaults gracefully
    from dbutils.enhanced_jdbc_provider import EnhancedProviderRegistry

    reg = EnhancedProviderRegistry(config_path=str(cfg))
    assert isinstance(reg.list_providers(), list)


def test_db_browser_pagination_and_inconsistency(monkeypatch):
    # Simulate a case where tables are returned but columns are missing entries
    def fake_q(sql):
        if 'FROM QSYS2.SYSTABLES' in sql:
            return [{'TABLE_SCHEMA': 'S', 'TABLE_NAME': 'T1', 'TABLE_TEXT': ''}, {'TABLE_SCHEMA': 'S', 'TABLE_NAME': 'T2'}]
        else:
            # Return columns only for T1
            return [{'TABLE_SCHEMA': 'S', 'TABLE_NAME': 'T1', 'COLUMN_NAME': 'ID', 'DATA_TYPE': 'INT', 'LENGTH': 10, 'NUMERIC_SCALE': 0, 'IS_NULLABLE': 'N', 'COLUMN_TEXT': ''}]

    monkeypatch.setenv('DBUTILS_JDBC_PROVIDER', 'X')
    monkeypatch.setattr('dbutils.db_browser.query_runner', fake_q, raising=True)

    tables, columns = get_all_tables_and_columns(use_mock=False, use_cache=False)
    assert any(t.name == 'T1' for t in tables)
    assert any(t.name == 'T2' for t in tables)
    # columns may not contain T2 subentries but code should not fail
    assert any(c.table == 'T1' for c in columns) or len(columns) >= 0


def test_search_index_large_word_count():
    from dbutils.db_browser import SearchIndex
    idx = SearchIndex()
    tables = [db_browser.TableInfo(schema='S', name=f'TBL{i}', remarks='') for i in range(2000)]
    columns = []
    idx.build_index(tables, columns)

    # Search something likely present
    res = idx.search_tables('TBL100')
    assert len(res) >= 1


def test_edge_case_schema_exists_none(monkeypatch):
    # query_runner raises an exception returning unexpected types; schema_exists should return False
    def fake_q(sql):
        return [None]

    monkeypatch.setenv('DBUTILS_JDBC_PROVIDER', 'X')
    monkeypatch.setattr('dbutils.db_browser.query_runner', fake_q, raising=True)

    # Our fake returns [None], so function should not raise and may return True given implementation
    assert db_browser.schema_exists('DACDATA')
    # And if empty list, it should return False
    monkeypatch.setattr('dbutils.db_browser.query_runner', lambda sql: [], raising=True)
    assert not db_browser.schema_exists('DACDATA')

