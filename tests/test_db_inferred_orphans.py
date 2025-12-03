"""Tests for inferred orphan SQL utility."""

import sys

from dbutils import db_inferred_orphans


def test_orphans_table_output(capsys):
    sys.argv = [
        "db_inferred_orphans.py",
        "--mock",
    ]
    db_inferred_orphans.main()
    out = capsys.readouterr().out
    lines = out.splitlines()
    assert any("CHILD_TABLE" in ln for ln in lines[:2])
    assert "-- Example orphan detection SQL" in out
    assert "SELECT COUNT(*)" in out


def test_orphans_json_output(capsys):
    sys.argv = [
        "db_inferred_orphans.py",
        "--mock",
        "--json",
        "--min-score",
        "0.0",
    ]
    db_inferred_orphans.main()
    out = capsys.readouterr().out
    assert out.strip().startswith("[")
    assert "sql" in out
    assert "score" in out
