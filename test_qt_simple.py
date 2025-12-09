#!/usr/bin/env python3
"""
Simple test to check if Qt application can run
"""

import os
import sys

# Add the src directory to Python path
src_path = os.path.join(os.path.dirname(__file__), "src")
sys.path.insert(0, src_path)

def main():
    """Test basic Qt functionality."""
    try:
        # Try to import Qt modules
        try:
            from PySide6.QtWidgets import QApplication, QMainWindow, QLabel
            from PySide6.QtCore import Qt
            print("PySide6 imported successfully")
        except ImportError:
            try:
                from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel
                from PyQt6.QtCore import Qt
                print("PyQt6 imported successfully")
            except ImportError as e:
                print(f"Cannot import Qt libraries: {e}")
                return

        # Check if QApplication instance already exists
        try:
            from PySide6.QtCore import QCoreApplication
        except ImportError:
            try:
                from PyQt6.QtCore import QCoreApplication
            except ImportError:
                QCoreApplication = None

        app = QCoreApplication.instance() if QCoreApplication else None
        if app is None:
            # Create new Qt application
            app = QApplication(sys.argv)
            print("Created new QApplication instance")
        else:
            # Use existing application instance
            print("Using existing QApplication instance")

        # Create a simple window
        window = QMainWindow()
        window.setWindowTitle("Qt Test")
        window.setGeometry(100, 100, 400, 300)

        # Add a label
        label = QLabel("Qt is working!", window)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("font-size: 24px; color: green;")
        window.setCentralWidget(label)

        window.show()
        print("Window shown")

        # Run event loop
        sys.exit(app.exec())

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()