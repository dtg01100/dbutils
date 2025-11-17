from dbutils.db_browser import DBBrowserTUI


def test_ohhst_in_mock_tables():
    browser = DBBrowserTUI(use_mock=True)
    names = {t.name.upper() for t in browser.tables}
    assert "OHHST" in names
    # Check OHHST exists in mock tables
    for t in browser.tables:
        if t.name.upper() == "OHHST":
            assert t.schema.upper() == "DACDATA"
            break
    else:
            raise AssertionError('OHHST table not found')
