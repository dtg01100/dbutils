"""
Schema Detection and Database-Specific Query Templates

This module provides database-type detection and appropriate schema/metadata
queries for different database systems (PostgreSQL, MySQL, Oracle, SQL Server, etc.)
"""

import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class DatabaseType:
    """Database type identifiers."""
    DB2_I = "db2_i"           # DB2 for i (AS/400, IBM i)
    DB2_ZOS = "db2_zos"       # DB2 for z/OS (Mainframe)
    DB2_LUW = "db2_luw"       # DB2 for Linux/Unix/Windows
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    ORACLE = "oracle"
    SQLSERVER = "sqlserver"
    SQLITE = "sqlite"
    MARIADB = "mariadb"
    H2 = "h2"
    DERBY = "derby"
    HSQLDB = "hsqldb"
    UNKNOWN = "unknown"


class SchemaQueryTemplates:
    """SQL query templates for different database systems."""
    
    # DB2 for i (AS/400, IBM i) - Uses QSYS2 catalog
    DB2_I_TABLES = """
        SELECT
            TABLE_SCHEMA,
            TABLE_NAME,
            TABLE_TEXT AS REMARKS
        FROM QSYS2.SYSTABLES
        WHERE TABLE_TYPE IN ('T', 'P')
        AND SYSTEM_TABLE = 'N'
        {schema_filter}
        ORDER BY TABLE_SCHEMA, TABLE_NAME
        {pagination}
    """
    
    DB2_I_COLUMNS = """
        SELECT
            c.TABLE_SCHEMA,
            c.TABLE_NAME,
            c.COLUMN_NAME,
            c.DATA_TYPE AS TYPENAME,
            c.LENGTH,
            c.NUMERIC_SCALE AS SCALE,
            c.IS_NULLABLE AS NULLS,
            c.COLUMN_TEXT AS REMARKS
        FROM QSYS2.SYSCOLUMNS c
        WHERE ({table_filter})
        ORDER BY c.TABLE_SCHEMA, c.TABLE_NAME, c.ORDINAL_POSITION
    """
    
    DB2_I_SCHEMAS = """
        SELECT DISTINCT TABLE_SCHEMA
        FROM QSYS2.SYSTABLES
        WHERE SYSTEM_TABLE = 'N'
        ORDER BY TABLE_SCHEMA
    """
    
    # DB2 for z/OS (Mainframe) - Uses SYSIBM catalog
    DB2_ZOS_TABLES = """
        SELECT
            CREATOR AS TABLE_SCHEMA,
            NAME AS TABLE_NAME,
            REMARKS
        FROM SYSIBM.SYSTABLES
        WHERE TYPE IN ('T', 'V')
        {schema_filter}
        ORDER BY CREATOR, NAME
        {pagination}
    """
    
    DB2_ZOS_COLUMNS = """
        SELECT
            TBCREATOR AS TABLE_SCHEMA,
            TBNAME AS TABLE_NAME,
            NAME AS COLUMN_NAME,
            COLTYPE AS TYPENAME,
            LENGTH,
            SCALE,
            NULLS,
            REMARKS
        FROM SYSIBM.SYSCOLUMNS
        WHERE ({table_filter})
        ORDER BY TBCREATOR, TBNAME, COLNO
    """
    
    DB2_ZOS_SCHEMAS = """
        SELECT DISTINCT CREATOR AS TABLE_SCHEMA
        FROM SYSIBM.SYSTABLES
        WHERE TYPE IN ('T', 'V')
        ORDER BY CREATOR
    """
    
    # PostgreSQL
    POSTGRESQL_TABLES = """
        SELECT
            table_schema AS TABLE_SCHEMA,
            table_name AS TABLE_NAME,
            obj_description((table_schema||'.'||table_name)::regclass, 'pg_class') AS REMARKS
        FROM information_schema.tables
        WHERE table_type IN ('BASE TABLE', 'VIEW')
        AND table_schema NOT IN ('pg_catalog', 'information_schema')
        {schema_filter}
        ORDER BY table_schema, table_name
        {pagination}
    """
    
    POSTGRESQL_COLUMNS = """
        SELECT
            c.table_schema AS TABLE_SCHEMA,
            c.table_name AS TABLE_NAME,
            c.column_name AS COLUMN_NAME,
            c.data_type AS TYPENAME,
            c.character_maximum_length AS LENGTH,
            c.numeric_scale AS SCALE,
            c.is_nullable AS NULLS,
            col_description((c.table_schema||'.'||c.table_name)::regclass, c.ordinal_position) AS REMARKS
        FROM information_schema.columns c
        WHERE ({table_filter})
        ORDER BY c.table_schema, c.table_name, c.ordinal_position
    """
    
    POSTGRESQL_SCHEMAS = """
        SELECT schema_name AS TABLE_SCHEMA
        FROM information_schema.schemata
        WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
        ORDER BY schema_name
    """
    
    # MySQL / MariaDB
    MYSQL_TABLES = """
        SELECT
            table_schema AS TABLE_SCHEMA,
            table_name AS TABLE_NAME,
            table_comment AS REMARKS
        FROM information_schema.tables
        WHERE table_type IN ('BASE TABLE', 'VIEW')
        AND table_schema NOT IN ('mysql', 'information_schema', 'performance_schema', 'sys')
        {schema_filter}
        ORDER BY table_schema, table_name
        {pagination}
    """
    
    MYSQL_COLUMNS = """
        SELECT
            c.table_schema AS TABLE_SCHEMA,
            c.table_name AS TABLE_NAME,
            c.column_name AS COLUMN_NAME,
            c.data_type AS TYPENAME,
            c.character_maximum_length AS LENGTH,
            c.numeric_scale AS SCALE,
            c.is_nullable AS NULLS,
            c.column_comment AS REMARKS
        FROM information_schema.columns c
        WHERE ({table_filter})
        ORDER BY c.table_schema, c.table_name, c.ordinal_position
    """
    
    MYSQL_SCHEMAS = """
        SELECT DISTINCT table_schema AS TABLE_SCHEMA
        FROM information_schema.tables
        WHERE table_schema NOT IN ('mysql', 'information_schema', 'performance_schema', 'sys')
        ORDER BY table_schema
    """
    
    # Oracle
    ORACLE_TABLES = """
        SELECT
            owner AS TABLE_SCHEMA,
            table_name AS TABLE_NAME,
            (SELECT comments FROM all_tab_comments tc 
             WHERE tc.owner = t.owner AND tc.table_name = t.table_name) AS REMARKS
        FROM all_tables t
        WHERE owner NOT IN ('SYS', 'SYSTEM', 'OUTLN', 'XDB', 'CTXSYS', 'MDSYS', 'OLAPSYS')
        {schema_filter}
        ORDER BY owner, table_name
        {pagination}
    """
    
    ORACLE_COLUMNS = """
        SELECT
            c.owner AS TABLE_SCHEMA,
            c.table_name AS TABLE_NAME,
            c.column_name AS COLUMN_NAME,
            c.data_type AS TYPENAME,
            c.data_length AS LENGTH,
            c.data_scale AS SCALE,
            c.nullable AS NULLS,
            (SELECT comments FROM all_col_comments cc 
             WHERE cc.owner = c.owner AND cc.table_name = c.table_name 
             AND cc.column_name = c.column_name) AS REMARKS
        FROM all_tab_columns c
        WHERE ({table_filter})
        ORDER BY c.owner, c.table_name, c.column_id
    """
    
    ORACLE_SCHEMAS = """
        SELECT DISTINCT owner AS TABLE_SCHEMA
        FROM all_tables
        WHERE owner NOT IN ('SYS', 'SYSTEM', 'OUTLN', 'XDB', 'CTXSYS', 'MDSYS', 'OLAPSYS')
        ORDER BY owner
    """
    
    # SQL Server
    SQLSERVER_TABLES = """
        SELECT
            s.name AS TABLE_SCHEMA,
            t.name AS TABLE_NAME,
            CAST(ep.value AS VARCHAR(MAX)) AS REMARKS
        FROM sys.tables t
        INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
        LEFT JOIN sys.extended_properties ep ON ep.major_id = t.object_id 
            AND ep.minor_id = 0 AND ep.name = 'MS_Description'
        WHERE s.name NOT IN ('sys', 'INFORMATION_SCHEMA')
        {schema_filter}
        ORDER BY s.name, t.name
        {pagination}
    """
    
    SQLSERVER_COLUMNS = """
        SELECT
            s.name AS TABLE_SCHEMA,
            t.name AS TABLE_NAME,
            c.name AS COLUMN_NAME,
            ty.name AS TYPENAME,
            c.max_length AS LENGTH,
            c.scale AS SCALE,
            CASE WHEN c.is_nullable = 1 THEN 'Y' ELSE 'N' END AS NULLS,
            CAST(ep.value AS VARCHAR(MAX)) AS REMARKS
        FROM sys.columns c
        INNER JOIN sys.tables t ON c.object_id = t.object_id
        INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
        INNER JOIN sys.types ty ON c.user_type_id = ty.user_type_id
        LEFT JOIN sys.extended_properties ep ON ep.major_id = c.object_id 
            AND ep.minor_id = c.column_id AND ep.name = 'MS_Description'
        WHERE ({table_filter})
        ORDER BY s.name, t.name, c.column_id
    """
    
    SQLSERVER_SCHEMAS = """
        SELECT DISTINCT s.name AS TABLE_SCHEMA
        FROM sys.schemas s
        WHERE s.name NOT IN ('sys', 'INFORMATION_SCHEMA', 'guest')
        ORDER BY s.name
    """


