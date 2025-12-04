# Comprehensive Profiling Plan for dbutils Application

## Overview
The dbutils application is a collection of command-line utilities for discovering and reasoning about DB2 schemas and relationships. It includes tools like `db-browser`, `db-relate`, `db-map`, etc. The application leverages direct JDBC connections via JayDeBeApi for database access.

## Profiling Objectives
1. Identify CPU-intensive operations
2. Detect memory bottlenecks and memory leaks
3. Find blocking operations that affect responsiveness
4. Analyze database query performance
5. Identify inefficient algorithms in schema processing
6. Profile startup and data loading times

## Application Components to Profile

### 1. Core Database Operations
- `dbutils.catalog` - Database query functions
- `dbutils.map_db` - Schema mapping and relationship inference
- `dbutils.utils.query_runner` - JDBC query integration
- `dbutils.db_browser.get_all_tables_and_columns` - Data loading functions

### 2. Performance-Critical Algorithms
- `dbutils.db_relate.infer_relationships` - Relationship inference logic
- `dbutils.accelerated.SearchIndex` - Search indexing and fuzzy matching
- `dbutils.utils.edit_distance` - String similarity calculations

### 3. UI Components (TUI/GUI)
- `dbutils.db_browser` - Textual TUI performance
- `dbutils.gui.qt_app` - Qt GUI performance

## Profiling Tools and Strategy

### 1. Scalene - CPU and Memory Profiling
**Purpose**: Comprehensive CPU and memory usage analysis
**Commands**:
- `scalene --profile-interval=1.0 script.py` - Continuous profiling
- `scalene --cli --profile-interval=1.0 -o scalene_profile.json script.py` - Output to JSON

### 2. py-spy - Non-intrusive Sampling Profiler
**Purpose**: Detect blocking operations without modifying code
**Commands**:
- `py-spy record -o profile.svg --pid <pid>` - Record profiling data
- `py-spy top --pid <pid>` - Real-time profiling view

### 3. line-profiler - Detailed Line-by-Line Analysis
**Purpose**: Identify specific slow lines in critical functions
**Approach**: Add `@profile` decorator to target functions

### 4. memory-profiler - Memory Usage Analysis
**Purpose**: Track memory allocation and identify memory leaks
**Commands**: `python -m memory_profiler script.py`

## Specific Profiling Scenarios

### 1. Schema Loading Performance
```bash
# Profile data loading from database
source .venv/bin/activate
scalene --cli --profile-interval=1.0 -o schema_load_profile.json -m dbutils.map_db --mock
```

### 2. Search Performance in TUI
```bash
# Profile search operations
scalene --cli --profile-interval=0.5 -o search_profile.json -c 'from dbutils.db_browser import get_all_tables_and_columns; get_all_tables_and_columns(use_mock=True)'
```

### 3. Relationship Inference Performance
```bash
# Profile relationship inference
scalene --cli --profile-interval=1.0 -o relationship_profile.json -m dbutils.db_relate --mock "TEST.TABLE1.COL1" "TEST.TABLE2.COL2"
```

### 4. GUI Application Performance
```bash
# Profile the Qt application (with mock data to avoid DB dependencies)
scalene --cli --profile-interval=1.0 -o gui_profile.json -c 'from dbutils.gui.qt_app import main; main()'
```

## Data Collection Strategy

### 1. Baseline Performance
- Profile all tools with `--mock` data first
- Document current performance metrics
- Establish baseline for comparison

### 2. Real Data Performance (if available)
- Profile with real database connections
- Compare performance between different schema sizes
- Identify scaling issues

### 3. Memory Growth Analysis
- Monitor memory usage over time
- Check for memory leaks during extended usage
- Profile garbage collection efficiency

## Performance Metrics to Track

### 1. CPU Usage
- Function-level CPU time
- Hotspot identification
- Algorithm efficiency

### 2. Memory Usage
- Memory allocation patterns
- Peak memory consumption
- Memory leak detection

### 3. Responsiveness
- Database query times
- UI update performance
- Search operation latency

### 4. I/O Operations
- External subprocess call overhead
- File I/O efficiency
- Network/database call performance

## Implementation Timeline

### Phase 1: Baseline Profiling (Day 1)
1. Profile all major utilities with mock data
2. Identify immediate performance bottlenecks
3. Document baseline metrics

### Phase 2: Detailed Analysis (Day 2)
1. Use line-profiler on identified hotspots
2. Perform deep memory analysis
3. Use py-spy for blocking operation detection

### Phase 3: Optimization (Day 3)
1. Apply fixes to identified bottlenecks
2. Profile improvements
3. Validate performance gains

## Expected Performance Issues

Based on code analysis, likely bottlenecks include:
1. String operations in search and matching algorithms
2. Database query subprocess overhead
3. Large schema processing inefficiencies
4. Memory allocation in data structures
5. Inefficient relationship inference algorithms

## Deliverables
1. Complete profiling reports for all major components
2. Identified performance bottlenecks with root cause analysis
3. Optimized code with measurable performance improvements
4. Updated benchmark tests to track future performance