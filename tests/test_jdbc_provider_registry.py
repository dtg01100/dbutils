import json

import pytest

from dbutils.jdbc_provider import JDBCProvider, ProviderRegistry, get_registry


def test_provider_registry_load_and_save(tmp_path, monkeypatch):
    # Use a temp config path
    cfg_file = tmp_path / 'providers.json'
    # Provide a minimal providers JSON
    initial = [
        {
            'name': 'Test',
            'driver_class': 'com.test.Driver',
            'jar_path': '/tmp/test.jar',
            'url_template': 'jdbc:test://{host}/{db}',
            'default_user': 'user',
            'default_password': 'pass',
        }
    ]
    cfg_file.write_text(json.dumps(initial))

    registry = ProviderRegistry(config_path=str(cfg_file))
    assert 'Test' in registry.list_names()

    # Add a new provider and save
    p = JDBCProvider(
        name='New',
        driver_class='com.example.Driver',
        jar_path='/tmp/a.jar',
        url_template='jdbc:ex:{host}',
    )
    registry.add_or_update(p)
    assert 'New' in registry.list_names()

    # Save and reload
    registry.save()
    r2 = ProviderRegistry(config_path=str(cfg_file))
    assert 'New' in r2.list_names()

    # Remove provider
    r2.remove('New')
    assert 'New' not in r2.list_names()


def test_get_registry_singleton(monkeypatch, tmp_path):
    # Ensure get_registry returns a singleton instance (but isolated via fresh process)
    cfg_file = tmp_path / 'providers.json'
    cfg_file.write_text(json.dumps([]))

    monkeypatch.setenv('DBUTILS_CONFIG_DIR', str(tmp_path))
    from dbutils import jdbc_provider
    # Reset _registry
    jdbc_provider._registry = None
    reg = get_registry()
    assert isinstance(reg, ProviderRegistry)


def test_connect_with_bad_provider_raises(monkeypatch, tmp_path):
    cfg_file = tmp_path / 'providers.json'
    cfg_file.write_text(json.dumps([]))
    monkeypatch.setenv('DBUTILS_CONFIG_DIR', str(tmp_path))
    from dbutils import jdbc_provider
    jdbc_provider._registry = None

    with pytest.raises(KeyError):
        jdbc_provider.connect('notfound', {}, None, None)
