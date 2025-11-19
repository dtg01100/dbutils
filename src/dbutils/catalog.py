"""
Catalog query abstraction for IBM i (DB2 for i) via QSYS2.

All queries return normalized dictionaries with consistent field names:
- TABSCHEMA, TABNAME for tables
- COLNAME, DATA_TYPE, LENGTH, SCALE for columns
- etc.
"""

import logging
from typing import Any, Dict, List, Optional

from .utils import query_runner

logger = logging.getLogger(__name__)


def get_tables(schema: Optional[str] = None, mock: bool = False) -> List[Dict[str, Any]]:
    """
    Get all tables from QSYS2.SYSTABLES for IBM i.

    Args:
        schema: Optional schema filter (e.g., 'MYSCHEMA')
        mock: Return mock data if True

    Returns:
        List of dicts with keys: TABSCHEMA, TABNAME, TYPE, REMARKS
    """
    if mock:
        return [
            {"TABSCHEMA": "TEST", "TABNAME": "USERS", "TYPE": "T", "REMARKS": "User accounts"},
            {"TABSCHEMA": "TEST", "TABNAME": "ORDERS", "TYPE": "T", "REMARKS": "Order records"},
            {"TABSCHEMA": "TEST", "TABNAME": "PRODUCTS", "TYPE": "T", "REMARKS": "Product catalog"},
        ]

    where_parts = ["TABLE_TYPE IN ('T', 'P', 'L')"]
    if schema:
        where_parts.append(f"TABLE_SCHEMA = '{schema}'")
    where_clause = "WHERE " + " AND ".join(where_parts)

    sql = f"""
        SELECT 
            TABLE_SCHEMA AS TABSCHEMA,
            TABLE_NAME AS TABNAME,
            TABLE_TYPE AS TYPE,
            COALESCE(TABLE_TEXT, '') AS REMARKS
        FROM QSYS2.SYSTABLES
        {where_clause}
        ORDER BY TABLE_SCHEMA, TABLE_NAME
    """

    result = query_runner(sql)
    if not result:
        logger.warning("No tables found or query failed")
        return []

    return result


def get_columns(schema: Optional[str] = None, table: Optional[str] = None, mock: bool = False) -> List[Dict[str, Any]]:
    """
    Get column metadata from QSYS2.SYSCOLUMNS for IBM i.

    Args:
        schema: Optional schema filter
        table: Optional table name filter
        mock: Return mock data if True

    Returns:
        List of dicts with keys: TABSCHEMA, TABNAME, COLNAME, DATA_TYPE, LENGTH, SCALE, ORDINAL_POSITION, REMARKS, IS_NULLABLE
    """
    if mock:
        return [
            {
                "TABSCHEMA": "TEST",
                "TABNAME": "USERS",
                "COLNAME": "ID",
                "DATA_TYPE": "INTEGER",
                "LENGTH": 4,
                "SCALE": 0,
                "ORDINAL_POSITION": 1,
                "REMARKS": "User ID",
                "IS_NULLABLE": "N",
            },
            {
                "TABSCHEMA": "TEST",
                "TABNAME": "USERS",
                "COLNAME": "NAME",
                "DATA_TYPE": "VARCHAR",
                "LENGTH": 100,
                "SCALE": 0,
                "ORDINAL_POSITION": 2,
                "REMARKS": "",
                "IS_NULLABLE": "Y",
            },
            {
                "TABSCHEMA": "TEST",
                "TABNAME": "ORDERS",
                "COLNAME": "ID",
                "DATA_TYPE": "INTEGER",
                "LENGTH": 4,
                "SCALE": 0,
                "ORDINAL_POSITION": 1,
                "REMARKS": "Order ID",
                "IS_NULLABLE": "N",
            },
            {
                "TABSCHEMA": "TEST",
                "TABNAME": "ORDERS",
                "COLNAME": "USER_ID",
                "DATA_TYPE": "INTEGER",
                "LENGTH": 4,
                "SCALE": 0,
                "ORDINAL_POSITION": 2,
                "REMARKS": "FK to USERS",
                "IS_NULLABLE": "Y",
            },
            {
                "TABSCHEMA": "TEST",
                "TABNAME": "ORDERS",
                "COLNAME": "PRODUCT_ID",
                "DATA_TYPE": "INTEGER",
                "LENGTH": 4,
                "SCALE": 0,
                "ORDINAL_POSITION": 3,
                "REMARKS": "FK to PRODUCTS",
                "IS_NULLABLE": "Y",
            },
            {
                "TABSCHEMA": "TEST",
                "TABNAME": "PRODUCTS",
                "COLNAME": "ID",
                "DATA_TYPE": "INTEGER",
                "LENGTH": 4,
                "SCALE": 0,
                "ORDINAL_POSITION": 1,
                "REMARKS": "Product ID",
                "IS_NULLABLE": "N",
            },
        ]

    where_clauses = []
    if schema:
        where_clauses.append(f"TABLE_SCHEMA = '{schema}'")
    if table:
        where_clauses.append(f"TABLE_NAME = '{table}'")

    where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

    sql = f"""
        SELECT 
            TABLE_SCHEMA AS TABSCHEMA,
            TABLE_NAME AS TABNAME,
            COLUMN_NAME AS COLNAME,
            DATA_TYPE,
            COALESCE(LENGTH, 0) AS LENGTH,
            COALESCE(NUMERIC_SCALE, 0) AS SCALE,
            ORDINAL_POSITION,
            COALESCE(COLUMN_TEXT, '') AS REMARKS,
            IS_NULLABLE
        FROM QSYS2.SYSCOLUMNS
        {where_clause}
        ORDER BY TABLE_SCHEMA, TABLE_NAME, ORDINAL_POSITION
    """

    result = query_runner(sql)
    if not result:
        logger.warning("No columns found or query failed")
        return []

    return result


