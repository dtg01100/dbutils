#!/usr/bin/env python3
"""
Test script to verify the JDBC configuration dialog import fix.
"""

import sys
import traceback

# Add the src directory to the Python path
sys.path.insert(0, "src")


def test_imports():
    """Test if the provider config dialog imports correctly"""
    print("Testing imports for ProviderConfigDialog...")

    # Try importing the dialog
    try:
        from dbutils.gui.provider_config_dialog import ProviderConfigDialog

        print("✅ Import successful")
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"❌ Unexpected error during import: {e}")
        traceback.print_exc()
        return False

    # Check if the basic class structure is valid
    try:
        # Just check if the class exists - we can't instantiate without Qt
        if hasattr(ProviderConfigDialog, "__init__"):
            print("✅ ProviderConfigDialog class exists")
        else:
            print("❌ ProviderConfigDialog class missing __init__")
            return False
    except Exception as e:
        print(f"❌ Error checking class structure: {e}")
        traceback.print_exc()
        return False

    # Try to check if QInputDialog is accessible where needed
    try:
        with open("src/dbutils/gui/provider_config_dialog.py", "r") as f:
            content = f.read()

        # Check if our import fix is in place
        if (
            "from PySide6.QtWidgets import QInputDialog" in content
            and "from PyQt6.QtWidgets import QInputDialog" in content
        ):
            print("✅ QInputDialog import fix is in place")
        else:
            print("❌ QInputDialog import fix not properly implemented")
            return False

        # Check if QInputDialog.getItem is used (this should be there)
        if "QInputDialog.getItem(" in content:
            print("✅ QInputDialog.getItem usage found in code")
        else:
            print("⚠️  QInputDialog.getItem usage not found (might be OK)")

    except Exception as e:
        print(f"❌ Error checking file content: {e}")
        traceback.print_exc()
        return False

    print("\n🎉 All checks passed! The fix appears to be working correctly.")
    return True


if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)
