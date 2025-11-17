# dbutils

Utilities to discover and reason about DB2 schemas and relationships.

This repository provides a set of command-line utilities that help generate JOIN snippets, produce a JSON representation of your DB2 schema, and perform other database analysis tasks. They are intended to be run against a live DB2 instance via an external `query_runner` command that executes SQL and returns results. The tools are resilient to different DB2 catalog dialects (SYSCAT, QSYS2, SYSIBM) and to `query_runner` output formats (JSON, CSV, TSV).

IMPORTANT: These tools are designed to run against a real database. The `--mock` flags are provided for unit tests and local development only — avoid using mocks for production runs or integration tests.

## Tools

The following scripts are available as command-line tools after installation:

- `db-relate`: Resolve a path (sequence of joins) between two schema-qualified columns and print a SQL JOIN snippet.
- `db-map`: Produce a JSON map of tables, columns, and inferred relationships. Useful for AI prompts, documentation, or generating ERDs.
- `db-analyze`: Provides comprehensive analysis of table statistics and performance metrics.
- `db-browser`: Interactive terminal UI for searching and browsing DB2 tables and columns with fuzzy search, dual search modes (tables/columns), and schema filtering.
- `db-diff`: Compare table schemas between different schemas or databases.
- `db-health`: Analyze database health, performance metrics, and potential issues.
- `db-search`: Search for values across multiple tables and columns.

All commands call an external `query_runner` binary on PATH. `query_runner` may return JSON, CSV, or tab-separated (TSV) output — `dbutils` will try to parse JSON first and fall back to delimited parsing and normalization.

## DB Browser Features

The `db-browser` tool provides an interactive TUI for exploring your database schema:

- **Dual Search Modes**: Search by table name/description OR find tables containing specific columns
- **Fuzzy Search**: Uses edit distance algorithm to find matches even with typos
- **Schema Filtering**: Focus on a specific schema (defaults to DACDATA) or browse all schemas
- **Settings Menu**: Press 'S' to change schema filter on-the-fly without restarting
- **Caching**: Results are cached for 1 hour to improve performance (use `--no-cache` to disable)
- **Mouse & Keyboard**: Full support for both mouse clicks and keyboard navigation

### DB Browser Usage

```bash
# Browse DACDATA schema (default)
uvx . db-browser

# Browse a different schema
uvx . db-browser --schema QGPL

# Browse all schemas
uvx . db-browser --schema ""

# Use mock data for testing
uvx . db-browser --mock

# Disable caching
uvx . db-browser --no-cache

# One-shot search mode (no TUI)
uvx . db-browser --search "customer" --limit 20
```

### DB Browser Keyboard Shortcuts

- **/** - Focus search input
- **Tab** - Toggle between table search and column search modes
- **S** - Open settings menu to change schema
- **↑↓** or **mouse** - Navigate results
- **Esc** - Clear search
- **Q** or **Ctrl+C** - Quit


## Installation and Usage

This project is designed to be installed as a Python package.

### Running with `uvx`

The recommended way to run the tools is with `uvx`, which will handle the installation and virtual environment automatically.

From the root of the project, you can run any of the scripts like this:

```bash
uvx . <script-name> [args...]
```

For example, to run the `db-relate` script:

```bash
uvx . db-relate "SCHEMA1.TABLE1.COLUMN1" "SCHEMA2.TABLE2.COLUMN2"
```

To map your database schema:

```bash
uvx . db-map
```

### Developer / testing

For development, you can install the project in editable mode with its development dependencies.

1.  Install the project and development tools:

    ```bash
    # Using uv
    uv pip install -e .[dev]
    ```

2.  Run the unit tests:

    ```bash
    pytest -q
    ```

## Troubleshooting

- If a command fails with catalog errors, your DB2 environment likely exposes a different catalog schema. `dbutils` already tries several common catalog queries — check the output for `SQL Error` text from `query_runner` and confirm your `query_runner` works directly by running a sanity query:

  ```bash
  python -c "from dbutils.map_db import query_runner; print(query_runner('SELECT 1 AS ONE FROM SYSIBM.SYSDUMMY1'))"
  ```

- If `query_runner` returns tab-separated output (TSV), `dbutils` will detect it automatically. If your environment uses a different delimiter or encoding, wrap the SQL with a small wrapper that normalizes output to JSON or CSV.