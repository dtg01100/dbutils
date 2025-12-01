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
        QSizePolicy,
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
        QSize,
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
            QSizePolicy,
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
            QSize,
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
        self._headers = ["Table", "Description"]  # Only show name and description
        self._header_tooltips = [
            "Table Name",
            "Table Description"
        ]

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

        # Get the object to work with (could be TableInfo or ColumnInfo for column search)
        item = None
        table = None
        column = None

        if self._search_results:
            if row >= len(self._search_results):
                return None
            result = self._search_results[row]
            item = result.item

            # Handle both table and column search results
            if isinstance(item, TableInfo):
                table = item
            elif isinstance(item, ColumnInfo):
                column = item
                # Find the corresponding table for display
                for t in self._tables:
                    if t.name == column.table and t.schema == column.schema:
                        table = t
                        break
        else:
            if row >= len(self._tables):
                return None
            table = self._tables[row]

        # Handle different roles
        if role == Qt.DisplayRole:
            if column is not None:
                # Column search result - display simplified column information in table format
                if col == 0:  # Name column
                    return f"{column.table} (col: {column.name})"
                elif col == 1:  # Description column
                    return f"Column: {column.name} - {column.remarks or 'No description'}"
            else:
                # Regular table result
                if col == 0:  # Table name
                    return table.name
                elif col == 1:  # Description
                    return table.remarks or ""
        elif role == Qt.ToolTipRole:
            # Return detailed info as tooltip for all columns
            if column is not None:
                # For column search results in table view
                return (f"Table: {column.table}\n"
                        f"Column: {column.name}\n"
                        f"Schema: {column.schema}\n"
                        f"Type: {column.typename}\n"
                        f"Length: {column.length or 'N/A'}\n"
                        f"Scale: {column.scale or 'N/A'}\n"
                        f"Nullable: {column.nulls}\n"
                        f"Description: {column.remarks or 'No description'}")
            else:
                # For regular table results
                return (f"Table: {table.name}\n"
                        f"Schema: {table.schema}\n"
                        f"Columns: {len(self._columns.get(f'{table.schema}.{table.name}', []))}\n"
                        f"Description: {table.remarks or 'No description'}")
        elif role == Qt.DecorationRole and col == 0:
            # Add an icon for tables - would require actual icon resources
            # For now, return None
            return None
        elif role == Qt.SizeHintRole:
            # Return size hint for better padding
            return QSize(0, 28)  # Match the row height we set

        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: Qt.DisplayRole):
        """Return header data."""
        if orientation == Qt.Horizontal:
            if role == Qt.DisplayRole:
                return self._headers[section]
            elif role == Qt.ToolTipRole:
                return self._header_tooltips[section]
        return None


