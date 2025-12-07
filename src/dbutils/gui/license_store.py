"""Persistent store for accepted JDBC driver licenses with expiration handling.

This file provides a filesystem-backed store used to remember which
vendor driver licenses the user has accepted, including expiration tracking
for commercial drivers. It stores a JSON file under DBUTILS_CONFIG_DIR
(or ~/.config/dbutils by default).
"""
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Optional


def _get_store_path() -> str:
    config_dir = os.environ.get('DBUTILS_CONFIG_DIR', os.path.expanduser('~/.config/dbutils'))
    os.makedirs(config_dir, exist_ok=True)
    return os.path.join(config_dir, 'accepted_licenses.json')


def load_accepted_licenses() -> Dict[str, dict]:
    """Load accepted licenses with expiration information."""
    path = _get_store_path()
    if not os.path.exists(path):
        return {}

    try:
        with open(path, 'r', encoding='utf-8') as fh:
            data = json.load(fh)
            if isinstance(data, dict):
                # Migrate old format if needed
                if 'accepted' in data and isinstance(data['accepted'], list):
                    # Convert old list format to new dict format
                    return {key: {'accepted': True} for key in data['accepted']}
                return data
            elif isinstance(data, list):
                # Convert old list format to new dict format
                return {key: {'accepted': True} for key in data}
    except Exception:
        # If parsing fails, treat as empty
        return {}

    return {}


def save_accepted_licenses(licenses: Dict[str, dict]) -> None:
    """Save accepted licenses with metadata."""
    path = _get_store_path()
    try:
        with open(path, 'w', encoding='utf-8') as fh:
            json.dump(licenses, fh, indent=2)
    except Exception:
        # Best-effort only
        pass


def is_license_accepted(key: str) -> bool:
    """Check if a license is accepted and not expired."""
    licenses = load_accepted_licenses()
    license_info = licenses.get(key, {})
    if not license_info.get('accepted', False):
        return False

    # Check expiration if present
    expiration_str = license_info.get('expiration')
    if expiration_str:
        try:
            expiration_date = datetime.fromisoformat(expiration_str)
            if datetime.now() > expiration_date:
                return False
        except (ValueError, TypeError):
            # Invalid expiration format, treat as not expired
            pass

    return True

def get_license_info(key: str) -> Optional[dict]:
    """Get detailed information about a license acceptance."""
    licenses = load_accepted_licenses()
    return licenses.get(key)

def get_all_license_info() -> Dict[str, dict]:
    """Get all license acceptance information."""
    return load_accepted_licenses()

def cleanup_expired_licenses() -> int:
    """Clean up expired licenses and return count removed."""
    licenses = load_accepted_licenses()
    expired_count = 0

    for key, license_info in list(licenses.items()):
        expiration_str = license_info.get('expiration')
        if expiration_str:
            try:
                expiration_date = datetime.fromisoformat(expiration_str)
                if datetime.now() > expiration_date:
                    del licenses[key]
                    expired_count += 1
            except (ValueError, TypeError):
                continue

    if expired_count > 0:
        save_accepted_licenses(licenses)

    return expired_count
    expiration_str = license_info.get('expiration')
    if expiration_str:
        try:
            expiration_date = datetime.fromisoformat(expiration_str)
            if datetime.now() > expiration_date:
                return False
        except (ValueError, TypeError):
            # Invalid expiration format, treat as not expired
            pass

    return True


def accept_license(key: str, expiration_days: Optional[int] = None) -> None:
    """Accept a license with optional expiration."""
    licenses = load_accepted_licenses()
    license_info = {
        'accepted': True,
        'accepted_date': datetime.now().isoformat()
    }

    if expiration_days:
        expiration_date = datetime.now() + timedelta(days=expiration_days)
        license_info['expiration'] = expiration_date.isoformat()

    licenses[key] = license_info
    save_accepted_licenses(licenses)


def revoke_license(key: str) -> None:
    """Revoke a license acceptance."""
    licenses = load_accepted_licenses()
    if key in licenses:
        del licenses[key]
        save_accepted_licenses(licenses)
