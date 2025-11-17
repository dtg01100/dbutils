"""Test cases for db_health.py functionality."""


def test_format_text_output():
    """Test text format output function for both database and schema checks."""
    from dbutils.db_health import format_text_output

    # Test database health output
    mock_db_results = {
        "summary": {"health_status": "GOOD", "db_version": "11.5", "db_name": "TESTDB"},
        "warnings": ["Sample warning"],
        "recommendations": ["Sample recommendation"],
        "tables": [{"TABSCHEMA": "TEST", "TABNAME": "T1", "CARD": 100}],
    }

    db_output = format_text_output(mock_db_results, False)
    assert "Database Health Report" in db_output
    assert "Health Status: GOOD" in db_output
    assert "Warnings (1)" in db_output

    # Test schema health output
    mock_schema_results = {
        "schema": "TEST_SCHEMA",
        "tables": [{"table_name": "T1", "row_count": 100, "columns": 5, "indexes": 2, "last_stats": "2023-01-01"}],
    }

    schema_output = format_text_output(mock_schema_results, True)
    assert "Schema Health Report: TEST_SCHEMA" in schema_output
    assert "Table: T1" in schema_output


if __name__ == "__main__":
    test_format_text_output()
    print("db_health tests passed")