def detect_database_type(jdbc_url: Optional[str] = None, driver_class: Optional[str] = None) -> str:
    """
    Detect database type from JDBC URL or driver class.
    
    Args:
        jdbc_url: JDBC connection URL
        driver_class: JDBC driver class name
        
    Returns:
        Database type identifier (DatabaseType constant)
    """
    # Check environment variable override first
    db_type_override = os.environ.get("DBUTILS_DATABASE_TYPE")
    if db_type_override:
        logger.info(f"Using database type from DBUTILS_DATABASE_TYPE: {db_type_override}")
        return db_type_override.lower()
    
    # Detect from JDBC URL
    if jdbc_url:
        url_lower = jdbc_url.lower()
        
        if "jdbc:as400:" in url_lower or "jdbc:db2:" in url_lower:
            # Distinguish between DB2 variants
            if "as400" in url_lower:
                return DatabaseType.DB2_I
            elif "db2:" in url_lower and (":446" in url_lower or "location=" in url_lower or "sysibm" in url_lower):
                # Port 446 is typical for z/OS, or location= parameter indicates z/OS
                return DatabaseType.DB2_ZOS
            elif re.search(r':5\d{3}\b', url_lower):
                # Port 5xxx (but not 50000) is typically DB2 for i
                port_match = re.search(r':(\d+)', url_lower)
                if port_match and port_match.group(1).startswith('5') and len(port_match.group(1)) == 4:
                    return DatabaseType.DB2_I
                return DatabaseType.DB2_LUW
            else:
                # Default to LUW for other DB2 connections (e.g., port 50000)
                return DatabaseType.DB2_LUW
        
        if "jdbc:postgresql:" in url_lower:
            return DatabaseType.POSTGRESQL
        
        if "jdbc:mysql:" in url_lower:
            return DatabaseType.MYSQL
        
        if "jdbc:mariadb:" in url_lower:
            return DatabaseType.MARIADB
        
        if "jdbc:oracle:" in url_lower:
            return DatabaseType.ORACLE
        
        if "jdbc:sqlserver:" in url_lower or "jdbc:jtds:" in url_lower:
            return DatabaseType.SQLSERVER
        
        if "jdbc:sqlite:" in url_lower:
            return DatabaseType.SQLITE
        
        if "jdbc:h2:" in url_lower:
            return DatabaseType.H2
        
        if "jdbc:derby:" in url_lower:
            return DatabaseType.DERBY
        
        if "jdbc:hsqldb:" in url_lower:
            return DatabaseType.HSQLDB
    
    # Detect from driver class
    if driver_class:
        driver_lower = driver_class.lower()
        
        if "db2" in driver_lower:
            if "as400" in driver_lower or "jt400" in driver_lower:
                return DatabaseType.DB2_I
            elif "zos" in driver_lower or "390" in driver_lower or "jcc" in driver_lower:
                # JCC driver is typically used for z/OS
                return DatabaseType.DB2_ZOS
            return DatabaseType.DB2_LUW
        
        if "postgresql" in driver_lower:
            return DatabaseType.POSTGRESQL
        
        if "mysql" in driver_lower:
            return DatabaseType.MYSQL
        
        if "mariadb" in driver_lower:
            return DatabaseType.MARIADB
        
        if "oracle" in driver_lower:
            return DatabaseType.ORACLE
        
        if "sqlserver" in driver_lower or "jtds" in driver_lower:
            return DatabaseType.SQLSERVER
        
        if "sqlite" in driver_lower:
            return DatabaseType.SQLITE
    
    # Default to DB2 for i (legacy behavior)
    logger.warning("Could not detect database type, defaulting to DB2 for i")
    return DatabaseType.DB2_I


