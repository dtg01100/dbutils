"""
Qt-based Database Browser - Experimental GUI Version

A modern Qt interface for database schema browsing with advanced features
including streaming search, visualizations, and enhanced user experience.
"""

from __future__ import annotations

import os
import sys
import asyncio
import json
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
        QDockWidget,
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
        QProcess,
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
            QDockWidget,
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
            QProcess,
        )
        from PyQt6.QtGui import QIcon, QFont, QPixmap, QAction

        QT_AVAILABLE = True
    except ImportError:
        QT_AVAILABLE = False

from ..catalog import get_all_tables_and_columns
from ..db_browser import TableInfo, ColumnInfo
from .widgets.enhanced_widgets import BusyOverlay

# Try to import accelerated C extensions for performance
try:
    from ..accelerated import fast_search_tables, fast_search_columns
    USE_FAST_OPS = True
except ImportError:
    USE_FAST_OPS = False

# Provide minimal stubs so this module can be imported in environments without Qt
if not QT_AVAILABLE:
    class QObject:  # type: ignore
        pass

    class Signal:  # type: ignore
        def __init__(self, *args, **kwargs):
            pass
        def connect(self, *args, **kwargs):
            pass
        def emit(self, *args, **kwargs):
            pass

    class QAbstractTableModel:  # type: ignore
        pass

    class QMainWindow:  # type: ignore
        pass

    class QModelIndex:  # type: ignore
        def __init__(self, *args, **kwargs):
            pass

    class QSize:  # type: ignore
        def __init__(self, *args, **kwargs):
            pass

    class QProcess:  # type: ignore
        def __init__(self, *args, **kwargs):
            pass
        def start(self, *args, **kwargs):
            pass
        def write(self, *args, **kwargs):
            pass
        def waitForStarted(self, *args, **kwargs):
            return False
        def terminate(self):
            pass
        def kill(self):
            pass
        def state(self):
            return 0


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
                    return table.remarks or ""
        elif QT_AVAILABLE and role == Qt.ToolTipRole:
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
        elif QT_AVAILABLE and role == Qt.DecorationRole and col == 0:
            # Add an icon for tables - would require actual icon resources
            # For now, return None
            return None
        elif QT_AVAILABLE and role == Qt.SizeHintRole:
            # Return size hint for better padding
            return QSize(0, 28)  # Match the row height we set

        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role=None):
        """Return header data."""
        if QT_AVAILABLE and orientation == Qt.Horizontal:
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

            return (f"Column: {column.name}\n"
                    f"Type: {type_str}\n"
                    f"Schema: {column.schema}\n"
                    f"Table: {column.table}\n"
                    f"Length: {column.length or 'N/A'}\n"
                    f"Scale: {column.scale or 'N/A'}\n"
                    f"Nullable: {column.nulls}\n"
                    f"Description: {column.remarks or 'No description'}")
        elif QT_AVAILABLE and role == Qt.TextAlignmentRole:
            # No special alignment needed since we're only showing text columns now
            return Qt.AlignLeft | Qt.AlignVCenter
        elif QT_AVAILABLE and role == Qt.SizeHintRole:
            # Return size hint for better padding
            return QSize(0, 28)  # Match the row height we set

        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role=None):
        """Return header data."""
        if QT_AVAILABLE and orientation == Qt.Horizontal:
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
                            QApplication.processEvents()
                
                elif search_mode == "columns":
                    scored_results = fast_search_columns(columns, query)
                    table_matches = {}
                    
                    for col, score in scored_results:
                        if self._search_cancelled:
                            return
                        table_key = f"{col.schema}.{col.table}"
                        if table_key not in table_matches:
                            table_matches[table_key] = []
                        table_matches[table_key].append(col)
                        
                        if len(table_matches[table_key]) == 1:
                            result = SearchResult(
                                item=col,
                                match_type="exact" if score >= 1.0 else "fuzzy",
                                relevance_score=score,
                                table_key=table_key,
                            )
                            results.append(result)
                        
                        # Emit results in batches
                        if len(results) % 15 == 0:
                            self.results_ready.emit(results.copy())
                            QApplication.processEvents()
                
                # Emit final results
                self.results_ready.emit(results)
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
    chunk_loaded = Signal(object, object, int, int)  # (tables_chunk, columns_chunk, loaded, total_est)
    error_occurred = Signal(str)
    progress_updated = Signal(str)
    progress_value = Signal(int, int)  # (current, total)

    def __init__(self):
        super().__init__()

    def load_data(self, schema_filter: Optional[str], use_mock: bool):
        """Load database data in background thread with granular progress updates and chunked streaming."""
        try:
            # Prefer async loader with pagination to avoid huge initial transfer
            self.progress_updated.emit("Connecting to database…")
            QApplication.processEvents()

            # Use async-aware functions from db_browser for better performance and caching
            from ..db_browser import (
                get_all_tables_and_columns,
                get_all_tables_and_columns_async,
                load_from_cache,
                save_to_cache,
            )
            from ..catalog import get_tables  # For schema list

            initial_limit = 200
            batch_size = 500
            loaded_total = 0
            estimated_total = 0  # Unknown until we probe

            # Try cache first for the initial chunk
            cached = load_from_cache(schema_filter, limit=initial_limit, offset=0)
            if cached:
                tables, columns = cached
            else:
                tables, columns = get_all_tables_and_columns(schema_filter, use_mock, use_cache=True, limit=initial_limit, offset=0)

            loaded_total += len(tables)
            # Emit first chunk immediately so UI becomes usable
            self.progress_updated.emit(f"Loaded {len(tables)} tables (initial chunk)…")
            self.progress_value.emit(1, 3)
            self.chunk_loaded.emit(tables, columns, loaded_total, estimated_total)
            QApplication.processEvents()

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
            offset = initial_limit
            more = True
            while more:
                # Check cache for this page
                cached = load_from_cache(schema_filter, limit=batch_size, offset=offset)
                if cached:
                    t_chunk, c_chunk = cached
                else:
                    t_chunk, c_chunk = get_all_tables_and_columns(
                        schema_filter, use_mock, use_cache=True, limit=batch_size, offset=offset
                    )

                if not t_chunk:
                    more = False
                    break

                loaded_total += len(t_chunk)
                self.progress_updated.emit(f"Loaded {loaded_total} tables…")
                # Emit chunk to UI
                self.chunk_loaded.emit(t_chunk, c_chunk, loaded_total, estimated_total)
                QApplication.processEvents()

                # Advance
                offset += len(t_chunk)
                # If this was a short page, we might be done
                if len(t_chunk) < batch_size:
                    more = False

            # After streaming chunks, fetch schemas list (one light query)
            self.progress_updated.emit("Loading available schemas…")
            QApplication.processEvents()
            all_tables = get_tables(mock=use_mock)
            all_schemas = sorted(set(table['TABSCHEMA'] for table in all_tables))

            # Final completion signal (aggregate not required, UI already holds accumulated state)
            self.progress_value.emit(3, 3)
            QApplication.processEvents()
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

    def start(self, schema_filter: Optional[str], use_mock: bool, initial_limit: int = 200, batch_size: int = 500):
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
            args = [python_exe, "-m", "dbutils.gui.data_loader_process"]
            self._proc.start(args[0], args[1:])
        
        if hasattr(self._proc, "waitForStarted") and not self._proc.waitForStarted(5000):
            self.error_occurred.emit("Failed to start data loader process")
            return

        # Send the start command as JSON line
        payload = {
            "cmd": "start",
            "schema_filter": schema_filter,
            "use_mock": bool(use_mock),
            "initial_limit": int(initial_limit),
            "batch_size": int(batch_size),
        }
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
                    if "ERROR" in part.upper() or "Traceback" in part or "File \"" in part:
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
            if hasattr(self, '_proc') and self._proc:
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
            t_list = [TableInfo(schema=t.get("schema"), name=t.get("name"), remarks=t.get("remarks", "")) for t in msg.get("tables", [])]
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

        # Worker threads / subprocess
        self.search_worker = None
        self.search_thread = None
        self.data_loader_worker = None
        self.data_loader_thread = None
        self.data_loader_proc = None
        self.use_subprocess_loader = True

        self.setup_ui()
        self.setup_menu()
        self.setup_status_bar()

        # Show window immediately, then load data in background
        self.show()
        # Use a slight delay to ensure the UI is fully rendered before starting data loading
        QTimer.singleShot(50, self.load_data)  # Load data after window is shown with a small delay

    def setup_ui(self):
        """Setup the main user interface."""
        self.setWindowTitle("DB Browser - Qt (Experimental)")
        self.setGeometry(100, 100, 1200, 800)

        # Set central widget to empty - we'll use all docks
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        central_widget.hide()  # Hide central widget, using only docks

        # Create all dock widgets
        self.setup_search_dock()
        self.setup_tables_dock()
        self.setup_columns_dock()
        self.setup_column_details_dock()

        # Busy overlays for panels
        try:
            self.tables_overlay = BusyOverlay(self.tables_table)
            self.columns_overlay = BusyOverlay(self.columns_table)
        except Exception:
            # If overlays cannot be created (e.g., tests without Qt), ignore gracefully
            self.tables_overlay = None
            self.columns_overlay = None

        # Create column details as dockable widget
        self.setup_column_details_dock()

    def setup_search_dock(self):
        """Create search panel as a dockable widget."""
        self.search_dock = QDockWidget("Search", self)
        self.search_dock.setAllowedAreas(
            Qt.DockWidgetArea.TopDockWidgetArea | 
            Qt.DockWidgetArea.BottomDockWidgetArea
        )
        
        # Create search panel content
        search_widget = self.create_search_panel()
        self.search_dock.setWidget(search_widget)
        
        # Add to main window at top
        self.addDockWidget(Qt.DockWidgetArea.TopDockWidgetArea, self.search_dock)

    def setup_tables_dock(self):
        """Create tables panel as a dockable widget."""
        self.tables_dock = QDockWidget("Tables", self)
        self.tables_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | 
            Qt.DockWidgetArea.RightDockWidgetArea
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
            Qt.DockWidgetArea.LeftDockWidgetArea | 
            Qt.DockWidgetArea.RightDockWidgetArea
        )
        
        # Create columns panel content
        columns_widget = self.create_columns_panel()
        self.columns_dock.setWidget(columns_widget)
        
        # Add to main window on right
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.columns_dock)

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
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

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

    def setup_column_details_dock(self):
        """Create column details as a dockable widget."""
        # Create dock widget
        self.column_details_dock = QDockWidget("Column Details", self)
        self.column_details_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | 
            Qt.DockWidgetArea.RightDockWidgetArea | 
            Qt.DockWidgetArea.BottomDockWidgetArea
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

        view_menu.addSeparator()

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
        """Load database data using a separate process (preferred) or thread fallback."""
        self.status_label.setText("Loading data...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 100)  # Determinate progress
        self.progress_bar.setValue(0)

        # Show overlays and disable inputs to indicate background work
        try:
            if getattr(self, 'tables_overlay', None):
                self.tables_overlay.show_with_message("Loading tables…")
            if getattr(self, 'columns_overlay', None):
                self.columns_overlay.show_with_message("Preparing view…")
            # Disable primary inputs during load
            self.search_input.setEnabled(False)
            self.schema_combo.setEnabled(False)
        except Exception:
            pass

        # Cancel any existing data loader thread/process
        if self.data_loader_worker:
            self.data_loader_worker = None

        if self.data_loader_thread:
            self.data_loader_thread.quit()
            self.data_loader_thread.wait()
            self.data_loader_thread = None

        if self.data_loader_proc and QT_AVAILABLE:
            try:
                # Only terminate if actually running
                if hasattr(self.data_loader_proc._proc, 'state') and self.data_loader_proc._proc.state() != 0:
                    self.data_loader_proc._proc.terminate()
                    self.data_loader_proc._proc.waitForFinished(1000)
            except Exception:
                pass
            self.data_loader_proc = None

        # Prefer subprocess to avoid GIL/UI contention
        if self.use_subprocess_loader and QT_AVAILABLE:
            self.data_loader_proc = DataLoaderProcess()
            self.data_loader_proc.data_loaded.connect(self.on_data_loaded)
            self.data_loader_proc.chunk_loaded.connect(self.on_data_chunk)
            self.data_loader_proc.error_occurred.connect(self.on_data_load_error)
            self.data_loader_proc.progress_updated.connect(self.status_label.setText)
            self.data_loader_proc.progress_value.connect(self.on_data_progress)
            self.data_loader_proc.start(self.schema_filter, self.use_mock, initial_limit=200, batch_size=500)
        else:
            # Fallback to thread-based worker
            self.data_loader_worker = DataLoaderWorker()
            self.data_loader_thread = QThread()
            self.data_loader_worker.moveToThread(self.data_loader_thread)
            self.data_loader_worker.data_loaded.connect(self.on_data_loaded)
            self.data_loader_worker.chunk_loaded.connect(self.on_data_chunk)
            self.data_loader_worker.error_occurred.connect(self.on_data_load_error)
            self.data_loader_worker.progress_updated.connect(self.status_label.setText)
            self.data_loader_worker.progress_value.connect(self.on_data_progress)
            self.data_loader_thread.started.connect(
                lambda: self.data_loader_worker.load_data(self.schema_filter, self.use_mock)
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
            if not hasattr(self, 'table_columns') or self.table_columns is None:
                self.table_columns = {}
            
            # Ensure tables and columns lists exist
            if not hasattr(self, 'tables') or self.tables is None:
                self.tables = []
            if not hasattr(self, 'columns') or self.columns is None:
                self.columns = []

            # Update UI
            # Update UI if we received data (e.g., non-streaming path)
            if self.tables or self.columns:
                self.tables_model.set_data(self.tables, self.table_columns)
            if hasattr(self, 'all_schemas') and self.all_schemas:
                self.update_schema_combo()

            self.status_label.setText(f"Loaded {len(self.tables)} tables, {len(self.columns)} columns")
            self.progress_bar.setValue(100)  # Set to 100% before hiding
            # Keep progress bar visible briefly to show completion
            QTimer.singleShot(500, lambda: self.progress_bar.setVisible(False))

            # Hide overlays and re-enable inputs
            try:
                if getattr(self, 'tables_overlay', None):
                    self.tables_overlay.hide()
                if getattr(self, 'columns_overlay', None):
                    self.columns_overlay.hide()
                self.search_input.setEnabled(True)
                self.schema_combo.setEnabled(True)
            except Exception:
                pass

            # Clean up thread
            if self.data_loader_thread:
                self.data_loader_thread.quit()
                self.data_loader_thread.wait()
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
            self.status_label.setText(f"Error processing data: {e}")
            self.progress_bar.setVisible(False)

            # Hide overlays and re-enable inputs on error
            try:
                if getattr(self, 'tables_overlay', None):
                    self.tables_overlay.hide()
                if getattr(self, 'columns_overlay', None):
                    self.columns_overlay.hide()
                self.search_input.setEnabled(True)
                self.schema_combo.setEnabled(True)
            except Exception:
                pass

            # Clean up thread
            if self.data_loader_thread:
                self.data_loader_thread.quit()
                self.data_loader_thread.wait()
                self.data_loader_thread = None
                self.data_loader_worker = None
            
            # Clean up subprocess
            if self.data_loader_proc and QT_AVAILABLE:
                try:
                    # Only terminate if actually running
                    if hasattr(self.data_loader_proc._proc, 'state') and self.data_loader_proc._proc.state() != 0:
                        self.data_loader_proc._proc.terminate()
                        self.data_loader_proc._proc.waitForFinished(1000)
                except Exception:
                    pass
                self.data_loader_proc = None

    def on_data_load_error(self, error: str):
        """Handle data loading errors."""
        self.status_label.setText(f"Error loading data: {error}")
        self.progress_bar.setVisible(False)

        # Hide overlays and re-enable inputs
        try:
            if getattr(self, 'tables_overlay', None):
                self.tables_overlay.hide()
            if getattr(self, 'columns_overlay', None):
                self.columns_overlay.hide()
            self.search_input.setEnabled(True)
            self.schema_combo.setEnabled(True)
        except Exception:
            pass

        # Clean up thread
        if self.data_loader_thread:
            self.data_loader_thread.quit()
            self.data_loader_thread.wait()
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
            if not hasattr(self, 'tables') or self.tables is None:
                self.tables = []
            if not hasattr(self, 'columns') or self.columns is None:
                self.columns = []
            if not hasattr(self, 'table_columns') or self.table_columns is None:
                self.table_columns = {}

            first_chunk = len(self.tables) == 0 and len(self.columns) == 0

            # Append new data
            self.tables.extend(tables_chunk or [])
            self.columns.extend(columns_chunk or [])

            for col in (columns_chunk or []):
                table_key = f"{col.schema}.{col.table}"
                if table_key not in self.table_columns:
                    self.table_columns[table_key] = []
                self.table_columns[table_key].append(col)

            # Update model (simple reset for correctness)
            self.tables_model.set_data(self.tables, self.table_columns)

            # After first chunk, hide overlays and enable inputs for immediate interaction
            if first_chunk:
                try:
                    if getattr(self, 'tables_overlay', None):
                        self.tables_overlay.hide()
                    if getattr(self, 'columns_overlay', None):
                        self.columns_overlay.hide()
                    self.search_input.setEnabled(True)
                    self.schema_combo.setEnabled(True)
                except Exception:
                    pass

            # If there's an active search query, re-run the search to include new data
            if hasattr(self, 'search_query') and self.search_query and self.search_query.strip():
                # Clear cache for current query so it re-searches with new data
                cache_key = f"{self.search_mode}:{self.search_query.lower()}"
                if cache_key in self.search_results_cache:
                    del self.search_results_cache[cache_key]
                # Trigger search update with new data
                self._trigger_incremental_search()

            # Update progress bar more meaningfully if total estimate provided
            if total_est and total_est > 0:
                pct = max(1, min(100, int((loaded / total_est) * 100)))
                self.progress_bar.setValue(pct)

        except Exception as e:
            self.status_label.setText(f"Chunk processing error: {e}")

    def update_schema_combo(self):
        """Update schema combo box with all available schemas."""
        # Use all available schemas instead of just those in current data
        schemas = self.all_schemas if hasattr(self, 'all_schemas') and self.all_schemas else sorted(set(table.schema for table in self.tables))

        # Preserve the currently selected schema filter during update
        current_filter = self.schema_filter

        # Block signals to prevent triggering on_schema_changed during update
        self.schema_combo.blockSignals(True)
        try:
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

        # Show overlay over the tables while searching
        try:
            if getattr(self, 'tables_overlay', None):
                self.tables_overlay.show_with_message("Searching…")
        except Exception:
            pass

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

    def _trigger_incremental_search(self):
        """Trigger search immediately without debounce - used for incremental updates during data loading."""
        if not self.search_query or not self.search_query.strip():
            return
        
        # Cancel any existing search
        if self.search_worker:
            self.search_worker.cancel_search()

        if self.search_thread and self.search_thread.isRunning():
            self.search_thread.quit()
            self.search_thread.wait(1000)

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
            if getattr(self, 'tables_overlay', None):
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
            if getattr(self, 'tables_overlay', None):
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
        else:
            self.columns_model.set_columns([])
            self.update_column_details(None, [])

    def update_column_details(self, table_key: Optional[str], columns: List[ColumnInfo]):
        """Update the column details panel with formatted information."""
        if not table_key or not columns:
            self.column_details_text.setPlainText("No table selected")
            return
        
        # Parse table key
        parts = table_key.split('.')
        schema = parts[0] if len(parts) > 0 else ''
        table = parts[1] if len(parts) > 1 else ''
        
        # Format column details
        details = []
        details.append(f"Table: {schema}.{table}")
        details.append(f"Columns: {len(columns)}")
        details.append("="*60)
        details.append("")
        
        for i, col in enumerate(columns, 1):
            details.append(f"{i}. {col.name}")
            details.append(f"   Type:     {col.typename}" + (f"({col.length})" if col.length else ""))
            if col.scale:
                details.append(f"   Scale:    {col.scale}")
            details.append(f"   Nullable: {'Yes' if col.nulls == 'Y' else 'No'}")
            if col.remarks:
                # Wrap long remarks
                remarks_lines = col.remarks.split('\n')
                details.append(f"   Remarks:  {remarks_lines[0]}")
                for remark_line in remarks_lines[1:]:
                    details.append(f"             {remark_line}")
            details.append("")
        
        self.column_details_text.setPlainText("\n".join(details))

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

    def rebuild_schema_cache(self):
        """Rebuild the schema cache from loaded tables."""
        from pathlib import Path
        import json
        
        try:
            # Build schema list from current loaded tables
            if not self.tables:
                QMessageBox.warning(
                    self,
                    "No Data Loaded",
                    "Please load data first before rebuilding the schema list."
                )
                return
            
            schemas = sorted({t.schema for t in self.tables})
            
            # Save to cache
            cache_dir = Path.home() / ".cache" / "dbutils"
            cache_dir.mkdir(parents=True, exist_ok=True)
            cache_path = cache_dir / "schemas.json"
            
            with open(cache_path, 'w') as f:
                json.dump({'schemas': schemas}, f)
            
            self.status_label.setText(f"Rebuilt schema cache with {len(schemas)} schemas")
            
            # Update the combo box with new schemas
            self.all_schemas = schemas
            self.update_schema_combo()
            
            QMessageBox.information(
                self,
                "Schema Cache Rebuilt",
                f"Successfully rebuilt schema cache with {len(schemas)} schemas.\n\n"
                "The schema list will now be loaded from cache on future startups."
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to rebuild schema cache: {e}"
            )

    def clear_all_caches(self):
        """Clear all cached data (schemas and table/column data)."""
        from pathlib import Path
        import glob
        
        try:
            cache_dir = Path.home() / ".cache" / "dbutils"
            
            if not cache_dir.exists():
                QMessageBox.information(
                    self,
                    "Cache Empty",
                    "No cache files found."
                )
                return
            
            # Count and delete cache files (both .json and .json.gz)
            json_files = list(cache_dir.glob("*.json"))
            gz_files = list(cache_dir.glob("*.json.gz"))
            cache_files = json_files + gz_files
            count = len(cache_files)
            
            if count == 0:
                QMessageBox.information(
                    self,
                    "Cache Empty",
                    "No cache files found."
                )
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
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                for cache_file in cache_files:
                    cache_file.unlink()
                
                self.status_label.setText(f"Cleared {count} cache files")
                
                QMessageBox.information(
                    self,
                    "Caches Cleared",
                    f"Successfully deleted {count} cache file(s).\n\n"
                    "Press F5 to reload data from the database."
                )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to clear caches: {e}"
            )

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

        # Terminate subprocess if used
        if self.data_loader_proc and QT_AVAILABLE:
            try:
                self.data_loader_proc._proc.terminate()
            except Exception:
                pass
            self.data_loader_proc = None

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
