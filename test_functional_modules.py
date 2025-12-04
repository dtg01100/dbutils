#!/usr/bin/env python3
"""
Functional test suite for key dbutils modules
"""
import pytest
import sys
from pathlib import Path

# Add the src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from PySide6.QtWidgets import QApplication


class TestUtilsModule:
    """Test the utils module functionality."""
    
    def test_utils_import(self):
        """Test that utils module can be imported."""
        import dbutils.utils
        assert dbutils.utils is not None
    
    def test_query_runner_exists(self):
        """Test that query_runner function exists (the key function)."""
        import dbutils.utils
        # The query_runner function is the main export
        assert hasattr(dbutils.utils, 'query_runner')
        assert callable(dbutils.utils.query_runner)


class TestDBBrowserModule:
    """Test the db_browser module functionality."""
    
    def test_db_browser_import(self):
        """Test that db_browser module can be imported."""
        import dbutils.db_browser
        assert dbutils.db_browser is not None
        
        # Check for key functions
        assert hasattr(dbutils.db_browser, 'query_runner')
        assert callable(dbutils.db_browser.query_runner)


class TestJDBCAutoDownloader:
    """Test the JDBC auto-downloader functionality."""
    
    def test_coordinate_definitions(self):
        """Test that JDBC driver coordinates are properly defined."""
        from dbutils.gui.jdbc_auto_downloader import JDBC_DRIVER_COORDINATES
        
        assert isinstance(JDBC_DRIVER_COORDINATES, dict)
        assert len(JDBC_DRIVER_COORDINATES) > 0
        
        # Check that some expected database types are present
        expected_dbs = ['postgresql', 'mysql', 'mariadb', 'sqlserver', 'sqlite', 'h2']
        for db in expected_dbs:
            assert db in JDBC_DRIVER_COORDINATES, f"Missing {db} in coordinates"
            
            # Check structure of each coordinate entry
            coords = JDBC_DRIVER_COORDINATES[db]
            assert 'group_id' in coords
            assert 'artifact_id' in coords
            assert 'metadata_url' in coords


class TestJDBCProviderModule:
    """Test the JDBC provider module functionality."""
    
    def test_basic_jdbc_provider_structure(self):
        """Test basic structure of JDBC provider module."""
        # Import the module to check basic functionality
        try:
            from dbutils import jdbc_provider
            # Basic import test
            assert hasattr(jdbc_provider, 'JDBCProvider')
        except ImportError as e:
            # This might fail due to JVM/jaydebeapi requirements, which is acceptable
            print(f"JDBC provider import skipped: {e}")
            pytest.skip(f"JDBC provider import issue: {e}")


class TestMainComponents:
    """Test main application components."""
    
    def test_main_launcher_functionality(self):
        """Test main launcher has expected functions."""
        import dbutils.main_launcher
        
        # Check for the main function
        assert hasattr(dbutils.main_launcher, 'main')
        assert callable(dbutils.main_launcher.main)
        
        # Check for utility functions
        assert hasattr(dbutils.main_launcher, 'check_gui_availability')
        assert callable(dbutils.main_launcher.check_gui_availability)
        
        # Check for launch function
        assert hasattr(dbutils.main_launcher, 'launch_qt_interface')
        assert callable(dbutils.main_launcher.launch_qt_interface)


class TestDataClasses:
    """Test that dataclasses are working correctly."""
    
    def test_enhanced_jdbc_provider_dataclass(self):
        """Test JDBCProvider dataclass works properly."""
        from dbutils.enhanced_jdbc_provider import JDBCProvider
        
        # Create a provider instance
        provider = JDBCProvider(
            name="Test Provider",
            category="Test",
            driver_class="com.test.Driver",
            jar_path="/path/to/test.jar",
            url_template="jdbc:test://localhost:5432/testdb"
        )
        
        # Verify the attributes are set correctly
        assert provider.name == "Test Provider"
        assert provider.category == "Test"
        assert provider.driver_class == "com.test.Driver"
        assert provider.jar_path == "/path/to/test.jar"
        assert provider.url_template == "jdbc:test://localhost:5432/testdb"
        
        # Verify default values
        assert provider.default_host == "localhost"
        assert provider.default_port == 0
        assert provider.default_user is None
        assert provider.default_password is None


class TestDatabaseAnalysisModules:
    """Test various database analysis modules."""
    
    def test_db_analyze_import(self):
        # db_analyze is no longer part of the codebase; this test is obsolete.
        import pytest
        pytest.skip("db_analyze removed from project")
    
    def test_db_diff_import(self):
        # db_diff removed from project — skip test
        import pytest
        pytest.skip("db_diff removed from project")
    
    def test_db_health_import(self):
        # db_health removed from project — skip test
        import pytest
        pytest.skip("db_health removed from project")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])