def get_schema_queries(db_type: str) -> Tuple[str, str, str]:
    """
    Get schema query templates for the specified database type.
    
    Args:
        db_type: Database type identifier
        
    Returns:
        Tuple of (tables_query, columns_query, schemas_query)
    """
    templates = SchemaQueryTemplates()
    
    if db_type == DatabaseType.DB2_I:
        return (templates.DB2_I_TABLES, templates.DB2_I_COLUMNS, templates.DB2_I_SCHEMAS)
    
    elif db_type == DatabaseType.DB2_ZOS:
        return (templates.DB2_ZOS_TABLES, templates.DB2_ZOS_COLUMNS, templates.DB2_ZOS_SCHEMAS)
    
    elif db_type == DatabaseType.POSTGRESQL:
        return (templates.POSTGRESQL_TABLES, templates.POSTGRESQL_COLUMNS, templates.POSTGRESQL_SCHEMAS)
    
    elif db_type in (DatabaseType.MYSQL, DatabaseType.MARIADB):
        return (templates.MYSQL_TABLES, templates.MYSQL_COLUMNS, templates.MYSQL_SCHEMAS)
    
    elif db_type == DatabaseType.ORACLE:
        return (templates.ORACLE_TABLES, templates.ORACLE_COLUMNS, templates.ORACLE_SCHEMAS)
    
    elif db_type == DatabaseType.SQLSERVER:
        return (templates.SQLSERVER_TABLES, templates.SQLSERVER_COLUMNS, templates.SQLSERVER_SCHEMAS)
    
    else:
        # Fallback to DB2 for i
        logger.warning(f"Unknown database type '{db_type}', using DB2 for i queries")
        return (templates.DB2_I_TABLES, templates.DB2_I_COLUMNS, templates.DB2_I_SCHEMAS)


