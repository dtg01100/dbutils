#!/usr/bin/env python3
"""
Alternative JT400 test with different JVM startup
"""

from pathlib import Path

import jpype


def test_jpype_alternative():
    """Test JPype with alternative startup."""
    print("=== Alternative JPype Test ===")

    jar_path = Path("jars/jt400.jar").absolute()

    # Try different JVM startup approaches
    approaches = [
        # Approach 1: Basic with classpath
        {
            "name": "Basic with classpath",
            "args": ["-Djava.class.path=" + str(jar_path)]
        },
        # Approach 2: With explicit classpath
        {
            "name": "With explicit classpath",
            "args": ["-classpath", str(jar_path)]
        },
        # Approach 3: Minimal
        {
            "name": "Minimal startup",
            "args": []
        }
    ]

    for approach in approaches:
        print(f"\n--- {approach['name']} ---")

        try:
            # Ensure JVM is shutdown
            if jpype.isJVMStarted():
                jpype.shutdownJVM()
                print("JVM shutdown")

            # Start JVM with this approach
            print(f"Starting JVM with args: {approach['args']}")
            jpype.startJVM(*approach['args'])
            print("✓ JVM started successfully")

            # Test basic Java functionality
            java_system = jpype.JClass("java.lang.System")
            print(f"✓ Java System class: {java_system.getProperty('java.version')}")

            # Try to load JT400 if classpath was provided
            if "class" in str(approach['args']):
                try:
                    driver_class = jpype.JClass("com.ibm.as400.access.AS400JDBCDriver")
                    print("✓ JT400 driver class loaded")
                    driver = driver_class()
                    print(f"✓ JT400 driver instantiated: {driver.getClass().getName()}")
                    return True
                except Exception as e:
                    print(f"✗ JT400 driver failed: {e}")
            else:
                print("Skipping JT400 test (no classpath)")

            # Shutdown for next approach
            jpype.shutdownJVM()

        except Exception as e:
            print(f"✗ Approach failed: {e}")
            if jpype.isJVMStarted():
                try:
                    jpype.shutdownJVM()
                except:
                    pass

    return False

def test_direct_jar():
    """Test direct JAR access."""
    print("\n=== Direct JAR Test ===")

    jar_path = Path("jars/jt400.jar")

    if jar_path.exists():
        print(f"✓ JAR exists: {jar_path}")
        print(f"  Size: {jar_path.stat().st_size:,} bytes")

        # Try to read JAR manifest
        import zipfile
        try:
            with zipfile.ZipFile(jar_path, 'r') as jar:
                manifest = jar.read('META-INF/MANIFEST.MF').decode('utf-8')
                print("✓ JAR manifest readable")

                # Look for key entries
                driver_found = False
                for name in jar.namelist():
                    if 'AS400JDBCDriver' in name:
                        driver_found = True
                        print(f"✓ Found driver class: {name}")
                        break

                if not driver_found:
                    print("✗ AS400JDBCDriver class not found in JAR")
                    return False

        except Exception as e:
            print(f"✗ JAR reading failed: {e}")
            return False
    else:
        print("✗ JAR file not found")
        return False

    return True

def main():
    """Run tests."""
    print("Testing JT400 with alternative approaches\n")

    # Test 1: Direct JAR access
    if not test_direct_jar():
        print("JAR file issues detected")
        return 1

    # Test 2: Alternative JPype approaches
    if test_jpype_alternative():
        print("\n🎉 Found working approach!")
        return 0
    else:
        print("\n❌ All approaches failed")
        return 1

if __name__ == "__main__":
    exit(main())
