# Tech Context

- Language: Python (>=3.13), with Cython extension.
- Dependencies: rich, PySide6 (GUI), JPype1, JayDeBeApi; optional dev extras include pytest, ruff, PyQt6.
- Build: `uv build` for packages; `uv run ruff check .` for linting; `uv run pytest` for tests; `uv run ruff format .` for formatting. Setup.py handles Cython extension compilation.
- Packaging: configured for uv/PEP 517 via setuptools; no existing release tags. Distribution currently via source checkout or uvx. Homebrew tap formula to be added.
- Runtime: JDBC drivers configured via environment variables (DBUTILS_DRIVER_DIR, DBUTILS_MAVEN_REPOS, DBUTILS_CONFIG_DIR). GUI requires Qt bindings. Tests rely on `DBUTILS_TEST_MODE=1`.