def build_schema_filter(db_type: str, schema_filter: Optional[str]) -> str:
    """
    Build schema filter clause appropriate for the database type.
    
    Args:
        db_type: Database type identifier
        schema_filter: Schema name to filter by
        
    Returns:
        SQL WHERE clause fragment
    """
    if not schema_filter:
        return ""
    
    # Map database types to their schema column names
    schema_column_map = {
        DatabaseType.DB2_I: "TABLE_SCHEMA",
        DatabaseType.DB2_ZOS: "CREATOR",
        DatabaseType.POSTGRESQL: "table_schema",
        DatabaseType.MYSQL: "table_schema",
        DatabaseType.MARIADB: "table_schema",
        DatabaseType.ORACLE: "owner",
        DatabaseType.SQLSERVER: "s.name",
    }
    
    schema_col = schema_column_map.get(db_type, "TABLE_SCHEMA")
    
    # Escape single quotes in schema name
    safe_schema = schema_filter.replace("'", "''")
    
    return f"AND {schema_col} = '{safe_schema.upper()}'"


def build_pagination_clause(db_type: str, limit: Optional[int], offset: Optional[int]) -> str:
    """
    Build pagination clause appropriate for the database type.
    
    Args:
        db_type: Database type identifier
        limit: Maximum number of rows
        offset: Number of rows to skip
        
    Returns:
        SQL pagination clause
    """
    if limit is None:
        return ""
    
    # Different databases use different syntax
    if db_type in (DatabaseType.POSTGRESQL, DatabaseType.MYSQL, DatabaseType.MARIADB, 
                   DatabaseType.SQLITE, DatabaseType.H2):
        # Standard LIMIT/OFFSET
        if offset:
            return f"LIMIT {limit} OFFSET {offset}"
        else:
            return f"LIMIT {limit}"
    
    elif db_type in (DatabaseType.DB2_I, DatabaseType.DB2_ZOS, DatabaseType.DB2_LUW):
        # DB2 uses FETCH FIRST ... ROWS ONLY with optional OFFSET
        if offset:
            return f"OFFSET {offset} ROWS FETCH FIRST {limit} ROWS ONLY"
        else:
            return f"FETCH FIRST {limit} ROWS ONLY"
    
    elif db_type == DatabaseType.ORACLE:
        # Oracle uses FETCH FIRST (12c+) or ROWNUM (older)
        if offset:
            return f"OFFSET {offset} ROWS FETCH FIRST {limit} ROWS ONLY"
        else:
            return f"FETCH FIRST {limit} ROWS ONLY"
    
    elif db_type == DatabaseType.SQLSERVER:
        # SQL Server uses OFFSET/FETCH (requires ORDER BY)
        if offset:
            return f"OFFSET {offset} ROWS FETCH NEXT {limit} ROWS ONLY"
        else:
            return f"OFFSET 0 ROWS FETCH NEXT {limit} ROWS ONLY"
    
    else:
        # Fallback to DB2 syntax
        if offset:
            return f"OFFSET {offset} ROWS FETCH FIRST {limit} ROWS ONLY"
        else:
            return f"FETCH FIRST {limit} ROWS ONLY"


