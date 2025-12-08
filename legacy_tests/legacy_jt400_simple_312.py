#!/usr/bin/env python3
"""
Simple JT400 driver test with Python 3.12
"""

from pathlib import Path

import jpype
import pytest


def test_jpype_basic():
    """Test basic JPype functionality."""
    print("=== Basic JPype Test ===")

    # Start JVM
    if not jpype.isJVMStarted():
        print("Starting JVM...")
        try:
            jpype.startJVM()
            print("✓ JVM started")
        except OSError as e:
            # Environment may already have a JVM or be unsuitable for JVM start.
            pytest.skip(f"Could not start JVM in test environment: {e}")
    else:
        print("✓ JVM already running")

    # Test basic Java functionality
    java_system = jpype.JClass("java.lang.System")
    print("✓ Java System class loaded")
    print(f"  Java version: {java_system.getProperty('java.version')}")

    # If we reach here the JVM is available and basic checks passed


def test_jt400_classpath():
    """Test loading JT400 with classpath."""
    print("\n=== JT400 Classpath Test ===")

    jar_path = Path("jars/jt400.jar").absolute()

    # Shutdown JVM to restart with classpath
    if jpype.isJVMStarted():
        jpype.shutdownJVM()
        print("JVM shutdown for restart with classpath")

    # Start JVM with JT400 classpath
    classpath = str(jar_path)
    jvm_args = ["-Djava.class.path=" + classpath]
    print(f"Starting JVM with classpath: {classpath}")

    try:
        jpype.startJVM(*jvm_args)
        print("✓ JVM started with JT400 classpath")
    except Exception as e:
        print(f"✗ Failed to start JVM: {e}")
        return False

    # Try to load JT400 driver
    try:
        driver_class = jpype.JClass("com.ibm.as400.access.AS400JDBCDriver")
        print("✓ JT400 driver class loaded")

        # Try to instantiate
        driver = driver_class()
        print("✓ JT400 driver instantiated")

        # Get driver info
        print(f"  Driver: {driver}")
        print(f"  Major version: {driver.getMajorVersion()}")
        print(f"  Minor version: {driver.getMinorVersion()}")

        return True

    except Exception as e:
        print(f"✗ Failed to load JT400 driver: {e}")
        return False


def main():
    """Run tests."""
    print("Testing JT400 with Python 3.12\n")

    # Test 1: Basic JPype
    if not test_jpype_basic():
        return 1

    # Test 2: JT400 with classpath
    if not test_jt400_classpath():
        return 1

    print("\n🎉 All tests passed!")
    return 0


if __name__ == "__main__":
    exit(main())
