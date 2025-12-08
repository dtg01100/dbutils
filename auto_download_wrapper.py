#!/usr/bin/env python3
"""
Auto-download wrapper for JDBC drivers.

This script provides a convenient way to get JDBC driver paths using
the auto-download system instead of hardcoded paths.
"""

import os
import sys

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from dbutils.gui.jdbc_provider_config import get_configured_provider


def get_jar_path_for_type(db_type: str) -> str:
    """Get the JAR path for a database type using auto-download system."""
    provider = get_configured_provider(db_type)
    if provider and "jar_path" in provider:
        return provider["jar_path"]
    else:
        # Fallback to auto-download marker
        return f"AUTO_DOWNLOAD_{db_type}"


def resolve_auto_download_paths():
    """Resolve all AUTO_DOWNLOAD_* paths to actual driver paths."""
    # This would be implemented in the actual system
    pass


if __name__ == "__main__":
    if len(sys.argv) > 1:
        db_type = sys.argv[1]
        print(get_jar_path_for_type(db_type))
    else:
        print("Usage: python auto_download_wrapper.py <database_type>")
        print("Supported types: sqlite, h2, derby, hsqldb, duckdb")
