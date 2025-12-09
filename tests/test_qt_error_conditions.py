"""Error condition and failure scenario tests for QtDBBrowser.

These tests specifically simulate failures, exceptions, and error paths.
"""

import pytest
from PySide6.QtCore import Qt
from unittest.mock import MagicMock
from dbutils.db_browser import ColumnInfo, TableInfo


class TestQtDBBrowserErrorHandling:
    """Test error handling and recovery."""

    def test_double_close(self, qapp):
        """Test closing window twice."""
        from dbutils.gui.qt_app import QtDBBrowser
        
        browser = QtDBBrowser(use_mock=True)
        browser.close()
        qapp.processEvents()
        
        # Second close should not crash
        browser.close()
        qapp.processEvents()

    def test_operations_after_close(self, qapp):
        """Test calling methods after window is closed."""
        from dbutils.gui.qt_app import QtDBBrowser
        
        browser = QtDBBrowser(use_mock=True)
        browser.close()
        qapp.processEvents()
        
        # These should handle gracefully
        try:
            browser.clear_search()
            browser.toggle_search_mode()
            browser.search_input.setText("test")
        except RuntimeError:
            # Qt may raise RuntimeError for deleted objects
            pass

    def test_access_deleted_widgets(self, qapp):
        """Test accessing widgets after they're deleted."""
        from dbutils.gui.qt_app import QtDBBrowser
        
        browser = QtDBBrowser(use_mock=True)
        search_input = browser.search_input
        
        browser.close()
        qapp.processEvents()
        
        # Accessing deleted widget should either work or raise RuntimeError
        try:
            _ = search_input.text()
        except RuntimeError:
            pass  # Expected

    def test_rapid_create_and_destroy(self, qapp):
        """Test rapidly creating and destroying windows."""
        from dbutils.gui.qt_app import QtDBBrowser
        
        for _ in range(20):
            browser = QtDBBrowser(use_mock=True)
            qapp.processEvents()
            browser.close()
            qapp.processEvents()

    def test_destroy_during_search(self, qapp):
        """Test closing window while search is in progress."""
        from dbutils.gui.qt_app import QtDBBrowser
        
        browser = QtDBBrowser(use_mock=True)
        
        # Start search
        browser.search_input.setText("TEST")
        
        # Close immediately
        browser.close()
        qapp.processEvents()


class TestQtDBBrowserWorkerFailures:
    """Test worker thread failure scenarios."""

    def test_search_worker_with_malformed_table_info(self, qapp):
        """Test SearchWorker with malformed TableInfo objects."""
        from dbutils.gui.qt_app import SearchWorker
        
        worker = SearchWorker()
        
        # Create object that looks like TableInfo but isn't
        class FakeTable:
            pass
        
        fake = FakeTable()
        fake.schema = None
        fake.name = None
        fake.remarks = None
        
        # Should handle malformed data
        try:
            worker.perform_search([fake], [], "test", "tables")
        except (AttributeError, TypeError):
            pass  # Expected

    def test_table_contents_worker_with_none_table(self, qapp):
        """Test TableContentsWorker with None table parameter."""
        from dbutils.gui.qt_app import TableContentsWorker
        
        worker = TableContentsWorker()
        
        # None table should be handled
        try:
            worker.load_table_contents(None)
        except (AttributeError, TypeError):
            pass  # Expected


