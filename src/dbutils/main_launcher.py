#!/usr/bin/env python3
"""Qt-only launcher for DB Browser.

Launches the Qt GUI interface exclusively with JDBC support.
"""

import argparse
import sys


def check_gui_availability() -> bool:
    """Check if Qt GUI environment is available."""
    # Prefer using importlib.util.find_spec to test availability without
    # importing heavy GUI modules into the process. This avoids unused
    # import linter warnings and reduces startup cost.
    from importlib import util as _util

    return bool(_util.find_spec("PySide6"))


def main():
    """Main Qt-only launcher entry point."""
    parser = argparse.ArgumentParser(
        description="Qt-only DB Browser Launcher - Always launches Qt GUI interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s               # Launch Qt GUI interface
  %(prog)s --mock      # Launch with mock data for testing
  %(prog)s --heavy-mock # Launch with heavy mock data (stress test)
  %(prog)s --schema MYLIB # Launch with specific schema filter
        """,
    )

    # Qt interface options
    interface_group = parser.add_argument_group("Qt GUI Options")
    interface_group.add_argument("--no-streaming", action="store_true", help="Disable streaming search in Qt mode")

    # Standard options (passed through to interface)
    parser.add_argument("--schema", help="Filter by specific schema (default: DACDATA)", default="DACDATA")
    parser.add_argument("--mock", action="store_true", help="Use mock data for testing")
    parser.add_argument("--heavy-mock", action="store_true", 
                       help="Use heavy mock data for stress testing (5 schemas, 50 tables each, 20 cols)")
    parser.add_argument("--install-deps", action="store_true", help="Show required Qt dependencies")

    args = parser.parse_args()

    # Handle dependency installation
    if args.install_deps:
        print("📦 Qt DB Browser Dependencies:")
        print("\n🖥️  Qt GUI Mode (Required):")
        print("   pip install PySide6")
        print("\n🔌 JDBC Support (Required):")
        print("   pip install JPype1 JayDeBeApi")
        print("\n📊 Rich Formatting (Optional):")
        print("   pip install rich")
        print("\n💡 Recommendation: Install all for full functionality")
        return

    # Launch Qt interface directly
    print("🚀 Launching Qt GUI interface...")
    launch_qt_interface(args)


def launch_qt_interface(args) -> None:
    """Launch Qt GUI interface."""
    try:
        from .gui.qt_app import main as qt_main

        # Set environment variables based on arguments if needed
        if args.schema:
            # This would be handled inside the Qt app, but we can pass as needed
            pass

        print("🖥️  Launching Qt GUI interface with JDBC support...")
        qt_main(args)
    except ImportError as e:
        print("❌ Error: Qt libraries not available")
        print(f"   {e}")
        print("\n💡 To install Qt support:")
        print("   pip install PySide6")
        sys.exit(1)


if __name__ == "__main__":
    main()