def get_primary_keys(schema: Optional[str] = None, mock: bool = False) -> List[Dict[str, Any]]:
    """
    Get primary key constraints from QSYS2.SYSCST and QSYS2.SYSCSTCOL for IBM i.

    Args:
        schema: Optional schema filter
        mock: Return mock data if True

    Returns:
        List of dicts with keys: TABSCHEMA, TABNAME, COLNAME, CONSTRAINT_NAME
    """
    if mock:
        return [
            {"TABSCHEMA": "TEST", "TABNAME": "USERS", "COLNAME": "ID", "CONSTRAINT_NAME": "PK_USERS"},
            {"TABSCHEMA": "TEST", "TABNAME": "ORDERS", "COLNAME": "ID", "CONSTRAINT_NAME": "PK_ORDERS"},
            {"TABSCHEMA": "TEST", "TABNAME": "PRODUCTS", "COLNAME": "ID", "CONSTRAINT_NAME": "PK_PRODUCTS"},
        ]

    where_clause = f"WHERE cst.CONSTRAINT_SCHEMA = '{schema}'" if schema else ""

    sql = f"""
        SELECT 
            cst.TABLE_SCHEMA AS TABSCHEMA,
            cst.TABLE_NAME AS TABNAME,
            col.COLUMN_NAME AS COLNAME,
            cst.CONSTRAINT_NAME
        FROM QSYS2.SYSCST cst
        JOIN QSYS2.SYSCSTCOL col 
            ON cst.CONSTRAINT_SCHEMA = col.CONSTRAINT_SCHEMA
            AND cst.CONSTRAINT_NAME = col.CONSTRAINT_NAME
        {where_clause}
        AND cst.CONSTRAINT_TYPE = 'PRIMARY KEY'
        ORDER BY TABSCHEMA, TABNAME, COLNAME
    """

    result = query_runner(sql)
    if not result:
        logger.warning("No primary keys found or query failed")
        return []

    return result


def get_indexes(schema: Optional[str] = None, table: Optional[str] = None, mock: bool = False) -> List[Dict[str, Any]]:
    """
    Get index metadata from QSYS2.SYSINDEXES for IBM i.

    Args:
        schema: Optional schema filter
        table: Optional table name filter
        mock: Return mock data if True

    Returns:
        List of dicts with keys: TABSCHEMA, TABNAME, INDEX_SCHEMA, INDEX_NAME, COLUMN_NAME, IS_UNIQUE, ORDINAL_POSITION
    """
    if mock:
        return [
            {
                "TABSCHEMA": "TEST",
                "TABNAME": "USERS",
                "INDEX_SCHEMA": "TEST",
                "INDEX_NAME": "IDX_USERS_ID",
                "COLUMN_NAME": "ID",
                "IS_UNIQUE": "Y",
                "ORDINAL_POSITION": 1,
            },
            {
                "TABSCHEMA": "TEST",
                "TABNAME": "ORDERS",
                "INDEX_SCHEMA": "TEST",
                "INDEX_NAME": "IDX_ORDERS_USER_ID",
                "COLUMN_NAME": "USER_ID",
                "IS_UNIQUE": "N",
                "ORDINAL_POSITION": 1,
            },
        ]

    where_clauses = []
    if schema:
        where_clauses.append(f"idx.TABLE_SCHEMA = '{schema}'")
    if table:
        where_clauses.append(f"idx.TABLE_NAME = '{table}'")

    where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

    sql = f"""
        SELECT 
            idx.TABLE_SCHEMA AS TABSCHEMA,
            idx.TABLE_NAME AS TABNAME,
            idx.INDEX_SCHEMA,
            idx.INDEX_NAME,
            keys.COLUMN_NAME,
            CASE WHEN idx.IS_UNIQUE = 'Y' THEN 'Y' ELSE 'N' END AS IS_UNIQUE,
            keys.ORDINAL_POSITION
        FROM QSYS2.SYSINDEXES idx
        JOIN QSYS2.SYSKEYS keys
            ON idx.INDEX_SCHEMA = keys.INDEX_SCHEMA
            AND idx.INDEX_NAME = keys.INDEX_NAME
        {where_clause}
        ORDER BY TABSCHEMA, TABNAME, INDEX_NAME, keys.ORDINAL_POSITION
    """

    result = query_runner(sql)
    if not result:
        logger.warning("No indexes found or query failed")
        return []

    return result


