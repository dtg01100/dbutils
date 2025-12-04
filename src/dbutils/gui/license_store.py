"""Persistent store for accepted JDBC driver licenses.

This file provides a tiny, filesystem-backed store used to remember which
vendor driver licenses the user has accepted. It stores a JSON file under
DBUTILS_CONFIG_DIR (or ~/.config/dbutils by default).
"""
import json
import os
from typing import Set


def _get_store_path() -> str:
    config_dir = os.environ.get('DBUTILS_CONFIG_DIR', os.path.expanduser('~/.config/dbutils'))
    os.makedirs(config_dir, exist_ok=True)
    return os.path.join(config_dir, 'accepted_licenses.json')


def load_accepted_licenses() -> Set[str]:
    path = _get_store_path()
    if not os.path.exists(path):
        return set()

    try:
        with open(path, 'r', encoding='utf-8') as fh:
            data = json.load(fh)
            if isinstance(data, list):
                return set(data)
            if isinstance(data, dict) and 'accepted' in data and isinstance(data['accepted'], list):
                return set(data['accepted'])
    except Exception:
        # If parsing fails, treat as empty
        return set()

    return set()


def save_accepted_licenses(keys: Set[str]) -> None:
    path = _get_store_path()
    try:
        with open(path, 'w', encoding='utf-8') as fh:
            json.dump(sorted(list(keys)), fh, indent=2)
    except Exception:
        # Best-effort only
        pass


def is_license_accepted(key: str) -> bool:
    return key in load_accepted_licenses()


def accept_license(key: str) -> None:
    keys = load_accepted_licenses()
    keys.add(key)
    save_accepted_licenses(keys)


def revoke_license(key: str) -> None:
    keys = load_accepted_licenses()
    if key in keys:
        keys.remove(key)
        save_accepted_licenses(keys)
