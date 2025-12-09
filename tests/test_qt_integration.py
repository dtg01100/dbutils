"""Integration tests for QtDBBrowser with actual window creation.

These tests create real Qt windows (not mocked) to test the full integration.
They use use_mock=True to avoid database connections, making them fast.
"""

import pytest
from dbutils.db_browser import ColumnInfo, TableInfo


class TestQtDBBrowserIntegration:
    """Integration tests for QtDBBrowser main window."""

    def test_create_window_basic(self, qapp):
        """Test creating a basic QtDBBrowser window."""
        from dbutils.gui.qt_app import QtDBBrowser
        
        browser = QtDBBrowser(use_mock=True)
        
        try:
            # Verify window was created
            assert browser is not None
            assert browser.isVisible()
            
            # Verify basic attributes
            assert browser.use_mock is True
            assert browser.search_mode == "tables"
            
            # Process events
            qapp.processEvents()
        finally:
            browser.close()
            qapp.processEvents()

    def test_create_window_with_schema_filter(self, qapp):
        """Test creating window with schema filter."""
        from dbutils.gui.qt_app import QtDBBrowser
        
        browser = QtDBBrowser(schema_filter="TEST", use_mock=True)
        
        try:
            assert browser.schema_filter == "TEST"
            qapp.processEvents()
        finally:
            browser.close()
            qapp.processEvents()

    def test_window_has_required_components(self, qapp):
        """Test window has all required UI components."""
        from dbutils.gui.qt_app import QtDBBrowser
        
        browser = QtDBBrowser(use_mock=True)
        
        try:
            # Check dock widgets
            assert hasattr(browser, 'search_dock')
            assert hasattr(browser, 'tables_dock')
            assert hasattr(browser, 'columns_dock')
            
            # Check core widgets
            assert hasattr(browser, 'search_input')
            assert hasattr(browser, 'mode_button')
            assert hasattr(browser, 'tables_table')
            assert hasattr(browser, 'columns_table')
            
            qapp.processEvents()
        finally:
            browser.close()
            qapp.processEvents()

    def test_toggle_search_mode(self, qapp):
        """Test toggling search mode."""
        from dbutils.gui.qt_app import QtDBBrowser
        
        browser = QtDBBrowser(use_mock=True)
        
        try:
            # Initial mode is tables
            assert browser.search_mode == "tables"
            
            # Toggle to columns
            browser.toggle_search_mode()
            qapp.processEvents()
            assert browser.search_mode == "columns"
            
            # Toggle back to tables
            browser.toggle_search_mode()
            qapp.processEvents()
            assert browser.search_mode == "tables"
        finally:
            browser.close()
            qapp.processEvents()

    def test_clear_search(self, qapp):
        """Test clearing search."""
        from dbutils.gui.qt_app import QtDBBrowser
        
        browser = QtDBBrowser(use_mock=True)
        
        try:
            # Set search text
            browser.search_input.setText("test query")
            qapp.processEvents()
            assert browser.search_input.text() == "test query"
            
            # Clear search
            browser.clear_search()
            qapp.processEvents()
            assert browser.search_input.text() == ""
        finally:
            browser.close()
            qapp.processEvents()

    def test_schema_combo_populated(self, qapp):
        """Test schema combo box gets populated."""
        from dbutils.gui.qt_app import QtDBBrowser
        
        browser = QtDBBrowser(use_mock=True)
        
        try:
            # Give time for data to load
            for _ in range(10):
                qapp.processEvents()
            
            # Schema combo should have at least "All Schemas"
            assert browser.schema_combo.count() >= 1
            assert browser.schema_combo.itemText(0) == "All Schemas"
        finally:
            browser.close()
            qapp.processEvents()

    def test_tables_loaded_with_mock(self, qapp):
        """Test that mock data gets loaded."""
        from dbutils.gui.qt_app import QtDBBrowser
        
        browser = QtDBBrowser(use_mock=True)
        
        try:
            # Give time for data to load
            for _ in range(20):
                qapp.processEvents()
            
            # With mock data, tables should be loaded
            assert len(browser.tables) > 0
        finally:
            browser.close()
            qapp.processEvents()

    def test_window_geometry(self, qapp):
        """Test window geometry."""
        from dbutils.gui.qt_app import QtDBBrowser
        
        browser = QtDBBrowser(use_mock=True)
        
        try:
            # Window should have reasonable size
            assert browser.width() > 0
            assert browser.height() > 0
            assert browser.minimumWidth() >= 700
            assert browser.minimumHeight() >= 450
            
            qapp.processEvents()
        finally:
            browser.close()
            qapp.processEvents()

    def test_menu_bar_exists(self, qapp):
        """Test menu bar is created."""
        from dbutils.gui.qt_app import QtDBBrowser
        
        browser = QtDBBrowser(use_mock=True)
        
        try:
            menu_bar = browser.menuBar()
            assert menu_bar is not None
            
            # Check for menus
            menus = [action.text() for action in menu_bar.actions()]
            assert len(menus) > 0
            
            qapp.processEvents()
        finally:
            browser.close()
            qapp.processEvents()

    def test_status_bar_exists(self, qapp):
        """Test status bar is created."""
        from dbutils.gui.qt_app import QtDBBrowser
        
        browser = QtDBBrowser(use_mock=True)
        
        try:
            status_bar = browser.statusBar()
            assert status_bar is not None
            
            qapp.processEvents()
        finally:
            browser.close()
            qapp.processEvents()
