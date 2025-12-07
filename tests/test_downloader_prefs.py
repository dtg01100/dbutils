import os
import json
import tempfile
from unittest.mock import MagicMock, patch
import pytest

from dbutils.gui.downloader_prefs import (
    load_prefs, save_prefs, get_maven_repos, set_maven_repos,
    validate_repository_url, validate_repositories, prioritize_repositories,
    _prefs_path
)

# Import test configuration
from conftest import get_test_config_manager

def test_load_prefs_default(tmp_path, monkeypatch):
    """Test loading preferences with default values when no file exists."""
    monkeypatch.setenv('DBUTILS_CONFIG_DIR', str(tmp_path))
    prefs = load_prefs()
    assert 'maven_repos' in prefs
    assert len(prefs['maven_repos']) > 0
    assert 'https://repo1.maven.org/maven2/' in prefs['maven_repos']

def test_load_prefs_existing_file(tmp_path, monkeypatch):
    """Test loading preferences from an existing file."""
    monkeypatch.setenv('DBUTILS_CONFIG_DIR', str(tmp_path))
    config_dir = tmp_path / '.config' / 'dbutils'
    config_dir.mkdir(parents=True, exist_ok=True)

    # Create a valid prefs file
    prefs_file = config_dir / 'downloader_prefs.json'
    test_prefs = {
        'maven_repos': ['https://custom.repo.com/maven2/', 'https://another.repo.com/'],
        'some_other_setting': 'value'
    }
    prefs_file.write_text(json.dumps(test_prefs))

    # Load preferences
    loaded_prefs = load_prefs()
    assert loaded_prefs['maven_repos'] == test_prefs['maven_repos']
    assert loaded_prefs['some_other_setting'] == 'value'

def test_load_prefs_corrupted_file(tmp_path, monkeypatch):
    """Test loading preferences from a corrupted file."""
    monkeypatch.setenv('DBUTILS_CONFIG_DIR', str(tmp_path))
    config_dir = tmp_path / '.config' / 'dbutils'
    config_dir.mkdir(parents=True, exist_ok=True)

    # Create a corrupted prefs file
    prefs_file = config_dir / 'downloader_prefs.json'
    prefs_file.write_text('not valid json content')

    # Should return default preferences
    loaded_prefs = load_prefs()
    assert 'maven_repos' in loaded_prefs
    assert len(loaded_prefs['maven_repos']) > 0

def test_save_prefs(tmp_path, monkeypatch):
    """Test saving preferences to file."""
    monkeypatch.setenv('DBUTILS_CONFIG_DIR', str(tmp_path))
    config_dir = tmp_path / '.config' / 'dbutils'
    config_dir.mkdir(parents=True, exist_ok=True)

    # Save preferences
    test_prefs = {
        'maven_repos': ['https://test.repo.com/maven2/'],
        'custom_setting': 'test_value'
    }
    save_prefs(test_prefs)

    # Verify file was created and contains correct data
    prefs_file = config_dir / 'downloader_prefs.json'
    assert prefs_file.exists()

    # Load and verify content
    loaded_prefs = load_prefs()
    assert loaded_prefs['maven_repos'] == test_prefs['maven_repos']
    assert loaded_prefs['custom_setting'] == 'test_value'

def test_get_maven_repos_default(tmp_path, monkeypatch):
    """Test getting default Maven repositories."""
    monkeypatch.setenv('DBUTILS_CONFIG_DIR', str(tmp_path))
    repos = get_maven_repos()
    assert isinstance(repos, list)
    assert len(repos) > 0
    assert 'https://repo1.maven.org/maven2/' in repos

def test_get_maven_repos_custom(tmp_path, monkeypatch):
    """Test getting custom Maven repositories."""
    monkeypatch.setenv('DBUTILS_CONFIG_DIR', str(tmp_path))
    config_dir = tmp_path / '.config' / 'dbutils'
    config_dir.mkdir(parents=True, exist_ok=True)

    # Set custom repositories
    custom_repos = ['https://custom1.repo.com/', 'https://custom2.repo.com/']
    prefs = {'maven_repos': custom_repos}
    save_prefs(prefs)

    # Get repositories
    repos = get_maven_repos()
    assert repos == custom_repos

