# C Extensions for Heavy Processing

## Overview

The `dbutils` package now includes optimized C extensions (via Cython) for performance-critical operations, particularly search functionality in the GUI.

## Features

### Fast Search Operations

The C extensions provide accelerated implementations for:

1. **Table Search** (`fast_search_tables`)
   - Case-insensitive substring matching
   - Word-boundary prefix matching (for underscore-separated names)
   - Relevance scoring (exact match > contains > prefix > remarks)
   - Optimized for large datasets (1000s of tables)

2. **Column Search** (`fast_search_columns`)
   - Name and type matching
   - Remarks/description search
   - Relevance scoring
   - Optimized for massive datasets (10000s of columns)

### Performance Improvements

Typical speedups (based on benchmarks):
- Table search: **1.5-2.6x faster** than pure Python
- Column search: **1.1-1.2x faster** for large result sets
- Best performance on exact/prefix matches

## Building Extensions

### Automatic Build

Extensions are automatically built when installing with pip/uv:

```bash
uv pip install -e .
```

### Manual Build

```bash
# Install build dependencies
uv pip install Cython setuptools wheel

# Build extensions in-place
uv run python setup.py build_ext --inplace

# Or use the convenience script
./build_extensions.sh
```

### Verify Installation

```bash
python -c "from dbutils.accelerated import fast_search_tables; print('✓ Extensions loaded')"
```

## Usage

### Automatic Usage in GUI

The Qt GUI (`db-browser-gui`) automatically uses C extensions when available:

```python
# In qt_app.py
try:
    from ..accelerated import fast_search_tables, fast_search_columns
    USE_FAST_OPS = True
except ImportError:
    USE_FAST_OPS = False  # Falls back to Python implementation
```

### Direct Usage

```python
from dbutils.accelerated import fast_search_tables, fast_search_columns
from dbutils.db_browser import TableInfo, ColumnInfo

# Create test data
tables = [
    TableInfo(schema="TEST", name="USERS", remarks="User data"),
    TableInfo(schema="TEST", name="ORDERS", remarks="Order records"),
]

# Search with C extensions
results = fast_search_tables(tables, "USER")
# Returns: [(TableInfo(...), score), ...]
# Results are sorted by relevance score (highest first)
```

## Architecture

### Implementation Details

- **Language**: Cython (compiles to optimized C)
- **Compiler Flags**: `-O3 -march=native` for maximum performance
- **Optimizations**:
  - Bounds checking disabled (`boundscheck=False`)
  - Negative indexing disabled (`wraparound=False`)
  - C-style division (`cdivision=True`)
  - None checks disabled where safe (`nonecheck=False`)

### File Structure

```
src/dbutils/
├── fast_ops.pyx          # Cython source code
├── fast_ops.c            # Generated C code (auto-generated)
├── accelerated.so        # Compiled extension (auto-generated)
└── gui/
    └── qt_app.py         # Uses accelerated search
```

## Fallback Behavior

The application gracefully falls back to pure Python if extensions aren't built:

1. Import attempt fails → `USE_FAST_OPS = False`
2. GUI continues using Python implementation
3. No feature loss, only performance difference

## Development

### Rebuilding After Changes

After modifying `fast_ops.pyx`:

```bash
uv run python setup.py build_ext --inplace
```

### Debugging

Generate annotated HTML showing Python/C interaction:

```python
# In setup.py, set:
annotate=True
```

Then rebuild and open `fast_ops.html` in a browser.

### Performance Testing

```bash
python benchmark_c_extensions.py
```

Sample output:
```
Query: 'USER'
  Python:     1.25 ms (2,000 results)
  C ext:      0.72 ms (2,000 results)
  Speedup: 1.7x faster
```

## Future Optimizations

Potential areas for additional C extensions:

1. **Data Transformation** - Table/column dict conversions in subprocess loader
2. **Filtering** - Schema/pattern-based filtering
3. **Sorting** - Multi-key sort operations for large datasets
4. **Caching** - Hash computation for cache keys
5. **Text Processing** - Advanced fuzzy matching algorithms

## Requirements

- **Python**: 3.13+
- **Cython**: 3.0+
- **C Compiler**: GCC or Clang
- **Build Tools**: setuptools, wheel

## Troubleshooting

### Extension Won't Build

**Issue**: `error: Microsoft Visual C++ 14.0 or greater is required`
- **Solution**: Install build tools for your platform
  - Linux: `apt install build-essential python3-dev`
  - macOS: `xcode-select --install`
  - Windows: Install Visual Studio Build Tools

### Extension Won't Import

**Issue**: `ImportError: No module named 'dbutils.accelerated'`
- **Solution**: Rebuild extensions: `uv run python setup.py build_ext --inplace`

### Performance Not Improved

**Issue**: No speedup observed
- **Check**: Verify extensions loaded (`USE_FAST_OPS = True` in logs)
- **Check**: Dataset size (benefits increase with larger datasets)
- **Check**: Query type (exact matches benefit more than fuzzy)

## License

Same as parent project (see main README.md)
