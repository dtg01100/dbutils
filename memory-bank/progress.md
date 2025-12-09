# Progress

## What works
- CLI/TUI tools for DB2 schema discovery and relationship inference (per README) with JDBC + Qt.
- Packaging via uv/setuptools; tests and lint workflows defined in AGENTS.md.

## Current work
- Introduce Homebrew tap distribution path and initialize Memory Bank documentation.

## Known gaps
- No published release tags; Homebrew formula will need an updated URL/sha once a release is cut.
- Homebrew formula will rely on Python dependencies pulled at build time; may require future vendoring or resource blocks for Homebrew-core compliance.
