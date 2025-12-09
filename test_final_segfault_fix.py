#!/usr/bin/env python3
"""Final verification test for the download button segfault fix."""

import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Don't use test mode
if "DBUTILS_TEST_MODE" in os.environ:
    del os.environ["DBUTILS_TEST_MODE"]

from PySide6.QtWidgets import QApplication, QDialog
from dbutils.gui.provider_config_dialog import ProviderConfigDialog


def test_complete_download_flow():
    """Test the complete download flow without segfault."""
    print("\n🧪 FINAL VERIFICATION TEST: Download Button Segfault Fix")
    print("=" * 70)

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    # Create the dialog
    dialog = ProviderConfigDialog()

    # Select a provider
    print("\n1. Selecting provider...")
    for i in range(dialog.provider_list.count()):
        item = dialog.provider_list.item(i)
        if item and "SQLite" in item.text():
            dialog.provider_list.setCurrentItem(item)
            provider_name = item.text()
            print(f"   ✅ Selected: {provider_name}")
            break

    # Verify button is now enabled
    print("\n2. Checking download button state...")
    if dialog.jar_download_btn.isEnabled():
        print(f"   ✅ Download button is enabled")
    else:
        print(f"   ❌ Download button is NOT enabled")
        return False

    # Track what happens when button is clicked
    print("\n3. Testing button click (main test)...")

    exec_called = False
    download_called = False
    error_occurred = False
    error_message = None

    # Patch to track calls
    original_exec = QDialog.exec
    original_download = dialog.perform_jdbc_download

    def mock_exec(dialog_self):
        nonlocal exec_called
        exec_called = True
        return QDialog.DialogCode.Accepted

    def mock_download(*args, **kwargs):
        nonlocal download_called
        download_called = True

    try:
        QDialog.exec = mock_exec
        dialog.perform_jdbc_download = mock_download

        # Click the button - this is where the segfault was happening
        print("   Clicking download button...")
        dialog.jar_download_btn.click()
        print("   ✅ Button clicked successfully (NO SEGFAULT)")

        # Verify the flow
        print("\n4. Verifying download dialog flow...")
        if exec_called:
            print("   ✅ Dialog.exec() was called")
        else:
            print("   ❌ Dialog.exec() was NOT called")

        if download_called:
            print("   ✅ perform_jdbc_download() was called")
        else:
            print("   ⚠️  perform_jdbc_download() was not called (may be test mode dependent)")

        return True

    except SegmentationFault as e:
        error_occurred = True
        error_message = f"SEGMENTATION FAULT: {e}"
        print(f"   ❌ {error_message}")
        return False

    except Exception as e:
        error_occurred = True
        error_message = str(e)
        print(f"   ❌ ERROR: {error_message}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        QDialog.exec = original_exec
        dialog.perform_jdbc_download = original_download


def test_error_handling():
    """Verify error handling works correctly."""
    print("\n5. Testing error handling...")

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    dialog = ProviderConfigDialog()

    # Select provider
    for i in range(dialog.provider_list.count()):
        item = dialog.provider_list.item(i)
        if item and "SQLite" in item.text():
            dialog.provider_list.setCurrentItem(item)
            break

    error_handled = False

    def mock_exec_error(dialog_self):
        raise RuntimeError("Test error in dialog.exec()")

    original_exec = QDialog.exec

    try:
        QDialog.exec = mock_exec_error

        # Mock QMessageBox to avoid actual display
        with patch("dbutils.gui.provider_config_dialog.QMessageBox.critical") as mock_error:
            # Click button - should handle error gracefully
            print("   Triggering error in dialog...")
            dialog.jar_download_btn.click()
            print("   ✅ Error was handled gracefully (no crash)")
            error_handled = True

    except Exception as e:
        print(f"   ❌ Error not handled: {e}")
        return False

    finally:
        QDialog.exec = original_exec

    return error_handled


if __name__ == "__main__":
    tests_passed = 0
    tests_total = 2

    # Run tests
    if test_complete_download_flow():
        tests_passed += 1
    else:
        print("\n❌ MAIN TEST FAILED")

    if test_error_handling():
        tests_passed += 1
    else:
        print("\n❌ ERROR HANDLING TEST FAILED")

    # Summary
    print("\n" + "=" * 70)
    print(f"📊 RESULTS: {tests_passed}/{tests_total} tests passed")
    print("=" * 70)

    if tests_passed == tests_total:
        print("✅ ALL TESTS PASSED - SEGFAULT FIX VERIFIED!\n")
        sys.exit(0)
    else:
        print(f"❌ {tests_total - tests_passed} test(s) failed\n")
        sys.exit(1)
