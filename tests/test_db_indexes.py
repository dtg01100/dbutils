"""Tests for db_indexes utility using mock mode."""

from dbutils import db_indexes


def test_mock_indexes_table_output(monkeypatch, capsys):
    """Verify table output contains expected index names."""
    import sys

    sys.argv = ["db_indexes.py", "--mock", "--format", "table"]
    db_indexes.main()
    captured = capsys.readouterr().out
    assert "IDX_USERS_ID" in captured
    assert "IDX_ORDERS_USER_ID" in captured
    assert "INDEX_SCHEMA" in captured.splitlines()[0]


if __name__ == "__main__":  # pragma: no cover
    test_mock_indexes_table_output()
    print("db_indexes tests passed")
