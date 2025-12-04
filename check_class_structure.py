#!/usr/bin/env python3
import sys
sys.path.insert(0, 'src')

try:
    from dbutils.gui.provider_config_dialog import ProviderConfigDialog
    print("Successfully imported ProviderConfigDialog")
    
    # Try to instantiate
    print("Trying to check class definition...")
    
    import inspect
    
    # Get the source of the class to examine its structure
    class_source = inspect.getsource(ProviderConfigDialog)
    
    print("Class source retrieved")
    
    # Count occurrences of method definitions
    import re
    method_defs = re.findall(r'^\s*def\s+(\w+)', class_source, re.MULTILINE)
    print(f"Methods found in class definition: {len(method_defs)}")
    download_methods = [m for m in method_defs if 'download' in m.lower()]
    print(f"Download-related methods: {download_methods}")
    
    # Check if our function is there
    if 'download_jdbc_driver' in method_defs:
        print("✅ download_jdbc_driver method is in the class!")
    else:
        print("❌ download_jdbc_driver method is NOT in the class")
        
    # Show first few method names to see the pattern
    print(f"\nFirst 10 methods: {method_defs[:10]}")
    if len(method_defs) >= 10:
        print(f"Last 10 methods: {method_defs[-10:]}")
    else:
        print(f"Last methods: {method_defs}")
    
except SyntaxError as e:
    print(f"Syntax error in file: {e}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()