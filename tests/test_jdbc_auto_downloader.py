import os
import tempfile
import urllib.error
from unittest.mock import MagicMock
import pytest

from dbutils.gui.jdbc_auto_downloader import (
    get_latest_version_from_maven_metadata,
    get_jdbc_driver_url,
    download_jdbc_driver,
    get_driver_directory,
    list_installed_drivers,
    find_existing_drivers,
)


def test_get_latest_version_from_maven_metadata(monkeypatch):
    xml = '<metadata><versioning><latest>1.2.3</latest></versioning></metadata>'
    class FakeResp:
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc, tb):
            return False
        def read(self):
            return xml.encode('utf-8')

    monkeypatch.setattr('urllib.request.urlopen', lambda url: FakeResp())
    v = get_latest_version_from_maven_metadata('https://repo/maven')
    assert v == '1.2.3'


def test_get_jdbc_driver_url_latest(monkeypatch):
    # Monkeypatch get_latest_version_from_maven_metadata indirectly via urlopen
    xml = '<metadata><versioning><latest>9.8.7</latest></versioning></metadata>'
    class FakeResp:
        def __enter__(self): return self
        def __exit__(self, a, b, c): return False
        def read(self): return xml.encode('utf-8')

    monkeypatch.setattr('urllib.request.urlopen', lambda url: FakeResp())
    url = get_jdbc_driver_url('sqlite', 'latest')
    assert url and url.endswith('.jar')


def test_download_jdbc_driver_not_found(monkeypatch, tmp_path):
    # Simulate HTTPError 404
    def fake_urlopen(req):
        raise urllib.error.HTTPError(req.full_url, 404, 'Not Found', hdrs=None, fp=None)

    monkeypatch.setenv('DBUTILS_DRIVER_DIR', str(tmp_path))
    monkeypatch.setattr('urllib.request.urlopen', fake_urlopen)
    out = download_jdbc_driver('sqlite', version='latest', target_dir=str(tmp_path))
    assert out is None


def test_list_and_find_existing_drivers(tmp_path, monkeypatch):
    # Create fake driver files
    d1 = tmp_path / 'sqlite-jdbc-latest.jar'
    d1.write_bytes(b'fake')
    d2 = tmp_path / 'other.jar'
    d2.write_bytes(b'fake')
    monkeypatch.setenv('DBUTILS_DRIVER_DIR', str(tmp_path))
    ld = list_installed_drivers()
    assert 'sqlite-jdbc-latest.jar' in ld
    found = find_existing_drivers('sqlite')
    assert any('sqlite-jdbc' in p for p in found)
import os
import tempfile
import urllib.error
from pathlib import Path

import pytest

from dbutils.gui import jdbc_auto_downloader as jad


class DummyResponse:
    def __init__(self, data: bytes, headers: dict | None = None):
        self._data = data
        self._pos = 0
        self.headers = headers or {"Content-Length": str(len(data))}

    def read(self, size: int = -1):
        if size == -1:
            size = len(self._data) - self._pos
        if self._pos >= len(self._data):
            return b""
        chunk = self._data[self._pos:self._pos + size]
        self._pos += len(chunk)
        return chunk

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_get_jdbc_driver_url_constructs_maven_url(monkeypatch):
    # Force get_latest_version to return a known version so URL construction is stable
    monkeypatch.setattr(jad, 'get_latest_version_from_maven_metadata', lambda url: '3.42.0.0')

    url = jad.get_jdbc_driver_url('sqlite', 'latest')
    assert url is not None
    assert url.endswith('/org/xerial/sqlite-jdbc/3.42.0.0/sqlite-jdbc-3.42.0.0.jar')


