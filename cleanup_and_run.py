#!/usr/bin/env python3
"""
Script to cleanup any existing QApplication instances and run the dbutils Qt application.
"""

import os
import sys
import gc

# Add the src directory to Python path
src_path = os.path.join(os.path.dirname(__file__), "src")
sys.path.insert(0, src_path)

def cleanup_qt_instances():
    """Try to cleanup any existing QApplication instances."""
    try:
        # Import Qt modules
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import QCoreApplication

        # Check if there's an existing instance
        existing_instance = QCoreApplication.instance()
        if existing_instance is not None:
            print(f"Found existing QApplication instance: {existing_instance}")
            try:
                # Try to quit the existing application
                existing_instance.quit()
                print("Existing QApplication instance quit() called")
            except Exception as e:
                print(f"Error quitting existing instance: {e}")

            # Force garbage collection
            gc.collect()
            print("Garbage collection completed")

    except ImportError:
        print("PySide6 not available, skipping cleanup")
    except Exception as e:
        print(f"Error during cleanup: {e}")

def main():
    """Launch the dbutils Qt application after cleanup."""
    try:
        cleanup_qt_instances()

        # Import the Qt application
        from dbutils.gui.qt_app import main as qt_main

        # Run the Qt application main function
        qt_main()
    except ImportError as e:
        print(f"Import error: {e}")
        print("Make sure all dependencies are installed:")
        print("pip install --break-system-packages PySide6 JPype1 JayDeBeApi")
        sys.exit(1)
    except Exception as e:
        print(f"Error running application: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()