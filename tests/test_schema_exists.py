from dbutils.db_browser import schema_exists


def test_schema_exists_mock_true():
    assert schema_exists("DACDATA", use_mock=True)


def test_schema_exists_mock_false():
    assert not schema_exists("NOT_THERE_SCHEMA", use_mock=True)
