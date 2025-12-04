# UI Hitch Analysis for dbutils Data Loading

## Identified Hitching Issues

### 1. Synchronous Data Processing in Textual TUI
**Location**: `src/dbutils/db_browser.py` - `load_more_tables` methods
**Issue**: When loading additional data, the processing happens in the main UI thread, potentially blocking the event loop
**Specific code**:
- `load_more_tables` method does synchronous operations
- Search result filtering happens on the main thread
- `_apply_search_update()` refreshes UI synchronously

### 2. Inefficient Search Updates During Loading
**Location**: `src/dbutils/db_browser.py` - `_load_more_for_search` and `_load_more_for_scroll`
**Issue**: When loading more data, the entire search is re-run each time, causing UI to freeze
**Specific code**:
- Lines 3013-3020: `filtered_tables = self.filter_tables(self.tables, search_query)` is called repeatedly
- This can be expensive as the table list grows

### 3. Potential Memory Issues with Large Datasets
**Location**: Both TUI and GUI applications
**Issue**: All data is loaded into memory, which can cause UI hitches during garbage collection
**Specific code**:
- Storing all tables and columns in memory
- Accumulating search results without limits

### 4. Qt GUI Pagination Delays
**Location**: `src/dbutils/gui/qt_app.py` - `_on_contents_scrolled`
**Issue**: When scrolling to load more table contents, the loading indicator doesn't appear immediately
**Specific code**:
- Line 3478: Loading indicator is only shown after other checks

## Recommended Fixes

### Fix 1: Move Data Processing to Background Worker
In the Textual application, ensure that expensive operations like `filter_tables` happen in a background thread:

```python
# Instead of running filter_tables on main thread:
filtered_tables = self.filter_tables(self.tables, search_query)

# Use a background worker:
from textual.workers import Worker
self.run_worker(
    lambda: filter_tables(self.tables, search_query),
    thread=True,
    exclusive=False
)
```

### Fix 2: Optimize Search Updates
Only re-run search on new data, not all data:

```python
# Instead of filtering all tables again, only filter the newly loaded chunk
def update_search_incrementally(self, new_tables_chunk, query):
    new_matches = []
    for table in new_tables_chunk:
        if self.is_match(table, query):  # Lightweight match check
            new_matches.append(table)
    return new_matches
```

### Fix 3: Implement Caching for Expensive Operations
Cache search results and clear only when necessary:

```python
# Add cache invalidation control
self._search_cache = {}
def invalidate_search_cache(self, query):
    if query in self._search_cache:
        del self._search_cache[query]
```

### Fix 4: Early Loading Indicators
Show loading indicators immediately upon request:

```python
# In _on_contents_scrolled, show loading indicator immediately
def _on_contents_scrolled(self, value: int):
    # Show loading indicator before checks to provide immediate feedback
    if hasattr(self, "contents_loading_container"):
        self.contents_loading_container.setVisible(True)
    # ... then do other checks
```

These changes would significantly reduce UI hitches during data loading operations.