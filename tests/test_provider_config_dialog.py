import json
from pathlib import Path
from unittest.mock import patch

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox

from dbutils.enhanced_jdbc_provider import EnhancedProviderRegistry, JDBCProvider
from dbutils.gui.provider_config_dialog import ProviderConfigDialog

# Import test configuration

@pytest.fixture
def qapp():
    """Fixture to provide a QApplication instance for Qt tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app

@pytest.fixture
def setup_test_environment(tmp_path, monkeypatch):
    """Set up test environment with temporary config directory."""
    config_dir = tmp_path / '.config' / 'dbutils'
    monkeypatch.setenv('DBUTILS_CONFIG_DIR', str(config_dir))
    config_dir.mkdir(parents=True, exist_ok=True)

    # Set up a basic providers.json file
    providers_file = config_dir / 'providers.json'
    providers_file.write_text(json.dumps([]))

    return config_dir

def test_provider_config_dialog_initialization(qapp, setup_test_environment):
    """Test that the ProviderConfigDialog initializes correctly."""
    dialog = ProviderConfigDialog()
    assert dialog is not None
    assert dialog.windowTitle() == "JDBC Provider Configuration"
    assert dialog.registry is not None
    assert dialog.current_provider is None

def test_provider_config_dialog_add_provider(qapp, tmp_path, monkeypatch):
    """Test adding a new provider through the dialog."""
    # Set temporary config dir for providers
    monkeypatch.setenv('DBUTILS_CONFIG_DIR', str(tmp_path))
    config_dir = Path(tmp_path) / 'providers.json'
    config_dir.write_text(json.dumps([]))

    dialog = ProviderConfigDialog()

    # Set form fields for a new provider
    dialog.name_input.setText('TestProvider')
    dialog.category_input.setCurrentText('Generic')
    dialog.driver_class_input.setText('com.test.Driver')
    dialog.jar_path_input.setText('/tmp/test.jar')
    dialog.url_template_input.setPlainText('jdbc:test://{host}')

    # Simulate clicking the OK button
    dialog.accept()

    # Verify provider was added to registry
    registry = EnhancedProviderRegistry()
    assert 'TestProvider' in registry.list_names()
    provider = registry.get_provider('TestProvider')
    assert provider.driver_class == 'com.test.Driver'
    assert provider.jar_path == '/tmp/test.jar'

def test_provider_config_dialog_edit_provider(qapp, tmp_path, monkeypatch):
    """Test editing an existing provider."""
    # Set up initial provider
    monkeypatch.setenv('DBUTILS_CONFIG_DIR', str(tmp_path))
    config_dir = Path(tmp_path) / 'providers.json'

    # Create initial provider
    initial_provider = JDBCProvider(
        name="ExistingProvider",
        category="Generic",
        driver_class="com.initial.Driver",
        jar_path="/initial/path.jar",
        url_template="jdbc:initial://{host}",
        default_host="localhost",
        default_port=3306,
        default_database="testdb",
        default_user="testuser",
        default_password="testpass",
        extra_properties={}
    )

    # Save initial provider
    registry = EnhancedProviderRegistry()
    registry.add_provider(initial_provider)
    registry.save_providers()

    # Now test editing
    dialog = ProviderConfigDialog()

    # Select the provider in the list
    for i in range(dialog.provider_list.count()):
        item = dialog.provider_list.item(i)
        if item.data(Qt.ItemDataRole.UserRole) == "ExistingProvider":
            dialog.provider_list.setCurrentItem(item)
            break

    # Modify some fields
    dialog.driver_class_input.setText('com.updated.Driver')
    dialog.jar_path_input.setText('/updated/path.jar')

    # Accept the changes
    dialog.accept()

    # Verify changes were saved
    updated_provider = registry.get_provider('ExistingProvider')
    assert updated_provider.driver_class == 'com.updated.Driver'
    assert updated_provider.jar_path == '/updated/path.jar'

def test_provider_config_dialog_delete_provider(qapp, tmp_path, monkeypatch):
    """Test deleting a provider."""
    # Set up initial provider
    monkeypatch.setenv('DBUTILS_CONFIG_DIR', str(tmp_path))
    config_dir = Path(tmp_path) / 'providers.json'

    # Create initial provider
    provider = JDBCProvider(
        name="ProviderToDelete",
        category="Generic",
        driver_class="com.test.Driver",
        jar_path="/test/path.jar",
        url_template="jdbc:test://{host}",
        default_host="localhost",
        default_port=3306,
        default_database="testdb",
        default_user="testuser",
        default_password="testpass",
        extra_properties={}
    )

    # Save initial provider
    registry = EnhancedProviderRegistry()
    registry.add_provider(provider)
    registry.save_providers()

    # Create dialog and select provider
    dialog = ProviderConfigDialog()

    # Find and select the provider to delete
    for i in range(dialog.provider_list.count()):
        item = dialog.provider_list.item(i)
        if item.data(Qt.ItemDataRole.UserRole) == "ProviderToDelete":
            dialog.provider_list.setCurrentItem(item)
            break

    # Mock the QMessageBox to automatically confirm deletion
    with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Yes):
        dialog.delete_selected()

    # Verify provider was deleted
    assert "ProviderToDelete" not in registry.list_names()

def test_provider_config_dialog_validation(qapp, tmp_path, monkeypatch):
    """Test validation of required fields."""
    monkeypatch.setenv('DBUTILS_CONFIG_DIR', str(tmp_path))
    config_dir = Path(tmp_path) / 'providers.json'
    config_dir.write_text(json.dumps([]))

    dialog = ProviderConfigDialog()

    # Try to accept with empty name (should show validation error)
    dialog.name_input.clear()
    dialog.driver_class_input.setText('com.test.Driver')
    dialog.jar_path_input.setText('/test/path.jar')

    # Mock QMessageBox to capture the validation error
    with patch.object(QMessageBox, 'warning') as mock_warning:
        dialog.accept()
        mock_warning.assert_called_once()
        args, kwargs = mock_warning.call_args
        assert "Validation Error" in args[1]
        assert "Provider name is required" in args[2]

def test_provider_config_dialog_search_filter(qapp, tmp_path, monkeypatch):
    """Test the search/filter functionality."""
    monkeypatch.setenv('DBUTILS_CONFIG_DIR', str(tmp_path))
    config_dir = Path(tmp_path) / 'providers.json'

    # Create multiple providers
    providers = [
        JDBCProvider(
            name="PostgreSQL",
            category="PostgreSQL",
            driver_class="org.postgresql.Driver",
            jar_path="/postgres.jar",
            url_template="jdbc:postgresql://{host}",
            default_host="localhost",
            default_port=5432,
            default_database="postgres",
            default_user="postgres",
            default_password="postgres",
            extra_properties={}
        ),
        JDBCProvider(
            name="MySQL",
            category="MySQL",
            driver_class="com.mysql.cj.jdbc.Driver",
            jar_path="/mysql.jar",
            url_template="jdbc:mysql://{host}",
            default_host="localhost",
            default_port=3306,
            default_database="mysql",
            default_user="root",
            default_password="root",
            extra_properties={}
        )
    ]

    # Save providers
    registry = EnhancedProviderRegistry()
    for provider in providers:
        registry.add_provider(provider)
    registry.save_providers()

    # Create dialog
    dialog = ProviderConfigDialog()

    # Test filtering by name
    dialog.search_box.setText("PostgreSQL")
    dialog.filter_providers("PostgreSQL")

    # Verify only PostgreSQL provider is shown
    assert dialog.provider_list.count() == 1
    item = dialog.provider_list.item(0)
    assert "PostgreSQL" in item.text()

    # Test filtering by category
    dialog.search_box.setText("MySQL")
    dialog.filter_providers("MySQL")

    # Verify only MySQL provider is shown
    assert dialog.provider_list.count() == 1
    item = dialog.provider_list.item(0)
    assert "MySQL" in item.text()

def test_provider_config_dialog_add_from_template(qapp, tmp_path, monkeypatch):
    """Test adding a provider from a template."""
    monkeypatch.setenv('DBUTILS_CONFIG_DIR', str(tmp_path))
    config_dir = Path(tmp_path) / 'providers.json'
    config_dir.write_text(json.dumps([]))

    dialog = ProviderConfigDialog()

    # Select a template category
    dialog.quick_add_combo.setCurrentText("PostgreSQL")

    # Mock QMessageBox to capture template addition confirmation
    with patch.object(QMessageBox, 'information') as mock_info:
        dialog.add_from_template()

        # Verify template was added
        mock_info.assert_called()
        args, kwargs = mock_info.call_args
        assert "Template Added" in args[1]

        # Verify provider list was updated
        assert dialog.provider_list.count() > 0

def test_provider_config_dialog_reset_defaults(qapp, tmp_path, monkeypatch):
    """Test resetting to default providers."""
    monkeypatch.setenv('DBUTILS_CONFIG_DIR', str(tmp_path))
    config_dir = Path(tmp_path) / 'providers.json'

    # Create a custom provider first
    custom_provider = JDBCProvider(
        name="CustomProvider",
        category="Generic",
        driver_class="com.custom.Driver",
        jar_path="/custom/path.jar",
        url_template="jdbc:custom://{host}",
        default_host="localhost",
        default_port=3306,
        default_database="testdb",
        default_user="testuser",
        default_password="testpass",
        extra_properties={}
    )

    # Save custom provider
    registry = EnhancedProviderRegistry()
    registry.add_provider(custom_provider)
    registry.save_providers()

    # Create dialog
    dialog = ProviderConfigDialog()

    # Mock QMessageBox to confirm reset
    with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Yes):
        dialog.reset_defaults()

    # Verify custom provider was removed and defaults were restored
    assert "CustomProvider" not in registry.list_names()
    # Verify some default providers exist
    assert len(registry.list_names()) > 0

def test_provider_config_dialog_advanced_properties(qapp, tmp_path, monkeypatch):
    """Test adding and removing advanced properties."""
    monkeypatch.setenv('DBUTILS_CONFIG_DIR', str(tmp_path))
    config_dir = Path(tmp_path) / 'providers.json'
    config_dir.write_text(json.dumps([]))

    dialog = ProviderConfigDialog()

    # Add a new provider first
    dialog.name_input.setText('TestProvider')
    dialog.driver_class_input.setText('com.test.Driver')
    dialog.jar_path_input.setText('/test/path.jar')
    dialog.url_template_input.setPlainText('jdbc:test://{host}')

    # Add some properties
    dialog.add_property_row()
    dialog.add_property_row()

    # Set property values
    dialog.properties_table.setItem(0, 0, dialog.properties_table.item(0, 0).__class__("property1"))
    dialog.properties_table.setItem(0, 1, dialog.properties_table.item(0, 1).__class__("value1"))
    dialog.properties_table.setItem(1, 0, dialog.properties_table.item(1, 0).__class__("property2"))
    dialog.properties_table.setItem(1, 1, dialog.properties_table.item(1, 1).__class__("value2"))

    # Accept the dialog
    dialog.accept()

    # Verify properties were saved
    registry = EnhancedProviderRegistry()
    provider = registry.get_provider('TestProvider')
    assert provider is not None
    assert 'property1' in provider.extra_properties
    assert provider.extra_properties['property1'] == 'value1'
    assert 'property2' in provider.extra_properties
    assert provider.extra_properties['property2'] == 'value2'

def test_provider_config_dialog_error_handling(qapp, tmp_path, monkeypatch):
    """Test error handling in provider operations."""
    monkeypatch.setenv('DBUTILS_CONFIG_DIR', str(tmp_path))
    config_dir = Path(tmp_path) / 'providers.json'

    # Create a corrupted providers file
    config_dir.write_text('invalid json content')

    # Test that dialog handles corrupted config gracefully
    dialog = ProviderConfigDialog()

    # Should still be able to create dialog even with corrupted config
    assert dialog is not None
    assert dialog.windowTitle() == "JDBC Provider Configuration"

    # Test adding a provider should work even with corrupted initial config
    dialog.name_input.setText('RecoveryProvider')
    dialog.driver_class_input.setText('com.test.Driver')
    dialog.jar_path_input.setText('/test/path.jar')
    dialog.url_template_input.setPlainText('jdbc:test://{host}')

    dialog.accept()

    # Verify provider was saved correctly
    registry = EnhancedProviderRegistry()
    assert 'RecoveryProvider' in registry.list_names()