class ColumnModel(QAbstractTableModel):
    """Qt model for table columns."""

    def __init__(self):
        super().__init__()
        self._columns: List[ColumnInfo] = []
        self._headers = ["Column", "Description"]  # Only show name and description
        self._header_tooltips = [
            "Column Name",
            "Column Description"
        ]

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

        # Handle different roles
        if role == Qt.DisplayRole:
            if col == 0:  # Column name
                return column.name
            elif col == 1:  # Description
                return column.remarks or ""
        elif role == Qt.ToolTipRole:
            # Return detailed info as tooltip for all columns
            type_str = column.typename
            if column.length:
                type_str += f"({column.length}"
                if column.scale:
                    type_str += f",{column.scale}"
                type_str += ")"

            return (f"Column: {column.name}\n"
                    f"Type: {type_str}\n"
                    f"Schema: {column.schema}\n"
                    f"Table: {column.table}\n"
                    f"Length: {column.length or 'N/A'}\n"
                    f"Scale: {column.scale or 'N/A'}\n"
                    f"Nullable: {column.nulls}\n"
                    f"Description: {column.remarks or 'No description'}")
        elif role == Qt.TextAlignmentRole:
            # No special alignment needed since we're only showing text columns now
            return Qt.AlignLeft | Qt.AlignVCenter
        elif role == Qt.SizeHintRole:
            # Return size hint for better padding
            return QSize(0, 28)  # Match the row height we set

        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: Qt.DisplayRole):
        """Return header data."""
        if orientation == Qt.Horizontal:
            if role == Qt.DisplayRole:
                return self._headers[section]
            elif role == Qt.ToolTipRole:
                return self._header_tooltips[section]
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
        """Perform streaming search and emit results as found with improved async behavior."""
        try:
            self._search_cancelled = False
            results = []

            if search_mode == "tables":
                # Table search with improved async behavior
                query_lower = query.lower()
                for i, table in enumerate(tables):
                    if self._search_cancelled:
                        return

                    # Check for match - prioritize fast checks first
                    match_score = 0.0
                    if query_lower in table.name.lower():
                        match_score = 1.0
                    elif any(word.startswith(query_lower) for word in table.name.lower().split("_")):
                        match_score = 0.6
                    elif table.remarks:
                        # Process remarks only if needed - this is the expensive operation
                        if query_lower in table.remarks.lower():
                            match_score = 0.8

                    if match_score > 0:
                        result = SearchResult(
                            item=table,
                            match_type="exact" if query_lower in table.name.lower() else "fuzzy",
                            relevance_score=match_score,
                            table_key=f"{table.schema}.{table.name}",
                        )
                        results.append(result)

                        # Emit results more frequently for better streaming UX
                        if len(results) % 3 == 0:  # Emit every 3 results instead of 5
                            self.results_ready.emit(results.copy())

                    # Add more frequent yield points for better async behavior
                    # especially important when processing description text
                    if i % 20 == 0:  # Yield more frequently
                        # Process Qt events to keep UI responsive without sleep
                        QApplication.processEvents()

            elif search_mode == "columns":
                # Column search with improved async behavior
                query_lower = query.lower()
                table_matches = {}

                for i, col in enumerate(columns):
                    if self._search_cancelled:
                        return

                    # Check for match - prioritize fast checks first
                    match_score = 0.0
                    if query_lower in col.name.lower():
                        match_score = 1.0
                    elif query_lower in col.typename.lower():
                        match_score = 0.7
                    elif col.remarks:
                        # Process remarks only if needed - this is the expensive operation
                        if query_lower in col.remarks.lower():
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

                        # Emit results more frequently for better UX
                        if len(results) % 5 == 0:  # Emit every 5 results instead of 10
                            self.results_ready.emit(results.copy())

                    # Add more frequent yield points for better async behavior
                    if i % 20 == 0:  # Yield more frequently
                        # Process Qt events to keep UI responsive without sleep
                        QApplication.processEvents()  # This allows the UI to remain responsive

            # Emit final results
            self.results_ready.emit(results)
            self.search_complete.emit()

        except Exception as e:
            self.error_occurred.emit(str(e))


