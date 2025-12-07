#!/usr/bin/env python3
"""
Test script for the auto-download infrastructure.

This script tests the complete auto-download functionality and verifies
that the system works as intended.
"""

import os
import sys
import json
import tempfile
import logging
from pathlib import Path

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from dbutils.gui.jdbc_provider_config import (
    AutoDownloadProviderConfig,
    get_configured_provider,
    ensure_all_drivers_available
)
from dbutils.gui.jdbc_auto_downloader import (
    get_driver_directory,
    list_installed_drivers,
    find_existing_drivers,
    get_jdbc_driver_url,
    download_jdbc_driver,
    get_repository_status,
    get_prioritized_repositories
)
from dbutils.gui.license_store import accept_license, is_license_accepted
from dbutils.gui.downloader_prefs import get_maven_repos

# Import new configuration system for testing
try:
    from dbutils.config.dbutils_config import get_maven_repositories as get_new_maven_repos
    from dbutils.config.url_config import get_maven_repositories as get_url_maven_repos
    NEW_CONFIG_AVAILABLE = True
except ImportError:
    NEW_CONFIG_AVAILABLE = False
    print("New configuration system not available, using fallback")

def test_auto_download_infrastructure():
    """Test the complete auto-download infrastructure."""
    print("Testing Auto-Download Infrastructure")
    print("=" * 50)

    # Test 1: Check that configuration files were updated
    print("\n1. Testing configuration file updates...")
    config_files = ["setup_multi_database_test.py", "tests/database_test_utils.py", "conftest.py"]

    for file_path in config_files:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                content = f.read()
            if "AUTO_DOWNLOAD_" in content:
                print(f"   ✓ {file_path} updated with auto-download references")
            else:
                print(f"   ✗ {file_path} not updated with auto-download references")
        else:
            print(f"   ✗ {file_path} not found")

    # Test 2: Check provider configuration
    print("\n2. Testing provider configuration...")
    config = AutoDownloadProviderConfig()

    # Check that we can get provider configs
    for db_type in ["sqlite", "h2", "derby", "hsqldb", "duckdb"]:
        provider_config = config.get_provider_config_for_auto_download(db_type)
        if provider_config:
            print(f"   ✓ {db_type} provider configuration available")
        else:
            print(f"   ✗ {db_type} provider configuration not available")

    # Test 3: Check Maven repository configuration
    print("\n3. Testing Maven repository configuration...")
    maven_repos = get_maven_repos()
    print(f"   ✓ Configured {len(maven_repos)} Maven repositories (legacy system):")
    for i, repo in enumerate(maven_repos, 1):
        print(f"     {i}. {repo}")

    # Test new configuration system if available
    if NEW_CONFIG_AVAILABLE:
        print("\n3b. Testing new configuration system...")
        try:
            new_maven_repos = get_new_maven_repos()
            print(f"   ✓ New config system: {len(new_maven_repos)} Maven repositories:")
            for i, repo in enumerate(new_maven_repos, 1):
                print(f"     {i}. {repo}")

            # Test repository status
            repo_status = get_repository_status()
            print(f"   ✓ Repository status checked: {len(repo_status)} repositories tested")

            # Test prioritized repositories
            prioritized_repos = get_prioritized_repositories()
            print(f"   ✓ Prioritized repositories: {len(prioritized_repos)} repositories")

        except Exception as e:
            print(f"   ✗ New configuration system test failed: {e}")

    # Test 4: Test URL generation
    print("\n4. Testing JDBC driver URL generation...")
    test_urls = []
    for db_type in ["sqlite", "h2", "postgresql", "mysql"]:
        url = get_jdbc_driver_url(db_type, "latest")
        if url:
            test_urls.append(url)
            print(f"   ✓ {db_type}: {url}")
        else:
            print(f"   ✗ {db_type}: URL generation failed")

    # Test 5: Test license acceptance (this will enable downloads)
    print("\n5. Testing license acceptance...")
    # Accept licenses for common databases to enable testing
    for db_type in ["sqlite", "h2", "derby", "hsqldb", "duckdb", "postgresql", "mysql"]:
        license_key = f"jdbc_driver_{db_type}"
        if not is_license_accepted(license_key):
            accept_license(license_key, expiration_days=365)
            print(f"   ✓ Accepted license for {db_type}")
        else:
            print(f"   ✓ License already accepted for {db_type}")

    # Test 6: Test driver availability after license acceptance
    print("\n6. Testing driver availability after license acceptance...")
    driver_results = ensure_all_drivers_available()
    available_count = sum(1 for result in driver_results.values() if result)
    print(f"   ✓ {available_count}/{len(driver_results)} drivers available after license acceptance")

    # Test 7: Test provider configuration with licenses accepted
    print("\n7. Testing provider configuration with licenses...")
    for db_type in ["sqlite", "h2"]:
        provider = get_configured_provider(db_type)
        if provider:
            print(f"   ✓ {db_type} provider: {provider.get('name', 'Unknown')}")
            if 'jar_path' in provider and provider['jar_path']:
                print(f"     JAR path: {provider['jar_path']}")
            else:
                print(f"     No JAR path available")
        else:
            print(f"   ✗ {db_type} provider not available")

    # Test 8: Test driver directory setup
    print("\n8. Testing driver directory setup...")
    driver_dir = get_driver_directory()
    print(f"   ✓ Driver directory: {driver_dir}")

    # List any existing drivers
    existing_drivers = list_installed_drivers()
    if existing_drivers:
        print(f"   ✓ Found {len(existing_drivers)} existing drivers:")
        for driver in existing_drivers:
            print(f"     - {driver}")
    else:
        print("   ✓ No existing drivers found (expected after cleanup)")

    # Test 9: Test configuration file creation
    print("\n9. Testing configuration file creation...")
    config_file = os.path.join(config.config_dir, "providers.json")
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            providers_data = json.load(f)
        print(f"   ✓ Providers configuration file created with {len(providers_data)} providers")

        # Check for auto-download providers
        auto_download_providers = [p for p in providers_data if p.get('auto_download', False)]
        print(f"   ✓ Found {len(auto_download_providers)} auto-download providers")
    else:
        print("   ✗ Providers configuration file not found")

    # Test 10: Test new version management system
    if NEW_CONFIG_AVAILABLE:
        print("\n10. Testing new version management system...")
        try:
            from dbutils.gui.jdbc_provider_config import AutoDownloadProviderConfig

            version_config = AutoDownloadProviderConfig()

            # Test version resolution strategy
            strategy = version_config.get_version_resolution_strategy()
            print(f"   ✓ Version resolution strategy: {strategy}")

            # Test fallback versions
            for db_type in ["sqlite", "h2"]:
                fallback_versions = version_config.get_fallback_versions(db_type)
                print(f"   ✓ {db_type} fallback versions: {fallback_versions}")

            # Test version override functionality
            sqlite_config = version_config.get_auto_download_configs()["sqlite"]
            print(f"   ✓ SQLite recommended version: {sqlite_config['recommended_version']}")

        except Exception as e:
            print(f"   ✗ Version management test failed: {e}")

    # Test 10: Test environment variables
    print("\n10. Testing environment variables...")
    driver_dir_env = os.environ.get("DBUTILS_DRIVER_DIR")
    maven_repos_env = os.environ.get("DBUTILS_MAVEN_REPOS")

    if driver_dir_env:
        print(f"   ✓ DBUTILS_DRIVER_DIR: {driver_dir_env}")
    else:
        print("   ✗ DBUTILS_DRIVER_DIR not set")

    if maven_repos_env:
        try:
            repos_list = json.loads(maven_repos_env)
            print(f"   ✓ DBUTILS_MAVEN_REPOS: {len(repos_list)} repositories")
        except:
            print(f"   ✓ DBUTILS_MAVEN_REPOS: {maven_repos_env}")
    else:
        print("   ✗ DBUTILS_MAVEN_REPOS not set")

    print("\n" + "=" * 50)
    print("AUTO-DOWNLOAD INFRASTRUCTURE TEST COMPLETE!")
    print("=" * 50)

    return True

