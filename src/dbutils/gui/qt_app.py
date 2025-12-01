"""
Qt-based Database Browser - Experimental GUI Version

A modern Qt interface for database schema browsing with advanced features
including streaming search, visualizations, and enhanced user experience.
"""

import os
import sys
import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

try:
    from PySide6.QtWidgets import (
        QApplication,
        QMainWindow,
        QWidget,
        QVBoxLayout,
        QHBoxLayout,
        QSplitter,
        QTableView,
        QLineEdit,
        QPushButton,
        QLabel,
        QComboBox,
        QCheckBox,
        QGroupBox,
        QStatusBar,
        QMenuBar,
        QMenu,
        QProgressBar,
        QTextEdit,
        QAbstractItemView,
        QHeaderView,
        QMessageBox,
    )
    from PySide6.QtCore import (
        Qt,
        QTimer,
        QThread,
        Signal,
        QObject,
        QAbstractTableModel,
        QModelIndex,
        QSortFilterProxyModel,
    )
    from PySide6.QtGui import QIcon, QFont, QPixmap, QAction

    QT_AVAILABLE = True
except ImportError:
    try:
        from PyQt6.QtWidgets import (
            QApplication,
            QMainWindow,
            QWidget,
            QVBoxLayout,
            QHBoxLayout,
            QSplitter,
            QTableView,
            QLineEdit,
            QPushButton,
            QLabel,
            QComboBox,
            QCheckBox,
            QGroupBox,
            QStatusBar,
            QMenuBar,
            QMenu,
            QProgressBar,
            QTextEdit,
            QAbstractItemView,
            QHeaderView,
            QMessageBox,
        )
        from PyQt6.QtCore import (
            Qt,
            QTimer,
            QThread,
            pyqtSignal as Signal,
            QObject,
            QAbstractTableModel,
            QModelIndex,
            QSortFilterProxyModel,
        )
        from PyQt6.QtGui import QIcon, QFont, QPixmap, QAction

        QT_AVAILABLE = True
    except ImportError:
        QT_AVAILABLE = False

from ..catalog import get_all_tables_and_columns
from ..db_browser import TableInfo, ColumnInfo


@dataclass
class SearchResult:
    """Represents a search result with metadata."""

    item: Any
    match_type: str  # "exact", "prefix", "fuzzy"
    relevance_score: float
    table_key: str = ""


class DatabaseModel(QAbstractTableModel):
    """Qt model for database tables with search support."""

    def __init__(self):
        super().__init__()
        self._tables: List[TableInfo] = []
        self._columns: Dict[str, List[ColumnInfo]] = {}
        self._search_results: List[SearchResult] = []
        self._headers = ["Table", "Schema", "Description", "Columns", "Size"]

    def set_data(self, tables: List[TableInfo], columns: Dict[str, List[ColumnInfo]]):
        """Set the model data."""
        self.beginResetModel()
        self._tables = tables
        self._columns = columns
        self._search_results = []
        self.endResetModel()

    def set_search_results(self, results: List[SearchResult]):
        """Set search results with relevance scoring."""
        self.beginResetModel()
        self._search_results = sorted(results, key=lambda x: x.relevance_score, reverse=True)
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        """Return number of rows."""
        if self._search_results:
            return len(self._search_results)
        return len(self._tables)

    def columnCount(self, parent=QModelIndex()):
        """Return number of columns."""
        return len(self._headers)

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        """Return data for given index and role."""
        if not index.isValid():
            return None

        row = index.row()
        col = index.column()

        if self._search_results:
            if row >= len(self._search_results):
                return None
            result = self._search_results[row]
            item = result.item

            if isinstance(item, TableInfo):
                if col == 0:
                    return item.name
                elif col == 1:
                    return item.schema
                elif col == 2:
                    return item.remarks or ""
                elif col == 3:
                    table_key = f"{item.schema}.{item.name}"
                    return len(self._columns.get(table_key, []))
                elif col == 4:
                    return "Unknown"  # TODO: Implement size calculation
            return None
        else:
            if row >= len(self._tables):
                return None
            table = self._tables[row]

            if col == 0:
                return table.name
            elif col == 1:
                return table.schema
            elif col == 2:
                return table.remarks or ""
            elif col == 3:
                table_key = f"{table.schema}.{table.name}"
                return len(self._columns.get(table_key, []))
            elif col == 4:
                return "Unknown"  # TODO: Implement size calculation

        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: Qt.DisplayRole):
        """Return header data."""
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._headers[section]
        return None


