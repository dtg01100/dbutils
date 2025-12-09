import io
import urllib.error
import urllib.request
from pathlib import Path

from dbutils.gui.jdbc_driver_manager import JDBCDriverDownloader


class DummyResponse:
    def __init__(self, status=200, data: bytes = b"", headers=None):
        self.status = status
        self._data = data
        self._fp = io.BytesIO(data)
        self.headers = headers or {}

    def read(self, n=-1):
        return self._fp.read(n)

    def geturl(self):
        return "dummy"

    def getheaders(self):
        return list(self.headers.items())

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        pass


def mock_urlopen_returning_jar(url, *args, **kwargs):
    # Handle urllib.request.Request objects by extracting full_url
    try:
        u = url.full_url
    except Exception:
        u = str(url)
    # Return a small jar response for sqlite and other jars
    if u.endswith(".jar"):
        return DummyResponse(status=200, data=b"fake-jar-content", headers={"Content-Length": "16"})
    # For metadata, return minimal xml if asked
    if "maven-metadata.xml" in str(url):
        xml = b"""<?xml version='1.0'?><metadata><versioning><latest>3.42.0.0</latest><release>3.42.0.0</release></versioning></metadata>"""
        return DummyResponse(status=200, data=xml, headers={"Content-Length": str(len(xml))})
    # Otherwise return a generic 200 HTML page
    return DummyResponse(status=200, data=b"<html>OK</html>", headers={"Content-Length": "13"})


def mock_urlopen_404(url, *args, **kwargs):
    # Raise HTTPError for jar URLs
    try:
        u = url.full_url
    except Exception:
        u = str(url)
    if u.endswith(".jar"):
        raise urllib.error.HTTPError(url, 404, "Not Found", hdrs=None, fp=None)
    # Return valid metadata
    if "maven-metadata.xml" in u:
        xml = b"""<?xml version='1.0'?><metadata><versioning><latest>8.0.33</latest><release>8.0.33</release></versioning></metadata>"""
        return DummyResponse(status=200, data=xml, headers={"Content-Length": str(len(xml))})
    # For vendor page return 200
    return DummyResponse(status=200, data=b"<html>OK</html>", headers={"Content-Length": "13"})


def test_mysql_falls_back_to_manual(tmp_path, monkeypatch, caplog):
    # Setup a temp driver dir
    driver_dir = tmp_path / "drivers"
    driver_dir.mkdir()
    monkeypatch.setenv("DBUTILS_DRIVER_DIR", str(driver_dir))

    downloader = JDBCDriverDownloader()

    # Ensure we use the recommended version and simulate jar 404
    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen_404)
    # force URL checks to report not-found for jar urls
    monkeypatch.setattr(JDBCDriverDownloader, "_url_exists", lambda self, u, timeout=10: False)
    # Force latest version discovery to return expected version
    monkeypatch.setattr(JDBCDriverDownloader, "_get_latest_version_from_maven", lambda self, g, a, r: "8.0.33")

    # mysql should return None because our constructed .jar URL 404s and we'll fallback to manual
    caplog.set_level("INFO")
    result = downloader.download_driver("mysql", version="8.0.33")
    assert result is None
    # Should have logged navigation instructions for manual download
    assert any("Navigate to:" in rec.getMessage() or "Navigate to:" in rec.message for rec in caplog.records)


def test_jt400_requires_manual(tmp_path, monkeypatch, caplog):
    driver_dir = tmp_path / "drivers"
    driver_dir.mkdir()
    monkeypatch.setenv("DBUTILS_DRIVER_DIR", str(driver_dir))

    downloader = JDBCDriverDownloader()

    # Simulate that metadata isn't found (no maven artifact) and vendor page is accessible
    def fake_latest(self, g, a, r):
        return None

    monkeypatch.setattr(JDBCDriverDownloader, "_get_latest_version_from_maven", fake_latest)
    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen_404)
    # Force url checks to return False to ensure manual fallback
    monkeypatch.setattr(JDBCDriverDownloader, "_url_exists", lambda self, u, timeout=10: False)

    # Should return None because we don't have a direct jar URL to download and vendor page is manual
    caplog.set_level("INFO")
    result = downloader.download_driver("jt400", version="recommended")
    assert result is None
    assert any("Navigate to:" in rec.getMessage() or "Navigate to:" in rec.message for rec in caplog.records)


def test_sqlite_downloads(tmp_path, monkeypatch):
    # SQLite has a maven artifact; simulate jar availability and ensure we can download it
    driver_dir = tmp_path / "drivers"
    driver_dir.mkdir()
    monkeypatch.setenv("DBUTILS_DRIVER_DIR", str(driver_dir))

    # Use our success mock that returns jar bytes
    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen_returning_jar)
    # Force url_exists to True so it will attempt download
    monkeypatch.setattr(JDBCDriverDownloader, "_url_exists", lambda self, u, timeout=10: True)
    downloader = JDBCDriverDownloader()
    res = downloader.download_driver("sqlite", version="3.42.0.0")
    # Should be path(s) and files should exist
    assert res is not None
    paths = res if isinstance(res, list) else [res]
    assert all(Path(p).exists() for p in paths)
    # All downloaded files should be in our driver_dir
    assert all(Path(p).parent == driver_dir for p in paths)
    # Clean up
    for p in paths:
        Path(p).unlink()
