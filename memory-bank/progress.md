# Progress

## What works
- CLI/TUI tools for DB2 schema discovery and relationship inference (per README) with JDBC + Qt.
- Packaging via uv/setuptools; tests and lint workflows defined in AGENTS.md.
- Homebrew tap distribution. Users can install via `brew tap dtg01100/dbutils && brew install dbutils`.
- SQLite JDBC auto-download now fetches required SLF4J dependencies; real JDBC integration test passes end-to-end.

## Recent completion (Dec 9, 2025)
- Created v0.1.0 release tag with computed sha256.
- Built Homebrew tap formula in `homebrew-dbutils/` directory.
- Updated README with tap installation as primary method.
- Added comprehensive HOMEBREW_TAP.md guide for maintaining the formula.
- Initialized and committed git repo for tap (ready to push to dtg01100/homebrew-dbutils).
- Added sqlite-specific multi-artifact download (sqlite-jdbc + slf4j-api + slf4j-simple) with env override `DBUTILS_SLF4J_VERSION`.
- Enhanced `test_sqlite_jdbc_real` to bootstrap downloads, include dependencies, disable autocommit, and fix transaction handling; test now passes via `uv run pytest tests/test_sqlite_jdbc_real.py -q`.

## Next steps (future)
- Push homebrew-dbutils tap repo to https://github.com/dtg01100/homebrew-dbutils (users can then `brew tap dtg01100/dbutils`).
- For each new version, update formula sha256 and URL in homebrew-dbutils repo.
- Monitor for Homebrew formula compliance issues or improvements.
