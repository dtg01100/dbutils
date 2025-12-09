"""
Qt-based Database Browser - Experimental GUI Version

A modern Qt interface for database schema browsing with advanced features
including streaming search, visualizations, and enhanced user experience.
"""

# This file contains the Qt GUI for the database browser and requires one of
# the supported Qt bindings (PySide6 or PyQt6) at runtime. The module maps
# bindings to a common set of symbols so the rest of the application code can
# reference Qt classes uniformly.
# ruff: noqa
# type: ignore

from __future__ import annotations

import os
import sys
import asyncio
import json
import csv
from typing import Dict, List, Optional, Any
import html
from dataclasses import dataclass

try:
    # Prefer importing the modules and mapping names explicitly so we don't
    # define the same names multiple times which confuses static analysis.
    import PySide6.QtWidgets as _QtWidgets
    import PySide6.QtCore as _QtCore
    import PySide6.QtGui as _QtGui

    QApplication = _QtWidgets.QApplication
    QMainWindow = _QtWidgets.QMainWindow
    QWidget = _QtWidgets.QWidget
    QVBoxLayout = _QtWidgets.QVBoxLayout
    QHBoxLayout = _QtWidgets.QHBoxLayout
    QSplitter = _QtWidgets.QSplitter
    QTableView = _QtWidgets.QTableView
    QLineEdit = _QtWidgets.QLineEdit
    QPushButton = _QtWidgets.QPushButton
    QLabel = _QtWidgets.QLabel
    QComboBox = _QtWidgets.QComboBox
    QCheckBox = _QtWidgets.QCheckBox
    QGroupBox = _QtWidgets.QGroupBox
    QStatusBar = _QtWidgets.QStatusBar
    QMenuBar = _QtWidgets.QMenuBar
    QMenu = _QtWidgets.QMenu
    QProgressBar = _QtWidgets.QProgressBar
    QTextEdit = _QtWidgets.QTextEdit
    QAbstractItemView = _QtWidgets.QAbstractItemView
    QHeaderView = _QtWidgets.QHeaderView
    QMessageBox = _QtWidgets.QMessageBox
    QSizePolicy = _QtWidgets.QSizePolicy
    QDockWidget = _QtWidgets.QDockWidget
    QFileDialog = _QtWidgets.QFileDialog
    QProgressDialog = _QtWidgets.QProgressDialog
    QStyledItemDelegate = _QtWidgets.QStyledItemDelegate
    QStyleOptionViewItem = _QtWidgets.QStyleOptionViewItem

    Qt = _QtCore.Qt
    QTimer = _QtCore.QTimer
    QThread = _QtCore.QThread
    Signal = getattr(_QtCore, "Signal", getattr(_QtCore, "pyqtSignal", None))
    QObject = _QtCore.QObject
    QAbstractTableModel = _QtCore.QAbstractTableModel
    QModelIndex = _QtCore.QModelIndex
    QSortFilterProxyModel = _QtCore.QSortFilterProxyModel
    QSize = _QtCore.QSize
    QProcess = _QtCore.QProcess

    QIcon = _QtGui.QIcon
    QFont = _QtGui.QFont
    QPixmap = _QtGui.QPixmap
    QAction = _QtGui.QAction
    # Rich text rendering helpers used by highlight delegate
    QTextDocument = _QtGui.QTextDocument
    QAbstractTextDocumentLayout = _QtGui.QAbstractTextDocumentLayout
    QPalette = _QtGui.QPalette

    QT_AVAILABLE = True
except ImportError:
    try:
        import PyQt6.QtWidgets as _QtWidgets
        import PyQt6.QtCore as _QtCore
        import PyQt6.QtGui as _QtGui

        QApplication = _QtWidgets.QApplication
        QMainWindow = _QtWidgets.QMainWindow
        QWidget = _QtWidgets.QWidget
        QVBoxLayout = _QtWidgets.QVBoxLayout
        QHBoxLayout = _QtWidgets.QHBoxLayout
        QSplitter = _QtWidgets.QSplitter
        QTableView = _QtWidgets.QTableView
        QLineEdit = _QtWidgets.QLineEdit
        QPushButton = _QtWidgets.QPushButton
        QLabel = _QtWidgets.QLabel
        QComboBox = _QtWidgets.QComboBox
        QCheckBox = _QtWidgets.QCheckBox
        QGroupBox = _QtWidgets.QGroupBox
        QStatusBar = _QtWidgets.QStatusBar
        QMenuBar = _QtWidgets.QMenuBar
        QMenu = _QtWidgets.QMenu
        QProgressBar = _QtWidgets.QProgressBar
        QTextEdit = _QtWidgets.QTextEdit
        QAbstractItemView = _QtWidgets.QAbstractItemView
        QHeaderView = _QtWidgets.QHeaderView
        QMessageBox = _QtWidgets.QMessageBox
        QSizePolicy = _QtWidgets.QSizePolicy
        QDockWidget = _QtWidgets.QDockWidget
        QFileDialog = _QtWidgets.QFileDialog
        QProgressDialog = _QtWidgets.QProgressDialog
        QStyledItemDelegate = _QtWidgets.QStyledItemDelegate
        QStyleOptionViewItem = _QtWidgets.QStyleOptionViewItem

        Qt = _QtCore.Qt
        QTimer = _QtCore.QTimer
        QThread = _QtCore.QThread
        Signal = getattr(_QtCore, "pyqtSignal", getattr(_QtCore, "Signal", None))
        QObject = _QtCore.QObject
        QAbstractTableModel = _QtCore.QAbstractTableModel
        QModelIndex = _QtCore.QModelIndex
        QSortFilterProxyModel = _QtCore.QSortFilterProxyModel
        QSize = _QtCore.QSize
        QProcess = _QtCore.QProcess

        QIcon = _QtGui.QIcon
        QFont = _QtGui.QFont
        QPixmap = _QtGui.QPixmap
        QAction = _QtGui.QAction
        # Rich text rendering helpers used by highlight delegate
        QTextDocument = _QtGui.QTextDocument
        QAbstractTextDocumentLayout = _QtGui.QAbstractTextDocumentLayout
        QPalette = _QtGui.QPalette

        QT_AVAILABLE = True
    except ImportError as _exc:
        raise ImportError(
            "Qt libraries are required by dbutils.gui.qt_app.\n"
            "Please install PySide6 or PyQt6 (e.g. `pip install PySide6`)."
        ) from _exc

# Core helpers & data types from library
from dbutils.catalog import get_all_tables_and_columns
from dbutils.db_browser import TableInfo, ColumnInfo
from .widgets.enhanced_widgets import BusyOverlay

# Try to import accelerated C extensions for performance (optional)
try:
    # fast_ops may be an optional compiled extension; import fast helpers
    from dbutils.fast_ops import fast_search_tables, fast_search_columns

    USE_FAST_OPS = True
except Exception:
    fast_search_tables = None
    fast_search_columns = None
    USE_FAST_OPS = False

# Qt is a hard runtime requirement — we fail fast if the bindings are missing.


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
        # `_search_results` holds the active search result items when a
        # search is active. We also track `_search_active` so we can
        # distinguish between "no active search (show all tables)" and
        # "active search with zero matches". This allows the UI to show an
        # empty table when a column search returns zero matches and the
        # "show non-matching" toggle is off.
        self._search_results: List[SearchResult] = []
        self._search_active = False
        self._headers = ["Table", "Description"]  # Only show name and description
        self._header_tooltips = ["Table Name", "Table Description"]

    def set_data(self, tables: List[TableInfo], columns: Dict[str, List[ColumnInfo]]):
        """Set the model data."""
        # Check if we can do incremental update
        old_count = len(self._tables)
        new_count = len(tables)

        # For small incremental changes, use dataChanged to avoid full reset
        if old_count > 0 and new_count > old_count and new_count - old_count < 1000:
            # Incremental update - just append
            first_new = old_count
            self.beginInsertRows(QModelIndex(), first_new, new_count - 1)
            self._tables = tables
            self._columns = columns
            self.endInsertRows()
        else:
            # Full reset for large changes or initial load
            self.beginResetModel()
            self._tables = tables
            self._columns = columns
            self._search_results = []
            self.endResetModel()

    def set_search_results(self, results: Optional[List[SearchResult]]):
        """Set search results with relevance scoring."""
        self.beginResetModel()
        # Special sentinel: None means "search is active but there are no
        # matches". An empty list means "no active search / clear search".
        if results is None:
            # Active search with zero matches
            self._search_active = True
            self._search_results = []
        else:
            # If an empty list is provided we consider the search cleared
            # (no active search); otherwise we have a non-empty search
            # result list and mark search active.
            self._search_active = bool(results)
            # Defer sorting for large result sets to avoid blocking
            # Sort in place is faster than creating new list
            if results:
                results.sort(key=lambda x: x.relevance_score, reverse=True)
                self._search_results = results
            else:
                self._search_results = []
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        """Return number of rows."""
        # mark `parent` as used for linters/static analyzers
        _ = parent
        # When a search is active we always reflect the search result count
        # (which may be zero). When not actively searching, show the full
        # table list.
        if self._search_active:
            return len(self._search_results)
        return len(self._tables)

    def columnCount(self, parent=QModelIndex()):
        """Return number of columns."""
        # mark `parent` as used for linters/static analyzers
        _ = parent
        return len(self._headers)

    def data(self, index: QModelIndex, role=None):
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
        # Avoid hard dependency on Qt enums at import time
        if QT_AVAILABLE and role == Qt.DisplayRole:
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
                    # If this table row is present because of matching
                    # columns (aggregate), show a hint with number of
                    # matching columns so it's visually distinct from a
                    # direct table match.
                    try:
                        match_type = getattr(result, "match_type", None)
                        if match_type == "column":
                            count = int(result.relevance_score) if result.relevance_score else 0
                            base = table.remarks or ""
                            if count > 0:
                                suffix = f" — {count} matching column{'s' if count != 1 else ''}"
                            else:
                                suffix = " — matching columns"
                            return f"{base}{suffix}" if base else suffix.lstrip(" — ")
                    except Exception:
                        pass

                    return table.remarks or ""
        elif QT_AVAILABLE and role == Qt.ToolTipRole:
            # Return detailed info as tooltip for all columns
            if column is not None:
                # For column search results in table view
                return (
                    f"Table: {column.table}\n"
                    f"Column: {column.name}\n"
                    f"Schema: {column.schema}\n"
                    f"Type: {column.typename}\n"
                    f"Length: {column.length or 'N/A'}\n"
                    f"Scale: {column.scale or 'N/A'}\n"
                    f"Nullable: {column.nulls}\n"
                    f"Description: {column.remarks or 'No description'}"
                )
            else:
                # For regular table results
                return (
                    f"Table: {table.name}\n"
                    f"Schema: {table.schema}\n"
                    f"Columns: {len(self._columns.get(f'{table.schema}.{table.name}', []))}\n"
                    f"Description: {table.remarks or 'No description'}"
                )
        elif QT_AVAILABLE and role == Qt.DecorationRole and col == 0:
            # Add an icon for tables - would require actual icon resources
            # For now, return None
            return None
        elif QT_AVAILABLE and role == Qt.SizeHintRole:
            # Return size hint for better padding
            return QSize(0, 28)  # Match the row height we set

        return None

    # headerData() for TableContentsModel is defined above and returns
    # the current column name for DisplayRole. No extra header data is
    # required here.


def highlight_text_as_html(text: str, query: str) -> str:
    """Return text converted to HTML with occurrences of query highlighted.

    This function is intentionally independent of Qt so it can be unit-tested
    in non-GUI environments. Highlighting is case-insensitive and supports
    multiple whitespace-separated terms in the query.
    """
    if not text:
        return ""

    if not query or not query.strip():
        return html.escape(text)

    import re

    # Break query into words and build one regex to match any of them
    words = [w for w in re.split(r"\s+", query) if w]
    if not words:
        return html.escape(text)

    # Sort by length to prefer longer matches first so we don't accidentally
    # highlight sub-parts of larger terms.
    words = sorted(set(words), key=lambda x: -len(x))
    pattern = re.compile("(" + "|".join(re.escape(w) for w in words) + ")", re.IGNORECASE)

    parts = pattern.split(text)
    out_parts: List[str] = []
    for part in parts:
        if pattern.fullmatch(part):
            out_parts.append(f'<span style="background-color:#fffb8f;color:#000;">{html.escape(part)}</span>')
        else:
            out_parts.append(html.escape(part))

    return "".join(out_parts)


if QT_AVAILABLE:

    class HighlightDelegate(QStyledItemDelegate):
        """Item delegate that renders display text as HTML and highlights search matches.

        The delegate calls a provided callable to obtain the active search query so
        it updates automatically as the query changes in the main window.
        """

        def __init__(self, parent=None, get_query_callable=None):
            # Be tolerant of non-QObject parents in test environments where a
            # simple dummy object is passed. If passing `parent` to the Qt
            # base constructor fails, fall back to a no-parent construction
            # so the delegate instance still gets created and can be installed
            # into test doubles that provide `setItemDelegate`.
            try:
                super().__init__(parent)
            except Exception:
                try:
                    super().__init__()
                except Exception:
                    # If even that fails for some reason, ignore and continue
                    pass
            # Callable that returns current search query (string)
            self._get_query = get_query_callable or (lambda: "")
            # Keep reference to the provided parent (if any). Tests commonly
            # pass simple dummy objects rather than QObject instances and we
            # want to retain that parent reference without requiring it to be
            # a QObject.
            self._parent = parent

        def paint(self, painter, option, index):
            # Use the model's display string
            text = index.data(Qt.DisplayRole) or ""

            query = ""
            try:
                query = str(self._get_query() or "")
            except Exception:
                query = ""

            # Build HTML string with highlighted segments
            html_text = highlight_text_as_html(text, query) if query else html.escape(text)

            # Prepare QTextDocument for rich text rendering
            doc = QTextDocument()
            doc.setDefaultFont(option.font)
            doc.setHtml(html_text)

            # Draw selection/background using style, then render the document
            painter.save()

            opt = option
            # Ensure we use the widget style to draw the background and selection
            self.initStyleOption(opt, index)
            style = opt.widget.style() if opt.widget is not None else QApplication.style()
            try:
                style.drawControl(style.CE_ItemViewItem, opt, painter, opt.widget)
            except Exception:
                # Some Qt bindings may not expose control enums identically; ignore gracefully
                pass

            # Compute text rectangle and paint document there
            try:
                text_rect = style.subElementRect(style.SE_ItemViewItemText, opt, opt.widget)
            except Exception:
                text_rect = option.rect

            # Translate painter to the top-left of the text rect to draw document contents
            painter.translate(text_rect.topLeft())
            doc.setTextWidth(text_rect.width())
            ctx = QAbstractTextDocumentLayout.PaintContext()
            # Set text color to the view's text color for non-highlighted parts
            default_color = opt.palette.text().color()
            try:
                ctx.palette.setColor(QPalette.Text, default_color)
            except Exception:
                # In case of missing methods in some environments, ignore
                pass
            doc.documentLayout().draw(painter, ctx)
            painter.restore()

        def sizeHint(self, option, index):
            text = index.data(Qt.DisplayRole) or ""
            doc = QTextDocument()
            doc.setDefaultFont(option.font)
            doc.setHtml(highlight_text_as_html(text, self._get_query() or ""))
            # Width may not be set yet; use option.rect fallback
            w = option.rect.width() if getattr(option, "rect", None) is not None else 200
            doc.setTextWidth(w)
            return QSize(int(doc.idealWidth()) + 4, int(doc.size().height()) + 6)
