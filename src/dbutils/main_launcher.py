#!/usr/bin/env python3
"""Smart launcher for DB Browser - Chooses optimal interface based on environment.

Automatically selects between Qt GUI, Textual TUI, or CLI based on:
- Display availability (X11/Wayland)
- User preferences
- Environment constraints
- Command line arguments
"""

import argparse
import os
import sys
from typing import Optional


def detect_display_environment() -> str:
    """Detect the display environment."""
    # Check for explicit display
    if os.environ.get("DISPLAY"):
        return "x11"
    if os.environ.get("WAYLAND_DISPLAY"):
        return "wayland"
    if os.environ.get("SSH_CONNECTION") or os.environ.get("SSH_CLIENT"):
        return "ssh"
    if sys.platform == "win32":
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    return "headless"


def check_gui_availability() -> bool:
    """Check if GUI environment is available."""
    # Check for display server
    display_env = detect_display_environment()

    if display_env in ["x11", "wayland", "windows", "macos"]:
        # Prefer using importlib.util.find_spec to test availability without
        # importing heavy GUI modules into the process. This avoids unused
        # import linter warnings and reduces startup cost.
        from importlib import util as _util

        if _util.find_spec("PySide6") or _util.find_spec("PyQt6"):
            return True
        return False
    elif display_env == "ssh":
        # Check if X forwarding is available
        if os.environ.get("DISPLAY"):
            return check_gui_availability()
        return False

    return False


def check_tui_availability() -> bool:
    """Check if TUI environment is available."""
    from importlib import util as _util

    return bool(_util.find_spec("textual"))


def detect_user_preference() -> Optional[str]:
    """Detect user preference from config file."""
    config_files = [
        os.path.expanduser("~/.config/dbutils/config.json"),
        os.path.expanduser("~/.dbutils.json"),
        "dbutils.json",
    ]

    for config_file in config_files:
        if os.path.exists(config_file):
            try:
                import json

                with open(config_file) as f:
                    config = json.load(f)
                    return config.get("preferred_interface")
            except Exception:
                continue

    return None


def save_user_preference(interface: str) -> None:
    """Save user preference to config file."""
    config_dir = os.path.expanduser("~/.config/dbutils")
    os.makedirs(config_dir, exist_ok=True)
    config_file = os.path.join(config_dir, "config.json")

    try:
        import json

        config = {"preferred_interface": interface, "last_used": interface}

        with open(config_file, "w") as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not save preference: {e}")


def choose_best_interface(args) -> str:
    """Choose the best interface based on environment and arguments."""
    # Command line arguments take priority
    if args.force_gui:
        return "qt"
    if args.force_tui:
        return "textual"
    if args.force_cli:
        return "cli"

    # User preference
    user_pref = detect_user_preference()
    if user_pref:
        if user_pref in ["qt", "textual", "cli"]:
            return user_pref

    # Auto-detection based on environment
    gui_available = check_gui_availability()
    tui_available = check_tui_availability()

    if gui_available and tui_available:
        # Both available - prefer GUI for desktop environments
        display_env = detect_display_environment()
        if display_env in ["x11", "wayland", "windows", "macos"]:
            return "qt"
        # SSH or headless - prefer TUI
        return "textual"
    if gui_available:
        return "qt"
    if tui_available:
        return "textual"
    return "cli"


def launch_qt_interface(args) -> None:
    """Launch Qt GUI interface."""
    try:
        from .gui.qt_app import main as qt_main

        print("🖥️  Launching Qt GUI interface...")
        qt_main()
    except ImportError as e:
        print("❌ Error: Qt libraries not available")
        print(f"   {e}")
        print("\n💡 To install Qt support:")
        print("   pip install PySide6")
        print("   # or")
        print("   pip install PyQt6")
        sys.exit(1)


def launch_textual_interface(args) -> None:
    """Launch Textual TUI interface."""
    try:
        from .db_browser import main as textual_main

        print("🖥️  Launching Textual TUI interface...")
        textual_main()
    except ImportError as e:
        print("❌ Error: Textual library not available")
        print(f"   {e}")
        print("\n💡 To install TUI support:")
        print("   pip install textual")
        sys.exit(1)


