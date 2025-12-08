"""Unit tests for dbutils GUI JDBC driver downloader functionality.

Tests for:
- JDBCDriverRegistry and driver information
- JDBCDriverDownloader class
- Download functionality (mocked)
- Driver directory management
- Driver installation process
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

from dbutils.gui.jdbc_driver_downloader import (
    JDBCDriverInfo,
    JDBCDriverRegistry,
    get_driver_directory,
    suggest_jar_filename,
)
from dbutils.gui.jdbc_driver_manager import (
    JDBCDriverDownloader,
    download_jdbc_driver,
    find_existing_jdbc_drivers,
    get_jdbc_driver_download_info,
)


class TestJDBCDriverInfo:
    """Test the JDBCDriverInfo NamedTuple."""

    def test_jdbc_driver_info_creation(self):
        """Test basic JDBCDriverInfo creation."""
        driver_info = JDBCDriverInfo(
            name="Test Driver",
            driver_class="com.test.Driver",
            download_url="https://example.com/driver.jar",
            alternative_urls=["https://alt.example.com"],
            license="MIT",
            min_java_version="8",
            description="Test driver",
            recommended_version="1.0.0",
        )

        assert driver_info.name == "Test Driver"
        assert driver_info.driver_class == "com.test.Driver"
        assert driver_info.download_url == "https://example.com/driver.jar"


class TestJDBCDriverRegistry:
    """Test the JDBCDriverRegistry functionality."""

    def test_drivers_loaded(self):
        """Test that drivers are properly loaded in the registry."""
        assert len(JDBCDriverRegistry.DRIVERS) > 0
        assert "postgresql" in JDBCDriverRegistry.DRIVERS
        assert "mysql" in JDBCDriverRegistry.DRIVERS

    def test_get_driver_info(self):
        """Test getting driver info by database type."""
        # Test direct lookup
        pg_info = JDBCDriverRegistry.get_driver_info("postgresql")
        assert pg_info is not None
        assert pg_info.driver_class == "org.postgresql.Driver"
        assert pg_info.name == "PostgreSQL JDBC Driver"

        # Test MySQL
        mysql_info = JDBCDriverRegistry.get_driver_info("mysql")
        assert mysql_info is not None
        assert mysql_info.driver_class == "com.mysql.cj.jdbc.Driver"

    def test_get_driver_info_case_insensitive(self):
        """Test that driver lookup is case insensitive."""
        info1 = JDBCDriverRegistry.get_driver_info("POSTGRESQL")
        info2 = JDBCDriverRegistry.get_driver_info("PostgreSQL")
        info3 = JDBCDriverRegistry.get_driver_info("postgresql")

        assert info1 == info2 == info3

    def test_get_driver_info_with_aliases(self):
        """Test that aliases work properly."""
        # Test PostgreSQL aliases
        pg_info = JDBCDriverRegistry.get_driver_info("postgres")
        assert pg_info is not None
        assert pg_info.driver_class == "org.postgresql.Driver"

        # Test MySQL/MariaDB
        mysql_info = JDBCDriverRegistry.get_driver_info("mysql")
        assert mysql_info is not None

        maria_info = JDBCDriverRegistry.get_driver_info("mariadb")
        assert maria_info is not None

        # Test SQL Server aliases
        sqlserver_info = JDBCDriverRegistry.get_driver_info("sqlserver")
        assert sqlserver_info is not None

        mssql_info = JDBCDriverRegistry.get_driver_info("mssql")
        assert mssql_info is not None

    def test_get_all_database_types(self):
        """Test getting all supported database types."""
        types = JDBCDriverRegistry.get_all_database_types()
        assert len(types) > 0
        assert "postgresql" in types
        assert "mysql" in types
        assert "h2" in types
        assert "jt400" in types  # AS400 support

    def test_get_jt400_driver_info(self):
        """Test getting JT400/AS400 driver info."""
        jt400_info = JDBCDriverRegistry.get_driver_info("jt400")
        assert jt400_info is not None
        assert jt400_info.driver_class == "com.ibm.as400.access.AS400JDBCDriver"
        assert jt400_info.name == "IBM Toolbox for Java (JT400) - AS400/IBM i"
        assert jt400_info.license == "IBM Public License"

    def test_get_driver_info_with_as400_aliases(self):
        """Test that AS400/JT400 aliases work properly."""
        # Test direct lookup
        jt400_info = JDBCDriverRegistry.get_driver_info("jt400")
        assert jt400_info is not None

        # Test AS400 alias
        as400_info = JDBCDriverRegistry.get_driver_info("as400")
        assert as400_info is not None
        assert as400_info.driver_class == "com.ibm.as400.access.AS400JDBCDriver"

        # Test case insensitive
        as400_upper_info = JDBCDriverRegistry.get_driver_info("AS400")
        assert as400_upper_info == as400_info

    def test_get_quick_download_links(self):
        """Test getting quick download links."""
        links = JDBCDriverRegistry.get_quick_download_links()
        assert "postgresql" in links
        assert "mysql" in links
        assert links["postgresql"].startswith("https://")
        assert links["mysql"].startswith("https://")


class TestDriverDirectory:
    """Test driver directory functionality."""

    def test_get_driver_directory_default(self):
        """Test getting default driver directory."""
        with patch.dict("os.environ", {}, clear=True):
            directory = get_driver_directory()
            expected = os.path.expanduser("~/.config/dbutils/drivers")
            assert directory == expected

    def test_get_driver_directory_custom(self, tmp_path):
        """Test getting custom driver directory from environment."""
        custom_dir = str(tmp_path / "custom" / "drivers" / "path")
        with patch.dict("os.environ", {"DBUTILS_DRIVER_DIR": custom_dir}):
            directory = get_driver_directory()
            assert directory == custom_dir

    def test_get_driver_directory_creates_path(self, tmp_path):
        """Test that driver directory is created if it doesn't exist."""
        custom_dir = tmp_path / "new" / "driver" / "path"
        with patch.dict("os.environ", {"DBUTILS_DRIVER_DIR": str(custom_dir)}):
            directory = get_driver_directory()
            assert directory == str(custom_dir)
            assert os.path.exists(custom_dir)


