import json
from unittest.mock import MagicMock

from dbutils.enhanced_jdbc_provider import (
    EnhancedProviderRegistry,
    JDBCConnection,
    JDBCProvider,
    PredefinedProviderTemplates,
    QueryWorker,
)


def test_predefined_provider_templates():
    cats = PredefinedProviderTemplates.get_categories()
    assert "PostgreSQL" in cats
    tpl = PredefinedProviderTemplates.get_template("PostgreSQL")
    assert tpl and "driver_class" in tpl
    prov = PredefinedProviderTemplates.create_provider_from_template("PostgreSQL", "MyPG", host="localhost")
    assert prov.name == "MyPG"


def test_jdbc_connection_failure(monkeypatch):
    # Simulate missing jpype or failing getDefaultJVMPath
    prov = JDBCProvider(name="X", category="Generic", driver_class="", jar_path="", url_template="jdbc:x")
    # Monkeypatch jpype to simulate failure
    import sys

    fake_jpype = MagicMock()
    fake_jpype.isJVMStarted.return_value = False
    fake_jpype.getDefaultJVMPath.side_effect = RuntimeError("No JVM")
    monkeypatch.setitem(sys.modules, "jpype", fake_jpype)
    # Ensure jaydebeapi is also available to avoid NameError
    fake_jd = MagicMock()
    monkeypatch.setitem(sys.modules, "jaydebeapi", fake_jd)

    conn = JDBCConnection(prov)
    # Connect should return False and not raise
    rv = conn.connect()
    assert rv is False


def test_query_worker_success_and_cancel(monkeypatch):
    # Create a fake connection with a cursor
    class FakeCursor:
        description = [("ID",), ("NAME",)]

        def execute(self, sql):
            pass

        def fetchall(self):
            return [(1, "Alice"), (2, "Bob")]

        def close(self):
            pass

    class FakeConn:
        def cursor(self):
            return FakeCursor()

    worker = QueryWorker(FakeConn(), "select *")
    results = []
    errors = []

    worker.query_finished.connect(lambda r: results.append(r))
    worker.error_occurred.connect(lambda e: errors.append(e))

    # Run normal
    worker.run()
    assert len(results) == 1 and isinstance(results[0], list)

    # Test cancel
    worker2 = QueryWorker(FakeConn(), "select *")
    worker2.cancel()
    finished = []
    worker2.finished.connect(lambda: finished.append(True))
    worker2.run()
    assert finished == [True]


def test_enhanced_provider_registry_save_and_load(tmp_path):
    cfg = tmp_path / "cfg" / "providers.json"
    # Make sure directory exists
    cfg.parent.mkdir(parents=True, exist_ok=True)
    registry = EnhancedProviderRegistry(config_path=str(cfg))
    # Add a provider
    prov = JDBCProvider(name="TestProv", category="Generic")
    assert registry.add_provider(prov) is True
    # Duplicate add should be False
    assert registry.add_provider(prov) is False
    # Update provider
    prov2 = JDBCProvider(name="TestProv", category="Generic", driver_class="c")
    assert registry.update_provider(prov2) is True
    # Get and list
    p = registry.get_provider("TestProv")
    assert p.driver_class == "c"
    assert "TestProv" in [x.name for x in registry.list_providers()]
    # Remove
    assert registry.remove_provider("TestProv") is True
    assert registry.remove_provider("TestProv") is False


def test_predefined_templates_lookup():
    templates = PredefinedProviderTemplates.get_categories()
    assert "PostgreSQL" in templates

    tpl = PredefinedProviderTemplates.get_template("PostgreSQL")
    assert tpl is not None
    provider = PredefinedProviderTemplates.create_provider_from_template("PostgreSQL", "PG Test")
    assert isinstance(provider, JDBCProvider)
    assert provider.driver_class.startswith("org.postgresql.Driver")


def test_enhanced_provider_registry_save_load(tmp_path, monkeypatch):
    cfg = tmp_path / "jdbc_providers.json"
    # Create initial providers JSON to simulate existing config
    initial = [
        {
            "name": "Example DB2",
            "category": "DB2",
            "driver_class": "com.ibm.db2.jcc.DB2Driver",
            "jar_path": "/path/to/db2jcc.jar",
            "url_template": "jdbc:db2://{host}:{port}/{database}",
            "default_host": "localhost",
            "default_port": 50000,
            "default_database": "SAMPLE",
            "extra_properties": {"securityMechanism": "3"},
        }
    ]
    cfg.write_text(json.dumps(initial))

    reg = EnhancedProviderRegistry(config_path=str(cfg))
    # Default providers initialized
    names = [p.name for p in reg.list_providers()]
    assert len(names) >= 1

    # Add a new provider, save, reload
    p = JDBCProvider(
        name="UnitTest",
        category="Generic",
        driver_class="com.test.Driver",
        jar_path="/tmp/j.jar",
        url_template="jdbc:test://{host}",
    )
    added = reg.add_provider(p)
    assert added
    assert reg.get_provider("UnitTest").name == "UnitTest"

    reg2 = EnhancedProviderRegistry(config_path=str(cfg))
    assert "UnitTest" in [pp.name for pp in reg2.list_providers()]

    # Update provider
    p.default_database = "SAMPLE"
    assert reg.update_provider(p)
    assert reg.get_provider("UnitTest").default_database == "SAMPLE"

    # Remove provider
    assert reg.remove_provider("UnitTest")
    assert reg.get_provider("UnitTest") is None


def test_jdbc_connection_connect_disconnect(monkeypatch):
    from dbutils.enhanced_jdbc_provider import JDBCConnection, JDBCProvider

    # Create a sample provider
    prov = JDBCProvider(
        name="P",
        category="Generic",
        driver_class="com.test.Driver",
        jar_path="/tmp/jar",
        url_template="jdbc:test://{host}",
    )

    # Create a fake jaydebeapi that returns a connection object with close method
    class FakeConn:
        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

    class FakeJaydebeapi:
        def connect(self, driver_class, url, props):
            return FakeConn()

    class FakeJPype:
        @staticmethod
        def isJVMStarted():
            return True

    monkeypatch.setattr("dbutils.enhanced_jdbc_provider.jaydebeapi", FakeJaydebeapi())
    monkeypatch.setattr("dbutils.enhanced_jdbc_provider.jpype", FakeJPype())

    jc = JDBCConnection(prov, username=None, password=None)
    assert jc.connect() is True
    jc.disconnect()
