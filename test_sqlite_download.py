#!/usr/bin/env python3
"""
Test script to debug SQLite auto-download functionality.
"""

import os
import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# Set test mode
os.environ['DBUTILS_TEST_MODE'] = '1'

# Create temp directories
temp_dir = tempfile.mkdtemp()
config_dir = Path(temp_dir) / ".config" / "dbutils"
driver_dir = Path(temp_dir) / "drivers"
config_dir.mkdir(parents=True, exist_ok=True)
driver_dir.mkdir(parents=True, exist_ok=True)

os.environ['DBUTILS_CONFIG_DIR'] = str(config_dir)
os.environ['DBUTILS_DRIVER_DIR'] = str(driver_dir)

print(f"Test config dir: {config_dir}")
print(f"Test driver dir: {driver_dir}")

# Now test the actual download
from dbutils.gui.jdbc_driver_manager import download_jdbc_driver

print("\n=== Testing SQLite Download ===")
print("Attempting to download SQLite JDBC driver...")

try:
    result = download_jdbc_driver(
        "sqlite",
        version="latest",
        on_status=lambda msg: print(f"  Status: {msg}"),
        on_progress=lambda d, t: print(f"  Progress: {d}/{t}")
    )
    
    if result:
        print(f"\n✅ Download successful!")
        if isinstance(result, list):
            for jar in result:
                print(f"   - {jar}")
                if os.path.exists(jar):
                    size = os.path.getsize(jar)
                    print(f"     Size: {size} bytes")
        else:
            print(f"   Path: {result}")
            if os.path.exists(result):
                size = os.path.getsize(result)
                print(f"   Size: {size} bytes")
    else:
        print("\n❌ Download returned None")
        
except Exception as e:
    print(f"\n❌ Download failed with error: {e}")
    import traceback
    traceback.print_exc()

# List what's in the driver directory
print(f"\n=== Contents of {driver_dir} ===")
if driver_dir.exists():
    files = list(driver_dir.iterdir())
    if files:
        for f in files:
            print(f"  - {f.name} ({f.stat().st_size} bytes)")
    else:
        print("  (empty)")
else:
    print("  (directory not found)")