class TestQtDBBrowserKeyboardInput:
    """Test keyboard input edge cases."""

    def test_ctrl_c_in_search(self, qapp):
        """Test Ctrl+C in search input."""
        from dbutils.gui.qt_app import QtDBBrowser
        from PySide6.QtTest import QTest
        
        browser = QtDBBrowser(use_mock=True)
        try:
            browser.search_input.setText("test")
            browser.search_input.setFocus()
            qapp.processEvents()
            
            # Simulate Ctrl+C
            QTest.keyClick(browser.search_input, Qt.Key_C, Qt.ControlModifier)
            qapp.processEvents()
            
            # Should not crash
        finally:
            browser.close()
            qapp.processEvents()

    def test_escape_key(self, qapp):
        """Test Escape key in search input."""
        from dbutils.gui.qt_app import QtDBBrowser
        from PySide6.QtTest import QTest
        
        browser = QtDBBrowser(use_mock=True)
        try:
            browser.search_input.setText("test")
            browser.search_input.setFocus()
            qapp.processEvents()
            
            # Press Escape
            QTest.keyClick(browser.search_input, Qt.Key_Escape)
            qapp.processEvents()
            
            # Might clear search or do nothing, but shouldn't crash
        finally:
            browser.close()
            qapp.processEvents()

    def test_enter_in_search(self, qapp):
        """Test Enter key in search input."""
        from dbutils.gui.qt_app import QtDBBrowser
        from PySide6.QtTest import QTest
        
        browser = QtDBBrowser(use_mock=True)
        try:
            browser.search_input.setText("test")
            browser.search_input.setFocus()
            qapp.processEvents()
            
            # Press Enter
            QTest.keyClick(browser.search_input, Qt.Key_Return)
            qapp.processEvents()
            
            # Should handle gracefully
        finally:
            browser.close()
            qapp.processEvents()

    @pytest.mark.skip(reason="Tab navigation causes Qt internal crash")
    def test_tab_navigation(self, qapp):
        """Test tab key navigation."""
        from dbutils.gui.qt_app import QtDBBrowser
        from PySide6.QtTest import QTest
        
        browser = QtDBBrowser(use_mock=True)
        try:
            browser.search_input.setFocus()
            qapp.processEvents()
            
            # Press Tab multiple times
            for _ in range(10):
                QTest.keyClick(qapp.focusWidget(), Qt.Key_Tab)
                qapp.processEvents()
            
            # Should cycle through widgets
        finally:
            browser.close()
            qapp.processEvents()


class TestQtDBBrowserMouseInput:
    """Test mouse input edge cases."""

    def test_rapid_clicking(self, qapp):
        """Test rapid clicking on UI elements."""
        from dbutils.gui.qt_app import QtDBBrowser
        from PySide6.QtTest import QTest
        from PySide6.QtCore import Qt
        
        browser = QtDBBrowser(use_mock=True)
        try:
            # Rapid click on search input
            for _ in range(50):
                QTest.mouseClick(browser.search_input, Qt.LeftButton)
                if _ % 10 == 0:
                    qapp.processEvents()
            
            # Should handle without issues
        finally:
            browser.close()
            qapp.processEvents()

    def test_double_click_speed(self, qapp):
        """Test double-clicking."""
        from dbutils.gui.qt_app import QtDBBrowser
        from PySide6.QtTest import QTest
        from PySide6.QtCore import Qt
        
        browser = QtDBBrowser(use_mock=True)
        try:
            # Double click on search input
            QTest.mouseDClick(browser.search_input, Qt.LeftButton)
            qapp.processEvents()
            
            # Should handle gracefully
        finally:
            browser.close()
            qapp.processEvents()


