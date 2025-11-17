"""Test cases for db_diff.py functionality."""


def test_format_text_output():
    """Test text format output function."""
    from dbutils.db_diff import format_text_output

    mock_results = [
        {
            "table": "TEST_TABLE",
            "status": "different",
            "added_columns": [{"COLNAME": "NEW_COL", "TYPENAME": "VARCHAR"}],
            "removed_columns": [{"COLNAME": "OLD_COL", "TYPENAME": "INTEGER"}],
            "modified_columns": [
                {"column_name": "MOD_COL", "differences": {"TYPENAME": {"source": "INTEGER", "target": "VARCHAR"}}}
            ],
        }
    ]

    output = format_text_output(mock_results)
    assert "Schema Comparison Results" in output
    assert "Table: TEST_TABLE" in output
    assert "Status: different" in output
    assert "Added columns: 1" in output
    assert "Removed columns: 1" in output
    assert "Modified columns: 1" in output


if __name__ == "__main__":
    test_format_text_output()
    print("db_diff tests passed")
