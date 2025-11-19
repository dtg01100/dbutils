#!/usr/bin/env python3
"""
DB2 Table Analysis Tool

Provides comprehensive analysis of table statistics, performance metrics,
and recommendations for optimization.

Uses dbutils.utils.query_runner for consistent SQL execution and parsing.
"""

import argparse
import json
from typing import Dict, Optional

from dbutils import catalog


def analyze_table(table_name: str, schema: Optional[str] = None) -> Dict:
    """Analyze a specific table and return statistics."""
    full_table_name = f"{schema}.{table_name}" if schema else table_name

    analysis = {
        "table": full_table_name,
        "basic_info": {},
        "columns": [],
        "indexes": [],
        "constraints": [],
        "recommendations": [],
    }

    # Get basic table info from catalog
    table_sizes = catalog.get_table_sizes(schema=schema)
    table_info = next((t for t in table_sizes if t["TABNAME"] == table_name.upper()), None)
    if table_info:
        analysis["basic_info"] = {
            "TABNAME": table_info.get("TABNAME"),
            "TABSCHEMA": table_info.get("TABSCHEMA"),
            "CARD": table_info.get("ROWCOUNT"),
            "DATA_SIZE": table_info.get("DATA_SIZE"),
        }

    # Get columns
    columns_info = catalog.get_columns(schema=schema, table=table_name)
    analysis["columns"] = columns_info

    # Get indexes
    indexes_info = catalog.get_indexes(schema=schema, table=table_name)
    analysis["indexes"] = indexes_info

    # Get constraints (primary keys and foreign keys)
    constraints = []

    # Primary keys
    pks = catalog.get_primary_keys(schema=schema)
    table_pks = [pk for pk in pks if pk.get("TABNAME") == table_name.upper()]
    for pk in table_pks:
        constraints.append(
            {
                "CONSTNAME": pk.get("CONSTRAINT_NAME"),
                "TYPE": "PRIMARY KEY",
                "COLNAME": pk.get("COLNAME"),
            }
        )

    # Foreign keys
    fks = catalog.get_foreign_keys(schema=schema)
    table_fks = [fk for fk in fks if fk.get("TABNAME") == table_name.upper()]
    for fk in table_fks:
        constraints.append(
            {
                "CONSTNAME": fk.get("FK_NAME"),
                "TYPE": "FOREIGN KEY",
                "COLNAME": fk.get("FKCOLUMN_NAME"),
                "REFTABNAME": fk.get("PKTABLE_NAME"),
                "REFCOLNAME": fk.get("PKCOLUMN_NAME"),
            }
        )

    analysis["constraints"] = constraints

    # Recommendations
    if table_info and int(table_info.get("ROWCOUNT", 0)) > 100000:
        analysis["recommendations"].append("Consider partitioning for large table")

    if not indexes_info:
        analysis["recommendations"].append("Consider adding indexes for performance")

    # Check for potential issues in columns
    for col in columns_info:
        if col.get("IS_NULLABLE", "Y") == "N" and col.get("COLUMN_DEFAULT") is None:
            analysis["recommendations"].append(f"Column {col['COLNAME']} is NOT NULL but has no default")

    return analysis


def main():
    parser = argparse.ArgumentParser(description="Analyze DB2 table statistics and performance metrics")
    parser.add_argument("table", help="Table name (schema.table or just table)")
    parser.add_argument("--output", "-o", help="Output file (default: stdout)")
    parser.add_argument("--format", choices=["json", "text"], default="json", help="Output format (default: json)")
    args = parser.parse_args()

    # Parse schema.table format
    schema = None
    table = args.table
    if "." in args.table:
        schema, table = args.table.split(".", 1)

    analysis = analyze_table(table, schema)

    if args.format == "json":
        output = json.dumps(analysis, indent=2)
    else:  # text format
        output = format_text_output(analysis)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
    else:
        print(output)


def format_text_output(analysis: Dict) -> str:
    """Format analysis in human-readable text format."""
    output = f"Table Analysis: {analysis['table']}\n"
    output += "=" * 50 + "\n"

    # Basic info
    basic = analysis.get("basic_info", {})
    if basic:
        output += f"Row Count: {basic.get('CARD', 'Unknown')}\n"
        output += f"Average Row Size: {basic.get('AVGROWSIZE', 'Unknown')} bytes\n"
        output += f"Last Stats Update: {basic.get('STATS_TIME', 'Never')}\n"

    # Columns
    output += f"\nColumns ({len(analysis.get('columns', []))}):\n"
    for col in analysis.get("columns", []):
        output += f"  - {col['COLNAME']} ({col['TYPENAME']})"
        if col.get("LENGTH"):
            output += f"[{col['LENGTH']}]"
        if col.get("SCALE"):
            output += f"({col['SCALE']})"
        if col.get("NULLS") == "N":
            output += " NOT NULL"
        output += "\n"

    # Indexes
    output += f"\nIndexes ({len(analysis.get('indexes', []))}):\n"
    for idx in analysis.get("indexes", []):
        output += f"  - {idx['INDNAME']} ({idx['UNIQUERULE']}): {idx['COLNAMES']}\n"

    # Constraints
    output += f"\nConstraints ({len(analysis.get('constraints', []))}):\n"
    for constraint in analysis.get("constraints", []):
        output += f"  - {constraint['CONSTNAME']} ({constraint['TYPE']}): {constraint['COLNAME']}\n"

    # Recommendations
    if analysis.get("recommendations"):
        output += "\nRecommendations:\n"
        for rec in analysis["recommendations"]:
            output += f"  - {rec}\n"

    return output


if __name__ == "__main__":
    main()
