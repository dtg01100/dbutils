#!/usr/bin/env python3
"""
DB2 Table Analysis Tool

Provides comprehensive analysis of table statistics, performance metrics,
and recommendations for optimization.

Uses dbutils.utils.query_runner for consistent SQL execution and parsing.
"""

import argparse
import json
from typing import Dict, List, Optional

from dbutils.utils import query_runner


def _run_candidates(candidates: List[str]) -> List[Dict]:
    for sql in candidates:
        try:
            rows = query_runner(sql)
            if rows:
                return rows
        except Exception:
            continue
    return []


def _get_table_info(
    table_name: str,
    schema_clause_env: str,
    schema_clause_qsys: str,
    schema_clause_zos: str,
) -> List[Dict]:
    candidates = [
        f"""SELECT TABNAME, TABSCHEMA, CARD, NPAGES, Fpages, Page_split,
                   DISTINCT_LIT, AVGROWSIZE, STATS_TIME
            FROM SYSCAT.TABLES
            WHERE TABNAME = '{table_name.upper()}'{schema_clause_env}""",
        f"""SELECT TABLE_NAME AS TABNAME, TABLE_SCHEMA AS TABSCHEMA, NUMBER_OF_ROWS AS CARD,
                   NUMBER_OF_PAGES AS NPAGES, NULL AS Fpages, NULL AS Page_split,
                   NULL AS DISTINCT_LIT, AVERAGE_ROW_LENGTH AS AVGROWSIZE, NULL AS STATS_TIME
            FROM QSYS2.SYSTABLES
            WHERE TABLE_NAME = '{table_name.upper()}'{schema_clause_qsys} AND TABLE_TYPE = 'T'""",
        f"""SELECT NAME AS TABNAME, CREATOR AS TABSCHEMA, CARDF AS CARD, NULL AS NPAGES,
                   NULL AS Fpages, NULL AS Page_split, NULL AS DISTINCT_LIT,
                   AVGROWLEN AS AVGROWSIZE, NULL AS STATS_TIME
            FROM SYSIBM.SYSTABLES
            WHERE NAME = '{table_name.upper()}'{schema_clause_zos} AND TYPE = 'T'""",
    ]
    return _run_candidates(candidates)


def _get_columns_info(
    table_name: str,
    schema_clause_env: str,
    schema_clause_qsys: str,
    schema_clause_zos: str,
) -> List[Dict]:
    candidates = [
        f"""SELECT COLNAME, TYPENAME, LENGTH, SCALE, NULLS, DEFAULT, COLNO,
                   KEYSEQ, SEQUENCE_NO, REMARKS
            FROM SYSCAT.COLUMNS
            WHERE TABNAME = '{table_name.upper()}'{schema_clause_env}
            ORDER BY COLNO""",
        f"""SELECT COLUMN_NAME AS COLNAME, DATA_TYPE AS TYPENAME, NUMERIC_PRECISION AS LENGTH,
                   NUMERIC_SCALE AS SCALE, IS_NULLABLE AS NULLS, COLUMN_DEFAULT AS DEFAULT,
                   ORDINAL_POSITION AS COLNO, NULL AS KEYSEQ, NULL AS SEQUENCE_NO,
                   COLUMN_TEXT AS REMARKS
            FROM QSYS2.SYSCOLUMNS
            WHERE TABLE_NAME = '{table_name.upper()}'{schema_clause_qsys}
            ORDER BY ORDINAL_POSITION""",
        f"""SELECT NAME AS COLNAME, COLTYPE AS TYPENAME, LENGTH, SCALE, NULLS, DEFAULT,
                   COLNO, KEYSEQ, NULL AS SEQUENCE_NO, REMARKS
            FROM SYSIBM.SYSCOLUMNS
            WHERE TBNAME = '{table_name.upper()}'{schema_clause_zos}
            ORDER BY COLNO""",
    ]
    return _run_candidates(candidates)


