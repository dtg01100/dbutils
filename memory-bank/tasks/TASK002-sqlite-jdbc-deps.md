# TASK002 - SQLite JDBC dependency handling

**Status:** Completed  
**Added:** 2025-12-09  
**Updated:** 2025-12-09

## Original Request
Automatically download and include SQLite JDBC driver with required dependencies (SLF4J), and make the real JDBC integration test run end-to-end without manual downloads.

## Thought Process
- The real SQLite JDBC test was failing due to missing SLF4J (`LoggerFactory`) and manual jar downloads were not acceptable.
- The JDBC driver manager should fetch transitive dependencies (slf4j-api/simple) alongside the sqlite driver.
- The integration test should bootstrap the environment (download jars) and manage JPype classpath including dependencies.
- SQLite JDBC autocommit behavior caused commit/transaction errors; need to disable autocommit and avoid nested BEGIN.

## Implementation Plan
- Add sqlite-specific download resolution that returns multiple artifacts (sqlite-jdbc + slf4j-api + slf4j-simple) using Maven repos, with env override for SLF4J version.
- Update downloader return typing and tests to accept multi-jar results.
- Enhance real SQLite JDBC test to use the downloader, assemble classpath, disable autocommit, and fix transaction handling.
- Re-run targeted test to confirm pass.

## Progress Tracking

**Overall Status:** Completed - 100%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 2.1 | Add multi-jar download support for sqlite dependencies | Completed | 2025-12-09 | Returns sqlite + slf4j-api + slf4j-simple from Maven repos |
| 2.2 | Update downloader tests for list outputs | Completed | 2025-12-09 | Adjusted sqlite link test to handle multi-path results |
| 2.3 | Make real sqlite JDBC test self-bootstrapping and transaction-safe | Completed | 2025-12-09 | Uses downloader, sets autocommit False, removes explicit BEGIN |
| 2.4 | Run targeted sqlite JDBC test | Completed | 2025-12-09 | `uv run pytest tests/test_sqlite_jdbc_real.py -q` passes |

## Progress Log
### 2025-12-09
- Implemented sqlite-specific URL generation returning sqlite-jdbc plus slf4j-api/simple artifacts from the first Maven repo; added SLF4J version env override `DBUTILS_SLF4J_VERSION`.
- Updated downloader typing and convenience function to allow list-of-paths; modified sqlite download link test to expect multi-jar results.
- Enhanced `test_sqlite_jdbc_real` to invoke the downloader, gather jars, set JPype classpath, disable autocommit, and avoid nested BEGIN for rollback test.
- Ran `uv run pytest tests/test_sqlite_jdbc_real.py -q` — 5 tests passed (1 deprecation warning from jaydebeapi/JPype).
- Ensured jars directory uses app-managed downloads instead of manual wget.
