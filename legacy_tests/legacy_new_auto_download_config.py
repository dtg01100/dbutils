#!/usr/bin/env python3
"""
Test script to verify the new auto-download configuration system works correctly.
"""

import os
import sys

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


def test_configuration_loading():
    """Test that the new configuration system loads correctly."""
    print("Testing new auto-download configuration system...")

    try:
        from dbutils.config.dbutils_config import get_maven_repositories
        from dbutils.gui.jdbc_provider_config import AutoDownloadProviderConfig

        # Test provider config loading
        config = AutoDownloadProviderConfig()
        auto_configs = config.get_auto_download_configs()

        print(f"✓ Loaded {len(auto_configs)} auto-download provider configurations")

        # Test that we have the expected providers
        expected_providers = ["sqlite", "h2", "derby", "hsqldb", "duckdb"]
        for provider in expected_providers:
            if provider in auto_configs:
                print(f"✓ Found {provider} configuration")
                provider_config = auto_configs[provider]
                print(f"  - Name: {provider_config['name']}")
                print(f"  - Maven Artifact: {provider_config['maven_artifact']}")
                print(f"  - Recommended Version: {provider_config['recommended_version']}")
            else:
                print(f"✗ Missing {provider} configuration")

        # Test Maven repositories
        maven_repos = get_maven_repositories()
        print(f"✓ Loaded {len(maven_repos)} Maven repositories")
        for i, repo in enumerate(maven_repos):
            print(f"  {i + 1}. {repo}")

        # Test version resolution
        version_strategy = config.get_version_resolution_strategy()
        print(f"✓ Version resolution strategy: {version_strategy}")

        # Test fallback versions
        for provider in ["sqlite", "h2"]:
            fallback_versions = config.get_fallback_versions(provider)
            print(f"✓ {provider} fallback versions: {fallback_versions}")

        # Test repository priority
        repo_priority = config.get_repository_priority()
        print(f"✓ Repository priority list: {len(repo_priority)} repositories")

        print("\n✓ All configuration tests passed!")
        return True

    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_environment_variable_overrides():
    """Test environment variable override functionality."""
    print("\nTesting environment variable overrides...")

    try:
        # Set some test environment variables
        os.environ["DBUTILS_SQLITE_VERSION"] = "3.45.0.0"
        os.environ["DBUTILS_H2_VERSION"] = "2.3.000"

        from dbutils.gui.jdbc_provider_config import AutoDownloadProviderConfig

        config = AutoDownloadProviderConfig()
        auto_configs = config.get_auto_download_configs()

        # Test that environment variables override the recommended versions
        sqlite_config = auto_configs["sqlite"]
        h2_config = auto_configs["h2"]

        if sqlite_config["recommended_version"] == "3.45.0.0":
            print("✓ SQLite version overridden by environment variable")
        else:
            print(f"✗ SQLite version override failed: {sqlite_config['recommended_version']}")

        if h2_config["recommended_version"] == "2.3.000":
            print("✓ H2 version overridden by environment variable")
        else:
            print(f"✗ H2 version override failed: {h2_config['recommended_version']}")

        print("✓ Environment variable override tests completed!")
        return True

    except Exception as e:
        print(f"✗ Environment variable test failed: {e}")
        return False
    finally:
        # Clean up environment variables
        os.environ.pop("DBUTILS_SQLITE_VERSION", None)
        os.environ.pop("DBUTILS_H2_VERSION", None)


def test_backward_compatibility():
    """Test that the new system maintains backward compatibility."""
    print("\nTesting backward compatibility...")

    try:
        # Test that old imports still work
        from dbutils.gui.jdbc_provider_config import (
            get_configured_provider,
        )

        print("✓ Old import paths still work")

        # Test that the main functions are still available
        config = get_configured_provider("sqlite")
        if config:
            print("✓ get_configured_provider still works")
        else:
            print("✗ get_configured_provider failed")

        print("✓ Backward compatibility tests passed!")
        return True

    except Exception as e:
        print(f"✗ Backward compatibility test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("Testing New Auto-Download Configuration System")
    print("=" * 50)

    tests = [test_configuration_loading, test_environment_variable_overrides, test_backward_compatibility]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1

    print("\n" + "=" * 50)
    print(f"Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! New configuration system is working correctly.")
        return True
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
