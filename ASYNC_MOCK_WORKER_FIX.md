# Table Contents Loading Fix - Async Path Implementation

## Summary

Successfully implemented mock row data generation for the **async path** of table contents loading, ensuring the GUI displays preview data in mock mode instead of empty tables.

## Problem Identified

The GUI had two code paths for loading table row data:

1. **Sync Path** (`load_table_contents()` - direct query)
2. **Async Path** (`_start_contents_fetch()` → `TableContentsWorker`)

Both paths called `query_runner()` which requires the `DBUTILS_JDBC_PROVIDER` environment variable. In mock mode, this variable is not set, causing `query_runner()` to fail silently, resulting in empty table previews.

### Original Flow
```
Table Selected (UI)
    ↓
on_table_selected()
    ↓
load_table_contents()
    ├─ Sync: query_runner() fails → sets rows = [] (EMPTY)
    └─ Async: _start_contents_fetch()
        → TableContentsWorker.perform_fetch()
            → query_runner() fails → error_occurred signal → empty
```

## Solution Implemented

### 1. Updated TableContentsWorker Signature (Line 994)

Added two new parameters to support mock mode:

```python
def perform_fetch(
    self,
    schema: str,
    table: str,
    limit: int = 25,
    start_offset: int = 0,
    column_filter: Optional[str] = None,
    value: Optional[str] = None,
    where_clause: Optional[str] = None,
    use_mock: bool = False,              # ← NEW
    table_columns: Optional[Dict] = None, # ← NEW
):
```

### 2. Added Mock Data Generation in Worker (Lines 1090-1116)

When `query_runner()` fails and `use_mock=True`:

```python
try:
    rows = query_runner(sql) or []
except Exception as e:
    # If in mock mode, generate mock data instead of failing
    if use_mock and table_columns:
        rows = []
        for row_id in range(int(start_offset), int(start_offset) + int(limit)):
            row_data = {}
            for i, col in enumerate(table_columns):
                col_name = col.name
                # Generate mock data based on column type
                if "INT" in (col.typename or "").upper():
                    row_data[col_name] = row_id * 100 + i
                elif "DECIMAL" in (col.typename or "").upper() or "FLOAT" in (col.typename or "").upper():
                    row_data[col_name] = float(row_id) * 10.5 + float(i)
                elif "DATE" in (col.typename or "").upper():
                    # Generate dates with rotation
                    day = (row_id % 28) + 1
                    month = ((row_id // 28) % 12) + 1
                    row_data[col_name] = f"2024-{month:02d}-{day:02d}"
                else:
                    # String/default
                    row_data[col_name] = f"{table}.{col_name}.row{row_id}"
            rows.append(row_data)
    else:
        # Bubble to error emission
        self.error_occurred.emit(str(e))
        return
```

### 3. Updated Worker Invocation (Lines 3336-3345)

Pass `use_mock` and `table_columns` to worker from main UI thread:

```python
self.contents_thread.started.connect(
    lambda: self.contents_worker.perform_fetch(
        schema,
        table,
        limit=limit,
        start_offset=int(start_offset),
        column_filter=column_filter,
        value=value,
        where_clause=where_clause,
        use_mock=self.use_mock,                           # ← NEW
        table_columns=self.table_columns.get((schema, table), []), # ← NEW
    )
)
```

## Mock Data Generation Logic

The implementation generates realistic mock data based on column types:

| Column Type | Example Data |
|-------------|--------------|
| INTEGER | 0, 100, 200, 300... (row_id * 100 + col_index) |
| DECIMAL/FLOAT | 0.0, 10.5, 21.0, 31.5... |
| DATE | 2024-01-01, 2024-01-02, ... (rotating through months) |
| VARCHAR/other | "TABLE.COLUMN.row0", "TABLE.COLUMN.row1"... |

## Test Coverage

### 1. Async Worker Tests (3 new tests in `tests/test_async_mock_worker.py`)

✅ **test_async_worker_mock_mode_generates_data**
- Verifies mock data is generated when query_runner fails in mock mode
- Checks correct data types (integer, float, string, date)
- Ensures no error signal is emitted

✅ **test_async_worker_non_mock_mode_reports_error**
- Verifies non-mock mode properly reports errors
- Ensures errors bubble up correctly

✅ **test_async_worker_mock_mode_with_offset**
- Verifies pagination offset is respected
- Checks row IDs start at correct offset value

### 2. Overall Test Status

**Total Tests**: 55 ✅
- 52 existing table contents tests (all passing)
- 3 new async worker mock tests (all passing)
- **Execution Time**: ~0.6 seconds
- **Pass Rate**: 100%

## Code Changes Summary

| File | Lines | Change |
|------|-------|--------|
| `src/dbutils/gui/qt_app.py` | 994-1010 | Updated perform_fetch() signature |
| `src/dbutils/gui/qt_app.py` | 1090-1116 | Added mock data generation logic |
| `src/dbutils/gui/qt_app.py` | 3336-3345 | Pass use_mock and table_columns to worker |
| `tests/test_async_mock_worker.py` | NEW | 3 new async worker mock mode tests |

## Impact

### Before Fix
- GUI displays empty table previews in mock mode
- Async path fails silently on query_runner error
- User sees no data despite successful mock metadata loading

### After Fix
- GUI displays realistic mock row data in both sync and async paths
- Type-aware data generation provides natural-looking previews
- Pagination and offset work correctly with mock data
- Error handling preserved for non-mock mode

## Verification

To verify the fix works end-to-end:

```bash
# Run with mock mode to see table row previews
python3 run_qt_browser.py --mock

# Or heavy mock for stress testing
python3 run_qt_browser.py --heavy-mock

# Run all tests
python3 -m pytest tests/test_table_contents_loading.py tests/test_async_mock_worker.py -v
```

## Files Modified

1. **`src/dbutils/gui/qt_app.py`**
   - TableContentsWorker.perform_fetch() - Updated signature and mock data generation
   - _start_contents_fetch() - Pass use_mock and table_columns parameters

2. **`tests/test_async_mock_worker.py`** (NEW)
   - Comprehensive tests for async worker mock mode functionality

## Implementation Notes

- Mock data generation respects pagination offsets
- Data types are correctly inferred from column metadata
- No breaking changes to existing code paths
- Error handling preserved for non-mock mode
- All 55 tests pass successfully
