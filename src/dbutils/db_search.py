#!/usr/bin/env python3
"""
DB2 Data Search Tool

Search for values across multiple tables and columns in a DB2 database.

Uses shared utilities from dbutils.utils for consistent SQL execution and parsing.
"""

import argparse
import csv
import json
from typing import Dict, List, Optional

from dbutils import catalog
from dbutils.utils import query_runner


def get_tables(schema: Optional[str] = None) -> List[Dict]:
    """Get list of tables in the database."""
    return catalog.get_tables(schema=schema)


def get_columns(table_name: str, schema: str) -> List[Dict]:
    """Get columns for a specific table."""
    columns = catalog.get_columns(schema=schema, table=table_name)
    
    # Filter for searchable types
    searchable_types = ['VARCHAR', 'CHAR', 'CLOB', 'INTEGER', 'BIGINT', 'DECIMAL', 
                        'NUMERIC', 'DOUBLE', 'REAL', 'DATE', 'TIME', 'TIMESTAMP']
    
    filtered = [c for c in columns if c.get("DATA_TYPE") in searchable_types]
    
    # Normalize to expected format
    normalized = []
    for col in filtered:
        normalized.append({
            "COLNAME": col.get("COLNAME"),
            "TYPENAME": col.get("DATA_TYPE")
        })
    
    return normalized


def search_in_table(
    table_schema: str, table_name: str, columns: List[Dict], search_term: str, max_results: int = 10
) -> List[Dict]:
    """Search for a term in a specific table."""
    results = []

    # Build WHERE clause for text search
    where_conditions = []
    for col in columns:
        col_name = col["COLNAME"]
        col_type = col["TYPENAME"]

        # Different search patterns based on column type
        if col_type in ["VARCHAR", "CHAR", "CLOB"]:
            where_conditions.append(f"UPPER(CAST({col_name} AS VARCHAR(4000))) LIKE UPPER('%{search_term}%')")
        elif col_type in ["INTEGER", "BIGINT", "DECIMAL", "NUMERIC", "DOUBLE", "REAL"]:
            try:
                # If search term is numeric, also search for it as a number
                float(search_term)  # Validate it's a number
                where_conditions.append(f"CAST({col_name} AS VARCHAR(50)) LIKE '%{search_term}%'")
            except ValueError:
                # If not numeric, just search as string
                where_conditions.append(f"CAST({col_name} AS VARCHAR(50)) LIKE '%{search_term}%'")
        elif col_type in ["DATE", "TIME", "TIMESTAMP"]:
            where_conditions.append(f"CAST({col_name} AS VARCHAR(50)) LIKE '%{search_term}%'")

    if not where_conditions:
        return results

    where_clause = " OR ".join(where_conditions)
    sql = f"""
    SELECT *, '{table_schema}' AS SEARCH_SCHEMA, '{table_name}' AS SEARCH_TABLE
    FROM {table_schema}.{table_name}
    WHERE {where_clause}
    LIMIT {max_results}
    """

    try:
        table_results = query_runner(sql)
        for result in table_results:
            # Add table info to each result
            result["TABLE_SCHEMA"] = table_schema
            result["TABLE_NAME"] = table_name
        results.extend(table_results)
    except Exception:
        # Skip tables that cause errors (e.g., permission issues)
        pass

    return results


def search_data(
    search_term: str, schema: Optional[str] = None, max_results: int = 10, max_tables: Optional[int] = None
) -> List[Dict]:
    """Search for a term across all accessible tables."""
    all_results = []

    # Get tables
    tables = get_tables(schema)

    # Limit number of tables to search if specified
    if max_tables:
        tables = tables[:max_tables]

    for table in tables:
        table_schema = table["TABSCHEMA"]
        table_name = table["TABNAME"]

        # Get columns for this table
        columns = get_columns(table_name, table_schema)

        if not columns:
            continue

        # Search in this table
        table_results = search_in_table(table_schema, table_name, columns, search_term, max_results)
        all_results.extend(table_results)

        # Stop if we've reached the max results
        if len(all_results) >= max_results:
            break

    return all_results[:max_results]


def main():
    parser = argparse.ArgumentParser(description="Search for values across DB2 tables and columns")
    parser.add_argument("search_term", help="Value to search for")
    parser.add_argument("--schema", help="Specific schema to search in (optional)")
    parser.add_argument("--max-results", type=int, default=10, help="Maximum number of results to return (default: 10)")
    parser.add_argument("--max-tables", type=int, help="Maximum number of tables to search (optional)")
    parser.add_argument("--output", "-o", help="Output file (default: stdout)")
    parser.add_argument("--format", choices=["json", "csv"], default="json", help="Output format (default: json)")

    args = parser.parse_args()

    results = search_data(
        args.search_term, schema=args.schema, max_results=args.max_results, max_tables=args.max_tables
    )

    if args.format == "json":
        output = json.dumps(results, indent=2)
    else:  # csv format
        if results:
            import io

            output_io = io.StringIO()
            fieldnames = list(results[0].keys()) if results else ["TABLE_SCHEMA", "TABLE_NAME", "SEARCH_RESULT"]
            writer = csv.DictWriter(output_io, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
            output = output_io.getvalue()
            output_io.close()
        else:
            output = "No results found\n"

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
    else:
        print(output)


if __name__ == "__main__":
    main()
