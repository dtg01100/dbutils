import argparse
import json
import logging
from typing import Dict, List

from dbutils import catalog
from dbutils.utils import query_runner


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


def get_tables() -> List[Dict[str, object]]:
    """Get tables using IBM i catalog."""
    return catalog.get_tables()


def get_columns() -> List[Dict[str, object]]:
    """Get columns using IBM i catalog."""
    result = catalog.get_columns()
    # Normalize TYPENAME field name for compatibility
    for col in result:
        if "DATA_TYPE" in col and "TYPENAME" not in col:
            col["TYPENAME"] = col["DATA_TYPE"]
    return result


def get_primary_keys() -> List[Dict[str, object]]:
    """Get primary keys using IBM i catalog."""
    result = catalog.get_primary_keys()
    # Add TYPENAME field by looking up column data type
    if result:
        cols = catalog.get_columns()
        col_types = {
            (c["TABSCHEMA"], c["TABNAME"], c["COLNAME"]): c.get("DATA_TYPE", "")
            for c in cols
        }
        for pk in result:
            key = (pk["TABSCHEMA"], pk["TABNAME"], pk["COLNAME"])
            pk["TYPENAME"] = col_types.get(key, "")
    return result


def get_foreign_keys() -> List[Dict[str, object]]:
    """Get foreign keys using IBM i catalog."""
    return catalog.get_foreign_keys()


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


def infer_relationships(
    tables: List[Dict[str, object]],
    columns: List[Dict[str, object]],
    pks: List[Dict[str, object]],
    use_mock: bool = False,
) -> List[Dict[str, str]]:
    """Infer foreign-key-like relationships using actual constraints, remarks, and naming heuristics.

    Returns list of relationships with keys: TABSCHEMA, TABNAME, COLNAME, REFTABSCHEMA, REFTABNAME, REFCOLNAME
    """
    relationships: List[Dict[str, str]] = []

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
            table_cols = [c for c in columns if f"{c.get('TABSCHEMA')}.{c.get('TABNAME')}" == table_key]
            for col in table_cols:
                col_name = col["COLNAME"]
                col_type = col.get("TYPENAME")
                col_desc = str(col.get("REMARKS", "")).lower()

                # Check description for explicit references
                for other_key, other_table in table_dict.items():
                    if other_key == table_key:
                        continue
                    other_table_name = other_table["TABNAME"].lower()
                    if other_table_name in col_desc and any(
                        k in col_desc for k in ("ref", "foreign", "key", "references")
                    ):
                        matching_pks = [
                            pk
                            for pk in pks
                            if f"{pk.get('TABSCHEMA')}.{pk.get('TABNAME')}" == other_key
                            and pk.get("TYPENAME") == col_type
                        ]
                        for pk in matching_pks:
                            relationships.append(
                                {
                                    "TABSCHEMA": table["TABSCHEMA"],
                                    "TABNAME": table["TABNAME"],
                                    "COLNAME": col_name,
                                    "REFTABSCHEMA": pk.get("TABSCHEMA") or table["TABSCHEMA"],
                                    "REFTABNAME": pk.get("TABNAME"),
                                    "REFCOLNAME": pk.get("COLNAME"),
                                }
                            )
                            break

                # Heuristic fallback: name-based
                for pk in pks:
                    pk_table_key = f"{pk.get('TABSCHEMA')}.{pk.get('TABNAME')}"
                    if pk_table_key == table_key:
                        continue
                    pk_col = pk.get("COLNAME")
                    pk_type = pk.get("TYPENAME")
                    if pk_type and col_type and str(pk_type) == str(col_type):
                        if (
                            col_name.lower() == (pk_col or "").lower()
                            or col_name.lower() == f"{pk.get('TABNAME', '').lower()}_id"
                            or (
                                col_name.lower().endswith("_id")
                                and col_name[:-3].lower() == pk.get("TABNAME", "").lower()
                            )
                        ):
                            relationships.append(
                                {
                                    "TABSCHEMA": table["TABSCHEMA"],
                                    "TABNAME": table["TABNAME"],
                                    "COLNAME": col_name,
                                    "REFTABSCHEMA": pk.get("TABSCHEMA") or table["TABSCHEMA"],
                                    "REFTABNAME": pk.get("TABNAME"),
                                    "REFCOLNAME": pk_col,
                                }
                            )
    return relationships


def build_schema_map(
    tables: List[Dict[str, object]], columns: List[Dict[str, object]], relationships: List[Dict[str, str]]
) -> Dict[str, object]:
    """Build a schema mapping keyed by 'SCHEMA.TABLE' containing columns and relationships."""
    schema: Dict[str, object] = {}
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
                }
            )
    return schema


def main():
    # Set up logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    parser = argparse.ArgumentParser(description="Map DB2 database schema")
    parser.add_argument("-o", "--output", help="Output file (default stdout)")
    parser.add_argument("-t", "--table", help="Specific table to map (schema.table)")
    parser.add_argument("--mock", action="store_true", help="Use mock data for testing")
    args = parser.parse_args()

    logging.info("Starting schema mapping")
    logging.info(f"Using mock data: {args.mock}")
    if args.table:
        logging.info(f"Mapping specific table: {args.table}")
    if args.output:
        logging.info(f"Output will be written to: {args.output}")

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

        schema = build_schema_map(tables, columns, relationships)
        logging.info(f"Built schema map for {len(schema)} tables")

        if args.table:
            if args.table in schema:
                result = {args.table: schema[args.table]}
                logging.info(f"Successfully mapped table {args.table}")
            else:
                result = {"error": f"Table {args.table} not found"}
                logging.warning(f"Requested table {args.table} not found in schema")
            output = json.dumps(result, indent=2)
        else:
            output = json.dumps(schema, indent=2)
            logging.info("Successfully mapped complete schema")

        if args.output:
            logging.info(f"Writing output to {args.output}")
            with open(args.output, "w") as f:
                f.write(output)
            logging.info("Output written successfully")
        else:
            print(output)

    except Exception as e:
        logging.error(f"An error occurred during schema mapping: {str(e)}")
        raise


if __name__ == "__main__":
    main()
