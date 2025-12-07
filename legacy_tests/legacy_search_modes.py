#!/usr/bin/env python3
"""Test the dual search mode functionality."""

import sys

sys.path.insert(0, "src")

from dbutils.db_browser import RICH_AVAILABLE

if RICH_AVAILABLE:
    print("✓ Textual TUI with dual search modes is available!")
    print("\n📋 Search Modes:")
    print("  1. Table Search (default)")
    print("     - Search by table name or description")
    print("     - Shows matching tables")
    print()
    print("  2. Column Search (press Tab to toggle)")
    print("     - Search by column name, type, or description")
    print("     - Shows tables that CONTAIN matching columns")
    print("     - Displays count of matching columns per table")
    print()
    print("🎮 Controls:")
    print("  - Tab: Toggle between Table/Column search modes")
    print("  - Type to search in current mode")
    print("  - /: Focus search box")
    print("  - Esc: Clear search")
    print("  - Arrow keys or mouse: Navigate")
    print()
    print("📝 Example searches:")
    print("  Table mode: 'customer', 'order', 'invoice'")
    print("  Column mode: 'id', 'date', 'name', 'integer'")
    print()
    print("Run: db-browser --mock")
else:
    print("✗ Textual TUI has been removed; use DBBrowserTUI or one-shot search instead.")