class TestSuggestJarFilename:
    """Test JAR filename suggestion functionality."""

    def test_suggest_postgresql_filename(self):
        """Test PostgreSQL JAR filename suggestion."""
        filename = suggest_jar_filename("postgresql", "42.6.0")
        assert filename == "postgresql-42.6.0.jar"

        filename_latest = suggest_jar_filename("postgresql", "latest")
        assert filename_latest == "postgresql-latest.jar"

    def test_suggest_mysql_filename(self):
        """Test MySQL JAR filename suggestion."""
        filename = suggest_jar_filename("mysql", "8.0.33")
        assert filename == "mysql-connector-java-8.0.33.jar"

        filename_latest = suggest_jar_filename("mysql", "latest")
        assert filename_latest == "mysql-connector-java-latest.jar"

    def test_suggest_mariadb_filename(self):
        """Test MariaDB JAR filename suggestion."""
        filename = suggest_jar_filename("mariadb", "3.1.4")
        assert filename == "mariadb-java-client-3.1.4.jar"

        filename_latest = suggest_jar_filename("mariadb", "latest")
        assert filename_latest == "mariadb-java-client-latest.jar"

    def test_suggest_oracle_filename(self):
        """Test Oracle JAR filename suggestion."""
        filename = suggest_jar_filename("oracle", "21.13.0.0")
        assert filename == "ojdbc21.13.0.0.jar"

        filename_latest = suggest_jar_filename("oracle", "latest")
        assert filename_latest == "ojdbc-latest.jar"

    def test_suggest_sqlserver_filename(self):
        """Test SQL Server JAR filename suggestion."""
        filename = suggest_jar_filename("sqlserver", "12.4.2.jre11")
        assert filename == "mssql-jdbc-12.4.2.jre11.jar"

        filename_latest = suggest_jar_filename("sqlserver", "latest")
        assert filename_latest == "mssql-jdbc-latest.jar"

    def test_suggest_generic_filename(self):
        """Test generic JAR filename suggestion."""
        filename = suggest_jar_filename("unknown_db", "1.0")
        assert filename == "unknown_db-jdbc-driver.jar"

    def test_suggest_jt400_filename(self):
        """Test JT400/AS400 JAR filename suggestion."""
        filename = suggest_jar_filename("jt400", "10.5")
        assert filename == "jtopen-10.5.jar"

        filename_latest = suggest_jar_filename("jt400", "latest")
        assert filename_latest == "jtopen-latest.jar"


