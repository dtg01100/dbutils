#!/usr/bin/env python3
"""
dbutils.db_browser - DB2 Schema Browser TUI

Interactive terminal UI for searching and browsing DB2 tables and columns.
Provides a fzf-like search experience for database schemas.
"""

import argparse
import asyncio
import csv
import io
import json
import os
import pickle
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

# Import rich for TUI
try:
    from rich.console import Console
    from rich.text import Text
    from rich.panel import Panel

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# Import Textual for advanced TUI with mouse support
try:
    from textual.app import App, ComposeResult
    from textual.containers import Container, Horizontal, Vertical
    from textual.widgets import Input, Static, DataTable, Footer, Header, Button, Label, ListView, ListItem
    from textual.binding import Binding
    from textual.screen import ModalScreen
    from textual import on

    TEXTUAL_AVAILABLE = True
except ImportError:
    TEXTUAL_AVAILABLE = False

from dataclasses import dataclass


@dataclass
class ColumnInfo:
    """Represents a column in the database."""

    schema: str
    table: str
    name: str
    typename: str
    length: Optional[int]
    scale: Optional[int]
    nulls: str
    remarks: str


@dataclass
class TableInfo:
    """Represents a table in the database."""

    schema: str
    name: str
    remarks: str



def query_runner(sql: str) -> List[Dict]:
    """Run an external `query_runner` command and return parsed results."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as f:
        f.write(sql)
        temp_file = f.name

    try:
        result = subprocess.run(["query_runner", "-t", "db2", temp_file], capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"query_runner failed: {result.stderr}")

        # Try JSON first
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            # Assume tab-separated with header
            reader = csv.DictReader(io.StringIO(result.stdout), delimiter="\t")
            return list(reader)
    finally:
        os.unlink(temp_file)


def mock_get_tables() -> List[TableInfo]:
    """Mock data for testing."""
    return [
        TableInfo(schema="TEST", name="USERS", remarks="User information table"),
        TableInfo(schema="TEST", name="ORDERS", remarks="Order records table"),
        TableInfo(schema="TEST", name="PRODUCTS", remarks="Product catalog table"),
        TableInfo(schema="DACDATA", name="CUSTOMERS", remarks="Customer data"),
        TableInfo(schema="DACDATA", name="INVOICES", remarks="Invoice records"),
        TableInfo(schema="DACDATA", name="OHHST", remarks="OH HST master history table"),
    ]


def mock_get_columns() -> List[ColumnInfo]:
    """Mock data for testing."""
    return [
        ColumnInfo(
            schema="TEST",
            table="USERS",
            name="ID",
            typename="INTEGER",
            length=10,
            scale=0,
            nulls="N",
            remarks="User identifier",
        ),
        ColumnInfo(
            schema="TEST",
            table="USERS",
            name="NAME",
            typename="VARCHAR",
            length=100,
            scale=0,
            nulls="N",
            remarks="User name",
        ),
        ColumnInfo(
            schema="TEST",
            table="USERS",
            name="EMAIL",
            typename="VARCHAR",
            length=255,
            scale=0,
            nulls="Y",
            remarks="User email address",
        ),
        ColumnInfo(
            schema="TEST",
            table="ORDERS",
            name="ID",
            typename="INTEGER",
            length=10,
            scale=0,
            nulls="N",
            remarks="Order identifier",
        ),
        ColumnInfo(
            schema="TEST",
            table="ORDERS",
            name="USER_ID",
            typename="INTEGER",
            length=10,
            scale=0,
            nulls="N",
            remarks="Foreign key to USERS",
        ),
        ColumnInfo(
            schema="TEST",
            table="ORDERS",
            name="PRODUCT_ID",
            typename="INTEGER",
            length=10,
            scale=0,
            nulls="N",
            remarks="Foreign key to PRODUCTS",
        ),
        ColumnInfo(
            schema="TEST",
            table="ORDERS",
            name="ORDER_DATE",
            typename="DATE",
            length=10,
            scale=0,
            nulls="N",
            remarks="Date of order",
        ),
        ColumnInfo(
            schema="TEST",
            table="PRODUCTS",
            name="ID",
            typename="INTEGER",
            length=10,
            scale=0,
            nulls="N",
            remarks="Product identifier",
        ),
        ColumnInfo(
            schema="TEST",
            table="PRODUCTS",
            name="NAME",
            typename="VARCHAR",
            length=200,
            scale=0,
            nulls="N",
            remarks="Product name",
        ),
        ColumnInfo(
            schema="TEST",
            table="PRODUCTS",
            name="PRICE",
            typename="DECIMAL",
            length=10,
            scale=2,
            nulls="N",
            remarks="Product price",
        ),
        ColumnInfo(
            schema="DACDATA",
            table="CUSTOMERS",
            name="CUST_ID",
            typename="INTEGER",
            length=10,
            scale=0,
            nulls="N",
            remarks="Customer identifier",
        ),
        ColumnInfo(
            schema="DACDATA",
            table="CUSTOMERS",
            name="CUST_NAME",
            typename="VARCHAR",
            length=150,
            scale=0,
            nulls="N",
            remarks="Customer name",
        ),
        ColumnInfo(
            schema="DACDATA",
            table="INVOICES",
            name="INV_ID",
            typename="INTEGER",
            length=10,
            scale=0,
            nulls="N",
            remarks="Invoice identifier",
        ),
        ColumnInfo(
            schema="DACDATA",
            table="INVOICES",
            name="CUST_ID",
            typename="INTEGER",
            length=10,
            scale=0,
            nulls="N",
            remarks="Foreign key to CUSTOMERS",
        ),
        ColumnInfo(
            schema="DACDATA",
            table="INVOICES",
            name="INV_DATE",
            typename="DATE",
            length=10,
            scale=0,
            nulls="N",
            remarks="Invoice date",
        ),
    ]


# Cache configuration
CACHE_DIR = Path.home() / ".cache" / "dbutils"
CACHE_FILE = CACHE_DIR / "schema_cache.pkl"


def get_cache_key(schema_filter: Optional[str]) -> str:
    """Generate a cache key based on schema filter."""
    return schema_filter.upper() if schema_filter else "ALL_SCHEMAS"


def load_from_cache(schema_filter: Optional[str]) -> Optional[tuple[List[TableInfo], List[ColumnInfo]]]:
    """Load tables and columns from cache if available and recent."""
    if not CACHE_FILE.exists():
        return None

    try:
        with open(CACHE_FILE, "rb") as f:
            cache_data = pickle.load(f)

        cache_key = get_cache_key(schema_filter)
        if cache_key not in cache_data:
            return None

        cached_item = cache_data[cache_key]
        # Check if cache is less than 1 hour old
        import time

        if time.time() - cached_item["timestamp"] > 3600:
            return None

        return cached_item["tables"], cached_item["columns"]
    except Exception:
        return None


def save_to_cache(schema_filter: Optional[str], tables: List[TableInfo], columns: List[ColumnInfo]) -> None:
    """Save tables and columns to cache."""
    try:
        # Create cache directory if it doesn't exist
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

        # Load existing cache or create new
        cache_data = {}
        if CACHE_FILE.exists():
            try:
                with open(CACHE_FILE, "rb") as f:
                    cache_data = pickle.load(f)
            except Exception:
                cache_data = {}

        # Update cache
        import time

        cache_key = get_cache_key(schema_filter)
        cache_data[cache_key] = {"timestamp": time.time(), "tables": tables, "columns": columns}

        # Save cache
        with open(CACHE_FILE, "wb") as f:
            pickle.dump(cache_data, f)
    except Exception:
        # Silently fail - caching is optional
        pass


@dataclass
class SchemaInfo:
    """Represents a schema with table count."""

    name: str
    table_count: int


def get_available_schemas(use_mock: bool = False) -> List[SchemaInfo]:
    """Fetch list of available schemas with table counts."""
    if use_mock:
        return [
            SchemaInfo(name="DACDATA", table_count=15),
            SchemaInfo(name="TEST", table_count=8),
            SchemaInfo(name="QGPL", table_count=23),
            SchemaInfo(name="PRODUCTION", table_count=42),
        ]

    # Query for schemas with table counts
    schemas_sql = """
        SELECT
            TABLE_SCHEMA,
            COUNT(*) AS TABLE_COUNT
        FROM QSYS2.SYSTABLES
        WHERE TABLE_TYPE IN ('T', 'P')
        AND SYSTEM_TABLE = 'N'
        GROUP BY TABLE_SCHEMA
        ORDER BY TABLE_COUNT DESC, TABLE_SCHEMA
    """

    schemas = []
    try:
        schema_data = query_runner(schemas_sql)
        for row in schema_data:
            schemas.append(SchemaInfo(name=row.get("TABLE_SCHEMA", ""), table_count=int(row.get("TABLE_COUNT", 0))))
    except Exception as exc:
        # If query fails, return empty list
        print(f"Warning: Could not fetch schemas: {exc}")

    return schemas


def schema_exists(schema: str, use_mock: bool = False) -> bool:
    """Check whether a schema (library) exists by detecting at least one table in it.

    Returns True if QSYS2.SYSTABLES reports at least one table for this schema.
    When use_mock=True, returns True only for known mock schemas (DACDATA).
    """
    if use_mock:
        # Mock datasets include DACDATA
        return schema.upper() == "DACDATA"

    sql = f"SELECT 1 FROM QSYS2.SYSTABLES WHERE TABLE_SCHEMA = '{schema.upper()}' AND TABLE_TYPE IN ('T','P') AND SYSTEM_TABLE='N' FETCH FIRST 1 ROWS ONLY"
    try:
        data = query_runner(sql)
        if not data:
            return False
        # If multiple formats, check for truthy results
        return len(data) > 0
    except Exception:
        return False


def get_all_tables_and_columns(
    schema_filter: Optional[str] = None, use_mock: bool = False, use_cache: bool = True
) -> tuple[List[TableInfo], List[ColumnInfo]]:
    """Fetch all tables and columns from the database."""
    if use_mock:
        tables = mock_get_tables()
        columns = mock_get_columns()

        # Apply schema filter to mock data if needed
        if schema_filter:
            tables = [t for t in tables if t.schema.upper() == schema_filter.upper()]
            columns = [c for c in columns if c.schema.upper() == schema_filter.upper()]

        return tables, columns

    # Try to load from cache first
    if use_cache:
        cached_data = load_from_cache(schema_filter)
        if cached_data:
            return cached_data

    # Real database implementation
    tables = []
    columns = []

    # Build schema filter clause
    schema_clause = ""
    if schema_filter:
        schema_clause = f"AND TABLE_SCHEMA = '{schema_filter.upper()}'"

    # Query for tables (DB2 for i uses QSYS2.SYSTABLES instead of SYSCAT.TABLES)
    tables_sql = f"""
        SELECT
            TABLE_SCHEMA,
            TABLE_NAME,
            TABLE_TEXT
        FROM QSYS2.SYSTABLES
        WHERE TABLE_TYPE IN ('T', 'P')
        AND SYSTEM_TABLE = 'N'
        {schema_clause}
        ORDER BY TABLE_SCHEMA, TABLE_NAME
    """

    try:
        tables_data = query_runner(tables_sql)
        for row in tables_data:
            tables.append(
                TableInfo(
                    schema=row.get("TABLE_SCHEMA", ""),
                    name=row.get("TABLE_NAME", ""),
                    remarks=row.get("TABLE_TEXT", ""),
                )
            )
    except Exception as e:
        # If query fails, return empty list (graceful degradation)
        print(f"Warning: Could not fetch tables: {e}")

    # Query for columns (DB2 for i uses QSYS2.SYSCOLUMNS instead of SYSCAT.COLUMNS)
    columns_sql = f"""
        SELECT
            TABLE_SCHEMA,
            TABLE_NAME,
            COLUMN_NAME,
            DATA_TYPE,
            LENGTH,
            NUMERIC_SCALE,
            IS_NULLABLE,
            COLUMN_TEXT
        FROM QSYS2.SYSCOLUMNS
            WHERE TABLE_SCHEMA IN (
            SELECT TABLE_SCHEMA FROM QSYS2.SYSTABLES
            WHERE TABLE_TYPE IN ('T', 'P') AND SYSTEM_TABLE = 'N' {schema_clause}
        )
        ORDER BY TABLE_SCHEMA, TABLE_NAME, ORDINAL_POSITION
    """

    try:
        columns_data = query_runner(columns_sql)
        for row in columns_data:
            # Handle numeric fields that might be strings
            length = row.get("LENGTH")
            scale = row.get("NUMERIC_SCALE")

            # Convert to int if they're strings
            if isinstance(length, str):
                length = int(length) if length and length.isdigit() else None
            if isinstance(scale, str):
                scale = int(scale) if scale and scale.isdigit() else None

            # Map IS_NULLABLE to Y/N format
            nulls = "Y" if row.get("IS_NULLABLE") == "Y" else "N"

            columns.append(
                ColumnInfo(
                    schema=row.get("TABLE_SCHEMA", ""),
                    table=row.get("TABLE_NAME", ""),
                    name=row.get("COLUMN_NAME", ""),
                    typename=row.get("DATA_TYPE", ""),
                    length=length,
                    scale=scale,
                    nulls=nulls,
                    remarks=row.get("COLUMN_TEXT", ""),
                )
            )
    except Exception as e:
        # If query fails, return what we have so far
        print(f"Warning: Could not fetch columns: {e}")

    # Save to cache if we got data
    if use_cache and (tables or columns):
        save_to_cache(schema_filter, tables, columns)

    return tables, columns


class DBBrowserTUI:
    """TUI for browsing DB2 schemas with search functionality."""

    def __init__(self, schema_filter: Optional[str] = None, use_mock: bool = False):
        self.console = Console() if RICH_AVAILABLE else None
        self.schema_filter = schema_filter
        self.use_mock = use_mock

        # Show loading message
        if self.console:
            if use_mock:
                self.console.print("[dim]Loading mock data...[/dim]")
            else:
                self.console.print("[dim]Loading database schema... This may take a moment.[/dim]")

        try:
            self.tables, self.columns = get_all_tables_and_columns(schema_filter, use_mock)
            if self.console:
                self.console.print(f"[green]✓ Loaded {len(self.tables)} tables and {len(self.columns)} columns[/green]")
        except Exception as e:
            if self.console:
                self.console.print(f"[red]Error loading database schema: {e}[/red]")
            self.tables, self.columns = [], []

        # Precompute table columns mapping for performance
        self.table_columns = {}
        for col in self.columns:
            if col.schema and col.table:  # Ensure not None
                table_key = f"{col.schema}.{col.table}"
                if table_key not in self.table_columns:
                    self.table_columns[table_key] = []
                self.table_columns[table_key].append(col)

        # Initialize state
        self.search_query = ""
        self.selected_table = None
        self.selected_column_name: Optional[str] = None
        self.filtered_tables = self.tables
        self.filtered_columns = []

    def select_column(self, column: ColumnInfo) -> None:
        """Select a column in the basic TUI: sets the table and shows all columns
        for that table, with the clicked column highlighted. This mirrors the
        behavior in the Textual TUI's column selection."""
        if not column or not column.schema or not column.table:
            return

        table_key = f"{column.schema}.{column.table}"
        # Find and set the TableInfo
        for t in self.tables:
            if f"{t.schema}.{t.name}" == table_key:
                self.selected_table = t
                break
        # Set selected column name so render will highlight it
        self.selected_column_name = column.name
        # Update filtered columns in case search query or selection changed
        self.update_filters()

    def filter_items(self, items, query):
        """Filter items based on search query (case-insensitive partial match)."""
        if not query:
            return items

        query_lower = query.lower()
        filtered = []

        for item in items:
            # Check different fields for the query term
            name_match = query_lower in (getattr(item, "name", "") or "").lower()
            remarks_match = query_lower in (getattr(item, "remarks", "") or "").lower()
            type_match = query_lower in (getattr(item, "typename", "") or "").lower()

            if name_match or remarks_match or type_match:
                filtered.append(item)

        return filtered

    def update_filters(self):
        """Update filtered lists based on current search query."""
        self.filtered_tables = self.filter_items(self.tables, self.search_query)

        if self.selected_table:
            table_key = f"{self.selected_table.schema}.{self.selected_table.name}"
            if table_key in self.table_columns:
                # Show all columns of selected table, don't filter by search query
                self.filtered_columns = self.table_columns[table_key]
            else:
                self.filtered_columns = []
        else:
            # No table selected, show columns that match search
            self.filtered_columns = self.filter_items(self.columns, self.search_query)

    def run_basic_interactive(self):
        """Fallback interactive mode using standard input."""
        if self.console:
            self.console.print("[yellow]Using basic command-line mode (not fully interactive)[/yellow]")
            self.console.print("For the full interactive TUI experience, run in a proper terminal.")
            self.console.print("")

        while True:
            # Display search bar
            if self.console:
                search_panel = self.render_search_bar()
                self.console.print(search_panel)

            # Display tables and columns side by side using simple text layout
            if self.console:
                table_panel = self.render_table_list()
                col_panel = self.render_column_list()

                # For basic mode, display sequentially since Rich layout doesn't work well in non-TTY
                self.console.print(table_panel)
                self.console.print("")  # Add spacing
                self.console.print(col_panel)

            try:
                # Get user command
                user_input = input("\nEnter command ([N]umber to select table, [S]earch term, [Q]uit): ").strip()

                if not user_input:
                    continue

                # Handle different input types
                if user_input.lower() in ["q", "quit", "exit"]:
                    break
                elif user_input.lower() in ["s", "search"]:
                    search_term = input("Enter search term: ").strip()
                    self.search_query = search_term
                elif user_input.isdigit():
                    table_num = int(user_input) - 1
                    if 0 <= table_num < len(self.filtered_tables):
                        self.selected_table = self.filtered_tables[table_num]
                        self.selected_column_name = None
                        if self.console:
                            self.console.print(
                                f"[green]Selected: {self.selected_table.schema}.{self.selected_table.name}[/green]"
                            )
                    else:
                        if self.console:
                            self.console.print(
                                f"[red]Invalid table number. Please select 1-{len(self.filtered_tables)}[/red]"
                            )
                        continue
                elif user_input.startswith("> "):
                    self.search_query = user_input[2:]
                else:
                    # Treat as search term
                    self.search_query = user_input

            except KeyboardInterrupt:
                break
            except EOFError:
                break

    def render_search_bar(self):
        """Render the search bar."""
        if not self.console:
            return None

        if self.search_query:
            # Truncate long search queries
            search_display = self.search_query[:50]
            if len(self.search_query) > 50:
                search_display += "..."
            search_text = f"> {search_display}"
        else:
            search_text = "> (type to search)"

        return Panel(
            Text(search_text, style="bold"),
            title="Search [Enter: select table, Ctrl+C: quit]",
            border_style="cyan",
        )

    def render_table_list(self, panel_width=None):
        """Render the table list panel as formatted text."""
        if not self.console:
            return None

        self.update_filters()

        lines = []
        lines.append("Tables:")
        for i, t in enumerate(self.filtered_tables[:10]):  # Show first 10
            marker = (
                "→"
                if (
                    self.selected_table
                    and t.schema == self.selected_table.schema
                    and t.name == self.selected_table.name
                )
                else " "
            )
            table_info = f"{i + 1}. {t.schema}.{t.name}"
            lines.append(f"  {marker} {table_info}")

        content = "\n".join(lines)
        return Panel(
            Text(content),
            title=f"Tables ({len(self.filtered_tables)} total)",
            border_style="blue",
        )

    def render_column_list(self, panel_width=None):
        """Render the column list panel."""
        if not self.console:
            return None

        if not self.selected_table:
            # If there's an active search, show columns matching the query across all tables
            if self.search_query:
                # Use filtered_columns which was computed by update_filters()
                self.update_filters()
                matches = self.filtered_columns
                lines = [f"Columns matching '{self.search_query}':"]
                for i, c in enumerate(matches[:50]):
                    lines.append(f"  {i + 1}. {c.schema}.{c.table}.{c.name} ({c.typename})")

                content = "\n".join(lines)
                return Panel(Text(content), title=f"Column Matches ({len(matches)} found)", border_style="yellow")

            return Panel(
                "Select a table to see its columns\n\nUse number keys or ↑↓ arrows to select tables",
                title="Columns",
                border_style="yellow",
            )

        lines = []
        lines.append(f"Columns in {self.selected_table.schema}.{self.selected_table.name}:")

        table_key = f"{self.selected_table.schema}.{self.selected_table.name}"
        columns = self.table_columns.get(table_key, [])

        for i, c in enumerate(columns[:10]):  # Show first 10
            marker = "→" if self.selected_column_name and c.name == self.selected_column_name else " "
            lines.append(f"  {marker} {i + 1}. {c.name} ({c.typename})")

        content = "\n".join(lines)
        return Panel(
            Text(content),
            title=f"Columns ({len(columns)} total)",
            border_style="green",
        )

    def run(self):
        """Run the TUI application."""
        if self.console:
            self.console.print("DB2 Schema Browser - Interactive TUI", style="bold blue")
            self.console.print("Loading... (the interactive search bar will appear below)", style="dim")

        try:
            self.run_basic_interactive()
        except KeyboardInterrupt:
            pass


