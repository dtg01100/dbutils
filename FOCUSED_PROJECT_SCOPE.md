# Focus of Project: Qt GUI Database Browser with JDBC

## Core Focus: Qt GUI Database Browser Application

The primary focus should be on the Qt GUI database browser application with JDBC support. This means the core components are:

### Essential Files for GUI Database Browser
1. `src/dbutils/gui/qt_app.py` - Main Qt application with database browsing capabilities
2. `src/dbutils/jdbc_provider.py` - JDBC connection provider implementation
3. `src/dbutils/db_browser.py` - Core data loading, search, and browsing logic
4. `src/dbutils/utils.py` - Essential utilities (edit_distance, fuzzy_match, JDBC query runner)
5. `src/dbutils/catalog.py` - Database catalog query abstractions
6. `src/dbutils/main_launcher.py` - Application launcher
7. `src/dbutils/gui/provider_config.py` - JDBC provider configuration dialog
8. `src/dbutils/gui/widgets/` - Enhanced Qt widgets (if used by Qt app)

### Out-of-Scope Command-Line Tools (can be removed for focused project)
These were part of the original dbutils package but are not part of the GUI database browser focus:
1. `src/dbutils/db_relate.py` - Relationship resolution tool (command-line)
2. `src/dbutils/map_db.py` - Schema mapping tool (command-line) 
3. `src/dbutils/db_analyze.py` - Database analysis tool (command-line)
4. `src/dbutils/db_search.py` - Value search tool (command-line)
5. `src/dbutils/db_diff.py` - Schema comparison tool (command-line)
6. `src/dbutils/db_health.py` - Health analysis tool (command-line)
7. `src/dbutils/db_table_sizes.py` - Table size analysis (command-line)
8. `src/dbutils/db_indexes.py` - Index analysis (command-line)
9. `src/dbutils/db_inferred_ref_coverage.py` - Inferred relationship coverage (command-line)
10. `src/dbutils/db_inferred_orphans.py` - Inferred orphan detection (command-line)

### Project Scripts to Remove (in pyproject.toml)
- db-relate = "dbutils.db_relate:main"
- db-map = "dbutils.map_db:main"
- db-analyze = "dbutils.db_analyze:main"
- db-search = "dbutils.db_search:main"
- db-diff = "dbutils.db_diff:main"
- db-health = "dbutils.db_health:main"
- db-table-sizes = "dbutils.db_table_sizes:main"
- db-indexes = "dbutils.db_indexes:main"
- db-inferred-ref-coverage = "dbutils.db_inferred_ref_coverage:main"
- db-inferred-orphans = "dbutils.db_inferred_orphans:main"

### Project Scripts to Keep (for GUI Browser Focus)
- db-browser = "dbutils.main_launcher:main" (TUI launcher)
- db-browser-gui = "dbutils.gui.qt_app:main" (Qt GUI application)

### Key Dependencies for Focused Project
- PySide6 (Qt framework)
- JPype1 and JayDeBeApi (JDBC connectivity)
- Rich and Textual (TUI components)

### Summary
The Qt GUI Database Browser with JDBC functionality should be the core focus. The numerous command-line utilities for analysis, relationship inference, schema comparison, etc. are outside the scope of the GUI browser application and would complicate the project focus.