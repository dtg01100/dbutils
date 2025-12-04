# Profiling Guide for dbutils Application

## Summary of Current Performance Analysis

The dbutils application currently includes:
- Custom benchmark scripts for comparing Python vs Cython implementations
- Performance testing with real database connections
- Timing measurements using `time.time()` and `time.perf_counter()`
- Caching mechanisms to improve performance
- Asynchronous operations to prevent UI blocking

## Key Performance Bottlenecks Identified

### 1. Database Operations
- **JDBC connection calls**: Each database query requires establishing a JDBC connection which might introduce overhead
- **Multiple independent queries**: Tables and columns are fetched separately when they could potentially be joined
- **Schema filtering**: Filtering large schemas may require significant data transfer and processing

### 2. Data Processing
- **String parsing**: Converting database responses to Python objects
- **String interning**: While memory-optimized, may add overhead for large datasets
- **Trie index building**: Creating search indices from large datasets

### 3. Caching
- **Cache serialization/deserialization**: Pickle and gzip operations for cache persistence
- **Cache validation**: Checking cache timestamps and validity

## Recommended Profiling Solutions

### 1. Built-in Python Profilers

#### cProfile Integration
Add a `--profile` flag to existing commands:

```python
# Example for db-browser command
import cProfile
import pstats

def profile_main():
    pr = cProfile.Profile()
    pr.enable()
    main()  # Your actual main function
    pr.disable()
    
    # Sort and save results
    stats = pstats.Stats(pr)
    stats.sort_stats('cumulative')
    stats.print_stats(20)  # Top 20 functions
    stats.dump_stats('profile_output.prof')

if __name__ == "__main__":
    if "--profile" in sys.argv:
        profile_main()
    else:
        main()
```

#### line_profiler for Detailed Analysis
First install: `pip install line_profiler`

Add `@profile` decorator to functions of interest and run:
`kernprof -l -v script.py`

### 2. Memory Profiling

#### memory_profiler Integration
```python
# Install: pip install memory_profiler
from memory_profiler import profile

@profile
def function_to_profile():
    # Function code here
    pass
```

#### Or use mprofile for command-line usage:
`mprof run script.py`
`mprof plot`

### 3. Custom Profiling Decorators

Create a profiling module in dbutils:

```python
# src/dbutils/profiling.py
import time
import functools
from typing import Any, Callable
import logging

logger = logging.getLogger(__name__)

def profile_function(func: Callable) -> Callable:
    """Decorator to profile function execution time."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        
        logger.info(f"{func.__name__} executed in {end_time - start_time:.4f}s")
        return result
    return wrapper

def profile_db_operation(func: Callable) -> Callable:
    """Decorator specifically for database operations."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        logger.info(f"Starting DB operation: {func.__name__}")
        
        result = func(*args, **kwargs)
        
        end_time = time.perf_counter()
        logger.info(f"DB operation {func.__name__} completed in {end_time - start_time:.4f}s")
        return result
    return wrapper
```

### 4. Advanced Profiling with Scalene

Scalene is excellent for Python applications that may have performance issues related to both CPU and memory:

```bash
pip install scalene
scalene your_script.py
```

### 5. Database-Specific Profiling

Since the app uses direct JDBC connections, add timing around database calls:

```python
def query_runner_with_profiling(sql: str) -> List[Dict]:
    """Profile wrapper for query_runner with timing."""
    start_time = time.perf_counter()
    result = query_runner(sql)  # Original function
    end_time = time.perf_counter()
    
    logger.info(f"Query execution time: {end_time - start_time:.4f}s")
    logger.info(f"Query returned {len(result)} rows")
    
    return result
```

## Implementation Plan

### Phase 1: Basic Profiling Integration
1. Add `--profile` command-line argument to all main utilities
2. Integrate cProfile for function-level timing
3. Add basic timing logs to database operations

### Phase 2: Detailed Analysis Tools
1. Add line_profiler decorators to key functions (query processing, search index building)
2. Add memory_profiler to identify memory bottlenecks
3. Create specialized profiling scripts for database operations

### Phase 3: Advanced Profiling
1. Integrate Scalene for comprehensive performance analysis
2. Add distributed tracing for multi-step operations
3. Create profiling reports with performance metrics

## Specific Functions to Profile

### Database Query Functions
- `catalog.get_tables()`
- `catalog.get_columns()`
- `catalog.get_primary_keys()`
- `catalog.get_foreign_keys()`
- `db_browser.query_runner()`

### Data Processing Functions
- `SearchIndex.build_index()`
- `SearchIndex.search_tables()`
- `SearchIndex.search_columns()`
- `map_db.infer_relationships()`

### Caching Functions
- `db_browser.load_from_cache()`
- `db_browser.save_to_cache()`
- Cache validation functions

## Example Implementation

Create a new profiling module at `src/dbutils/profiler.py`:

```python
"""Performance profiling utilities for dbutils."""

import cProfile
import pstats
import time
from functools import wraps
from typing import Any, Callable
import io
import sys
from pathlib import Path

_profile_enabled = False
_pr = None

def enable_profiling():
    """Enable profiling for the application."""
    global _profile_enabled, _pr
    _profile_enabled = True
    _pr = cProfile.Profile()

def disable_profiling():
    """Disable profiling."""
    global _profile_enabled
    _profile_enabled = False

def start_profiling():
    """Start the profiler."""
    if _profile_enabled and _pr:
        _pr.enable()

def stop_profiling():
    """Stop the profiler and save results."""
    if _profile_enabled and _pr:
        _pr.disable()
        
        # Create StringIO object to capture stats
        s = io.StringIO()
        ps = pstats.Stats(_pr, stream=s)
        ps.sort_stats('cumulative')
        ps.print_stats(20)  # Show top 20 functions
        
        print("Profiling Results:")
        print(s.getvalue())
        
        # Save to file as well
        output_file = Path("profile_output.prof")
        _pr.dump_stats(output_file)
        print(f"Full profile saved to {output_file}")

def profiled_function(func: Callable) -> Callable:
    """Decorator to conditionally profile a function."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if _profile_enabled and _pr:
            _pr.enable()
            try:
                result = func(*args, **kwargs)
            finally:
                _pr.disable()
        else:
            result = func(*args, **kwargs)
        return result
    return wrapper

def time_function(func: Callable) -> Callable:
    """Decorator to time function execution."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        print(f"{func.__name__} took {end - start:.4f} seconds")
        return result
    return wrapper
```

## Usage Examples

### For Command-Line Tools
Add to each main function:
```python
parser.add_argument("--profile", action="store_true", help="Enable profiling")
args = parser.parse_args()

if args.profile:
    from dbutils.profiler import enable_profiling, start_profiling, stop_profiling
    enable_profiling()
    start_profiling()

# Run your main logic here

if args.profile:
    stop_profiling()
```

### For Database Operations
```python
@profiled_function
def get_all_tables_and_columns(...) -> tuple[List[TableInfo], List[ColumnInfo]]:
    # Original function code
    pass
```

## Additional Recommendations

1. **Database Query Profiling**: Consider adding query timing to the JDBC connections for performance monitoring
2. **Caching Efficiency**: Profile cache hit/miss ratios and validate cache performance
3. **Memory Usage**: Monitor memory growth during large schema operations
4. **Concurrency**: Profile async operations to ensure they provide expected performance benefits
5. **JDBC vs External Runner**: Compare performance between JDBC provider and external query runner

This profiling infrastructure will provide detailed insights into the performance characteristics of dbutils and help identify optimization opportunities.