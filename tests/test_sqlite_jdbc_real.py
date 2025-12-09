"""Real SQLite JDBC integration test.

This test uses the actual sqlite-jdbc.jar with JPype + JayDeBeApi to exercise
real JDBC operations (create/read/update/delete, transactions, constraints, and
binary data) against a temporary on-disk SQLite database.
"""

from __future__ import annotations

import os
import sqlite3
import tempfile
from pathlib import Path
from typing import Iterator

import pytest
from dbutils.gui.jdbc_driver_manager import JDBCDriverDownloader


@pytest.fixture(scope="module")
def sqlite_jdbc_env() -> dict:
    """Ensure sqlite JDBC env is available and start JVM if needed."""
    try:
        import jpype
        import jaydebeapi
    except ImportError as e:  # pragma: no cover - handled by skip
        pytest.skip(f"JDBC dependencies missing: {e}")

    driver_dir = Path(__file__).resolve().parent.parent / "jars"
    driver_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("DBUTILS_DRIVER_DIR", driver_dir.as_posix())

    # Collect existing jars (driver + slf4j deps) and download missing ones
    jar_paths: list[str] = []

    local_driver = driver_dir / "sqlite-jdbc.jar"
    if local_driver.exists():
        jar_paths.append(local_driver.as_posix())

    # Existing slf4j jars if present
    for pattern in ("slf4j-api-*.jar", "slf4j-simple-*.jar"):
        for jar in driver_dir.glob(pattern):
            jar_paths.append(jar.as_posix())

    downloader = JDBCDriverDownloader()
    downloaded = downloader.download_driver("sqlite", version="recommended")
    if downloaded:
        if isinstance(downloaded, list):
            jar_paths.extend(downloaded)
        else:
            jar_paths.append(downloaded)

    # De-duplicate while preserving order and ensure files exist
    deduped: list[str] = []
    seen = set()
    for p in jar_paths:
        if p and os.path.exists(p) and p not in seen:
            deduped.append(p)
            seen.add(p)

    if not deduped:  # pragma: no cover - environment guard
        pytest.skip("SQLite JDBC artifacts not available")

    # Ensure classpath contains all jars (safe no-op if JVM already started)
    try:
        for p in deduped:
            jpype.addClassPath(p)
    except Exception:
        pass

    # Locate JVM; skip if unavailable in environment
    try:
        jvm_path = jpype.getDefaultJVMPath()
    except Exception as e:  # pragma: no cover - environment guard
        pytest.skip(f"JVM not available: {e}")

    if not jvm_path or not os.path.exists(jvm_path):  # pragma: no cover - environment guard
        pytest.skip("JVM shared library not found (set JAVA_HOME)")

    if not jpype.isJVMStarted():
        # Start JVM with explicit path; convertStrings=False to preserve bytes
        jpype.startJVM(jvm_path, classpath=deduped, convertStrings=False)

    return {"jar_paths": deduped, "jpype": jpype, "jaydebeapi": jaydebeapi}