class TestQtDBBrowserDataRaces:
    """Test potential race conditions and threading issues."""

    def test_modify_data_during_search(self, qapp):
        """Test modifying table data while search is in progress."""
        from dbutils.gui.qt_app import QtDBBrowser
        
        browser = QtDBBrowser(use_mock=True)
        try:
            # Start with some data
            browser.tables = [
                TableInfo(schema="TEST", name="TABLE1", remarks="Remark1")
            ]
            
            # Start search
            browser.search_input.setText("TABLE")
            qapp.processEvents()
            
            # Modify data during search
            browser.tables = [
                TableInfo(schema="TEST2", name="TABLE2", remarks="Remark2")
            ]
            qapp.processEvents()
            
            # Clear search
            browser.clear_search()
            qapp.processEvents()
            
            # Should handle without crashing
        finally:
            browser.close()
            qapp.processEvents()

    def test_switch_mode_during_search(self, qapp):
        """Test switching search mode while search is active."""
        from dbutils.gui.qt_app import QtDBBrowser
        
        browser = QtDBBrowser(use_mock=True)
        try:
            # Start search in tables mode
            browser.search_mode = "tables"
            browser.search_input.setText("TEST")
            qapp.processEvents()
            
            # Switch to columns mode
            browser.toggle_search_mode()
            qapp.processEvents()
            
            # Switch back
            browser.toggle_search_mode()
            qapp.processEvents()
            
            # Should handle mode changes
        finally:
            browser.close()
            qapp.processEvents()

    def test_clear_during_load(self, qapp):
        """Test clearing search during data load."""
        from dbutils.gui.qt_app import QtDBBrowser
        
        browser = QtDBBrowser(use_mock=True)
        try:
            # Set up data load scenario
            huge_tables = [
                TableInfo(schema=f"S{i}", name=f"T{i}", remarks=f"R{i}")
                for i in range(1000)
            ]
            browser.tables = huge_tables
            
            # Start search
            browser.search_input.setText("T500")
            
            # Immediately clear
            browser.clear_search()
            qapp.processEvents()
            
            # Should handle gracefully
        finally:
            browser.close()
            qapp.processEvents()


class TestQtDBBrowserModelStress:
    """Stress test Qt models with extreme data."""

    def test_model_with_zero_data(self, qapp):
        """Test models with completely empty data."""
        from dbutils.gui.qt_app import DatabaseModel, ColumnModel, TableContentsModel
        
        # DatabaseModel with no data
        db_model = DatabaseModel()
        db_model.set_data([], {})
        assert db_model.rowCount() == 0
        
        # ColumnModel with no columns
        col_model = ColumnModel()
        col_model.set_columns([])
        assert col_model.rowCount() == 0
        
        # TableContentsModel with no data
        tc_model = TableContentsModel()
        assert tc_model.rowCount() == 0

    def test_model_with_single_item(self, qapp):
        """Test models with single item (boundary case)."""
        from dbutils.gui.qt_app import DatabaseModel, ColumnModel
        
        # Single table
        db_model = DatabaseModel()
        single_table = [TableInfo(schema="S", name="T", remarks="R")]
        db_model.set_data(single_table, {"S.T": []})
        assert db_model.rowCount() == 1
        
        # Single column
        col_model = ColumnModel()
        single_column = [
            ColumnInfo(
                schema="S", table="T", name="C",
                typename="VARCHAR", length=10, scale=0,
                nulls="Y", remarks="R"
            )
        ]
        col_model.set_columns(single_column)
        assert col_model.rowCount() == 1

    def test_model_repeated_set_data(self, qapp):
        """Test calling set_data many times rapidly."""
        from dbutils.gui.qt_app import DatabaseModel
        
        model = DatabaseModel()
        
        for i in range(100):
            tables = [
                TableInfo(schema=f"S{i}", name=f"T{i}", remarks=f"R{i}")
            ]
            model.set_data(tables, {f"S{i}.T{i}": []})
            
            if i % 20 == 0:
                qapp.processEvents()
        
        # Should handle rapid updates

    def test_model_with_duplicate_data(self, qapp):
        """Test models with duplicate entries."""
        from dbutils.gui.qt_app import DatabaseModel, ColumnModel
        
        # Duplicate tables
        db_model = DatabaseModel()
        dup_tables = [
            TableInfo(schema="S", name="T", remarks="R"),
            TableInfo(schema="S", name="T", remarks="R"),
            TableInfo(schema="S", name="T", remarks="R"),
        ]
        db_model.set_data(dup_tables, {"S.T": []})
        
        # Duplicate columns
        col_model = ColumnModel()
        dup_columns = [
            ColumnInfo(
                schema="S", table="T", name="C",
                typename="VARCHAR", length=10, scale=0,
                nulls="Y", remarks="R"
            )
        ] * 5
        col_model.set_columns(dup_columns)