def launch_cli_interface(args) -> None:
    """Launch CLI interface."""
    try:
        from .db_browser import search_and_output

        if not args.search:
            print("❌ CLI mode requires --search argument")
            sys.exit(1)

        print("⌨️  Launching CLI interface...")
        search_and_output(args.search, args.schema, args.limit, args.format, args.mock)
    except Exception as e:
        print(f"❌ Error in CLI mode: {e}")
        sys.exit(1)


def show_environment_info() -> None:
    """Show environment detection information."""
    print("🔍 Environment Detection Results:")
    print(f"   Display Environment: {detect_display_environment()}")
    print(f"   GUI Available: {check_gui_availability()}")
    print(f"   TUI Available: {check_tui_availability()}")
    print(f"   User Preference: {detect_user_preference()}")

    display_env = detect_display_environment()
    if display_env == "ssh":
        print(f"   SSH Session: {bool(os.environ.get('SSH_CONNECTION'))}")
        if os.environ.get("DISPLAY"):
            print(f"   X Forwarding: {os.environ.get('DISPLAY')}")

    print()


def main():
    """Main launcher entry point."""
    parser = argparse.ArgumentParser(
        description="Smart DB Browser Launcher - Chooses optimal interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Auto-detect best interface
  %(prog)s --force-gui            # Force Qt GUI mode
  %(prog)s --force-tui            # Force Textual TUI mode
  %(prog)s --force-cli --search user # Force CLI mode with search
  %(prog)s --info                 # Show environment detection info
        """,
    )

    # Interface selection options
    interface_group = parser.add_argument_group("Interface Selection")
    interface_group.add_argument("--force-gui", action="store_true", help="Force Qt GUI interface")
    interface_group.add_argument("--force-tui", action="store_true", help="Force Textual TUI interface")
    interface_group.add_argument("--force-cli", action="store_true", help="Force CLI interface")

    # Information options
    info_group = parser.add_argument_group("Information")
    info_group.add_argument("--info", action="store_true", help="Show environment detection information")

    # Standard options (passed through to interfaces)
    parser.add_argument("--schema", help="Filter by specific schema (default: DACDATA)", default="DACDATA")
    parser.add_argument("--search", "-s", help="Search query (activates CLI mode)")
    parser.add_argument("--limit", "-l", type=int, default=10, help="Limit number of results in CLI mode (default: 10)")
    parser.add_argument(
        "--format",
        choices=["table", "json", "csv"],
        default="table",
        help="Output format for CLI mode (default: table)",
    )
    parser.add_argument("--mock", action="store_true", help="Use mock data for testing")
    parser.add_argument("--no-streaming", action="store_true", help="Disable streaming search (Qt mode)")
    parser.add_argument("--install-deps", action="store_true", help="Show required dependencies")

    args = parser.parse_args()

    # Handle dependency installation
    if args.install_deps:
        print("📦 DB Browser Dependencies:")
        print("\n🖥️  Qt GUI Mode:")
        print("   pip install PySide6")
        print("   # or")
        print("   pip install PyQt6")
        print("\n🖥️  Textual TUI Mode:")
        print("   pip install textual")
        print("\n📊 Rich CLI Mode:")
        print("   pip install rich")
        print("\n🔧 Core Dependencies:")
        print("   pip install ibm_db")
        print("   pip install asyncio")
        print("\n💡 Recommendation: Install all for full flexibility")
        return

    # Show environment info
    if args.info:
        show_environment_info()
        return

    # Choose and launch interface
    interface = choose_best_interface(args)

    # Save user preference (except for forced modes)
    if not any([args.force_gui, args.force_tui, args.force_cli]):
        save_user_preference(interface)

    print(f"🚀 Launching {interface.upper()} interface...")

    # Launch the chosen interface
    if interface == "qt":
        launch_qt_interface(args)
    elif interface == "textual":
        launch_textual_interface(args)
    else:
        launch_cli_interface(args)


if __name__ == "__main__":
    main()
