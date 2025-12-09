# Critical Bug Fix: Table Columns Key Lookup

## Issue
Table contents **still** weren't loading in mock mode despite implementing mock row generation.

## Root Cause
Dictionary key mismatch in async worker invocation (line 3343 in `qt_app.py`):

```python
# INCORRECT (tuple key)
table_columns=self.table_columns.get((schema, table), [])
```

The `table_columns` dictionary uses **string keys** in the format `"SCHEMA.TABLE"` (set on line 2394), but the async worker was trying to look it up using a **tuple key** `(schema, table)`.

This caused the worker to **always** receive an empty column list `[]`, preventing mock row generation from working correctly.

## Fix
Changed line 3343 to use string key format:

```python
# CORRECT (string key)
table_columns=self.table_columns.get(f"{schema}.{table}", [])
```

## Verification

### Before Fix
```python
table_columns = {"PUBLIC.USERS": [col1, col2]}
cols = table_columns.get(("PUBLIC", "USERS"), [])  # Returns []
```

### After Fix  
```python
table_columns = {"PUBLIC.USERS": [col1, col2]}
cols = table_columns.get("PUBLIC.USERS", [])  # Returns [col1, col2] ✅
```

## Testing
- ✅ All 3 async worker tests still pass
- ✅ Code compiles without errors
- ✅ Key lookup verification script passes

## Impact
With this fix, the async worker now correctly receives the column metadata and can generate type-aware mock row data when `query_runner()` fails in mock mode.

## File Changed
- `src/dbutils/gui/qt_app.py` line 3343: Changed tuple key to string key
