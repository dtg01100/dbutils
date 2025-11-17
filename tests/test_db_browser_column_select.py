from dbutils.db_browser import DBBrowserTUI


def test_select_column_selects_table_and_highlights_column():
    browser = DBBrowserTUI(use_mock=True)
    # Find a column that belongs to DACDATA.CUSTOMERS
    target = None
    for c in browser.columns:
        if c.schema.upper() == "DACDATA" and c.table.upper() == "CUSTOMERS" and "CUST_ID" in c.name.upper():
            target = c
            break

    assert target is not None, "Mock column DACDATA.CUSTOMERS.CUST_ID should exist"

    # Select the column
    browser.select_column(target)

    # After selecting a column, the table should be selected
    assert browser.selected_table is not None
    assert browser.selected_table.schema.upper() == "DACDATA"
    assert browser.selected_table.name.upper() == "CUSTOMERS"

    # The selected column's name should be recorded and included in filtered_columns
    assert browser.selected_column_name == target.name
    assert any(c.name == target.name for c in browser.filtered_columns)
