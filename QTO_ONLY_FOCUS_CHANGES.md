# Qt-Only Database Browser Project Focus Changes

## Summary of Changes Made

### 1. Dependencies Updated
- **Removed**: textual>=6.6.0 (Textual TUI library)
- **Kept**: rich, PySide6, JPype1, JayDeBeApi for Qt and JDBC functionality

### 2. Command-Line Utilities Removed from Entry Points
- **Removed**: All command-line tools except the Qt GUI launcher:
  - `db-relate` (relationship resolution) 
  - `db-map` (schema mapping)
  - `db-analyze` (analysis tool)
  - `db-search` (value search)
  - `db-diff` (schema diff)
  - `db-health` (health checks)
  - `db-table-sizes` (table size analysis)
  - `db-indexes` (index info)
  - `db-inferred-ref-coverage` (relationship coverage)
  - `db-inferred-orphans` (orphan detection)

- **Kept**: 
  - `db-browser` (Qt-only launcher)
  - `db-browser-gui` (Qt GUI application)

### 3. Main Launcher Updated
- **Before**: Smart launcher chose between Qt GUI, Textual TUI, or CLI based on environment
- **After**: Qt-only launcher that directly launches the Qt interface
- **Removed**: Textual TUI detection and launching code
- **Removed**: CLI interface functionality

### 4. Core Focus Maintained
The core functionality remains for the Qt database browser:
- JDBC connectivity via JayDeBeApi and JPype1
- Qt GUI with PySide6
- Database schema browsing and search
- Streaming search results
- Performance optimizations

### 5. File Structure
- `src/dbutils/gui/qt_app.py` - Main Qt application (retained)
- `src/dbutils/jdbc_provider.py` - JDBC integration (retained) 
- `src/dbutils/db_browser.py` - Backend functionality for Qt app (core functions retained)
- `src/dbutils/utils.py` - Utilities for Qt app (retained)
- `src/dbutils/catalog.py` - Database catalog queries (retained)

### 6. Project Scope Clarification
**Focus**: Qt GUI database browser with JDBC connectivity
**Not Included**: Command-line analysis tools, Textual TUI, multiple interface options

The project now focuses exclusively on the Qt GUI database browser application with JDBC connectivity, eliminating all TUI and command-line utilities that were outside the core scope.