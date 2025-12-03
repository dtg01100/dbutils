# JDBC Integration (Python + Qt)

This project now supports JDBC providers via JayDeBeApi + JPype (Python embedding the JVM) while keeping the Qt app (PySide6/PyQt6).

## How it works
- `src/dbutils/jdbc_provider.py` implements:
  - Provider registry persisted in `~/.config/dbutils/providers.json`
  - Connection wrapper using JayDeBeApi + JPype
  - Simple `query(sql) -> List[Dict]` returning rows as dicts
- `src/dbutils/gui/provider_config.py` provides a Qt dialog to manage providers.
- `src/dbutils/db_browser.py` prefers JDBC when environment variables are set, else falls back to the legacy external `query_runner`.

## Configure a provider
1. Launch the GUI and open Settings → "Manage JDBC Providers…"
2. Add your provider:
   - Name: any label
   - Driver Class: e.g., `com.ibm.db2.jcc.DB2Driver`, `org.h2.Driver`
   - JAR Path: path to the JDBC driver JAR
   - URL Template: e.g., `jdbc:db2://{host}:{port}/{database}`
   - Default User/Password: optional
3. The registry is saved to `~/.config/dbutils/providers.json`.

## Use JDBC at runtime
Set environment variables before launching:
- `DBUTILS_JDBC_PROVIDER`: provider name from registry
- `DBUTILS_JDBC_URL_PARAMS`: JSON string for template params, e.g. `{"host":"db.example","port":50000,"database":"SAMPLE"}`
- `DBUTILS_JDBC_USER` and `DBUTILS_JDBC_PASSWORD`: optional overrides

Example:
```
export DBUTILS_JDBC_PROVIDER="H2 (Embedded)"
export DBUTILS_JDBC_URL_PARAMS='{"database":"testdb"}'
/workspaces/dbutils/.venv/bin/python -m dbutils.gui.qt_app
```

## Flatpak notes
- Bundle an OpenJDK runtime and your JDBC JAR(s).
- Ensure JVM discovery works under Flatpak; JPype will need `JAVA_HOME` or a standard JRE path.
- Place JARs in an app-accessible directory and reference via absolute or app-relative paths in the provider configuration.
- Grant filesystem permissions for reading JARs if necessary.

## Dependencies
Added to `pyproject.toml`:
- `JPype1` and `JayDeBeApi` for JDBC
- Qt bindings remain as before (PySide6/PyQt6)

## Limitations
- Unit tests involving Qt may require system OpenGL (libEGL). In headless CI, skip GUI tests or use xvfb/OS packages to supply GL libraries.
- The external `query_runner` remains as a fallback when JDBC env vars are not set.