# Textual-based TUI with keyboard and mouse support
if TEXTUAL_AVAILABLE:

    class SettingsScreen(ModalScreen):
        """A modal screen for settings configuration."""

        CSS = """
        SettingsScreen {
            align: center middle;
        }

        #settings-dialog {
            width: 70;
            height: auto;
            max-height: 90%;
            border: thick $background 80%;
            background: $surface;
            padding: 1 2;
        }

        #settings-title {
            width: 100%;
            text-align: center;
            color: $accent;
            text-style: bold;
            margin-bottom: 1;
        }

        .settings-section {
            margin: 1 0;
        }

        .settings-label {
            color: $text;
            text-style: bold;
            margin: 1 0 0 0;
        }

        #schema-list {
            height: 20;
            border: solid $primary;
            margin: 1 0;
        }

        .help-text {
            color: $text-muted;
            text-style: italic;
            margin: 0 0 1 0;
        }

        #loading-text {
            color: $warning;
            text-style: italic;
            text-align: center;
        }

        #buttons-container {
            layout: horizontal;
            width: 100%;
            height: auto;
            align: center middle;
            margin-top: 1;
        }

        #buttons-container Button {
            margin: 0 1;
        }
        """

        BINDINGS = [
            Binding("escape", "dismiss(None)", "Cancel"),
        ]

        def __init__(self, current_schema: Optional[str] = None, use_mock: bool = False):
            super().__init__()
            self.current_schema = current_schema or ""
            self.use_mock = use_mock
            self.schemas: List[SchemaInfo] = []
            self.selected_schema: Optional[str] = None

        def compose(self) -> ComposeResult:
            """Compose the settings dialog."""
            with Container(id="settings-dialog"):
                yield Label("Select Schema", id="settings-title")

                with Container(classes="settings-section"):
                    yield Label("Available Schemas:", classes="settings-label")
                    yield Label("Loading schemas...", id="loading-text")
                    yield ListView(id="schema-list")
                    yield Label(
                        "Select a schema to filter tables, or choose 'All Schemas' to search everything.",
                        classes="help-text",
                    )

                with Horizontal(id="buttons-container"):
                    yield Button("Select", variant="primary", id="select-button")
                    yield Button("Cancel", variant="default", id="cancel-button")

        async def on_mount(self) -> None:
            """Load schemas when mounted."""
            # Load schemas in background
            self.run_worker(self.load_schemas, exclusive=True)

        async def load_schemas(self) -> None:
            """Load available schemas."""
            try:
                # Fetch schemas
                self.schemas = get_available_schemas(self.use_mock)

                # Update UI
                loading_label = self.query_one("#loading-text", Label)
                loading_label.display = False

                schema_list = self.query_one("#schema-list", ListView)

                # Add "All Schemas" option
                all_item = ListItem(Label("[All Schemas] (all tables)"))
                all_item.add_class("schema-all")
                schema_list.append(all_item)

                # Add individual schemas
                for schema in self.schemas:
                    item_label = f"{schema.name} ({schema.table_count} tables)"
                    item = ListItem(Label(item_label))
                    if schema.name == self.current_schema:
                        schema_list.index = len(schema_list) - 1 + 1  # Will select after append
                    schema_list.append(item)

                # Set initial selection
                if self.current_schema:
                    # Find and select current schema
                    for idx, schema in enumerate(self.schemas):
                        if schema.name == self.current_schema:
                            schema_list.index = idx + 1  # +1 for "All Schemas" option
                            break
                else:
                    # Select "All Schemas"
                    schema_list.index = 0

            except Exception as e:
                loading_label = self.query_one("#loading-text", Label)
                loading_label.update(f"Error loading schemas: {e}")

        @on(ListView.Selected, "#schema-list")
        def schema_selected(self, event: ListView.Selected) -> None:
            """Handle schema selection from list."""
            index = event.list_view.index
            if index == 0:
                # "All Schemas" selected
                self.selected_schema = None
            else:
                # Individual schema selected
                schema_idx = index - 1
                if 0 <= schema_idx < len(self.schemas):
                    self.selected_schema = self.schemas[schema_idx].name

        @on(Button.Pressed, "#select-button")
        def select_schema(self) -> None:
            """Select the highlighted schema and close."""
            schema_list = self.query_one("#schema-list", ListView)
            index = schema_list.index

            if index is None or index < 0:
                # Nothing selected, use current
                self.dismiss(self.current_schema if self.current_schema else None)
                return

            if index == 0:
                # "All Schemas" selected
                self.dismiss(None)
            else:
                # Individual schema selected
                schema_idx = index - 1
                if 0 <= schema_idx < len(self.schemas):
                    self.dismiss(self.schemas[schema_idx].name)
                else:
                    self.dismiss(None)

        @on(Button.Pressed, "#cancel-button")
        def cancel_settings(self) -> None:
            """Cancel and close."""
            self.dismiss(None)

    class DBBrowserApp(App):
        """A Textual app for browsing DB2 schemas with keyboard and mouse support."""

        CSS = """
        Screen {
            layout: vertical;
        }

        #search-container {
            height: auto;
            layout: horizontal;
            background: $surface;
            border: solid $primary;
            padding: 1;
            align: center middle;
        }

        #search-input {
            width: 1fr;
            margin: 0;
            color: white;
            background: black;
        }

        #search-input:focus {
            background: #111111;
        }

        #search-input > .input--placeholder {
            color: gray;
        }

        #search-mode-label {
            width: auto;
            min-width: 20;
            margin: 0 1 0 0;
        }

        Button#search-mode-label {
            width: auto;
            min-width: 20;
        }

        #main-container {
            layout: horizontal;
            height: 1fr;
        }

        #tables-container {
            width: 1fr;
            border: solid $accent;
        }

        #columns-container {
            width: 2fr;
            border: solid $success;
        }

        DataTable {
            height: 1fr;
        }

        DataTable > .datatable--cursor {
            background: $accent 50%;
        }

        DataTable > .datatable--hover {
            background: $accent 30%;
        }

        .info-text {
            color: $text-muted;
            padding: 1;
        }

        .search-mode {
            color: $accent;
            text-style: bold;
            background: $panel;
            border: solid $accent;
            padding: 0 1;
        }
        """

        BINDINGS = [
            Binding("q", "quit", "Quit"),
            Binding("ctrl+c", "quit", "Quit"),
            Binding("escape", "clear_search", "Clear Search"),
            Binding("f1", "help", "Help", show=False),
            Binding("/", "focus_search", "Search"),
            Binding("tab", "toggle_search_mode", "Toggle Search Mode"),
            Binding("s", "open_settings", "Settings"),
        ]

        def __init__(self, schema_filter: Optional[str] = None, use_mock: bool = False, use_cache: bool = True):
            super().__init__()
            self.schema_filter = schema_filter
            self.use_mock = use_mock
            self.use_cache = use_cache
            self.tables: List[TableInfo] = []
            self.columns: List[ColumnInfo] = []
            self.table_columns: Dict[str, List[ColumnInfo]] = {}
            self.search_query = ""
            self.search_mode = "tables"  # "tables" or "columns"
            # Search optimization: cache results and debounce updates
            self._search_cache: Dict[str, Dict[str, Any]] = {}
            self._last_search_query = ""
            self._last_search_mode = ""
            self._debounce_timer: Optional[asyncio.Task] = None
            # Pre-computed lowercase fields for faster searching
            self._table_search_data: Dict[str, str] = {}  # table_key -> lowercase searchable text
            self._column_search_data: Dict[str, str] = {}  # column_key -> lowercase searchable text

        # -----------------------------
        # Search caching & debounce utils
        # -----------------------------
        def _cache_key(self, mode: str, query: str) -> str:
            return f"{mode}|{(query or '').lower()}"

        def _get_cached(self, mode: str, query: str) -> Optional[Dict[str, Any]]:
            return self._search_cache.get(self._cache_key(mode, query))

        def _set_cached(self, mode: str, query: str, value: Dict[str, Any]) -> None:
            self._search_cache[self._cache_key(mode, query)] = value

        def _clear_search_cache(self) -> None:
            self._search_cache.clear()
            self._last_search_query = ""
            self._last_search_mode = ""

        def _apply_search_update(self) -> None:
            """Apply current search query/mode to UI."""
            self.update_tables_display()
            # If a table is selected, update columns display too
            try:
                tables_table = self.query_one("#tables-table", DataTable)
                if tables_table.cursor_row >= 0:
                    row = tables_table.get_row_at(tables_table.cursor_row)
                    if row:
                        self.update_columns_display(str(row[0]))
            except Exception:
                pass

        async def _debounced_apply(self, expected_query: str, expected_mode: str) -> None:
            try:
                await asyncio.sleep(0.2)
            except Exception:
                return
            # Only apply if state hasn't changed since timer was scheduled
            if self.search_query == expected_query and self.search_mode == expected_mode:
                self._apply_search_update()

        def compose(self) -> ComposeResult:
            """Create child widgets for the app."""
            yield Header()
            with Container(id="search-container"):
                yield Button("📋 Search Tables", id="search-mode-label", variant="default")
                yield Input(placeholder="Type to search tables by name or description...", id="search-input")
            with Horizontal(id="main-container"):
                with Vertical(id="tables-container"):
                    yield Static("Tables", classes="info-text")
                    yield DataTable(id="tables-table", cursor_type="row")
                with Vertical(id="columns-container"):
                    yield Static("Columns (select a table)", classes="info-text")
                    yield DataTable(id="columns-table", cursor_type="row")
            yield Footer()

        async def on_mount(self) -> None:
            """Load data when the app starts."""
            # Set the app title to show database and schema
            if self.schema_filter:
                self.title = f"DB Browser [S782c451] - Schema: {self.schema_filter}"
                self.sub_title = "Press 'S' to change schema"
            else:
                self.title = "DB Browser [S782c451] - All Schemas"
                self.sub_title = "Press 'S' to filter by schema"

            # Setup tables table FIRST (before showing loading message)
            tables_table = self.query_one("#tables-table", DataTable)
            tables_table.add_columns("Table", "Info")
            tables_table.cursor_type = "row"
            tables_table.zebra_stripes = True

            # Setup columns table FIRST (before showing loading message)
            columns_table = self.query_one("#columns-table", DataTable)
            columns_table.add_columns("Column", "Type", "Nulls", "Description")
            columns_table.cursor_type = "row"
            columns_table.zebra_stripes = True

            # Update info text to show loading
            tables_info = self.query_one("#tables-container .info-text", Static)
            tables_info.update("Loading tables...")

            # Show loading notification and start loading data after UI is ready
            self.call_after_refresh(self.start_loading)

        def start_loading(self) -> None:
            """Start loading data after UI is rendered."""
            # Show loading notification
            if self.use_mock:
                self.notify("Loading mock data...", timeout=1)
            else:
                if self.schema_filter:
                    self.notify(f"Loading schema: {self.schema_filter}... This may take a moment.", timeout=3)
                else:
                    self.notify("Loading all database schemas... This may take a moment.", timeout=3)

            # Load data asynchronously to not block UI
            # Run the query in a worker to keep UI responsive
            self.run_worker(self.load_data, exclusive=True)

        async def load_data(self) -> None:
            """Load data from database in background."""
            try:
                # Load tables and columns
                self.tables, self.columns = get_all_tables_and_columns(
                    self.schema_filter, self.use_mock, self.use_cache
                )

                # Build table-columns mapping and pre-compute search data
                self.table_columns = {}
                self._table_search_data = {}
                self._column_search_data = {}
                
                for table in self.tables:
                    table_key = f"{table.schema}.{table.name}"
                    # Pre-compute lowercase searchable text for each table
                    search_text = f"{table.name} {table.schema} {table.remarks or ''}".lower()
                    self._table_search_data[table_key] = search_text
                
                for col in self.columns:
                    if col.schema and col.table:
                        table_key = f"{col.schema}.{col.table}"
                        if table_key not in self.table_columns:
                            self.table_columns[table_key] = []
                        self.table_columns[table_key].append(col)
                        
                        # Pre-compute lowercase searchable text for each column
                        col_key = f"{col.schema}.{col.table}.{col.name}"
                        search_text = f"{col.name} {col.typename} {col.remarks or ''}".lower()
                        self._column_search_data[col_key] = search_text

                # Populate tables
                self.update_tables_display()
                # Clear any stale search cache after data refresh
                self._clear_search_cache()

                # Focus search input
                self.query_one("#search-input", Input).focus()

                # Show success message
                table_count = len(self.tables)
                column_count = len(self.columns)

                if table_count == 0:
                    if self.schema_filter:
                        self.notify(
                            f"⚠️ No tables found in schema '{self.schema_filter}'. Try Settings (S) to change schema.",
                            severity="warning",
                            timeout=8,
                        )
                    else:
                        self.notify("⚠️ No tables loaded! Check database connection.", severity="warning", timeout=5)
                else:
                    if self.schema_filter:
                        msg = f"✓ Loaded {table_count} tables from '{self.schema_filter}' ({column_count} columns)"
                    else:
                        msg = f"✓ Loaded {table_count} tables from all schemas ({column_count} columns)"
                    self.notify(msg, severity="information", timeout=3)
            except Exception as e:
                self.notify(f"❌ Error loading schema: {e}", severity="error", timeout=10)
                self.tables, self.columns = [], []
                self.update_tables_display()

        def update_tables_display(self) -> None:
            """Update the tables display based on current search mode."""
            tables_table = self.query_one("#tables-table", DataTable)
            tables_table.clear()

            if self.search_mode == "tables":
                # Standard table search - filter tables by name/description
                if not self.search_query:
                    filtered_tables = self.tables
                else:
                    cached = self._get_cached("tables", self.search_query)
                    if cached and "filtered_tables" in cached:
                        filtered_tables = cached["filtered_tables"]
                    else:
                        filtered_tables = self.filter_tables(self.tables, self.search_query)
                        self._set_cached("tables", self.search_query, {"filtered_tables": filtered_tables})

                # Add rows
                for table in filtered_tables:
                    tables_table.add_row(
                        table.name, table.remarks or "", key=f"{table.schema}.{table.name}"
                    )

                # Update info text
                info = self.query_one("#tables-container .info-text", Static)
                info.update(f"Tables ({len(filtered_tables)} matching)")

            else:  # search_mode == "columns"
                # Column-focused search - find tables that contain matching columns
                if not self.search_query:
                    # Show all tables when no search
                    for table in self.tables:
                        tables_table.add_row(
                            table.name, table.remarks or "", key=f"{table.schema}.{table.name}"
                        )
                    info = self.query_one("#tables-container .info-text", Static)
                    info.update(f"Tables ({len(self.tables)} total)")
                else:
                    # Try cache first
                    cached = self._get_cached("columns", self.search_query)
                    if cached and "matching_table_counts" in cached and "matching_columns" in cached:
                        matching_table_counts = cached["matching_table_counts"]
                        matching_columns = cached["matching_columns"]
                    else:
                        matching_table_counts: Dict[str, int] = {}
                        matching_columns = []
                        q = self.search_query
                        for col in self.columns:
                            if self.column_matches_query(col, q):
                                t_key = f"{col.schema}.{col.table}"
                                matching_table_counts[t_key] = matching_table_counts.get(t_key, 0) + 1
                                matching_columns.append(col)
                        self._set_cached(
                            "columns",
                            self.search_query,
                            {
                                "matching_table_counts": matching_table_counts,
                                "matching_columns": matching_columns,
                            },
                        )

                    # Display tables that have matching columns
                    tables_with_matches = []
                    for table in self.tables:
                        table_key = f"{table.schema}.{table.name}"
                        if table_key in matching_table_counts:
                            match_count = matching_table_counts[table_key]
                            info_text = table.remarks or ""
                            if info_text:
                                info_text = f"{info_text} — {match_count} matching column(s)"
                            else:
                                info_text = f"{match_count} matching column(s)"
                            tables_table.add_row(
                                table.name,
                                info_text,
                                key=table_key,
                            )
                            tables_with_matches.append(table)

                    # Update info text
                    info = self.query_one("#tables-container .info-text", Static)
                    info.update(f"Tables with matching columns ({len(tables_with_matches)} found)")
                    # Populate the columns panel with all matches across tables
                    columns_table = self.query_one("#columns-table", DataTable)
                    columns_table.clear()
                    for col in matching_columns:
                        col_key = f"{col.schema}.{col.table}.{col.name}"
                        type_str = f"{col.typename}"
                        if col.length:
                            type_str += f"({col.length}"
                            if col.scale:
                                type_str += f",{col.scale}"
                            type_str += ")"
                        columns_table.add_row(
                            f"{col.schema}.{col.table}.{col.name}",
                            type_str,
                            col.nulls,
                            col.remarks or "",
                            key=col_key,
                        )
                    info = self.query_one("#columns-container .info-text", Static)
                    info.update(f"Column matches across tables ({len(matching_columns)} found)")

                # If we have a selected table, ensure the DataTable cursor highlights it
                try:
                    if self.selected_table:
                        for idx in range(tables_table.row_count):
                            row = tables_table.get_row_at(idx)
                            if row and row[0] == self.selected_table.name:
                                tables_table.cursor_row = idx
                                break
                except Exception:
                    pass

        def column_matches_query(self, col: ColumnInfo, query: str) -> bool:
            """Check if a column matches the search query using pre-computed data and fuzzy matching."""
            if not query:
                return True
                
            col_key = f"{col.schema}.{col.table}.{col.name}"
            search_text = self._column_search_data.get(col_key, "")
            query_lower = query.lower()
            
            # Fast substring check first using pre-computed data
            if query_lower in search_text:
                return True
            
            # Fall back to fuzzy matching
            return (
                self.fuzzy_match(col.name, query)
                or self.fuzzy_match(col.typename, query)
                or self.fuzzy_match(col.remarks or "", query)
            )

        def update_columns_display(self, table_key: Optional[str] = None) -> None:
            """Update the columns display for selected table."""
            columns_table = self.query_one("#columns-table", DataTable)
            columns_table.clear()

            if not table_key:
                info = self.query_one("#columns-container .info-text", Static)
                info.update("Columns (select a table)")
                return

            # Get columns for this table
            columns = self.table_columns.get(table_key, [])

            # In column search mode with a query, show all columns but dim non-matches
            show_all_with_dimming = self.search_mode == "columns" and self.search_query

            if show_all_with_dimming:
                # Show all columns, marking which ones match
                matching_count = 0
                for col in columns:
                    type_str = f"{col.typename}"
                    if col.length:
                        type_str += f"({col.length}"
                        if col.scale:
                            type_str += f",{col.scale}"
                        type_str += ")"

                    # Use full key including schema.table.column so we can map selection back
                    col_key = f"{col.schema}.{col.table}.{col.name}"

                    # Check if this column matches the search query
                    matches = self.column_matches_query(col, self.search_query)
                    if matches:
                        matching_count += 1
                        # Matching columns shown normally
                        columns_table.add_row(col.name, type_str, col.nulls, col.remarks or "", key=col_key)
                    else:
                        # Non-matching columns shown with prefix indicator
                        dim_name = f"· {col.name}"
                        columns_table.add_row(dim_name, type_str, col.nulls, col.remarks or "", key=col_key)

                # Update info text with match count
                info = self.query_one("#columns-container .info-text", Static)
                schema, table = table_key.split(".", 1)
                info.update(f"Columns in {schema}.{table} ({matching_count} matching, {len(columns)} total)")
            else:
                # Standard mode: filter columns if there's a search query in table mode
                if self.search_query and self.search_mode == "tables":
                    columns = self.filter_columns(columns, self.search_query)

                # Add rows
                for col in columns:
                    type_str = f"{col.typename}"
                    if col.length:
                        type_str += f"({col.length}"
                        if col.scale:
                            type_str += f",{col.scale}"
                        type_str += ")"

                    # Use full key including schema.table.column so we can map selection back
                    col_key = f"{col.schema}.{col.table}.{col.name}"
                    columns_table.add_row(col.name, type_str, col.nulls, col.remarks or "", key=col_key)

                # Update info text
                info = self.query_one("#columns-container .info-text", Static)
                schema, table = table_key.split(".", 1)
                info.update(f"Columns in {schema}.{table} ({len(columns)} total)")

            # If a column was previously selected, focus/highlight it now
            if hasattr(self, "selected_column_key") and self.selected_column_key:
                try:
                    # Find the selected column in the columns table and set the cursor
                    sel_col = self.selected_column_key
                    sel_col_name = sel_col.split(".")[-1]
                    for idx in range(columns_table.row_count):
                        row = columns_table.get_row_at(idx)
                        if row:
                            # Handle both normal and dimmed column names
                            col_display_name = str(row[0])
                            actual_col_name = col_display_name.lstrip("· ")
                            if actual_col_name == sel_col_name:
                                columns_table.cursor_row = idx
                                break
                except Exception:
                    pass

        def edit_distance(self, s1: str, s2: str) -> int:
            """
            Calculate Levenshtein distance between two strings.
            Returns the minimum number of edits needed to transform s1 into s2.
            """
            if len(s1) < len(s2):
                return self.edit_distance(s2, s1)

            if len(s2) == 0:
                return len(s1)

            previous_row = range(len(s2) + 1)
            for i, c1 in enumerate(s1):
                current_row = [i + 1]
                for j, c2 in enumerate(s2):
                    # Cost of insertions, deletions, or substitutions
                    insertions = previous_row[j + 1] + 1
                    deletions = current_row[j] + 1
                    substitutions = previous_row[j] + (c1 != c2)
                    current_row.append(min(insertions, deletions, substitutions))
                previous_row = current_row

            return previous_row[-1]

        def fuzzy_match(self, text: str, query: str) -> bool:
            """
            Optimized fuzzy match with early exits.
            1. Exact substring match (highest priority)
            2. Word boundary match (e.g., 'cus' matches 'customer_order')
            3. Edit distance within threshold for similar words
            4. Sequential character match (fallback fuzzy)
            """
            if not query:
                return True
            if not text:
                return False

            text_lower = text.lower()
            query_lower = query.lower()

            # Strategy 1: Exact substring match (fast and intuitive) - early exit
            if query_lower in text_lower:
                return True
            
            # For very short queries, skip expensive operations
            if len(query_lower) < 2:
                return False

            # Strategy 2: Check each word in text (split by _ or space)
            words = text_lower.replace("_", " ").split()
            for word in words:
                # Check if query is prefix of word - early exit
                if word.startswith(query_lower):
                    return True

                # Check edit distance only for similar-length words (optimization)
                if len(query_lower) >= 3 and abs(len(word) - len(query_lower)) <= 2:
                    # Allow 1 edit per 3 characters
                    max_distance = max(1, len(query_lower) // 3)
                    if self.edit_distance(word, query_lower) <= max_distance:
                        return True

            # Strategy 3: Sequential character match (fallback fuzzy)
            # Only try this if query is reasonably short
            if len(query_lower) <= len(text_lower):
                text_idx = 0
                for char in query_lower:
                    text_idx = text_lower.find(char, text_idx)
                    if text_idx == -1:
                        return False
                    text_idx += 1
                return True
            
            return False

        def filter_tables(self, tables: List[TableInfo], query: str) -> List[TableInfo]:
            """Filter tables based on fuzzy search query using pre-computed data."""
            if not query:
                return tables
            
            query_lower = query.lower()
            filtered = []
            
            # Use pre-computed search data for faster matching
            for table in tables:
                table_key = f"{table.schema}.{table.name}"
                search_text = self._table_search_data.get(table_key, "")
                
                # Fast substring check first (most common case)
                if query_lower in search_text:
                    filtered.append(table)
                # Fall back to fuzzy match if needed
                elif self.fuzzy_match(table.name, query) or self.fuzzy_match(table.remarks or "", query):
                    filtered.append(table)
            
            return filtered

        def filter_columns(self, columns: List[ColumnInfo], query: str) -> List[ColumnInfo]:
            """Filter columns based on fuzzy search query using pre-computed data."""
            if not query:
                return columns
            
            query_lower = query.lower()
            filtered = []
            
            # Use pre-computed search data for faster matching
            for col in columns:
                col_key = f"{col.schema}.{col.table}.{col.name}"
                search_text = self._column_search_data.get(col_key, "")
                
                # Fast substring check first (most common case)
                if query_lower in search_text:
                    filtered.append(col)
                # Fall back to fuzzy match if needed
                elif self.fuzzy_match(col.name, query) or self.fuzzy_match(col.typename, query):
                    filtered.append(col)
            
            return filtered

        @on(Input.Changed, "#search-input")
        def on_search_changed(self, event: Input.Changed) -> None:
            """Handle search input changes with debounce and caching."""
            self.search_query = event.value
            expected_query = self.search_query
            expected_mode = self.search_mode
            # Debounce recompute to reduce per-keystroke cost
            try:
                if self._debounce_timer and not self._debounce_timer.done():
                    self._debounce_timer.cancel()
            except Exception:
                pass
            try:
                self._debounce_timer = asyncio.create_task(
                    self._debounced_apply(expected_query, expected_mode)
                )
            except Exception:
                # Fallback to immediate update if scheduling fails
                self._apply_search_update()

        @on(DataTable.RowSelected, "#tables-table")
        def on_table_selected(self, event: DataTable.RowSelected) -> None:
            """Handle table selection."""
            if event.row_key:
                # Clear prior column selection when a table is directly selected
                self.selected_column_key = None
                self.update_columns_display(event.row_key.value)

        @on(DataTable.RowSelected, "#columns-table")
        def on_column_selected(self, event: DataTable.RowSelected) -> None:
            """When a column is selected, switch to the table containing it and
            highlight the clicked column.
            """
            try:
                if event.row_key:
                    col_key = event.row_key.value  # e.g. DACDATA.CUSTOMERS.CUST_ID
                    parts = col_key.split(".")
                    if len(parts) >= 3:
                        table_key = f"{parts[0]}.{parts[1]}"
                        # Remember selected column so we can highlight it after re-render
                        self.selected_column_key = col_key

                        # Find and set the TableInfo as selected
                        for t in self.tables:
                            if f"{t.schema}.{t.name}" == table_key:
                                self.selected_table = t
                                break

                        # Update displays to focus the table and then the column
                        self.update_tables_display()
                        self.update_columns_display(table_key)
            except Exception:
                pass

        @on(DataTable.RowHighlighted, "#tables-table")
        def on_table_highlighted(self, event: DataTable.RowHighlighted) -> None:
            """Handle table highlighting (keyboard navigation or mouse hover)."""
            if event.row_key:
                table_key = event.row_key.value
                self.update_columns_display(table_key)
                # Show IBM i path for the highlighted table
                try:
                    # Find the TableInfo (path display removed)
                    for t in self.tables:
                        if f"{t.schema}.{t.name}" == table_key:
                            break
                except Exception:
                    pass

        @on(Button.Pressed, "#search-mode-label")
        def on_search_mode_button_pressed(self) -> None:
            """Handle search mode button click."""
            self.action_toggle_search_mode()

        def action_focus_search(self) -> None:
            """Focus the search input."""
            self.query_one("#search-input", Input).focus()

        def action_clear_search(self) -> None:
            """Clear the search."""
            search_input = self.query_one("#search-input", Input)
            search_input.value = ""
            search_input.focus()

        def action_toggle_search_mode(self) -> None:
            """Toggle between table search and column search modes."""
            # Remember current table selection before switching
            current_table_key = None
            try:
                tables_table = self.query_one("#tables-table", DataTable)
                if tables_table.cursor_row >= 0:
                    row = tables_table.get_row_at(tables_table.cursor_row)
                    if row:
                        # Get the row key which is schema.table
                        current_table_key = list(tables_table.rows.keys())[tables_table.cursor_row]
            except Exception:
                pass
            
            if self.search_mode == "tables":
                self.search_mode = "columns"
                mode_button = self.query_one("#search-mode-label", Button)
                mode_button.label = "🔍 Search Columns"
                search_input = self.query_one("#search-input", Input)
                search_input.placeholder = "Type to search columns by name, type, or description..."
                self.notify(
                    "🔍 COLUMN SEARCH MODE: Find tables with matching columns", severity="information", timeout=4
                )
            else:
                self.search_mode = "tables"
                mode_button = self.query_one("#search-mode-label", Button)
                mode_button.label = "📋 Search Tables"
                search_input = self.query_one("#search-input", Input)
                search_input.placeholder = "Type to search tables by name or description..."
                self.notify("📋 TABLE SEARCH MODE: Filter by table name/description", severity="information", timeout=4)

            # Re-run search with new mode
            self.update_tables_display()
            
            # Restore table selection and update columns display
            if current_table_key:
                try:
                    tables_table = self.query_one("#tables-table", DataTable)
                    # Find the row with matching key
                    for idx, key in enumerate(tables_table.rows.keys()):
                        if key == current_table_key:
                            tables_table.cursor_row = idx
                            # Update columns display for the selected table
                            self.update_columns_display(str(current_table_key))
                            break
                except Exception:
                    pass

        def action_open_settings(self) -> None:
            """Open the settings dialog."""

            def handle_settings_result(new_schema: Optional[str]) -> None:
                """Handle the result from settings dialog."""
                if new_schema is not None:
                    # Schema was changed
                    old_schema = self.schema_filter
                    self.schema_filter = new_schema

                    # Show notification about schema change
                    if new_schema:
                        self.notify(f"Schema filter changed to: {new_schema}", severity="information", timeout=3)
                    else:
                        self.notify("Schema filter cleared - searching all schemas", severity="information", timeout=3)

                    # Only reload if schema actually changed
                    if old_schema != new_schema:
                        self.notify("Reloading data with new schema filter...", timeout=2)
                        self.run_worker(self.reload_data, exclusive=True)

            self.push_screen(SettingsScreen(self.schema_filter, self.use_mock), handle_settings_result)

        async def reload_data(self) -> None:
            """Reload data with new settings."""
            try:
                # Verify schema exists before loading - helpful if DACDATA is missing
                if self.schema_filter:
                    if not schema_exists(self.schema_filter, self.use_mock):
                        self.notify(
                            f"Schema '{self.schema_filter}' not found in current database. Try settings (S) to select a different schema.",
                            severity="warning",
                            timeout=6,
                        )
                        # Clear existing data and return
                        self.tables, self.columns = [], []
                        self.update_tables_display()
                        return
                # Update title to reflect new schema
                if self.schema_filter:
                    self.title = f"DB Browser [S782c451] - Schema: {self.schema_filter}"
                    self.sub_title = "Press 'S' to change schema"
                else:
                    self.title = "DB Browser [S782c451] - All Schemas"
                    self.sub_title = "Press 'S' to filter by schema"

                # Clear existing data
                self.tables = []
                self.columns = []
                self.table_columns = {}
                self._table_search_data = {}
                self._column_search_data = {}

                # Clear displays
                tables_table = self.query_one("#tables-table", DataTable)
                tables_table.clear()
                columns_table = self.query_one("#columns-table", DataTable)
                columns_table.clear()

                # Reload data
                self.tables, self.columns = get_all_tables_and_columns(
                    self.schema_filter, self.use_mock, self.use_cache
                )

                # Rebuild table-columns mapping and pre-computed search data
                for table in self.tables:
                    table_key = f"{table.schema}.{table.name}"
                    # Pre-compute lowercase searchable text for each table
                    search_text = f"{table.name} {table.schema} {table.remarks or ''}".lower()
                    self._table_search_data[table_key] = search_text
                
                for col in self.columns:
                    if col.schema and col.table:
                        table_key = f"{col.schema}.{col.table}"
                        if table_key not in self.table_columns:
                            self.table_columns[table_key] = []
                        self.table_columns[table_key].append(col)
                        
                        # Pre-compute lowercase searchable text for each column
                        col_key = f"{col.schema}.{col.table}.{col.name}"
                        search_text = f"{col.name} {col.typename} {col.remarks or ''}".lower()
                        self._column_search_data[col_key] = search_text

                # Update display
                self.update_tables_display()
                # Invalidate search cache after reload
                self._clear_search_cache()

                # Show result message
                table_count = len(self.tables)
                if table_count == 0:
                    if self.schema_filter:
                        self.notify(
                            f"⚠️ No tables found in schema '{self.schema_filter}'", severity="warning", timeout=5
                        )
                    else:
                        self.notify("⚠️ No tables found", severity="warning", timeout=5)
                else:
                    if self.schema_filter:
                        self.notify(
                            f"✓ Loaded {table_count} tables from '{self.schema_filter}'",
                            severity="information",
                            timeout=2,
                        )
                    else:
                        self.notify(
                            f"✓ Loaded {table_count} tables from all schemas", severity="information", timeout=2
                        )
            except Exception as e:
                self.notify(f"Error reloading data: {str(e)}", severity="error", timeout=5)

        def action_help(self) -> None:
            """Show help information."""
            self.notify(
                "Navigation: ↑↓/mouse | Search: type | Tab: toggle mode | S: settings | Y: copy path | /: focus | Esc: clear | Q: quit",
                timeout=5,
            )

        def action_copy_table_path(self) -> None:
            """Copy the currently highlighted table's IBM i path to clipboard."""
            # Path copying was removed; show help about keybindings instead
            self.notify("Copy Table Path is not available in this build", severity="warning", timeout=3)


def search_and_output(query, schema_filter=None, limit=10, output_format="table", use_mock=False):
    """Perform a search and output results directly without TUI."""
    tables, columns = get_all_tables_and_columns(schema_filter, use_mock)

    # Simple filtering for demo
    filtered_tables = [
        t for t in tables if query.lower() in t.name.lower() or query.lower() in (t.remarks or "").lower()
    ]
    filtered_columns = [
        c for c in columns if query.lower() in c.name.lower() or query.lower() in (c.remarks or "").lower()
    ]

    # Take top N results
    top_tables = filtered_tables[:limit]
    top_columns = filtered_columns[:limit]

    if output_format == "json":
        result = {
            "query": query,
            "tables": [{"schema": t.schema, "name": t.name, "remarks": t.remarks} for t in top_tables],
            "columns": [
                {"schema": c.schema, "table": c.table, "name": c.name, "typename": c.typename, "remarks": c.remarks}
                for c in top_columns
            ],
        }
        print(json.dumps(result, indent=2))
    elif output_format == "table":
        print(f"Tables matching '{query}':")
        print("-" * 80)
        for table in top_tables:
            print(f"{table.schema}.{table.name:<30} {table.remarks or '(no description)'}")

        print(f"\nColumns matching '{query}':")
        print("-" * 80)
        for col in top_columns:
            print(f"{col.schema}.{col.table}.{col.name:<40} [{col.typename}] {col.remarks or '(no description)'}")
    elif output_format == "csv":
        print("type,schema,table,column,typename,remarks")
        for table in top_tables:
            remarks = (table.remarks or "").replace('"', '""')
            print(f'table,"{table.schema}","{table.name}","","","{remarks}"')
        for col in top_columns:
            remarks = (col.remarks or "").replace('"', '""')
            print(f'column,"{col.schema}","{col.table}","{col.name}","{col.typename}","{remarks}"')


def main():
    parser = argparse.ArgumentParser(description="Interactive DB2 Schema Browser TUI")
    parser.add_argument("--schema", help="Filter by specific schema (default: DACDATA)", default="DACDATA")
    parser.add_argument("--search", "-s", help="Search query (activates one-shot mode)")
    parser.add_argument(
        "--limit", "-l", type=int, default=10, help="Limit number of results in one-shot mode (default: 10)"
    )
    parser.add_argument(
        "--format",
        choices=["table", "json", "csv"],
        default="table",
        help="Output format for one-shot mode (default: table)",
    )
    parser.add_argument("--mock", action="store_true", help="Use mock data for testing")
    parser.add_argument("--install-deps", action="store_true", help="Show required dependencies")
    parser.add_argument("--basic", action="store_true", help="Use basic mode (no Textual TUI)")
    parser.add_argument("--no-cache", action="store_true", help="Disable caching of database schema")

    args = parser.parse_args()

    if args.install_deps:
        print("This tool can use multiple TUI libraries:")
        print("- Rich (basic display): pip install rich")
        print("- Textual (full TUI with mouse/keyboard): pip install textual")
        print("\nRecommended: pip install rich textual")
        return

    # If search is provided, run in one-shot mode
    if args.search:
        if not RICH_AVAILABLE:
            print("Error: Search output requires the 'rich' library.")
            print("Please install it with: pip install rich")
            return
        search_and_output(args.search, args.schema, args.limit, args.format, args.mock)
    else:
        # Interactive mode - prefer Textual if available
        if TEXTUAL_AVAILABLE and not args.basic:
            app = DBBrowserApp(schema_filter=args.schema, use_mock=args.mock, use_cache=not args.no_cache)
            app.run()
        elif RICH_AVAILABLE:
            if not TEXTUAL_AVAILABLE:
                print("[Note: For full keyboard/mouse support, install Textual: pip install textual]")
                print()
            browser = DBBrowserTUI(schema_filter=args.schema, use_mock=args.mock)
            browser.run()
        else:
            print("Error: This tool requires either 'rich' or 'textual' library.")
            print("Please install with: pip install rich textual")
            return


if __name__ == "__main__":
    main()
