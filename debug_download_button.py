#!/usr/bin/env python3
"""Debug script to check download button state."""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

if "DBUTILS_TEST_MODE" in os.environ:
    del os.environ["DBUTILS_TEST_MODE"]

from PySide6.QtWidgets import QApplication
from dbutils.gui.provider_config_dialog import ProviderConfigDialog


def main():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    # Create the dialog
    dialog = ProviderConfigDialog()

    # Select a provider to make the download button visible
    print("Selecting SQLite provider...")
    for i in range(dialog.provider_list.count()):
        item = dialog.provider_list.item(i)
        if item and "SQLite" in item.text():
            dialog.provider_list.setCurrentItem(item)
            print(f"✅ Selected: {item.text()}")
            break

    # Check if download button exists
    if hasattr(dialog, "jar_download_btn"):
        btn = dialog.jar_download_btn
        print(f"\n✅ jar_download_btn exists")
        print(f"   - Visible: {btn.isVisible()}")
        print(f"   - Enabled: {btn.isEnabled()}")
        print(f"   - Text: {btn.text()}")

        # Check if it has connections
        try:
            receivers = btn.receivers("clicked")
            print(f"   - Click handlers connected: {receivers}")
        except Exception as e:
            print(f"   - Could not check receivers: {e}")

        # Try to programmatically trigger the click
        print("\nAttempting to trigger click...")

        call_count = 0

        original_method = dialog.download_jdbc_driver_gui

        def tracked_download():
            nonlocal call_count
            call_count += 1
            print(f"   ✅ download_jdbc_driver_gui() called (call #{call_count})")
            return original_method()

        dialog.download_jdbc_driver_gui = tracked_download

        try:
            btn.click()
            print(f"✅ Button click triggered")
            if call_count > 0:
                print(f"✅ Handler was executed ({call_count} times)")
            else:
                print(f"❌ Handler was NOT executed")
        except Exception as e:
            print(f"❌ Error during click: {e}")
            import traceback

            traceback.print_exc()

    else:
        print("❌ jar_download_btn not found on dialog")


if __name__ == "__main__":
    main()
