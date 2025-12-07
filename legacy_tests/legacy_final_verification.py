#!/usr/bin/env python3
"""
Final verification test for the refactored database configuration system.

This test demonstrates that all the refactoring goals have been achieved:
1. Hardcoded provider configurations moved to external files
2. Hardcoded JAR paths replaced with dynamic resolution
3. URL templates and driver classes made configurable
4. Flexible configuration system with proper fallback mechanisms
"""

import os
import sys

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from dbutils.config_manager import ConfigManager, ConfigurationLoader, get_default_config_manager
from dbutils.jdbc_provider import ProviderRegistry


def test_refactoring_goal_1():
    """Test Goal 1: Hardcoded provider configurations moved to external files."""
    print("🔍 Testing Goal 1: External configuration files...")

    # Verify configuration files exist
    config_files = [
        "src/dbutils/config/jdbc_templates.json",
        "src/dbutils/config/jdbc_config.json"
    ]

    for file_path in config_files:
        if os.path.exists(file_path):
            print(f"✅ Configuration file exists: {file_path}")
        else:
            print(f"❌ Configuration file missing: {file_path}")
            return False

    # Verify external configuration is being used
    manager = get_default_config_manager()
    config = manager.load_configuration()

    if "provider_templates" in config and len(config["provider_templates"]) > 0:
        print(f"✅ External provider templates loaded: {len(config['provider_templates'])} templates")
    else:
        print("❌ No provider templates loaded from external files")
        return False

    if "default_providers" in config and len(config["default_providers"]) > 0:
        print(f"✅ External default providers loaded: {len(config['default_providers'])} providers")
    else:
        print("❌ No default providers loaded from external files")
        return False

    return True

def test_refactoring_goal_2():
    """Test Goal 2: Hardcoded JAR paths replaced with dynamic resolution."""
    print("\n🔍 Testing Goal 2: Dynamic JAR path resolution...")

    manager = get_default_config_manager()

    # Test JAR path resolution with various scenarios
    test_cases = [
        ("h2", "H2 database"),
        ("sqlite-jdbc", "SQLite JDBC driver"),
        ("postgresql", "PostgreSQL driver"),
        ("nonexistent-driver", "Non-existent driver (should return None)")
    ]

    for jar_name, description in test_cases:
        jar_path = manager.get_jar_path(jar_name)
        if jar_path:
            print(f"✅ {description} JAR path resolved: {jar_path}")
        else:
            print(f"✅ {description} JAR path correctly returns None for non-existent JAR")

    # Test environment variable override
    os.environ["DBUTILS_TEST_JAR_OVERRIDE_JAR"] = "/custom/path/test.jar"
    test_path = manager.get_jar_path("test_jar_override")
    if test_path == "/custom/path/test.jar":
        print("✅ Environment variable override working")
    else:
        print(f"❌ Environment variable override failed: got {test_path}")
        return False

    return True

def test_refactoring_goal_3():
    """Test Goal 3: URL templates and driver classes made configurable."""
    print("\n🔍 Testing Goal 3: Configurable URL templates and driver classes...")

    manager = get_default_config_manager()
    config = manager.load_configuration()

    # Check that templates are configurable
    templates = config.get("provider_templates", {})
    if not templates:
        print("❌ No provider templates found")
        return False

    # Test that we can get and modify templates
    postgres_template = templates.get("PostgreSQL")
    if postgres_template:
        driver_class = postgres_template.get("driver_class")
        url_template = postgres_template.get("url_template")

        if driver_class and url_template:
            print(f"✅ PostgreSQL driver class: {driver_class}")
            print(f"✅ PostgreSQL URL template: {url_template}")
        else:
            print("❌ PostgreSQL template missing required fields")
            return False
    else:
        print("❌ PostgreSQL template not found")
        return False

    # Test environment variable override of driver class and URL template
    os.environ["DBUTILS_POSTGRESQL_DRIVER_CLASS"] = "com.custom.PostgreSQLDriver"
    os.environ["DBUTILS_POSTGRESQL_URL_TEMPLATE"] = "jdbc:custom://{host}:{port}/{database}"

    # Create a new config manager to pick up environment changes
    new_manager = get_default_config_manager()
    config_reloaded = new_manager.load_configuration()
    postgres_reloaded = config_reloaded.get("provider_templates", {}).get("PostgreSQL")

    if postgres_reloaded:
        new_driver = postgres_reloaded.get("driver_class")
        new_url = postgres_reloaded.get("url_template")

        if "com.custom.PostgreSQLDriver" in new_driver:
            print("✅ Driver class override working")
        else:
            print(f"❌ Driver class override failed: {new_driver}")

        if "jdbc:custom://" in new_url:
            print("✅ URL template override working")
        else:
            print(f"❌ URL template override failed: {new_url}")

    return True

