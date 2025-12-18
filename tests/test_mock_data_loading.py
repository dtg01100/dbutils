"""Test that mock data loads correctly in QtDBBrowser."""

import pytest
import time
from PySide6.QtCore import Qt


def test_qt_browser_mock_data_loads(qapp):
    """Test that mock data actually loads into the QtDBBrowser UI."""
    from dbutils.gui.qt_app import QtDBBrowser
    
    browser = QtDBBrowser(use_mock=True)
    
    # Wait for data loading to complete
    start_time = time.time()
    max_timeout = 10  # 10 seconds
    
    while time.time() - start_time < max_timeout:
        qapp.processEvents()
        
        # Check if data has been loaded
        if hasattr(browser, 'tables') and browser.tables:
            break
        
        time.sleep(0.1)
    
    # Verify that data was actually loaded
    assert len(browser.tables) > 0, "Mock data should have loaded tables"
    assert len(browser.columns) > 0, "Mock data should have loaded columns"
    
    # Verify specific mock tables are present
    table_names = {t.name for t in browser.tables}
    assert "USERS" in table_names, "USERS table should be in mock data"
    assert "ORDERS" in table_names, "ORDERS table should be in mock data"
    
    browser.close()
    qapp.processEvents()


def test_qt_browser_heavy_mock_data_loads(qapp):
    """Test that heavy mock data loads correctly."""
    from dbutils.gui.qt_app import QtDBBrowser
    
    browser = QtDBBrowser(use_mock=True, use_heavy_mock=True)
    
    # Wait for data loading to complete
    start_time = time.time()
    max_timeout = 10
    
    while time.time() - start_time < max_timeout:
        qapp.processEvents()
        if hasattr(browser, 'tables') and len(browser.tables) > 50:
            # Heavy mock should have many tables
            break
        time.sleep(0.1)
    
    # Heavy mock should load significantly more data
    assert len(browser.tables) > 50, f"Heavy mock should load >50 tables, got {len(browser.tables)}"
    assert len(browser.columns) > 100, f"Heavy mock should load >100 columns, got {len(browser.columns)}"
    
    browser.close()
    qapp.processEvents()


def test_qt_browser_mock_with_schema_filter(qapp):
    """Test that mock data respects schema filter."""
    from dbutils.gui.qt_app import QtDBBrowser
    
    browser = QtDBBrowser(use_mock=True, schema_filter="TEST")
    
    # Wait for data loading
    start_time = time.time()
    max_timeout = 10
    
    while time.time() - start_time < max_timeout:
        qapp.processEvents()
        if hasattr(browser, 'tables') and browser.tables:
            break
        time.sleep(0.1)
    
    # Verify that only TEST schema data is loaded
    assert len(browser.tables) > 0, "Should have tables for TEST schema"
    
    for table in browser.tables:
        assert table.schema == "TEST", f"Expected TEST schema, got {table.schema}"
    
    browser.close()
    qapp.processEvents()