class TestQtDBBrowserSignalSlots:
    """Test signal/slot edge cases."""

    def test_emit_signals_after_close(self, qapp):
        """Test emitting signals after window close."""
        from dbutils.gui.qt_app import QtDBBrowser
        
        browser = QtDBBrowser(use_mock=True)
        
        # Get reference to search worker if it exists
        search_worker = getattr(browser, 'search_worker', None)
        
        browser.close()
        qapp.processEvents()
        
        # Try to emit signals (may raise or be no-op)
        if search_worker:
            try:
                search_worker.finished.emit([], [])
            except RuntimeError:
                pass  # Expected for deleted objects

    def test_disconnect_slots(self, qapp):
        """Test disconnecting slots."""
        from dbutils.gui.qt_app import QtDBBrowser
        
        browser = QtDBBrowser(use_mock=True)
        try:
            # Try to disconnect signals
            try:
                browser.search_input.textChanged.disconnect()
            except TypeError:
                # May fail if no connections
                pass
            
            # Window should still function
            qapp.processEvents()
        finally:
            browser.close()
            qapp.processEvents()


class TestQtDBBrowserResourceLeaks:
    """Test for potential resource leaks."""

    def test_create_many_models(self, qapp):
        """Test creating many model instances."""
        from dbutils.gui.qt_app import DatabaseModel, ColumnModel, TableContentsModel
        
        models = []
        for _ in range(100):
            models.append(DatabaseModel())
            models.append(ColumnModel())
            models.append(TableContentsModel())
        
        qapp.processEvents()
        
        # Models should be created without issues
        assert len(models) == 300

    def test_create_many_workers(self, qapp):
        """Test creating many worker instances."""
        from dbutils.gui.qt_app import SearchWorker
        
        workers = []
        for _ in range(50):
            worker = SearchWorker()
            workers.append(worker)
        
        qapp.processEvents()
        
        # Workers should be created
        assert len(workers) == 50

    def test_repeated_window_creation_same_schema(self, qapp):
        """Test creating windows with same schema filter repeatedly."""
        from dbutils.gui.qt_app import QtDBBrowser
        
        for _ in range(10):
            browser = QtDBBrowser(schema_filter="TEST", use_mock=True)
            qapp.processEvents()
            browser.close()
            qapp.processEvents()


class TestQtDBBrowserInvalidStates:
    """Test putting browser in invalid states."""

    def test_negative_window_position(self, qapp):
        """Test moving window to negative coordinates."""
        from dbutils.gui.qt_app import QtDBBrowser
        
        browser = QtDBBrowser(use_mock=True)
        try:
            browser.move(-1000, -1000)
            qapp.processEvents()
            # Should handle negative positions
        finally:
            browser.close()
            qapp.processEvents()

    def test_search_input_max_length(self, qapp):
        """Test if search input has a maximum length."""
        from dbutils.gui.qt_app import QtDBBrowser
        
        browser = QtDBBrowser(use_mock=True)
        try:
            # Try to set 100,000 character string
            mega_string = "A" * 100000
            browser.search_input.setText(mega_string)
            qapp.processEvents()
            
            # Should either truncate or handle
            length = len(browser.search_input.text())
            assert length >= 0  # Just verify it doesn't crash
        finally:
            browser.close()
            qapp.processEvents()

    def test_null_parent_widget(self, qapp):
        """Test creating browser without parent (default behavior)."""
        from dbutils.gui.qt_app import QtDBBrowser
        
        # QtDBBrowser doesn't accept parent parameter, just create normally
        browser = QtDBBrowser(use_mock=True)
        try:
            # Should have no parent (top-level window)
            assert browser.parent() is None
        finally:
            browser.close()
            qapp.processEvents()
