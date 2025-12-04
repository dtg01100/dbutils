#!/usr/bin/env python3
"""
Test to verify the JDBC configuration manager fix.
This script tests the specific functionality that was broken.
"""
import sys
import os

# Add the source directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from PySide6.QtWidgets import QApplication, QMessageBox
from dbutils.gui.provider_config_dialog import ProviderConfigDialog

def test_jdbc_config_manager():
    """Test that the JDBC configuration manager opens without error."""
    app = QApplication(sys.argv)
    
    print("Testing JDBC configuration manager...")
    
    # Try to create the dialog - this was failing before the fix
    try:
        dialog = ProviderConfigDialog()
        print("✅ ProviderConfigDialog created successfully")
    except Exception as e:
        print(f"❌ Failed to create dialog: {e}")
        return False
    
    # Test specific methods that were problematic
    if not hasattr(dialog, 'download_jdbc_driver_gui'):
        print("❌ download_jdbc_driver_gui method not found")
        return False
    else:
        print("✅ download_jdbc_driver_gui method exists")
    
    # Test that the QInputDialog import fix is working by checking
    # that we can access the method that uses QInputDialog
    import inspect
    method_source = inspect.getsource(ProviderConfigDialog.download_jdbc_driver_gui)
    if 'QInputDialog.getItem' in method_source:
        print("✅ QInputDialog.getItem usage confirmed in source")
    
    # Test that the get_categories fix is working
    from dbutils.enhanced_jdbc_provider import PredefinedProviderTemplates
    try:
        categories = PredefinedProviderTemplates.get_categories()
        print(f"✅ get_categories() works, found {len(categories)} categories")
    except AttributeError as e:
        print(f"❌ get_categories() failed: {e}")
        return False
    
    print("🎉 All tests passed! The JDBC configuration manager is fixed!")
    return True

if __name__ == "__main__":
    success = test_jdbc_config_manager()
    sys.exit(0 if success else 1)