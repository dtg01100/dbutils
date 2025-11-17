from dbutils.map_db import (
    build_schema_map,
    infer_relationships,
    mock_get_columns,
    mock_get_primary_keys,
    mock_get_tables,
)


def test_build_schema_map_with_mock():
    tables = mock_get_tables()
    columns = mock_get_columns()
    pks = mock_get_primary_keys()

    rels = infer_relationships(tables, columns, pks)
    assert isinstance(rels, list)
    assert len(rels) >= 2  # expect at least user and product references from ORDERS

    schema = build_schema_map(tables, columns, rels)
    assert "TEST.USERS" in schema
    assert "TEST.ORDERS" in schema
    assert "TEST.PRODUCTS" in schema

    orders_rels = schema["TEST.ORDERS"]["relationships"]
    parent_tables = {r["parent_table"] for r in orders_rels}
    assert "TEST.USERS" in parent_tables
    assert "TEST.PRODUCTS" in parent_tables


def test_empty_schema():
    # Test with empty inputs
    schema = build_schema_map([], [], [])
    assert schema == {}, "Empty inputs should produce empty schema"


def test_schema_with_no_relationships():
    # Test schema building when there are no relationships
    tables = mock_get_tables()
    columns = mock_get_columns()

    # Pass empty relationships list
    schema = build_schema_map(tables, columns, [])

    # All tables should be in schema but with no relationships
    assert "TEST.USERS" in schema
    assert "TEST.ORDERS" in schema
    assert "TEST.PRODUCTS" in schema

    # Each table should have columns but no relationships
    assert len(schema["TEST.USERS"]["columns"]) > 0
    assert len(schema["TEST.USERS"]["relationships"]) == 0
