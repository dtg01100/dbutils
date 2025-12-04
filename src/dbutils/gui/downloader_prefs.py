"""Persistent preferences for the JDBC downloader (repositories, defaults)."""
import json
import os
from typing import List


def _prefs_path() -> str:
    config_dir = os.environ.get('DBUTILS_CONFIG_DIR', os.path.expanduser('~/.config/dbutils'))
    os.makedirs(config_dir, exist_ok=True)
    return os.path.join(config_dir, 'downloader_prefs.json')


DEFAULT_REPOS = [
    "https://repo1.maven.org/maven2/",
    "https://repo.maven.apache.org/maven2/",
]


def load_prefs() -> dict:
    path = _prefs_path()
    if not os.path.exists(path):
        return {"maven_repos": DEFAULT_REPOS}

    try:
        with open(path, 'r', encoding='utf-8') as fh:
            data = json.load(fh)
            if 'maven_repos' in data and isinstance(data['maven_repos'], list):
                return data
    except Exception:
        pass

    return {"maven_repos": DEFAULT_REPOS}


def save_prefs(prefs: dict) -> None:
    path = _prefs_path()
    try:
        with open(path, 'w', encoding='utf-8') as fh:
            json.dump(prefs, fh, indent=2)
    except Exception:
        pass


def get_maven_repos() -> List[str]:
    return load_prefs().get('maven_repos', DEFAULT_REPOS)


def set_maven_repos(repos: List[str]) -> None:
    prefs = load_prefs()
    prefs['maven_repos'] = repos
    save_prefs(prefs)
