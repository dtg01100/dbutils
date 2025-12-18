"""Compatibility module exposing DatabaseModel for GUI tests.

The core implementation lives in :mod:`dbutils.gui.qt_app` but some tests import
`dbutils.gui.database_model`. This thin wrapper re-exports the same class.
"""

from __future__ import annotations

from .qt_app import ColumnModel, DatabaseModel

__all__ = ["DatabaseModel", "ColumnModel"]
