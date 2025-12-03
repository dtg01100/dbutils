import argparse
import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List

from dbutils import catalog


def mock_get_tables() -> List[Dict[str, str]]:
    return [
        {"TABSCHEMA": "TEST", "TABNAME": "USERS", "TYPE": "T"},
        {"TABSCHEMA": "TEST", "TABNAME": "ORDERS", "TYPE": "T"},
        {"TABSCHEMA": "TEST", "TABNAME": "PRODUCTS", "TYPE": "T"},
    ]


def mock_get_columns() -> List[Dict[str, object]]:
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


def mock_get_primary_keys() -> List[Dict[str, str]]:
    return [
        {"TABSCHEMA": "TEST", "TABNAME": "USERS", "COLNAME": "ID", "TYPENAME": "INTEGER"},
        {"TABSCHEMA": "TEST", "TABNAME": "ORDERS", "COLNAME": "ID", "TYPENAME": "INTEGER"},
        {"TABSCHEMA": "TEST", "TABNAME": "PRODUCTS", "COLNAME": "ID", "TYPENAME": "INTEGER"},
    ]


def mock_get_foreign_keys() -> List[Dict[str, str]]:
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


def get_tables() -> List[Dict[str, Any]]:
    """Get tables using IBM i catalog."""
    return catalog.get_tables()


def get_columns() -> List[Dict[str, Any]]:
    """Get columns using IBM i catalog and normalize."""
    result = catalog.get_columns()
    for col in result:
        if "DATA_TYPE" in col and "TYPENAME" not in col:
            col["TYPENAME"] = col["DATA_TYPE"]
    return result


