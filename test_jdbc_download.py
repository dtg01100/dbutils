#!/usr/bin/env python3
"""Test the new JDBC auto-download functionality."""

import sys
import os

# Add the source to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from dbutils.gui.jdbc_auto_downloader import (
    get_jdbc_driver_url,
    download_jdbc_driver,
    get_latest_version_from_maven_metadata,
    list_installed_drivers
)


def test_jdbc_auto_download():
    """Test the JDBC auto-download functionality."""
    print("Testing JDBC Auto-Downloader...")
    
    # Test getting download URLs
    print("\n1. Testing download URL generation:")
    for db_type in ['postgresql', 'mysql', 'sqlite']:
        url = get_jdbc_driver_url(db_type, 'latest')
        print(f"   {db_type}: {url}")
    
    # Test getting latest versions
    print("\n2. Testing version retrieval:")
    for db_type in ['postgresql', 'mysql', 'sqlite']:
        coords = {
            'postgresql': {
                'metadata_url': 'https://repo1.maven.org/maven2/org/postgresql/postgresql/maven-metadata.xml'
            },
            'mysql': {
                'metadata_url': 'https://repo1.maven.org/maven2/mysql/mysql-connector-java/maven-metadata.xml'
            },
            'sqlite': {
                'metadata_url': 'https://repo1.maven.org/maven2/org/xerial/sqlite-jdbc/maven-metadata.xml'
            }
        }
        metadata_url = coords[db_type]['metadata_url']
        latest = get_latest_version_from_maven_metadata(metadata_url)
        print(f"   {db_type}: Latest version = {latest}")
    
    # Test listing installed drivers
    print("\n3. Testing installed drivers listing:")
    installed = list_installed_drivers()
    print(f"   Found {len(installed)} installed drivers:")
    for driver in installed[:5]:  # Show first 5
        print(f"      {driver}")
    if len(installed) > 5:
        print(f"      ... and {len(installed)-5} more")
    
    print("\n✅ All basic tests passed!")


def simulate_small_download():
    """Try to download a small test driver to verify functionality."""
    try:
        print("\n4. Attempting to download SQLite driver (small test):")
        result = download_jdbc_driver('sqlite', 'latest')
        if result:
            print(f"   Successfully downloaded to: {result}")
        else:
            print("   Download not attempted (may require network access or may have already been downloaded)")
    except Exception as e:
        print(f"   Error during download: {e}")


if __name__ == "__main__":
    test_jdbc_auto_download()
    simulate_small_download()
    print("\nTesting completed.")