@pytest.fixture()
def jdbc_connection(sqlite_jdbc_env) -> Iterator[tuple]:
    """Create a fresh SQLite DB and return a JDBC connection to it."""
    jpype = sqlite_jdbc_env["jpype"]
    jaydebeapi = sqlite_jdbc_env["jaydebeapi"]
    jar_paths = sqlite_jdbc_env["jar_paths"]

    # Create a temp DB file
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    db_path = tmp.name

    # Connect via JDBC
    conn = jaydebeapi.connect(
        "org.sqlite.JDBC",
        f"jdbc:sqlite:{db_path}",
        {},
        jar_paths,
    )

    # Ensure we manage transactions explicitly
    try:
        conn.jconn.setAutoCommit(False)  # type: ignore[attr-defined]
    except Exception:
        pass

    # Bootstrap schema and seed data via JDBC
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            total REAL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """
    )
    cur.execute("INSERT INTO users (name, email) VALUES (?, ?)", ("Alice", "a@example.com"))
    cur.execute("INSERT INTO users (name, email) VALUES (?, ?)", ("Bob", "b@example.com"))
    cur.execute("INSERT INTO orders (user_id, total) VALUES (?, ?)", (1, 42.50))
    conn.commit()

    try:
        yield conn, db_path
    finally:
        try:
            conn.close()
        except Exception:
            pass
        try:
            os.remove(db_path)
        except OSError:
            pass


def test_real_jdbc_crud(jdbc_connection):
    conn, db_path = jdbc_connection
    print(f"\n[CRUD Test] Using SQLite DB: {db_path}")
    print(f"[CRUD Test] DB file exists: {os.path.exists(db_path)}")
    print(f"[CRUD Test] DB file size: {os.path.getsize(db_path)} bytes")
    cur = conn.cursor()

    # Create
    cur.execute("INSERT INTO users (name, email) VALUES (?, ?)", ("Carol", "c@example.com"))
    conn.commit()
    print(f"[CRUD Test] Inserted Carol; file size now: {os.path.getsize(db_path)} bytes")

    # Read
    cur.execute("SELECT name, email FROM users ORDER BY id")
    rows = cur.fetchall()
    print(f"[CRUD Test] Selected users: {rows}")
    assert len(rows) == 3
    assert rows[0][0] == "Alice"

    # Update
    cur.execute("UPDATE users SET name = ? WHERE email = ?", ("Bobbert", "b@example.com"))
    conn.commit()
    cur.execute("SELECT name FROM users WHERE email = ?", ("b@example.com",))
    result = cur.fetchall()[0][0]
    print(f"[CRUD Test] Updated Bob to: {result}")
    assert result == "Bobbert"

    # Delete
    cur.execute("DELETE FROM users WHERE email = ?", ("c@example.com",))
    conn.commit()
    cur.execute("SELECT COUNT(*) FROM users")
    final_count = cur.fetchall()[0][0]
    print(f"[CRUD Test] After delete, user count: {final_count}")
    assert final_count == 2


def test_real_jdbc_transactions_and_rollback(jdbc_connection):
    conn, db_path = jdbc_connection
    print(f"\n[Rollback Test] Using SQLite DB: {db_path}")
    cur = conn.cursor()

    # With autocommit disabled, each connection starts a transaction implicitly
    cur.execute("INSERT INTO orders (user_id, total) VALUES (?, ?)", (1, 99.99))
    cur.execute("SELECT COUNT(*) FROM orders")
    before = cur.fetchall()[0][0]
    print(f"[Rollback Test] Before rollback, order count: {before}")
    conn.rollback()
    cur.execute("SELECT COUNT(*) FROM orders")
    after = cur.fetchall()[0][0]
    print(f"[Rollback Test] After rollback, order count: {after}")
    assert before - 1 == after


def test_real_jdbc_parameter_types_and_blob(jdbc_connection):
    conn, db_path = jdbc_connection
    print(f"\n[Blob Test] Using SQLite DB: {db_path}")
    cur = conn.cursor()

    blob_data = b"\x00\x01\x02BLOB"
    cur.execute("CREATE TABLE files (id INTEGER PRIMARY KEY, name TEXT, data BLOB)")
    cur.execute("INSERT INTO files (name, data) VALUES (?, ?)", ("payload", blob_data))
    conn.commit()
    print(f"[Blob Test] Inserted blob data: {blob_data}")

    cur.execute("SELECT name, data FROM files WHERE name = ?", ("payload",))
    name, data = cur.fetchall()[0]
    print(f"[Blob Test] Retrieved name: {name}, data type: {type(data)}")
    assert name == "payload"
    # jaydebeapi returns memoryview for blobs; normalize
    if isinstance(data, memoryview):
        data = data.tobytes()
    print(f"[Blob Test] Retrieved blob data: {data}")
    assert data == blob_data


def test_real_jdbc_constraint_violation(jdbc_connection):
    conn, _ = jdbc_connection
    cur = conn.cursor()

    with pytest.raises(Exception):
        cur.execute("INSERT INTO users (name, email) VALUES (?, ?)", ("Dup", "a@example.com"))


def test_real_jdbc_metadata_inspection(jdbc_connection):
    conn, _ = jdbc_connection
    cur = conn.cursor()

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [r[0] for r in cur.fetchall()]
    assert {"orders", "users"}.issubset(set(tables))

    # Verify PRAGMA table_info works through JDBC
    cur.execute("PRAGMA table_info('users')")
    columns = [r[1] for r in cur.fetchall()]
    assert {"id", "name", "email", "created_at"}.issubset(set(columns))