def get_primary_keys(all_columns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Get primary keys and enrich with type info from all_columns."""
    pks = catalog.get_primary_keys()
    if not pks:
        return []

    col_types = {(c["TABSCHEMA"], c["TABNAME"], c["COLNAME"]): c.get("DATA_TYPE", "") for c in all_columns}
    for pk in pks:
        key = (pk["TABSCHEMA"], pk["TABNAME"], pk["COLNAME"])
        pk["TYPENAME"] = col_types.get(key, "")
    return pks


def get_foreign_keys() -> List[Dict[str, Any]]:
    """Get foreign keys using IBM i catalog."""
    return catalog.get_foreign_keys()


def infer_relationships(
    tables: List[Dict[str, Any]],
    columns: List[Dict[str, Any]],
    pks: List[Dict[str, Any]],
    fks: List[Dict[str, Any]] | None = None,
) -> List[Dict[str, str]]:
    """Infer relationships using actual constraints, remarks, and naming heuristics."""
    relationships: Dict[tuple, Dict[str, str]] = {}

    # 1. Use actual foreign key constraints (if provided)
    for fk in fks or []:
        rel_key = (
            fk["TABSCHEMA"],
            fk["TABNAME"],
            fk["COLNAME"],
            fk["REFTABSCHEMA"],
            fk["REFTABNAME"],
            fk["REFCOLNAME"],
        )
        relationships[rel_key] = {
            "TABSCHEMA": fk["TABSCHEMA"],
            "TABNAME": fk["TABNAME"],
            "COLNAME": fk["COLNAME"],
            "REFTABSCHEMA": fk["REFTABSCHEMA"],
            "REFTABNAME": fk["REFTABNAME"],
            "REFCOLNAME": fk["REFCOLNAME"],
        }

    # 2. Fallback to inference if no FKs were found
    if not relationships:
        # Pre-build lookups for efficiency
        table_dict = {f"{t['TABSCHEMA']}.{t['TABNAME']}": t for t in tables}
        pk_lookup = {(pk.get("TABSCHEMA"), pk.get("TABNAME")): [] for pk in pks}
        for pk in pks:
            pk_lookup[(pk.get("TABSCHEMA"), pk.get("TABNAME"))].append(pk)

        for col in columns:
            col_table_key = f"{col.get('TABSCHEMA')}.{col.get('TABNAME')}"
            col_name_lower = col["COLNAME"].lower()
            col_type = col.get("TYPENAME")
            col_desc = str(col.get("REMARKS", "")).lower()

            # Heuristic 1: Check description for explicit references
            if any(k in col_desc for k in ("ref", "foreign", "key", "references")):
                for other_key, other_table in table_dict.items():
                    if other_key == col_table_key:
                        continue
                    if other_table["TABNAME"].lower() in col_desc:
                        matching_pks = pk_lookup.get((other_table["TABSCHEMA"], other_table["TABNAME"]), [])
                        for pk in matching_pks:
                            if pk.get("TYPENAME") == col_type:
                                rel_key = (
                                    col["TABSCHEMA"],
                                    col["TABNAME"],
                                    col["COLNAME"],
                                    pk["TABSCHEMA"],
                                    pk["TABNAME"],
                                    pk["COLNAME"],
                                )
                                relationships[rel_key] = {
                                    "TABSCHEMA": col["TABSCHEMA"],
                                    "TABNAME": col["TABNAME"],
                                    "COLNAME": col["COLNAME"],
                                    "REFTABSCHEMA": pk["TABSCHEMA"],
                                    "REFTABNAME": pk["TABNAME"],
                                    "REFCOLNAME": pk["COLNAME"],
                                }

            # Heuristic 2: Name-based matching
            for pk in pks:
                pk_table_key = f"{pk.get('TABSCHEMA')}.{pk.get('TABNAME')}"
                if pk_table_key == col_table_key:
                    continue

                pk_col_lower = (pk.get("COLNAME") or "").lower()
                pk_table_lower = (pk.get("TABNAME") or "").lower()

                if str(pk.get("TYPENAME")) == str(col_type):
                    is_match = (
                        col_name_lower == pk_col_lower
                        or col_name_lower == f"{pk_table_lower}_id"
                        or (col_name_lower.endswith("_id") and col_name_lower[:-3] == pk_table_lower)
                    )
                    if is_match:
                        rel_key = (
                            col["TABSCHEMA"],
                            col["TABNAME"],
                            col["COLNAME"],
                            pk["TABSCHEMA"],
                            pk["TABNAME"],
                            pk["COLNAME"],
                        )
                        relationships[rel_key] = {
                            "TABSCHEMA": col["TABSCHEMA"],
                            "TABNAME": col["TABNAME"],
                            "COLNAME": col["COLNAME"],
                            "REFTABSCHEMA": pk["TABSCHEMA"],
                            "REFTABNAME": pk["TABNAME"],
                            "REFCOLNAME": pk["COLNAME"],
                        }
    return list(relationships.values())


def build_schema_map(
    tables: List[Dict[str, Any]],
    columns: List[Dict[str, Any]],
    relationships: List[Dict[str, str]],
) -> Dict[str, Any]:
    """Build a schema mapping keyed by 'SCHEMA.TABLE'."""
    schema: Dict[str, Any] = {}
    for table in tables:
        key = f"{table['TABSCHEMA']}.{table['TABNAME']}"
        schema[key] = {"type": table.get("TYPE"), "columns": {}, "relationships": []}

    for col in columns:
        key = f"{col.get('TABSCHEMA')}.{col.get('TABNAME')}"
        if key in schema:
            schema[key]["columns"][col["COLNAME"]] = {
                "type": col.get("TYPENAME"),
                "length": col.get("LENGTH"),
                "scale": col.get("SCALE"),
                "description": col.get("REMARKS", ""),
            }

    for rel in relationships:
        child_key = f"{rel['TABSCHEMA']}.{rel['TABNAME']}"
        parent_key = f"{rel['REFTABSCHEMA']}.{rel['REFTABNAME']}"
        if child_key in schema:
            schema[child_key]["relationships"].append(
                {
                    "parent_table": parent_key,
                    "child_column": rel["COLNAME"],
                    "parent_column": rel["REFCOLNAME"],
                },
            )
    return schema


async def get_schema_details(executor: ThreadPoolExecutor, use_mock: bool) -> tuple:
    """Fetch schema details concurrently."""
    if use_mock:
        return mock_get_tables(), mock_get_columns(), mock_get_primary_keys(), mock_get_foreign_keys()

    loop = asyncio.get_running_loop()

    # Fetch columns first, as they are needed by primary keys
    columns = await loop.run_in_executor(executor, get_columns)

    # Now fetch tables, pks, and fks concurrently
    tables_task = loop.run_in_executor(executor, get_tables)
    pks_task = loop.run_in_executor(executor, get_primary_keys, columns)
    fks_task = loop.run_in_executor(executor, get_foreign_keys)

    tables, pks, fks = await asyncio.gather(tables_task, pks_task, fks_task)

    return tables, columns, pks, fks


async def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    parser = argparse.ArgumentParser(description="Map DB2 database schema")
    parser.add_argument("-o", "--output", help="Output file (default stdout)")
    parser.add_argument("-t", "--table", help="Specific table to map (schema.table)")
    parser.add_argument("--mock", action="store_true", help="Use mock data for testing")
    args = parser.parse_args()

    logging.info("Starting schema mapping")
    logging.info(f"Using mock data: {args.mock}")

    try:
        with ThreadPoolExecutor() as executor:
            tables, columns, pks, fks = await get_schema_details(executor, args.mock)

        logging.info(
            f"Found {len(tables)} tables, {len(columns)} columns, {len(pks)} primary keys, {len(fks)} foreign keys",
        )

        relationships = infer_relationships(tables, columns, pks, fks)
        logging.info(f"Identified {len(relationships)} relationships")

        schema = build_schema_map(tables, columns, relationships)
        logging.info(f"Built schema map for {len(schema)} tables")

        if args.table:
            result = (
                {args.table: schema[args.table]} if args.table in schema else {"error": f"Table {args.table} not found"}
            )
            output = json.dumps(result, indent=2)
        else:
            output = json.dumps(schema, indent=2)

        if args.output:
            with open(args.output, "w") as f:
                f.write(output)
            logging.info(f"Output written to {args.output}")
        else:
            print(output)

    except Exception as e:
        logging.error(f"An error occurred: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
