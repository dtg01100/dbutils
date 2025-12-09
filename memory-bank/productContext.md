# Product Context

- Primary goal: simplify DB2 schema discovery and relationship inference through command-line utilities and an interactive TUI/GUI browser.
- Users: engineers needing quick schema insights, join snippets, health metrics, or cross-table searches over JDBC connections.
- Key experience goals: fast, scriptable CLI tools plus an optional Qt TUI/GUI experience with fuzzy search and schema filtering; resilient to varying catalog dialects; minimal manual configuration.
- Environment expectations: run against live JDBC-enabled databases; mocks used only for tests/development; configuration via environment variables (JDBC URL, credentials, driver paths).