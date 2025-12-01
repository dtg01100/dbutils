"""
DB Utils Package

A comprehensive toolkit for DB2 database administration and analysis.
"""

from .db_browser import main as db_browser_main
from .db_analyze import main as db_analyze_main
from .db_diff import main as db_diff_main
from .db_health import main as db_health_main
from .db_indexes import main as db_indexes_main
from .db_inferred_orphans import main as db_inferred_orphans_main
from .db_inferred_ref_coverage import main as db_inferred_ref_coverage_main
from .db_relate import main as db_relate_main
from .db_search import main as db_search_main
from .db_table_sizes import main as db_table_sizes_main
from .map_db import main as map_db_main
from .main_launcher import main as smart_launcher_main

__all__ = [
    "db_browser_main",
    "db_analyze_main",
    "db_diff_main",
    "db_health_main",
    "db_indexes_main",
    "db_inferred_orphans_main",
    "db_inferred_ref_coverage_main",
    "db_relate_main",
    "db_search_main",
    "db_table_sizes_main",
    "map_db_main",
    "smart_launcher_main",
]
