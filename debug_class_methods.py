import sys

sys.path.insert(0, "src")

# Test to see all methods in the class
from dbutils.gui.provider_config_dialog import ProviderConfigDialog

print("Methods in ProviderConfigDialog class:")
methods = [method for method in dir(ProviderConfigDialog) if not method.startswith("_")]
for method in sorted(methods):
    if "download" in method.lower() or "Download" in method:
        print(f"  - {method}")

print("\nAll methods (including private):")
all_methods = [method for method in dir(ProviderConfigDialog) if callable(getattr(ProviderConfigDialog, method, None))]
download_related = [m for m in all_methods if "download" in m.lower()]
print("Download-related methods found:", download_related)

# Check if the specific method exists
has_method = hasattr(ProviderConfigDialog, "download_jdbc_driver")
print(f"\ndownload_jdbc_driver method exists: {has_method}")

if has_method:
    import inspect

    method = ProviderConfigDialog.download_jdbc_driver
    print(f"Method signature: {inspect.signature(method)}")
    print("Method properly bound to class: SUCCESS")
else:
    print("Method missing - checking for alternate names...")
    for attr in dir(ProviderConfigDialog):
        if "download" in attr.lower():
            obj = getattr(ProviderConfigDialog, attr)
            if callable(obj):
                print(f"  Found: {attr} (type: {type(obj)})")
