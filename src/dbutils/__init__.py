"""DB Utils Package - Qt GUI Database Browser with JDBC Support

Focused on Qt GUI database browser application with JDBC connectivity.
"""

from .db_browser import main as db_browser_main
from .main_launcher import main as smart_launcher_main

# Import Qt GUI main lazily/optionally so environments without Qt can still use the library/tests
try:
    from .gui.qt_app import main as qt_gui_main
except Exception:  # ImportError or Qt not available

    def qt_gui_main(*args, **kwargs):  # type: ignore
        raise ImportError(
            "Qt GUI is not available. Install PySide6 to use db-browser GUI (pip install PySide6).",
        )


__all__ = [
    "db_browser_main",
    "qt_gui_main",
    "smart_launcher_main",
]
