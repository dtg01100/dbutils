from dbutils.db_browser import DBBrowserTUI


def test_column_search_shows_all_matches():
    browser = DBBrowserTUI(use_mock=True)
    # Confirm our mock has a CUST_* column in DACDATA.CUSTOMERS and INVOICES
    browser.search_query = "CUST"
    browser.update_filters()

    # filtered_columns should contain both customer and invoice columns with CUST in name
    names = {c.name.upper() for c in browser.filtered_columns}
    assert any("CUST_ID" in n or "CUST_NAME" in n for n in names)
    # Also ensure the columns include entries from both tables (schema.table)
    matches = [(c.schema.upper(), c.table.upper(), c.name.upper()) for c in browser.filtered_columns]
    assert any(m[1] == "CUSTOMERS" for m in matches)
    assert any(m[1] == "INVOICES" for m in matches)
