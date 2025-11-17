import argparse
import csv
import io
import json
import logging
import os
import subprocess
import tempfile
from collections import defaultdict, deque


def query_runner(sql):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as f:
        f.write(sql)
        temp_file = f.name

    logging.debug(f"Executing SQL query: {sql[:100]}...")  # Log first 100 chars of query

    try:
        result = subprocess.run(["query_runner", "-t", "db2", temp_file], capture_output=True, text=True)
        if result.returncode != 0:
            error_msg = f"query_runner failed: {result.stderr}"
            logging.error(error_msg)
            raise RuntimeError(error_msg)

        # Log the raw output for debugging if needed
        logging.debug(f"Raw query output: {result.stdout[:500]}...")  # First 500 chars

        # Try JSON first
        try:
            data = json.loads(result.stdout)
            logging.info(
                f"Successfully parsed JSON response with {len(data) if isinstance(data, list) else 'N/A'} rows"
            )
            return data
        except json.JSONDecodeError:
            # Assume tab-separated with header
            logging.debug("JSON parsing failed, attempting tab-separated parsing")
            reader = csv.DictReader(io.StringIO(result.stdout), delimiter="\t")
            data = list(reader)
            logging.info(f"Successfully parsed tab-separated response with {len(data)} rows")
            return data
    except Exception as e:
        logging.error(f"Error running query: {str(e)}")
        raise
    finally:
        os.unlink(temp_file)


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
    candidates = [
        # DB2 LUW
        "SELECT TABSCHEMA, TABNAME, TYPE FROM SYSCAT.TABLES WHERE TYPE = 'T'",
        # IBM i
        "SELECT TABLE_SCHEMA AS TABSCHEMA, TABLE_NAME AS TABNAME, TABLE_TYPE AS TYPE FROM QSYS2.SYSTABLES WHERE TABLE_TYPE = 'T'",
        # DB2 z/OS
        "SELECT CREATOR AS TABSCHEMA, NAME AS TABNAME, TYPE FROM SYSIBM.SYSTABLES WHERE TYPE = 'T'",
    ]

    for sql in candidates:
        try:
            result = query_runner(sql)
            if result:
                return result
        except Exception:
            continue
    return []


def get_columns():
    candidates = [
        # DB2 LUW
        "SELECT TABSCHEMA, TABNAME, COLNAME, TYPENAME, LENGTH, SCALE, REMARKS FROM SYSCAT.COLUMNS",
        # IBM i
        "SELECT TABLE_SCHEMA AS TABSCHEMA, TABLE_NAME AS TABNAME, COLUMN_NAME AS COLNAME, DATA_TYPE AS TYPENAME, NUMERIC_PRECISION AS LENGTH, NUMERIC_SCALE AS SCALE, COLUMN_TEXT AS REMARKS FROM QSYS2.SYSCOLUMNS",
        # DB2 z/OS
        "SELECT TBCREATOR AS TABSCHEMA, TBNAME AS TABNAME, NAME AS COLNAME, COLTYPE AS TYPENAME, LENGTH, SCALE, REMARKS FROM SYSIBM.SYSCOLUMNS",
    ]

    for sql in candidates:
        try:
            result = query_runner(sql)
            if result:
                return result
        except Exception:
            continue
    return []


def get_primary_keys():
    candidates = [
        # DB2 LUW
        "SELECT TABSCHEMA, TABNAME, COLNAME, TYPENAME FROM SYSCAT.COLUMNS WHERE KEYSEQ > 0",
        # IBM i - primary keys are harder, try SYSKEYS
        "SELECT TABLE_SCHEMA AS TABSCHEMA, TABLE_NAME AS TABNAME, COLUMN_NAME AS COLNAME, DATA_TYPE AS TYPENAME FROM QSYS2.SYSKEYS WHERE CONSTRAINT_TYPE = 'PRIMARY KEY'",
        # DB2 z/OS
        "SELECT TBCREATOR AS TABSCHEMA, TBNAME AS TABNAME, NAME AS COLNAME, COLTYPE AS TYPENAME FROM SYSIBM.SYSCOLUMNS WHERE KEYSEQ > 0",
    ]

    for sql in candidates:
        try:
            result = query_runner(sql)
            if result:
                return result
        except Exception:
            continue
    return []


