# Heavy Mock Data System

## Overview

The heavy mock data system provides configurable stress-testing capabilities for the DB Browser. It generates large datasets for performance and scalability testing.

## Feature Summary

| Aspect | Light Mock | Heavy Mock |
|--------|-----------|-----------|
| Schemas | 2 | 5 |
| Tables | 6 | 250 |
| Columns | ~20 | 5,000 |
| Purpose | Testing | Stress Testing |
| Use Case | Unit Tests | Performance Analysis |

## Quick Start

### Command Line
```bash
# Light mock (standard testing)
python3 run_qt_browser.py --mock

# Heavy mock (stress testing)
python3 run_qt_browser.py --heavy-mock
```

### Python API
```python
from dbutils.db_browser import get_all_tables_and_columns

# Light mock
tables, columns = get_all_tables_and_columns(use_mock=True)

# Heavy mock
tables, columns = get_all_tables_and_columns(use_mock=True, use_heavy_mock=True)

# Async variant
tables, columns = await get_all_tables_and_columns_async(
    use_mock=True, 
    use_heavy_mock=True
)
```

## Configuration

The heavy mock generators accept parameters for flexible sizing:

```python
from dbutils.db_browser import mock_get_tables_heavy, mock_get_columns_heavy

# Default: 5 schemas, 50 tables per schema
tables = mock_get_tables_heavy()

# Custom sizing
tables = mock_get_tables_heavy(num_schemas=10, tables_per_schema=100)
columns = mock_get_columns_heavy(
    num_schemas=10, 
    tables_per_schema=100, 
    columns_per_table=15
)
```

## Data Structure

### Default Configuration
- **Schemas**: 5 (SCHEMA_000 through SCHEMA_004)
- **Tables per Schema**: 50
- **Columns per Table**: 20
- **Total Tables**: 250
- **Total Columns**: 5,000

### Table Naming
```
Pattern: {TYPE}_{NUMBER}
Examples:
  - USER_0000, USER_0001, ...
  - ORDER_0000, ORDER_0001, ...
  - PRODUCT_0000, PRODUCT_0001, ...
  - CUSTOMER_0000, CUSTOMER_0001, ...
  - TRANSACTION_0000, TRANSACTION_0001, ...
```

### Column Data Types
The heavy mock includes realistic column types:

| Type | Count | Purpose |
|------|-------|---------|
| INTEGER | 20% | Numeric IDs, counts |
| VARCHAR | 40% | Text, names, descriptions |
| DATE | 15% | Date fields |
| TIMESTAMP | 15% | DateTime fields |
| DECIMAL | 10% | Monetary amounts, precise decimals |

### Column Properties
- **Length**: Type-appropriate (e.g., VARCHAR 50-255)
- **Scale**: For DECIMAL types (0-2)
- **Nullability**: Mix of nullable and non-nullable
- **Remarks**: Descriptive metadata for each column

## Integration Points

### 1. Core Functions (db_browser.py)
```python
def mock_get_tables_heavy(num_schemas: int = 5, 
                          tables_per_schema: int = 50) -> List[TableInfo]:
    """Generate heavy mock tables."""

def mock_get_columns_heavy(num_schemas: int = 5, 
                           tables_per_schema: int = 50, 
                           columns_per_table: int = 20) -> List[ColumnInfo]:
    """Generate heavy mock columns."""
```

### 2. Async API (db_browser.py)
```python
async def get_all_tables_and_columns_async(
    use_mock: bool = False, 
    use_heavy_mock: bool = False
) -> Tuple[List[TableInfo], List[ColumnInfo]]:
```

### 3. Sync API (db_browser.py)
```python
def get_all_tables_and_columns(
    use_mock: bool = False, 
    use_heavy_mock: bool = False
) -> Tuple[List[TableInfo], List[ColumnInfo]]:
```

### 4. Catalog Wrapper (catalog.py)
```python
def get_all_tables_and_columns(
    use_mock: bool = False, 
    use_heavy_mock: bool = False
) -> Tuple[List[TableInfo], List[ColumnInfo]]:
```

### 5. Qt GUI (qt_app.py)
```python
class QtDBBrowser(QMainWindow):
    def __init__(self, ..., use_heavy_mock: bool = False):
        self.use_heavy_mock = use_heavy_mock
        
class DataLoaderWorker(QRunnable):
    def load_data(self, ..., use_heavy_mock: bool = False):
        # Load data with heavy mock if requested
        tables, columns = get_all_tables_and_columns(
            use_mock=use_mock, 
            use_heavy_mock=use_heavy_mock
        )
```

