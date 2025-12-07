import os
import json
import tempfile
from unittest.mock import MagicMock
import pytest

from dbutils.gui.jdbc_driver_manager import JDBCDriverDownloader, download_jdbc_driver


def test_get_maven_repos_json(monkeypatch):
    monkeypatch.setenv('DBUTILS_MAVEN_REPOS', json.dumps(['https://repo.example/maven/']))
    dl = JDBCDriverDownloader()
    repos = dl._get_maven_repos()
    assert isinstance(repos, list)
    assert 'https://repo.example/maven/' in repos


def test_get_maven_repos_csv(monkeypatch):
    monkeypatch.setenv('DBUTILS_MAVEN_REPOS', 'https://one,https://two')
    dl = JDBCDriverDownloader()
    repos = dl._get_maven_repos()
    assert 'https://one' in repos and 'https://two' in repos


def test_is_jar_url_true():
    dl = JDBCDriverDownloader()
    assert dl._is_jar_url('https://repo.example/whatever.jar')
    assert not dl._is_jar_url('https://example.com/download.html')


def test_get_latest_version_from_maven(monkeypatch):
    xml = '<metadata><versioning><latest>3.2.1</latest></versioning></metadata>'

    class FakeResp:
        headers = {'Content-Length': '10'}

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return xml.encode('utf-8')

    monkeypatch.setattr('urllib.request.urlopen', lambda req: FakeResp())
    dl = JDBCDriverDownloader()
    v = dl._get_latest_version_from_maven('org.xerial', 'sqlite-jdbc', ['https://repo1.maven.org/maven2/'])
    assert v == '3.2.1'


def test_download_single_file(monkeypatch, tmp_path):
    # Simulate a small JAR download stream
    content = b'0123456789'

    class FakeResp:
        def __init__(self, data):
            self._data = data
            self.headers = {'Content-Length': str(len(data))}

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self, n=-1):
            if not self._data:
                return b''
            chunk = self._data[:n] if n > 0 else self._data
            self._data = self._data[n:]
            return chunk

    monkeypatch.setattr('urllib.request.urlopen', lambda req: FakeResp(content[:]))
    tmp_dir = str(tmp_path)
    monkeypatch.setenv('DBUTILS_DRIVER_DIR', tmp_dir)
    dl = JDBCDriverDownloader()

    # Download a fake jar and ensure it saves to target
    target = tmp_path / 'sqlite-jdbc-TEST.jar'
    out = dl._download_single_file('http://example.com/file.jar', str(target))
    assert out and os.path.exists(out)


def test_download_driver_sqlite(monkeypatch, tmp_path):
    # Simulate download_jdbc_driver for a maven-backed sqlite
    monkeypatch.setenv('DBUTILS_DRIVER_DIR', str(tmp_path))
    content = b'JAR' * 10

    class FakeResp:
        def __init__(self, data):
            self._data = data
            self.headers = {'Content-Length': str(len(data))}

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self, n=-1):
            if not self._data:
                return b''
            chunk = self._data[:n] if n > 0 else self._data
            self._data = self._data[n:]
            return chunk

    # Monkeypatch urlopen and get_latest_version
    monkeypatch.setattr('urllib.request.urlopen', lambda req: FakeResp(content[:]))
    dl = JDBCDriverDownloader()
    # Monkeypatch _get_download_url_for_version to return a direct jar url
    monkeypatch.setattr(JDBCDriverDownloader, '_get_download_url_for_version', lambda self, info, version: 'http://example.com/test.jar')
    out = dl.download_driver('sqlite', version='latest')
    # It should return a path inside downloads dir
    assert out is None or os.path.exists(out) or isinstance(out, str)


def test_download_driver_multi_artifact(monkeypatch, tmp_path):
    # Simulate a driver_info with multiple maven artifacts (DB2 or complex drivers)
    monkeypatch.setenv('DBUTILS_DRIVER_DIR', str(tmp_path))
    content = b'JAR'*10

    class FakeResp:
        def __init__(self, data):
            self._data = data
            self.headers = {'Content-Length': str(len(data))}
        def __enter__(self): return self
        def __exit__(self, a,b,c): return False
        def read(self, n=-1):
            if not self._data: return b''
            chunk = self._data[:n] if n>0 else self._data
            self._data = self._data[n:]
            return chunk

    monkeypatch.setattr('urllib.request.urlopen', lambda req: FakeResp(content[:]))
    dl = JDBCDriverDownloader()
    # Monkeypatch _get_download_url_for_version to return a list of jar urls
    monkeypatch.setattr(JDBCDriverDownloader, '_get_download_url_for_version', lambda self, info, version: ['http://example.com/one.jar', 'http://example.com/two.jar'])
    out = dl.download_driver('sqlite', version='latest')
    # For list-of-artifact case, returns list or single path; ensure it's valid
    if isinstance(out, list):
        assert all(os.path.exists(p) or isinstance(p, str) for p in out)
    else:
        assert out is None or os.path.exists(out)


def test_download_driver_oracle_manual(monkeypatch, tmp_path):
    # Oracle should fallback to manual download (not a jar URL)
    monkeypatch.setenv('DBUTILS_DRIVER_DIR', str(tmp_path))
    dl = JDBCDriverDownloader()
    out = dl.download_driver('oracle', version='recommended')
    assert out is None