def test_get_jdbc_driver_url_for_multiple_databases(monkeypatch):
    # Ensure URL construction works for a couple of other supported databases
    monkeypatch.setattr(jad, 'get_latest_version_from_maven_metadata', lambda url: '42.6.0')

    pg_url = jad.get_jdbc_driver_url('postgresql', 'latest')
    assert pg_url is not None
    assert '/org/postgresql/postgresql/42.6.0/postgresql-42.6.0.jar' in pg_url

    monkeypatch.setattr(jad, 'get_latest_version_from_maven_metadata', lambda url: '8.0.33')
    mysql_url = jad.get_jdbc_driver_url('mysql', 'latest')
    assert mysql_url is not None
    assert '/mysql/mysql-connector-java/8.0.33/mysql-connector-java-8.0.33.jar' in mysql_url


def test_get_jdbc_driver_url_returns_none_for_unknown():
    assert jad.get_jdbc_driver_url('this_is_not_supported', 'latest') is None


def test_get_latest_version_from_maven_metadata_parses_latest(monkeypatch):
    # Provide a small metadata XML blob and ensure parser returns the <latest> element
    xml = b"""
    <metadata>
      <groupId>org.xerial</groupId>
      <artifactId>sqlite-jdbc</artifactId>
      <versioning>
        <latest>3.42.0.0</latest>
        <release>3.42.0.0</release>
        <versions>
          <version>3.40.0.0</version>
          <version>3.41.0.0</version>
          <version>3.42.0.0</version>
        </versions>
      </versioning>
    </metadata>
    """

    def fake_urlopen(url):
        class R:
            def read(self):
                return xml
        return R()

    monkeypatch.setattr(jad.urllib.request, 'urlopen', fake_urlopen)

    latest = jad.get_latest_version_from_maven_metadata('https://example.com/maven-metadata.xml')
    assert latest == '3.42.0.0'


def test_download_jdbc_driver_success(monkeypatch, tmp_path):
    # Make download URL point to a test URL; monkeypatch urlopen to return a DummyResponse
    test_data = b'hello-jdbc-jar'
    def fake_urlopen(req):
        return DummyResponse(test_data)

    monkeypatch.setattr(jad, 'get_jdbc_driver_url', lambda db, v: 'https://example.com/sqlite-jdbc-3.42.0.0.jar')
    monkeypatch.setattr(jad.urllib.request, 'urlopen', fake_urlopen)

    # Use a custom driver dir
    driver_dir = tmp_path / 'drivers'
    monkeypatch.setenv('DBUTILS_DRIVER_DIR', str(driver_dir))

    result = jad.download_jdbc_driver('sqlite', '3.42.0.0')
    assert result is not None

    path = Path(result)
    assert path.exists()
    assert path.read_bytes() == test_data


def test_download_jdbc_driver_skips_if_exists(monkeypatch, tmp_path):
    # If the file already exists, download_jdbc_driver should return the existing path
    driver_dir = tmp_path / 'drivers'
    driver_dir.mkdir(parents=True)
    existing = driver_dir / 'sqlite-jdbc-3.42.0.0.jar'
    existing.write_text('already')

    monkeypatch.setenv('DBUTILS_DRIVER_DIR', str(driver_dir))
    # Ensure URL generation returns the same filename
    monkeypatch.setattr(jad, 'get_jdbc_driver_url', lambda db, v: str(existing))

    result = jad.download_jdbc_driver('sqlite', '3.42.0.0')
    assert result == str(existing)


def test_download_jdbc_driver_http_404(monkeypatch, tmp_path):
    # Simulate HTTP 404
    def raise_404(req):
        raise urllib.error.HTTPError(url=req.get_full_url() if hasattr(req, 'get_full_url') else str(req), code=404, msg='Not Found', hdrs=None, fp=None)

    monkeypatch.setattr(jad, 'get_jdbc_driver_url', lambda db, v: 'https://example.com/missing.jar')
    monkeypatch.setattr(jad.urllib.request, 'urlopen', raise_404)

    monkeypatch.setenv('DBUTILS_DRIVER_DIR', str(tmp_path / 'drivers'))

    result = jad.download_jdbc_driver('sqlite', '1.0.0')
    assert result is None
