import argparse
import csv
import io
import json
import logging
import os
import subprocess
import tempfile
from collections import defaultdict, deque

from . import catalog


def query_runner(sql):
    """Run a SQL statement via external query_runner.

    Attempts JSON parse first then falls back to tab-separated parsing.
    Uses lazy logging formatting for performance.
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as f:
        f.write(sql)
        temp_file = f.name

    logging.debug("Executing SQL query (first 100 chars): %s", sql[:100])

    try:
        result = subprocess.run(["query_runner", "-t", "db2", temp_file], capture_output=True, text=True, check=False)
        if result.returncode != 0:
            error_msg = f"query_runner failed: {result.stderr.strip()}"
            logging.error(error_msg)
            raise RuntimeError(error_msg)

        logging.debug("Raw query output (first 500 chars): %s", result.stdout[:500])

        # Try JSON first
        try:
            data = json.loads(result.stdout)
            logging.info(
                "Successfully parsed JSON response with %s rows",
                len(data) if isinstance(data, list) else "N/A",
            )
            return data
        except json.JSONDecodeError:
            logging.debug("JSON parsing failed, attempting tab-separated parsing")
            reader = csv.DictReader(io.StringIO(result.stdout), delimiter="\t")
            data = list(reader)
            logging.info("Successfully parsed tab-separated response with %s rows", len(data))
            return data
    except Exception as e:
        logging.exception("Error running query: %s", e)
        raise
    finally:
        try:
            os.unlink(temp_file)
        except OSError:
            pass


def mock_get_tables():
    return [
        {"TABSCHEMA": "TEST", "TABNAME": "USERS", "TYPE": "T"},
        {"TABSCHEMA": "TEST", "TABNAME": "ORDERS", "TYPE": "T"},
        {"TABSCHEMA": "TEST", "TABNAME": "PRODUCTS", "TYPE": "T"},
    ]


def mock_get_columns():
    return [
        {
            "TABSCHEMA": "TEST",
            "TABNAME": "USERS",
            "COLNAME": "ID",
            "TYPENAME": "INTEGER",
            "LENGTH": 10,
            "SCALE": 0,
            "REMARKS": "",
        },
        {
            "TABSCHEMA": "TEST",
            "TABNAME": "USERS",
            "COLNAME": "NAME",
            "TYPENAME": "VARCHAR",
            "LENGTH": 100,
            "SCALE": 0,
            "REMARKS": "",
        },
        {
            "TABSCHEMA": "TEST",
            "TABNAME": "ORDERS",
            "COLNAME": "ID",
            "TYPENAME": "INTEGER",
            "LENGTH": 10,
            "SCALE": 0,
            "REMARKS": "",
        },
        {
            "TABSCHEMA": "TEST",
            "TABNAME": "ORDERS",
            "COLNAME": "USER_ID",
            "TYPENAME": "INTEGER",
            "LENGTH": 10,
            "SCALE": 0,
            "REMARKS": "Foreign key to users table",
        },
        {
            "TABSCHEMA": "TEST",
            "TABNAME": "ORDERS",
            "COLNAME": "PRODUCT_ID",
            "TYPENAME": "INTEGER",
            "LENGTH": 10,
            "SCALE": 0,
            "REMARKS": "References products",
        },
        {
            "TABSCHEMA": "TEST",
            "TABNAME": "PRODUCTS",
            "COLNAME": "ID",
            "TYPENAME": "INTEGER",
            "LENGTH": 10,
            "SCALE": 0,
            "REMARKS": "",
        },
        {
            "TABSCHEMA": "TEST",
            "TABNAME": "PRODUCTS",
            "COLNAME": "NAME",
            "TYPENAME": "VARCHAR",
            "LENGTH": 100,
            "SCALE": 0,
            "REMARKS": "",
        },
    ]


def mock_get_primary_keys():
    return [
        {
            "TABSCHEMA": "TEST",
            "TABNAME": "USERS",
            "COLNAME": "ID",
            "TYPENAME": "INTEGER",
        },
        {
            "TABSCHEMA": "TEST",
            "TABNAME": "ORDERS",
            "COLNAME": "ID",
            "TYPENAME": "INTEGER",
        },
        {
            "TABSCHEMA": "TEST",
            "TABNAME": "PRODUCTS",
            "COLNAME": "ID",
            "TYPENAME": "INTEGER",
        },
    ]


def get_tables():
    """Get tables using IBM i catalog."""
    return catalog.get_tables()


def get_columns():
    """Get columns using IBM i catalog."""
    result = catalog.get_columns()
    # Normalize TYPENAME field name for compatibility
    for col in result:
        if "DATA_TYPE" in col and "TYPENAME" not in col:
            col["TYPENAME"] = col["DATA_TYPE"]
    return result


def get_primary_keys():
    """Get primary keys using IBM i catalog."""
    result = catalog.get_primary_keys()
    # Add TYPENAME field by looking up column data type
    if result:
        cols = catalog.get_columns()
        col_types = {(c["TABSCHEMA"], c["TABNAME"], c["COLNAME"]): c.get("DATA_TYPE", "") for c in cols}
        for pk in result:
            key = (pk["TABSCHEMA"], pk["TABNAME"], pk["COLNAME"])
            pk["TYPENAME"] = col_types.get(key, "")
    return result


def get_foreign_keys():
    """Get foreign keys using IBM i catalog."""
    return catalog.get_foreign_keys()


def mock_get_foreign_keys():
    return [
        {
            "TABSCHEMA": "TEST",
            "TABNAME": "ORDERS",
            "COLNAME": "USER_ID",
            "REFTABSCHEMA": "TEST",
            "REFTABNAME": "USERS",
            "REFCOLNAME": "ID",
        },
        {
            "TABSCHEMA": "TEST",
            "TABNAME": "ORDERS",
            "COLNAME": "PRODUCT_ID",
            "REFTABSCHEMA": "TEST",
            "REFTABNAME": "PRODUCTS",
            "REFCOLNAME": "ID",
        },
    ]


def infer_relationships(tables, columns, pks, use_mock=False):
    relationships = []
    # First, try to get actual foreign key constraints from the database
    try:
        fks = get_foreign_keys() if not use_mock else mock_get_foreign_keys()
        for fk in fks:
            relationships.append(
                {
                    "TABSCHEMA": fk["TABSCHEMA"],
                    "TABNAME": fk["TABNAME"],
                    "COLNAME": fk["COLNAME"],
                    "REFTABSCHEMA": fk["REFTABSCHEMA"],
                    "REFTABNAME": fk["REFTABNAME"],
                    "REFCOLNAME": fk["REFCOLNAME"],
                },
            )
    except Exception:
        # If we can't get actual foreign keys, fall back to inference methods
        pass

    # If no actual foreign keys were found, use inference methods
    if not relationships:
        table_dict = {f"{t['TABSCHEMA']}.{t['TABNAME']}": t for t in tables}
        for table in tables:
            table_key = f"{table['TABSCHEMA']}.{table['TABNAME']}"
            table_cols = [c for c in columns if f"{c['TABSCHEMA']}.{c['TABNAME']}" == table_key]
            for col in table_cols:
                col_name = col["COLNAME"]
                col_type = col["TYPENAME"]
                col_desc = col.get("REMARKS", "").lower()
                # Check description for references
                for other_table_key, other_table in table_dict.items():
                    if table_key != other_table_key:
                        other_table_name = other_table["TABNAME"].lower()
                        if other_table_name in col_desc and (
                            "ref" in col_desc or "foreign" in col_desc or "key" in col_desc
                        ):
                            # Find matching PK
                            matching_pks = [
                                pk
                                for pk in pks
                                if f"{pk['TABSCHEMA']}.{pk['TABNAME']}" == other_table_key
                                and pk["TYPENAME"] == col_type
                            ]
                            for pk in matching_pks:
                                relationships.append(
                                    {
                                        "TABSCHEMA": table["TABSCHEMA"],
                                        "TABNAME": table["TABNAME"],
                                        "COLNAME": col_name,
                                        "REFTABSCHEMA": pk["TABSCHEMA"],
                                        "REFTABNAME": pk["TABNAME"],
                                        "REFCOLNAME": pk["COLNAME"],
                                    },
                                )
                                break  # Only one per col
                # Fallback to naming heuristics
                for pk in pks:
                    pk_table_key = f"{pk['TABSCHEMA']}.{pk['TABNAME']}"
                    pk_col = pk["COLNAME"]
                    pk_type = pk["TYPENAME"]
                    if col_type == pk_type and table_key != pk_table_key:
                        if (
                            col_name.lower() == pk_col.lower()
                            or col_name.lower() == f"{pk['TABNAME'].lower()}_id"
                            or (col_name.lower().endswith("_id") and col_name[:-3].lower() == pk["TABNAME"].lower())
                        ):
                            relationships.append(
                                {
                                    "TABSCHEMA": table["TABSCHEMA"],
                                    "TABNAME": table["TABNAME"],
                                    "COLNAME": col_name,
                                    "REFTABSCHEMA": pk["TABSCHEMA"],
                                    "REFTABNAME": pk["TABNAME"],
                                    "REFCOLNAME": pk_col,
                                },
                            )
    return relationships


def score_relationships(relationships, columns, pks):
    """Assign heuristic scores to relationships.

    Signals used:
      - name_match: child column name patterns matching parent PK (exact or <table>_id)
      - remarks_hint: child column REMARKS referencing parent table with keywords
      - type_match: TYPENAME equality between child col and parent pk
      - parent_unique: always true for declared/inferred PK list

    Score weights chosen for simplicity. Returns list of enriched relationship dicts.
    """
    # Build quick lookup maps
    pk_types = {(pk["TABSCHEMA"], pk["TABNAME"], pk["COLNAME"]): pk.get("TYPENAME") for pk in pks}
    col_map = {}
    for c in columns:
        col_map[(c["TABSCHEMA"], c["TABNAME"], c["COLNAME"])] = c

    weighted = []
    for rel in relationships:
        child_key = (rel["TABSCHEMA"], rel["TABNAME"], rel["COLNAME"])
        parent_key = (rel["REFTABSCHEMA"], rel["REFTABNAME"], rel["REFCOLNAME"])
        child_col = col_map.get(child_key, {})
        # parent_col not needed directly; remove to satisfy linters
        parent_pk_type = pk_types.get(parent_key)
        child_type = child_col.get("TYPENAME")

        # Signals
        name_match = 0
        cc_lower = rel["COLNAME"].lower()
        parent_pk_lower = rel["REFCOLNAME"].lower()
        parent_table_lower = rel["REFTABNAME"].lower()
        if (
            cc_lower == parent_pk_lower
            or cc_lower == f"{parent_table_lower}_id"
            or (cc_lower.endswith("_id") and cc_lower[:-3] == parent_table_lower)
        ):
            name_match = 1

        remarks_hint = 0
        remarks = child_col.get("REMARKS", "") or ""
        r_lower = remarks.lower()
        if parent_table_lower in r_lower and any(k in r_lower for k in ("ref", "foreign", "key")):
            remarks_hint = 1

        type_match = 1 if (child_type and parent_pk_type and child_type == parent_pk_type) else 0
        parent_unique = 1  # given PK list

        weights = {
            "name_match": 0.35,
            "remarks_hint": 0.15,
            "type_match": 0.25,
            "parent_unique": 0.25,
        }
        score = (
            name_match * weights["name_match"]
            + remarks_hint * weights["remarks_hint"]
            + type_match * weights["type_match"]
            + parent_unique * weights["parent_unique"]
        )

        enriched = dict(rel)
        enriched["score"] = round(score, 4)
        enriched["signals"] = {
            "name_match": bool(name_match),
            "remarks_hint": bool(remarks_hint),
            "type_match": bool(type_match),
            "parent_unique": bool(parent_unique),
        }
        weighted.append(enriched)
    return weighted


def build_graph(fks):
    graph = defaultdict(dict)
    for fk in fks:
        parent_table = f"{fk['REFTABSCHEMA']}.{fk['REFTABNAME']}"
        child_table = f"{fk['TABSCHEMA']}.{fk['TABNAME']}"
        parent_col = fk["REFCOLNAME"]
        child_col = fk["COLNAME"]
        graph[child_table][parent_table] = (child_col, parent_col)
        graph[parent_table][child_table] = (parent_col, child_col)
    return graph


def find_path(graph, start_table, start_col, end_table, end_col, max_hops=None):
    # BFS to find path
    queue = deque([(start_table, [start_table], [start_col])])
    visited = set()
    while queue:
        current_table, path, cols = queue.popleft()

        # Check if we've exceeded the max hops limit
        if max_hops is not None and len(path) - 1 > max_hops:
            continue

        if current_table in visited:
            continue
        visited.add(current_table)
        if current_table == end_table and cols[-1] == end_col:
            return path, cols
        for neighbor in graph[current_table]:
            if neighbor not in visited:
                connecting_col = graph[current_table][neighbor][1]
                new_path = path + [neighbor]
                new_cols = cols + [connecting_col]
                queue.append((neighbor, new_path, new_cols))
    return None, None


def generate_sql(graph, path):
    if not path or len(path) < 2:
        return f"FROM {path[0]}" if path else ""
    sql = f"FROM {path[0]}"
    for i in range(1, len(path)):
        col_prev = graph[path[i - 1]][path[i]][0]
        col_curr = graph[path[i - 1]][path[i]][1]
        sql += f" JOIN {path[i]} ON {path[i - 1]}.{col_prev} = {path[i]}.{col_curr}"
    return sql


def generate_dot(graph, path):
    if not path:
        return ""
    dot = "digraph G {\n"
    for i, table in enumerate(path):
        dot += f'  node{i} [label="{table}"];\n'
    for i in range(len(path) - 1):
        dot += f"  node{i} -> node{i + 1};\n"
    dot += "}"
    return dot


def generate_full_select(graph, path, start_col_info=None, end_col_info=None):
    if not path:
        return ""
    # If we know the start and end columns, we can generate a more complete SELECT
    if start_col_info and end_col_info:
        start_full = f"{start_col_info['table']}.{start_col_info['column']}"
        end_full = f"{end_col_info['table']}.{end_col_info['column']}"
        select_clause = f"SELECT {start_full}, {end_full}"
    else:
        select_clause = "SELECT *"  # Fallback if specific columns aren't known

    sql = generate_sql(graph, path)
    return f"{select_clause} {sql}"


def main():
    # Set up logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    parser = argparse.ArgumentParser(description="Resolve DB2 relationships")
    parser.add_argument("start", help="Start schema.table.column")
    parser.add_argument("end", help="End schema.column")
    parser.add_argument("--mock", action="store_true", help="Use mock data for testing")
    parser.add_argument(
        "--format",
        choices=["sql", "dot", "full-select", "relationships-json"],
        default="sql",
        help=(
            "Output format: SQL JOIN snippet (default), DOT/Graphviz, full SELECT statement, "
            "or raw inferred relationships as JSON"
        ),
    )
    parser.add_argument("--max-hops", type=int, help="Maximum number of hops to search for a path")
    parser.add_argument(
        "--enhanced",
        action="store_true",
        help="Enable scoring heuristics for relationships JSON output",
    )
    parser.add_argument(
        "--min-score",
        type=float,
        default=0.0,
        help="Minimum score threshold when --enhanced is used (default: 0.0)",
    )
    args = parser.parse_args()

    logging.info("Starting relationship resolution from %s to %s", args.start, args.end)
    logging.info("Using format: %s, mock: %s", args.format, args.mock)
    if args.max_hops is not None:
        logging.info("Max hops limit: %s", args.max_hops)

    # Validate input format
    start_parts = args.start.split(".")
    end_parts = args.end.split(".")

    if len(start_parts) == 3:
        start_table = f"{start_parts[0]}.{start_parts[1]}"
        start_col = start_parts[2]
    elif len(start_parts) == 2:
        start_table = start_parts[0]
        start_col = start_parts[1]
    else:
        error_msg = f"Invalid start format: {args.start}. Expected schema.table.column or table.column"
        logging.error(error_msg)
        raise ValueError(error_msg)

    if len(end_parts) == 3:
        end_table = f"{end_parts[0]}.{end_parts[1]}"
        end_col = end_parts[2]
    elif len(end_parts) == 2:
        end_table = end_parts[0]
        end_col = end_parts[1]
    else:
        error_msg = f"Invalid end format: {args.end}. Expected schema.table.column or table.column"
        logging.error(error_msg)
        raise ValueError(error_msg)

    try:
        if args.mock:
            logging.info("Using mock data")
            tables = mock_get_tables()
            columns = mock_get_columns()
            pks = mock_get_primary_keys()
        else:
            logging.info("Fetching schema information from database")
            tables = get_tables()
            columns = get_columns()
            pks = get_primary_keys()

        logging.info("Found %s tables, %s columns, %s primary keys", len(tables), len(columns), len(pks))

        relationships = infer_relationships(tables, columns, pks, use_mock=args.mock)
        logging.info("Identified %s relationships", len(relationships))

        graph = build_graph(relationships)
        logging.info("Built graph with %s nodes", len(graph))

        logging.info("Searching for path from %s.%s to %s.%s", start_table, start_col, end_table, end_col)
        path, _cols = find_path(graph, start_table, start_col, end_table, end_col, args.max_hops)

        if args.format == "relationships-json":
            output_rels = relationships
            if args.enhanced:
                scored = score_relationships(relationships, columns, pks)
                if args.min_score > 0:
                    scored = [r for r in scored if r["score"] >= args.min_score]
                output_rels = scored
            print(json.dumps(output_rels, indent=2))
            return

        if path:
            logging.info("Found path with %s tables: %s", len(path), " -> ".join(path))
            if args.format == "sql":
                output = generate_sql(graph, path)
            elif args.format == "dot":
                output = generate_dot(graph, path)
            elif args.format == "full-select":
                # Include start and end column info for full select generation
                start_col_info = {"table": start_table, "column": start_col}
                end_col_info = {"table": end_table, "column": end_col}
                output = generate_full_select(graph, path, start_col_info, end_col_info)
            else:
                output = ""  # Should not reach here due to argparse choices
            print(output)
        else:
            logging.info("No path found")
            print("No path found")

    except Exception as e:
        logging.exception("An error occurred during processing: %s", e)
        raise


if __name__ == "__main__":
    main()