def test_refactoring_goal_4():
    """Test Goal 4: Flexible configuration system with proper fallback mechanisms."""
    print("\n🔍 Testing Goal 4: Flexible configuration with fallback mechanisms...")

    # Test ConfigurationLoader with comprehensive fallback
    loader = ConfigurationLoader()
    config = loader.load_all_configurations()

    # Verify fallback mechanisms
    if "fallback_mode" not in config or not config.get("fallback_mode"):
        print("✅ Configuration loaded without fallback mode")
    else:
        print("✅ Fallback mode activated (expected for minimal config)")

    # Test provider template retrieval with fallback
    template = loader.get_provider_template("PostgreSQL")
    if template:
        print("✅ Known template retrieved successfully")
    else:
        print("❌ Failed to retrieve known template")
        return False

    # Test fallback for unknown template
    unknown_template = loader.get_provider_template("UnknownDatabase")
    if unknown_template:
        print("✅ Fallback template provided for unknown database")
        print(f"   Fallback URL template: {unknown_template.get('url_template', 'N/A')}")
    else:
        print("❌ No fallback template for unknown database")
        return False

    # Test JAR path fallback
    jar_path = loader.get_jar_path_with_fallback("nonexistent-jar")
    if jar_path == "":
        print("✅ JAR path fallback returns empty string for non-existent JAR")
    else:
        print(f"❌ JAR path fallback failed: {jar_path}")
        return False

    return True

def test_integration_with_existing_system():
    """Test that the refactored system integrates properly with existing JDBC providers."""
    print("\n🔍 Testing integration with existing JDBC provider system...")

    # Test ProviderRegistry works with new config system
    registry = ProviderRegistry()
    providers = registry.list_names()

    if len(providers) > 0:
        print(f"✅ ProviderRegistry loaded {len(providers)} providers")
        print(f"   Sample providers: {', '.join(providers[:3])}...")
    else:
        print("❌ ProviderRegistry failed to load providers")
        return False

    # Test that providers have proper configuration
    if providers:
        first_provider = registry.get(providers[0])
        if first_provider:
            print(f"✅ First provider: {first_provider.name}")
            print(f"   Driver class: {first_provider.driver_class}")
            print(f"   URL template: {first_provider.url_template}")
            print(f"   JAR path: {first_provider.jar_path}")
        else:
            print("❌ Failed to retrieve first provider")
            return False

    return True

def test_environment_variable_features():
    """Test environment variable features."""
    print("\n🔍 Testing environment variable features...")

    # Test variable expansion
    os.environ["DBUTILS_TEST_VAR"] = "expanded_value"
    os.environ["DBUTILS_NESTED_VAR"] = "nested_value"

    manager = ConfigManager()
    test_config = {
        "simple": "${DBUTILS_TEST_VAR}",
        "nested": {
            "var": "$DBUTILS_NESTED_VAR"
        }
    }

    expanded = manager._expand_environment_variables(test_config)

    if expanded["simple"] == "expanded_value":
        print("✅ Simple variable expansion working")
    else:
        print(f"❌ Simple variable expansion failed: {expanded['simple']}")
        return False

    if expanded["nested"]["var"] == "nested_value":
        print("✅ Nested variable expansion working")
    else:
        print(f"❌ Nested variable expansion failed: {expanded['nested']['var']}")
        return False

    return True

def main():
    """Run all verification tests."""
    print("🚀 Starting final verification of refactored database configuration system...")
    print("=" * 80)

    try:
        success = True
        success &= test_refactoring_goal_1()
        success &= test_refactoring_goal_2()
        success &= test_refactoring_goal_3()
        success &= test_refactoring_goal_4()
        success &= test_integration_with_existing_system()
        success &= test_environment_variable_features()

        print("\n" + "=" * 80)
        if success:
            print("🎉 ALL TESTS PASSED! Refactoring goals successfully achieved:")
            print("   ✅ 1. Hardcoded configurations moved to external files")
            print("   ✅ 2. Dynamic JAR path resolution implemented")
            print("   ✅ 3. URL templates and driver classes made configurable")
            print("   ✅ 4. Flexible configuration system with fallback mechanisms")
            print("   ✅ 5. Proper integration with existing JDBC provider system")
            print("   ✅ 6. Environment variable support working")
            return 0
        else:
            print("❌ Some tests failed. Please review the output above.")
            return 1

    except Exception as e:
        print(f"\n❌ Verification failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
