import os
import json
import tempfile
import gzip
from unittest.mock import MagicMock, patch
import pytest

from dbutils.gui.data_loader_process import (
    get_cache_dir, get_schema_cache_path, get_data_cache_path,
    is_cache_valid, load_cached_data, save_data_to_cache,
    load_cached_schemas, save_schemas_to_cache,
    to_table_dicts, to_column_dicts, jprint
)

def test_get_cache_dir():
    """Test getting the cache directory."""
    cache_dir = get_cache_dir()
    assert cache_dir.exists()
    assert str(cache_dir).endswith('.cache/dbutils')

def test_get_schema_cache_path():
    """Test getting the schema cache path."""
    cache_path = get_schema_cache_path()
    assert cache_path.exists() or cache_path.parent.exists()
    assert 'schemas.json' in str(cache_path)

def test_get_data_cache_path():
    """Test getting the data cache path."""
    cache_path = get_data_cache_path(None)
    assert cache_path.exists() or cache_path.parent.exists()
    assert 'data_all.json' in str(cache_path)

    # Test with schema filter
    cache_path_filtered = get_data_cache_path('test_schema')
    assert 'data_test_schema.json' in str(cache_path_filtered)

def test_is_cache_valid_nonexistent(tmp_path):
    """Test cache validation for non-existent file."""
    cache_file = tmp_path / 'test_cache.json'
    assert not is_cache_valid(cache_file)

def test_is_cache_valid_expired(tmp_path):
    """Test cache validation for expired file."""
    import time
    from pathlib import Path

    cache_file = tmp_path / 'test_cache.json'
    # Create a file with old modification time
    old_time = time.time() - (25 * 60 * 60)  # 25 hours ago

    # Write test data
    test_data = {'tables': [], 'columns': [], 'cached_at': old_time}
    cache_file.write_text(json.dumps(test_data))

    # Set modification time to old time
    os.utime(cache_file, (old_time, old_time))

    # Should be invalid due to expiration
    assert not is_cache_valid(cache_file)

def test_is_cache_valid_valid(tmp_path):
    """Test cache validation for valid file."""
    import time
    from pathlib import Path

    cache_file = tmp_path / 'test_cache.json'
    # Create a file with recent modification time
    recent_time = time.time() - (30 * 60)  # 30 minutes ago

    # Write test data
    test_data = {'tables': [], 'columns': [], 'cached_at': recent_time}
    cache_file.write_text(json.dumps(test_data))

    # Set modification time to recent time
    os.utime(cache_file, (recent_time, recent_time))

    # Should be valid
    assert is_cache_valid(cache_file)

def test_load_cached_data_nonexistent(tmp_path):
    """Test loading cached data from non-existent file."""
    cache_file = tmp_path / 'test_cache.json'
    result = load_cached_data(None)
    assert result is None

def test_load_cached_data_invalid(tmp_path):
    """Test loading cached data from invalid file."""
    cache_file = tmp_path / 'test_cache.json'
    cache_file.write_text('invalid json content')

    result = load_cached_data(None)
    assert result is None

def test_load_cached_data_valid(tmp_path):
    """Test loading cached data from valid file."""
    cache_file = tmp_path / 'test_cache.json'

    # Create valid test data
    test_data = {
        'tables': [
            {'schema': 'test_schema', 'name': 'test_table', 'remarks': 'Test table'}
        ],
        'columns': [
            {'schema': 'test_schema', 'table': 'test_table', 'name': 'test_column',
             'typename': 'VARCHAR', 'length': 255, 'scale': 0, 'nulls': 'Y', 'remarks': 'Test column'}
        ],
        'cached_at': 1234567890,
        'schema_filter': None
    }

    cache_file.write_text(json.dumps(test_data))

    result = load_cached_data(None)
    assert result is not None
    tables, columns = result
    assert len(tables) == 1
    assert len(columns) == 1
    assert tables[0]['name'] == 'test_table'
    assert columns[0]['name'] == 'test_column'

def test_load_cached_data_compressed(tmp_path):
    """Test loading cached data from compressed file."""
    cache_file = tmp_path / 'test_cache.json.gz'

    # Create valid test data
    test_data = {
        'tables': [
            {'schema': 'test_schema', 'name': 'test_table', 'remarks': 'Test table'}
        ],
        'columns': [
            {'schema': 'test_schema', 'table': 'test_table', 'name': 'test_column',
             'typename': 'VARCHAR', 'length': 255, 'scale': 0, 'nulls': 'Y', 'remarks': 'Test column'}
        ],
        'cached_at': 1234567890,
        'schema_filter': None
    }

    # Write compressed data
    with gzip.open(cache_file, 'wt', encoding='utf-8') as f:
        json.dump(test_data, f)

    # Mock the cache path to use our test file
    with patch('dbutils.gui.data_loader_process.get_data_cache_path', return_value=cache_file):
        result = load_cached_data(None)
        assert result is not None
        tables, columns = result
        assert len(tables) == 1
        assert len(columns) == 1