def get_table_sizes(schema: Optional[str] = None, mock: bool = False) -> List[Dict[str, Any]]:
    """
    Get table size information from QSYS2.SYSTABLESTAT for IBM i.

    Args:
        schema: Optional schema filter
        mock: Return mock data if True

    Returns:
        List of dicts with keys: TABSCHEMA, TABNAME, ROWCOUNT, DATA_SIZE
    """
    if mock:
        return [
            {"TABSCHEMA": "TEST", "TABNAME": "USERS", "ROWCOUNT": 12345, "DATA_SIZE": 524288},
            {"TABSCHEMA": "TEST", "TABNAME": "ORDERS", "ROWCOUNT": 98765, "DATA_SIZE": 2097152},
        ]

    where_clause = f"WHERE TABLE_SCHEMA = '{schema}'" if schema else ""

    sql = f"""
        SELECT 
            TABLE_SCHEMA AS TABSCHEMA,
            TABLE_NAME AS TABNAME,
            COALESCE(NUMBER_ROWS, 0) AS ROWCOUNT,
            COALESCE(DATA_SIZE, 0) AS DATA_SIZE
        FROM QSYS2.SYSTABLESTAT
        {where_clause}
        ORDER BY ROWCOUNT DESC
    """

    result = query_runner(sql)
    if not result:
        logger.warning("No table size stats found or query failed")
        return []

    return result


def get_foreign_keys(schema: Optional[str] = None, mock: bool = False) -> List[Dict[str, Any]]:
    """
    Get foreign key relationships from QSYS2.SYSREFCST for IBM i.

    Args:
        schema: Optional schema filter
        mock: Return mock data if True

    Returns:
        List of dicts with keys: FK_SCHEMA, FK_TABLE, FK_COLUMN, PK_SCHEMA, PK_TABLE, PK_COLUMN, CONSTRAINT_NAME
    """
    if mock:
        return []

    where_clause = f"WHERE ref.CONSTRAINT_SCHEMA = '{schema}'" if schema else ""

    sql = f"""
        SELECT 
            ref.CONSTRAINT_SCHEMA AS FK_SCHEMA,
            fkcst.TABLE_NAME AS FK_TABLE,
            fkcol.COLUMN_NAME AS FK_COLUMN,
            ref.UNIQUE_CONSTRAINT_SCHEMA AS PK_SCHEMA,
            pkcst.TABLE_NAME AS PK_TABLE,
            pkcol.COLUMN_NAME AS PK_COLUMN,
            ref.CONSTRAINT_NAME
        FROM QSYS2.SYSREFCST ref
        JOIN QSYS2.SYSCST fkcst
            ON ref.CONSTRAINT_SCHEMA = fkcst.CONSTRAINT_SCHEMA
            AND ref.CONSTRAINT_NAME = fkcst.CONSTRAINT_NAME
        JOIN QSYS2.SYSCSTCOL fkcol
            ON ref.CONSTRAINT_SCHEMA = fkcol.CONSTRAINT_SCHEMA
            AND ref.CONSTRAINT_NAME = fkcol.CONSTRAINT_NAME
        JOIN QSYS2.SYSCST pkcst
            ON ref.UNIQUE_CONSTRAINT_SCHEMA = pkcst.CONSTRAINT_SCHEMA
            AND ref.UNIQUE_CONSTRAINT_NAME = pkcst.CONSTRAINT_NAME
        JOIN QSYS2.SYSCSTCOL pkcol
            ON pkcst.CONSTRAINT_SCHEMA = pkcol.CONSTRAINT_SCHEMA
            AND pkcst.CONSTRAINT_NAME = pkcol.CONSTRAINT_NAME
        {where_clause}
        ORDER BY FK_SCHEMA, FK_TABLE, FK_COLUMN
    """

    result = query_runner(sql)
    if not result:
        logger.info("No foreign keys found")
        return []

    return result
