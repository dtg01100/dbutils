from dbutils.db_browser import DBBrowserTUI


def test_select_table_updates_filtered_columns():
    # Use mock data to ensure deterministic results
    browser = DBBrowserTUI(use_mock=True)
    # Select first table and update filters
    assert len(browser.tables) > 0
    browser.selected_table = browser.tables[0]
    browser.update_filters()

    key = f"{browser.selected_table.schema}.{browser.selected_table.name}"
    # filtered_columns should be the same as table_columns for the selected table
    assert key in browser.table_columns
    assert browser.filtered_columns == browser.table_columns[key]


def test_filtered_columns_without_selection_uses_search():
    browser = DBBrowserTUI(use_mock=True)
    browser.selected_table = None
    # search for 'CUST' should match DACDATA.CUSTOMERS columns and DACDATA.INVOICES (CUST_ID)
    browser.search_query = "CUST"
    browser.update_filters()

    # Ensure filtered_columns includes at least one column related to customers
    names = {c.name.upper() for c in browser.filtered_columns}
    assert any("CUST" in n for n in names)