def _get_indexes_info(
    table_name: str,
    schema_clause_env: str,
    schema_clause_qsys: str,
    schema_clause_zos: str,
) -> List[Dict]:
    candidates = [
        f"""SELECT INDNAME, COLNAMES, UNIQUERULE, INDEXTYPE, CLUSTERRULE, DISTINCTCOUNT
            FROM SYSCAT.INDEXES
            WHERE TABNAME = '{table_name.upper()}'{schema_clause_env}""",
        f"""SELECT INDEX_NAME AS INDNAME, COLUMN_NAMES AS COLNAMES, IS_UNIQUE AS UNIQUERULE,
                   INDEX_TYPE AS INDEXTYPE, NULL AS CLUSTERRULE, NULL AS DISTINCTCOUNT
            FROM QSYS2.SYSINDEXES
            WHERE TABLE_NAME = '{table_name.upper()}'{schema_clause_qsys}""",
        f"""SELECT NAME AS INDNAME, COLNAMES, UNIQUERULE, INDEXTYPE, CLUSTERRULE, DISTINCTCOUNT
            FROM SYSIBM.SYSINDEXES
            WHERE TBNAME = '{table_name.upper()}'{schema_clause_zos}""",
    ]
    return _run_candidates(candidates)


def _get_constraints_info(
    table_name: str,
    schema_clause_env: str,
    schema_clause_qsys: str,
    schema_clause_zos: str,
) -> List[Dict]:
    candidates = [
        f"""SELECT CONSTNAME, TYPE, COLNAME, REFTABNAME, REFCOLNAME
            FROM SYSCAT.KEYCOLUSE
            WHERE TABNAME = '{table_name.upper()}'{schema_clause_env}""",
        f"""SELECT CONSTRAINT_NAME AS CONSTNAME, CONSTRAINT_TYPE AS TYPE, COLUMN_NAME AS COLNAME,
                   REFERENCED_TABLE_NAME AS REFTABNAME, REFERENCED_COLUMN_NAME AS REFCOLNAME
            FROM QSYS2.SYSKEYS
            WHERE TABLE_NAME = '{table_name.upper()}'{schema_clause_qsys}""",
        f"""SELECT CONSTNAME, TYPE, COLNAME, REFTABNAME, REFCOLNAME
            FROM SYSIBM.SYSKEYS
            WHERE TBNAME = '{table_name.upper()}'{schema_clause_zos}""",
    ]
    return _run_candidates(candidates)


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

    def _run_candidates(candidates: List[str]) -> List[Dict]:
        """Execute SQL candidates in order and return the first non-empty list of rows."""
        for sql in candidates:
            try:
                rows = query_runner(sql)
                if rows:
                    return rows
            except Exception:
                continue
        return []

    schema_clause_env = f" AND TABSCHEMA = '{schema.upper()}'" if schema else ""
    schema_clause_qsys = f" AND TABLE_SCHEMA = '{schema.upper()}'" if schema else ""
    schema_clause_zos = f" AND CREATOR = '{schema.upper()}'" if schema else ""

    # Get basic table info (try different catalog schemas)
    table_info = _get_table_info(table_name, schema_clause_env, schema_clause_qsys, schema_clause_zos)
    if table_info:
        analysis["basic_info"] = table_info[0]

    # Columns
    columns_info = _get_columns_info(table_name, schema_clause_env, schema_clause_qsys, schema_clause_zos)
    analysis["columns"] = columns_info

    # Indexes
    indexes_info = _get_indexes_info(table_name, schema_clause_env, schema_clause_qsys, schema_clause_zos)
    analysis["indexes"] = indexes_info

    # Constraints
    constraints_info = _get_constraints_info(table_name, schema_clause_env, schema_clause_qsys, schema_clause_zos)
    analysis["constraints"] = constraints_info

    # Recommendations
    def _get_recommendations(
        table_info: List[Dict], indexes: List[Dict], columns: List[Dict]
    ) -> List[str]:
        recs: List[str] = []
        if table_info and table_info[0].get("CARD", 0) > 100000:
            recs.append("Consider partitioning for large table")

        if not indexes:
            recs.append("Consider adding indexes for performance")

        # Check for potential issues in columns
        for col in columns:
            if col.get("NULLS", "Y") == "N" and col.get("DEFAULT") is None:
                recs.append(f"Column {col['COLNAME']} is NOT NULL but has no default")

        return recs

    analysis["recommendations"] = _get_recommendations(table_info, indexes_info, columns_info)

    return analysis

    analysis["constraints"] = constraints_info

    # Generate recommendations
    if table_info and table_info[0].get("CARD", 0) > 100000:
        analysis["recommendations"].append("Consider partitioning for large table")

    if not indexes_info:
        analysis["recommendations"].append("Consider adding indexes for performance")
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
