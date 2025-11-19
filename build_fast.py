#!/usr/bin/env python3
"""
Build script for Cython extensions in dbutils.

This script compiles the performance-critical Cython modules for better performance.
"""

import subprocess
import sys
from pathlib import Path


def build_cython_extensions():
    """Build the Cython extensions."""
    print("Building Cython extensions for dbutils...")

    # Check if Cython is available
    try:
        import Cython

        print(f"✓ Cython {Cython.__version__} found")
    except ImportError:
        print("❌ Cython not found. Install with: pip install cython")
        return False

    # Check if numpy is available
    try:
        import numpy

        print(f"✓ NumPy {numpy.__version__} found")
    except ImportError:
        print("❌ NumPy not found. Install with: pip install numpy")
        return False

    # Create build directory
    build_dir = Path("build")
    build_dir.mkdir(exist_ok=True)

    # Build the extension
    try:
        cmd = [
            sys.executable,
            "setup_fast.py",
            "build_ext",
            "--inplace",
            "--build-lib",
            "src",
            "--build-temp",
            str(build_dir),
        ]

        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=Path.cwd(), capture_output=True, text=True)

        if result.returncode == 0:
            print("✓ Cython extensions built successfully")
            print("✓ Performance optimizations are now active")

            # Test that the extension loads
            try:
                sys.path.insert(0, str(Path("src").absolute()))
                from dbutils.accelerated import get_acceleration_status

                status = get_acceleration_status()
                print(f"✓ Acceleration status: {status}")
                return True
            except ImportError as e:
                print(f"⚠️  Extension built but cannot import: {e}")
                return False
        else:
            print("❌ Build failed:")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return False

    except Exception as e:
        print(f"❌ Build error: {e}")
        return False


def clean_build_artifacts():
    """Clean up build artifacts."""
    import shutil

    artifacts = [
        "build",
        "src/dbutils/fast_ops.c",
        "src/dbutils/fast_ops.so",
        "src/dbutils/fast_ops.pyd",  # Windows
    ]

    for artifact in artifacts:
        path = Path(artifact)
        if path.exists():
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
            print(f"✓ Cleaned {artifact}")


def main():
    """Main build function."""
    if len(sys.argv) > 1 and sys.argv[1] == "clean":
        print("Cleaning build artifacts...")
        clean_build_artifacts()
        return

    success = build_cython_extensions()
    if success:
        print("\n🎉 Cython extensions built successfully!")
        print("Performance optimizations are now active.")
        print("\nTo clean build artifacts, run: python build_fast.py clean")
    else:
        print("\n❌ Failed to build Cython extensions.")
        print("Falling back to pure Python implementations.")
        sys.exit(1)


if __name__ == "__main__":
    main()
