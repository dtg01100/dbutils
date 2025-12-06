"""Persistent preferences for the JDBC downloader (repositories, defaults) with validation."""
import json
import os
import time
from typing import List, Tuple
import urllib.request
import urllib.error


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

def validate_repository_url(url: str) -> Tuple[bool, str]:
    """Validate a repository URL and test connectivity."""
    if not url.strip():
        return False, "URL cannot be empty"

    if not url.startswith(('http://', 'https://')):
        return False, "URL must start with http:// or https://"

    try:
        # Test connectivity with a simple HEAD request
        req = urllib.request.Request(url, method='HEAD')
        req.add_header('User-Agent', 'dbutils-repo-validator/1.0')
        with urllib.request.urlopen(req, timeout=5) as response:
            status_code = response.getcode()
            if status_code == 200:
                return True, f"Repository {url} is valid and accessible"
            else:
                return False, f"Repository {url} returned HTTP {status_code}"
    except urllib.error.URLError as e:
        return False, f"Repository {url} is unreachable: {e.reason}"
    except Exception as e:
        return False, f"Repository {url} validation error: {str(e)}"

def validate_repositories(repos: List[str]) -> List[Tuple[str, bool, str]]:
    """Validate a list of repository URLs."""
    results = []
    for repo in repos:
        if not repo.strip():
            continue
        valid, message = validate_repository_url(repo)
        results.append((repo, valid, message))
    return results

def prioritize_repositories(repos: List[str]) -> List[str]:
    """Prioritize repositories based on connectivity and response time."""
    # Test each repository and sort by response time
    repo_performance = []
    for repo in repos:
        if not repo.strip():
            continue

        try:
            start_time = time.time()
            req = urllib.request.Request(repo, method='HEAD')
            req.add_header('User-Agent', 'dbutils-repo-validator/1.0')
            with urllib.request.urlopen(req, timeout=5) as response:
                response_time = time.time() - start_time
                if response.getcode() == 200:
                    repo_performance.append((repo, response_time, True))
                else:
                    repo_performance.append((repo, response_time, False))
        except:
            repo_performance.append((repo, float('inf'), False))

    # Sort by response time (fastest first), then by success status
    repo_performance.sort(key=lambda x: (x[2], x[1]))
    return [repo for repo, _, _ in repo_performance if repo]
    save_prefs(prefs)
