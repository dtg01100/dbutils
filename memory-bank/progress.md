# Progress

## What works
- CLI/TUI tools for DB2 schema discovery and relationship inference (per README) with JDBC + Qt.
- Packaging via uv/setuptools; tests and lint workflows defined in AGENTS.md.
- **NEW**: Homebrew tap distribution. Users can install via `brew tap dtg01100/dbutils && brew install dbutils`.

## Recent completion (Dec 9, 2025)
- Created v0.1.0 release tag with computed sha256.
- Built Homebrew tap formula in `homebrew-dbutils/` directory.
- Updated README with tap installation as primary method.
- Added comprehensive HOMEBREW_TAP.md guide for maintaining the formula.
- Initialized and committed git repo for tap (ready to push to dtg01100/homebrew-dbutils).
- Pushed all updates to GitHub (main repo now has v0.1.0 tag + Homebrew installation docs).

## Next steps (future)
- Push homebrew-dbutils tap repo to https://github.com/dtg01100/homebrew-dbutils (users can then `brew tap dtg01100/dbutils`).
- For each new version, update formula sha256 and URL in homebrew-dbutils repo.
- Monitor for Homebrew formula compliance issues or improvements.
