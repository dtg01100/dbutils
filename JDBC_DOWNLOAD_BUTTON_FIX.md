JDBC DOWNLOAD BUTTON FIX - CATEGORY NAME NORMALIZATION

## Problem Identified

When clicking the "Download…" button in the JDBC Provider Configuration dialog, the download would fail with an error. The issue was caused by a mismatch between the category names used in the UI and the category names expected by the download manager.

### Root Cause

1. **UI Category Names**: The provider configuration dialog uses capitalized category names from the templates:
   - "PostgreSQL", "MySQL", "SQLite", "Oracle", "SQL Server", "DB2", "H2", "MariaDB", "Custom"

2. **Download Manager Expectations**: The `jdbc_driver_manager.py` download functions expect lowercase database types:
   - "postgresql", "mysql", "sqlite", "oracle", "sqlserver", "db2", "h2", "mariadb"

3. **The Bug**: When the user clicked "Download…", the code passed the capitalized category name directly to the download manager, which couldn't find a matching driver configuration and returned `None`, causing the download to fail silently or with a cryptic error.

## Solution Implemented

### 1. Normalize Category Names in `download_jdbc_driver_gui()` (provider_config_dialog.py:614)

Added normalization to convert the UI category name to lowercase before passing to the download manager:

```python
category = self.category_input.currentText()
# Normalize category to lowercase for download manager (expects 'postgresql', 'mysql', etc.)
category_lower = category.lower() if category else ""
```

This ensures that:
- When detecting category from driver class: `category_lower = detected_category.lower()`
- When category is provided: `category_lower = category.lower()`
- The lowercase version is used in all downstream calls:
  - `find_existing_drivers(category_lower)`
  - `self.create_download_dialog(category_lower)`
  - `self.perform_jdbc_download(category_lower, version=version)`

### 2. Improve Category Detection in `handle_missing_jdbc_driver_auto_download()` (provider_config_dialog.py:1087)

Fixed the auto-download handler to detect category directly from the driver class using lowercase comparison:

```python
# Map provider driver_class to lowercase download category
category = None
if "sqlite" in provider.driver_class.lower():
    category = "sqlite"
elif "h2" in provider.driver_class.lower():
    category = "h2"
elif "postgres" in provider.driver_class.lower():
    category = "postgresql"
elif "mysql" in provider.driver_class.lower():
    category = "mysql"
elif "oracle" in provider.driver_class.lower():
    category = "oracle"
elif "sqlserver" in provider.driver_class.lower() or "mssql" in provider.driver_class.lower():
    category = "sqlserver"
elif "db2" in provider.driver_class.lower():
    category = "db2"
elif "mariadb" in provider.driver_class.lower():
    category = "mariadb"
```

This is more robust than provider name mapping and handles cases where the provider name doesn't exactly match the category.

## Files Modified

1. **src/dbutils/gui/provider_config_dialog.py**
   - Line 619: Added category normalization in `download_jdbc_driver_gui()`
   - Line 648: Set `category_lower` when detected from driver class
   - Line 677: Set `category_lower` for non-Generic categories
   - Line 671: Use `category_lower` in `find_existing_drivers()`
   - Line 703: Use `category_lower` in `create_download_dialog()`
   - Line 719: Use `category_lower` in `perform_jdbc_download()`
   - Lines 1087-1130: Improved category detection in `handle_missing_jdbc_driver_auto_download()`

## Testing

All tests pass with the fixes:
- ✅ 4 missing JDBC driver tests
- ✅ 4 auto-download workflow tests  
- ✅ 5 real JDBC integration tests
- **Total: 13/13 tests passing**

## User Experience

### Download Button Now Works

1. User opens JDBC Provider Configuration dialog
2. User selects a provider category (e.g., "SQLite")
3. User clicks "Download…" button
4. Category is normalized to lowercase internally ("sqlite")
5. Download dialog appears with correct driver information
6. Download proceeds successfully
7. Jar path is updated in provider configuration

### Auto-Download on Connection Failure

When a connection attempt fails due to missing driver:
1. Driver class is inspected (e.g., "org.sqlite.JDBC")
2. Category is detected from driver class (e.g., "sqlite")
3. Auto-download handler triggers
4. Driver downloads and installs
5. Connection retries and succeeds

## Backward Compatibility

- No breaking changes to public APIs
- Existing provider configurations continue to work
- Only internal category name normalization changed
- All existing tests pass

## Summary

The fix is simple but critical: ensure that category names are normalized to lowercase before passing to the download manager. This resolves the "download button not working" issue and ensures the auto-download feature works correctly when connections fail due to missing drivers.