class ColumnModel(QAbstractTableModel):
    """Qt model for table columns."""

    def __init__(self):
        super().__init__()
        self._columns: List[ColumnInfo] = []
        self._headers = ["Column", "Type", "Length", "Scale", "Nulls", "Description"]

    def set_columns(self, columns: List[ColumnInfo]):
        """Set the column data."""
        self.beginResetModel()
        self._columns = columns
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        """Return number of rows."""
        return len(self._columns)

    def columnCount(self, parent=QModelIndex()):
        """Return number of columns."""
        return len(self._headers)

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        """Return data for given index and role."""
        if not index.isValid():
            return None

        row = index.row()
        col = index.column()

        if row >= len(self._columns):
            return None

        column = self._columns[row]

        if col == 0:
            return column.name
        elif col == 1:
            type_str = column.typename
            if column.length:
                type_str += f"({column.length}"
                if column.scale:
                    type_str += f",{column.scale}"
                type_str += ")"
            return type_str
        elif col == 2:
            return str(column.length) if column.length else ""
        elif col == 3:
            return str(column.scale) if column.scale else ""
        elif col == 4:
            return column.nulls
        elif col == 5:
            return column.remarks or ""

        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: Qt.DisplayRole):
        """Return header data."""
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._headers[section]
        return None


class SearchWorker(QObject):
    """Worker for streaming search results."""

    results_ready = Signal(list)
    search_complete = Signal()
    error_occurred = Signal(str)

    def __init__(self):
        super().__init__()
        self._search_cancelled = False

    def cancel_search(self):
        """Cancel the current search."""
        self._search_cancelled = True

    def perform_search(self, tables: List[TableInfo], columns: List[ColumnInfo], query: str, search_mode: str):
        """Perform streaming search and emit results as found."""
        try:
            self._search_cancelled = False
            results = []

            if search_mode == "tables":
                # Simple table search for now
                query_lower = query.lower()
                for i, table in enumerate(tables):
                    if self._search_cancelled:
                        return

                    # Check for match
                    match_score = 0.0
                    if query_lower in table.name.lower():
                        match_score = 1.0
                    elif table.remarks and query_lower in table.remarks.lower():
                        match_score = 0.8
                    elif any(word.startswith(query_lower) for word in table.name.lower().split("_")):
                        match_score = 0.6

                    if match_score > 0:
                        result = SearchResult(
                            item=table,
                            match_type="exact" if query_lower in table.name.lower() else "fuzzy",
                            relevance_score=match_score,
                            table_key=f"{table.schema}.{table.name}",
                        )
                        results.append(result)

                        # Emit results in batches for streaming effect
                        if len(results) % 5 == 0:  # Emit every 5 results
                            self.results_ready.emit(results.copy())

                    # Small delay for visual effect
                    if i % 10 == 0:
                        QTimer.singleShot(1, lambda: None)

            elif search_mode == "columns":
                # Column search implementation
                query_lower = query.lower()
                table_matches = {}

                for i, col in enumerate(columns):
                    if self._search_cancelled:
                        return

                    # Check for match
                    match_score = 0.0
                    if query_lower in col.name.lower():
                        match_score = 1.0
                    elif query_lower in col.typename.lower():
                        match_score = 0.7
                    elif col.remarks and query_lower in col.remarks.lower():
                        match_score = 0.5

                    if match_score > 0:
                        table_key = f"{col.schema}.{col.table}"
                        if table_key not in table_matches:
                            table_matches[table_key] = []
                        table_matches[table_key].append(col)

                        # Create result for table aggregation
                        if len(table_matches[table_key]) == 1:  # First match for this table
                            result = SearchResult(
                                item=col,  # Will be processed in display
                                match_type="exact" if query_lower in col.name.lower() else "fuzzy",
                                relevance_score=match_score,
                                table_key=table_key,
                            )
                            results.append(result)

                        # Emit results in batches
                        if len(results) % 10 == 0:
                            self.results_ready.emit(results.copy())

                    # Small delay for visual effect
                    if i % 20 == 0:
                        QTimer.singleShot(1, lambda: None)

            # Emit final results
            self.results_ready.emit(results)
            self.search_complete.emit()

        except Exception as e:
            self.error_occurred.emit(str(e))


