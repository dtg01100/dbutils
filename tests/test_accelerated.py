import importlib
import sys


def test_accelerated_fallback_functions():
    # Import accelerated module and verify fallback functions work
    acc = importlib.import_module('dbutils.accelerated')

    assert hasattr(acc, 'fast_string_normalize')
    assert acc.fast_string_normalize('Hello_World') == 'hello world'
    assert acc.fast_string_normalize('') == ''

    assert hasattr(acc, 'fast_split_words')
    assert acc.fast_split_words('  Hello   world  ') == ['Hello', 'world']

    # Intern string returns the same object for identical input under fallback
    s1 = acc.fast_intern_string('abc')
    s2 = acc.fast_intern_string('abc')
    assert s1 is s2


def test_accelerated_search_index_interface():
    acc = importlib.import_module('dbutils.accelerated')
    idx = acc.create_accelerated_search_index()

    # Should support build_index and search methods
    assert hasattr(idx, 'build_index')
    assert hasattr(idx, 'search_tables')
    assert hasattr(idx, 'search_columns')

    # Use mock data from db_browser if available
    db_browser = importlib.import_module('dbutils.db_browser')
    tables = db_browser.mock_get_tables()
    columns = db_browser.mock_get_columns()

    idx.build_index(tables, columns)

    # Searching should not error; may return empty lists
    assert isinstance(idx.search_tables('user'), list)
    assert isinstance(idx.search_columns('id'), list)


def test_accelerated_cython_import(monkeypatch):
    # Simulate a Cython fast_ops module by inserting a fake module into sys.modules
    class FakeFastIndex:
        def __init__(self):
            self.built = False

        def build_index(self, tables, columns):
            self.built = True

        def search_tables(self, q):
            return ['FAKE_TABLE']

        def search_columns(self, q):
            return ['FAKE_COL']

    fake_module = type('m', (), {'FastSearchIndex': FakeFastIndex})
    monkeypatch.setitem(sys.modules, 'dbutils.fast_ops', fake_module)

    # Reload accelerated module to pick up the fake fast_ops
    import importlib
    acc = importlib.reload(importlib.import_module('dbutils.accelerated'))
    assert acc.HAS_CYTHON is True
    idx = acc.create_accelerated_search_index()
    idx.build_index([], [])
    assert idx.search_tables('x') == ['FAKE_TABLE']
    assert idx.search_columns('x') == ['FAKE_COL']
