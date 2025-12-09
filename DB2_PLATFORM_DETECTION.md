# DB2 Platform Detection

## Overview

The schema detector now distinguishes between three DB2 platforms, each with different system catalogs and characteristics:

1. **DB2 for i** (IBM i, AS/400) - Midrange platform
2. **DB2 for z/OS** (Mainframe) - Enterprise mainframe
3. **DB2 LUW** (Linux/Unix/Windows) - Distributed platform

## Key Differences

| Feature | DB2 for i | DB2 for z/OS | DB2 LUW |
|---------|-----------|--------------|---------|
| **Platform** | IBM i (AS/400) | z/OS Mainframe | Linux/Unix/Windows |
| **System Catalog** | QSYS2 | SYSIBM | SYSCAT |
| **Table View** | QSYS2.SYSTABLES | SYSIBM.SYSTABLES | SYSCAT.TABLES |
| **Column View** | QSYS2.SYSCOLUMNS | SYSIBM.SYSCOLUMNS | SYSCAT.COLUMNS |
| **Schema Column** | TABLE_SCHEMA | CREATOR | TABSCHEMA |
| **Table Column** | TABLE_NAME | NAME | TABNAME |
| **Typical Port** | 8471, 8475, 8476 | 446, 5025 | 50000 |
| **JDBC Driver** | JT400 (as400) | JCC | JCC or native |

## Detection Logic

### JDBC URL Detection

```
jdbc:as400://host               → DB2 for i
jdbc:db2://host:446/db           → DB2 for z/OS (port 446)
jdbc:db2://host/LOCATION=loc     → DB2 for z/OS (location parameter)
jdbc:db2://host:50000/db         → DB2 LUW (port 50000)
jdbc:db2://host:5xxx/db          → DB2 for i (4-digit port starting with 5, except 50000)
```

### Driver Class Detection

```
com.ibm.as400.access.AS400JDBCDriver  → DB2 for i (JT400)
com.ibm.db2.jcc.DB2Driver             → DB2 for z/OS (JCC typically mainframe)
```

### Environment Variable Override

```bash
export DBUTILS_DATABASE_TYPE="db2_zos"  # Force z/OS
export DBUTILS_DATABASE_TYPE="db2_i"    # Force i
export DBUTILS_DATABASE_TYPE="db2_luw"  # Force LUW
```

## SQL Query Differences

### Tables Query

**DB2 for i:**
```sql
SELECT TABLE_SCHEMA, TABLE_NAME, TABLE_TEXT AS REMARKS
FROM QSYS2.SYSTABLES
WHERE TABLE_TYPE IN ('T', 'P') AND SYSTEM_TABLE = 'N'
```

**DB2 for z/OS:**
```sql
SELECT CREATOR AS TABLE_SCHEMA, NAME AS TABLE_NAME, REMARKS
FROM SYSIBM.SYSTABLES  
WHERE TYPE IN ('T', 'V')
```

**DB2 LUW:**
```sql
SELECT TABSCHEMA AS TABLE_SCHEMA, TABNAME AS TABLE_NAME, REMARKS
FROM SYSCAT.TABLES
WHERE TYPE IN ('T', 'V')
```

### Columns Query

**DB2 for i:**
```sql
SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, 
       DATA_TYPE AS TYPENAME, LENGTH, NUMERIC_SCALE AS SCALE,
       IS_NULLABLE AS NULLS, COLUMN_TEXT AS REMARKS
FROM QSYS2.SYSCOLUMNS
```

**DB2 for z/OS:**
```sql
SELECT TBCREATOR AS TABLE_SCHEMA, TBNAME AS TABLE_NAME,
       NAME AS COLUMN_NAME, COLTYPE AS TYPENAME, 
       LENGTH, SCALE, NULLS, REMARKS
FROM SYSIBM.SYSCOLUMNS
```

**DB2 LUW:**
```sql
SELECT TABSCHEMA AS TABLE_SCHEMA, TABNAME AS TABLE_NAME,
       COLNAME AS COLUMN_NAME, TYPENAME,
       LENGTH, SCALE, NULLS, REMARKS
FROM SYSCAT.COLUMNS
```

## Common Pitfalls

### Port Numbers
- **Don't assume** port 50000 is DB2 for i just because it starts with '5'
- Port 50000 is the standard for **DB2 LUW**
- DB2 for i typically uses ports 8471-8476
- DB2 for z/OS often uses port 446 or 5025

### System Catalogs
- **DB2 for i**: Modern SQL services in QSYS2 (avoid older QSYS catalog)
- **DB2 for z/OS**: Classic SYSIBM catalog
- **DB2 LUW**: SYSCAT catalog (not SYSIBM)

### Column Naming
Each platform uses different column names:
- **i**: `TABLE_SCHEMA`, `TABLE_NAME`, `COLUMN_NAME`
- **z/OS**: `CREATOR`, `NAME` (tables), `TBCREATOR`, `TBNAME` (columns)
- **LUW**: `TABSCHEMA`, `TABNAME`, `COLNAME`

## Testing

Run the schema detector test to verify detection:

```bash
python3 test_schema_detector.py
```

Expected output:
```
✓ jdbc:as400://localhost           → db2_i
✓ jdbc:db2://mainframe:446         → db2_zos  
✓ jdbc:db2://mainframe:50000       → db2_luw
✓ com.ibm.as400.access.AS400JDBCDriver → db2_i
✓ com.ibm.db2.jcc.DB2Driver        → db2_zos
```

## Migration Notes

### From Legacy Code

Old code that assumed all DB2 = DB2 for i:

```python
# Old - assumes DB2 for i
sql = "SELECT * FROM QSYS2.SYSTABLES WHERE ..."
```

New code automatically detects platform:

```python
from dbutils.schema_detector import detect_database_type, get_schema_queries

db_type = detect_database_type(jdbc_url, driver_class)
tables_query, columns_query, _ = get_schema_queries(db_type)
# Uses QSYS2 for i, SYSIBM for z/OS, or SYSCAT for LUW
```

## References

- **DB2 for i**: [IBM i SQL Reference](https://www.ibm.com/docs/en/i/7.5?topic=reference-sql)
- **DB2 for z/OS**: [DB2 z/OS SQL Reference](https://www.ibm.com/docs/en/db2-for-zos)
- **DB2 LUW**: [DB2 LUW SQL Reference](https://www.ibm.com/docs/en/db2/11.5)