class QtDBBrowser(QMainWindow):
    """Main Qt Database Browser application."""

    def __init__(self, schema_filter: Optional[str] = None, use_mock: bool = False):
        super().__init__()

        if not QT_AVAILABLE:
            QMessageBox.critical(
                None,
                "Error",
                "Qt libraries not found. Please install PySide6 or PyQt6:\npip install PySide6\nor\npip install PyQt6",
            )
            sys.exit(1)

        self.schema_filter = schema_filter
        self.use_mock = use_mock
        self.tables: List[TableInfo] = []
        self.columns: List[ColumnInfo] = []
        self.table_columns: Dict[str, List[ColumnInfo]] = {}

        # Search state
        self.search_mode = "tables"  # "tables" or "columns"
        self.search_query = ""
        self.show_non_matching = True
        self.streaming_enabled = True

        # Worker thread
        self.search_worker = None
        self.search_thread = None

        self.setup_ui()
        self.setup_menu()
        self.setup_status_bar()
        self.load_data()

    def setup_ui(self):
        """Setup the main user interface."""
        self.setWindowTitle("DB Browser - Qt (Experimental)")
        self.setGeometry(100, 100, 1200, 800)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QVBoxLayout(central_widget)

        # Search panel
        search_panel = self.create_search_panel()
        main_layout.addWidget(search_panel)

        # Content splitter
        content_splitter = QSplitter(Qt.Horizontal)

        # Tables panel (left)
        tables_panel = self.create_tables_panel()
        content_splitter.addWidget(tables_panel)

        # Columns panel (right)
        columns_panel = self.create_columns_panel()
        content_splitter.addWidget(columns_panel)

        # Set splitter proportions
        content_splitter.setSizes([600, 600])

        main_layout.addWidget(content_splitter)

    def create_search_panel(self) -> QWidget:
        """Create the search input panel."""
        panel = QGroupBox("Search")
        layout = QVBoxLayout(panel)

        # Search input row
        search_row = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search tables, columns, or SQL...")
        self.search_input.textChanged.connect(self.on_search_changed)
        search_row.addWidget(self.search_input)

        # Search mode toggle
        self.mode_button = QPushButton("📋 Tables")
        self.mode_button.clicked.connect(self.toggle_search_mode)
        search_row.addWidget(self.mode_button)

        # Clear button
        clear_button = QPushButton("Clear")
        clear_button.clicked.connect(self.clear_search)
        search_row.addWidget(clear_button)

        layout.addLayout(search_row)

        # Search options row
        options_row = QHBoxLayout()

        # Schema filter
        self.schema_combo = QComboBox()
        self.schema_combo.addItem("All Schemas")
        self.schema_combo.currentTextChanged.connect(self.on_schema_changed)
        options_row.addWidget(QLabel("Schema:"))
        options_row.addWidget(self.schema_combo)

        # Show/hide non-matching
        self.show_non_matching_check = QCheckBox("Show Non-Matching")
        self.show_non_matching_check.setChecked(True)
        self.show_non_matching_check.toggled.connect(self.on_show_non_matching_changed)
        options_row.addWidget(self.show_non_matching_check)

        # Streaming toggle
        self.streaming_check = QCheckBox("Streaming Search")
        self.streaming_check.setChecked(True)
        self.streaming_check.toggled.connect(self.on_streaming_toggled)
        options_row.addWidget(self.streaming_check)

        layout.addLayout(options_row)

        # Progress bar for streaming
        self.search_progress = QProgressBar()
        self.search_progress.setVisible(False)
        layout.addWidget(self.search_progress)

        return panel

    def create_tables_panel(self) -> QWidget:
        """Create the tables panel."""
        panel = QGroupBox("Tables")
        layout = QVBoxLayout(panel)

        # Tables table
        self.tables_table = QTableView()
        self.tables_model = DatabaseModel()
        self.tables_proxy = QSortFilterProxyModel()
        self.tables_proxy.setSourceModel(self.tables_model)
        self.tables_table.setModel(self.tables_proxy)

        # Configure table
        self.tables_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tables_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tables_table.setSortingEnabled(True)
        self.tables_table.horizontalHeader().setStretchLastSection(True)

        self.tables_table.selectionModel().selectionChanged.connect(self.on_table_selected)

        layout.addWidget(self.tables_table)

        return panel

    def create_columns_panel(self) -> QWidget:
        """Create the columns panel."""
        panel = QGroupBox("Columns")
        layout = QVBoxLayout(panel)

        # Columns table
        self.columns_table = QTableView()
        self.columns_model = ColumnModel()
        self.columns_table.setModel(self.columns_model)

        # Configure table
        self.columns_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.columns_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.columns_table.setSortingEnabled(True)
        self.columns_table.horizontalHeader().setStretchLastSection(True)

        layout.addWidget(self.columns_table)

        return panel

    def setup_menu(self):
        """Setup the menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")

        refresh_action = QAction("Refresh", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self.load_data)
        file_menu.addAction(refresh_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # View menu
        view_menu = menubar.addMenu("View")

        toggle_streaming = QAction("Toggle Streaming Search", self)
        toggle_streaming.setShortcut("X")
        toggle_streaming.triggered.connect(self.toggle_streaming)
        view_menu.addAction(toggle_streaming)

        toggle_non_matching = QAction("Show/Hide Non-Matching", self)
        toggle_non_matching.setShortcut("H")
        toggle_non_matching.triggered.connect(self.toggle_show_non_matching)
        view_menu.addAction(toggle_non_matching)

        # Help menu
        help_menu = menubar.addMenu("Help")

        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def setup_status_bar(self):
        """Setup the status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Status label
        self.status_label = QLabel("Ready")
        self.status_bar.addWidget(self.status_label)

        # Progress indicator
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)

    def load_data(self):
        """Load database data."""
        self.status_label.setText("Loading data...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress

        try:
            # Load data in background thread
            QTimer.singleShot(100, self._load_data_background)
        except Exception as e:
            self.status_label.setText(f"Error: {e}")
            self.progress_bar.setVisible(False)

    def _load_data_background(self):
        """Load data in background."""
        try:
            self.tables, self.columns = get_all_tables_and_columns(self.schema_filter, self.use_mock)

            # Build table-columns mapping
            self.table_columns = {}
            for col in self.columns:
                table_key = f"{col.schema}.{col.table}"
                if table_key not in self.table_columns:
                    self.table_columns[table_key] = []
                self.table_columns[table_key].append(col)

            # Update UI
            self.tables_model.set_data(self.tables, self.table_columns)
            self.update_schema_combo()

            self.status_label.setText(f"Loaded {len(self.tables)} tables, {len(self.columns)} columns")
            self.progress_bar.setVisible(False)

        except Exception as e:
            self.status_label.setText(f"Error loading data: {e}")
            self.progress_bar.setVisible(False)

    def update_schema_combo(self):
        """Update schema combo box with available schemas."""
        schemas = sorted(set(table.schema for table in self.tables))

        self.schema_combo.clear()
        self.schema_combo.addItem("All Schemas")
        for schema in schemas:
            self.schema_combo.addItem(schema)

        # Set current selection
        if self.schema_filter:
            index = self.schema_combo.findText(self.schema_filter)
            if index >= 0:
                self.schema_combo.setCurrentIndex(index)

    def on_search_changed(self, text: str):
        """Handle search input changes."""
        self.search_query = text

        # Cancel previous search
        if self.search_worker:
            self.search_worker.cancel_search()

        if self.search_thread:
            self.search_thread.quit()
            self.search_thread.wait()

        if not text.strip():
            # Clear search
            self.tables_model.set_search_results([])
            self.status_label.setText("Ready")
            return

        # Start new search
        self.start_streaming_search()

    def start_streaming_search(self):
        """Start streaming search in worker thread."""
        self.status_label.setText("Searching...")
        self.search_progress.setVisible(True)
        self.search_progress.setRange(0, 100)

        # Create worker and thread
        self.search_worker = SearchWorker()
        self.search_thread = QThread()

        # Move worker to thread
        self.search_worker.moveToThread(self.search_thread)

        # Connect signals
        self.search_worker.results_ready.connect(self.on_search_results)
        self.search_worker.search_complete.connect(self.on_search_complete)
        self.search_worker.error_occurred.connect(self.on_search_error)

        # Start thread
        self.search_thread.started.connect(
            lambda: self.search_worker.perform_search(self.tables, self.columns, self.search_query, self.search_mode)
        )
        self.search_thread.start()

    def on_search_results(self, results: List[SearchResult]):
        """Handle streaming search results."""
        self.tables_model.set_search_results(results)

        # Update progress
        if self.search_query:
            self.search_progress.setValue(min(len(results) * 10, 100))
            self.status_label.setText(f"Found {len(results)} results...")

    def on_search_complete(self):
        """Handle search completion."""
        self.search_progress.setVisible(False)
        results_count = self.tables_model.rowCount()
        self.status_label.setText(f"Search complete - {results_count} results found")

    def on_search_error(self, error: str):
        """Handle search errors."""
        self.search_progress.setVisible(False)
        self.status_label.setText(f"Search error: {error}")

    def on_table_selected(self, selected, deselected):
        """Handle table selection."""
        if not selected.indexes():
            self.columns_model.set_columns([])
            return

        # Get selected table
        index = selected.indexes()[0]
        source_index = self.tables_proxy.mapToSource(index)
        row = source_index.row()

        if self.tables_model._search_results:
            # Search results mode
            if row < len(self.tables_model._search_results):
                result = self.tables_model._search_results[row]
                table_key = result.table_key
        else:
            # Normal mode
            if row < len(self.tables_model._tables):
                table = self.tables_model._tables[row]
                table_key = f"{table.schema}.{table.name}"
            else:
                self.columns_model.set_columns([])
                return

        # Update columns panel
        columns = self.table_columns.get(table_key, [])
        self.columns_model.set_columns(columns)

    def toggle_search_mode(self):
        """Toggle between table and column search modes."""
        if self.search_mode == "tables":
            self.search_mode = "columns"
            self.mode_button.setText("🔍 Columns")
            self.search_input.setPlaceholderText("Search columns by name, type, or description...")
        else:
            self.search_mode = "tables"
            self.mode_button.setText("📋 Tables")
            self.search_input.setPlaceholderText("Search tables by name or description...")

        # Restart search if there's a query
        if self.search_query.strip():
            self.start_streaming_search()

    def clear_search(self):
        """Clear the search."""
        self.search_input.clear()

    def toggle_streaming(self):
        """Toggle streaming search."""
        self.streaming_enabled = not self.streaming_enabled
        self.streaming_check.setChecked(self.streaming_enabled)

        mode = "enabled" if self.streaming_enabled else "disabled"
        self.status_label.setText(f"Streaming search {mode}")

    def toggle_show_non_matching(self):
        """Toggle show/hide non-matching tables."""
        self.show_non_matching = not self.show_non_matching
        self.show_non_matching_check.setChecked(self.show_non_matching)

        status = "shown" if self.show_non_matching else "hidden"
        self.status_label.setText(f"Non-matching tables {status}")

    def on_schema_changed(self, schema: str):
        """Handle schema filter change."""
        if schema == "All Schemas":
            self.schema_filter = None
        else:
            self.schema_filter = schema
        self.load_data()

    def on_show_non_matching_changed(self, checked: bool):
        """Handle show non-matching checkbox change."""
        self.show_non_matching = checked
        # Restart search if active
        if self.search_query.strip():
            self.start_streaming_search()

    def on_streaming_toggled(self, checked: bool):
        """Handle streaming checkbox change."""
        self.streaming_enabled = checked
        # Restart search if active
        if self.search_query.strip():
            self.start_streaming_search()

    def show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About DB Browser",
            "DB Browser - Qt (Experimental)\n\n"
            "A modern Qt interface for database schema browsing\n"
            "with streaming search and enhanced user experience.\n\n"
            "Features:\n"
            "• Streaming search results\n"
            "• Advanced filtering options\n"
            "• Rich table/column display\n"
            "• Export capabilities\n"
            "• Multi-schema support",
        )


def main():
    """Main entry point for Qt application."""
    import argparse

    parser = argparse.ArgumentParser(description="Experimental Qt Database Browser")
    parser.add_argument("--schema", help="Filter by specific schema")
    parser.add_argument("--mock", action="store_true", help="Use mock data for testing")
    parser.add_argument("--no-streaming", action="store_true", help="Disable streaming search")

    args = parser.parse_args()

    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName("DB Browser")
    app.setOrganizationName("DBUtils")

    # Create main window
    browser = QtDBBrowser(schema_filter=args.schema, use_mock=args.mock)
    if args.no_streaming:
        browser.streaming_enabled = False
        browser.streaming_check.setChecked(False)

    browser.show()

    # Run event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
