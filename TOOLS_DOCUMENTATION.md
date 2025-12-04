# DBUtils - Comprehensive Database Analysis Tools

A comprehensive suite of command-line utilities for analyzing, exploring, and understanding DB2 database schemas and relationships.

## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [Core Tools](#core-tools)
  - [db-browser](#db-browser)
  - [db-map](#db-map)
  - [db-relate](#db-relate)
  - [db-analyze](#db-analyze)
  - [db-health](#db-health)
  - [db-search](#db-search)
  - [db-table-sizes](#db-table-sizes)
  - [db-indexes](#db-indexes)
  - [db-inferred-ref-coverage](#db-inferred-ref-coverage)
  - [db-inferred-orphans](#db-inferred-orphans)
- [Catalog Module](#catalog-module)
- [Utilities](#utilities)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Performance Optimizations](#performance-optimizations)

## Overview

DBUtils provides a comprehensive set of tools for DB2 database analysis and exploration. The tools are designed to work with IBM i (DB2 for i) databases and support multiple output formats (JSON, CSV, table) for integration with other systems.

### Key Features

- **Schema Discovery**: Automatically discover tables, columns, indexes, and relationships
- **Relationship Analysis**: Infer and analyze foreign key relationships using multiple heuristics
- **Interactive Browsing**: Terminal-based UI for exploring large schemas
- **Health Monitoring**: Database health checks and performance metrics
- **Search Capabilities**: Full-text search across tables and columns
- **Export Formats**: JSON, CSV, and human-readable table formats
- **Mock Data Support**: Built-in mock data for testing and development

## Installation

### Using uvx (Recommended)

```bash
# Install the project in development mode
uv pip install -e .[dev]

# Run any tool
uvx . db-browser --help
```

### Direct Execution

```bash
# Run tools directly from source
python src/dbutils/db_browser.py --help
python src/dbutils/db_map.py --help
```

## Core Tools

### db-browser

**Interactive DB2 Schema Browser with Fuzzy Search**

The `db-browser` tool provides a powerful terminal-based user interface for exploring database schemas with advanced search capabilities.

#### Features

- **Dual Search Modes**: Search by table name/description OR find tables containing specific columns
- **Fuzzy Search**: Edit distance algorithm for typo-tolerant matching
- **Schema Filtering**: Focus on specific schemas or browse all schemas
- **Performance Optimized**: Lazy loading, caching, and result limiting for large databases
- **Mouse & Keyboard Support**: Full keyboard navigation and mouse support

#### Usage

```bash
# Browse DACDATA schema (default)
uvx . db-browser

# Browse specific schema
uvx . db-browser --schema QGPL

# Browse all schemas
uvx . db-browser --schema ""

# One-shot search mode
uvx . db-browser --search "customer" --limit 20

# Performance tuning
uvx . db-browser --initial-load-limit 50 --max-display-results 100 --search-debounce 0.1

# Use mock data for testing
uvx . db-browser --mock
```

#### Command-Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--schema SCHEMA` | Filter by specific schema | DACDATA |
| `--search SEARCH` | Search query (activates one-shot mode) | None |
| `--limit LIMIT` | Results limit in one-shot mode | 10 |
| `--format FORMAT` | Output format (table/json/csv) | table |
| `--mock` | Use mock data for testing | False |
| `--basic` | Use basic mode (no Textual TUI) | False |
| `--no-cache` | Disable caching | False |
| `--initial-load-limit N` | Initial tables to load | 100 |
| `--max-display-results N` | Maximum results to display | 200 |
| `--search-debounce F` | Search debounce delay | 0.2 |

#### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `/` | Focus search input |
| `Tab` | Toggle table/column search modes |
| `S` | Open schema selection |
| `↑↓` | Navigate results |
| `L` | Load more tables |
| `Ctrl+L` | Show all current results |
| `Esc` | Clear search |
| `Q/Ctrl+C` | Quit |

#### Performance Features

- **Lazy Loading**: Loads data in chunks to handle large schemas
- **Trie-based Search**: O(1) prefix matching for instant results
- **Multi-level Caching**: Query, search, and UI result caching
- **Result Limiting**: Prevents UI slowdown with large datasets
- **Progressive Rendering**: Shows results as they become available

---

### db-map

**Generate JSON Schema Map for AI Prompts and Documentation**

Creates a comprehensive JSON representation of your database schema including tables, columns, and inferred relationships.

#### Usage

```bash
# Map entire database
uvx . db-map

# Map specific table
uvx . db-map --table TEST.USERS

# Use mock data
uvx . db-map --mock

# Save to file
uvx . db-map --output schema.json
```

#### Output Format

```json
{
  "TEST.USERS": {
    "type": "T",
    "columns": {
      "ID": {
        "type": "INTEGER",
        "length": 10,
        "scale": 0,
        "description": "User ID"
      },
      "NAME": {
        "type": "VARCHAR",
        "length": 100,
        "scale": 0,
        "description": ""
      }
    },
    "relationships": [
      {
        "parent_table": "TEST.USERS",
        "child_column": "USER_ID",
        "parent_column": "ID"
      }
    ]
  }
}
```

---

### db-relate

**Resolve JOIN Paths Between Database Columns**

Finds and generates SQL JOIN statements to connect two database columns through foreign key relationships.

#### Features

- **Path Finding**: Uses BFS algorithm to find shortest paths between tables
- **Multiple Output Formats**: SQL JOINs, Graphviz DOT, full SELECT statements
- **Relationship Scoring**: Heuristic scoring for inferred relationships
- **Enhanced Mode**: Includes relationship confidence scores

#### Usage

```bash
# Basic JOIN generation
uvx . db-relate TEST.USERS.ID TEST.ORDERS.USER_ID

# Enhanced mode with scoring
uvx . db-relate TEST.USERS.ID TEST.ORDERS.USER_ID --enhanced --min-score 0.5

# Different output formats
uvx . db-relate TEST.USERS.ID TEST.ORDERS.USER_ID --format dot
uvx . db-relate TEST.USERS.ID TEST.ORDERS.USER_ID --format full-select

# Limit search depth
uvx . db-relate TEST.USERS.ID TEST.ORDERS.USER_ID --max-hops 3

# Raw relationships JSON
uvx . db-relate TEST.USERS.ID TEST.ORDERS.USER_ID --format relationships-json
```

#### Output Examples

**SQL Format:**
```
FROM TEST.USERS JOIN TEST.ORDERS ON TEST.USERS.ID = TEST.ORDERS.USER_ID
```

**Full SELECT Format:**
```sql
SELECT TEST.USERS.ID, TEST.ORDERS.USER_ID
FROM TEST.USERS
JOIN TEST.ORDERS ON TEST.USERS.ID = TEST.ORDERS.USER_ID
```

---

### db-analyze

**Comprehensive Table Analysis and Performance Metrics**

Provides detailed analysis of individual tables including statistics, indexes, constraints, and optimization recommendations.

#### Features

- **Table Statistics**: Row counts, data sizes, column information
- **Index Analysis**: Index coverage and performance recommendations
- **Constraint Analysis**: Primary keys and foreign key relationships
- **Optimization Recommendations**: Partitioning, indexing, and maintenance suggestions

#### Usage

```bash
# Analyze a specific table
uvx . db-analyze TEST.USERS

# Analyze table in specific schema
uvx . db-analyze DACDATA.CUSTOMERS

# Save analysis to file
uvx . db-analyze TEST.USERS --output analysis.json
```

#### Output Format

```json
{
  "table": "TEST.USERS",
  "basic_info": {
    "TABNAME": "USERS",
    "TABSCHEMA": "TEST",
    "CARD": 12345,
    "DATA_SIZE": 524288
  },
  "columns": [...],
  "indexes": [...],
  "constraints": [...],
  "recommendations": [
    "Consider partitioning for large table",
    "Column ID is NOT NULL but has no default"
  ]
}
```

---

### db-health

**Database Health Check and Performance Monitoring**

Analyzes database health, identifies performance issues, and provides maintenance recommendations.

#### Features

- **Health Assessment**: Overall database health scoring
- **Statistics Analysis**: Identifies tables with stale statistics
- **Performance Metrics**: Database size and utilization tracking
- **Maintenance Recommendations**: RUNSTATS, index rebuilding, partitioning

#### Usage

```bash
# Check entire database health
uvx . db-health

# Check specific schema
uvx . db-health --schema TEST

# Save report to file
uvx . db-health --output health_report.json
```

#### Output Format

```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "summary": {
    "health_status": "GOOD",
    "db_version": "7.4.0",
    "table_count": 150,
    "total_rows": 5000000
  },
  "performance_metrics": {
    "total_db_size_kb": 1048576,
    "avg_table_cardinality": 33333
  },
  "warnings": [
    "5 tables have stale or missing statistics"
  ],
  "recommendations": [
    "Run RUNSTATS on tables with stale statistics"
  ]
}
```

---

### db-search

**Full-Text Search Across Database Tables and Columns**

Searches for values across all accessible tables and columns in the database.

#### Features

- **Multi-Table Search**: Searches across all tables simultaneously
- **Type-Aware Search**: Different search strategies for text, numeric, and date columns
- **Configurable Limits**: Control search scope and result limits
- **Schema Filtering**: Limit search to specific schemas

#### Usage

```bash
# Search for a value
uvx . db-search "john.doe@example.com"

# Search in specific schema
uvx . db-search "customer" --schema DACDATA

# Limit results and tables
uvx . db-search "test" --max-results 50 --max-tables 10

# Export to CSV
uvx . db-search "error" --format csv --output search_results.csv
```

#### Output Format

```json
[
  {
    "TABLE_SCHEMA": "TEST",
    "TABLE_NAME": "USERS",
    "EMAIL": "john.doe@example.com",
    "NAME": "John Doe"
  }
]
```

---

### db-table-sizes

**Table Size and Row Count Analysis**

Lists approximate row counts and data sizes for database tables.

#### Usage

```bash
# List all table sizes
uvx . db-table-sizes

# Filter by schema
uvx . db-table-sizes --schema TEST

# Export to different formats
uvx . db-table-sizes --format json
uvx . db-table-sizes --format csv --output table_sizes.csv
```

#### Output Format

```
TABSCHEMA    TABNAME       ROWCOUNT    DATA_SIZE
TEST         USERS         12345       524288
TEST         ORDERS        98765       2097152
TEST         PRODUCTS      5432        131072
```

---

### db-indexes

**Index Metadata and Performance Analysis**

Lists index information including unique rules, column counts, and cardinality estimates.

#### Usage

```bash
# List all indexes
uvx . db-indexes

# Filter by schema or table
uvx . db-indexes --schema TEST
uvx . db-indexes --table ORDERS

# Export formats
uvx . db-indexes --format json
uvx . db-indexes --format csv
```

#### Output Format

```
INDEX_SCHEMA INDEX_NAME          TABSCHEMA TABNAME COLUMN_NAME    IS_UNIQUE ORDINAL_POSITION
TEST         IDX_USERS_ID        TEST      USERS   ID              Y         1
TEST         IDX_ORDERS_USER_ID  TEST      ORDERS  USER_ID         N         1
```

---

### db-inferred-ref-coverage

**Inferred Relationship Analysis with Heuristic Scoring**

Lists all inferred foreign key relationships with confidence scores based on naming conventions, data types, and column descriptions.

#### Features

- **Heuristic Scoring**: Multiple signals for relationship confidence
- **Score Filtering**: Focus on high-confidence relationships
- **Comprehensive Coverage**: Analyzes all possible relationships

#### Usage

```bash
# List all inferred relationships
uvx . db-inferred-ref-coverage

# Filter by minimum score
uvx . db-inferred-ref-coverage --min-score 0.5

# Use mock data for testing
uvx . db-inferred-ref-coverage --mock
```

#### Output Format

```
TABSCHEMA TABNAME COLNAME REFTABSCHEMA REFTABNAME REFCOLNAME SCORE
TEST      ORDERS  USER_ID TEST         USERS      ID         0.85
TEST      ORDERS  PROD_ID TEST         PRODUCTS   ID         0.75
```

---

### db-inferred-orphans

**Orphan Detection SQL Generation**

Generates SQL queries to detect orphaned records in inferred relationships.

#### Features

- **Automatic SQL Generation**: Creates LEFT JOIN queries for orphan detection
- **Score-Based Filtering**: Only generates SQL for high-confidence relationships
- **Batch Processing**: Handles multiple relationships efficiently

#### Usage

```bash
# Generate orphan detection SQL
uvx . db-inferred-orphans

# Filter by relationship score
uvx . db-inferred-orphans --min-score 0.6

# JSON output with SQL queries
uvx . db-inferred-orphans --json
```

#### Output Format

```json
[
  {
    "child_table": "TEST.ORDERS",
    "child_column": "USER_ID",
    "parent_table": "TEST.USERS",
    "parent_column": "ID",
    "score": 0.85,
    "sql": "SELECT COUNT(*) AS ORPHANS FROM TEST.ORDERS o LEFT JOIN TEST.USERS u ON o.USER_ID = u.ID WHERE o.USER_ID IS NOT NULL AND u.ID IS NULL"
  }
]
```

## Catalog Module

The `catalog` module provides low-level database metadata access functions.

### Functions

- `get_tables(schema=None)` - Get table list
- `get_columns(schema=None, table=None)` - Get column metadata
- `get_primary_keys(schema=None)` - Get primary key constraints
- `get_indexes(schema=None, table=None)` - Get index metadata
- `get_table_sizes(schema=None)` - Get table size statistics
- `get_foreign_keys(schema=None)` - Get foreign key relationships

All functions support schema filtering and mock data for testing.

## Utilities

### query_runner

Core utility for executing SQL queries via direct JDBC connections using JayDeBeApi.

- **JDBC Integration**: Direct Python-to-JDBC communication via JayDeBeApi
- **Error Handling**: Comprehensive error reporting and logging
- **Direct Processing**: No external file creation needed

## Configuration

### Environment Setup

Create a `.env` file in your project root:

```env
# Database connection settings
DB_TYPE=db2
DB_HOST=your-host
DB_PORT=446
DB_NAME=YOURDB
DB_USER=your-user
DB_PASSWORD=your-password
```

### JDBC Provider Setup

Configure JDBC providers through the GUI or by setting up providers.json. The system should be connected to your database environment via JDBC.

## Troubleshooting

### Common Issues

1. **"JDBC provider not found"**
   - Ensure DBUTILS_JDBC_PROVIDER environment variable is set
   - Check that JDBC drivers are properly configured

2. **"No tables found"**
   - Verify database connection settings
   - Check user permissions for catalog access
   - Try with `--mock` flag for testing

3. **"Catalog errors"**
   - Different DB2 environments use different catalog schemas
   - The tools try multiple common schemas automatically

4. **Performance Issues**
   - Use `--initial-load-limit` and `--max-display-results` for large databases
   - Enable caching with `--no-cache false`

### Debug Commands

```bash
# Test JDBC connection
python -c "from dbutils.db_browser import query_runner; print(query_runner('SELECT 1 AS ONE FROM SYSIBM.SYSDUMMY1'))"

# Test basic catalog query
python -c "from dbutils.catalog import get_tables; print(get_tables()[:5])"
```

## Performance Optimizations

The db-browser tool includes several performance optimizations for large databases:

### Database Level
- **Lazy Loading**: Loads data in chunks to handle large schemas
- **Query Optimization**: Uses JOINs instead of subqueries
- **Parallel Execution**: Concurrent table and column queries

### Search Level
- **Trie Indexing**: O(1) prefix matching for instant results
- **Result Caching**: Multi-level caching with smart invalidation
- **Progressive Rendering**: Shows results as they become available

### UI Level
- **Result Limiting**: Prevents UI slowdown with large datasets
- **Virtual Scrolling**: Efficient display of large result lists
- **Debounced Search**: Reduces search frequency during typing

### Memory Management
- **String Interning**: Reduces memory usage for repeated strings
- **Compressed Caching**: Efficient storage of UI render results
- **LRU Eviction**: Automatic cleanup of old cached data

These optimizations enable smooth operation with databases containing thousands of tables and millions of rows.
