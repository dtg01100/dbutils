# DB Browser TUI - Enhanced Features

## Overview
The DB Browser now includes a fully interactive TUI (Terminal User Interface) with comprehensive keyboard and mouse support using Textual.

## Features

### 🖱️ Mouse Support
- **Click on tables** to view their columns instantly
- **Hover over tables** to preview columns
- **Click on the search box** to focus it
- **Scroll** through long lists with mouse wheel
- **Click anywhere** to navigate the interface

### ⌨️ Keyboard Support
- **Arrow Keys (↑↓)**: Navigate through tables and columns
- **Type anywhere**: Search is automatically updated in real-time
- **`/`**: Focus the search input
- **`Esc`**: Clear the current search
- **`Tab`**: Move between widgets
- **`q` or `Ctrl+C`**: Quit the application
- **`F1`**: Show help (hidden in footer, accessible)

### 🔍 Real-time Search
- Type to filter tables and columns instantly
- Search matches:
  - Table names
  - Schema names
  - Column names
  - Data types
  - Descriptions/remarks

### 📊 UI Layout
```
┌─ DB Browser ───────────────────────────────────────┐
│ Search: [type to filter...                      ] │
├────────────────────┬────────────────────────────────┤
│ Tables (X)         │ Columns in SCHEMA.TABLE (Y)   │
│                    │                                │
│ SCHEMA.TABLE1      │ COLUMN1    TYPE    N  Desc     │
│ SCHEMA.TABLE2  ←   │ COLUMN2    TYPE    Y  Desc     │
│ SCHEMA.TABLE3      │ COLUMN3    TYPE    N  Desc     │
│                    │                                │
└────────────────────┴────────────────────────────────┘
```

## Usage

### Interactive Mode (Recommended)
```bash
# Launch with Textual TUI (full keyboard/mouse support)
db-browser --mock

# Filter by schema
db-browser --schema MYSCHEMA

# Use basic mode (fallback, no Textual)
db-browser --basic --mock
```

### One-shot Search Mode
```bash
# Search and output results
db-browser --search "customer" --format table

# JSON output
db-browser --search "user" --format json --limit 20

# CSV output for piping
db-browser --search "order" --format csv
```

## Installation

### Full Features (Recommended)
```bash
pip install rich textual
```

### Minimal (basic mode only)
```bash
pip install rich
```

## Development

The TUI is implemented using:
- **Textual**: Advanced TUI framework with mouse support
- **Rich**: Terminal formatting and basic display
- **DataTable**: Efficient table rendering with cursor navigation

### Architecture
- `DBBrowserApp`: Textual-based interactive app (preferred)
- `DBBrowserTUI`: Rich-based fallback for basic terminals
- Automatic fallback if Textual is not installed

## Tips
1. Start typing to search - no need to click the search box
2. Use arrow keys or mouse to navigate tables
3. Columns update automatically when you select a table
4. Press `/` to jump to search from anywhere
5. Press `Esc` to clear and start a new search

## Testing
```bash
# Run with mock data
db-browser --mock

# Check available features
python test_tui.py
```
