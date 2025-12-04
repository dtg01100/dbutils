#!/usr/bin/env python3
"""
dbutils launcher with JDBC configuration manager fix
"""

import sys
import os

# Add the src directory to Python path
src_path = os.path.join(os.path.dirname(__file__), 'src')
sys.path.insert(0, src_path)

def main():
    """Launch the dbutils Qt application."""
    try:
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