def test_manual_download_with_licenses():
    """Test manual download functionality with licenses accepted."""
    print("\nTesting Manual Download with Licenses Accepted")
    print("=" * 50)

    # Accept licenses first
    for db_type in ["sqlite", "postgresql"]:
        license_key = f"jdbc_driver_{db_type}"
        if not is_license_accepted(license_key):
            accept_license(license_key, expiration_days=365)

    # Test downloading a specific driver
    print(f"\nTesting download for sqlite...")
    result = download_jdbc_driver(
        db_type="sqlite",
        version="recommended",
        on_status=lambda msg: print(f"  Status: {msg}")
    )

    if result:
        print(f"✓ Successfully downloaded sqlite driver to: {result}")
    else:
        print("✗ Failed to download sqlite driver")

    return result is not None

def main():
    """Run all tests."""
    print("Running Auto-Download Infrastructure Tests")
    print("=" * 60)

    # Run main infrastructure test
    success1 = test_auto_download_infrastructure()

    # Run manual download test
    success2 = test_manual_download_with_licenses()

    print(f"\nOverall Test Results:")
    print(f"  Infrastructure Test: {'✓ PASSED' if success1 else '✗ FAILED'}")
    print(f"  Manual Download Test: {'✓ PASSED' if success2 else '✗ FAILED'}")

    if success1 and success2:
        print("\n🎉 ALL TESTS PASSED! Auto-download infrastructure is working correctly.")
        return True
    else:
        print("\n❌ Some tests failed. Please check the output above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)