def test_save_data_to_cache(tmp_path):
    """Test saving data to cache."""
    cache_file = tmp_path / 'test_cache.json'

    # Test data
    tables = [
        {'schema': 'test_schema', 'name': 'test_table', 'remarks': 'Test table'}
    ]
    columns = [
        {'schema': 'test_schema', 'table': 'test_table', 'name': 'test_column',
         'typename': 'VARCHAR', 'length': 255, 'scale': 0, 'nulls': 'Y', 'remarks': 'Test column'}
    ]

    # Mock the cache path to use our test file
    with patch('dbutils.gui.data_loader_process.get_data_cache_path', return_value=cache_file):
        save_data_to_cache(None, tables, columns)

    # Verify file was created
    assert cache_file.exists()

    # Verify content
    with open(cache_file) as f:
        saved_data = json.load(f)

    assert saved_data['tables'] == tables
    assert saved_data['columns'] == columns
    assert 'cached_at' in saved_data

def test_save_data_to_cache_compressed(tmp_path):
    """Test saving data to cache with compression."""
    cache_file = tmp_path / 'test_cache.json.gz'

    # Test data
    tables = [
        {'schema': 'test_schema', 'name': 'test_table', 'remarks': 'Test table'}
    ]
    columns = [
        {'schema': 'test_schema', 'table': 'test_table', 'name': 'test_column',
         'typename': 'VARCHAR', 'length': 255, 'scale': 0, 'nulls': 'Y', 'remarks': 'Test column'}
    ]

    # Mock the cache path to use our test file
    with patch('dbutils.gui.data_loader_process.get_data_cache_path', return_value=cache_file):
        save_data_to_cache(None, tables, columns)

    # Verify file was created
    assert cache_file.exists()

    # Verify compressed content
    with gzip.open(cache_file, 'rt', encoding='utf-8') as f:
        saved_data = json.load(f)

    assert saved_data['tables'] == tables
    assert saved_data['columns'] == columns

def test_load_cached_schemas_nonexistent(tmp_path):
    """Test loading cached schemas from non-existent file."""
    result = load_cached_schemas()
    assert result is None

def test_load_cached_schemas_valid(tmp_path):
    """Test loading cached schemas from valid file."""
    cache_file = tmp_path / 'schemas.json'

    # Create valid test data
    test_data = {
        'schemas': ['schema1', 'schema2', 'schema3']
    }

    cache_file.write_text(json.dumps(test_data))

    # Mock the cache path to use our test file
    with patch('dbutils.gui.data_loader_process.get_schema_cache_path', return_value=cache_file):
        result = load_cached_schemas()
        assert result == ['schema1', 'schema2', 'schema3']

def test_load_cached_schemas_compressed(tmp_path):
    """Test loading cached schemas from compressed file."""
    cache_file = tmp_path / 'schemas.json.gz'

    # Create valid test data
    test_data = {
        'schemas': ['schema1', 'schema2', 'schema3']
    }

    # Write compressed data
    with gzip.open(cache_file, 'wt', encoding='utf-8') as f:
        json.dump(test_data, f)

    # Mock the cache path to use our test file
    with patch('dbutils.gui.data_loader_process.get_schema_cache_path', return_value=cache_file):
        result = load_cached_schemas()
        assert result == ['schema1', 'schema2', 'schema3']

def test_save_schemas_to_cache(tmp_path):
    """Test saving schemas to cache."""
    cache_file = tmp_path / 'schemas.json'
    schemas = ['schema1', 'schema2', 'schema3']

    # Mock the cache path to use our test file
    with patch('dbutils.gui.data_loader_process.get_schema_cache_path', return_value=cache_file):
        save_schemas_to_cache(schemas)

    # Verify file was created
    assert cache_file.exists()

    # Verify content
    with open(cache_file) as f:
        saved_data = json.load(f)

    assert saved_data['schemas'] == schemas

