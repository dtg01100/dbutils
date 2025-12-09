"""
Test script to verify schema detector works correctly
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from dbutils.schema_detector import (
    detect_database_type,
    get_schema_queries,
    build_schema_filter,
    build_pagination_clause,
    DatabaseType,
)

def test_detection():
    """Test database type detection."""
    print("="*60)
    print("Testing Database Type Detection")
    print("="*60)
    
    test_cases = [
        ("jdbc:as400://localhost", None, DatabaseType.DB2_I),
        ("jdbc:db2://mainframe:446", None, DatabaseType.DB2_ZOS),
        ("jdbc:db2://mainframe:50000", None, DatabaseType.DB2_LUW),
        ("jdbc:postgresql://localhost:5432/mydb", None, DatabaseType.POSTGRESQL),
        ("jdbc:mysql://localhost:3306/mydb", None, DatabaseType.MYSQL),
        ("jdbc:oracle:thin:@localhost:1521:orcl", None, DatabaseType.ORACLE),
        ("jdbc:sqlserver://localhost:1433", None, DatabaseType.SQLSERVER),
        (None, "com.ibm.as400.access.AS400JDBCDriver", DatabaseType.DB2_I),
        (None, "com.ibm.db2.jcc.DB2Driver", DatabaseType.DB2_ZOS),
        (None, "org.postgresql.Driver", DatabaseType.POSTGRESQL),
        (None, "com.mysql.cj.jdbc.Driver", DatabaseType.MYSQL),
    ]
    
    for jdbc_url, driver_class, expected in test_cases:
        result = detect_database_type(jdbc_url, driver_class)
        status = "✓" if result == expected else "✗"
        print(f"{status} URL: {jdbc_url or 'None':50} Driver: {driver_class or 'None':30} => {result} (expected: {expected})")
    
    print()

def test_schema_queries():
    """Test getting schema queries for different database types."""
    print("="*60)
    print("Testing Schema Query Generation")
    print("="*60)
    
    db_types = [
        DatabaseType.DB2_I,
        DatabaseType.DB2_ZOS,
        DatabaseType.POSTGRESQL,
        DatabaseType.MYSQL,
        DatabaseType.ORACLE,
        DatabaseType.SQLSERVER,
    ]
    
    for db_type in db_types:
        print(f"\n{db_type.upper()}:")
        tables_q, columns_q, schemas_q = get_schema_queries(db_type)
        
        # Build actual query with filters
        schema_filter = build_schema_filter(db_type, "MYSCHEMA")
        pagination = build_pagination_clause(db_type, 10, 0)
        
        query = tables_q.format(schema_filter=schema_filter, pagination=pagination)
        
        # Show first 200 chars of formatted query
        print(f"  Tables query (excerpt): {query[:200]}...")
        print(f"  Schema filter: {schema_filter}")
        print(f"  Pagination: {pagination}")

def test_pagination():
    """Test pagination clause generation."""
    print("\n" + "="*60)
    print("Testing Pagination Clause Generation")
    print("="*60)
    
    test_cases = [
        (DatabaseType.POSTGRESQL, 10, 0),
        (DatabaseType.POSTGRESQL, 10, 20),
        (DatabaseType.MYSQL, 25, 0),
        (DatabaseType.DB2_I, 10, 0),
        (DatabaseType.DB2_I, 10, 50),
        (DatabaseType.DB2_ZOS, 10, 0),
        (DatabaseType.DB2_ZOS, 10, 50),
        (DatabaseType.ORACLE, 15, 0),
        (DatabaseType.SQLSERVER, 20, 100),
    ]
    
    for db_type, limit, offset in test_cases:
        clause = build_pagination_clause(db_type, limit, offset)
        print(f"  {db_type:15} LIMIT={limit:3} OFFSET={offset:3} => {clause}")

if __name__ == "__main__":
    test_detection()
    test_schema_queries()
    test_pagination()
    
    print("\n" + "="*60)
    print("✓ All tests completed!")
    print("="*60)
