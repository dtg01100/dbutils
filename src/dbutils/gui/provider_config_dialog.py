"""
Enhanced JDBC Provider Configuration Dialog
Similar to DBeaver's approach with simple defaults and advanced options hidden initially
"""

from __future__ import annotations

import os
from typing import Optional

# Try to import Qt components
try:
    from PySide6.QtCore import *
    from PySide6.QtGui import *
    from PySide6.QtWidgets import *

    QT_BINDINGS = "PySide6"
except ImportError:
    try:
        from PyQt6.QtCore import *
        from PyQt6.QtGui import *
        from PyQt6.QtWidgets import *

        QT_BINDINGS = "PyQt6"
    except ImportError:
        # If no Qt bindings available, create dummy classes for documentation
        QT_BINDINGS = None
        QWidget = object
        QVBoxLayout = object
        QHBoxLayout = object
        QFormLayout = object
        QGroupBox = object
        QListWidget = object
        QComboBox = object
        QLineEdit = object
        QSpinBox = object
        QTextEdit = object
        QPushButton = object
        QDialog = object
        QSplitter = object
        QScrollArea = object
        QTableWidget = object
        QTableWidgetItem = object
        QMessageBox = object
        QFileDialog = object
        QInputDialog = object
        QCheckBox = object


if QT_BINDINGS:
    if QT_BINDINGS == "PySide6":
        from PySide6.QtWidgets import QInputDialog
    else:  # PyQt6
        from PyQt6.QtWidgets import QInputDialog

    from dbutils.enhanced_jdbc_provider import EnhancedProviderRegistry, JDBCProvider, PredefinedProviderTemplates

    class ProviderConfigDialog(QDialog):
        """JDBC Provider Configuration Dialog with DBeaver-like approach."""

        def __init__(self, parent=None):
            super().__init__(parent)
            self.setWindowTitle("JDBC Provider Configuration")
            self.resize(800, 600)

            self.registry = EnhancedProviderRegistry()
            self.current_provider: Optional[JDBCProvider] = None

            self.setup_ui()
            self.refresh_provider_list()

        def setup_ui(self):
            """Set up the user interface."""
            layout = QVBoxLayout(self)

            # Main splitter for list/provider details
            splitter = QSplitter(Qt.Orientation.Horizontal)

            # Left side: Provider list and quick add
            left_panel = QWidget()
            left_layout = QVBoxLayout(left_panel)

            # Search box for providers
            self.search_box = QLineEdit()
            self.search_box.setPlaceholderText("Search providers...")
            self.search_box.textChanged.connect(self.filter_providers)
            left_layout.addWidget(QLabel("Providers:"))
            left_layout.addWidget(self.search_box)

            # Provider list
            self.provider_list = QListWidget()
            self.provider_list.setMaximumWidth(250)
            self.provider_list.itemSelectionChanged.connect(self.provider_selected)
            left_layout.addWidget(self.provider_list)

            # Quick-add buttons
            quick_add_layout = QHBoxLayout()
            self.quick_add_combo = QComboBox()
            # Create instance of PredefinedProviderTemplates to call instance method
            templates = PredefinedProviderTemplates()
            self.quick_add_combo.addItems(["Select database type..."] + templates.get_categories())
            self.quick_add_btn = QPushButton("Add from Template")
            self.quick_add_btn.clicked.connect(self.add_from_template)
            quick_add_layout.addWidget(self.quick_add_combo)
            quick_add_layout.addWidget(self.quick_add_btn)

            # Add custom provider button
            self.custom_provider_btn = QPushButton("Add Custom Provider")
            self.custom_provider_btn.clicked.connect(self.add_custom_provider)
            quick_add_layout.addWidget(self.custom_provider_btn)

            left_layout.addLayout(quick_add_layout)

            # Buttons for provider management
            provider_btn_layout = QHBoxLayout()
            self.add_btn = QPushButton("Add")
            self.edit_btn = QPushButton("Edit")
            self.delete_btn = QPushButton("Delete")
            self.reset_btn = QPushButton("Reset to Defaults")

            self.add_btn.clicked.connect(self.add_provider)
            self.edit_btn.clicked.connect(self.edit_selected)
            self.delete_btn.clicked.connect(self.delete_selected)
            self.reset_btn.clicked.connect(self.reset_defaults)

            provider_btn_layout.addWidget(self.add_btn)
            provider_btn_layout.addWidget(self.edit_btn)
            provider_btn_layout.addWidget(self.delete_btn)
            provider_btn_layout.addStretch()
            provider_btn_layout.addWidget(self.reset_btn)
            left_layout.addLayout(provider_btn_layout)

            splitter.addWidget(left_panel)

            # Right side: Provider configuration
            self.setup_provider_config_ui()
            splitter.addWidget(self.right_panel)

            # Set initial sizes for splitter
            splitter.setSizes([250, 550])

            layout.addWidget(splitter)

            # Add OK/Cancel buttons
            button_layout = QHBoxLayout()
            button_layout.addStretch()
            ok_btn = QPushButton("OK")
            cancel_btn = QPushButton("Cancel")
            ok_btn.clicked.connect(self.accept)
            cancel_btn.clicked.connect(self.reject)
            button_layout.addWidget(ok_btn)
            button_layout.addWidget(cancel_btn)
            layout.addLayout(button_layout)

            # Initially disable edit/delete buttons
            self.update_buttons_state()

        def setup_provider_config_ui(self):
            """Set up the provider configuration area."""
            self.right_panel = QWidget()
            right_layout = QVBoxLayout(self.right_panel)

            # Scroll area for the configuration form
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            self.config_widget = QWidget()
            config_vbox = QVBoxLayout(self.config_widget)  # Use a VBox for the main configuration layout

            # Basic settings (always visible)
            self.basic_group = QGroupBox("Basic Settings")
            self.basic_group.setCheckable(False)  # Always expanded
            self.basic_layout = QFormLayout(self.basic_group)

            self.name_input = QLineEdit()
            self.category_input = QComboBox()
            # Create instance of PredefinedProviderTemplates to call instance method
            templates = PredefinedProviderTemplates()
            self.category_input.addItems(templates.get_categories())
            self.host_input = QLineEdit("localhost")
            self.port_input = QSpinBox()
            self.port_input.setRange(0, 65535)
            self.database_input = QLineEdit()

            self.basic_layout.addRow("Name*", self.name_input)
            self.basic_layout.addRow("Category", self.category_input)
            self.basic_layout.addRow("Host", self.host_input)
            self.basic_layout.addRow("Port", self.port_input)
            self.basic_layout.addRow("Database", self.database_input)

            # Driver settings (initially collapsed like in DBeaver)
            self.driver_group = QGroupBox("Driver Settings")
            self.driver_group.setCheckable(True)  # Make it collapsible
            self.driver_group.setChecked(False)  # Collapsed by default (like DBeaver)
            self.driver_layout = QFormLayout(self.driver_group)

            self.driver_class_input = QLineEdit()
            self.jar_path_input = QLineEdit()
            self.jar_browse_btn = QPushButton("Browse...")
            self.jar_browse_btn.clicked.connect(self.browse_jar_file)

            # Add download button for JDBC drivers
            self.jar_download_btn = QPushButton("Download…")
            self.jar_download_btn.clicked.connect(self.download_jdbc_driver_gui)

            jar_layout = QHBoxLayout()
            jar_layout.addWidget(self.jar_path_input)
            jar_layout.addWidget(self.jar_browse_btn)
            jar_layout.addWidget(self.jar_download_btn)

            self.driver_layout.addRow("Driver Class*", self.driver_class_input)
            self.driver_layout.addRow("JAR File*", jar_layout)

            # Connection settings (initially expanded for better UX)
            self.connection_group = QGroupBox("Connection Settings")
            self.connection_group.setCheckable(True)
            self.connection_group.setChecked(True)  # Expanded by default for visibility
            self.connection_layout = QFormLayout(self.connection_group)

            self.username_input = QLineEdit()
            self.password_input = QLineEdit()
            self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.url_template_input = QTextEdit()
            self.url_template_input.setMaximumHeight(80)  # Limit height

            self.connection_layout.addRow("Username", self.username_input)
            self.connection_layout.addRow("Password", self.password_input)
            self.connection_layout.addRow("URL Template", self.url_template_input)

            # Advanced properties (initially collapsed)
            self.advanced_group = QGroupBox("Advanced Properties")
            self.advanced_group.setCheckable(True)
            self.advanced_group.setChecked(False)  # Collapsed by default
            self.advanced_layout = QVBoxLayout(self.advanced_group)

            self.properties_table = QTableWidget()
            self.properties_table.setColumnCount(2)
            self.properties_table.setHorizontalHeaderLabels(["Property", "Value"])
            self.properties_table.horizontalHeader().setStretchLastSection(True)

            advanced_btn_layout = QHBoxLayout()
            self.add_prop_btn = QPushButton("Add Property")
            self.remove_prop_btn = QPushButton("Remove Selected")
            self.add_prop_btn.clicked.connect(self.add_property_row)
            self.remove_prop_btn.clicked.connect(self.remove_property_row)
            advanced_btn_layout.addWidget(self.add_prop_btn)
            advanced_btn_layout.addWidget(self.remove_prop_btn)
            advanced_btn_layout.addStretch()

            self.advanced_layout.addWidget(self.properties_table)
            self.advanced_layout.addLayout(advanced_btn_layout)

            config_vbox.addWidget(self.basic_group)
            config_vbox.addWidget(self.driver_group)
            config_vbox.addWidget(self.connection_group)
            config_vbox.addWidget(self.advanced_group)
            config_vbox.addStretch()  # Push everything up

            scroll_area.setWidget(self.config_widget)
            right_layout.addWidget(scroll_area)

            # Connect change handlers to enable save button
            self.name_input.textChanged.connect(self.on_inputs_changed)
            self.category_input.currentTextChanged.connect(self.on_inputs_changed)
            self.driver_class_input.textChanged.connect(self.on_inputs_changed)
            self.jar_path_input.textChanged.connect(self.on_inputs_changed)
            self.url_template_input.textChanged.connect(self.on_inputs_changed)

        def refresh_provider_list(self, filter_text: str = ""):
            """Refresh the provider list, optionally with a filter."""
            self.provider_list.clear()

            providers = self.registry.list_providers()
            if filter_text:
                filter_lower = filter_text.lower()
                providers = [
                    p for p in providers if filter_lower in p.name.lower() or filter_lower in p.category.lower()
                ]

            for provider in sorted(providers, key=lambda p: (p.category, p.name)):
                item = QListWidgetItem(f"{provider.category}: {provider.name}")
                item.setData(Qt.ItemDataRole.UserRole, provider.name)
                self.provider_list.addItem(item)

            # Do not auto-select a provider here; allow explicit user selection to populate the form

        def filter_providers(self, text: str):
            """Filter provider list based on search text."""
            self.refresh_provider_list(text)

        def provider_selected(self):
            """Handle provider selection in the list."""
            items = self.provider_list.selectedItems()
            if items:
                provider_name = items[0].data(Qt.ItemDataRole.UserRole)
                provider = self.registry.get_provider(provider_name)
                if provider:
                    self.load_provider_into_form(provider)
                else:
                    self.clear_form()
            else:
                self.clear_form()

            self.update_buttons_state()

        def load_provider_into_form(self, provider: JDBCProvider):
            """Load provider data into the configuration form."""
            self.current_provider = provider

            # Basic settings
            self.name_input.setText(provider.name)
            self.category_input.setCurrentText(provider.category)

            # Connection settings (use default values if available)
            self.host_input.setText(provider.default_host or "localhost")
            self.port_input.setValue(provider.default_port or 0)
            self.database_input.setText(provider.default_database or "")

            # Driver settings
            self.driver_class_input.setText(provider.driver_class)
            self.jar_path_input.setText(provider.jar_path)

            # Connection details
            self.username_input.setText(provider.default_user or "")
            self.password_input.setText(provider.default_password or "")
            self.url_template_input.setPlainText(provider.url_template)

            # Advanced properties
            self.load_properties_to_table(provider.extra_properties or {})

        def load_properties_to_table(self, properties: dict):
            """Load properties dict into the properties table."""
            self.properties_table.setRowCount(0)  # Clear existing rows
            row = 0
            for key, value in properties.items():
                self.properties_table.insertRow(row)
                key_item = QTableWidgetItem(key)
                value_item = QTableWidgetItem(value)
                self.properties_table.setItem(row, 0, key_item)
                self.properties_table.setItem(row, 1, value_item)
                row += 1

        def clear_form(self):
            """Clear the configuration form."""
            self.current_provider = None
            self.name_input.clear()
            self.category_input.setCurrentText("Generic")
            self.host_input.setText("localhost")
            self.port_input.setValue(0)
            self.database_input.clear()
            self.driver_class_input.clear()
            self.jar_path_input.clear()
            self.username_input.clear()
            self.password_input.clear()
            self.url_template_input.clear()
            self.properties_table.setRowCount(0)

        def update_buttons_state(self):
            """Update the enabled state of buttons based on selection."""
            has_selection = len(self.provider_list.selectedItems()) > 0
            self.edit_btn.setEnabled(has_selection)
            self.delete_btn.setEnabled(has_selection)
            # Enable download button if a provider is selected
            self.jar_download_btn.setEnabled(has_selection)

        def on_inputs_changed(self):
            """Handle input changes to enable save functionality."""
            # Inputs changed, so we'd enable save if implementing live save
            pass

        def add_provider(self):
            """Add a new blank provider."""
            new_provider = JDBCProvider(
                name="New Provider",
                category="Generic",
                driver_class="",
                jar_path="",
                url_template="",
                default_host="localhost",
                default_port=0,
                default_database="",
                default_user=None,
                default_password=None,
                extra_properties={},
            )
            self.current_provider = new_provider
            self.load_provider_into_form(new_provider)

            # Add to list and select it
            item = QListWidgetItem("Generic: New Provider")
            item.setData(Qt.ItemDataRole.UserRole, "New Provider")
            self.provider_list.addItem(item)
            self.provider_list.setCurrentItem(item)

            # Focus on the name field for quick editing
            self.name_input.setFocus()
            self.name_input.selectAll()

        def edit_selected(self):
            """Edit the currently selected provider."""
            items = self.provider_list.selectedItems()
            if items:
                # Already handled by selection change, but could add edit-specific logic
                pass

        def delete_selected(self):
            """Delete the currently selected provider."""
            items = self.provider_list.selectedItems()
            if items:
                provider_name = items[0].data(Qt.ItemDataRole.UserRole)

                reply = QMessageBox.question(
                    self,
                    "Confirm Delete",
                    f"Are you sure you want to delete provider '{provider_name}'?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )

                if reply == QMessageBox.StandardButton.Yes:
                    self.registry.remove_provider(provider_name)
                    self.provider_list.takeItem(self.provider_list.row(items[0]))
                    self.clear_form()

        def add_from_template(self):
            """Add a provider based on a predefined template."""
            category = self.quick_add_combo.currentText()
            if category == "Select database type..." or not category:
                QMessageBox.information(self, "Info", "Please select a database type")
                return

            # Get a suggested name based on template
            templates = PredefinedProviderTemplates()
            template = templates.get_template(category)
            if not template:
                QMessageBox.warning(self, "Error", f"No template found for {category}")
                return

            # Create the provider with default name based on template
            default_name = f"My {category} Connection"
            provider = templates.create_provider_from_template(
                category=category, name=default_name, host="localhost", database=""
            )

            # Add to registry and UI
            self.registry.add_provider(provider)

            item = QListWidgetItem(f"{category}: {default_name}")
            item.setData(Qt.ItemDataRole.UserRole, default_name)
            self.provider_list.addItem(item)
            self.provider_list.setCurrentItem(item)

            QMessageBox.information(
                self, "Template Added", f"Added {category} provider template. Fill in the connection details."
            )

        def add_custom_provider(self):
            """Add a custom JDBC provider with blank template."""
            # Create a custom provider with empty/blank values
            custom_provider = JDBCProvider(
                name="Custom JDBC Provider",
                category="Custom",
                driver_class="",
                jar_path="",
                url_template="jdbc:{custom}://{host}:{port}/{database}",
                default_host="localhost",
                default_port=0,
                default_database="",
                default_user=None,
                default_password=None,
                extra_properties={},
            )

            # Add to registry and UI
            self.registry.add_provider(custom_provider)

            item = QListWidgetItem("Custom: Custom JDBC Provider")
            item.setData(Qt.ItemDataRole.UserRole, "Custom JDBC Provider")
            self.provider_list.addItem(item)
            self.provider_list.setCurrentItem(item)

            QMessageBox.information(
                self,
                "Custom Provider Added",
                "Added custom JDBC provider. Configure all connection parameters manually.",
            )

        def browse_jar_file(self):
            """Browse for JAR file."""
            default_dir = os.path.expanduser("~/Downloads")
            if not os.path.isdir(default_dir):
                default_dir = os.path.expanduser("~")

            fname, _ = QFileDialog.getOpenFileName(
                self, "Select JDBC Driver JAR", default_dir, "JAR Files (*.jar);;All Files (*)"
            )

            if fname:
                self.jar_path_input.setText(fname)

        def add_property_row(self):
            """Add a new blank property row."""
            row = self.properties_table.rowCount()
            self.properties_table.insertRow(row)
            self.properties_table.setItem(row, 0, QTableWidgetItem(""))
            self.properties_table.setItem(row, 1, QTableWidgetItem(""))

        def remove_property_row(self):
            """Remove selected property rows."""
            selected_rows = {item.row() for item in self.properties_table.selectedItems()}
            # Remove in reverse order to maintain row indices
            for row in sorted(selected_rows, reverse=True):
                self.properties_table.removeRow(row)

        def accept(self):
            """Handle OK button click - save changes."""
            if self.current_provider:
                # Validate required fields
                if not self.name_input.text().strip():
                    QMessageBox.warning(self, "Validation Error", "Provider name is required")
                    return

                # Update provider from form
                self.current_provider.name = self.name_input.text().strip()
                self.current_provider.category = self.category_input.currentText()

                # Basic connection settings
                self.current_provider.default_host = self.host_input.text().strip()
                self.current_provider.default_port = self.port_input.value()
                self.current_provider.default_database = self.database_input.text().strip()

                # Driver settings
                self.current_provider.driver_class = self.driver_class_input.text().strip()
                self.current_provider.jar_path = self.jar_path_input.text().strip()

                # Connection details
                self.current_provider.default_user = self.username_input.text().strip() or None
                self.current_provider.default_password = self.password_input.text().strip() or None
                self.current_provider.url_template = self.url_template_input.toPlainText()

                # Advanced properties
                props = {}
                for row in range(self.properties_table.rowCount()):
                    key_item = self.properties_table.item(row, 0)
                    value_item = self.properties_table.item(row, 1)
                    if key_item and value_item:
                        key = key_item.text().strip()
                        value = value_item.text().strip()
                        if key:
                            props[key] = value
                self.current_provider.extra_properties = props

                # Save to registry
                existing_provider = self.registry.get_provider(self.current_provider.name)
                if existing_provider:
                    self.registry.update_provider(self.current_provider)
                else:
                    self.registry.add_provider(self.current_provider)

            else:
                # No provider selected - treat as creating a new provider
                if not self.name_input.text().strip():
                    QMessageBox.warning(self, "Validation Error", "Provider name is required")
                    return

                # Collect advanced properties from table
                props = {}
                for row in range(self.properties_table.rowCount()):
                    key_item = self.properties_table.item(row, 0)
                    value_item = self.properties_table.item(row, 1)
                    if key_item and value_item:
                        key = key_item.text().strip()
                        value = value_item.text().strip()
                        if key:
                            props[key] = value

                new_provider = JDBCProvider(
                    name=self.name_input.text().strip(),
                    category=self.category_input.currentText(),
                    driver_class=self.driver_class_input.text().strip(),
                    jar_path=self.jar_path_input.text().strip(),
                    url_template=self.url_template_input.toPlainText(),
                    default_host=self.host_input.text().strip() or "localhost",
                    default_port=self.port_input.value() or 0,
                    default_database=self.database_input.text().strip() or "",
                    default_user=self.username_input.text().strip() or None,
                    default_password=self.password_input.text().strip() or None,
                    extra_properties=props,
                )
                self.registry.add_provider(new_provider)

            super().accept()

        def reset_defaults(self):
            """Reset to default providers."""
            reply = QMessageBox.question(
                self,
                "Confirm Reset",
                "This will reset all providers to default values and lose any custom providers. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.Yes:
                # Clear all providers and re-initialize with defaults
                self.registry.providers.clear()
                self.registry._initialize_default_providers()
                # Ensure changes are saved and other registry instances reload
                self.registry.save_providers()
                self.refresh_provider_list()
                self.clear_form()
                QMessageBox.information(self, "Reset Complete", "Providers have been reset to defaults.")

        def download_jdbc_driver_gui(self):
            """Download JDBC driver for the selected category with enhanced UI feedback."""
            from .jdbc_auto_downloader import find_existing_drivers

            category = self.category_input.currentText()
            if not category or category == "Generic":
                # Try to guess from driver class field if category is generic
                driver_class = self.driver_class_input.text().strip().lower()

                # Enhanced automatic driver detection
                detected_category = None
                detection_confidence = 0

                # Check for common driver class patterns
                driver_patterns = {
                    "postgresql": ["postgres", "pgjdbc"],
                    "mysql": ["mysql", "mariadb", "cj.jdbc"],
                    "oracle": ["oracle", "ojdbc"],
                    "sqlserver": ["sqlserver", "microsoft", "mssql"],
                    "db2": ["db2", "ibm"],
                    "sqlite": ["sqlite", "xerial"],
                    "h2": ["h2"],
                    "jt400": ["jt400", "as400", "ibm.i"],
                }

                for db_type, patterns in driver_patterns.items():
                    for pattern in patterns:
                        if pattern in driver_class:
                            detected_category = db_type
                            detection_confidence += 1
                            break

                if detected_category:
                    category = detected_category
                    QMessageBox.information(
                        self, "Driver Detected", f"Automatically detected {category} driver based on driver class."
                    )
                else:
                    # If no automatic detection, suggest common drivers
                    suggestion_msg = "Could not automatically detect driver type. Common options:\n\n"
                    suggestion_msg += "- PostgreSQL: org.postgresql.Driver\n"
                    suggestion_msg += "- MySQL: com.mysql.cj.jdbc.Driver\n"
                    suggestion_msg += "- Oracle: oracle.jdbc.OracleDriver\n"
                    suggestion_msg += "- SQL Server: com.microsoft.sqlserver.jdbc.SQLServerDriver\n"
                    suggestion_msg += "- SQLite: org.sqlite.JDBC\n"

                    QMessageBox.information(
                        self,
                        "Select Category",
                        suggestion_msg + "\nPlease select a database category or update the driver class field.",
                    )
                    return

            # Check if driver already exists
            existing_drivers = find_existing_drivers(category)
            if existing_drivers:
                reply = QMessageBox.question(
                    self,
                    "Driver Exists",
                    f"Found existing {category} drivers:\n"
                    + "\n".join([os.path.basename(path) for path in existing_drivers])
                    + "\n\nDo you want to download anyway?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if reply == QMessageBox.StandardButton.No:
                    # Use existing driver
                    selected_driver, ok = QInputDialog.getItem(
                        self,
                        "Select Driver",
                        "Choose an existing driver:",
                        [os.path.basename(path) for path in existing_drivers],
                        0,
                        False,
                    )
                    if ok and selected_driver:
                        for full_path in existing_drivers:
                            if selected_driver == os.path.basename(full_path):
                                self.jar_path_input.setText(full_path)
                                break
                    return

            # Build dialog (use helper so tests can inspect controls)
            dialog, download_btn, manual_btn, license_checkbox, _, _, _, _ = self.create_download_dialog(category)

            # If running under test mode, avoid blocking GUI; return the dialog and controls so tests
            # can interact with the returned widgets directly without opening a native modal dialog.
            if os.environ.get("DBUTILS_TEST_MODE"):
                # Return controls for inspection by tests
                return dialog, download_btn, manual_btn, license_checkbox

            # Show modal dialog otherwise with proper error handling
            try:
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    # User chose to download automatically
                    # Read any pending options captured when Download/Manual was clicked
                    version = None
                    if hasattr(self, "_pending_download_options"):
                        version = self._pending_download_options.get("version")
                    self.perform_jdbc_download(category, version=version)
            except Exception as e:
                QMessageBox.critical(self, "Download Dialog Error", f"Failed to open download dialog: {e}")
            finally:
                # Clean up dialog resources
                dialog.deleteLater()

        def create_download_dialog(self, category: str):
            """Create and return a download dialog and the main widgets for inspection/testing.

            Returns a tuple: (dialog, download_button, manual_button, license_checkbox_or_None)
            """
            from .jdbc_driver_downloader import JDBCDriverRegistry

            dialog = QDialog(self)
            # Set as modal dialog with proper parent window for Qt lifecycle management
            dialog.setModal(True)
            dialog.setWindowTitle(f"Download {category} JDBC Driver")
            dialog.resize(500, 400)

            layout = QVBoxLayout(dialog)

            # Show download information
            from .jdbc_auto_downloader import get_jdbc_driver_download_info as get_download_info

            info_text = get_download_info(category)
            if info_text:
                info_label = QLabel(info_text)
                info_label.setWordWrap(True)
                info_label.setAlignment(Qt.AlignmentFlag.AlignTop)
                info_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                layout.addWidget(info_label)
            else:
                layout.addWidget(QLabel(f"No specific download information available for {category}."))

            # Progress bar
            self.download_progress = QProgressBar()
            self.download_progress.setVisible(False)
            layout.addWidget(self.download_progress)

            # License acceptance (if required)
            license_checkbox = None
            driver_info = JDBCDriverRegistry.get_driver_info(category)
            if driver_info and getattr(driver_info, "requires_license", False):
                # Show license wording
                license_label_text = (
                    driver_info.license_text
                    or f"This driver requires acceptance of the vendor license: {driver_info.license_url}"
                )
                license_label = QLabel(license_label_text)
                license_label.setWordWrap(True)
                layout.addWidget(license_label)

                license_checkbox = QCheckBox("I have read and accept the driver license terms")
                license_checkbox.setChecked(False)
                layout.addWidget(license_checkbox)

            # Buttons
            button_layout = QHBoxLayout()

            download_btn = QPushButton("Download Automatically")

            # When clicked, accept the dialog and persist any license acceptance
            def on_download_clicked():
                # If license checkbox present and checked, persist acceptance
                try:
                    from .license_store import accept_license

                    if license_checkbox is not None and license_checkbox.isChecked():
                        accept_license(category.lower())
                except Exception:
                    pass

                # capture selected version
                sel_version = None
                if version_choice is not None:
                    sel = version_choice.currentText()
                    if sel == "specific" and specific_version_input is not None:
                        sel_version = specific_version_input.text().strip() or None
                    else:
                        sel_version = sel

                self._pending_download_options = {"version": sel_version}

                dialog.accept()

            download_btn.clicked.connect(on_download_clicked)

            manual_btn = QPushButton("Open Download Page")

            # Handle manual button so we can persist license acceptance too
            def on_manual_clicked():
                try:
                    from .license_store import accept_license

                    if license_checkbox is not None and license_checkbox.isChecked():
                        accept_license(category.lower())
                except Exception:
                    pass

                # record pending options when user opens manual page
                sel_version = None
                if version_choice is not None:
                    sel = version_choice.currentText()
                    if sel == "specific" and specific_version_input is not None:
                        sel_version = specific_version_input.text().strip() or None
                    else:
                        sel_version = sel

                self._pending_download_options = {"version": sel_version}

                # open download page but keep dialog open
                self.open_download_page(category)

            manual_btn.clicked.connect(on_manual_clicked)

            cancel_btn = QPushButton("Cancel")
            cancel_btn.clicked.connect(dialog.reject)

            button_layout.addWidget(download_btn)
            button_layout.addWidget(manual_btn)
            button_layout.addStretch()
            button_layout.addWidget(cancel_btn)

            layout.addLayout(button_layout)

            # If driver has maven artifacts, show version selection and repo config
            version_choice = None
            specific_version_input = None
            repo_list_label = None
            repo_edit_btn = None

            if driver_info and getattr(driver_info, "maven_artifacts", None):
                artifact_group = QGroupBox("Artifact Options")
                artifact_layout = QFormLayout(artifact_group)

                # Version selection: recommended / latest / specific
                version_choice = QComboBox()
                version_choices = ["recommended", "latest", "specific"]
                version_choice.addItems(version_choices)
                specific_version_input = QLineEdit()
                specific_version_input.setPlaceholderText("Enter specific version (e.g. 42.6.0)")
                specific_version_input.setEnabled(False)

                def on_version_changed(idx):
                    specific_version_input.setEnabled(version_choice.currentText() == "specific")

                version_choice.currentIndexChanged.connect(on_version_changed)

                artifact_layout.addRow("Version:", version_choice)
                artifact_layout.addRow("Specific Version:", specific_version_input)

                # Repo list display + edit button
                from .downloader_prefs import get_maven_repos, set_maven_repos, validate_repositories

                repos = get_maven_repos()
                repo_status = validate_repositories(repos)

                # Create a more informative repo status display
                repo_status_text = []
                for repo, valid, message in repo_status:
                    status_icon = "✓" if valid else "✗"
                    repo_status_text.append(f"{status_icon} {repo} - {message}")

                repo_list_label = QLabel("\n".join(repo_status_text))
                repo_list_label.setWordWrap(True)
                repo_edit_btn = QPushButton("Edit Repositories…")

                def open_edit_repos():
                    edit_dialog = QDialog(self)
                    edit_dialog.setWindowTitle("Edit Maven Repositories")
                    edit_layout = QVBoxLayout(edit_dialog)
                    repos_edit = QTextEdit("\n".join(repos))
                    edit_layout.addWidget(repos_edit)

                    btn_layout = QHBoxLayout()
                    save_btn = QPushButton("Save")
                    cancel_btn2 = QPushButton("Cancel")
                    btn_layout.addWidget(save_btn)
                    btn_layout.addWidget(cancel_btn2)
                    edit_layout.addLayout(btn_layout)

                    def save_and_close():
                        new_repos = [r.strip() for r in repos_edit.toPlainText().splitlines() if r.strip()]
                        set_maven_repos(new_repos)
                        repo_list_label.setText("\n".join(new_repos))
                        edit_dialog.accept()

                    save_btn.clicked.connect(save_and_close)
                    cancel_btn2.clicked.connect(edit_dialog.reject)

                    edit_dialog.exec()

                repo_edit_btn.clicked.connect(open_edit_repos)

                # Add to layout
                artifact_layout.addRow("Repositories:", repo_list_label)
                artifact_layout.addRow("", repo_edit_btn)

                layout.addWidget(artifact_group)

            # If license is required, disable action buttons until accepted
            if license_checkbox is not None:
                download_btn.setEnabled(False)
                manual_btn.setEnabled(False)

                def on_license_toggled(checked: bool):
                    """Enable/disable action buttons based on checkbox toggle."""
                    download_btn.setEnabled(bool(checked))
                    manual_btn.setEnabled(bool(checked))

                # Use the toggled(boolean) signal to ensure we get a boolean value
                # This avoids mismatches between Qt.CheckState enum values and plain ints
                license_checkbox.toggled.connect(on_license_toggled)

                # Check if license was previously accepted
                from .license_store import is_license_accepted

                if is_license_accepted(category.lower()):
                    license_checkbox.setChecked(True)
                    download_btn.setEnabled(True)
                    manual_btn.setEnabled(True)

            # Return controls so tests can interact and calling code can read selection
            return (
                dialog,
                download_btn,
                manual_btn,
                license_checkbox,
                version_choice,
                specific_version_input,
                repo_list_label,
                repo_edit_btn,
            )

        def open_download_page(self, category):
            """Open the download page for the specified category."""
            from .jdbc_driver_downloader import JDBCDriverRegistry

            driver_info = JDBCDriverRegistry.get_driver_info(category)
            if driver_info:
                # Avoid launching a real browser when running tests
                if os.environ.get("DBUTILS_TEST_MODE"):
                    # In test mode, return the URL for assertions instead of opening a browser
                    return driver_info.download_url
                import webbrowser

                webbrowser.open(driver_info.download_url)
            else:
                QMessageBox.information(self, "No Download Page", f"No specific download page available for {category}")

        def perform_jdbc_download(self, category, version: str | None = None):
            """Actually perform the JDBC driver download with enhanced feedback."""
            import os

            # Prefer richer manager which supports maven artifacts and multi-jar downloads
            from .jdbc_driver_manager import download_jdbc_driver as download_auto

            # Ensure there is a progress widget available
            if not hasattr(self, "download_progress") or self.download_progress is None:
                # Create a lightweight progress bar if it doesn't exist (tests may call this directly)
                self.download_progress = QProgressBar(self)
                self.download_progress.setVisible(False)

            # Create a status label for detailed feedback
            if not hasattr(self, "download_status_label") or self.download_status_label is None:
                self.download_status_label = QLabel()
                self.download_status_label.setWordWrap(True)

            # Show progress
            self.download_progress.setVisible(True)
            self.download_progress.setRange(0, 0)  # Indeterminate progress
            QApplication.processEvents()  # Update UI

            def progress_callback(downloaded, total):
                if total > 0:
                    self.download_progress.setRange(0, total)
                    self.download_progress.setValue(downloaded)
                QApplication.processEvents()

            def status_callback(message):
                self.download_status_label.setText(message)
                QApplication.processEvents()

            try:
                # Use requested version if provided, otherwise default to 'latest'
                requested = version or "latest"
                result = download_auto(
                    category, on_progress=progress_callback, on_status=status_callback, version=requested
                )
                if result:
                    # Support single-path or list-of-paths
                    if isinstance(result, list):
                        # Set first jar path into the input so the provider can use it
                        first = result[0] if result else ""
                        self.jar_path_input.setText(first)
                        names = ", ".join([os.path.basename(r) for r in result if r])
                        QMessageBox.information(
                            self, "Download Complete", f"Successfully downloaded JDBC driver(s):\n{names}"
                        )
                    else:
                        self.jar_path_input.setText(result)
                        QMessageBox.information(
                            self,
                            "Download Complete",
                            f"Successfully downloaded JDBC driver to:\n{os.path.basename(result)}",
                        )
                else:
                    QMessageBox.warning(
                        self,
                        "Download Failed",
                        f"Could not automatically download JDBC driver for {category}.\n"
                        f"Please download it manually from the official source.",
                    )
            except Exception as e:
                QMessageBox.critical(self, "Download Error", f"Error downloading JDBC driver: {e}")
            finally:
                self.download_progress.setVisible(False)
