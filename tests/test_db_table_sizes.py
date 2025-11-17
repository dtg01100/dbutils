"""Tests for db_table_sizes utility using mock mode."""

from dbutils import db_table_sizes


def test_mock_table_sizes_json(monkeypatch, capsys):
    """Ensure JSON output contains expected mock entries."""
    # Invoke main with arguments
    import sys

    sys.argv = [
        "db_table_sizes.py",
        "--mock",
        "--format",
        "json",
    ]
    db_table_sizes.main()
    captured = capsys.readouterr().out
    assert "USERS" in captured
    assert "ORDERS" in captured
    assert captured.strip().startswith("[")


if __name__ == "__main__":  # pragma: no cover
    test_mock_table_sizes_json()  # basic manual run
    print("db_table_sizes tests passed")
