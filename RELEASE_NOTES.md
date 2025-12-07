RELEASE NOTES
=============

Summary of recent test-compatibility and robustness fixes (Dec 2025)

- data_loader_process: improved handling of compressed cache files. Reads/writes now use the file extension (.gz) to determine compression, enabling explicit control in tests. A test-mode environment variable (`DBUTILS_TEST_MODE`) remains available to toggle certain behaviors.
- jdbc_auto_downloader: improved resilience for network calls by trying `urlopen` with `timeout` and intelligently falling back to a `timeout`-less call if tests monkeypatch `urllib.request.urlopen`. Included more detailed status messages and increased compatibility with mocked license checks.
- jdbc_driver_manager: `_url_exists` now attempts a GET if HEAD fails and is robust to test monkeypatches that return either a boolean or (status, message) tuple.
- enhanced_jdbc_provider: added class-method compatibility for templates API so `PredefinedProviderTemplates.get_categories()` and friends work without instantiation.
- enhanced_widgets: added a compatibility shim to provide `Qt.EventType` (mapped to `QEvent.Type`) for bindings that don't expose `EventType`. Also added `BusyOverlay._create_painter()` factory method (overridable in tests) to support GUI painting assertions with MagicMocks.
- Tests: updated tests and helpers to use these features and updated mocks for better compatibility with various Python Qt bindings.

If you have further minor suggestions or want these changes split into more atomic PRs, I can do that.
