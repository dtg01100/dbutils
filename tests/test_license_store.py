import os
import json
from pathlib import Path
import pytest

from dbutils.gui import license_store


def test_license_store_persistence(tmp_path, monkeypatch):
    config_dir = tmp_path / '.config' / 'dbutils'
    monkeypatch.setenv('DBUTILS_CONFIG_DIR', str(config_dir))
    # Ensure empty
    license_store.revoke_license('oracle')
    assert not license_store.is_license_accepted('oracle')

    license_store.accept_license('oracle')
    assert license_store.is_license_accepted('oracle')

    # Revoke
    license_store.revoke_license('oracle')
    assert not license_store.is_license_accepted('oracle')


def test_license_store_corrupted_file(tmp_path, monkeypatch):
    config_dir = tmp_path / '.config' / 'dbutils'
    monkeypatch.setenv('DBUTILS_CONFIG_DIR', str(config_dir))
    config_dir.mkdir(parents=True, exist_ok=True)
    p = config_dir / 'accepted_licenses.json'
    p.write_text('not a json')
    # Should return empty set instead of raising
    assert not license_store.is_license_accepted('oracle')
