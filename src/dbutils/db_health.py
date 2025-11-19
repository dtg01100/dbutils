#!/usr/bin/env python3
"""
DB2 Database Health Check Tool

Analyze database health, performance metrics, and potential issues.

Uses dbutils.catalog for IBM i system catalog queries.
"""

import argparse
import json
from typing import Dict

from dbutils import catalog
from dbutils.utils import query_runner


def check_database_health() -> Dict:
    """Check overall database health."""
    health_report = {
        "timestamp": "",
        "summary": {},
        "tables": [],
        "indexes": [],
        "performance_metrics": {},
        "warnings": [],
        "recommendations": [],
    }

    # Get basic database info
    try:
        db_info = query_runner(
            "SELECT SERVICE_LEVEL, FIXPACK_NUM, DB_NAME FROM TABLE(SYSPROC.ENV_GET_INST_INFO()) AS T"
        )
        if db_info:
            health_report["summary"]["db_version"] = (
                f"{db_info[0].get('SERVICE_LEVEL', 'Unknown')}.{db_info[0].get('FIXPACK_NUM', 'Unknown')}"
            )
            health_report["summary"]["db_name"] = db_info[0].get("DB_NAME", "Unknown")
    except Exception:
        health_report["warnings"].append("Could not retrieve database version info")

    # Get table count and stats using catalog
    try:
        tables = catalog.get_tables()
        table_sizes = catalog.get_table_sizes()
        health_report["summary"]["table_count"] = len(tables)
        health_report["summary"]["total_rows"] = sum(int(t.get("ROWCOUNT", 0)) for t in table_sizes)
    except Exception:
        health_report["warnings"].append("Could not retrieve table statistics")

    # Find tables without statistics
    try:
        # Note: IBM i doesn't have STATS_TIME like LUW, using basic table info
        tables = catalog.get_tables()
        table_sizes = catalog.get_table_sizes()

        # Build dict for quick lookup
        size_dict = {f"{t.get('TABSCHEMA')}.{t.get('TABNAME')}": t for t in table_sizes}

        stale_stats = []
        for table in tables:
            key = f"{table.get('TABSCHEMA')}.{table.get('TABNAME')}"
            size_info = size_dict.get(key)
            if size_info is None:
                stale_stats.append({"TABSCHEMA": table.get("TABSCHEMA"), "TABNAME": table.get("TABNAME"), "CARD": 0})

        health_report["tables"] = stale_stats

        if len(stale_stats) > 10:  # If more than 10 tables with stale stats
            health_report["warnings"].append(f"{len(stale_stats)} tables have stale or missing statistics")
            health_report["recommendations"].append("Run RUNSTATS on tables with stale statistics")
    except Exception:
        health_report["warnings"].append("Could not check table statistics freshness")

    # Check for fragmented indexes
    try:
        # Note: IBM i indexes don't have NLEAF/NLEVELS like LUW
        # Using basic index info instead
        all_indexes = catalog.get_indexes()

        # For IBM i, we can't easily detect fragmentation, so skip this check
        fragmented_indexes = []
        health_report["indexes"] = fragmented_indexes

        if fragmented_indexes:
            health_report["warnings"].append(f"{len(fragmented_indexes)} potentially fragmented indexes found")
            health_report["recommendations"].append("Consider rebuilding fragmented indexes")
    except Exception:
        health_report["warnings"].append("Could not check index fragmentation")

    # Check for long-running transactions
    try:
        # Note: IBM i doesn't have SYSPROC.SNAP_GET_APPL_INFO like LUW
        # This check is not applicable to IBM i
        long_tx = []
        if long_tx:
            health_report["warnings"].append(f"{len(long_tx)} potentially long-running transactions found")
            health_report["recommendations"].append("Investigate long-running transactions")
    except Exception:
        health_report["warnings"].append("Could not check for long-running transactions")

    # Check database size and utilization
    try:
        table_sizes = catalog.get_table_sizes()

        total_size_kb = sum(int(t.get("DATA_SIZE", 0)) for t in table_sizes)
        avg_card = sum(int(t.get("ROWCOUNT", 0)) for t in table_sizes) / len(table_sizes) if table_sizes else 0

        health_report["performance_metrics"]["total_db_size_kb"] = total_size_kb
        health_report["performance_metrics"]["avg_table_cardinality"] = avg_card
    except Exception:
        health_report["warnings"].append("Could not retrieve database size information")

    # Overall health assessment
    warning_count = len(health_report["warnings"])
    if warning_count == 0:
        health_report["summary"]["health_status"] = "GOOD"
    elif warning_count <= 2:
        health_report["summary"]["health_status"] = "FAIR"
    else:
        health_report["summary"]["health_status"] = "POOR"

    return health_report