def test_set_maven_repos(tmp_path, monkeypatch):
    """Test setting Maven repositories."""
    monkeypatch.setenv('DBUTILS_CONFIG_DIR', str(tmp_path))
    config_dir = tmp_path / '.config' / 'dbutils'
    config_dir.mkdir(parents=True, exist_ok=True)

    # Set new repositories
    new_repos = ['https://new1.repo.com/', 'https://new2.repo.com/']
    set_maven_repos(new_repos)

    # Verify repositories were set
    repos = get_maven_repos()
    assert repos == new_repos

def test_validate_repository_url_valid():
    """Test validation of valid repository URLs."""
    # Test valid HTTPS URL
    valid, message = validate_repository_url('https://repo1.maven.org/maven2/')
    assert valid
    assert 'valid and accessible' in message.lower() or 'valid' in message.lower()

    # Test valid HTTP URL
    valid, message = validate_repository_url('http://repo.example.com/maven2/')
    assert valid
    assert 'valid and accessible' in message.lower() or 'valid' in message.lower()

def test_validate_repository_url_invalid():
    """Test validation of invalid repository URLs."""
    # Test empty URL
    valid, message = validate_repository_url('')
    assert not valid
    assert 'empty' in message.lower()

    # Test URL without protocol
    valid, message = validate_repository_url('repo.example.com/maven2/')
    assert not valid
    assert 'http' in message.lower()

    # Test invalid URL format
    valid, message = validate_repository_url('not-a-url')
    assert not valid

def test_validate_repository_url_unreachable():
    """Test validation of unreachable repository URLs."""
    # Test with a URL that should be unreachable
    valid, message = validate_repository_url('https://this-should-not-exist-12345.invalid/')
    assert not valid
    assert 'unreachable' in message.lower() or 'error' in message.lower()

def test_validate_repositories_mixed(tmp_path, monkeypatch):
    """Test validation of a mixed list of repository URLs."""
    monkeypatch.setenv('DBUTILS_CONFIG_DIR', str(tmp_path))

    # Test with a mix of valid and invalid URLs
    repos = [
        'https://repo1.maven.org/maven2/',
        'invalid-url',
        'https://another-valid-repo.com/',
        ''
    ]

    results = validate_repositories(repos)

    # Should have results for non-empty URLs
    assert len(results) == 3  # Empty string should be skipped

    # Check that we have both valid and invalid results
    valid_count = sum(1 for _, valid, _ in results if valid)
    invalid_count = sum(1 for _, valid, _ in results if not valid)

    assert valid_count >= 1  # At least one valid (the maven.org one)
    assert invalid_count >= 1  # At least one invalid

def test_prioritize_repositories(tmp_path, monkeypatch):
    """Test repository prioritization based on connectivity and response time."""
    monkeypatch.setenv('DBUTILS_CONFIG_DIR', str(tmp_path))

    # Test with known good repositories
    repos = [
        'https://repo1.maven.org/maven2/',
        'https://repo.maven.apache.org/maven2/'
    ]

    # This test may take a moment as it tests actual connectivity
    prioritized = prioritize_repositories(repos)

    assert isinstance(prioritized, list)
    assert len(prioritized) > 0
    assert all(repo in repos for repo in prioritized)

def test_prioritize_repositories_with_invalid(tmp_path, monkeypatch):
    """Test repository prioritization with a mix of valid and invalid repos."""
    monkeypatch.setenv('DBUTILS_CONFIG_DIR', str(tmp_path))

    repos = [
        'https://repo1.maven.org/maven2/',
        'https://invalid-repo-12345.invalid/',
        'https://repo.maven.apache.org/maven2/'
    ]

    prioritized = prioritize_repositories(repos)

    # Should return only valid repositories
    assert isinstance(prioritized, list)
    assert len(prioritized) > 0
    assert 'https://invalid-repo-12345.invalid/' not in prioritized

