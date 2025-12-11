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
        # Import Qt modules
        from PySide6.QtWidgets import QApplication, QMainWindow, QLabel
        from PySide6.QtCore import Qt, QTimer
        print("PySide6 imported successfully")

        # Check if QApplication instance already exists
        from PySide6.QtCore import QCoreApplication

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

        # Add automatic close timer for test environments
        # This ensures the test doesn't hang and closes automatically
        def close_window():
            print("Closing window automatically...")
            window.close()
            # Force quit the application to ensure cleanup
            app.quit()

        # Set timer to close window after 2 seconds (2000 ms)
        # This is long enough to verify the window opens but short enough for tests
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(close_window)
        timer.start(2000)  # 2 seconds

        # Run event loop
        sys.exit(app.exec())

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()