"""Test enhanced scoring JSON output of db_relate."""

from dbutils import db_relate
import sys


def test_relationships_json_enhanced(capsys):
    sys.argv = [
        "db_relate.py",
        "TEST.USERS.ID",
        "TEST.ORDERS.USER_ID",
        "--mock",
        "--format",
        "relationships-json",
        "--enhanced",
        "--min-score",
        "0.0",
    ]
    db_relate.main()
    out = capsys.readouterr().out
    assert "score" in out
    assert "signals" in out


if __name__ == "__main__":  # pragma: no cover
    print("Run with pytest to execute tests")
