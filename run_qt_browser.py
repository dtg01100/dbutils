#!/usr/bin/env python3
"""Simple script to run the Qt DB Browser interface."""

import os
import sys

# Add the src directory to the path to import dbutils
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from dbutils.gui.qt_app import main

if __name__ == "__main__":
    main()
