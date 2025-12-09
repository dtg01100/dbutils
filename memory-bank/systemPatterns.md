# System Patterns

- Packaging: Python project (pyproject.toml) using setuptools; Cython extension `dbutils.accelerated` compiled from `src/dbutils/fast_ops.pyx` with setup.py for extensions.
- Entry points: defined under `[project.scripts]` (`db-browser`, `db-browser-gui`) invoking `dbutils.main_launcher` and `dbutils.gui.qt_app`.
- Architecture: CLI utilities rely on JDBC via JPype1 + JayDeBeApi; Qt UI uses PySide6; optional PyQt6 dependency group. Caching and mock modes used for testing.
- Development workflows: use `uv` for dependency management and packaging; linting with Ruff; testing with pytest and `DBUTILS_TEST_MODE=1` to avoid GUI dialogs during automated runs.
- Repository docs include various performance/optimization and testing guides; no Homebrew packaging yet (current task to add a tap formula).