def check_schema_health(schema_name: str) -> Dict:
    """Check health of a specific schema."""
    schema_report = {
        "schema": schema_name,
        "tables": [],
        "unreferenced_tables": [],
        "orphaned_indexes": [],
        "warnings": [],
        "recommendations": [],
    }

    # Get all tables in schema
    try:
        schema_tables = catalog.get_tables(schema=schema_name.upper())
        table_names = [t["TABNAME"] for t in schema_tables]

        for table_name in table_names:
            table_data = {"table_name": table_name, "row_count": 0, "columns": 0, "indexes": 0, "last_stats": None}

            # Get table size info
            table_sizes = catalog.get_table_sizes(schema=schema_name.upper())
            size_info = next((t for t in table_sizes if t["TABNAME"] == table_name.upper()), None)

            if size_info:
                table_data["row_count"] = int(size_info.get("ROWCOUNT", 0))

            # Get columns
            columns = catalog.get_columns(schema=schema_name.upper(), table=table_name.upper())
            table_data["columns"] = len(columns)

            # Get index count
            indexes = catalog.get_indexes(schema=schema_name.upper(), table=table_name.upper())
            table_data["indexes"] = len(indexes)

            schema_report["tables"].append(table_data)

            # Check for issues
            if table_data["row_count"] == 0:
                schema_report["warnings"].append(f"Table {table_name} has 0 rows (might be unused)")
            elif table_data["row_count"] > 1000000:
                schema_report["recommendations"].append(
                    f"Table {table_name} has {table_data['row_count']} rows, consider partitioning"
                )

            if table_data["last_stats"] is None:
                schema_report["warnings"].append(f"Table {table_name} has no statistics")

    except Exception as e:
        schema_report["warnings"].append(f"Could not analyze schema {schema_name}: {str(e)}")

    return schema_report


def main():
    parser = argparse.ArgumentParser(description="Check DB2 database health and performance metrics")
    parser.add_argument("--schema", help="Specific schema to check (optional - default: entire database)")
    parser.add_argument("--output", "-o", help="Output file (default: stdout)")
    parser.add_argument("--format", choices=["json", "text"], default="json", help="Output format (default: json)")

    args = parser.parse_args()

    if args.schema:
        results = check_schema_health(args.schema)
    else:
        results = check_database_health()

    if args.format == "json":
        output = json.dumps(results, indent=2)
    else:  # text format
        output = format_text_output(results, args.schema is not None)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
    else:
        print(output)


def format_text_output(results: Dict, is_schema_check: bool) -> str:
    """Format health check results in human-readable text format."""
    if is_schema_check:
        output = f"Schema Health Report: {results['schema']}\n"
        output += "=" * 50 + "\n\n"

        output += f"Tables analyzed: {len(results.get('tables', []))}\n\n"

        for table in results.get("tables", []):
            output += f"Table: {table['table_name']}\n"
            output += f"  Rows: {table['row_count']}\n"
            output += f"  Columns: {table['columns']}\n"
            output += f"  Indexes: {table['indexes']}\n"
            output += f"  Last stats: {table['last_stats'] or 'Never'}\n\n"
    else:
        output = "Database Health Report\n"
        output += "=" * 50 + "\n\n"

        summary = results.get("summary", {})
        output += f"Health Status: {summary.get('health_status', 'Unknown')}\n"
        output += f"DB Version: {summary.get('db_version', 'Unknown')}\n"
        output += f"DB Name: {summary.get('db_name', 'Unknown')}\n"
        output += f"Table Count: {summary.get('table_count', 'Unknown')}\n"
        output += f"Total Rows: {summary.get('total_rows', 'Unknown')}\n\n"

        metrics = results.get("performance_metrics", {})
        if metrics:
            output += "Performance Metrics:\n"
            for key, value in metrics.items():
                output += f"  {key}: {value}\n"
            output += "\n"

        warnings = results.get("warnings", [])
        if warnings:
            output += f"Warnings ({len(warnings)}):\n"
            for warning in warnings:
                output += f"  - {warning}\n\n"

        recommendations = results.get("recommendations", [])
        if recommendations:
            output += f"Recommendations ({len(recommendations)}):\n"
            for rec in recommendations:
                output += f"  - {rec}\n\n"

        tables = results.get("tables", [])
        if tables:
            output += f"Tables with stale stats ({len(tables)} examples):\n"
            for table in tables[:5]:  # Show first 5
                output += f"  - {table.get('TABSCHEMA', '')}.{table.get('TABNAME', '')} ({table.get('CARD', 0)} rows)\n"
            if len(tables) > 5:
                output += f"  ... and {len(tables) - 5} more\n\n"

    return output


if __name__ == "__main__":
    main()