else:
    # Provide a no-op stub so the module can be imported in non-Qt environments
    class HighlightDelegate:
        def __init__(self, *args, **kwargs):
            pass

        def paint(self, *args, **kwargs):
            return None

        def sizeHint(self, *args, **kwargs):
            # Minimal placeholder that mimics QSize behavior
            try:
                return QSize(0, 28)
            except Exception:
                return None


class ColumnModel(QAbstractTableModel):
    """Qt model for table columns."""

    def __init__(self):
        super().__init__()
        self._columns: List[ColumnInfo] = []
        self._headers = ["Column", "Description"]  # Only show name and description
        self._header_tooltips = ["Column Name", "Column Description"]

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

    def data(self, index: QModelIndex, role=None):
        """Return data for given index and role."""
        if not index.isValid():
            return None

        row = index.row()
        col = index.column()

        if row >= len(self._columns):
            return None

        column = self._columns[row]

        # Handle different roles
        if QT_AVAILABLE and role == Qt.DisplayRole:
            if col == 0:  # Column name
                return column.name
            elif col == 1:  # Description
                return column.remarks or ""
        elif QT_AVAILABLE and role == Qt.ToolTipRole:
            # Return detailed info as tooltip for all columns
            type_str = column.typename
            if column.length:
                type_str += f"({column.length}"
                if column.scale:
                    type_str += f",{column.scale}"
                type_str += ")"

            return (
                f"Column: {column.name}\n"
                f"Type: {type_str}\n"
                f"Schema: {column.schema}\n"
                f"Table: {column.table}\n"
                f"Length: {column.length or 'N/A'}\n"
                f"Scale: {column.scale or 'N/A'}\n"
                f"Nullable: {column.nulls}\n"
                f"Description: {column.remarks or 'No description'}"
            )
        elif QT_AVAILABLE and role == Qt.TextAlignmentRole:
            # No special alignment needed since we're only showing text columns now
            return Qt.AlignLeft | Qt.AlignVCenter
        elif QT_AVAILABLE and role == Qt.SizeHintRole:
            # Return size hint for better padding
            return QSize(0, 28)  # Match the row height we set

        return None


class TableContentsModel(QAbstractTableModel):
    """Qt model to hold a preview of rows for a selected table.

    Stores a list of column names and a list of rows (each a dict mapping
    column name to value). This mirrors the lightweight preview used by
    the GUI and is testable without the rest of Qt code.
    """

    def __init__(self):
        super().__init__()
        self._columns: List[str] = []
        # _display_columns holds the header labels shown in the view
        # which may be either the column names or descriptive text.
        self._display_columns: List[str] = []
        self._rows: List[Dict[str, Any]] = []
        self._is_loading = False
        self._loading_message = ""

    def set_contents(self, columns: List[str], rows: List[Dict[str, Any]]):
        """Replace the model contents with provided columns and rows."""
        # Check if we can do incremental update for pagination
        old_row_count = len(self._rows)
        new_row_count = len(rows or [])

        # If we're adding rows (pagination) and columns haven't changed, use incremental update
        if old_row_count > 0 and new_row_count > old_row_count and self._columns == (columns or []):
            # Incremental append - more efficient for pagination
            first_new = old_row_count
            self.beginInsertRows(QModelIndex(), first_new, new_row_count - 1)
            self._rows = rows or []
            self.endInsertRows()
        else:
            # Full reset for new table or column changes
            self.beginResetModel()
            self._columns = columns or []
            # Default display labels mirror the actual column names
            self._display_columns = list(self._columns)
            self._rows = rows or []
            self.endResetModel()

    def clear(self):
        self.set_contents([], [])
        self._is_loading = False
        self._loading_message = ""

    def show_loading(self, message: str = "Loading table contents..."):
        """Show a loading placeholder."""
        self.beginResetModel()
        self._is_loading = True
        self._loading_message = message
        self._columns = []
        self._display_columns = []
        self._rows = []
        self.endResetModel()

    def hide_loading(self):
        """Hide the loading placeholder."""
        if self._is_loading:
            self.beginResetModel()
            self._is_loading = False
            self._loading_message = ""
            self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        _ = parent
        if self._is_loading:
            return 1  # Show single placeholder row
        return len(self._rows)

    def columnCount(self, parent=QModelIndex()):
        _ = parent
        if self._is_loading:
            return 1  # Show single column for placeholder
        return len(self._columns)

    def data(self, index: QModelIndex, role=None):
        if not index.isValid():
            return None

        r = index.row()
        c = index.column()

        # Show loading placeholder
        if self._is_loading:
            if QT_AVAILABLE and role == Qt.DisplayRole:
                return self._loading_message
            elif QT_AVAILABLE and role == Qt.TextAlignmentRole:
                return Qt.AlignCenter
            elif QT_AVAILABLE and role == Qt.ForegroundRole:
                from PySide6.QtGui import QColor

                return QColor("#888")
            return None

        if r >= len(self._rows) or c >= len(self._columns):
            return None

        col_name = self._columns[c]
        row = self._rows[r]

        if QT_AVAILABLE and role == Qt.DisplayRole:
            # Convert value to string for display
            try:
                val = row.get(col_name)
            except Exception:
                val = None
            return "" if val is None else str(val)

        elif QT_AVAILABLE and role == Qt.ToolTipRole:
            try:
                val = row.get(col_name)
            except Exception:
                val = None
            return "" if val is None else str(val)

        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role=None):
        if self._is_loading:
            return None  # No headers while loading
        if QT_AVAILABLE and orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if section < len(self._display_columns):
                return self._display_columns[section]
        return None

    def set_header_display_mode(self, mode: str, column_meta: Optional[List[ColumnInfo]] = None):
        """Set how headers should be displayed.

        mode: 'name' uses the column names; 'description' shows column remarks
        (falling back to the name when description not present).

        column_meta: optional list of ColumnInfo objects for the current
        table so we can show richer descriptions.
        """
        try:
            if mode == "description" and column_meta:
                # Map names -> description
                name_to_desc = {c.name: (c.remarks or c.name) for c in column_meta}
                self._display_columns = [name_to_desc.get(n, n) for n in self._columns]
            else:
                # Default is to show names
                self._display_columns = list(self._columns)
            # Notify the view the headers changed
            try:
                self.headerDataChanged.emit(Qt.Horizontal, 0, max(0, len(self._display_columns) - 1))
            except Exception:
                # headerDataChanged may not be available in stubbed tests; ignore
                pass
        except Exception:
            # Keep previous state on any failure
            pass

    # TableContentsModel only needs one headerData implementation (above)


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

            # Use C-accelerated search if available
            if USE_FAST_OPS:
                if search_mode == "tables":
                    scored_results = fast_search_tables(tables, query)
                    for table, score in scored_results:
                        if self._search_cancelled:
                            return
                        result = SearchResult(
                            item=table,
                            match_type="exact" if score >= 1.0 else "fuzzy",
                            relevance_score=score,
                            table_key=f"{table.schema}.{table.name}",
                        )
                        results.append(result)

                        # Emit results in batches
                        if len(results) % 10 == 0:
                            self.results_ready.emit(results.copy())

                elif search_mode == "columns":
                    scored_results = fast_search_columns(columns, query)
                    # Collect per-table aggregates and per-column results.
                    table_matches: dict[str, dict] = {}
                    column_results: list[tuple[ColumnInfo, float]] = []

                    for col, score in scored_results:
                        if self._search_cancelled:
                            return
                        column_results.append((col, score))
                        table_key = f"{col.schema}.{col.table}"
                        entry = table_matches.setdefault(table_key, {"cols": [], "max_score": 0.0})
                        entry["cols"].append(col)
                        if score > entry["max_score"]:
                            entry["max_score"] = score

                        # Emit intermediate column items occasionally to keep UI responsive
                        if len(column_results) % 15 == 0:
                            # For streaming responsiveness emit a copy of the
                            # current column results (not the final aggregates)
                            interim = [
                                SearchResult(
                                    item=c,
                                    match_type=("exact" if s >= 1.0 else "fuzzy"),
                                    relevance_score=s,
                                    table_key=f"{c.schema}.{c.table}",
                                )
                                for c, s in column_results
                            ]
                            self.results_ready.emit(interim)

                # Build final results combining per-table aggregates and
                # per-column items so the UI shows tables (with a column
                # match marker) followed by detailed column matches.
                table_lookup = {f"{t.schema}.{t.name}": t for t in tables}
                agg_results = []
                for t_key, info in table_matches.items():
                    t_obj = table_lookup.get(t_key)
                    if t_obj:
                        count = len(info.get("cols", []))
                        agg_results.append(
                            SearchResult(item=t_obj, match_type="column", relevance_score=float(count), table_key=t_key)
                        )

                agg_results.sort(key=lambda r: -r.relevance_score)
                col_results_sorted = [
                    SearchResult(
                        item=c,
                        match_type=("exact" if s >= 1.0 else "fuzzy"),
                        relevance_score=s,
                        table_key=f"{c.schema}.{c.table}",
                    )
                    for c, s in sorted(column_results, key=lambda x: -x[1])
                ]
                results = agg_results + col_results_sorted
                self.search_complete.emit()
                return

            # Fallback to Python implementation
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

                    # Yield point for better async behavior - signal emits will process events
                    if i % 20 == 0:
                        # Just emit current results to keep UI updated
                        if results:
                            self.results_ready.emit(results.copy())

            elif search_mode == "columns":
                # Column search with improved async behavior
                query_lower = query.lower()
                # Build per-table aggregation and per-column listings
                table_matches = {}
                column_results = []

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
                        entry = table_matches.setdefault(table_key, {"cols": [], "max_score": 0.0})
                        entry["cols"].append(col)
                        if match_score > entry["max_score"]:
                            entry["max_score"] = match_score

                        # Collect per-column results for later emission
                        column_results.append((col, match_score))

                        # Emit intermediate column items occasionally to keep UI responsive
                        if len(column_results) % 5 == 0:
                            interim = [
                                SearchResult(
                                    item=c,
                                    match_type=("exact" if (query_lower in c.name.lower()) else "fuzzy"),
                                    relevance_score=s,
                                    table_key=f"{c.schema}.{c.table}",
                                )
                                for c, s in column_results
                            ]
                            self.results_ready.emit(interim)

                    # Yield point - emit results to update UI
                    if i % 20 == 0 and column_results:
                        interim = [
                            SearchResult(
                                item=c,
                                match_type=("exact" if (query_lower in c.name.lower()) else "fuzzy"),
                                relevance_score=s,
                                table_key=f"{c.schema}.{c.table}",
                            )
                            for c, s in column_results
                        ]
                        self.results_ready.emit(interim)

            # Emit final results. For column-mode, synthesize aggregate table
            # SearchResult entries (type TableInfo with match_type 'column')
            # so tables containing matching columns appear as matches as well.
            if search_mode == "columns":
                # Build table lookup
                table_lookup = {f"{t.schema}.{t.name}": t for t in tables}
                agg_results: list[SearchResult] = []

                for t_key, info in table_matches.items():
                    t_obj = table_lookup.get(t_key)
                    if t_obj:
                        count = len(info.get("cols", []))
                        # Use count as a simple relevance proxy
                        agg_results.append(
                            SearchResult(item=t_obj, match_type="column", relevance_score=float(count), table_key=t_key)
                        )

                # Sort aggregates by descending count then append column results sorted by score
                agg_results.sort(key=lambda r: -r.relevance_score)

                col_results_sorted = []
                try:
                    # For fast path column_results may exist
                    if "column_results" in locals():
                        col_results_sorted = [
                            SearchResult(
                                item=c,
                                match_type=("exact" if s >= 1.0 else "fuzzy"),
                                relevance_score=s,
                                table_key=f"{c.schema}.{c.table}",
                            )
                            for c, s in sorted(column_results, key=lambda x: -x[1])
                        ]
                except Exception:
                    col_results_sorted = results

                final = agg_results + col_results_sorted
                self.results_ready.emit(final)
            else:
                self.results_ready.emit(results)
            self.search_complete.emit()

        except Exception as e:
            self.error_occurred.emit(str(e))