class DataLoaderWorker(QObject):
    """Worker for loading database data in background thread."""

    data_loaded = Signal(object, object, object)  # (tables, columns, all_schemas)
    error_occurred = Signal(str)
    progress_updated = Signal(str)

    def __init__(self):
        super().__init__()

    def load_data(self, schema_filter: Optional[str], use_mock: bool):
        """Load database data in background thread."""
        try:
            self.progress_updated.emit("Loading tables and columns...")
            from ..catalog import get_all_tables_and_columns
            from ..catalog import get_tables  # Use this to get a list of all schemas

            # Get the actual tables and columns based on the schema filter
            tables, columns = get_all_tables_and_columns(schema_filter, use_mock)

            # Also get all possible schemas (without filter) to populate the dropdown completely
            all_tables = get_tables(mock=use_mock)
            all_schemas = sorted(set(table['TABSCHEMA'] for table in all_tables))

            self.data_loaded.emit(tables, columns, all_schemas)
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
        self.streaming_enabled = True  # Always enabled now

        # Caching for search results to maintain state
        self.search_results_cache: Dict[str, List[SearchResult]] = {}

        # Worker threads
        self.search_worker = None
        self.search_thread = None
        self.data_loader_worker = None
        self.data_loader_thread = None

        self.setup_ui()
        self.setup_menu()
        self.setup_status_bar()

        # Show window immediately, then load data in background
        self.show()
        QTimer.singleShot(0, self.load_data)  # Load data after window is shown

    def setup_ui(self):
        """Setup the main user interface."""
        self.setWindowTitle("DB Browser - Qt (Experimental)")
        self.setGeometry(100, 100, 1200, 800)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout with reduced spacing
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(6)  # Reduce spacing between elements
        main_layout.setContentsMargins(8, 6, 8, 6)  # Reduce margins around the layout

        # Search panel - keep it at a fixed size
        search_panel = self.create_search_panel()
        main_layout.addWidget(search_panel)
        # Set the search panel to have a fixed size policy so it doesn't expand
        search_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        # Content splitter - will take up remaining space
        content_splitter = QSplitter(Qt.Horizontal)
        content_splitter.setHandleWidth(3)  # Make splitter handle thinner

        # Tables panel (left)
        tables_panel = self.create_tables_panel()
        content_splitter.addWidget(tables_panel)

        # Columns panel (right)
        columns_panel = self.create_columns_panel()
        content_splitter.addWidget(columns_panel)

        # Set splitter proportions
        content_splitter.setSizes([600, 600])

        main_layout.addWidget(content_splitter)
        # Make the splitter expand to take up available space
        content_splitter.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def create_search_panel(self) -> QWidget:
        """Create the search input panel."""
        panel = QGroupBox("🔍 Search")
        layout = QVBoxLayout(panel)
        layout.setSpacing(4)  # Reduced spacing to keep panel compact
        layout.setContentsMargins(8, 8, 8, 6)  # Standard margins

        # Search input row
        search_row = QHBoxLayout()
        search_row.setSpacing(6)  # Keep spacing reasonable for visual separation

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search tables, columns, or descriptions...")
        self.search_input.setClearButtonEnabled(True)  # Add clear button to QLineEdit
        self.search_input.textChanged.connect(self.on_search_changed)
        search_row.addWidget(self.search_input)

        # Search mode toggle
        self.mode_button = QPushButton("📋 Tables")
        self.mode_button.clicked.connect(self.toggle_search_mode)
        self.mode_button.setStyleSheet(
            "QPushButton { padding: 4px 8px; border: 1px solid #ccc; border-radius: 3px; font-size: 10px; }"
            "QPushButton:hover { background-color: #f0f0f0; }"
        )
        search_row.addWidget(self.mode_button)

        # Clear button
        clear_button = QPushButton("🗑️ Clear")
        clear_button.clicked.connect(self.clear_search)
        clear_button.setStyleSheet(
            "QPushButton { padding: 4px 8px; border: 1px solid #ccc; border-radius: 3px; font-size: 10px; }"
            "QPushButton:hover { background-color: #ffebee; }"
        )
        search_row.addWidget(clear_button)

        layout.addLayout(search_row)

        # Search options row
        options_row = QHBoxLayout()
        options_row.setSpacing(6)  # Slightly reduced spacing

        # Schema filter - pair label with combo box
        schema_layout = QHBoxLayout()
        schema_layout.setSpacing(6)  # Standard spacing between label and combo
        schema_layout.addWidget(QLabel("Schema:"))
        self.schema_combo = QComboBox()
        self.schema_combo.addItem("All Schemas")
        self.schema_combo.currentTextChanged.connect(self.on_schema_changed)
        schema_layout.addWidget(self.schema_combo)
        schema_layout.addStretch()  # Add stretch to keep schema selector compact
        options_row.addLayout(schema_layout)

        # Show/hide non-matching
        self.show_non_matching_check = QCheckBox("Show Non-Matching")
        self.show_non_matching_check.setChecked(True)
        self.show_non_matching_check.toggled.connect(self.on_show_non_matching_changed)
        options_row.addWidget(self.show_non_matching_check)
        options_row.addStretch()  # Add stretch to keep controls left-aligned

        layout.addLayout(options_row)

        # Progress bar container to reserve space and prevent UI jumping
        progress_container = QWidget()
        progress_layout = QVBoxLayout(progress_container)
        progress_layout.setContentsMargins(0, 2, 0, 0)  # Small top margin, no other margins
        progress_layout.setSpacing(0)  # No spacing

        self.search_progress = QProgressBar()
        self.search_progress.setVisible(False)
        self.search_progress.setTextVisible(False)  # Remove text to save space
        self.search_progress.setFixedHeight(6)  # Reduce height
        self.search_progress.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        # Add a stretch to push the progress bar to the top
        progress_layout.addWidget(self.search_progress)
        progress_layout.addStretch()  # Add stretch to fill space if invisible

        # Set the container's size policy to remain fixed with minimal height
        progress_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        progress_container.setFixedHeight(10)  # Reduced fixed height container

        layout.addWidget(progress_container)

        # Store reference to container for potential future use
        self.search_progress_container = progress_container

        # Set a minimum size to ensure the group box label is visible
        panel.setMinimumHeight(140)  # Increased to ensure group box label is fully visible
        panel.setMaximumHeight(180)  # Increased maximum to accommodate all content

        return panel

    def create_tables_panel(self) -> QWidget:
        """Create the tables panel."""
        panel = QGroupBox("Tables")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)  # Add margins around the layout
        layout.setSpacing(6)  # Add spacing between elements

        # Tables table
        self.tables_table = QTableView()
        self.tables_model = DatabaseModel()
        self.tables_proxy = QSortFilterProxyModel()
        self.tables_proxy.setSourceModel(self.tables_model)
        self.tables_table.setModel(self.tables_proxy)

        # Configure table with performance and visual enhancements
        self.tables_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tables_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tables_table.setSortingEnabled(True)
        self.tables_table.setAlternatingRowColors(True)
        self.tables_table.setShowGrid(False)
        self.tables_table.setWordWrap(False)

        # Add better row height and padding
        self.tables_table.verticalHeader().setDefaultSectionSize(30)  # Increase row height for better readability

        # Optimize for performance
        self.tables_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)  # Qt6 equivalent
        self.tables_table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.tables_table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)

        # Configure headers
        header = self.tables_table.horizontalHeader()
        header.setStretchLastSection(True)  # Stretch the last section (Description) to fill space
        header.setSectionsMovable(True)
        header.setHighlightSections(False)  # Better visual for sorting

        # Set initial column widths - Table name should have minimum width, description fills remaining
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Table name - auto fit with min size
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Description - stretch to fill
        # Set minimum section size for table name to prevent excessive truncation
        header.setMinimumSectionSize(150)  # Ensure minimum width for readability

        self.tables_table.selectionModel().selectionChanged.connect(self.on_table_selected)

        layout.addWidget(self.tables_table)

        return panel

    def create_columns_panel(self) -> QWidget:
        """Create the columns panel."""
        panel = QGroupBox("Columns")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)  # Add margins around the layout
        layout.setSpacing(6)  # Add spacing between elements

        # Columns table
        self.columns_table = QTableView()
        self.columns_model = ColumnModel()
        self.columns_table.setModel(self.columns_model)

        # Configure table with performance and visual enhancements
        self.columns_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.columns_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.columns_table.setSortingEnabled(True)
        self.columns_table.setAlternatingRowColors(True)
        self.columns_table.setShowGrid(False)
        self.columns_table.setWordWrap(False)

        # Add better row height and padding
        self.columns_table.verticalHeader().setDefaultSectionSize(30)  # Increase row height for better readability

        # Optimize for performance
        self.columns_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)  # Qt6 equivalent
        self.columns_table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.columns_table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)

        # Configure headers
        header = self.columns_table.horizontalHeader()
        header.setStretchLastSection(True)  # Stretch the last section (Description) to fill space
        header.setSectionsMovable(True)
        header.setHighlightSections(False)  # Better visual for sorting

        # Set column resize modes - Column name should have minimum width, description fills remaining
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Column name - auto fit with min size
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Description - stretch to fill
        # Set minimum section size for column name to prevent excessive truncation
        header.setMinimumSectionSize(150)  # Ensure minimum width for readability

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
        """Load database data in background thread."""
        self.status_label.setText("Loading data...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress

        # Cancel any existing data loader thread
        if self.data_loader_worker:
            self.data_loader_worker = None

        if self.data_loader_thread:
            self.data_loader_thread.quit()
            self.data_loader_thread.wait()
            self.data_loader_thread = None

        # Create new worker and thread
        self.data_loader_worker = DataLoaderWorker()
        self.data_loader_thread = QThread()

        # Move worker to thread
        self.data_loader_worker.moveToThread(self.data_loader_thread)

        # Connect signals
        self.data_loader_worker.data_loaded.connect(self.on_data_loaded)
        self.data_loader_worker.error_occurred.connect(self.on_data_load_error)
        self.data_loader_worker.progress_updated.connect(self.status_label.setText)

        # Start thread and initiate data loading
        self.data_loader_thread.started.connect(
            lambda: self.data_loader_worker.load_data(self.schema_filter, self.use_mock)
        )
        self.data_loader_thread.start()

    def on_data_loaded(self, tables, columns, all_schemas=None):
        """Handle data loaded from background thread."""
        try:
            self.tables = tables
            self.columns = columns
            self.all_schemas = all_schemas or []  # Store all available schemas

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

            # Clean up thread
            if self.data_loader_thread:
                self.data_loader_thread.quit()
                self.data_loader_thread.wait()
                self.data_loader_thread = None
                self.data_loader_worker = None

        except Exception as e:
            self.status_label.setText(f"Error processing data: {e}")
            self.progress_bar.setVisible(False)

    def on_data_load_error(self, error: str):
        """Handle data loading errors."""
        self.status_label.setText(f"Error loading data: {error}")
        self.progress_bar.setVisible(False)

        # Clean up thread
        if self.data_loader_thread:
            self.data_loader_thread.quit()
            self.data_loader_thread.wait()
            self.data_loader_thread = None
            self.data_loader_worker = None

    def update_schema_combo(self):
        """Update schema combo box with all available schemas."""
        # Use all available schemas instead of just those in current data
        schemas = self.all_schemas if hasattr(self, 'all_schemas') and self.all_schemas else sorted(set(table.schema for table in self.tables))

        # Preserve the currently selected schema filter during update
        current_filter = self.schema_filter

        self.schema_combo.clear()
        self.schema_combo.addItem("All Schemas")
        for schema in schemas:
            self.schema_combo.addItem(schema)

        # Restore the selection based on the current filter
        if current_filter:
            index = self.schema_combo.findText(current_filter)
            if index >= 0:
                self.schema_combo.setCurrentIndex(index)
            else:
                # Selected schema is not available in schema list, reset to "All Schemas"
                self.schema_combo.setCurrentIndex(0)
                # Update filter to reflect change
                self.schema_filter = None
        else:
            # Default to "All Schemas"
            self.schema_combo.setCurrentIndex(0)

    def on_search_changed(self, text: str):
        """Handle search input changes with debouncing to prevent UI locking and implement caching."""
        self.search_query = text

        # Check if we have cached results for this query
        cache_key = f"{self.search_mode}:{text.lower()}"

        if text.strip() and cache_key in self.search_results_cache:
            # Use cached results if available
            cached_results = self.search_results_cache[cache_key]
            self.tables_model.set_search_results(cached_results)
            self.status_label.setText(f"Showing cached results for '{text}' ({len(cached_results)} found)")
            return

        # Cancel previous search
        if self.search_worker:
            self.search_worker.cancel_search()

        if self.search_thread:
            self.search_thread.quit()
            self.search_thread.wait()

        if not text.strip():
            # Clear search and clear cache
            self.tables_model.set_search_results([])
            self.status_label.setText("Ready")
            # Clear cache when search is cleared
            self.search_results_cache.clear()
            return

        # Use a timer to debounce search input and avoid UI locking
        if hasattr(self, '_search_timer'):
            self._search_timer.stop()

        # Create or reuse the timer
        if not hasattr(self, '_search_timer'):
            self._search_timer = QTimer()
            self._search_timer.setSingleShot(True)
            self._search_timer.timeout.connect(self.start_streaming_search)
        else:
            self._search_timer.timeout.disconnect()
            self._search_timer.timeout.connect(self.start_streaming_search)

        # Start new search after a delay to prevent rapid searches
        # Use shorter delay for more responsive experience, especially important
        # when dealing with potentially slow description searches
        self._search_timer.start(200)  # Wait 200ms after user stops typing

    def start_streaming_search(self):
        """Start streaming search in worker thread."""
        self.status_label.setText("Searching...")
        self.search_progress.setVisible(True)
        self.search_progress.setRange(0, 100)

        # Cancel any existing search first to prevent multiple threads
        if self.search_worker:
            self.search_worker.cancel_search()

        if self.search_thread and self.search_thread.isRunning():
            self.search_thread.quit()
            self.search_thread.wait(2000)  # Wait up to 2 seconds

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

        # Cache the results
        cache_key = f"{self.search_mode}:{self.search_query.lower()}"
        # Only cache if there are results to avoid caching empty searches
        if results_count > 0:
            self.search_results_cache[cache_key] = self.tables_model._search_results.copy()

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

        table_key = None

        if self.tables_model._search_results:
            # Search results mode
            if row < len(self.tables_model._search_results):
                result = self.tables_model._search_results[row]

                # For table search, use the table info directly
                if self.search_mode == "tables" and isinstance(result.item, TableInfo):
                    table_key = f"{result.item.schema}.{result.item.name}"
                # For column search, get the table from the column result
                elif self.search_mode == "columns" and isinstance(result.item, ColumnInfo):
                    table_key = f"{result.item.schema}.{result.item.table}"
        else:
            # Normal mode
            if row < len(self.tables_model._tables):
                table = self.tables_model._tables[row]
                table_key = f"{table.schema}.{table.name}"
            else:
                self.columns_model.set_columns([])
                return

        # Update columns panel if we found a valid table key
        if table_key:
            columns = self.table_columns.get(table_key, [])
            self.columns_model.set_columns(columns)
        else:
            self.columns_model.set_columns([])

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

        # Clear the cache when search mode changes to avoid showing wrong cached results
        self.search_results_cache.clear()

        # Restart search if there's a query
        if self.search_query.strip():
            self.start_streaming_search()
        else:
            # If no query, clear search results
            self.tables_model.set_search_results([])
            self.columns_model.set_columns([])

    def clear_search(self):
        """Clear the search."""
        self.search_input.clear()
        self.search_query = ""
        self.tables_model.set_search_results([])
        self.search_results_cache.clear()  # Clear the cache when search is cleared
        self.status_label.setText("Ready")

    def toggle_streaming(self):
        """Toggle streaming search - now always enabled."""
        self.streaming_enabled = True  # Always enabled
        #self.streaming_check.setChecked(self.streaming_enabled)

        self.status_label.setText("Streaming search always enabled")

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
        """Handle streaming checkbox change - now always enabled."""
        self.streaming_enabled = True  # Always enabled regardless of checkbox that's now removed
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

    def closeEvent(self, event):
        """Handle window close event and cleanup threads."""
        # Cancel any ongoing search
        if self.search_worker:
            self.search_worker.cancel_search()

        if self.search_thread and self.search_thread.isRunning():
            self.search_thread.quit()
            if not self.search_thread.wait(3000):  # Wait up to 3 seconds
                print("Warning: Search thread did not finish in time")

        # Cancel data loading if in progress
        if self.data_loader_worker:
            # No way to cancel data loading, just wait
            pass

        if self.data_loader_thread and self.data_loader_thread.isRunning():
            self.data_loader_thread.quit()
            if not self.data_loader_thread.wait(3000):  # Wait up to 3 seconds
                print("Warning: Data loader thread did not finish in time")

        event.accept()


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
