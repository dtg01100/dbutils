# Active Context

## Current Status (Dec 9, 2025)
- **COMPLETED**: Homebrew tap distribution is ready. Users can now install via `brew tap dtg01100/dbutils && brew install dbutils`.
- **NEW**: SQLite JDBC auto-download now pulls required SLF4J dependencies, and the real JDBC integration test passes end-to-end without manual jar downloads.

## Work Summary
- Created v0.1.0 release tag pointing to current commit.
- Built Homebrew tap formula in `homebrew-dbutils/` using Python 3.13 virtualenv helper.
- Formula URL: `https://github.com/dtg01100/dbutils/archive/v0.1.0.tar.gz`
- SHA256: `ab8466e147e9d9c668bb983696d1ab98943c53b7e7d65dc552bbe46d3037770c`
- Updated main README with tap installation as primary distribution method.
- Added sqlite-specific multi-artifact download (sqlite-jdbc + slf4j-api + slf4j-simple) with env override `DBUTILS_SLF4J_VERSION`.
- Enhanced real SQLite JDBC test to bootstrap downloads, include dependencies on classpath, disable autocommit, and avoid nested BEGIN; test now passes.

## Next Steps (Future)
- Push `homebrew-dbutils/` to separate public repo (dtg01100/homebrew-dbutils) for users to tap from.
- Monitor for formula refinements (e.g., if Homebrew-core compliance requires changes).
- For each new version, update sha256 and URL in the formula.
