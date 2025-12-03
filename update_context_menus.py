#!/usr/bin/env python3
"""Script to add enhanced context menus to all node types.

Helper script to update generated context menu code in the Qt GUI module. It
is intended for developer convenience, edits `src/dbutils/gui/qt_app.py`
and can be run manually when a richer contextMenuEvent implementation is
required for node classes.
"""

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

# Read the file
path = Path("src/dbutils/gui/qt_app.py")
content = path.read_text(encoding="utf-8")

# Define the generic disconnect methods that will be added
disconnect_methods = """
    def disconnect_all(self):
        for conn in self.connections[:]:
            self.disconnect_single(conn)

    def disconnect_single(self, connection):
        if hasattr(connection, 'source_node') and hasattr(connection, 'target_node'):
            if connection in connection.source_node.connections:
                connection.source_node.connections.remove(connection)
            if connection in connection.target_node.connections:
                connection.target_node.connections.remove(connection)
            if hasattr(connection, 'source_port') and hasattr(connection.source_port, 'update_appearance'):
                connection.source_port.update_appearance()
            if hasattr(connection, 'target_port') and hasattr(connection.target_port, 'update_appearance'):
                connection.target_port.update_appearance()
            if connection.scene():
                connection.scene().removeItem(connection)
"""

# Node-specific menu configurations
node_configs = {
    "ProjectionNodeItem": {
        "edit_actions": [
            ("✏️ Edit Columns", "columns_text"),
        ],
    },
    "OrderByNodeItem": {
        "edit_actions": [
            ("✏️ Edit Order Expression", "order_text"),
        ],
    },
    "LimitNodeItem": {
        "edit_actions": [
            ("✏️ Edit Limit", "limit_text"),
            ("✏️ Edit Offset", "offset_text"),
        ],
    },
    "SubqueryNodeItem": {
        "edit_actions": [
            ("✏️ Edit Correlation Condition", "correlation_text"),
        ],
    },
    "UnionNodeItem": {
        "toggle_actions": [
            ("⚡ Toggle ALL/DISTINCT", "toggle_union_all"),
        ],
    },
    "OutputNodeItem": {
        "edit_actions": [],  # No edit actions, just disconnect and delete
    },
    "TableNodeItem": {
        "view_actions": [
            ("📋 Show Columns", "show_columns"),
        ],
    },
}


# Function to create context menu code
def create_context_menu(node_name, config):
    menu_code = """    def contextMenuEvent(self, event):
        from PySide6.QtWidgets import QMenu
        menu = QMenu()

"""

    # Add edit actions
    if "edit_actions" in config:
        for label, field in config["edit_actions"]:
            menu_code += f"""        edit_action = menu.addAction("{label}")
        edit_action.triggered.connect(lambda: self.{field}.setFocus())

"""

    # Add toggle actions
    if "toggle_actions" in config:
        for label, method in config["toggle_actions"]:
            menu_code += f"""        toggle_action = menu.addAction("{label}")
        toggle_action.triggered.connect(self.{method})

"""

    # Add view actions
    if "view_actions" in config:
        for label, method in config["view_actions"]:
            menu_code += f"""        view_action = menu.addAction("{label}")
        view_action.triggered.connect(self.{method})

"""

    if config.get("edit_actions") or config.get("toggle_actions") or config.get("view_actions"):
        menu_code += """        menu.addSeparator()

"""

    # Add disconnect section
    menu_code += """        # Disconnect options
        if self.connections:
            disconnect_menu = menu.addMenu("🔌 Disconnect")
            disconnect_all = disconnect_menu.addAction("All Connections")
            disconnect_all.triggered.connect(self.disconnect_all)

            disconnect_menu.addSeparator()
            for conn in self.connections:
                # Build a readable connection label in a few steps to keep
                # the generated source lines short and readable for linters.
                tgt = conn.source_node if conn.target_node == self else conn.target_node
                tgt_name = getattr(tgt, "table_name", "Node")
                conn_name = f"Connection to {tgt_name}"
                disconnect_single = disconnect_menu.addAction(conn_name)
                disconnect_single.triggered.connect(lambda checked=False, c=conn: self.disconnect_single(c))

        menu.addSeparator()
        delete_action = menu.addAction("🗑️ Delete Node")
        delete_action.triggered.connect(self.delete_node)
        menu.exec(event.screenPos())
"""

    return menu_code


# Process each node type
for node_name, config in node_configs.items():
    # Find the old contextMenuEvent for this node
    pattern = (
        rf"(class {node_name}\(.*?\n(?:.*?\n)*?)"
        r"    def contextMenuEvent\(self, event\):\s*\n"
        r"        from PySide6\.QtWidgets import QMenu\s*\n"
        r"        menu = QMenu\(\)\s*\n"
        r'        delete_action = menu\.addAction\("🗑️ Delete Node"\)\s*\n'
        r"        delete_action\.triggered\.connect\(self\.delete_node\)\s*\n"
        r"        menu\.exec\(event\.screenPos\(\)\)\s*\n"
    )

    matches = list(re.finditer(pattern, content, re.DOTALL))
    if matches:
        logger.info("Updating %s...", node_name)
        match = matches[0]

        # Create the new contextMenuEvent
        new_menu = create_context_menu(node_name, config)

        # Replace old menu with new one
        old_section = match.group(0)
        new_section = match.group(1) + new_menu + "\n"

        # Check if disconnect methods already exist for this class
        # Look for delete_node method position
        delete_pattern = rf"({re.escape(new_section)})    def delete_node\(self\):"

        # Add disconnect methods before delete_node if they don't exist
        if "disconnect_all" not in content[match.start() : match.start() + 2000]:
            new_section = new_section + disconnect_methods + "\n    def delete_node(self):"
            content = content[: match.start()] + new_section + content[match.end() :]
        else:
            content = content[: match.start()] + new_section + content[match.end() :]
    else:
        logger.warning("Could not find contextMenuEvent for %s", node_name)

# Write back
path.write_text(content, encoding="utf-8")
logger.info("Done updating context menus")
