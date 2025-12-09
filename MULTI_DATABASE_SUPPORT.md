# Multi-Database Schema Support

## Overview

The Qt Browser now includes automatic database-type detection and uses appropriate schema metadata queries for different database systems. This eliminates the need for hardcoded DB2-specific queries and enables support for PostgreSQL, MySQL, Oracle, SQL Server, and other databases via JDBC.

## Supported Databases

- **DB2 for i (AS/400, IBM i)** - Uses QSYS2 system catalog
- **DB2 for z/OS (Mainframe)** - Uses SYSIBM catalog  
- **DB2 LUW (Linux/Unix/Windows)** - Uses SYSCAT catalog
- **PostgreSQL** - Uses information_schema and pg_catalog
- **MySQL / MariaDB** - Uses information_schema
- **Oracle** - Uses ALL_TABLES and ALL_TAB_COLUMNS
- **SQL Server** - Uses sys.tables and sys.columns
- **SQLite** - Direct file access (already implemented)
- **H2, Derby, HSQLDB** - Generic LIMIT/OFFSET support

## Implementation

### New Module: `schema_detector.py`

This module provides:

1. **Database Type Detection**
   - Automatically detects database type from JDBC URL
   - Falls back to driver class name detection
   - Environment variable override: `DBUTILS_DATABASE_TYPE`

2. **Schema Query Templates**
   - Database-specific SQL for querying tables and columns
   - Handles schema/catalog differences across databases
   - Filters out system schemas appropriately for each DB

3. **Pagination Support**
   - PostgreSQL/MySQL: `LIMIT n OFFSET m`
   - DB2: `OFFSET m ROWS FETCH FIRST n ROWS ONLY`
   - Oracle: `FETCH FIRST n ROWS ONLY` (12c+)
   - SQL Server: `OFFSET m ROWS FETCH NEXT n ROWS ONLY`

4. **Schema Filtering**
   - Adapts to each database's schema column naming
   - Handles case sensitivity appropriately

## Usage

### Automatic Detection

The system automatically detects the database type from environment variables:

```bash
# Example for PostgreSQL
export DBUTILS_JDBC_URL="jdbc:postgresql://localhost:5432/mydb"
export DBUTILS_JDBC_PROVIDER="postgresql"
export DBUTILS_JDBC_USER="dbuser"
export DBUTILS_JDBC_PASSWORD="password"

python3 run_qt_browser.py
```

### Manual Override

You can force a specific database type:

```bash
export DBUTILS_DATABASE_TYPE="postgresql"
```

### Detection Sources (in order of priority)

1. `DBUTILS_DATABASE_TYPE` environment variable (explicit override)
2. `DBUTILS_JDBC_URL` environment variable (parsed for database type)
3. `DBUTILS_JDBC_DRIVER_CLASS` environment variable (inferred from class name)
4. Default: DB2 for i (legacy behavior)

## Database-Specific Details

### DB2 for i (AS/400, IBM i)

Uses the QSYS2 catalog with modern SQL services:

```sql
-- Tables
SELECT TABLE_SCHEMA, TABLE_NAME, TABLE_TEXT AS REMARKS
FROM QSYS2.SYSTABLES
WHERE TABLE_TYPE IN ('T', 'P') AND SYSTEM_TABLE = 'N'

-- Columns
SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, DATA_TYPE, ...
FROM QSYS2.SYSCOLUMNS
```

**Detection:**
- JDBC URL: `jdbc:as400://host`
- Driver: `com.ibm.as400.access.AS400JDBCDriver` (JT400)
- Typical ports: 8471, 8475, 8476

### DB2 for z/OS (Mainframe)

Uses the SYSIBM catalog (classic DB2 on mainframe):

```sql
-- Tables
SELECT CREATOR AS TABLE_SCHEMA, NAME AS TABLE_NAME, REMARKS
FROM SYSIBM.SYSTABLES
WHERE TYPE IN ('T', 'V')

-- Columns
SELECT TBCREATOR AS TABLE_SCHEMA, TBNAME AS TABLE_NAME, 
       NAME AS COLUMN_NAME, COLTYPE AS TYPENAME, ...
FROM SYSIBM.SYSCOLUMNS
```

**Detection:**
- JDBC URL: `jdbc:db2://mainframe:446` (port 446 typical)
- JDBC URL with: `location=` parameter or `sysibm` in URL
- Driver: `com.ibm.db2.jcc.DB2Driver` (IBM JCC Driver)

### DB2 LUW (Linux/Unix/Windows)

Uses the SYSCAT catalog:

```sql
-- Tables  
SELECT TABSCHEMA, TABNAME, REMARKS
FROM SYSCAT.TABLES
WHERE TYPE IN ('T', 'V')

-- Columns
SELECT TABSCHEMA, TABNAME, COLNAME, TYPENAME, ...
FROM SYSCAT.COLUMNS
```

**Detection:**
- JDBC URL: `jdbc:db2://server:50000/database`
- Driver: `com.ibm.db2.jcc.DB2Driver` or other DB2 drivers
- Typical port: 50000

### DB2 for i (AS/400)

### PostgreSQL

Uses standard information_schema with PostgreSQL-specific enhancements:

```sql
-- Tables
SELECT table_schema, table_name, 
       obj_description((table_schema||'.'||table_name)::regclass) AS REMARKS
FROM information_schema.tables
WHERE table_schema NOT IN ('pg_catalog', 'information_schema')

-- Columns
SELECT table_schema, table_name, column_name, data_type, ...
FROM information_schema.columns
```

### MySQL / MariaDB

```sql
-- Tables
SELECT table_schema, table_name, table_comment AS REMARKS
FROM information_schema.tables
WHERE table_schema NOT IN ('mysql', 'information_schema', 'performance_schema', 'sys')

-- Columns
SELECT table_schema, table_name, column_name, data_type, ...
FROM information_schema.columns
```

### Oracle

```sql
-- Tables
SELECT owner, table_name,
       (SELECT comments FROM all_tab_comments ...) AS REMARKS
FROM all_tables
WHERE owner NOT IN ('SYS', 'SYSTEM', ...)

-- Columns
SELECT owner, table_name, column_name, data_type, ...
FROM all_tab_columns
```

### SQL Server

```sql
-- Tables
SELECT s.name AS TABLE_SCHEMA, t.name AS TABLE_NAME,
       CAST(ep.value AS VARCHAR(MAX)) AS REMARKS
FROM sys.tables t
INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
LEFT JOIN sys.extended_properties ep ...

-- Columns  
SELECT s.name, t.name, c.name, ty.name, ...
FROM sys.columns c
INNER JOIN sys.tables t ...
```

## Configuration Examples

### DB2 for i (AS/400, IBM i)

```bash
export DBUTILS_JDBC_PROVIDER="jt400"
export DBUTILS_JDBC_URL="jdbc:as400://myserver"
export DBUTILS_JDBC_USER="myuser"
export DBUTILS_JDBC_PASSWORD="mypassword"
```

### DB2 for z/OS (Mainframe)

```bash
export DBUTILS_JDBC_PROVIDER="db2zos"
export DBUTILS_JDBC_URL="jdbc:db2://mainframe.company.com:446/DB2PROD"
export DBUTILS_JDBC_USER="DBUSER"
export DBUTILS_JDBC_PASSWORD="secret"
# Or with location parameter
export DBUTILS_JDBC_URL="jdbc:db2://mainframe:5025/LOCATION=DB2PROD"
```

### DB2 LUW (Linux/Unix/Windows)

```bash
export DBUTILS_JDBC_PROVIDER="db2"
export DBUTILS_JDBC_URL="jdbc:db2://dbserver:50000/SAMPLE"
export DBUTILS_JDBC_USER="db2admin"
export DBUTILS_JDBC_PASSWORD="password"
```

### PostgreSQL

```bash
export DBUTILS_JDBC_PROVIDER="postgresql"
export DBUTILS_JDBC_URL="jdbc:postgresql://localhost:5432/mydb"
export DBUTILS_JDBC_USER="postgres"
export DBUTILS_JDBC_PASSWORD="secret"
```

### MySQL

```bash
export DBUTILS_JDBC_PROVIDER="mysql"
export DBUTILS_JDBC_URL="jdbc:mysql://localhost:3306/mydb"
export DBUTILS_JDBC_USER="root"
export DBUTILS_JDBC_PASSWORD="secret"
```

### Oracle

```bash
export DBUTILS_JDBC_PROVIDER="oracle"
export DBUTILS_JDBC_URL="jdbc:oracle:thin:@localhost:1521:orcl"
export DBUTILS_JDBC_USER="system"
export DBUTILS_JDBC_PASSWORD="oracle"
```

### SQL Server

```bash
export DBUTILS_JDBC_PROVIDER="sqlserver"
export DBUTILS_JDBC_URL="jdbc:sqlserver://localhost:1433;databaseName=mydb"
export DBUTILS_JDBC_USER="sa"
export DBUTILS_JDBC_PASSWORD="YourPassword123"
```

## Testing

Run the schema detector test to verify functionality:

```bash
python3 test_schema_detector.py
```

This will test:
- Database type detection from URLs and driver classes
- Query template generation for each database type
- Pagination clause construction
- Schema filtering

## Benefits

1. **Universal JDBC Support** - Works with any JDBC-compliant database
2. **Automatic Adaptation** - No manual configuration required
3. **Optimized Queries** - Uses database-specific metadata catalogs
4. **Consistent Interface** - Same Qt browser UI works with all databases
5. **System Schema Filtering** - Automatically hides system/internal schemas

## Migration Notes

### From DB2-only Code

The existing code hardcoded DB2 for i queries:

```python
# Old approach
sql = "SELECT * FROM QSYS2.SYSTABLES WHERE ..."
```

New approach automatically selects appropriate queries:

```python
# New approach
from dbutils.schema_detector import detect_database_type, get_schema_queries

db_type = detect_database_type(jdbc_url, driver_class)
tables_query, columns_query, schemas_query = get_schema_queries(db_type)
```

### Backward Compatibility

- Default behavior remains DB2 for i when no detection possible
- All existing DB2 functionality preserved
- No breaking changes to API

## Future Enhancements

Potential improvements:
- Catalog vs Schema distinction for SQL Server
- Database-specific data type mapping
- Constraint and index metadata queries
- Stored procedure/function browsing
- Extended properties for all object types