class TestJDBCDriverDownloader:
    """Test the JDBCDriverDownloader class."""

    def test_downloader_initialization(self, tmp_path):
        """Test downloader initialization."""
        with patch.dict("os.environ", {"DBUTILS_DRIVER_DIR": str(tmp_path / "drivers")}):
            downloader = JDBCDriverDownloader()
            assert downloader.downloads_dir == str(tmp_path / "drivers")
            # The directory should be created during initialization
            assert os.path.exists(downloader.downloads_dir)

    def test_download_single_file_success(self, tmp_path, monkeypatch):
        """Test that the downloader's single-file download works end-to-end (mocked network)."""
        # Prepare downloader with custom dir
        with patch.dict("os.environ", {"DBUTILS_DRIVER_DIR": str(tmp_path / "drivers")}):
            downloader = JDBCDriverDownloader()

            # Create a fake response object compatible with urlopen
            class FakeResp:
                def __init__(self, data: bytes):
                    self._data = data
                    self._pos = 0
                    self.headers = {"Content-Length": str(len(data))}

                def read(self, size=-1):
                    if self._pos >= len(self._data):
                        return b""
                    if size == -1:
                        size = len(self._data) - self._pos
                    chunk = self._data[self._pos : self._pos + size]
                    self._pos += len(chunk)
                    return chunk

                def __enter__(self):
                    return self

                def __exit__(self, exc_type, exc, tb):
                    return False

            test_bytes = b"test-jar-bytes"

            def fake_urlopen(req):
                return FakeResp(test_bytes)

            monkeypatch.setattr("dbutils.gui.jdbc_driver_manager.urllib.request.urlopen", fake_urlopen)

            target = os.path.join(downloader.downloads_dir, "test.jar")
            result = downloader._download_single_file("https://example.com/test.jar", target)
            assert result == target
            assert os.path.exists(target)
            assert Path(target).read_bytes() == test_bytes

    def test_suggest_jar_filename_method(self):
        """Test the suggest_jar_filename method."""
        downloader = JDBCDriverDownloader()

        # Test different database types
        assert downloader._suggest_jar_filename("postgresql", "1.0") == "postgresql-1.0.jar"
        assert downloader._suggest_jar_filename("mysql", "2.0") == "mysql-connector-java-2.0.jar"
        # The Oracle driver in JDBCDriverDownloader does remove dots from version
        assert downloader._suggest_jar_filename("oracle", "3.0") == "ojdbc30.jar"
        # Test JT400/AS400 driver
        assert downloader._suggest_jar_filename("jt400", "10.5") == "jtopen-10.5.jar"

    def test_is_jar_url(self):
        """Test URL type detection."""
        downloader = JDBCDriverDownloader()

        # Test JAR URLs
        assert downloader._is_jar_url(
            "https://repo1.maven.org/maven2/org/postgresql/postgresql/42.6.0/postgresql-42.6.0.jar"
        )
        assert downloader._is_jar_url("http://example.com/driver.jar")

        # Test non-JAR URLs
        assert not downloader._is_jar_url("https://jdbc.postgresql.org/download.html")
        assert not downloader._is_jar_url("https://repo1.maven.org/maven2/org/postgresql/postgresql/")

    @patch("dbutils.gui.jdbc_driver_manager.JDBCDriverRegistry")
    def test_download_driver_unknown_type(self, mock_registry):
        """Test downloading driver for unknown database type."""
        mock_registry.DRIVERS.get.return_value = None

        downloader = JDBCDriverDownloader()
        result = downloader.download_driver("unknown_db")

        assert result is None

    @patch("dbutils.gui.jdbc_driver_manager.JDBCDriverRegistry")
    def test_download_driver_with_progress_callback(self, mock_registry, tmp_path):
        """Test downloading driver with progress callback."""
        # Mock driver info
        mock_driver_info = MagicMock()
        mock_driver_info.download_url = "https://example.com/driver.jar"
        mock_driver_info.recommended_version = "1.0.0"
        mock_driver_info.alternative_urls = []
        mock_registry.DRIVERS.get.return_value = mock_driver_info

        # Set up environment
        driver_dir = tmp_path / "drivers"
        with patch.dict("os.environ", {"DBUTILS_DRIVER_DIR": str(driver_dir)}):
            downloader = JDBCDriverDownloader()

            # Mock the download methods to avoid actual network calls
            with patch.object(downloader, "_is_jar_url", return_value=False):
                with patch.object(downloader, "_handle_complex_download", return_value=None):
                    progress_called = []

                    def progress_callback(downloaded, total):
                        progress_called.append((downloaded, total))

                    result = downloader.download_driver("test_db", on_progress=progress_callback)

                    # The result will be None because _handle_complex_download returns None
                    assert result is None

    def test_get_download_instructions(self, tmp_path):
        """Test getting download instructions."""
        driver_dir = tmp_path / "drivers"
        with patch.dict("os.environ", {"DBUTILS_DRIVER_DIR": str(driver_dir)}):
            downloader = JDBCDriverDownloader()

            instructions = downloader.get_download_instructions("postgresql")

            # Check that instructions contain expected information
            assert instructions is not None
            assert "JDBC Driver:" in instructions
            assert "org.postgresql.Driver" in instructions
            assert str(driver_dir) in instructions
            assert "Primary download:" in instructions

    def test_find_existing_drivers_empty(self, tmp_path):
        """Test finding existing drivers when none exist."""
        driver_dir = tmp_path / "drivers"
        driver_dir.mkdir()

        with patch.dict("os.environ", {"DBUTILS_DRIVER_DIR": str(driver_dir)}):
            downloader = JDBCDriverDownloader()

            # Initially no drivers
            existing = downloader.find_existing_drivers("postgresql")
            assert len(existing) == 0

    def test_find_existing_drivers_with_files(self, tmp_path):
        """Test finding existing drivers when files exist."""
        driver_dir = tmp_path / "drivers"
        driver_dir.mkdir()

        # Create some mock JAR files
        (driver_dir / "postgresql-42.6.0.jar").touch()
        (driver_dir / "mysql-connector-java-8.0.33.jar").touch()
        (driver_dir / "other-file.txt").touch()

        with patch.dict("os.environ", {"DBUTILS_DRIVER_DIR": str(driver_dir)}):
            downloader = JDBCDriverDownloader()

            pg_drivers = downloader.find_existing_drivers("postgresql")
            assert len(pg_drivers) == 1
            assert "postgresql-42.6.0.jar" in pg_drivers[0]

            mysql_drivers = downloader.find_existing_drivers("mysql")
            assert len(mysql_drivers) == 1
            assert "mysql-connector-java-8.0.33.jar" in mysql_drivers[0]

    def test_list_available_drivers(self, tmp_path):
        """Test listing all available drivers."""
        driver_dir = tmp_path / "drivers"
        driver_dir.mkdir()

        # Create some mock JAR files
        (driver_dir / "postgresql-42.6.0.jar").touch()
        (driver_dir / "mysql-connector-java-8.0.33.jar").touch()

        with patch.dict("os.environ", {"DBUTILS_DRIVER_DIR": str(driver_dir)}):
            downloader = JDBCDriverDownloader()

            all_drivers = downloader.list_available_drivers()
            assert len(all_drivers) == 2
            assert "postgresql-42.6.0.jar" in all_drivers
            assert "mysql-connector-java-8.0.33.jar" in all_drivers

    def test_get_download_url_for_version_maven(self, monkeypatch):
        """Ensure maven-based download URL generation returns artifact URLs."""
        downloader = JDBCDriverDownloader()

        # Patch _get_maven_repos to a predictable single repo
        monkeypatch.setattr(downloader, "_get_maven_repos", lambda: ["https://repo1.maven.org/maven2/"])
        # Patch metadata lookup to return a known version
        monkeypatch.setattr(downloader, "_get_latest_version_from_maven", lambda g, a, r: "42.6.0")

        # Use the registry to get postgresql info
        driver_info = JDBCDriverRegistry.DRIVERS["postgresql"]
        urls = downloader._get_download_url_for_version(driver_info, "latest")
        assert isinstance(urls, list)
        assert any("/org/postgresql/postgresql/42.6.0/postgresql-42.6.0.jar" in u for u in urls)

    def test_download_driver_multiple_artifacts(self, tmp_path, monkeypatch):
        """Test downloading multiple maven artifacts for a single driver.

        We simulate two artifacts and ensure both are downloaded and returned.
        """
        # Create a fake driver entry and patch the registry
        fake_info = JDBCDriverInfo(
            name="Multi Driver",
            driver_class="com.example.Multi",
            download_url="https://example.com",
            alternative_urls=[],
            license="MIT",
            min_java_version="8",
            description="Multi artifact driver",
            recommended_version="1.2.3",
            maven_artifacts=["com.example:lib1", "com.example:lib2"],
        )

        with patch.dict("dbutils.gui.jdbc_driver_downloader.JDBCDriverRegistry.DRIVERS", {"multi": fake_info}):
            with patch.dict("os.environ", {"DBUTILS_DRIVER_DIR": str(tmp_path / "drivers")}):
                downloader = JDBCDriverDownloader()

                # Make _get_maven_repos deterministic
                monkeypatch.setattr(downloader, "_get_maven_repos", lambda: ["https://repo1.maven.org/maven2/"])
                # Make metadata resolution return recommended version
                monkeypatch.setattr(downloader, "_get_latest_version_from_maven", lambda g, a, r: "1.2.3")

                # Mock urlopen to return jar bytes for any URL
                class FakeResp:
                    def __init__(self, data: bytes):
                        self._data = data
                        self._pos = 0
                        self.headers = {"Content-Length": str(len(data))}

                    def read(self, size=-1):
                        if self._pos >= len(self._data):
                            return b""
                        if size == -1:
                            size = len(self._data) - self._pos
                        chunk = self._data[self._pos : self._pos + size]
                        self._pos += len(chunk)
                        return chunk

                    def __enter__(self):
                        return self

                    def __exit__(self, exc_type, exc, tb):
                        return False

                test_bytes = b"multi-jar-contents"

                def fake_urlopen(req):
                    return FakeResp(test_bytes)

                monkeypatch.setattr("dbutils.gui.jdbc_driver_manager.urllib.request.urlopen", fake_urlopen)

                result = downloader.download_driver("multi")
                # For two artifacts, expect a list of two paths
                assert isinstance(result, list)
                assert len(result) == 2
                for p in result:
                    assert os.path.exists(p)
                    assert Path(p).read_bytes() == test_bytes