### 6. CLI Entry Point (main_launcher.py & qt_app.py)
```python
def main(args=None):
    # Parse --heavy-mock flag
    # Forward to QtDBBrowser(use_heavy_mock=args.heavy_mock)
```

## Usage Examples

### Testing Search Performance
```bash
# Launch heavy mock to test search responsiveness
python3 run_qt_browser.py --heavy-mock

# Then in the GUI:
# - Test search across 250 tables
# - Verify sorting with 5000 columns
# - Check filtering performance
```

### Programmatic Testing
```python
import asyncio
from dbutils.db_browser import get_all_tables_and_columns_async

async def stress_test():
    """Test performance with heavy dataset."""
    import time
    
    start = time.time()
    tables, columns = await get_all_tables_and_columns_async(
        use_mock=True, 
        use_heavy_mock=True
    )
    elapsed = time.time() - start
    
    print(f"Loaded {len(tables)} tables in {elapsed:.2f}s")
    print(f"Loaded {len(columns)} columns in {elapsed:.2f}s")

asyncio.run(stress_test())
```

### Custom Dataset Size
```python
from dbutils.db_browser import mock_get_tables_heavy, mock_get_columns_heavy

# Smaller dataset (100 tables, 2000 columns)
tables = mock_get_tables_heavy(num_schemas=2, tables_per_schema=50)
columns = mock_get_columns_heavy(
    num_schemas=2, 
    tables_per_schema=50, 
    columns_per_table=20
)

# Larger dataset (1000 tables, 20000 columns)
tables = mock_get_tables_heavy(num_schemas=10, tables_per_schema=100)
columns = mock_get_columns_heavy(
    num_schemas=10, 
    tables_per_schema=100, 
    columns_per_table=20
)
```

## Performance Characteristics

### Generation Time
- Heavy mock generation: ~100-200ms (depending on hardware)
- Includes data structure creation and serialization

### Memory Usage
- 250 tables + 5000 columns: ~5-10MB in memory
- Scales linearly with table/column counts

### UI Responsiveness
With heavy mock enabled:
- Search: Should complete within 500ms
- Sorting: Should complete within 1s
- Filtering: Should complete within 500ms

## Verification

Run the integration test to verify heavy mock is working:

```bash
python3 test_heavy_mock_integration.py
```

Expected output:
```
✅ All integration tests passed!

The heavy mock is fully integrated:
  - Generators produce 250 tables × 5000 columns
  - CLI flag --heavy-mock is available
  - API accepts use_heavy_mock parameter
  - Both sync and async paths work
```

## Implementation Details

### Light Mock vs Heavy Mock Selection Logic

In `db_browser.py`:
```python
if use_mock:
    if use_heavy_mock:
        # Load heavy mock (250 tables, 5000 columns)
        tables = mock_get_tables_heavy(...)
        columns = mock_get_columns_heavy(...)
    else:
        # Load light mock (6 tables, ~20 columns)
        tables = mock_get_tables()
        columns = mock_get_columns()
```

This approach ensures:
1. `use_mock=True` always works (backward compatible)
2. `use_heavy_mock=True` requires `use_mock=True`
3. Both light and heavy mocks share the same data structures
4. No changes to real database loading paths

## Future Enhancements

Possible improvements:
1. **Configurable column data**: Add realistic sample data in column values
2. **Relation definitions**: Mock foreign keys and indexes
3. **Query history**: Mock recent query suggestions
4. **Performance profiling**: Built-in timing metrics for stress tests
5. **Export options**: Save mock data to SQL or CSV for external testing

## Troubleshooting

### Heavy mock not loading?
1. Verify `--heavy-mock` flag is used (not just `--mock`)
2. Check console output for `use_heavy_mock=True` message
3. Run `test_heavy_mock_integration.py` to verify API

### UI seems slow with heavy mock?
1. This is expected behavior - 5000 columns is a stress test
2. Monitor memory usage: should be <100MB
3. Consider reducing table/column counts for specific tests

### Different column count than expected?
1. Light mock: ~20 columns across 6 tables
2. Heavy mock: 5000 columns across 250 tables
3. Custom sizing can be adjusted in generator parameters

## References

- **Generator Functions**: `src/dbutils/db_browser.py` (lines 425-520)
- **API Integration**: `src/dbutils/db_browser.py` (lines 720-950)
- **GUI Integration**: `src/dbutils/gui/qt_app.py` (main, QtDBBrowser, DataLoaderWorker)
- **CLI Integration**: `src/dbutils/main_launcher.py`, `src/dbutils/gui/qt_app.py:main()`
- **Test Suite**: `test_heavy_mock_integration.py`
