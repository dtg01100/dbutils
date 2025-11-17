"""Tests for inferred ref coverage utility."""

from dbutils import db_inferred_ref_coverage
import sys


def test_ref_coverage_table_output(capsys):
    sys.argv = [
        "db_inferred_ref_coverage.py",
        "--mock",
        "--format",
        "table",
    ]
    db_inferred_ref_coverage.main()
    out = capsys.readouterr().out
    assert "TABSCHEMA" in out.splitlines()[0]
    assert "USERS" in out or "ORDERS" in out


def test_ref_coverage_json_output(capsys):
    sys.argv = [
        "db_inferred_ref_coverage.py",
        "--mock",
        "--format",
        "json",
        "--min-score",
        "0.0",
    ]
    db_inferred_ref_coverage.main()
    out = capsys.readouterr().out
    assert out.strip().startswith("[")
    assert "score" in out

