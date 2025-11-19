#!/usr/bin/env python3
"""
DB2 Schema Comparison Tool

Compare table schemas between different schemas or databases using query_runner.

Relies on dbutils.utils.query_runner for consistent SQL execution and parsing.
"""

import argparse
import json
from typing import Dict, List, Optional

from dbutils import catalog


def get_table_schema(table_name: str, schema: str) -> List[Dict]:
    """Get detailed schema information for a table."""
    return catalog.get_columns(schema=schema, table=table_name)


def get_table_list(schema: str) -> List[Dict]:
    """Get list of tables in a schema."""
    tables = catalog.get_tables(schema=schema)
    return [{"TABNAME": t["TABNAME"]} for t in tables]


def compare_columns(col1: Dict, col2: Dict) -> Dict:
    """Compare two columns and return differences."""
    differences = {}

    # Map catalog field names to comparison fields
    fields_to_compare = [
        ("DATA_TYPE", "DATA_TYPE"),
        ("CHARACTER_MAXIMUM_LENGTH", "LENGTH"),
        ("NUMERIC_SCALE", "SCALE"),
        ("IS_NULLABLE", "NULLS"),
        ("COLUMN_DEFAULT", "DEFAULT"),
        ("COLUMN_TEXT", "REMARKS"),
    ]

    for catalog_field, display_name in fields_to_compare:
        val1 = str(col1.get(catalog_field, ""))
        val2 = str(col2.get(catalog_field, ""))

        if val1 != val2:
            differences[display_name] = {"source": val1, "target": val2}

    return differences


def compare_tables(source_schema: str, target_schema: str, table_name: str) -> Dict:
    """Compare a single table between two schemas."""
    result = {
        "table": table_name,
        "status": "identical",
        "source_schema": source_schema,
        "target_schema": target_schema,
        "added_columns": [],
        "removed_columns": [],
        "modified_columns": [],
        "extra_info": {},
    }

    # Get schema from both sides
    try:
        source_cols = get_table_schema(table_name, source_schema)
    except Exception:
        source_cols = []

    try:
        target_cols = get_table_schema(table_name, target_schema)
    except Exception:
        target_cols = []

    # Convert to dict for easier lookup by column name
    source_col_dict = {col["COLNAME"]: col for col in source_cols}
    target_col_dict = {col["COLNAME"]: col for col in target_cols}

    # Find added columns (in target but not in source)
    for col_name in target_col_dict:
        if col_name not in source_col_dict:
            result["added_columns"].append(target_col_dict[col_name])

    # Find removed columns (in source but not in target)
    for col_name in source_col_dict:
        if col_name not in target_col_dict:
            result["removed_columns"].append(source_col_dict[col_name])

    # Find modified columns (in both but different)
    for col_name in source_col_dict:
        if col_name in target_col_dict:
            differences = compare_columns(source_col_dict[col_name], target_col_dict[col_name])
            if differences:
                result["modified_columns"].append({"column_name": col_name, "differences": differences})

    # Determine overall status
    if result["added_columns"] or result["removed_columns"] or result["modified_columns"]:
        result["status"] = "different"

    return result


def compare_schemas(source_schema: str, target_schema: str, specific_table: Optional[str] = None) -> List[Dict]:
    """Compare all tables between two schemas."""
    results = []

    if specific_table:
        # Compare just one specific table
        result = compare_tables(source_schema, target_schema, specific_table)
        results.append(result)
    else:
        # Get all tables from both schemas
        source_tables = {row["TABNAME"] for row in get_table_list(source_schema)}
        target_tables = {row["TABNAME"] for row in get_table_list(target_schema)}

        # Check all tables that exist in either schema
        all_tables = source_tables.union(target_tables)

        for table_name in sorted(all_tables):
            result = compare_tables(source_schema, target_schema, table_name)
            results.append(result)

    return results


def main():
    parser = argparse.ArgumentParser(description="Compare DB2 table schemas between schemas or databases")
    parser.add_argument("source_schema", help="Source schema name")
    parser.add_argument("target_schema", help="Target schema name")
    parser.add_argument("--table", help="Specific table to compare (optional)")
    parser.add_argument("--output", "-o", help="Output file (default: stdout)")
    parser.add_argument("--format", choices=["json", "text"], default="json", help="Output format (default: json)")

    args = parser.parse_args()

    results = compare_schemas(args.source_schema, args.target_schema, args.table)

    if args.format == "json":
        output = json.dumps(results, indent=2)
    else:  # text format
        output = format_text_output(results)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
    else:
        print(output)


def format_text_output(results: List[Dict]) -> str:
    """Format comparison results in human-readable text format."""
    output = "Schema Comparison Results\n"
    output += "=" * 50 + "\n\n"

    for result in results:
        output += f"Table: {result['table']}\n"
        output += f"Status: {result['status']}\n"

        if result["added_columns"]:
            output += f"  Added columns: {len(result['added_columns'])}\n"
            for col in result["added_columns"]:
                output += f"    + {col['COLNAME']} ({col['TYPENAME']})\n"

        if result["removed_columns"]:
            output += f"  Removed columns: {len(result['removed_columns'])}\n"
            for col in result["removed_columns"]:
                output += f"    - {col['COLNAME']} ({col['TYPENAME']})\n"

        if result["modified_columns"]:
            output += f"  Modified columns: {len(result['modified_columns'])}\n"
            for mod in result["modified_columns"]:
                output += f"    ~ {mod['column_name']}\n"
                for field, values in mod["differences"].items():
                    output += f"      {field}: {values['source']} -> {values['target']}\n"

        output += "\n"

    return output


if __name__ == "__main__":
    main()
