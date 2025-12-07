#!/usr/bin/env python3
"""
Test script for JT400 JDBC driver integration.
This script tests the jt400.jar file and verifies JDBC connectivity.
"""

import sys
from pathlib import Path

# Add src to path so we can import dbutils
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_jt400_jar_exists():
    """Test that the jt400.jar file exists in the jars directory."""
    jar_path = Path("jars/jt400.jar")
    if jar_path.exists():
        print(f"✓ JT400 JAR found at: {jar_path.absolute()}")
        print(f"  Size: {jar_path.stat().st_size:,} bytes")
        return True
    else:
        print(f"✗ JT400 JAR not found at: {jar_path.absolute()}")
        return False

def test_jdbc_dependencies():
    """Test that JDBC dependencies are available."""
    try:
        import jaydebeapi
        import jpype
        print("✓ JDBC dependencies (JayDeBeApi, JPype) are available")
        return True
    except ImportError as e:
        print(f"✗ JDBC dependencies not available: {e}")
        return False

def create_jt400_provider():
    """Create a JT400 provider configuration."""
    from dbutils.jdbc_provider import JDBCProvider, get_registry

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
            "decimal separator": "."
        }
    )

    # Add to registry
    registry = get_registry()
    registry.add_or_update(provider)

    print(f"✓ Created JT400 provider: {provider.name}")
    print(f"  Driver: {provider.driver_class}")
    print(f"  JAR: {provider.jar_path}")
    print(f"  URL Template: {provider.url_template}")

    return provider

def test_jt400_driver_load():
    """Test that the JT400 driver can be loaded via JPype."""
    try:
        import jpype

        jar_path = Path("jars/jt400.jar").absolute()

        # Start JVM with JT400 classpath
        if not jpype.isJVMStarted():
            cp = str(jar_path)
            jvm_args = ["-Djava.class.path=" + cp]
            jpype.startJVM(*jvm_args)
            print("✓ JVM started with JT400 classpath")

        # Try to load the driver class
        driver_class = jpype.JClass("com.ibm.as400.access.AS400JDBCDriver")
        print("✓ JT400 driver class loaded successfully")

        # Test driver instantiation
        driver = driver_class()
        print("✓ JT400 driver instantiated successfully")

        return True

    except Exception as e:
        print(f"✗ Failed to load JT400 driver: {e}")
        return False

def test_connection_parameters():
    """Show example connection parameters for JT400."""
    print("\nExample connection parameters for JT400:")
    print("Environment variables:")
    print('export DBUTILS_JDBC_PROVIDER="IBM i (JT400)"')
    print('export DBUTILS_JDBC_URL_PARAMS=\'{"host":"your-as400","port":446,"database":"your-lib"}\'')
    print('export DBUTILS_JDBC_USER="your-user"')
    print('export DBUTILS_JDBC_PASSWORD="your-password"')
    print("\nOr use in code:")
    print('conn = dbutils.jdbc_provider.connect(')
    print('    "IBM i (JT400)",')
    print('    {"host": "your-as400", "port": 446, "database": "your-lib"},')
    print('    user="your-user",')
    print('    password="your-password"')
    print(')')

def main():
    """Run all tests."""
    print("=== JT400 JDBC Driver Test ===\n")

    # Test 1: JAR file exists
    jar_ok = test_jt400_jar_exists()
    print()

    # Test 2: Dependencies available
    deps_ok = test_jdbc_dependencies()
    print()

    if not jar_ok:
        print("Cannot proceed without JT400 JAR file.")
        return 1

    if not deps_ok:
        print("Cannot proceed without JDBC dependencies.")
        print("Install with: pip install JPype1 JayDeBeApi")
        return 1

    # Test 3: Create provider configuration
    try:
        provider = create_jt400_provider()
        print()
    except Exception as e:
        print(f"✗ Failed to create provider: {e}")
        return 1

    # Test 4: Test driver loading
    driver_ok = test_jt400_driver_load()
    print()

    # Test 5: Show connection examples
    test_connection_parameters()

    print("\n=== Test Summary ===")
    print(f"JAR File: {'✓' if jar_ok else '✗'}")
    print(f"Dependencies: {'✓' if deps_ok else '✗'}")
    print(f"Provider Config: {'✓' if True else '✗'}")
    print(f"Driver Load: {'✓' if driver_ok else '✗'}")

    if all([jar_ok, deps_ok, driver_ok]):
        print("\n🎉 All tests passed! JT400 integration is ready.")
        return 0
    else:
        print("\n❌ Some tests failed. Check the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
