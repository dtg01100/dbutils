#!/usr/bin/env python3
"""
Simple integration test to verify the refactored configuration system works.
"""

import os
import sys

# Add the src directory to the path so we can import the modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from dbutils.config_manager import ConfigManager, ConfigurationLoader, get_default_config_manager
from dbutils.jdbc_provider import ProviderRegistry


def test_config_manager_basic():
    """Test basic ConfigManager functionality."""
    print("Testing ConfigManager basic functionality...")

    manager = get_default_config_manager()
    config = manager.load_configuration()

    # Verify we have the expected structure
    assert "provider_templates" in config, "Missing provider_templates"
    assert "default_providers" in config, "Missing default_providers"

    templates = config["provider_templates"]
    providers = config["default_providers"]

    print(f"✅ Loaded {len(templates)} provider templates and {len(providers)} default providers")

    return True

def test_jar_path_resolution():
    """Test JAR path resolution functionality."""
    print("\nTesting JAR path resolution...")

    manager = get_default_config_manager()

    # Test with known JAR names
    h2_path = manager.get_jar_path("h2")
    sqlite_path = manager.get_jar_path("sqlite-jdbc")

    print(f"H2 JAR path: {h2_path}")
    print(f"SQLite JAR path: {sqlite_path}")

    # Test with environment variable override
    os.environ["DBUTILS_TEST_JAR"] = "/test/path/test.jar"
    test_path = manager.get_jar_path("test")
    print(f"Test JAR path with env override: {test_path}")

    assert test_path == "/test/path/test.jar", "Environment variable override failed"

    return True

def test_configuration_loader():
    """Test ConfigurationLoader with fallback mechanisms."""
    print("\nTesting ConfigurationLoader...")

    loader = ConfigurationLoader()
    config = loader.load_all_configurations()

    # Test provider template retrieval
    postgres_template = loader.get_provider_template("PostgreSQL")
    assert postgres_template is not None, "PostgreSQL template should exist"
    assert "driver_class" in postgres_template, "Template should have driver_class"

    print(f"✅ PostgreSQL template: {postgres_template['driver_class']}")

    # Test fallback for non-existent template
    unknown_template = loader.get_provider_template("NonExistentDB")
    assert unknown_template is not None, "Should provide fallback template"
    assert "driver_class" in unknown_template, "Fallback template should have driver_class"

    print("✅ Fallback template provided for non-existent database")

    return True

def test_environment_variable_expansion():
    """Test environment variable expansion."""
    print("\nTesting environment variable expansion...")

    # Set test variables
    os.environ["DBUTILS_TEST_VAR"] = "test_value"
    os.environ["DBUTILS_NESTED_TEST_VAR"] = "nested_value"

    manager = ConfigManager()
    manager.add_config_source("DBUTILS", "env")

    # Test expansion
    test_config = {
        "simple": "${DBUTILS_TEST_VAR}",
        "nested": {
            "var": "$DBUTILS_NESTED_TEST_VAR"
        }
    }

    expanded = manager._expand_environment_variables(test_config)

    assert expanded["simple"] == "test_value", "Simple variable expansion failed"
    assert expanded["nested"]["var"] == "nested_value", "Nested variable expansion failed"

    print("✅ Environment variable expansion working correctly")

    return True

def test_provider_registry_integration():
    """Test that ProviderRegistry works with the new config system."""
    print("\nTesting ProviderRegistry integration...")

    # Test basic ProviderRegistry functionality
    registry = ProviderRegistry()
    providers = registry.list_names()

    print(f"✅ ProviderRegistry loaded {len(providers)} providers: {providers}")

    # Verify we can get a provider
    if providers:
        first_provider = registry.get(providers[0])
        assert first_provider is not None, "Should be able to get provider"
        print(f"✅ Can retrieve provider: {first_provider.name}")

    return True

def test_fallback_mechanisms():
    """Test fallback mechanisms."""
    print("\nTesting fallback mechanisms...")

    # Test ConfigurationLoader fallback
    loader = ConfigurationLoader()

    # Test minimal fallback config
    fallback_config = loader._get_minimal_fallback_config()
    assert "provider_templates" in fallback_config, "Fallback should have provider_templates"
    assert "default_providers" in fallback_config, "Fallback should have default_providers"
    assert "fallback_mode" in fallback_config, "Fallback should be marked as fallback"

    print("✅ Fallback mechanisms working correctly")

    return True

def main():
    """Run all tests."""
    print("Starting simple integration tests...")

    try:
        test_config_manager_basic()
        test_jar_path_resolution()
        test_configuration_loader()
        test_environment_variable_expansion()
        test_provider_registry_integration()
        test_fallback_mechanisms()

        print("\n🎉 All simple integration tests passed!")

        return 0

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
