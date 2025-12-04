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
            self.quick_add_combo.addItems(["Select database type..."] +
                                        PredefinedProviderTemplates.get_categories())
            self.quick_add_btn = QPushButton("Add from Template")
            self.quick_add_btn.clicked.connect(self.add_from_template)
            quick_add_layout.addWidget(self.quick_add_combo)
            quick_add_layout.addWidget(self.quick_add_btn)
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
            self.config_layout = QFormLayout(self.config_widget)

            # Basic settings (always visible)
            self.basic_group = QGroupBox("Basic Settings")
            self.basic_group.setCheckable(False)  # Always expanded
            self.basic_layout = QFormLayout(self.basic_group)

            self.name_input = QLineEdit()
            self.category_input = QComboBox()
            self.category_input.addItems(PredefinedProviderTemplates.get_categories())
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

            # Add all groups to main config layout using QVBoxLayout wrapper
            config_vbox = QVBoxLayout(self.config_widget)
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
                    p for p in providers
                    if filter_lower in p.name.lower() or filter_lower in p.category.lower()
                ]

            for provider in sorted(providers, key=lambda p: (p.category, p.name)):
                item = QListWidgetItem(f"{provider.category}: {provider.name}")
                item.setData(Qt.ItemDataRole.UserRole, provider.name)
                self.provider_list.addItem(item)

            # Auto-select the first provider to populate the right pane
            if self.provider_list.count() > 0 and not self.provider_list.selectedItems():
                self.provider_list.setCurrentRow(0)
                self.provider_selected()

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
                extra_properties={}
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
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
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
            template = PredefinedProviderTemplates.get_template(category)
            if not template:
                QMessageBox.warning(self, "Error", f"No template found for {category}")
                return

            # Create the provider with default name based on template
            default_name = f"My {category} Connection"
            provider = PredefinedProviderTemplates.create_provider_from_template(
                category=category,
                name=default_name,
                host="localhost",
                database=""
            )

            # Add to registry and UI
            self.registry.add_provider(provider)

            item = QListWidgetItem(f"{category}: {default_name}")
            item.setData(Qt.ItemDataRole.UserRole, default_name)
            self.provider_list.addItem(item)
            self.provider_list.setCurrentItem(item)

            QMessageBox.information(
                self,
                "Template Added",
                f"Added {category} provider template. Fill in the connection details."
            )

        def browse_jar_file(self):
            """Browse for JAR file."""
            default_dir = os.path.expanduser("~/Downloads")
            if not os.path.isdir(default_dir):
                default_dir = os.path.expanduser("~")

            fname, _ = QFileDialog.getOpenFileName(
                self,
                "Select JDBC Driver JAR",
                default_dir,
                "JAR Files (*.jar);;All Files (*)"
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

            super().accept()

        def reset_defaults(self):
            """Reset to default providers."""
            reply = QMessageBox.question(
                self,
                "Confirm Reset",
                "This will reset all providers to default values and lose any custom providers. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                # Clear all providers and re-initialize with defaults
                self.registry.providers.clear()
                self.registry._initialize_default_providers()
                self.refresh_provider_list()
                self.clear_form()
                QMessageBox.information(
                    self,
                    "Reset Complete",
                    "Providers have been reset to defaults."
                )

    def download_jdbc_driver_gui(self):
        """Download JDBC driver for the selected category."""
        from .jdbc_auto_downloader import find_existing_drivers
        from .jdbc_auto_downloader import get_jdbc_driver_download_info as get_download_info

        category = self.category_input.currentText()
        if not category or category == "Generic":
            # Try to guess from driver class field if category is generic
            driver_class = self.driver_class_input.text().strip().lower()
            if "postgres" in driver_class:
                category = "postgresql"
            elif "mysql" in driver_class:
                category = "mysql"
            elif "mariadb" in driver_class:
                category = "mariadb"
            elif "oracle" in driver_class:
                category = "oracle"
            elif "sqlserver" in driver_class or "microsoft" in driver_class:
                category = "sqlserver"
            elif "db2" in driver_class:
                category = "db2"
            elif "sqlite" in driver_class:
                category = "sqlite"
            elif "h2" in driver_class:
                category = "h2"
            else:
                QMessageBox.information(
                    self,
                    "Select Category",
                    "Please select a database category first or fill in the driver class field to help identify the database type."
                )
                return

        # Check if driver already exists
        existing_drivers = find_existing_drivers(category)
        if existing_drivers:
            reply = QMessageBox.question(
                self,
                "Driver Exists",
                f"Found existing {category} drivers:\n" + "\n".join([os.path.basename(d) for d in existing_drivers]) +
                "\n\nDo you want to download anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                # Use existing driver
                selected_driver, ok = QInputDialog.getItem(
                    self,
                    "Select Driver",
                    "Choose an existing driver:",
                    [os.path.basename(d) for d in existing_drivers],
                    0,
                    False
                )
                if ok and selected_driver:
                    # Find the full path for the selected driver
                    for driver_path in existing_drivers:
                        if selected_driver == os.path.basename(driver_path):
                            self.jar_path_input.setText(driver_path)
                            break
                return

        # Show download dialog
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Download {category} JDBC Driver")
        dialog.resize(500, 400)

        layout = QVBoxLayout(dialog)

        # Show download information
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

        # Buttons
        button_layout = QHBoxLayout()

        download_btn = QPushButton("Download Automatically")
        download_btn.clicked.connect(dialog.accept)

        manual_btn = QPushButton("Open Download Page")
        manual_btn.clicked.connect(lambda: self.open_download_page(category))

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)

        button_layout.addWidget(download_btn)
        button_layout.addWidget(manual_btn)
        button_layout.addStretch()
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

        # Show modal dialog
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # User chose to download automatically
            self.perform_jdbc_download(category)

    def open_download_page(self, category):
        """Open the download page for the specified category."""
        from .jdbc_driver_downloader import JDBCDriverRegistry

        driver_info = JDBCDriverRegistry.get_driver_info(category)
        if driver_info:
            import webbrowser
            webbrowser.open(driver_info.download_url)
        else:
            QMessageBox.information(
                self,
                "No Download Page",
                f"No specific download page available for {category}"
            )

    def perform_jdbc_download(self, category):
        """Actually perform the JDBC driver download."""
        import os

        from .jdbc_auto_downloader import download_jdbc_driver as download_auto

        # Show progress
        self.download_progress.setVisible(True)
        self.download_progress.setRange(0, 0)  # Indeterminate progress
        QApplication.processEvents()  # Update UI

        def progress_callback(downloaded, total):
            if total > 0:
                self.download_progress.setRange(0, total)
                self.download_progress.setValue(downloaded)
            QApplication.processEvents()

        try:
            result = download_auto(category, "latest", on_progress=progress_callback)
            if result:
                self.jar_path_input.setText(result)
                QMessageBox.information(
                    self,
                    "Download Complete",
                    f"Successfully downloaded JDBC driver to:\n{os.path.basename(result)}"
                )
            else:
                QMessageBox.warning(
                    self,
                    "Download Failed",
                    f"Could not automatically download JDBC driver for {category}.\n"
                    f"Please download it manually from the official source."
                )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Download Error",
                f"Error downloading JDBC driver: {e}"
            )
        finally:
            self.download_progress.setVisible(False)


# The rest of the file should be properly closed here