def test_save_schemas_to_cache_compressed(tmp_path):
    """Test saving schemas to cache with compression."""
    cache_file = tmp_path / 'schemas.json.gz'
    schemas = ['schema1', 'schema2', 'schema3']

    # Mock the cache path to use our test file
    with patch('dbutils.gui.data_loader_process.get_schema_cache_path', return_value=cache_file):
        save_schemas_to_cache(schemas)

    # Verify file was created
    assert cache_file.exists()

    # Verify compressed content
    with gzip.open(cache_file, 'rt', encoding='utf-8') as f:
        saved_data = json.load(f)

    assert saved_data['schemas'] == schemas

def test_to_table_dicts():
    """Test conversion of table objects to dictionaries."""
    # Test with dataclass-style objects
    class MockTable:
        def __init__(self, schema, name, remarks=None):
            self.schema = schema
            self.name = name
            self.remarks = remarks or ""

    tables = [
        MockTable('test_schema', 'table1', 'Test table 1'),
        MockTable('test_schema', 'table2', 'Test table 2')
    ]

    result = to_table_dicts(tables)
    assert len(result) == 2
    assert result[0]['schema'] == 'test_schema'
    assert result[0]['name'] == 'table1'
    assert result[0]['remarks'] == 'Test table 1'

def test_to_table_dicts_dict_input():
    """Test conversion of table dictionaries to dictionaries."""
    tables = [
        {'schema': 'test_schema', 'name': 'table1', 'remarks': 'Test table 1'},
        {'schema': 'test_schema', 'name': 'table2', 'remarks': 'Test table 2'}
    ]

    result = to_table_dicts(tables)
    assert len(result) == 2
    assert result[0]['schema'] == 'test_schema'
    assert result[0]['name'] == 'table1'

def test_to_column_dicts():
    """Test conversion of column objects to dictionaries."""
    # Test with dataclass-style objects
    class MockColumn:
        def __init__(self, schema, table, name, typename, length, scale, nulls, remarks=None):
            self.schema = schema
            self.table = table
            self.name = name
            self.typename = typename
            self.length = length
            self.scale = scale
            self.nulls = nulls
            self.remarks = remarks or ""

    columns = [
        MockColumn('test_schema', 'table1', 'column1', 'VARCHAR', 255, 0, 'Y', 'Test column 1'),
        MockColumn('test_schema', 'table1', 'column2', 'INTEGER', None, 0, 'N', 'Test column 2')
    ]

    result = to_column_dicts(columns)
    assert len(result) == 2
    assert result[0]['schema'] == 'test_schema'
    assert result[0]['table'] == 'table1'
    assert result[0]['name'] == 'column1'
    assert result[0]['typename'] == 'VARCHAR'
    assert result[0]['nulls'] == 'Y'

def test_to_column_dicts_dict_input():
    """Test conversion of column dictionaries to dictionaries."""
    columns = [
        {'schema': 'test_schema', 'table': 'table1', 'name': 'column1',
         'typename': 'VARCHAR', 'length': 255, 'scale': 0, 'nulls': 'Y', 'remarks': 'Test column 1'},
        {'schema': 'test_schema', 'table': 'table1', 'name': 'column2',
         'typename': 'INTEGER', 'length': None, 'scale': 0, 'nulls': 'N', 'remarks': 'Test column 2'}
    ]

    result = to_column_dicts(columns)
    assert len(result) == 2
    assert result[0]['schema'] == 'test_schema'
    assert result[0]['table'] == 'table1'
    assert result[0]['name'] == 'column1'

def test_to_column_dicts_nulls_normalization():
    """Test normalization of nulls field in column conversion."""
    # Test various nulls formats
    columns = [
        {'schema': 'test', 'table': 'test', 'name': 'col1', 'typename': 'VARCHAR',
         'length': 255, 'scale': 0, 'nulls': 'Y', 'remarks': ''},
        {'schema': 'test', 'table': 'test', 'name': 'col2', 'typename': 'VARCHAR',
         'length': 255, 'scale': 0, 'nulls': 'N', 'remarks': ''},
        {'schema': 'test', 'table': 'test', 'name': 'col3', 'typename': 'VARCHAR',
         'length': 255, 'scale': 0, 'nulls': True, 'remarks': ''},
        {'schema': 'test', 'table': 'test', 'name': 'col4', 'typename': 'VARCHAR',
         'length': 255, 'scale': 0, 'nulls': False, 'remarks': ''},
        {'schema': 'test', 'table': 'test', 'name': 'col5', 'typename': 'VARCHAR',
         'length': 255, 'scale': 0, 'nulls': 'y', 'remarks': ''},
        {'schema': 'test', 'table': 'test', 'name': 'col6', 'typename': 'VARCHAR',
         'length': 255, 'scale': 0, 'nulls': 'n', 'remarks': ''}
    ]

    result = to_column_dicts(columns)
    assert result[0]['nulls'] == 'Y'
    assert result[1]['nulls'] == 'N'
    assert result[2]['nulls'] == 'Y'  # True -> 'Y'
    assert result[3]['nulls'] == 'N'  # False -> 'N'
    assert result[4]['nulls'] == 'Y'  # 'y' -> 'Y'
    assert result[5]['nulls'] == 'N'  # 'n' -> 'N'