def test_prefs_path_environment_variable(tmp_path, monkeypatch):
    """Test that prefs path respects environment variable."""
    custom_config_dir = tmp_path / 'custom_config'
    monkeypatch.setenv('DBUTILS_CONFIG_DIR', str(custom_config_dir))

    prefs_path = _prefs_path()
    assert str(custom_config_dir) in prefs_path
    assert 'downloader_prefs.json' in prefs_path

def test_prefs_path_default_location(tmp_path, monkeypatch):
    """Test default prefs path when no environment variable is set."""
    # Don't set DBUTILS_CONFIG_DIR to test default
    monkeypatch.delenv('DBUTILS_CONFIG_DIR', raising=False)

    prefs_path = _prefs_path()
    assert '.config/dbutils' in prefs_path
    assert 'downloader_prefs.json' in prefs_path

def test_save_prefs_error_handling(tmp_path, monkeypatch):
    """Test error handling when saving preferences fails."""
    monkeypatch.setenv('DBUTILS_CONFIG_DIR', str(tmp_path))
    config_dir = tmp_path / '.config' / 'dbutils'
    config_dir.mkdir(parents=True, exist_ok=True)

    # Make the config directory read-only to simulate permission error
    os.chmod(config_dir, 0o444)

    try:
        # This should not raise an exception due to error handling
        save_prefs({'maven_repos': ['https://test.com/']})
    finally:
        # Restore permissions
        os.chmod(config_dir, 0o755)

def test_load_prefs_error_handling(tmp_path, monkeypatch):
    """Test error handling when loading preferences fails."""
    monkeypatch.setenv('DBUTILS_CONFIG_DIR', str(tmp_path))
    config_dir = tmp_path / '.config' / 'dbutils'
    config_dir.mkdir(parents=True, exist_ok=True)

    # Create a file with invalid JSON structure
    prefs_file = config_dir / 'downloader_prefs.json'
    prefs_file.write_text('{"maven_repos": [}')  # Invalid JSON

    # Should return default preferences without crashing
    prefs = load_prefs()
    assert 'maven_repos' in prefs
    assert len(prefs['maven_repos']) > 0

def test_get_maven_repos_empty_file(tmp_path, monkeypatch):
    """Test getting Maven repositories from an empty preferences file."""
    monkeypatch.setenv('DBUTILS_CONFIG_DIR', str(tmp_path))
    config_dir = tmp_path / '.config' / 'dbutils'
    config_dir.mkdir(parents=True, exist_ok=True)

    # Create an empty prefs file
    prefs_file = config_dir / 'downloader_prefs.json'
    prefs_file.write_text('{}')

    # Should return default repositories
    repos = get_maven_repos()
    assert len(repos) > 0
    assert 'https://repo1.maven.org/maven2/' in repos

def test_set_maven_repos_empty_list(tmp_path, monkeypatch):
    """Test setting Maven repositories to an empty list."""
    monkeypatch.setenv('DBUTILS_CONFIG_DIR', str(tmp_path))
    config_dir = tmp_path / '.config' / 'dbutils'
    config_dir.mkdir(parents=True, exist_ok=True)

    # Set empty list
    set_maven_repos([])

    # Should return default repositories when getting
    repos = get_maven_repos()
    assert len(repos) > 0  # Should fall back to defaults

def test_validate_repositories_empty_list():
    """Test validation of an empty repository list."""
    repos = []
    results = validate_repositories(repos)
    assert results == []  # Empty list should return empty results

def test_validate_repositories_whitespace(tmp_path, monkeypatch):
    """Test validation of repository URLs with whitespace."""
    monkeypatch.setenv('DBUTILS_CONFIG_DIR', str(tmp_path))

    repos = ['  https://repo1.maven.org/maven2/  ', '  ']

    results = validate_repositories(repos)

    # Should handle whitespace properly
    assert len(results) == 1  # Only the non-whitespace URL should be processed
    assert results[0][0].strip() == 'https://repo1.maven.org/maven2/'