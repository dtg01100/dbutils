"""Compatibility module exposing TableContentsModel for GUI tests.

The actual implementation resides in :mod:`dbutils.gui.qt_app`. This module
re-exports it so imports like ``from dbutils.gui.table_contents_model import
TableContentsModel`` continue to work.
"""

from __future__ import annotations

from .qt_app import TableContentsModel

__all__ = ["TableContentsModel"]