class TableContentsWorker(QObject):
    """Worker to fetch a small preview of table rows in a background thread.

    This worker builds a safe-enough SQL preview and delegates to
    dbutils.db_browser.query_runner for execution. It emits results_ready
    with (columns, rows) upon success, or error_occurred on failures.
    """

    results_ready = Signal(list, list)
    error_occurred = Signal(str)

    def __init__(self):
        super().__init__()
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    @staticmethod
    def _is_string_type(typename: Optional[str]) -> bool:
        if not typename:
            return True
        t = typename.upper()
        # treat common textual/date/time types as strings
        for prefix in ("CHAR", "VARCHAR", "CLOB", "TEXT", "DATE", "TIMESTAMP", "TIME"):
            if prefix in t:
                return True
        return False

    def perform_fetch(
        self,
        schema: str,
        table: str,
        limit: int = 25,
        start_offset: int = 0,
        column_filter: Optional[str] = None,
        value: Optional[str] = None,
        where_clause: Optional[str] = None,
        use_mock: bool = False,
        table_columns: Optional[Dict] = None,
        db_file: Optional[str] = None,
    ):
        """Perform a fetch and emit results_ready(columns, rows).

        - If where_clause is provided it is used verbatim (caller responsibility).
        - Otherwise, if column_filter and value are provided, a WHERE clause is constructed
          using heuristic quoting based on column types.
        - If use_mock is True, generates mock row data instead of querying database.
        - If db_file is provided, queries SQLite database instead of DB2.
        """
        try:
            self._cancelled = False

            # Handle SQLite database
            if db_file:
                import sqlite3
                
                conn = sqlite3.connect(db_file)
                conn.row_factory = sqlite3.Row  # Enable column name access
                cursor = conn.cursor()
                
                # Build WHERE clause
                where = ""
                if where_clause:
                    where = f" WHERE {where_clause}"
                elif column_filter and (value is not None):
                    # SQLite handles quoting more simply
                    safe_val = str(value).replace("'", "''")
                    where = f" WHERE {column_filter} = '{safe_val}'"
                
                # Build query with LIMIT and OFFSET
                sql = f"SELECT * FROM {table}{where} LIMIT {int(limit)} OFFSET {int(start_offset)}"
                
                cursor.execute(sql)
                rows_data = cursor.fetchall()
                
                # Convert to list of dicts
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                rows = []
                for row in rows_data:
                    row_dict = {col: row[col] for col in columns}
                    rows.append(row_dict)
                
                conn.close()
                
                if self._cancelled:
                    return
                
                self.results_ready.emit(columns, rows)
                return

            # Import here so worker can be used in tests without heavy imports at module load
            from dbutils.db_browser import query_runner

            # Build base SQL
            tbl = f"{schema}.{table}"

            where = ""
            if where_clause:
                where = f" WHERE {where_clause}"
            elif column_filter and (value is not None):
                # Try to be type-aware: attempt to inspect column metadata via catalog
                try:
                    # Caller is expected to have table_columns mapping; attempt to import metadata helper(s)
                    from dbutils.catalog import get_columns_for_table as _get_cols_fn
                except Exception:
                    _get_cols_fn = None

                # Some legacy code/tests provide `get_columns` instead - check that too
                try:
                    from dbutils.catalog import get_columns as _get_cols_alt
                except Exception:
                    _get_cols_alt = None

                is_str = True
                if _get_cols_fn or _get_cols_alt:
                    try:
                        cols = None
                        if _get_cols_fn:
                            cols = _get_cols_fn(schema, table)
                        elif _get_cols_alt:
                            cols = _get_cols_alt(schema, table)

                        # find the column definition
                        found = None
                        if cols:
                            for c in cols:
                                if isinstance(c, dict):
                                    if c.get("COLNAME") == column_filter or c.get("name") == column_filter:
                                        found = c
                                        break
                                else:
                                    if getattr(c, "name", None) == column_filter:
                                        found = c
                                        break

                        if found:
                            typename = (
                                found.get("TYPENAME") if isinstance(found, dict) else getattr(found, "typename", None)
                            )
                            is_str = self._is_string_type(typename)
                    except Exception:
                        # best-effort fallback
                        is_str = True

                # Quote or not
                if is_str:
                    safe_val = str(value).replace("'", "''")
                    where = f" WHERE {column_filter} = '{safe_val}'"
                else:
                    where = f" WHERE {column_filter} = {value}"

            # Include offset for pagination when requested (OFFSET <n> ROWS)
            # NOTE: OFFSET requires a stable ORDER BY for predictable results
            # We'll order by the first column as a simple heuristic
            # TODO: Use primary key columns if available for better performance
            order_by = " ORDER BY 1"

            if int(start_offset) > 0:
                sql = f"SELECT * FROM {tbl}{where}{order_by} OFFSET {int(start_offset)} ROWS FETCH FIRST {int(limit)} ROWS ONLY"
            else:
                sql = f"SELECT * FROM {tbl}{where}{order_by} FETCH FIRST {int(limit)} ROWS ONLY"

            # Run the query
            rows = []
            try:
                rows = query_runner(sql) or []
            except Exception as e:
                # If in mock mode, generate mock data instead of failing
                if use_mock and table_columns:
                    rows = []
                    for row_id in range(int(start_offset), int(start_offset) + int(limit)):
                        row_data = {}
                        for i, col in enumerate(table_columns):
                            col_name = col.name
                            # Generate mock data based on column type
                            if "INT" in (col.typename or "").upper():
                                row_data[col_name] = row_id * 100 + i
                            elif "DECIMAL" in (col.typename or "").upper() or "FLOAT" in (col.typename or "").upper():
                                row_data[col_name] = float(row_id) * 10.5 + float(i)
                            elif "DATE" in (col.typename or "").upper():
                                # Generate dates with rotation
                                day = (row_id % 28) + 1
                                month = ((row_id // 28) % 12) + 1
                                row_data[col_name] = f"2024-{month:02d}-{day:02d}"
                            else:
                                # String/default
                                row_data[col_name] = f"{table}.{col_name}.row{row_id}"
                        rows.append(row_data)
                else:
                    # Bubble to error emission
                    self.error_occurred.emit(str(e))
                    return

            # Try to infer columns
            columns = []
            if rows:
                first = rows[0]
                if isinstance(first, dict):
                    columns = list(first.keys())
                else:
                    # if tuples returned, we cannot know column names here; return empty list (UI can use metadata)
                    columns = []

            if self._cancelled:
                return

            self.results_ready.emit(columns, rows)
        except Exception as e:
            self.error_occurred.emit(str(e))


class DataLoaderWorker(QObject):
    """Worker for loading database data in background thread."""

    data_loaded = Signal(object, object, object)  # (tables, columns, all_schemas)
    chunk_loaded = Signal(object, object, int, int)  # (tables_chunk, columns_chunk, loaded, total_est)
    error_occurred = Signal(str)
    progress_updated = Signal(str)
    progress_value = Signal(int, int)  # (current, total)

    def __init__(self):
        super().__init__()

    def load_data(self, schema_filter: Optional[str], use_mock: bool, start_offset: int = 0, use_heavy_mock: bool = False, db_file: Optional[str] = None):
        """Load database data in background thread with granular progress updates and chunked streaming."""
        try:
            # Prefer async loader with pagination to avoid huge initial transfer
            self.progress_updated.emit("Connecting to database…")

            # Use async-aware functions from db_browser for better performance and caching
            from dbutils.db_browser import (
                get_all_tables_and_columns_async,
                load_from_cache,
                save_to_cache,
            )
            from dbutils.catalog import get_tables  # For schema list

            initial_limit = 200
            batch_size = 500
            loaded_total = 0
            estimated_total = 0  # Unknown until we probe

            # Try cache first for the initial chunk
            cached = load_from_cache(schema_filter, limit=initial_limit, offset=int(start_offset))
            if cached:
                tables, columns = cached
            else:
                tables, columns = get_all_tables_and_columns(
                    schema_filter, use_mock, use_cache=True, limit=initial_limit, offset=int(start_offset), use_heavy_mock=use_heavy_mock, db_file=db_file
                )

            loaded_total += len(tables)
            # Emit first chunk immediately so UI becomes usable
            self.progress_updated.emit(f"Loaded {len(tables)} tables (initial chunk)…")
            self.progress_value.emit(1, 3)
            self.chunk_loaded.emit(tables, columns, loaded_total, estimated_total)

            # Estimate total tables count (best effort)
            try:
                # Quick estimate via count query in a worker would require DB call; skip heavy count
                # Use heuristic: if fewer than batch_size returned, we likely loaded all
                if len(tables) < initial_limit:
                    estimated_total = loaded_total
                else:
                    estimated_total = loaded_total + batch_size * 4  # rough placeholder estimate
            except Exception:
                estimated_total = loaded_total

            # Stream remaining tables in batches
            offset = int(start_offset) + initial_limit
            more = True
            while more:
                # Check cache for this page
                cached = load_from_cache(schema_filter, limit=batch_size, offset=offset)
                if cached:
                    t_chunk, c_chunk = cached
                else:
                    t_chunk, c_chunk = get_all_tables_and_columns(
                        schema_filter, use_mock, use_cache=True, limit=batch_size, offset=offset, db_file=db_file
                    )

                if not t_chunk:
                    more = False
                    break

                loaded_total += len(t_chunk)
                self.progress_updated.emit(f"Loaded {loaded_total} tables…")
                # Emit chunk to UI
                self.chunk_loaded.emit(t_chunk, c_chunk, loaded_total, estimated_total)

                # Advance
                offset += len(t_chunk)
                # If this was a short page, we might be done
                if len(t_chunk) < batch_size:
                    more = False

            # After streaming chunks, fetch schemas list (one light query)
            self.progress_updated.emit("Loading available schemas…")
            all_tables = get_tables(mock=use_mock)
            all_schemas = sorted(set(table["TABSCHEMA"] for table in all_tables))

            # Final completion signal (aggregate not required, UI already holds accumulated state)
            self.progress_value.emit(3, 3)
            self.data_loaded.emit([], [], all_schemas)
        except Exception as e:
            self.error_occurred.emit(str(e))


class DataLoaderProcess(QObject):
    """Subprocess-based data loader using QProcess to avoid GIL/UI hitching."""

    data_loaded = Signal(object, object, object)  # (tables, columns, all_schemas)
    chunk_loaded = Signal(object, object, int, int)  # (tables_chunk, columns_chunk, loaded, total_est)
    error_occurred = Signal(str)
    progress_updated = Signal(str)
    progress_value = Signal(int, int)  # (current, total)

    def __init__(self):
        super().__init__()
        self._proc = QProcess()
        self._stdout_buffer = ""
        self._schemas = None
        self._finished_handled = False  # Track if we've already handled the finish event

        # Connect signals if running within Qt
        if QT_AVAILABLE:
            try:
                self._proc.readyReadStandardOutput.connect(self._on_stdout)
            except Exception:
                pass
            try:
                self._proc.readyReadStandardError.connect(self._on_stderr)
            except Exception:
                pass
            try:
                # PySide/PyQt both offer finished(int, QProcess.ExitStatus)
                self._proc.finished.connect(self._on_finished)
            except Exception:
                pass
            try:
                self._proc.errorOccurred.connect(lambda e: self.error_occurred.emit(f"Process error: {e}"))
            except Exception:
                pass

    def start(
        self,
        schema_filter: Optional[str],
        use_mock: bool,
        initial_limit: int = 200,
        batch_size: int = 500,
        start_offset: int = 0,
    ):
        """Start the data loader subprocess and send the initial command."""
        # Launch module as subprocess
        # Check if we're running under uv (UV_PROJECT_DIR env var is set)
        # or if sys.executable can import dbutils, otherwise use fallback
        python_exe = sys.executable
        use_uv = os.environ.get("VIRTUAL_ENV") or os.environ.get("UV_PROJECT_DIR")

        if use_uv:
            # Use uv run to ensure correct environment
            args = ["uv", "run", "python", "-m", "dbutils.gui.data_loader_process"]
            self._proc.start("uv", args[1:])
        else:
            # Set up environment with proper Python path
            try:
                from PySide6.QtCore import QProcessEnvironment
            except ImportError:
                try:
                    from PyQt6.QtCore import QProcessEnvironment
                except ImportError:
                    QProcessEnvironment = None

            if QProcessEnvironment:
                env = QProcessEnvironment.systemEnvironment()
                # Add the src directory to Python path
                src_path = os.path.join(os.path.dirname(__file__), "..", "..")
                python_path = env.value("PYTHONPATH", "")
                if python_path:
                    python_path = f"{src_path}:{python_path}"
                else:
                    python_path = src_path
                env.insert("PYTHONPATH", python_path)
                self._proc.setProcessEnvironment(env)

            args = [python_exe, "-m", "dbutils.gui.data_loader_process"]
            self._proc.start(args[0], args[1:])

        # Don't block on waitForStarted - send command when ready
        # Connect to started signal to send initial command
        if not hasattr(self, "_started_connected"):
            self._proc.started.connect(self._send_start_command)
            self._started_connected = True

        # Store payload for sending after process starts
        payload = {
            "cmd": "start",
            "schema_filter": schema_filter,
            "use_mock": bool(use_mock),
            "initial_limit": int(initial_limit),
            "batch_size": int(batch_size),
            "start_offset": int(start_offset),
        }
        self._start_payload = payload

    def _send_start_command(self):
        """Send start command to process after it has started."""
        if not hasattr(self, "_start_payload") or not self._start_payload:
            return
        payload = self._start_payload
        self._start_payload = None

        data = (json.dumps(payload) + "\n").encode("utf-8")
        try:
            self._proc.write(data)
        except Exception as e:
            self.error_occurred.emit(f"Failed to communicate with data loader: {e}")

    def _on_stdout(self):
        try:
            raw = bytes(self._proc.readAllStandardOutput()).decode("utf-8", errors="ignore")
            if not raw:
                return
            self._stdout_buffer += raw
            lines = self._stdout_buffer.splitlines(keepends=True)
            # Keep incomplete last line in buffer
            if not lines:
                return
            if not lines[-1].endswith("\n"):
                self._stdout_buffer = lines[-1]
                lines = lines[:-1]
            else:
                self._stdout_buffer = ""

            for line in lines:
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                except Exception:
                    continue
                self._handle_message(msg)
        except Exception as e:
            self.error_occurred.emit(f"Stdout processing error: {e}")

    def _on_stderr(self):
        try:
            raw = bytes(self._proc.readAllStandardError()).decode("utf-8", errors="ignore")
            if raw:
                # Log stderr lines - both to console and as error signals
                for part in raw.strip().splitlines():
                    print(f"[SUBPROCESS STDERR] {part}", file=sys.stderr)
                    # Emit as error if it contains "ERROR" or traceback info
                    if "ERROR" in part.upper() or "Traceback" in part or 'File "' in part:
                        self.error_occurred.emit(part)
                    else:
                        self.progress_updated.emit(part)
        except Exception as e:
            print(f"Error reading stderr: {e}", file=sys.stderr)

    def _on_finished(self, code: int, status):  # status type varies
        # Prevent double-handling of finish event
        if self._finished_handled:
            return
        self._finished_handled = True

        print(f"[SUBPROCESS] Process finished with exit code {code}, status={status}", file=sys.stderr)
        # Only emit error if process failed AND we haven't received schemas yet
        # (schemas indicate successful completion)
        if code != 0 and self._schemas is None:
            self.error_occurred.emit(f"Data loader process terminated with exit code {code}")

        # Schedule cleanup of the QProcess object after a short delay
        # This prevents destroying it while Qt is still processing signals
        QTimer.singleShot(100, self._cleanup_process)

    def _cleanup_process(self):
        """Clean up the process after it has finished."""
        try:
            # Process has finished, safe to clean up now
            if hasattr(self, "_proc") and self._proc:
                self._proc.deleteLater()
        except Exception as e:
            print(f"Error cleaning up process: {e}", file=sys.stderr)

    def _handle_message(self, msg: Dict[str, Any]):
        typ = msg.get("type")
        if typ == "progress":
            self.progress_updated.emit(msg.get("message", ""))
            cur = int(msg.get("current", 0))
            tot = int(msg.get("total", 0))
            if tot:
                self.progress_value.emit(cur, tot)
        elif typ == "chunk":
            # Convert payload dicts to TableInfo/ColumnInfo
            t_list = [
                TableInfo(schema=t.get("schema"), name=t.get("name"), remarks=t.get("remarks", ""))
                for t in msg.get("tables", [])
            ]
            c_list = [
                ColumnInfo(
                    schema=c.get("schema"),
                    table=c.get("table"),
                    name=c.get("name"),
                    typename=c.get("typename"),
                    length=c.get("length"),
                    scale=c.get("scale"),
                    nulls=c.get("nulls"),
                    remarks=c.get("remarks", ""),
                )
                for c in msg.get("columns", [])
            ]
            loaded = int(msg.get("loaded", 0))
            est = int(msg.get("estimated", 0)) if msg.get("estimated") is not None else 0
            self.chunk_loaded.emit(t_list, c_list, loaded, est)
        elif typ == "schemas":
            self._schemas = list(msg.get("schemas", []))
        elif typ == "done":
            # Emit final data_loaded with schemas only (tables/columns streamed via chunks)
            self.data_loaded.emit([], [], self._schemas or [])
        elif typ == "error":
            self.error_occurred.emit(msg.get("message", "Unknown error"))


def humanize_schema_name(raw: str) -> str:
    """Return a human-friendly label for a schema name.

    Cosmetic only - does not change the real schema identifier.
    """
    if not raw:
        return ""
    return " ".join(part for part in raw.replace("__", "_").split("_") if part)


class QtDBBrowser(QMainWindow):
    """Main Qt Database Browser application."""

    def __init__(self, schema_filter: Optional[str] = None, use_mock: bool = False, use_heavy_mock: bool = False, db_file: Optional[str] = None):
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
        self.use_heavy_mock = use_heavy_mock
        self.db_file = db_file
        self.tables: List[TableInfo] = []
        self.columns: List[ColumnInfo] = []
        self.table_columns: Dict[str, List[ColumnInfo]] = {}

        # Search state
        self.search_mode = "tables"  # "tables" or "columns"
        self.search_query = ""
        # Inline highlight enabled state - can be toggled by user
        self.inline_highlight_enabled = True
        self.show_non_matching = True
        self.streaming_enabled = True  # Always enabled now

        # Caching for search results to maintain state
        self.search_results_cache: Dict[str, List[SearchResult]] = {}

        # Worker threads / subprocess
        self.search_worker = None
        self.search_thread = None
        self.data_loader_worker = None
        self.data_loader_thread = None
        self.data_loader_proc = None
        self.use_subprocess_loader = True
        # Table contents background worker references
        self.contents_worker = None
        self.contents_thread = None

        self.setup_ui()
        self.setup_menu()
        self.setup_status_bar()

        # Show window immediately, then load data in background
        self.show()
        # Start loading immediately for fastest possible startup
        QTimer.singleShot(0, self.load_data)

    def setup_ui(self):
        """Setup the main user interface."""
        self.setWindowTitle("DB Browser - Qt (Experimental)")
        # Start with a reasonable default size but allow significantly smaller minimums
        self.setGeometry(100, 100, 1000, 700)
        try:
            # Permit compact layouts for smaller screens or tiled dev environments
            self.setMinimumSize(QSize(700, 450))
        except Exception:
            # In non-Qt test stubs, QSize may be unavailable; ignore gracefully
            pass

        # Enable nested and tabbed docks for flexible layout
        self.setDockNestingEnabled(True)

        # Set central widget to empty - we'll use all docks
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        central_widget.hide()  # Hide central widget, using only docks

        # Create all dock widgets
        self.setup_search_dock()
        self.setup_tables_dock()
        self.setup_columns_dock()
        # Add a dock for table contents preview (hidden until a table is selected)
        self.setup_contents_dock()
        self.setup_column_details_dock()

        # Force search dock to compact height after layout is complete
        QTimer.singleShot(0, lambda: self.resizeDocks([self.search_dock], [120], Qt.Orientation.Vertical))

        # Busy overlays for panels
        try:
            self.tables_overlay = BusyOverlay(self.tables_table)
            self.columns_overlay = BusyOverlay(self.columns_table)
        except Exception:
            # If overlays cannot be created (e.g., tests without Qt), ignore gracefully
            self.tables_overlay = None
            self.columns_overlay = None

    def setup_search_dock(self):
        """Create search panel as a dockable widget."""
        self.search_dock = QDockWidget("Search", self)
        self.search_dock.setAllowedAreas(Qt.DockWidgetArea.TopDockWidgetArea | Qt.DockWidgetArea.BottomDockWidgetArea)

        # Prevent the dock from being resized too large
        self.search_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable | QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )

        # Create search panel content
        search_widget = self.create_search_panel()

        # Set explicit maximum height to prevent dock from expanding
        search_widget.setMaximumHeight(120)

        self.search_dock.setWidget(search_widget)

        # Set size policy on the dock itself
        self.search_dock.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        # Add to main window at top
        self.addDockWidget(Qt.DockWidgetArea.TopDockWidgetArea, self.search_dock)

    def setup_tables_dock(self):
        """Create tables panel as a dockable widget."""
        self.tables_dock = QDockWidget("Tables", self)
        self.tables_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea
            | Qt.DockWidgetArea.RightDockWidgetArea
            | Qt.DockWidgetArea.TopDockWidgetArea
            | Qt.DockWidgetArea.BottomDockWidgetArea
        )

        # Create tables panel content
        tables_widget = self.create_tables_panel()
        self.tables_dock.setWidget(tables_widget)

        # Add to main window on left
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.tables_dock)

    def setup_columns_dock(self):
        """Create columns panel as a dockable widget."""
        self.columns_dock = QDockWidget("Columns", self)
        self.columns_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea
            | Qt.DockWidgetArea.RightDockWidgetArea
            | Qt.DockWidgetArea.TopDockWidgetArea
            | Qt.DockWidgetArea.BottomDockWidgetArea
        )

        # Create columns panel content
        columns_widget = self.create_columns_panel()
        self.columns_dock.setWidget(columns_widget)

        # Split with tables dock to create side-by-side layout
        self.splitDockWidget(self.tables_dock, self.columns_dock, Qt.Orientation.Horizontal)

    def create_search_panel(self) -> QWidget:
        """Create the search input panel."""
        panel = QWidget()
        panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout = QVBoxLayout(panel)
        layout.setSpacing(4)
        layout.setContentsMargins(8, 8, 8, 6)

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
        # Inline highlight toggle
        self.highlight_check = QCheckBox("Inline Highlight")
        self.highlight_check.setChecked(True)
        self.highlight_check.toggled.connect(self.on_highlight_toggled)
        options_row.addWidget(self.highlight_check)
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

        # Set compact size constraints for the search panel
        panel.setMinimumHeight(80)
        panel.setMaximumHeight(120)

        return panel

    pass

    def create_tables_panel(self) -> QWidget:
        """Create the tables panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        # Tables table
        self.tables_table = QTableView()
        self.tables_model = DatabaseModel()
        self.tables_proxy = QSortFilterProxyModel()
        self.tables_proxy.setSourceModel(self.tables_model)
        self.tables_table.setModel(self.tables_proxy)
        # Delegate to render highlighted search matches (only if enabled)
        try:
            self.tables_delegate = None
            if getattr(self, "inline_highlight_enabled", True):
                self.tables_delegate = HighlightDelegate(self.tables_table, lambda: self.search_query)
                self.tables_table.setItemDelegate(self.tables_delegate)
        except Exception:
            # In environments without Qt installed (tests), gracefully continue
            self.tables_delegate = None

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
        # Allow slightly tighter minimums so the window can shrink sensibly
        header.setMinimumSectionSize(120)

        self.tables_table.selectionModel().selectionChanged.connect(self.on_table_selected)

        layout.addWidget(self.tables_table)

        return panel

    def create_columns_panel(self) -> QWidget:
        """Create the columns panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        # Columns table
        self.columns_table = QTableView()
        self.columns_model = ColumnModel()
        self.columns_table.setModel(self.columns_model)
        # Delegate to render highlighted search matches (columns view) — only if enabled
        try:
            self.columns_delegate = None
            if getattr(self, "inline_highlight_enabled", True):
                self.columns_delegate = HighlightDelegate(self.columns_table, lambda: self.search_query)
                self.columns_table.setItemDelegate(self.columns_delegate)
        except Exception:
            self.columns_delegate = None

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
        # Allow slightly tighter minimums so the window can shrink sensibly
        header.setMinimumSectionSize(120)

        layout.addWidget(self.columns_table)

        return panel

    def create_contents_panel(self) -> QWidget:
        """Create the table contents preview panel (rows preview)."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        # Controls: limit, column selector and filter
        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(6)

        ctrl_row.addWidget(QLabel("Limit:"))
        # Try to get QSpinBox from the mapped Qt widgets. If not available,
        # create a tiny fallback so tests can still exercise logic without Qt.
        try:
            QSpinBox = getattr(_QtWidgets, "QSpinBox", None)
        except Exception:
            QSpinBox = None

        if QSpinBox is not None:
            self.contents_limit = QSpinBox()
            try:
                self.contents_limit.setRange(1, 1000)
            except Exception:
                pass
            try:
                self.contents_limit.setValue(25)
            except Exception:
                pass
            try:
                ctrl_row.addWidget(self.contents_limit)
            except Exception:
                pass
        else:
            # Minimal fallback object providing setValue/value API used in code
            class _FakeSpin:
                def __init__(self, value=25):
                    self._v = value

                def setRange(self, a, b):
                    pass

                def setValue(self, v):
                    self._v = v

                def value(self):
                    return self._v

            self.contents_limit = _FakeSpin(25)
            # No widget to add

        ctrl_row.addWidget(QLabel("Filter column:"))
        # Mode for header/selector display: Names or Descriptions
        self.contents_display_mode = QComboBox()
        try:
            self.contents_display_mode.addItem("Names")
            self.contents_display_mode.addItem("Descriptions")
            # Update column selector and headers when user toggles display mode
            try:
                self.contents_display_mode.currentIndexChanged.connect(
                    lambda _: self._on_contents_display_mode_changed()
                )
            except Exception:
                pass
        except Exception:
            # Some test environments may stub QComboBox - ignore
            pass
        ctrl_row.addWidget(self.contents_display_mode)

        self.contents_column_combo = QComboBox()
        ctrl_row.addWidget(self.contents_column_combo)

        ctrl_row.addWidget(QLabel("Filter value:"))
        self.contents_filter_input = QLineEdit()
        self.contents_filter_input.setPlaceholderText("e.g. 'ABC' or 123")
        ctrl_row.addWidget(self.contents_filter_input)

        self.contents_apply_btn = QPushButton("Apply")
        self.contents_apply_btn.clicked.connect(lambda: self._apply_contents_filter())
        ctrl_row.addWidget(self.contents_apply_btn)

        # Add a lightweight spacer
        ctrl_row.addStretch()

        layout.addLayout(ctrl_row)

        # Contents table
        self.contents_table = QTableView()
        self.contents_model = TableContentsModel()
        self.contents_table.setModel(self.contents_model)

        # Configure view - read-only preview
        self.contents_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.contents_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.contents_table.setAlternatingRowColors(True)
        self.contents_table.setShowGrid(False)
        self.contents_table.setWordWrap(False)

        self.contents_table.verticalHeader().setDefaultSectionSize(28)
        self.contents_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.contents_table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.contents_table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)

        header = self.contents_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionsMovable(True)
        header.setHighlightSections(False)

        # Connect scroll events to support infinite scroll (load more on bottom)
        try:
            sb = self.contents_table.verticalScrollBar()
            sb.valueChanged.connect(lambda v: self._on_contents_scrolled(v))
        except Exception:
            # In test environments scrollbars may be stubs; ignore
            pass

        layout.addWidget(self.contents_table)

        # Loading indicator for pagination (hidden by default)
        loading_container = QWidget()
        loading_layout = QHBoxLayout(loading_container)
        loading_layout.setContentsMargins(10, 8, 10, 8)

        # Create a spinner-style progress bar with better styling
        self.contents_loading_indicator = QProgressBar()
        self.contents_loading_indicator.setMaximum(0)  # Indeterminate mode (spinner)
        self.contents_loading_indicator.setTextVisible(False)
        self.contents_loading_indicator.setFixedHeight(6)
        self.contents_loading_indicator.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 3px;
                background-color: #e0e0e0;
            }
            QProgressBar::chunk {
                background-color: #4a90e2;
                border-radius: 3px;
            }
        """)

        # Add icon and label
        loading_label = QLabel("⟳ Loading more rows...")
        loading_label.setStyleSheet("color: #666; font-size: 11px; font-style: italic;")

        loading_layout.addStretch()
        loading_layout.addWidget(loading_label)
        loading_layout.addWidget(self.contents_loading_indicator, 2)
        loading_layout.addStretch()

        loading_container.setVisible(False)
        loading_container.setStyleSheet("background-color: #f8f8f8; border-top: 1px solid #ddd;")
        self.contents_loading_container = loading_container

        layout.addWidget(loading_container)

        return panel

    def setup_contents_dock(self):
        """Create the Table Contents dock that shows a preview of rows for selected table."""
        self.contents_dock = QDockWidget("Table Contents", self)
        self.contents_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea
            | Qt.DockWidgetArea.RightDockWidgetArea
            | Qt.DockWidgetArea.TopDockWidgetArea
            | Qt.DockWidgetArea.BottomDockWidgetArea
        )

        contents_widget = self.create_contents_panel()
        self.contents_dock.setWidget(contents_widget)

        # Add to main window on right side and tabify with columns dock
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.contents_dock)
        try:
            # Tabify so Columns and Contents share the same stacked area
            if getattr(self, "columns_dock", None):
                self.tabifyDockWidget(self.columns_dock, self.contents_dock)
        except Exception:
            # Some Qt variants or test environments may not support tabify; ignore
            pass

        # Hide contents by default (user can show it with the View menu)
        self.contents_dock.hide()

    def setup_column_details_dock(self):
        """Create column details as a dockable widget."""
        # Create dock widget
        self.column_details_dock = QDockWidget("Column Details", self)
        self.column_details_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea
            | Qt.DockWidgetArea.RightDockWidgetArea
            | Qt.DockWidgetArea.TopDockWidgetArea
            | Qt.DockWidgetArea.BottomDockWidgetArea
        )

        # Create the content widget
        dock_widget = QWidget()
        layout = QVBoxLayout(dock_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Create a text edit widget for displaying column details
        self.column_details_text = QTextEdit()
        self.column_details_text.setReadOnly(True)
        self.column_details_text.setPlaceholderText("Select a table to view column details...")

        # Style the text edit for better readability
        self.column_details_text.setStyleSheet("""
            QTextEdit {
                font-family: 'Courier New', monospace;
                font-size: 10pt;
                background-color: #f8f9fa;
                border: 1px solid #ddd;
                padding: 8px;
            }
        """)

        layout.addWidget(self.column_details_text)
        self.column_details_dock.setWidget(dock_widget)

        # Add to main window on the right side, initially hidden
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.column_details_dock)
        self.column_details_dock.hide()

    def setup_menu(self):
        """Setup the menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")

        refresh_action = QAction("Refresh Data", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self.load_data)
        file_menu.addAction(refresh_action)

        refresh_schemas_action = QAction("Rebuild Schema List", self)
        refresh_schemas_action.setShortcut("Shift+F5")
        refresh_schemas_action.triggered.connect(self.rebuild_schema_cache)
        file_menu.addAction(refresh_schemas_action)

        clear_cache_action = QAction("Clear All Caches", self)
        clear_cache_action.setShortcut("Ctrl+Shift+C")
        clear_cache_action.triggered.connect(self.clear_all_caches)
        file_menu.addAction(clear_cache_action)

        file_menu.addSeparator()

        export_action = QAction("Export...", self)
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self.show_export_dialog)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # View menu
        view_menu = menubar.addMenu("View")

        toggle_search_action = QAction("Show Search Panel", self)
        toggle_search_action.setShortcut("Ctrl+Shift+S")
        toggle_search_action.setCheckable(True)
        toggle_search_action.setChecked(True)
        toggle_search_action.triggered.connect(self.toggle_search_dock)
        view_menu.addAction(toggle_search_action)
        self.toggle_search_action = toggle_search_action

        toggle_tables_action = QAction("Show Tables Panel", self)
        toggle_tables_action.setShortcut("Ctrl+Shift+T")
        toggle_tables_action.setCheckable(True)
        toggle_tables_action.setChecked(True)
        toggle_tables_action.triggered.connect(self.toggle_tables_dock)
        view_menu.addAction(toggle_tables_action)
        self.toggle_tables_action = toggle_tables_action

        toggle_columns_action = QAction("Show Columns Panel", self)
        toggle_columns_action.setShortcut("Ctrl+Shift+C")
        toggle_columns_action.setCheckable(True)
        toggle_columns_action.setChecked(True)
        toggle_columns_action.triggered.connect(self.toggle_columns_dock)
        view_menu.addAction(toggle_columns_action)
        self.toggle_columns_action = toggle_columns_action

        toggle_details_action = QAction("Show Column Details", self)
        toggle_details_action.setShortcut("Ctrl+D")
        toggle_details_action.setCheckable(True)
        toggle_details_action.setChecked(False)
        toggle_details_action.triggered.connect(self.toggle_column_details)
        view_menu.addAction(toggle_details_action)
        self.toggle_details_action = toggle_details_action

        toggle_contents_action = QAction("Show Table Contents", self)
        toggle_contents_action.setShortcut("Ctrl+Shift+V")
        toggle_contents_action.setCheckable(True)
        toggle_contents_action.setChecked(False)
        toggle_contents_action.triggered.connect(lambda: self.toggle_contents_dock())
        view_menu.addAction(toggle_contents_action)
        self.toggle_contents_action = toggle_contents_action

        view_menu.addSeparator()

        toggle_streaming = QAction("Toggle Streaming Search", self)
        toggle_streaming.setShortcut("X")
        toggle_streaming.triggered.connect(self.toggle_streaming)
        view_menu.addAction(toggle_streaming)

        toggle_non_matching = QAction("Show/Hide Non-Matching", self)
        toggle_non_matching.setShortcut("H")
        toggle_non_matching.triggered.connect(self.toggle_show_non_matching)
        view_menu.addAction(toggle_non_matching)

        # Settings menu
        settings_menu = menubar.addMenu("Settings")
        manage_providers_action = QAction("Manage JDBC Providers…", self)
        manage_providers_action.setShortcut("Ctrl+J")

        def _open_providers():
            try:
                from dbutils.gui.provider_config_dialog import ProviderConfigDialog

                dlg = ProviderConfigDialog(self)
                dlg.exec()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Unable to open provider configuration: {e}")

        manage_providers_action.triggered.connect(_open_providers)
        settings_menu.addAction(manage_providers_action)

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
        """Load database data using a separate process (preferred) or thread fallback."""
        self.status_label.setText("Loading data...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 100)  # Determinate progress
        self.progress_bar.setValue(0)

        # Show overlays and disable inputs to indicate background work (defer to avoid blocking)
        try:
            if getattr(self, "tables_overlay", None):
                QTimer.singleShot(0, lambda: self.tables_overlay.show_with_message("Loading tables…"))
            if getattr(self, "columns_overlay", None):
                QTimer.singleShot(0, lambda: self.columns_overlay.show_with_message("Preparing view…"))
            # Disable primary inputs during load (deferred)
            QTimer.singleShot(0, lambda: self.search_input.setEnabled(False))
            QTimer.singleShot(0, lambda: self.schema_combo.setEnabled(False))
        except Exception:
            pass

        # Cancel any existing data loader thread/process
        if self.data_loader_worker:
            self.data_loader_worker = None

        if self.data_loader_thread:
            self.data_loader_thread.quit()
            # Don't block UI with wait() - let it finish asynchronously
            self.data_loader_thread.deleteLater()
            self.data_loader_thread = None

        if self.data_loader_proc and QT_AVAILABLE:
            try:
                # Only terminate if actually running - don't block waiting
                if hasattr(self.data_loader_proc._proc, "state") and self.data_loader_proc._proc.state() != 0:
                    self.data_loader_proc._proc.terminate()
                    # Don't block with waitForFinished - let it terminate async
            except Exception:
                pass
            self.data_loader_proc = None

        # Compute a resume offset so re-starting the loader (for example
        # when the user changes batch sizes) does not re-send already
        # loaded tables. We want the UI to be seamless and keep existing
        # results while the loader continues from where it left off.
        start_offset = len(self.tables) if getattr(self, "tables", None) else 0

        # Use thread-based worker (disable subprocess for now due to path issues)
        self.data_loader_worker = DataLoaderWorker()
        self.data_loader_thread = QThread()
        self.data_loader_worker.data_loaded.connect(self.on_data_loaded)
        self.data_loader_worker.chunk_loaded.connect(self.on_data_chunk)
        self.data_loader_worker.error_occurred.connect(self.on_data_load_error)
        self.data_loader_worker.progress_updated.connect(self.status_label.setText)
        self.data_loader_worker.progress_value.connect(self.on_data_progress)
        self.data_loader_thread.started.connect(
            lambda: self.data_loader_worker.load_data(self.schema_filter, self.use_mock, start_offset=start_offset, use_heavy_mock=self.use_heavy_mock, db_file=self.db_file)
        )
        self.data_loader_thread.start()

    def on_data_progress(self, current: int, total: int):
        """Handle data loading progress updates."""
        progress_percent = int((current / total) * 100) if total > 0 else 0
        self.progress_bar.setValue(progress_percent)

    def on_data_loaded(self, tables, columns, all_schemas=None):
        """Handle data loaded from background thread."""
        try:
            # Finalization step: only schemas are provided at this point in streaming mode
            if tables and columns:
                # Fallback if full data was sent (non-streaming path)
                self.tables = tables
                self.columns = columns
            if all_schemas:
                self.all_schemas = all_schemas  # Store all available schemas

            # Ensure table-columns mapping exists
            if not hasattr(self, "table_columns") or self.table_columns is None:
                self.table_columns = {}

            # Ensure tables and columns lists exist
            if not hasattr(self, "tables") or self.tables is None:
                self.tables = []
            if not hasattr(self, "columns") or self.columns is None:
                self.columns = []

            # Defer all UI updates to avoid blocking on completion
            def finalize_load():
                try:
                    # Update UI if we received data (e.g., non-streaming path)
                    if self.tables or self.columns:
                        self.tables_model.set_data(self.tables, self.table_columns)
                        if getattr(self, "tables_proxy", None):
                            self.tables_proxy.invalidate()
                    if hasattr(self, "all_schemas") and self.all_schemas:
                        self.update_schema_combo()

                    self.status_label.setText(f"Loaded {len(self.tables)} tables, {len(self.columns)} columns")
                    self.progress_bar.setValue(100)
                    # Hide progress bar after brief delay
                    QTimer.singleShot(300, lambda: self.progress_bar.setVisible(False))

                    # Hide overlays and re-enable inputs
                    if getattr(self, "tables_overlay", None):
                        self.tables_overlay.hide()
                    if getattr(self, "columns_overlay", None):
                        self.columns_overlay.hide()
                    self.search_input.setEnabled(True)
                    self.schema_combo.setEnabled(True)
                except Exception:
                    pass

            # Defer to next event loop to avoid blocking
            QTimer.singleShot(0, finalize_load)

            # Clean up thread without blocking
            if self.data_loader_thread:
                self.data_loader_thread.quit()
                self.data_loader_thread.deleteLater()
                self.data_loader_thread = None
                self.data_loader_worker = None

            # Clean up subprocess - wait for it to finish properly
            if self.data_loader_proc and QT_AVAILABLE:
                try:
                    # Don't destroy the QProcess here - it will clean up after the process exits
                    # Destroying it here sends SIGTERM to the still-running process
                    # Just disconnect signals to prevent further processing
                    pass
                except Exception:
                    pass

        except Exception as e:
            # Defer error handling to avoid blocking
            def handle_error():
                try:
                    self.status_label.setText(f"Error processing data: {e}")
                    self.progress_bar.setVisible(False)

                    # Hide overlays and re-enable inputs on error
                    if getattr(self, "tables_overlay", None):
                        self.tables_overlay.hide()
                    if getattr(self, "columns_overlay", None):
                        self.columns_overlay.hide()
                    self.search_input.setEnabled(True)
                    self.schema_combo.setEnabled(True)
                except Exception:
                    pass

            QTimer.singleShot(0, handle_error)

            # Clean up thread
            if self.data_loader_thread:
                self.data_loader_thread.quit()
                # Don't block - clean up asynchronously
                self.data_loader_thread.deleteLater()
                self.data_loader_thread = None
                self.data_loader_worker = None

            # Clean up subprocess
            if self.data_loader_proc and QT_AVAILABLE:
                try:
                    # Only terminate if actually running - don't block
                    if hasattr(self.data_loader_proc._proc, "state") and self.data_loader_proc._proc.state() != 0:
                        self.data_loader_proc._proc.terminate()
                        # Don't block with waitForFinished
                except Exception:
                    pass
                self.data_loader_proc = None

    def on_data_load_error(self, error: str):
        """Handle data loading errors."""
        self.status_label.setText(f"Error loading data: {error}")
        self.progress_bar.setVisible(False)

        # Hide overlays and re-enable inputs
        try:
            if getattr(self, "tables_overlay", None):
                self.tables_overlay.hide()
            if getattr(self, "columns_overlay", None):
                self.columns_overlay.hide()
            self.search_input.setEnabled(True)
            self.schema_combo.setEnabled(True)
        except Exception:
            pass

        # Clean up thread
        if self.data_loader_thread:
            self.data_loader_thread.quit()
            # Don't block - clean up asynchronously
            self.data_loader_thread.deleteLater()
            self.data_loader_thread = None
            self.data_loader_worker = None

        # Clean up subprocess
        if self.data_loader_proc and QT_AVAILABLE:
            try:
                self.data_loader_proc._proc.terminate()
            except Exception:
                pass
            self.data_loader_proc = None

    def on_data_chunk(self, tables_chunk, columns_chunk, loaded: int, total_est: int):
        """Handle streaming chunk of tables/columns loaded in background."""
        try:
            # Initialize data structures if first chunk
            if not hasattr(self, "tables") or self.tables is None:
                self.tables = []
            if not hasattr(self, "columns") or self.columns is None:
                self.columns = []
            if not hasattr(self, "table_columns") or self.table_columns is None:
                self.table_columns = {}

            first_chunk = len(self.tables) == 0 and len(self.columns) == 0

            # Append new data (fast operation)
            self.tables.extend(tables_chunk or [])
            self.columns.extend(columns_chunk or [])

            for col in columns_chunk or []:
                table_key = f"{col.schema}.{col.table}"
                if table_key not in self.table_columns:
                    self.table_columns[table_key] = []
                self.table_columns[table_key].append(col)

            # Only update model on first chunk and every 5th chunk to reduce UI updates
            # This dramatically reduces hitching during initial load
            chunk_count = getattr(self, "_chunk_count", 0) + 1
            self._chunk_count = chunk_count

            should_update_ui = first_chunk or (chunk_count % 5 == 0)

            if should_update_ui:
                # Defer model update to avoid blocking on beginResetModel
                # Use timer with 0ms delay to run after current event processing
                if not hasattr(self, "_model_update_timer"):
                    self._model_update_timer = QTimer()
                    self._model_update_timer.setSingleShot(True)
                    self._model_update_timer.timeout.connect(self._update_model)
                # Schedule update for next event loop iteration
                self._model_update_timer.start(0)

            # After first chunk, enable UI immediately for interaction
            if first_chunk:
                try:
                    if getattr(self, "tables_overlay", None):
                        self.tables_overlay.hide()
                    if getattr(self, "columns_overlay", None):
                        self.columns_overlay.hide()
                    self.search_input.setEnabled(True)
                    self.schema_combo.setEnabled(True)
                except Exception:
                    pass

            # Defer search updates to avoid blocking - only on larger chunks
            if hasattr(self, "search_query") and self.search_query and self.search_query.strip():
                if should_update_ui:
                    # Use timer to defer search so UI stays responsive
                    if not hasattr(self, "_search_update_timer"):
                        self._search_update_timer = QTimer()
                        self._search_update_timer.setSingleShot(True)
                        self._search_update_timer.timeout.connect(self._deferred_search_update)
                    # Restart timer - only search after chunks stop coming
                    self._search_update_timer.start(150)

            # Update progress bar (lightweight operation)
            if total_est and total_est > 0:
                pct = max(1, min(100, int((loaded / total_est) * 100)))
                self.progress_bar.setValue(pct)

        except Exception as e:
            self.status_label.setText(f"Chunk processing error: {e}")

    def _update_model(self):
        """Deferred model update to avoid blocking during chunk processing."""
        try:
            # Update model with current data
            if hasattr(self, "tables") and hasattr(self, "table_columns"):
                self.tables_model.set_data(self.tables, self.table_columns)
                # Defer invalidate to avoid blocking
                if getattr(self, "tables_proxy", None):
                    QTimer.singleShot(0, self.tables_proxy.invalidate)
        except Exception:
            pass

    def _deferred_search_update(self):
        """Deferred search update to avoid blocking during chunk loading."""
        try:
            if hasattr(self, "search_query") and self.search_query and self.search_query.strip():
                # Clear cache for current query
                cache_key = f"{self.search_mode}:{self.search_query.lower()}"
                if cache_key in self.search_results_cache:
                    del self.search_results_cache[cache_key]
                # Trigger search update with new data
                self._trigger_incremental_search()
        except Exception:
            pass

    def update_schema_combo(self):
        """Update schema combo box with all available schemas.

        The combo will show a friendly label containing both the schema
        name and a hint of how many tables are present in that schema,
        while storing the actual schema name as user data. This avoids
        ambiguity and ensures the selected schema_filter remains the
        proper schema name when users pick a human readable label.
        """
        # Use all available schemas instead of just those in current data
        schemas = (
            self.all_schemas
            if hasattr(self, "all_schemas") and self.all_schemas
            else sorted(set(table.schema for table in self.tables))
        )

        # Preserve the currently selected schema filter during update
        current_filter = self.schema_filter

        # Block signals to prevent triggering on_schema_changed during update
        self.schema_combo.blockSignals(True)
        try:
            self.schema_combo.clear()
            # Add 'All Schemas' with explicit userData=None so we can detect it later
            self.schema_combo.addItem("All Schemas", None)

            # Cache schema counts if not already computed
            if not hasattr(self, "_schema_counts_cache"):
                self._schema_counts_cache = {}

            # Only compute counts if we have a reasonable number of tables
            # Skip count computation during initial load to avoid blocking
            compute_counts = len(self.tables) < 5000 if hasattr(self, "tables") else False

            # Add a friendly display string for each schema, but attach the
            # real schema name as the QComboBox itemData so we don't need to
            # parse the shown label when the selection changes.
            for schema_entry in schemas:
                # Support both string schemas and richer dict entries produced by the data loader
                if isinstance(schema_entry, dict):
                    name = schema_entry.get("name")
                    raw_count = schema_entry.get("count")
                    # Only display count if it's a positive integer - avoid showing 0 tables
                    try:
                        rc = int(raw_count) if raw_count is not None else None
                    except Exception:
                        rc = None
                    count = rc if rc and rc > 0 else None
                else:
                    name = schema_entry
                    count = None
                    # Use cached count if available
                    if name in self._schema_counts_cache:
                        count = self._schema_counts_cache[name]
                    elif compute_counts and self.tables:
                        # Only compute if we have few enough tables
                        computed = sum(1 for t in self.tables if getattr(t, "schema", None) == name)
                        count = computed if computed > 0 else None
                        self._schema_counts_cache[name] = count

                # For Qt dropdown we want to show the exact schema name coming
                # from the database so users can match the DB value exactly.
                display_name = name
                if count is None:
                    label = f"{display_name}"
                else:
                    label = f"{display_name} ({count} table{'s' if count != 1 else ''})"

                # store the actual schema name as userData
                self.schema_combo.addItem(label, name)

            # Restore the selection based on the current filter using stored userData
            if current_filter:
                index = self.schema_combo.findData(current_filter)
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
        finally:
            # Re-enable signals
            self.schema_combo.blockSignals(False)

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
            try:
                # Check if thread is still valid and running
                if hasattr(self.search_thread, 'isRunning') and self.search_thread.isRunning():
                    self.search_thread.quit()
                    # Don't block with wait() - let it finish async
                    self.search_thread.deleteLater()
                else:
                    # Thread is not running, safe to clean up
                    self.search_thread.deleteLater()
            except Exception:
                # Thread may already be deleted or invalid, ignore gracefully
                pass

        if not text.strip():
            # Clear search and clear cache
            self.tables_model.set_search_results([])
            self.status_label.setText("Ready")
            # Clear cache when search is cleared
            self.search_results_cache.clear()
            return

        # Use a timer to debounce search input and avoid UI locking
        if hasattr(self, "_search_timer"):
            self._search_timer.stop()

        # Create or reuse the timer
        if not hasattr(self, "_search_timer"):
            self._search_timer = QTimer()
            self._search_timer.setSingleShot(True)
            self._search_timer.timeout.connect(self.start_streaming_search)
        else:
            self._search_timer.timeout.disconnect()
            self._search_timer.timeout.connect(self.start_streaming_search)

        # Start new search after a delay to prevent rapid searches
        # Use shorter delay for more responsive experience
        self._search_timer.start(150)  # Reduced from 200ms to 150ms

    def start_streaming_search(self):
        """Start streaming search in worker thread."""
        self.status_label.setText("Searching...")
        self.search_progress.setVisible(True)
        self.search_progress.setRange(0, 100)

        # Show overlay over the tables while searching
        try:
            if getattr(self, "tables_overlay", None):
                self.tables_overlay.show_with_message("Searching…")
        except Exception:
            pass

        # Cancel any existing search first to prevent multiple threads
        if self.search_worker:
            self.search_worker.cancel_search()

        if self.search_thread:
            try:
                # Check if thread is still valid and running
                if hasattr(self.search_thread, 'isRunning') and self.search_thread.isRunning():
                    self.search_thread.quit()
                    # Don't block UI - let it quit asynchronously
                    self.search_thread.requestInterruption()
                else:
                    # Thread is not running, safe to clean up
                    self.search_thread.deleteLater()
            except Exception:
                # Thread may already be deleted or invalid, ignore gracefully
                pass

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

    def _trigger_incremental_search(self):
        """Trigger search immediately without debounce - used for incremental updates during data loading."""
        if not self.search_query or not self.search_query.strip():
            return

        # Cancel any existing search
        if self.search_worker:
            self.search_worker.cancel_search()

        if self.search_thread:
            try:
                # Check if thread is still valid and running
                if hasattr(self.search_thread, 'isRunning') and self.search_thread.isRunning():
                    self.search_thread.quit()
                    # Don't block - let it finish asynchronously
                    self.search_thread.requestInterruption()
                else:
                    # Thread is not running, safe to clean up
                    self.search_thread.deleteLater()
            except Exception:
                # Thread may already be deleted or invalid, ignore gracefully
                pass

        # Create worker and thread
        self.search_worker = SearchWorker()
        self.search_thread = QThread()

        # Move worker to thread
        self.search_worker.moveToThread(self.search_thread)

        # Connect signals
        self.search_worker.results_ready.connect(self.on_search_results)
        self.search_worker.search_complete.connect(self.on_incremental_search_complete)
        self.search_worker.error_occurred.connect(self.on_search_error)

        # Start thread
        self.search_thread.started.connect(
            lambda: self.search_worker.perform_search(self.tables, self.columns, self.search_query, self.search_mode)
        )
        self.search_thread.start()

    def on_search_results(self, results: List[SearchResult]):
        """Handle streaming search results."""
        # Columns-mode special-case: when a column search is active and
        # returns zero matches, the UI previously fell back to showing all
        # tables. Respect the "show_non_matching" toggle: if the user
        # wants non-matching tables hidden and a column search returns no
        # matches, present an active-empty result set so the table view is
        # empty instead of showing all tables.
        if self.search_mode == "columns" and (not results):
            if self.search_query.strip() and not self.show_non_matching:
                # Indicate active search with zero matches.
                self.tables_model.set_search_results(None)
            else:
                # No search active or user wants non-matching shown — clear
                # any active search state so the full tables list appears.
                self.tables_model.set_search_results([])
        else:
            # If we're in column search mode and the incoming result batch
            # contains only column SearchResult items (streaming/interim
            # updates will often do that), synthesize per-table aggregate
            # SearchResult entries so tables that contain matching columns
            # appear as hits (indirect matches). This also ensures the
            # 'show_non_matching' toggle behaves sensibly during streaming.
            if self.search_mode == "columns" and results:
                has_table = any(isinstance(r.item, TableInfo) for r in results)
                # If results are only ColumnInfo items, synthesize aggregates
                if not has_table:
                    table_map = {}
                    col_results = []
                    for r in results:
                        if isinstance(r.item, ColumnInfo):
                            table_key = r.table_key or f"{r.item.schema}.{r.item.table}"
                            table_map.setdefault(table_key, []).append(r)
                            col_results.append(r)

                    agg_results = []
                    # Find table objects for these keys from current data
                    for t_key, cols in table_map.items():
                        schema, name = t_key.split(".", 1) if "." in t_key else (None, t_key)
                        t_obj = next(
                            (
                                t
                                for t in self.tables
                                if getattr(t, "schema", None) == schema and getattr(t, "name", None) == name
                            ),
                            None,
                        )
                        if t_obj:
                            agg_results.append(
                                SearchResult(
                                    item=t_obj, match_type="column", relevance_score=float(len(cols)), table_key=t_key
                                )
                            )

                    # Sort aggregates by descending match count and columns by score
                    agg_results.sort(key=lambda r: -r.relevance_score)
                    col_results_sorted = sorted(col_results, key=lambda r: -r.relevance_score)

                    combined = agg_results + col_results_sorted
                    # If show_non_matching is False we present only matches (which
                    # combined will be). If show_non_matching is True we still
                    # display combined matches — non-matching tables are not part
                    # of streaming results so nothing extra to show here.
                    self.tables_model.set_search_results(combined)
                    results = combined
                else:
                    self.tables_model.set_search_results(results)
            else:
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

        # Hide table overlay after search completes
        try:
            if getattr(self, "tables_overlay", None):
                self.tables_overlay.hide()
        except Exception:
            pass

    def on_incremental_search_complete(self):
        """Handle incremental search completion during data loading - quieter than normal search complete."""
        results_count = self.tables_model.rowCount()

        # Update status to show search is updating with new data
        self.status_label.setText(f"Found {results_count} results (loading more data...)")

        # Don't cache incremental results - they're incomplete
        # Don't hide progress or overlay - data is still loading

    def on_search_error(self, error: str):
        """Handle search errors."""
        self.search_progress.setVisible(False)
        self.status_label.setText(f"Search error: {error}")

        # Hide overlay on error
        try:
            if getattr(self, "tables_overlay", None):
                self.tables_overlay.hide()
        except Exception:
            pass

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
            self.update_column_details(table_key, columns)
            # Also load a small preview of table contents to show in the
            # Table Contents dock. This is a lightweight fetch and will not
            # block the UI if the environment provides a responsive query
            # runner. Errors are caught so tests and headless environments
            # remain stable.
            try:
                # Defer dock show and contents loading to prevent UI hitching
                # Use QTimer.singleShot to execute after the current event completes
                def _deferred_contents_load():
                    try:
                        # Show the dock automatically when a table is selected
                        if getattr(self, "contents_dock", None) and not self.contents_dock.isVisible():
                            try:
                                self.contents_dock.show()
                                if getattr(self, "toggle_contents_action", None):
                                    self.toggle_contents_action.setChecked(True)
                                    self.toggle_contents_action.setText("Hide Table Contents")
                            except Exception:
                                pass

                        # Populate contents column selector
                        try:
                            col_combo = getattr(self, "contents_column_combo", None)
                            if col_combo is not None:
                                # Rebuild items using current display mode; store
                                # actual column name in userData so we can always
                                # retrieve the real column identifier when filtering.
                                try:
                                    display_mode = getattr(self, "contents_display_mode", None)
                                    mode = display_mode.currentText().lower() if display_mode is not None else "names"
                                except Exception:
                                    mode = "names"

                                col_combo.clear()
                                for c in columns:
                                    try:
                                        if mode.startswith("desc"):
                                            label = c.remarks or c.name
                                        else:
                                            label = c.name
                                        col_combo.addItem(label, c.name)
                                    except Exception:
                                        pass

                                # Update the contents model's header display to match
                                try:
                                    if getattr(self, "contents_model", None):
                                        self.contents_model.set_header_display_mode(
                                            "description" if mode.startswith("desc") else "name", columns
                                        )
                                except Exception:
                                    pass
                        except Exception:
                            pass

                        # Start background fetch (non-blocking when running in Qt)
                        try:
                            self.load_table_contents(
                                table_key,
                                limit=(self.contents_limit.value() if hasattr(self.contents_limit, "value") else 25),
                            )
                        except Exception:
                            # fallback to sync call if asynchronous path fails
                            try:
                                QtDBBrowser.load_table_contents(
                                    self,
                                    table_key,
                                    limit=(
                                        self.contents_limit.value() if hasattr(self.contents_limit, "value") else 25
                                    ),
                                )
                            except Exception:
                                pass
                    except Exception:
                        # Swallow errors to avoid affecting table selection flow
                        pass

                # Execute deferred load immediately for responsive feel
                try:
                    from PySide6.QtCore import QTimer

                    QTimer.singleShot(0, _deferred_contents_load)
                except Exception:
                    # If QTimer not available, fall back to immediate execution
                    _deferred_contents_load()
            except Exception:
                # Swallow errors to avoid affecting table selection flow
                pass
        else:
            self.columns_model.set_columns([])
            self.update_column_details(None, [])

    def update_column_details(self, table_key: Optional[str], columns: List[ColumnInfo]):
        """Update the column details panel with formatted information."""
        if not table_key or not columns:
            self.column_details_text.setPlainText("No table selected")
            return

        # Parse table key
        parts = table_key.split(".")
        schema = parts[0] if len(parts) > 0 else ""
        table = parts[1] if len(parts) > 1 else ""

        # Format column details
        details = []
        details.append(f"Table: {schema}.{table}")
        details.append(f"Columns: {len(columns)}")
        details.append("=" * 60)
        details.append("")

        for i, col in enumerate(columns, 1):
            details.append(f"{i}. {col.name}")
            details.append(f"   Type:     {col.typename}" + (f"({col.length})" if col.length else ""))
            if col.scale:
                details.append(f"   Scale:    {col.scale}")
            details.append(f"   Nullable: {'Yes' if col.nulls == 'Y' else 'No'}")
            if col.remarks:
                # Wrap long remarks
                remarks_lines = col.remarks.split("\n")
                details.append(f"   Remarks:  {remarks_lines[0]}")
                for remark_line in remarks_lines[1:]:
                    details.append(f"             {remark_line}")
            details.append("")

        self.column_details_text.setPlainText("\n".join(details))

    def load_table_contents(
        self,
        table_key: str,
        limit: int = 25,
        start_offset: int = 0,
        column_filter: Optional[str] = None,
        value: Optional[str] = None,
        where_clause: Optional[str] = None,
        async_fetch: bool = True,
    ):
        """Fetch a small preview of rows for `table_key` and populate contents model.

        Uses dbutils.db_browser.query_runner to run a SELECT on the target
        table and updates the TableContentsModel. Errors are handled
        gracefully so the UI remains stable when a database connection is
        not available (e.g., in tests or mock mode).
        """
        try:
            # Find TableInfo object
            parts = table_key.split(".")
            schema = parts[0] if len(parts) > 0 else None
            name = parts[1] if len(parts) > 1 else None

            table_obj = None
            for t in getattr(self, "tables", []):
                if f"{t.schema}.{t.name}" == table_key:
                    table_obj = t
                    break

            if table_obj is None:
                # Nothing to fetch
                if getattr(self, "contents_model", None):
                    self.contents_model.clear()
                return

            # Initialize pagination/accumulation state for new table OR when explicitly requesting a fresh load
            # Reset state if: (1) different table, OR (2) requesting offset 0 explicitly
            should_reset = (
                not hasattr(self, "contents_table_key") or self.contents_table_key != table_key or start_offset == 0
            )

            if should_reset:
                self.contents_table_key = table_key
                self.contents_offset = 0
                self.contents_accumulated_rows = []
                self.contents_has_more = True
                self.contents_loading = False
                # Hide loading indicator when starting fresh
                if hasattr(self, "contents_loading_container"):
                    self.contents_loading_container.setVisible(False)
                # Show loading placeholder in table
                if hasattr(self, "contents_model"):
                    self.contents_model.show_loading(f"Loading contents for {table_key}...")
            else:
                # Pagination request - ensure we're not already loading
                if getattr(self, "contents_loading", False):
                    # Already loading, skip this request
                    return

            # If caller asked for async_fetch and Qt runtime/threading is available
            if async_fetch and QT_AVAILABLE and hasattr(self, "_start_contents_fetch"):
                # Cancel any previous worker
                try:
                    if getattr(self, "contents_worker", None):
                        try:
                            self.contents_worker.cancel()
                        except Exception:
                            pass
                        self.contents_worker = None
                    if getattr(self, "contents_thread", None):
                        try:
                            self.contents_thread.quit()
                            # Don't block UI - quit asynchronously
                            self.contents_thread.requestInterruption()
                        except Exception:
                            pass
                        self.contents_thread = None
                except Exception:
                    pass

                # Start background worker and return immediately (worker will update model)
                self._start_contents_fetch(
                    table_obj.schema,
                    table_obj.name,
                    limit=limit,
                    start_offset=int(start_offset),
                    column_filter=column_filter,
                    value=value,
                    where_clause=where_clause,
                )
                return

            # Import the query runner helper (may be the external wrapper)
            from dbutils.db_browser import query_runner

            # Build SQL for synchronous fetch similar to TableContentsWorker
            tbl = f"{schema}.{name}"

            where = ""
            if where_clause:
                where = f" WHERE {where_clause}"
            elif column_filter and (value is not None):
                # Attempt to inspect catalog metadata to guess type
                try:
                    from dbutils.catalog import get_columns_for_table as _get_cols
                except Exception:
                    _get_cols = None

                # Some catalogs expose a get_columns helper - try that too
                try:
                    from dbutils.catalog import get_columns as _get_cols_alt
                except Exception:
                    _get_cols_alt = None

                is_str = True
                try:
                    cols = None
                    if _get_cols:
                        cols = _get_cols(schema, name)
                    elif _get_cols_alt:
                        cols = _get_cols_alt(schema, name)

                    if cols:
                        # Accept either dict keys or ColumnInfo-like objects
                        found = None
                        for c in cols:
                            if isinstance(c, dict):
                                if c.get("COLNAME") == column_filter or c.get("name") == column_filter:
                                    found = c
                                    break
                            else:
                                # ColumnInfo instance
                                if getattr(c, "name", None) == column_filter:
                                    found = c
                                    break

                        if found:
                            typename = (
                                found.get("TYPENAME") if isinstance(found, dict) else getattr(found, "typename", None)
                            )
                            is_str = TableContentsWorker._is_string_type(typename)
                except Exception:
                    is_str = True

                if is_str:
                    safe_val = str(value).replace("'", "''")
                    where = f" WHERE {column_filter} = '{safe_val}'"
                else:
                    where = f" WHERE {column_filter} = {value}"

            # Add ORDER BY for stable pagination (order by first column)
            order_by = " ORDER BY 1"

            # Include OFFSET for pagination if start_offset > 0
            if int(start_offset) > 0:
                sql = f"SELECT * FROM {tbl}{where}{order_by} OFFSET {int(start_offset)} ROWS FETCH FIRST {int(limit)} ROWS ONLY"
            else:
                sql = f"SELECT * FROM {tbl}{where}{order_by} FETCH FIRST {int(limit)} ROWS ONLY"

            rows = []
            try:
                rows = query_runner(sql)
            except Exception as e:
                # If query_runner fails, check if we're in mock mode and generate mock data
                if getattr(self, "use_mock", False):
                    # Generate mock row data for the selected table
                    try:
                        cols = self.table_columns.get(table_key, [])
                        if cols:
                            # Generate mock rows based on column count and types
                            rows = []
                            for row_id in range(int(start_offset), int(start_offset) + int(limit)):
                                row_data = {}
                                for i, col in enumerate(cols):
                                    col_name = col.name
                                    # Generate mock data based on column type
                                    if "INT" in (col.typename or "").upper():
                                        row_data[col_name] = row_id * 100 + i
                                    elif "DECIMAL" in (col.typename or "").upper() or "FLOAT" in (col.typename or "").upper():
                                        row_data[col_name] = float(row_id) * 10.5 + float(i)
                                    elif "DATE" in (col.typename or "").upper():
                                        # Generate dates
                                        day = (row_id % 28) + 1
                                        month = ((row_id // 28) % 12) + 1
                                        row_data[col_name] = f"2024-{month:02d}-{day:02d}"
                                    else:
                                        # String/default
                                        row_data[col_name] = f"{table}.{col_name}.row{row_id}"
                                rows.append(row_data)
                    except Exception:
                        rows = []
                else:
                    rows = []

            # Fallback synchronous path follows (for tests or when Qt not available)
            # Normalize to list of dicts
            rows = rows or []

            # Derive columns either from rows or from metadata table_columns
            columns = []
            if rows:
                # Use keys from first row (keeping stable ordering)
                first = rows[0]
                if isinstance(first, dict):
                    columns = list(first.keys())
                else:
                    # If query_runner returns tuples, ask columns from metadata
                    columns = [c.name for c in self.table_columns.get(table_key, [])]
            else:
                columns = [c.name for c in self.table_columns.get(table_key, [])]

            # Populate the contents model (append or replace depending on offset)
            if getattr(self, "contents_model", None):
                # Hide loading placeholder
                self.contents_model.hide_loading()

                # Update accumulated rows
                if int(start_offset) > 0:
                    self.contents_accumulated_rows.extend(rows)
                    self.contents_offset = int(start_offset) + len(rows)
                else:
                    self.contents_accumulated_rows = list(rows)
                    self.contents_offset = len(rows)

                # Determine if we probably have more rows to fetch
                self.contents_has_more = len(rows) >= int(limit)

                # Use current columns if the worker didn't provide them
                cols_final = columns if columns else [c.name for c in self.table_columns.get(table_key, [])]
                self.contents_model.set_contents(cols_final, self.contents_accumulated_rows)

        except Exception as e:
            # Log to stderr but don't raise
            try:
                sys.stderr.write(f"[QtDBBrowser] load_table_contents error: {e}\n")
                sys.stderr.flush()
            except Exception:
                pass
            if getattr(self, "contents_model", None):
                self.contents_model.clear()

    def _start_contents_fetch(
        self,
        schema: str,
        table: str,
        limit: int = 25,
        start_offset: int = 0,
        column_filter: Optional[str] = None,
        value: Optional[str] = None,
        where_clause: Optional[str] = None,
    ):
        """Create a TableContentsWorker in a new thread and perform fetch asynchronously."""
        try:
            # Clean up any existing worker/thread without blocking
            if getattr(self, "contents_worker", None):
                try:
                    self.contents_worker.cancel()
                except Exception:
                    pass
                # Don't set to None yet - let finished handler clean it up

            if getattr(self, "contents_thread", None):
                try:
                    # Just request quit - don't wait (non-blocking)
                    self.contents_thread.quit()
                except Exception:
                    pass
                # Don't set to None yet - let finished handler clean it up

            # Create worker and thread
            self.contents_worker = TableContentsWorker()
            self.contents_thread = QThread()
            self.contents_worker.moveToThread(self.contents_thread)

            # Connect signals to update UI
            # Capture start_offset locally so closure knows whether to append
            start = int(start_offset)

            def on_results(cols, rows):
                try:
                    cols_final = cols if cols else [c.name for c in self.table_columns.get(f"{schema}.{table}", [])]
                    if getattr(self, "contents_model", None):
                        # Hide loading placeholder
                        self.contents_model.hide_loading()

                        # If this is a paginated fetch (start > 0), append rows
                        if start > 0:
                            try:
                                if not hasattr(self, "contents_accumulated_rows"):
                                    self.contents_accumulated_rows = []
                                self.contents_accumulated_rows.extend(rows or [])
                                self.contents_offset = start + len(rows or [])
                                self.contents_has_more = len(rows or []) >= int(limit)
                                self.contents_model.set_contents(cols_final, self.contents_accumulated_rows)
                            except Exception:
                                # Fallback to replace if append fails
                                self.contents_model.set_contents(cols_final, rows or [])
                        else:
                            # Fresh fetch - replace
                            self.contents_accumulated_rows = list(rows or [])
                            self.contents_offset = len(rows or [])
                            self.contents_has_more = len(rows or []) >= int(limit)
                            self.contents_model.set_contents(cols_final, self.contents_accumulated_rows)

                    # Mark loading finished and hide loading indicator
                    try:
                        self.contents_loading = False
                        if hasattr(self, "contents_loading_container"):
                            self.contents_loading_container.setVisible(False)
                    except Exception:
                        pass
                except Exception:
                    pass

            def on_error(msg):
                try:
                    self.status_label.setText(f"Contents error: {msg}")
                    # Hide loading indicator on error
                    if hasattr(self, "contents_loading_container"):
                        self.contents_loading_container.setVisible(False)
                    self.contents_loading = False
                except Exception:
                    pass

            self.contents_worker.results_ready.connect(on_results)
            self.contents_worker.error_occurred.connect(on_error)

            # Clean up thread when it finishes
            def cleanup_thread():
                try:
                    if hasattr(self, "contents_thread") and self.contents_thread:
                        self.contents_thread.deleteLater()
                        self.contents_thread = None
                    if hasattr(self, "contents_worker") and self.contents_worker:
                        self.contents_worker.deleteLater()
                        self.contents_worker = None
                except Exception:
                    pass

            self.contents_thread.finished.connect(cleanup_thread)

            # Start thread and invoke
            # Mark that a fetch is in progress
            try:
                self.contents_loading = True
            except Exception:
                pass

            self.contents_thread.started.connect(
                lambda: self.contents_worker.perform_fetch(
                    schema,
                    table,
                    limit=limit,
                    start_offset=int(start_offset),
                    column_filter=column_filter,
                    value=value,
                    where_clause=where_clause,
                    use_mock=self.use_mock,
                    table_columns=self.table_columns.get(f"{schema}.{table}", []),
                    db_file=self.db_file,
                )
            )

            # Quit thread after worker finishes
            def quit_on_complete():
                try:
                    if hasattr(self, "contents_thread") and self.contents_thread:
                        self.contents_thread.quit()
                except Exception:
                    pass

            self.contents_worker.results_ready.connect(quit_on_complete)
            self.contents_worker.error_occurred.connect(quit_on_complete)

            self.contents_thread.start()
        except Exception as e:
            try:
                sys.stderr.write(f"[QtDBBrowser] _start_contents_fetch error: {e}\n")
                sys.stderr.flush()
            except Exception:
                pass

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

    def toggle_column_details(self):
        """Toggle the column details dock widget visibility."""
        if self.column_details_dock.isVisible():
            self.column_details_dock.hide()
            self.toggle_details_action.setChecked(False)
            self.toggle_details_action.setText("Show Column Details")
        else:
            self.column_details_dock.show()
            self.toggle_details_action.setChecked(True)
            self.toggle_details_action.setText("Hide Column Details")

    def toggle_contents_dock(self):
        """Toggle the table contents dock visibility."""
        if getattr(self, "contents_dock", None) and self.contents_dock.isVisible():
            self.contents_dock.hide()
            if getattr(self, "toggle_contents_action", None):
                self.toggle_contents_action.setChecked(False)
                self.toggle_contents_action.setText("Show Table Contents")
        else:
            if getattr(self, "contents_dock", None):
                self.contents_dock.show()
            if getattr(self, "toggle_contents_action", None):
                self.toggle_contents_action.setChecked(True)
                self.toggle_contents_action.setText("Hide Table Contents")

    def _apply_contents_filter(self):
        """Read controls and trigger a contents fetch using the selected filter and limit."""
        try:
            # Find current table key from selection (best-effort)
            table_key = None
            try:
                sel = self.tables_table.selectionModel().selectedIndexes()
                if sel:
                    source_index = self.tables_proxy.mapToSource(sel[0])
                    row = source_index.row()
                    if self.tables_model._search_results:
                        if row < len(self.tables_model._search_results):
                            table_key = self.tables_model._search_results[row].table_key
                    else:
                        if row < len(self.tables_model._tables):
                            t = self.tables_model._tables[row]
                            table_key = f"{t.schema}.{t.name}"
            except Exception:
                table_key = None

            if not table_key:
                return

            # derive filter values
            limit = self.contents_limit.value() if hasattr(self.contents_limit, "value") else 25
            col = None
            try:
                if getattr(self, "contents_column_combo", None):
                    # Prefer userData (actual column name) if present, otherwise use visible text
                    try:
                        col = self.contents_column_combo.currentData()
                    except Exception:
                        col = self.contents_column_combo.currentText()
                else:
                    col = None
            except Exception:
                col = None
            val = self.contents_filter_input.text() if getattr(self, "contents_filter_input", None) else None

            # Reset pagination for a new filter and start async fetch
            try:
                self.contents_offset = 0
                self.contents_accumulated_rows = []
                self.contents_has_more = True
                self.contents_loading = False
            except Exception:
                pass

            # Start async fetch
            self.load_table_contents(
                table_key, limit=limit, start_offset=0, column_filter=col or None, value=val or None, async_fetch=True
            )
        except Exception:
            pass

    def _on_contents_display_mode_changed(self):
        """Handle user toggling the contents header/selector display mode.

        Rebuilds the contents_column_combo display labels based on current
        table selection and updates the TableContentsModel header labels.
        """
        try:
            # Determine currently selected table
            table_key = None
            sel = None
            try:
                sel = self.tables_table.selectionModel().selectedIndexes()
            except Exception:
                sel = None

            if sel:
                try:
                    source_index = self.tables_proxy.mapToSource(sel[0])
                    row = source_index.row()
                    if self.tables_model._search_results:
                        if row < len(self.tables_model._search_results):
                            table_key = self.tables_model._search_results[row].table_key
                    else:
                        if row < len(self.tables_model._tables):
                            t = self.tables_model._tables[row]
                            table_key = f"{t.schema}.{t.name}"
                except Exception:
                    table_key = None

            if not table_key:
                return

            columns = self.table_columns.get(table_key, [])

            # Rebuild column selector display
            try:
                col_combo = getattr(self, "contents_column_combo", None)
                if col_combo is not None:
                    try:
                        display_mode = getattr(self, "contents_display_mode", None)
                        mode = display_mode.currentText().lower() if display_mode is not None else "names"
                    except Exception:
                        mode = "names"

                    col_combo.clear()
                    for c in columns:
                        try:
                            label = c.remarks or c.name if mode.startswith("desc") else c.name
                            col_combo.addItem(label, c.name)
                        except Exception:
                            pass
            except Exception:
                pass

            # Update header display labels
            try:
                if getattr(self, "contents_model", None):
                    self.contents_model.set_header_display_mode(
                        "description" if mode.startswith("desc") else "name", columns
                    )
            except Exception:
                pass
        except Exception:
            pass

    def _on_contents_scrolled(self, value: int):
        """Triggered when contents table scrollbar changes; fetch more when near bottom.

        Uses self.contents_has_more and self.contents_loading to avoid concurrent loads.
        Shows a loading indicator when fetching more data.
        """
        try:
            if not getattr(self, "contents_has_more", False):
                return
            if getattr(self, "contents_loading", False):
                return

            sb = self.contents_table.verticalScrollBar()
            if not sb:
                return

            maximum = sb.maximum()
            if maximum <= 0:
                return

            # Trigger pagination when within 100px of bottom (allows for overscroll effect)
            if value >= max(0, maximum - 100):
                try:
                    # Show loading indicator
                    if hasattr(self, "contents_loading_container"):
                        self.contents_loading_container.setVisible(True)

                    current_offset = getattr(self, "contents_offset", 0) or 0
                    limit = self.contents_limit.value() if hasattr(self.contents_limit, "value") else 25
                    # Next page starts at current_offset (which tracks total rows loaded)
                    next_offset = current_offset
                    if next_offset is None:
                        next_offset = 0
                    self.load_table_contents(
                        getattr(self, "contents_table_key", ""), limit=limit, start_offset=next_offset, async_fetch=True
                    )
                except Exception:
                    pass
        except Exception:
            pass

    def toggle_search_dock(self):
        """Toggle the search dock widget visibility."""
        if self.search_dock.isVisible():
            self.search_dock.hide()
            self.toggle_search_action.setChecked(False)
            self.toggle_search_action.setText("Show Search Panel")
        else:
            self.search_dock.show()
            self.toggle_search_action.setChecked(True)
            self.toggle_search_action.setText("Hide Search Panel")

    def toggle_tables_dock(self):
        """Toggle the tables dock widget visibility."""
        if self.tables_dock.isVisible():
            self.tables_dock.hide()
            self.toggle_tables_action.setChecked(False)
            self.toggle_tables_action.setText("Show Tables Panel")
        else:
            self.tables_dock.show()
            self.toggle_tables_action.setChecked(True)
            self.toggle_tables_action.setText("Hide Tables Panel")

    def toggle_columns_dock(self):
        """Toggle the columns dock widget visibility."""
        if self.columns_dock.isVisible():
            self.columns_dock.hide()
            self.toggle_columns_action.setChecked(False)
            self.toggle_columns_action.setText("Show Columns Panel")
        else:
            self.columns_dock.show()
            self.toggle_columns_action.setChecked(True)
            self.toggle_columns_action.setText("Hide Columns Panel")

    def toggle_streaming(self):
        """Toggle streaming search - now always enabled."""
        self.streaming_enabled = True  # Always enabled
        # self.streaming_check.setChecked(self.streaming_enabled)

        self.status_label.setText("Streaming search always enabled")

    def toggle_show_non_matching(self):
        """Toggle show/hide non-matching tables."""
        self.show_non_matching = not self.show_non_matching
        self.show_non_matching_check.setChecked(self.show_non_matching)

        status = "shown" if self.show_non_matching else "hidden"
        self.status_label.setText(f"Non-matching tables {status}")

    def show_export_dialog(self):
        """Show export dialog to choose format and file."""
        # Get current filtered data
        if hasattr(self, "tables_proxy") and self.tables_proxy:
            row_count = self.tables_proxy.rowCount()
        else:
            row_count = 0

        if row_count == 0:
            QMessageBox.warning(self, "No Data", "No tables to export. Please load data first.")
            return

        # Ask user for export format
        format_dialog = QMessageBox(self)
        format_dialog.setWindowTitle("Export Format")
        format_dialog.setText("Choose export format:")
        csv_btn = format_dialog.addButton("CSV (Table List)", QMessageBox.ButtonRole.ActionRole)
        json_btn = format_dialog.addButton("JSON (Full Schema)", QMessageBox.ButtonRole.ActionRole)
        sql_btn = format_dialog.addButton("SQL DDL", QMessageBox.ButtonRole.ActionRole)
        format_dialog.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        format_dialog.exec()

        clicked = format_dialog.clickedButton()
        if clicked == csv_btn:
            self.export_csv()
        elif clicked == json_btn:
            self.export_json()
        elif clicked == sql_btn:
            self.export_sql()

    def export_csv(self):
        """Export filtered tables to CSV format."""
        filename, _ = QFileDialog.getSaveFileName(self, "Export to CSV", "", "CSV Files (*.csv);;All Files (*)")
        if not filename:
            return

        try:
            progress = QProgressDialog("Exporting to CSV...", "Cancel", 0, 100, self)
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.show()

            with open(filename, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Schema", "Table", "Column Count", "Description"])

                # Export visible/filtered tables
                proxy = self.tables_proxy
                total = proxy.rowCount()

                for row in range(total):
                    if progress.wasCanceled():
                        break

                    schema_idx = proxy.index(row, 0)
                    table_idx = proxy.index(row, 1)
                    count_idx = proxy.index(row, 2)
                    desc_idx = proxy.index(row, 3)

                    schema = proxy.data(schema_idx)
                    table = proxy.data(table_idx)
                    count = proxy.data(count_idx)
                    desc = proxy.data(desc_idx) or ""

                    writer.writerow([schema, table, count, desc])

                    if row % 10 == 0:
                        progress.setValue(int(row * 100 / total))
                        QApplication.processEvents()

            progress.setValue(100)
            QMessageBox.information(self, "Export Complete", f"Exported {total} tables to {filename}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export: {e}")

    def export_json(self):
        """Export full schema structure to JSON format."""
        filename, _ = QFileDialog.getSaveFileName(self, "Export to JSON", "", "JSON Files (*.json);;All Files (*)")
        if not filename:
            return

        try:
            progress = QProgressDialog("Exporting to JSON...", "Cancel", 0, 100, self)
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.show()

            # Build complete schema structure
            schema_data = {}
            proxy = self.tables_proxy
            total = proxy.rowCount()

            for row in range(total):
                if progress.wasCanceled():
                    break

                schema_idx = proxy.index(row, 0)
                table_idx = proxy.index(row, 1)
                desc_idx = proxy.index(row, 3)

                schema = proxy.data(schema_idx)
                table = proxy.data(table_idx)
                desc = proxy.data(desc_idx) or ""

                if schema not in schema_data:
                    schema_data[schema] = {}

                # Get columns for this table
                columns = []
                for col in self.all_columns:
                    if col.table_schema == schema and col.table_name == table:
                        columns.append(
                            {
                                "name": col.column_name,
                                "type": col.data_type,
                                "length": col.length,
                                "scale": col.scale,
                                "nullable": col.nullable,
                                "remarks": col.remarks or "",
                            }
                        )

                schema_data[schema][table] = {"description": desc, "columns": columns}

                if row % 10 == 0:
                    progress.setValue(int(row * 100 / total))
                    QApplication.processEvents()

            # Write JSON file
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(schema_data, f, indent=2, ensure_ascii=False)

            progress.setValue(100)
            QMessageBox.information(self, "Export Complete", f"Exported schema to {filename}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export: {e}")

    def export_sql(self):
        """Export CREATE TABLE DDL statements."""
        filename, _ = QFileDialog.getSaveFileName(self, "Export to SQL", "", "SQL Files (*.sql);;All Files (*)")
        if not filename:
            return

        try:
            progress = QProgressDialog("Generating SQL DDL...", "Cancel", 0, 100, self)
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.show()

            with open(filename, "w", encoding="utf-8") as f:
                proxy = self.tables_proxy
                total = proxy.rowCount()

                for row in range(total):
                    if progress.wasCanceled():
                        break

                    schema_idx = proxy.index(row, 0)
                    table_idx = proxy.index(row, 1)
                    desc_idx = proxy.index(row, 3)

                    schema = proxy.data(schema_idx)
                    table = proxy.data(table_idx)
                    desc = proxy.data(desc_idx)

                    # Write table comment if available
                    if desc:
                        f.write(f"-- {desc}\\n")

                    f.write(f"CREATE TABLE {schema}.{table} (\\n")

                    # Get columns for this table
                    columns = []
                    for col in self.all_columns:
                        if col.table_schema == schema and col.table_name == table:
                            columns.append(col)

                    # Write column definitions
                    col_lines = []
                    for col in columns:
                        col_def = f"    {col.column_name} {col.data_type}"
                        if col.length:
                            if col.scale:
                                col_def += f"({col.length},{col.scale})"
                            else:
                                col_def += f"({col.length})"
                        if not col.nullable:
                            col_def += " NOT NULL"
                        col_lines.append(col_def)

                    f.write(",\\n".join(col_lines))
                    f.write("\\n);\\n\\n")

                    # Add column comments if available
                    for col in columns:
                        if col.remarks:
                            f.write(f"COMMENT ON COLUMN {schema}.{table}.{col.column_name} IS '{col.remarks}';\\n")

                    if any(col.remarks for col in columns):
                        f.write("\\n")

                    if row % 10 == 0:
                        progress.setValue(int(row * 100 / total))
                        QApplication.processEvents()

            progress.setValue(100)
            QMessageBox.information(self, "Export Complete", f"Generated DDL for {total} tables")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export: {e}")

    def on_schema_changed(self, schema: str):
        """Handle schema filter change.

        The QComboBox stores human-friendly labels but the real schema name
        is stored as the item's userData so we should prefer that when
        updating the active filter.
        """
        try:
            idx = self.schema_combo.currentIndex()
            # itemData will be the real schema name (or None for All Schemas)
            selected = self.schema_combo.itemData(idx)
        except Exception:
            # Fall back to the supplied text for environments without Qt
            selected = None if schema == "All Schemas" else schema

        if selected is None:
            self.schema_filter = None
        else:
            # Ensure string type
            self.schema_filter = str(selected)

        self.load_data()

    def on_show_non_matching_changed(self, checked: bool):
        """Handle show non-matching checkbox change."""
        self.show_non_matching = checked
        # Restart search if active
        if self.search_query.strip():
            self.start_streaming_search()

    def on_highlight_toggled(self, checked: bool):
        """Enable or disable inline highlighting delegate on views."""
        # Update state
        self.inline_highlight_enabled = bool(checked)

        try:
            if self.inline_highlight_enabled:
                # install delegates
                try:
                    self.tables_delegate = HighlightDelegate(self.tables_table, lambda: self.search_query)
                    self.tables_table.setItemDelegate(self.tables_delegate)
                except Exception:
                    self.tables_delegate = None

                try:
                    self.columns_delegate = HighlightDelegate(self.columns_table, lambda: self.search_query)
                    self.columns_table.setItemDelegate(self.columns_delegate)
                except Exception:
                    self.columns_delegate = None
            else:
                # remove delegates to use default rendering
                try:
                    self.tables_table.setItemDelegate(None)
                    self.tables_delegate = None
                except Exception:
                    pass

                # contents scroll handler moved to class scope so it can be connected safely

                try:
                    self.columns_table.setItemDelegate(None)
                    self.columns_delegate = None
                except Exception:
                    pass

            # Force view refresh
            try:
                if getattr(self, "tables_proxy", None):
                    self.tables_proxy.invalidate()
                if getattr(self, "tables_table", None):
                    self.tables_table.viewport().update()
                if getattr(self, "columns_table", None):
                    self.columns_table.viewport().update()
            except Exception:
                pass
        except Exception:
            # Be resilient; don't crash the whole UI
            pass

    def on_streaming_toggled(self, checked: bool):
        """Handle streaming checkbox change - now always enabled."""
        self.streaming_enabled = True  # Always enabled regardless of checkbox that's now removed
        # Restart search if active
        if self.search_query.strip():
            self.start_streaming_search()

    def rebuild_schema_cache(self):
        """Rebuild the schema cache from loaded tables."""
        from pathlib import Path
        import json

        try:
            # Build schema list from current loaded tables
            if not self.tables:
                QMessageBox.warning(self, "No Data Loaded", "Please load data first before rebuilding the schema list.")
                return

            schemas = sorted({t.schema for t in self.tables})

            # Save to cache
            cache_dir = Path.home() / ".cache" / "dbutils"
            cache_dir.mkdir(parents=True, exist_ok=True)
            cache_path = cache_dir / "schemas.json"

            with open(cache_path, "w") as f:
                json.dump({"schemas": schemas}, f)

            self.status_label.setText(f"Rebuilt schema cache with {len(schemas)} schemas")

            # Update the combo box with new schemas
            self.all_schemas = schemas
            self.update_schema_combo()

            QMessageBox.information(
                self,
                "Schema Cache Rebuilt",
                f"Successfully rebuilt schema cache with {len(schemas)} schemas.\n\n"
                "The schema list will now be loaded from cache on future startups.",
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to rebuild schema cache: {e}")

    def clear_all_caches(self):
        """Clear all cached data (schemas and table/column data)."""
        from pathlib import Path
        import glob

        try:
            cache_dir = Path.home() / ".cache" / "dbutils"

            if not cache_dir.exists():
                QMessageBox.information(self, "Cache Empty", "No cache files found.")
                return

            # Count and delete cache files (both .json and .json.gz)
            json_files = list(cache_dir.glob("*.json"))
            gz_files = list(cache_dir.glob("*.json.gz"))
            cache_files = json_files + gz_files
            count = len(cache_files)

            if count == 0:
                QMessageBox.information(self, "Cache Empty", "No cache files found.")
                return

            # Confirm deletion
            reply = QMessageBox.question(
                self,
                "Clear Caches",
                f"This will delete {count} cache file(s):\n\n"
                "• Schema list cache\n"
                "• Table/column data caches\n\n"
                "Data will be reloaded from the database on next refresh.\n\n"
                "Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.Yes:
                for cache_file in cache_files:
                    cache_file.unlink()

                self.status_label.setText(f"Cleared {count} cache files")

                QMessageBox.information(
                    self,
                    "Caches Cleared",
                    f"Successfully deleted {count} cache file(s).\n\nPress F5 to reload data from the database.",
                )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to clear caches: {e}")

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

        if self.search_thread:
            try:
                # Check if thread is still valid and running
                if hasattr(self.search_thread, 'isRunning') and self.search_thread.isRunning():
                    self.search_thread.quit()
                    self.search_thread.wait(3000)  # Wait up to 3 seconds
                # Clean up the thread reference
                self.search_thread.deleteLater()
            except Exception:
                # Thread may already be deleted or invalid, ignore gracefully
                pass

        # Cancel table contents worker if running
        if hasattr(self, "contents_worker") and self.contents_worker:
            if hasattr(self.contents_worker, "cancel"):
                self.contents_worker.cancel()

        if hasattr(self, "contents_thread") and self.contents_thread and self.contents_thread.isRunning():
            self.contents_thread.quit()
            self.contents_thread.wait(3000)

        # Cancel data loading if in progress
        if self.data_loader_thread and self.data_loader_thread.isRunning():
            self.data_loader_thread.quit()
            self.data_loader_thread.wait(3000)  # Wait up to 3 seconds

        # Terminate subprocess if used
        if self.data_loader_proc and QT_AVAILABLE:
            try:
                if hasattr(self.data_loader_proc, "_proc") and self.data_loader_proc._proc:
                    self.data_loader_proc._proc.terminate()
                    self.data_loader_proc._proc.waitForFinished(2000)
            except Exception:
                pass
            self.data_loader_proc = None

        event.accept()


def main(args=None):
    """Main entry point for Qt application."""
    import argparse

    if args is None:
        # Parse arguments from command line if not provided
        parser = argparse.ArgumentParser(description="Experimental Qt Database Browser")
        parser.add_argument("--schema", help="Filter by specific schema")
        parser.add_argument("--mock", action="store_true", help="Use mock data for testing")
        parser.add_argument("--heavy-mock", action="store_true", 
                           help="Use heavy mock data for stress testing (5 schemas, 50 tables each, 20 columns each)")
        parser.add_argument("--no-streaming", action="store_true", help="Disable streaming search")
        parser.add_argument("--db-file", help="SQLite database file to open")

        args = parser.parse_args()
    else:
        # Args passed from caller, ensure they have required attributes
        if not hasattr(args, 'schema'):
            args.schema = None
        if not hasattr(args, 'mock'):
            args.mock = False
        if not hasattr(args, 'heavy_mock'):
            args.heavy_mock = False
        if not hasattr(args, 'no_streaming'):
            args.no_streaming = False
        if not hasattr(args, 'db_file'):
            args.db_file = None

    # Check if QApplication instance already exists
    try:
        from PySide6.QtCore import QCoreApplication
    except ImportError:
        try:
            from PyQt6.QtCore import QCoreApplication
        except ImportError:
            QCoreApplication = None

    app = QCoreApplication.instance() if QCoreApplication else None
    if app is None:
        # Create new Qt application
        app = QApplication(sys.argv)
        app.setApplicationName("DB Browser")
        app.setOrganizationName("DBUtils")
    else:
        # Use existing application instance
        print("Using existing QApplication instance")

    # Create main window
    # Use heavy mock if requested, otherwise use regular mock if requested
    use_mock = args.heavy_mock or args.mock
    browser = QtDBBrowser(schema_filter=args.schema, use_mock=use_mock, use_heavy_mock=args.heavy_mock, db_file=args.db_file)
    if args.no_streaming:
        browser.streaming_enabled = False
        if hasattr(browser, 'streaming_check'):
            browser.streaming_check.setChecked(False)

    browser.show()

    # Run event loop only if we created the app
    if QApplication.instance() is not None:
        sys.exit(app.exec())
    else:
        print("QApplication instance not available, cannot start event loop")
        sys.exit(1)


if __name__ == "__main__":
    main()