def build_table_filter(db_type: str, tables: List[Any]) -> str:
    """
    Build table filter clause for column queries.
    
    Args:
        db_type: Database type identifier
        tables: List of TableInfo objects
        
    Returns:
        SQL WHERE clause fragment
    """
    if not tables:
        return "1=0"  # No tables, impossible condition
    
    # Build conditions for each table
    conditions = []
    
    # Schema and table column names vary by database
    if db_type == DatabaseType.ORACLE:
        schema_col, table_col = "c.owner", "c.table_name"
    elif db_type == DatabaseType.SQLSERVER:
        schema_col, table_col = "s.name", "t.name"
    elif db_type == DatabaseType.DB2_ZOS:
        schema_col, table_col = "TBCREATOR", "TBNAME"
    elif db_type in (DatabaseType.POSTGRESQL, DatabaseType.MYSQL, DatabaseType.MARIADB):
        schema_col, table_col = "c.table_schema", "c.table_name"
    else:  # DB2 for i, DB2 LUW, etc.
        schema_col, table_col = "c.TABLE_SCHEMA", "c.TABLE_NAME"
    
    for table in tables:
        schema = table.schema.replace("'", "''")
        name = table.name.replace("'", "''")
        conditions.append(f"({schema_col} = '{schema}' AND {table_col} = '{name}')")
    
    return " OR ".join(conditions)
