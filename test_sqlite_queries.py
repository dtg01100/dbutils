#!/usr/bin/env python3
"""
Demonstrate queries to enumerate tables and columns for SQLite using Python's sqlite3.
This file is intentionally independent of JDBC and JPype — it's for developing and
verifying the exact SQL to use when we later translate to other JDBC providers.

What we'll show:
- Create sample tables (including foreign key, index)
- Query sqlite_master to list tables and views
- Use PRAGMA table_info to list columns, types, nullable, defaults, pk
- Use PRAGMA foreign_key_list to enumerate foreign keys
- Use PRAGMA index_list / index_info to enumerate indexes
"""

import sqlite3
import os
import sys

DB_FILE = os.environ.get("DBUTILS_SQLITE_FILE", ":memory:")


def create_sample_schema(conn):
    cur = conn.cursor()
    cur.executescript(
        """
        PRAGMA foreign_keys = ON;

        CREATE TABLE IF NOT EXISTS authors (
            author_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE
        );

        CREATE TABLE IF NOT EXISTS books (
            book_id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            author_id INTEGER NOT NULL,
            published_date TEXT,
            price REAL DEFAULT 0.0,
            FOREIGN KEY(author_id) REFERENCES authors(author_id)
        );

        CREATE INDEX IF NOT EXISTS idx_books_author ON books(author_id);
        """
    )
    conn.commit()


def list_tables(conn):
    """Return list of tables and views from sqlite_master."""
    cur = conn.cursor()
    cur.execute("SELECT name, type, sql FROM sqlite_master WHERE type IN ('table','view') ORDER BY name")
    return cur.fetchall()


def table_columns(conn, table_name):
    """Return columns using PRAGMA table_info (name, type, notnull, dflt_value, pk)."""
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info('{table_name}')")
    # PRAGMA table_info returns: cid, name, type, notnull, dflt_value, pk
    return cur.fetchall()


def foreign_keys(conn, table_name):
    cur = conn.cursor()
    cur.execute(f"PRAGMA foreign_key_list('{table_name}')")
    # Returns: id, seq, table, from, to, on_update, on_delete, match
    return cur.fetchall()


def indexes(conn, table_name):
    cur = conn.cursor()
    cur.execute(f"PRAGMA index_list('{table_name}')")
    idxs = cur.fetchall()
    result = []
    for idx in idxs:
        # idx returns seq, name, unique, origin, partial
        name = idx[1]
        cur.execute(f"PRAGMA index_info('{name}')")
        cols = cur.fetchall()  # seqno, cid, name
        result.append((idx, cols))
    return result


def count_rows(conn, table_name):
    cur = conn.cursor()
    cur.execute(f"SELECT COUNT(*) FROM {table_name}")
    return cur.fetchone()[0]


def main():
    print("=== SQLite schema iteration examples ===\n")
    conn = sqlite3.connect(DB_FILE)

    try:
        create_sample_schema(conn)

        print("Tables/views discovered in sqlite_master:")
        for name, typ, sql in list_tables(conn):
            print(f" - {name} (type={typ})")

        print("\nColumns for 'authors':")
        for row in table_columns(conn, 'authors'):
            cid, name, ctype, notnull, dflt_value, pk = row
            print(f"  - {name}: {ctype}, notnull={bool(notnull)}, default={dflt_value}, pk={bool(pk)}")

        print("\nColumns for 'books':")
        for row in table_columns(conn, 'books'):
            cid, name, ctype, notnull, dflt_value, pk = row
            print(f"  - {name}: {ctype}, notnull={bool(notnull)}, default={dflt_value}, pk={bool(pk)}")

        print("\nForeign keys for 'books':")
        for fk in foreign_keys(conn, 'books'):
            print(f"  - {fk}")

        print("\nIndexes for 'books':")
        for idx, cols in indexes(conn, 'books'):
            print(f"  - index: {idx}")
            for c in cols:
                print(f"      column: {c}")

        print("\nRow counts:")
        print(f"  authors = {count_rows(conn, 'authors')}")
        print(f"  books = {count_rows(conn, 'books')}")

    finally:
        conn.close()

    print('\n=== Done ===')


if __name__ == '__main__':
    main()
