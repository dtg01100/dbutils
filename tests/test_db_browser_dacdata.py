# Unit test to ensure DACDATA.OHHST appears in searches and path is computed
from dbutils.db_browser import DBBrowserTUI


def test_ohhst_table_path_and_search():
    browser = DBBrowserTUI(use_mock=True)
    # Table and path present in mock data
    ohhst = [t for t in browser.tables if t.name.upper() == "OHHST"]
    assert len(ohhst) == 1
    t = ohhst[0]
    assert t.schema.upper() == "DACDATA"

    # Search should find table by full name and partials
    assert any(table.name == "OHHST" for table in browser.filter_items(browser.tables, "ohhst"))
    assert any(table.name == "OHHST" for table in browser.filter_items(browser.tables, "ohh"))

    # Search by description
    assert any(table.name == "OHHST" for table in browser.filter_items(browser.tables, "history"))