def test_jprint_output(capsys):
    """Test jprint function output."""
    test_obj = {'type': 'test', 'message': 'test message'}

    # Capture stdout
    with patch('sys.stdout') as mock_stdout:
        jprint(test_obj)
        mock_stdout.write.assert_called_once_with(json.dumps(test_obj) + '\n')
        mock_stdout.flush.assert_called_once()

def test_cache_expiration(tmp_path):
    """Test cache expiration logic."""
    import time
    from pathlib import Path

    cache_file = tmp_path / 'test_cache.json'

    # Create a cache file that's just under expiration
    recent_time = time.time() - (23 * 60 * 60)  # 23 hours ago
    test_data = {'tables': [], 'columns': [], 'cached_at': recent_time}
    cache_file.write_text(json.dumps(test_data))
    os.utime(cache_file, (recent_time, recent_time))

    # Should still be valid
    assert is_cache_valid(cache_file)

    # Create a cache file that's just over expiration
    old_time = time.time() - (25 * 60 * 60)  # 25 hours ago
    test_data = {'tables': [], 'columns': [], 'cached_at': old_time}
    cache_file.write_text(json.dumps(test_data))
    os.utime(cache_file, (old_time, old_time))

    # Should be invalid
    assert not is_cache_valid(cache_file)

def test_cache_with_schema_filter(tmp_path):
    """Test cache functionality with schema filter."""
    # Test data cache path with schema filter
    cache_path = get_data_cache_path('test_schema')
    assert 'test_schema' in str(cache_path)

    # Test with special characters in schema name
    cache_path_special = get_data_cache_path('test_schema-with_special.chars')
    assert 'test_schema-with_special.chars' in str(cache_path_special)

def test_cache_error_handling(tmp_path):
    """Test error handling in cache operations."""
    # Test load_cached_data with corrupted file
    cache_file = tmp_path / 'corrupted_cache.json'
    cache_file.write_text('{invalid json')

    # Mock the cache path to use our corrupted file
    with patch('dbutils.gui.data_loader_process.get_data_cache_path', return_value=cache_file):
        result = load_cached_data(None)
        assert result is None

    # Test save_data_to_cache with invalid data
    with patch('dbutils.gui.data_loader_process.get_data_cache_path', return_value=cache_file):
        # This should not crash even with invalid data
        save_data_to_cache(None, None, None)

def test_cache_compression_performance(tmp_path):
    """Test cache compression performance and file size."""
    import time

    # Create large test data
    tables = []
    columns = []

    for i in range(1000):
        tables.append({
            'schema': f'schema_{i}',
            'name': f'table_{i}',
            'remarks': f'Test table {i}'
        })

        for j in range(10):
            columns.append({
                'schema': f'schema_{i}',
                'table': f'table_{i}',
                'name': f'column_{j}',
                'typename': 'VARCHAR',
                'length': 255,
                'scale': 0,
                'nulls': 'Y',
                'remarks': f'Test column {j}'
            })

    # Test uncompressed save
    uncompressed_file = tmp_path / 'uncompressed.json'
    with patch('dbutils.gui.data_loader_process.get_data_cache_path', return_value=uncompressed_file):
        start_time = time.time()
        save_data_to_cache(None, tables, columns)
        uncompressed_time = time.time() - start_time

    uncompressed_size = uncompressed_file.stat().st_size

    # Test compressed save
    compressed_file = tmp_path / 'compressed.json.gz'
    with patch('dbutils.gui.data_loader_process.get_data_cache_path', return_value=compressed_file):
        start_time = time.time()
        save_data_to_cache(None, tables, columns)
        compressed_time = time.time() - start_time

    compressed_size = compressed_file.stat().st_size

    # Compressed should be significantly smaller
    compression_ratio = uncompressed_size / compressed_size if compressed_size > 0 else 1
    assert compression_ratio > 2  # Should be at least 2x compression

    # Both should be readable
    with open(uncompressed_file) as f:
        uncompressed_data = json.load(f)

    with gzip.open(compressed_file, 'rt', encoding='utf-8') as f:
        compressed_data = json.load(f)

    assert uncompressed_data == compressed_data