def get_foreign_keys():
    candidates = [
        "SELECT TABSCHEMA, TABNAME, COLNAME, REFTABSCHEMA, REFTABNAME, REFCOLNAME FROM SYSCAT.FOREIGNKEYS",
        "SELECT TF.TABSCHEMA AS TABSCHEMA, TF.TABNAME AS TABNAME, TF.COLNAME AS COLNAME, TF.REFTABSCHEMA AS REFTABSCHEMA, TF.REFTABNAME AS REFTABNAME, TF.REFCOLNAME AS REFCOLNAME FROM SYSCAT.KEYCOLUSE TF JOIN SYSCAT.TABCONST TC ON TF.TABSCHEMA = TC.TABSCHEMA AND TF.TABNAME = TC.TABNAME AND TF.CONSTNAME = TC.CONSTNAME WHERE TC.TYPE = 'F'",
        "SELECT CREATOR AS TABSCHEMA, NAME AS TABNAME, COLNAME, REFTBCREATOR AS REFTABSCHEMA, REFTBNAME AS REFTABNAME, REFCOLNAME FROM SYSIBM.SYSRELS",
    ]
    for sql in candidates:
        try:
            rows = query_runner(sql)
            if rows:
                normalized = []
                for r in rows:
                    nr = {k.strip().upper(): v for k, v in r.items()}
                    mapped = {
                        "TABSCHEMA": nr.get("TABSCHEMA") or nr.get("CREATOR"),
                        "TABNAME": nr.get("TABNAME") or nr.get("NAME"),
                        "COLNAME": nr.get("COLNAME"),
                        "REFTABSCHEMA": nr.get("REFTABSCHEMA") or nr.get("REFTBCREATOR"),
                        "REFTABNAME": nr.get("REFTABNAME") or nr.get("REFTBNAME"),
                        "REFCOLNAME": nr.get("REFCOLNAME"),
                    }
                    normalized.append(mapped)
                return normalized
        except RuntimeError:
            continue
    return []


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
                }
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
                                    }
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
                                }
                            )
    return relationships


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
        choices=["sql", "dot", "full-select"],
        default="sql",
        help="Output format: SQL JOIN snippet (default), DOT/Graphviz, or full SELECT statement",
    )
    parser.add_argument("--max-hops", type=int, help="Maximum number of hops to search for a path")
    args = parser.parse_args()

    logging.info(f"Starting relationship resolution from {args.start} to {args.end}")
    logging.info(f"Using format: {args.format}, mock: {args.mock}")
    if args.max_hops is not None:
        logging.info(f"Max hops limit: {args.max_hops}")

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

        logging.info(f"Found {len(tables)} tables, {len(columns)} columns, {len(pks)} primary keys")

        relationships = infer_relationships(tables, columns, pks, use_mock=args.mock)
        logging.info(f"Identified {len(relationships)} relationships")

        graph = build_graph(relationships)
        logging.info(f"Built graph with {len(graph)} nodes")

        logging.info(f"Searching for path from {start_table}.{start_col} to {end_table}.{end_col}")
        path, cols = find_path(graph, start_table, start_col, end_table, end_col, args.max_hops)

        if path:
            logging.info(f"Found path with {len(path)} tables: {' -> '.join(path)}")
            if args.format == "sql":
                output = generate_sql(graph, path)
            elif args.format == "dot":
                output = generate_dot(graph, path)
            elif args.format == "full-select":
                # Include start and end column info for full select generation
                start_col_info = {"table": start_table, "column": start_col}
                end_col_info = {"table": end_table, "column": end_col}
                output = generate_full_select(graph, path, start_col_info, end_col_info)
            print(output)
        else:
            logging.info("No path found")
            print("No path found")

    except Exception as e:
        logging.error(f"An error occurred during processing: {str(e)}")
        raise


if __name__ == "__main__":
    main()
