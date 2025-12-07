#!/usr/bin/env python3
"""
Setup JT400 provider in the dbutils registry.
This script adds the JT400 provider to the providers.json configuration.
"""

import os
import sys
from pathlib import Path

# Add src to path so we can import dbutils
sys.path.insert(0, str(Path(__file__).parent / "src"))

def setup_jt400_provider():
    """Setup the JT400 provider in the registry."""
    try:
        from dbutils.jdbc_provider import JDBCProvider, get_registry

        # Create the JT400 provider
        provider = JDBCProvider(
            name="IBM i (JT400)",
            driver_class="com.ibm.as400.access.AS400JDBCDriver",
            jar_path=str(Path("jars/jt400.jar").absolute()),
            url_template="jdbc:as400://{host}:{port}/{database};naming=1;errors=full",
            default_user=None,
            default_password=None,
            extra_properties={
                "date format": "iso",
                "time format": "iso",
                "decimal separator": ".",
                "translate binary": "true",
                "package": "default",
                "lazy close": "true"
            }
        )

        # Add to registry
        registry = get_registry()
        registry.add_or_update(provider)

        print("✓ Successfully added JT400 provider to registry")
        print(f"  Configuration saved to: {registry.config_path}")

        # Show all available providers
        print("\nAvailable providers:")
        for name in registry.list_names():
            p = registry.get(name)
            print(f"  - {name}: {p.driver_class}")

        return True

    except Exception as e:
        print(f"✗ Failed to setup JT400 provider: {e}")
        return False

def show_config_file():
    """Show the contents of the providers.json file."""
    try:
        from dbutils.jdbc_provider import PROVIDERS_JSON

        if os.path.exists(PROVIDERS_JSON):
            print(f"\n=== {PROVIDERS_JSON} ===")
            with open(PROVIDERS_JSON, 'r') as f:
                content = f.read()
                print(content)
        else:
            print(f"Configuration file not found: {PROVIDERS_JSON}")

    except Exception as e:
        print(f"Error reading config file: {e}")

def main():
    """Setup the JT400 provider."""
    print("=== Setting up JT400 Provider ===\n")

    success = setup_jt400_provider()

    if success:
        show_config_file()
        print("\n🎉 JT400 provider is now configured!")
        print("\nNext steps:")
        print("1. Install JDBC dependencies: pip install JPype1 JayDeBeApi")
        print("2. Set environment variables for your connection:")
        print('   export DBUTILS_JDBC_PROVIDER="IBM i (JT400)"')
        print('   export DBUTILS_JDBC_URL_PARAMS=\'{"host":"your-as400","port":446,"database":"your-lib"}\'')
        print("3. Run the GUI: python -m dbutils.gui.qt_app")
        return 0
    else:
        print("\n❌ Failed to setup JT400 provider")
        return 1

if __name__ == "__main__":
    sys.exit(main())
