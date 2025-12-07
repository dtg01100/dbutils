import json
import os
from pathlib import Path

import pytest


@pytest.mark.qt
def test_provider_config_dialog_add_provider(qapp, tmp_path, monkeypatch):
    # Set temporary config dir for providers
    monkeypatch.setenv('DBUTILS_CONFIG_DIR', str(tmp_path))
    # Import inside test to pick up env var
    from dbutils.gui.provider_config import ProviderConfigDialog
    from dbutils.jdbc_provider import ProviderRegistry

    # Ensure registry points at temporary dir
    cfg_path = Path(os.environ['DBUTILS_CONFIG_DIR']) / 'providers.json'
    # Start with empty providers
    cfg_path.write_text(json.dumps([]))

    dlg = ProviderConfigDialog()
    # Set form fields
    dlg.name_edit.setText('TestAdd')
    dlg.driver_edit.setText('com.test.Driver')
    dlg.jar_edit.setText('/tmp/test.jar')
    dlg.url_edit.setText('jdbc:test://{host}')
    dlg.user_edit.setText('u')
    dlg.pass_edit.setText('p')

    # Add provider
    dlg._on_add_update()

    # Providers should be saved in config
    registry = ProviderRegistry(config_path=str(cfg_path))
    assert 'TestAdd' in registry.list_names()
    p = registry.get('TestAdd')
    assert p.driver_class == 'com.test.Driver'
    assert p.default_user == 'u'
