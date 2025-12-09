# SQLite Support for Qt Browser

## Overview

The Qt Browser now supports SQLite databases in addition to DB2/AS400 databases and mock data. This allows testing and demonstration of the browser with local SQLite databases.

## Implementation

### Features Added

1. **Command-line argument**: `--db-file` to specify an SQLite database file
2. **SQLite data loading**: Modified `get_all_tables_and_columns()` to query SQLite system tables
3. **Table contents viewing**: Updated `TableContentsWorker` to query SQLite tables
4. **Pagination support**: SQLite queries support LIMIT/OFFSET for efficient loading

### Files Modified

- `src/dbutils/gui/qt_app.py`
  - Added `--db-file` argument to argument parser
  - Added `db_file` parameter to `QtDBBrowser.__init__()`
  - Updated `DataLoaderWorker.load_data()` to pass `db_file`
  - Updated `TableContentsWorker.perform_fetch()` to handle SQLite queries
  - Updated `_start_contents_fetch()` to pass `db_file` to worker

- `src/dbutils/db_browser.py`
  - Added `db_file` parameter to `get_all_tables_and_columns()`
  - Added `db_file` parameter to `get_all_tables_and_columns_async()`
  - Added `db_file` parameter to `_get_all_tables_and_columns_sync()`
  - Implemented SQLite metadata querying using `sqlite_master` and `PRAGMA table_info()`

### Test Files Created

- `test_qt_with_sqlite.py` - Creates a sample SQLite database and launches the Qt browser
- `verify_sqlite_integration.py` - Verifies SQLite loading without launching the GUI

## Usage

### Launch Qt Browser with SQLite Database

```bash
python3 ./run_qt_browser.py --db-file /path/to/database.db
```

### Create and Test with Sample Database

```bash
# Create sample database and launch browser
python3 ./test_qt_with_sqlite.py

# Verify integration without GUI
python3 ./verify_sqlite_integration.py
```

## Sample Database Schema

The test database includes realistic sample data:

- **Tables**: customers, products, orders, order_items, employees
- **Views**: customer_order_summary
- **Indexes**: 4 indexes for performance
- **Data**: 10 customers, 12 products, 8 orders, 15 order items, 7 employees

## Technical Details

### SQLite Metadata Queries

**Tables and Views:**
```sql
SELECT name, type 
FROM sqlite_master 
WHERE type IN ('table', 'view')
AND name NOT LIKE 'sqlite_%'
ORDER BY name
```

**Column Information:**
```sql
PRAGMA table_info(table_name)
```

### Table Contents

**Data Query:**
```sql
SELECT * FROM table_name LIMIT {limit} OFFSET {offset}
```

### Schema Mapping

Since SQLite doesn't have schemas like DB2, we use:
- Schema name: `'main'` for all tables
- Table type stored in `remarks` field: "SQLite table" or "SQLite view"

## Testing Results

✓ Successfully loads 6 tables (5 tables + 1 view)
✓ Successfully loads 39 columns across all tables
✓ Pagination works correctly (LIMIT/OFFSET)
✓ Table contents display properly
✓ Column metadata (type, nullable, primary key) captured correctly

## Compatibility

The implementation maintains backward compatibility:
- Existing DB2/AS400 database support unchanged
- Mock data generation unchanged
- No dependencies on SQLite when using other database types

## Future Enhancements

Potential improvements:
- Support for attached databases (multiple schemas)
- Foreign key relationship visualization
- Index information display
- Trigger information
- View definition display
- Export/import functionality
