#!/usr/bin/env python3
"""Fix the class structure in provider_config_dialog.py to ensure all methods are properly within the class."""

import re

# Read the entire file to analyze its structure
with open('/workspaces/dbutils/src/dbutils/gui/provider_config_dialog.py', 'r') as f:
    content = f.read()

print("Analyzing file structure...")

# Find the class definition and where it should end
class_start = content.find('class ProviderConfigDialog(QDialog):')
if class_start != -1:
    print(f"Found class definition at position {class_start}")
    
    # Find all methods that should be within the class
    # Count indentation levels to determine if functions are properly nested
    lines = content.split('\n')
    
    in_class = False
    class_indent_level = 0
    method_indent_found = 0
    
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith('class ProviderConfigDialog'):
            in_class = True
            class_indent_level = len(line) - len(stripped)  # Count leading spaces
            print(f"Class starts at line {i+1} with indent level {class_indent_level}")
        elif in_class and stripped.startswith('def ') and len(line) - len(stripped) == class_indent_level:
            # This is a function at the same level as the class, which means the class ended
            print(f"Found function at same indent level as class at line {i+1}: {stripped}")
            print(f"This suggests the class may have ended before line {i+1}")
            in_class = False
        elif in_class and stripped.startswith('    def download_jdbc_driver_gui'):
            print(f"Found our method at line {i+1}, indent: {len(line) - len(stripped)}")
            method_indent_found = len(line) - len(stripped)
    
    print(f"Expected class indent: {class_indent_level}")
    print(f"Our method indent: {method_indent_found}")
    
    if method_indent_found and method_indent_found <= class_indent_level:
        print("ERROR: Method is not properly indented within the class!")
    else:
        print("Method indentation looks correct")
else:
    print("Class definition not found!")

print("Complete file structure analysis finished.")