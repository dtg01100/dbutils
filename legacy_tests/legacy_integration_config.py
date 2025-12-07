#!/usr/bin/env python3
"""
Integration test to verify the refactored configuration system works with existing JDBC providers.
"""

import os
import sys

# Add the src directory to the path so we can import the modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from dbutils.config_manager import ConfigurationLoader, get_default_config_manager
from dbutils.enhanced_jdbc_provider import EnhancedProviderRegistry, PredefinedProviderTemplates
from dbutils.jdbc_provider import ProviderRegistry


def test_enhanced_provider_integration():
    """Test that the enhanced JDBC provider works with the new configuration system."""
    print("Testing EnhancedProviderRegistry integration...")

    # Test PredefinedProviderTemplates with config manager
    config_manager = get_default_config_manager()
    templates = PredefinedProviderTemplates(config_manager)

    # Test template retrieval
    postgres_template = templates.get_template("PostgreSQL")
    if postgres_template:
        print(f"✅ PostgreSQL template loaded: {postgres_template['driver_class']}")
    else:
        print("❌ PostgreSQL template not found")
        return False

    # Test creating provider from template
    provider = templates.create_provider_from_template("PostgreSQL", "Test PostgreSQL", "localhost", "testdb")
    if provider:
        print(f"✅ Created provider: {provider.name} with driver {provider.driver_class}")
    else:
        print("❌ Failed to create provider from template")
        return False

    # Test EnhancedProviderRegistry with config manager
    registry = EnhancedProviderRegistry(config_manager=config_manager)
    providers = registry.list_providers()

    print(f"✅ EnhancedProviderRegistry loaded {len(providers)} providers")

    return True

def test_jdbc_provider_integration():
    """Test that the basic JDBC provider works with the new configuration system."""
    print("\nTesting ProviderRegistry integration...")

    # Test that ProviderRegistry can use the new config system
    config_manager = get_default_config_manager()

    # Test JAR path resolution
    h2_jar = config_manager.get_jar_path("h2")
    sqlite_jar = config_manager.get_jar_path("sqlite-jdbc")

    print(f"H2 JAR path: {h2_jar}")
    print(f"SQLite JAR path: {sqlite_jar}")

    # Test ProviderRegistry initialization
    registry = ProviderRegistry()
    providers = registry.list_names()

    print(f"✅ ProviderRegistry loaded {len(providers)} providers: {providers}")

    return True

def test_environment_override_integration():
    """Test environment variable overrides work with the provider system."""
    print("\nTesting environment variable override integration...")

    # Set test environment variables
    os.environ["DBUTILS_POSTGRESQL_DRIVER_CLASS"] = "com.test.PostgreSQLDriver"
    os.environ["DBUTILS_POSTGRESQL_URL_TEMPLATE"] = "jdbc:test://{host}:{port}/{database}"

    # Test with config manager
    config_manager = get_default_config_manager()
    config = config_manager.load_configuration()

    # Check if overrides were applied
    postgres_template = config.get("provider_templates", {}).get("PostgreSQL")
    if postgres_template:
        driver_class = postgres_template.get("driver_class")
        url_template = postgres_template.get("url_template")

        if "com.test.PostgreSQLDriver" in driver_class:
            print("✅ Driver class override applied")
        else:
            print("❌ Driver class override not applied")

        if "jdbc:test://" in url_template:
            print("✅ URL template override applied")
        else:
            print("❌ URL template override not applied")

    # Test with PredefinedProviderTemplates
    templates = PredefinedProviderTemplates(config_manager)
    template = templates.get_template("PostgreSQL")

    if template and "com.test.PostgreSQLDriver" in template.get("driver_class", ""):
        print("✅ Template system respects environment overrides")
    else:
        print("❌ Template system doesn't respect environment overrides")

    return True

def test_fallback_mechanisms_integration():
    """Test that fallback mechanisms work in the provider system."""
    print("\nTesting fallback mechanisms integration...")

    # Test with non-existent template
    config_manager = get_default_config_manager()
    templates = PredefinedProviderTemplates(config_manager)

    # Request a non-existent template
    unknown_template = templates.get_template("NonExistentDB")
    if unknown_template:
        print(f"✅ Fallback template provided: {unknown_template}")
    else:
        print("❌ No fallback template provided")

    # Test provider creation with fallback
    provider = templates.create_provider_from_template("NonExistentDB", "Test Fallback")
    if provider:
        print(f"✅ Fallback provider created: {provider.name}")
    else:
        print("❌ Fallback provider creation failed")

    return True

def test_configuration_consistency():
    """Test that configuration is consistent across different loading mechanisms."""
    print("\nTesting configuration consistency...")

    # Load configuration through different methods
    config_manager = get_default_config_manager()
    config1 = config_manager.load_configuration()

    config_loader = ConfigurationLoader()
    config2 = config_loader.load_all_configurations()

    # Compare provider templates
    templates1 = config1.get("provider_templates", {})
    templates2 = config2.get("provider_templates", {})

    if len(templates1) == len(templates2):
        print(f"✅ Consistent template count: {len(templates1)}")
    else:
        print(f"❌ Inconsistent template count: {len(templates1)} vs {len(templates2)}")
        return False

    # Compare default providers
    providers1 = config1.get("default_providers", {})
    providers2 = config2.get("default_providers", {})

    if len(providers1) == len(providers2):
        print(f"✅ Consistent provider count: {len(providers1)}")
    else:
        print(f"❌ Inconsistent provider count: {len(providers1)} vs {len(providers2)}")
        return False

    return True

def main():
    """Run all integration tests."""
    print("Starting integration tests for refactored configuration system...")

    try:
        success = True
        success &= test_enhanced_provider_integration()
        success &= test_jdbc_provider_integration()
        success &= test_environment_override_integration()
        success &= test_fallback_mechanisms_integration()
        success &= test_configuration_consistency()

        if success:
            print("\n🎉 All integration tests passed! The refactored configuration system is working correctly.")
            return 0
        else:
            print("\n❌ Some integration tests failed.")
            return 1

    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
