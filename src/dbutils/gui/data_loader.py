"""Lightweight data loader helper for GUI tests.

Provides a minimal `DataLoader` API used by tests that expect a module named
``dbutils.gui.data_loader``. This implementation keeps dependencies simple and
works with any DB-API 2.0 style connection (including jaydebeapi connections
used in E2E tests).
"""

from __future__ import annotations

from typing import Iterable, List, Sequence, Tuple


class DataLoader:
    """Minimal table loader returning column names and rows.

    This is intentionally small: tests only need to import the symbol and, in
    some cases, fetch table contents for verification.
    """

    def __init__(self, connection=None):
        self.connection = connection

    def load_table(self, connection, table_name: str, limit: int | None = None) -> Tuple[List[str], List[Sequence]]:
        """Load a table using a DB-API cursor, returning (columns, rows)."""
        conn = connection or self.connection
        if conn is None:
            raise ValueError("A DB-API connection is required")

        cur = conn.cursor()
        try:
            sql = f"SELECT * FROM {table_name}"
            if limit:
                sql += f" LIMIT {int(limit)}"
            cur.execute(sql)
            columns = [col[0] for col in (cur.description or [])]
            rows = cur.fetchall() or []
            return columns, rows
        finally:
            try:
                cur.close()
            except Exception:
                pass


__all__ = ["DataLoader"]
