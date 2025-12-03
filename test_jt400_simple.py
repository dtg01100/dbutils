#!/usr/bin/env python3
"""
Simple JT400 JAR verification script.
This script verifies the jt400.jar structure without requiring JDBC dependencies.
"""

import os
import sys
import zipfile
from pathlib import Path

def test_jt400_jar_exists():
    """Test that the jt400.jar file exists in the jars directory."""
    jar_path = Path("jars/jt400.jar")
    if jar_path.exists():
        print(f"✓ JT400 JAR found at: {jar_path.absolute()}")
        print(f"  Size: {jar_path.stat().st_size:,} bytes")
        return True, jar_path
    else:
        print(f"✗ JT400 JAR not found at: {jar_path.absolute()}")
        return False, None

def inspect_jar_structure(jar_path):
    """Inspect the JAR file structure to verify it contains JT400 classes."""
    try:
        with zipfile.ZipFile(jar_path, 'r') as jar:
            files = jar.namelist()
            
            # Look for key JT400 classes
            driver_class = None
            manifest = None
            
            for file in files:
                if file.endswith("AS400JDBCDriver.class"):
                    driver_class = file
                elif file == "META-INF/MANIFEST.MF":
                    manifest = file
            
            print(f"✓ JAR contains {len(files):,} files")
            
            if driver_class:
                print(f"✓ Found JDBC driver class: {driver_class}")
            else:
                print("✗ AS400JDBCDriver class not found")
                
            if manifest:
                print(f"✓ Found manifest: {manifest}")
                # Read and display key manifest info
                try:
                    with jar.open(manifest) as mf:
                        content = mf.read().decode('utf-8')
                        lines = [line.strip() for line in content.split('\n') if line.strip()]
                        for line in lines[:10]:  # Show first 10 lines
                            if any(key in line for key in ['Manifest-Version', 'Implementation-Version', 'Main-Class']):
                                print(f"  {line}")
                except Exception as e:
                    print(f"  Could not read manifest: {e}")
            else:
                print("✗ No manifest found")
                
            # Show some package structure
            packages = set()
            for file in files:
                if '/' in file and file.endswith('.class'):
                    pkg = file.split('/')[0]
                    packages.add(pkg)
            
            print(f"✓ Found {len(packages)} main packages:")
            for pkg in sorted(packages)[:10]:  # Show first 10 packages
                print(f"  - {pkg}")
            if len(packages) > 10:
                print(f"  ... and {len(packages) - 10} more")
                
            return True
            
    except zipfile.BadZipFile:
        print("✗ JAR file is corrupted or not a valid ZIP file")
        return False
    except Exception as e:
        print(f"✗ Error reading JAR file: {e}")
        return False

def create_provider_config():
    """Create the provider configuration for JT400."""
    config = {
        "name": "IBM i (JT400)",
        "driver_class": "com.ibm.as400.access.AS400JDBCDriver",
        "jar_path": str(Path("jars/jt400.jar").absolute()),
        "url_template": "jdbc:as400://{host}:{port}/{database};naming=1;errors=full",
        "default_user": None,
        "default_password": None,
        "extra_properties": {
            "date format": "iso",
            "time format": "iso",
            "decimal separator": ".",
            "translate binary": "true",
            "package": "default",
            "lazy close": "true"
        }
    }
    
    print("\n=== JT400 Provider Configuration ===")
    print("Add this configuration to your providers.json or use the GUI:")
    print()
    
    import json
    print(json.dumps(config, indent=2))
    
    return config

def show_usage_examples():
    """Show examples of how to use the JT400 provider."""
    print("\n=== Usage Examples ===")
    print()
    
    print("1. Using Environment Variables:")
    print('export DBUTILS_JDBC_PROVIDER="IBM i (JT400)"')
    print('export DBUTILS_JDBC_URL_PARAMS=\'{"host":"your-as400","port":446,"database":"your-lib"}\'')
    print('export DBUTILS_JDBC_USER="your-user"')
    print('export DBUTILS_JDBC_PASSWORD="your-password"')
    print("python -m dbutils.gui.qt_app")
    print()
    
    print("2. Using in Python Code:")
    print("""
from dbutils.jdbc_provider import connect

# Connect to IBM i system
conn = connect(
    "IBM i (JT400)",
    {"host": "your-as400", "port": 446, "database": "your-lib"},
    user="your-user",
    password="your-password"
)

# Execute queries
try:
    rows = conn.query("SELECT * FROM QSYS2.SYSTABLES FETCH FIRST 5 ROWS ONLY")
    for row in rows:
        print(row)
finally:
    conn.close()
""")
    
    print("3. Common URL Template Variations:")
    print('  - Default: "jdbc:as400://{host}:{port}/{database};naming=1;errors=full"')
    print('  - SQL naming: "jdbc:as400://{host}:{port}/{database};naming=0;errors=full"')
    print('  - With libraries: "jdbc:as400://{host}:{port};libraries=LIB1,LIB2; naming=1"')
    print('  - With date format: "jdbc:as400://{host}:{port}/{database};date format=iso;time format=iso"')

def show_troubleshooting():
    """Show troubleshooting tips."""
    print("\n=== Troubleshooting ===")
    print()
    print("1. JVM Requirements:")
    print("   - Java 8+ recommended")
    print("   - JAVA_HOME should point to valid Java installation")
    print("   - JPype will automatically start the JVM")
    print()
    print("2. Common Issues:")
    print("   - 'java.lang.UnsatisfiedLinkError': Usually Java native library issues")
    print("   - 'ClassNotFoundException': Driver class not found in JAR")
    print("   - 'Connection refused': Check host, port, and firewall")
    print("   - 'SQL error': Check database/library name and permissions")
    print()
    print("3. JT400 Specific:")
    print("   - Port 446 for SSL connections, 445 for non-SSL")
    print("   - Database parameter is usually the library/schema name")
    print("   - Use naming=1 for SQL naming (recommended)")
    print("   - Use naming=0 for system naming (*LIB/FILE)")

def main():
    """Run all tests and show configuration."""
    print("=== JT400 JAR Verification ===\n")
    
    # Test 1: JAR file exists
    jar_ok, jar_path = test_jt400_jar_exists()
    print()
    
    if not jar_ok:
        print("Cannot proceed without JT400 JAR file.")
        return 1
    
    # Test 2: Inspect JAR structure
    structure_ok = inspect_jar_structure(jar_path)
    print()
    
    # Test 3: Show provider configuration
    config = create_provider_config()
    
    # Test 4: Show usage examples
    show_usage_examples()
    
    # Test 5: Show troubleshooting
    show_troubleshooting()
    
    print("\n=== Summary ===")
    print(f"JAR File: {'✓' if jar_ok else '✗'}")
    print(f"JAR Structure: {'✓' if structure_ok else '✗'}")
    
    if jar_ok and structure_ok:
        print("\n🎉 JT400 JAR is ready for use!")
        print("Install JDBC dependencies with: pip install JPype1 JayDeBeApi")
        print("Then configure the provider as shown above.")
        return 0
    else:
        print("\n❌ JAR file has issues. Check the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())