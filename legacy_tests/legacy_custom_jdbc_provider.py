#!/usr/bin/env python3
"""
Test script to verify custom JDBC provider functionality
"""

import os
import sys

# Add the src directory to the path so we can import dbutils modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from dbutils.config_manager import get_default_config_manager
from dbutils.enhanced_jdbc_provider import JDBCProvider, PredefinedProviderTemplates


def test_custom_provider_template():
    """Test that Custom provider template is available"""
    print("Testing Custom JDBC Provider Template...")

    # Test that Custom is in the standard categories
    from dbutils.enhanced_jdbc_provider import STANDARD_CATEGORIES
    assert "Custom" in STANDARD_CATEGORIES, "Custom should be in STANDARD_CATEGORIES"
    print("✓ Custom is in STANDARD_CATEGORIES")

    # Test that Custom template is available
    templates = PredefinedProviderTemplates()
    categories = templates.get_categories()
    assert "Custom" in categories, "Custom should be available in template categories"
    print("✓ Custom template is available in categories")

    # Test that we can get the Custom template
    custom_template = templates.get_template("Custom")
    assert custom_template is not None, "Custom template should be retrievable"
    assert custom_template["driver_class"] == "", "Custom template should have empty driver class"
    assert custom_template["description"] == "Custom JDBC provider - configure all parameters manually"
    print("✓ Custom template has correct properties")

    # Test creating a provider from Custom template
    custom_provider = templates.create_provider_from_template(
        category="Custom",
        name="Test Custom Provider",
        host="localhost",
        database="testdb"
    )
    assert custom_provider is not None, "Should be able to create provider from Custom template"
    assert custom_provider.category == "Custom"
    assert custom_provider.driver_class == ""
    assert custom_provider.url_template == "jdbc:{custom}://{host}:{port}/{database}"
    print("✓ Can create provider from Custom template")

def test_config_manager_custom_support():
    """Test that config manager supports Custom template"""
    print("\nTesting Config Manager Custom Support...")

    config_manager = get_default_config_manager()
    config = config_manager.load_configuration()

    # Check that Custom template is in provider templates
    provider_templates = config.get("provider_templates", {})
    assert "Custom" in provider_templates, "Custom template should be in provider templates"
    print("✓ Config manager includes Custom template")

    custom_template = provider_templates["Custom"]
    assert custom_template["driver_class"] == ""
    assert custom_template["description"] == "Custom JDBC provider - configure all parameters manually"
    print("✓ Config manager Custom template has correct properties")

def test_custom_provider_creation():
    """Test creating and using a custom provider"""
    print("\nTesting Custom Provider Creation...")

    # Create a custom provider manually
    custom_provider = JDBCProvider(
        name="My Custom Database",
        category="Custom",
        driver_class="com.example.CustomDriver",
        jar_path="/path/to/custom-driver.jar",
        url_template="jdbc:custom://{host}:{port}/{database}",
        default_host="custom-server",
        default_port=1234,
        default_database="customdb",
        extra_properties={"customProperty": "customValue"}
    )

    assert custom_provider.name == "My Custom Database"
    assert custom_provider.category == "Custom"
    assert custom_provider.driver_class == "com.example.CustomDriver"
    assert custom_provider.jar_path == "/path/to/custom-driver.jar"
    assert custom_provider.url_template == "jdbc:custom://{host}:{port}/{database}"
    assert custom_provider.default_host == "custom-server"
    assert custom_provider.default_port == 1234
    assert custom_provider.default_database == "customdb"
    assert custom_provider.extra_properties == {"customProperty": "customValue"}
    print("✓ Custom provider can be created with all parameters")

if __name__ == "__main__":
    try:
        test_custom_provider_template()
        test_config_manager_custom_support()
        test_custom_provider_creation()
        print("\n🎉 All tests passed! Custom JDBC provider functionality is working correctly.")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