class TestConvenienceFunctions:
    """Test the convenience functions."""

    def test_download_jdbc_driver_function(self, tmp_path):
        """Test the download_jdbc_driver convenience function."""
        driver_dir = tmp_path / "drivers"
        with patch.dict("os.environ", {"DBUTILS_DRIVER_DIR": str(driver_dir)}):
            # Mock the actual download to avoid network calls
            with patch("dbutils.gui.jdbc_driver_manager.JDBCDriverDownloader.download_driver") as mock_download:
                mock_download.return_value = str(driver_dir / "test-driver.jar")

                result = download_jdbc_driver("postgresql")

                assert result is not None
                mock_download.assert_called_once_with("postgresql", None, "recommended")

    def test_get_jdbc_driver_download_info(self, tmp_path):
        """Test getting JDBC driver download info."""
        driver_dir = tmp_path / "drivers"
        with patch.dict("os.environ", {"DBUTILS_DRIVER_DIR": str(driver_dir)}):
            info = get_jdbc_driver_download_info("postgresql")

            assert info is not None
            assert "JDBC Driver:" in info
            assert "PostgreSQL JDBC Driver" in info

    def test_find_existing_jdbc_drivers(self, tmp_path):
        """Test finding existing JDBC drivers."""
        driver_dir = tmp_path / "drivers"
        driver_dir.mkdir()

        # Create a mock driver file
        (driver_dir / "postgresql-42.6.0.jar").touch()

        with patch.dict("os.environ", {"DBUTILS_DRIVER_DIR": str(driver_dir)}):
            # Mock the finder method
            with patch("dbutils.gui.jdbc_driver_manager.JDBCDriverDownloader.find_existing_drivers") as mock_find:
                mock_find.return_value = [str(driver_dir / "postgresql-42.6.0.jar")]

                result = find_existing_jdbc_drivers("postgresql")

                assert len(result) == 1
                mock_find.assert_called_once_with("postgresql")
