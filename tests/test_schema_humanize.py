from dbutils.db_browser import humanize_schema_name


def test_humanize_basic():
    assert humanize_schema_name("SCHEMA_1") == "SCHEMA 1"
    assert humanize_schema_name("MY__SCHEMA__NAME") == "MY SCHEMA NAME"
    assert humanize_schema_name("") == ""
    assert humanize_schema_name(None) == ""
