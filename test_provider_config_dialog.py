#!/usr/bin/env python3
"""
Pytest-Qt tests for ProviderConfigDialog functionality
"""
import pytest
import sys
import os
from pathlib import Path

# Add the src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from PySide6.QtWidgets import QApplication
from dbutils.gui.provider_config_dialog import ProviderConfigDialog


@pytest.fixture
def app(qapp):
    """Provide the QApplication instance."""
    return qapp


@pytest.fixture
def dialog(app):
    """Create a ProviderConfigDialog instance for testing."""
    dialog = ProviderConfigDialog(None)

    # Ensure providers are present for tests — initialize defaults when empty
    if dialog.provider_list.count() == 0:
        dialog.registry._initialize_default_providers()
        dialog.refresh_provider_list()

    # Ensure there is a selected provider
    if dialog.provider_list.count() > 0 and not dialog.provider_list.selectedItems():
        dialog.provider_list.setCurrentRow(0)
        dialog.provider_selected()

    return dialog


class TestProviderConfigDialog:
    """Test suite for ProviderConfigDialog."""

    def test_dialog_initialization(self, dialog):
        """Test that the dialog initializes properly."""
        assert dialog is not None
        assert dialog.windowTitle() == "JDBC Provider Configuration"
        # After our fix, first provider is auto-selected and loaded immediately
        assert dialog.current_provider is not None  # First provider is auto-selected
        assert dialog.current_provider.name != ""  # Provider has data loaded

    def test_provider_list_auto_selection(self, dialog):
        """Test that providers are loaded and first one is auto-selected."""
        # There should be default providers loaded
        assert dialog.provider_list.count() > 0
        
        # The first provider should be selected automatically
        selected_items = dialog.provider_list.selectedItems()
        assert len(selected_items) == 1
        
        # A current provider should be loaded
        assert dialog.current_provider is not None
        assert dialog.current_provider.name != ""

    def test_right_pane_populated(self, dialog):
        """Test that right pane is populated when provider is selected."""
        # After initialization, there should be a current provider
        assert dialog.current_provider is not None
        
        # Form fields should be populated with provider data
        assert dialog.name_input.text() != ""
        assert dialog.driver_class_input.text() != ""
        assert dialog.url_template_input.toPlainText() != ""
        
        # Connection details should be populated
        # (These might be empty strings for template providers, but fields exist)
        assert hasattr(dialog, 'username_input')
        assert hasattr(dialog, 'password_input')
        assert hasattr(dialog, 'url_template_input')

    def test_connection_group_expanded_by_default(self, dialog):
        """Test that connection settings group is expanded by default."""
        # The connection group should be checked (expanded) by default
        assert dialog.connection_group.isChecked() is True

    def test_driver_group_collapsed_by_default(self, dialog):
        """Test that driver settings group is collapsed by default."""
        # The driver group should be unchecked (collapsed) by default
        assert dialog.driver_group.isChecked() is False

    def test_basic_group_not_collapsible(self, dialog):
        """Test that basic group is always expanded."""
        # Basic group should not be checkable/collapsible
        assert dialog.basic_group.isCheckable() is False

    def test_form_fields_enabled(self, dialog):
        """Test that form fields are enabled for editing."""
        assert dialog.name_input.isEnabled() is True
        assert dialog.username_input.isEnabled() is True
        assert dialog.password_input.isEnabled() is True
        assert dialog.url_template_input.isEnabled() is True

    def test_connection_field_editing(self, dialog):
        """Test that connection fields can be edited."""
        original_username = dialog.username_input.text()
        original_url = dialog.url_template_input.toPlainText()
        
        # Test username field editing
        dialog.username_input.setText("test_username")
        assert dialog.username_input.text() == "test_username"
        
        # Test URL template field editing
        dialog.url_template_input.setPlainText("jdbc:test://newhost:5432/testdb")
        assert dialog.url_template_input.toPlainText() == "jdbc:test://newhost:5432/testdb"
        
        # Restore original values
        dialog.username_input.setText(original_username)
        dialog.url_template_input.setPlainText(original_url)

    def test_provider_selection_updates_form(self, dialog):
        """Test that selecting different providers updates the form."""
        original_name = dialog.name_input.text()
        
        # Select a different provider if available
        if dialog.provider_list.count() > 1:
            dialog.provider_list.setCurrentRow(1)
            dialog.provider_selected()
            
            # Form should be updated with new provider's data
            new_name = dialog.name_input.text()
            assert new_name != original_name
            assert new_name != ""

    def test_add_new_provider(self, dialog):
        """Test adding a new provider works correctly."""
        initial_count = dialog.provider_list.count()
        original_provider_name = dialog.current_provider.name if dialog.current_provider else None

        # Add a new provider
        dialog.add_provider()

        # The list should have one more item
        assert dialog.provider_list.count() == initial_count + 1

        # A new provider entry should be in the list
        selected_items = dialog.provider_list.selectedItems()
        assert len(selected_items) == 1
        assert selected_items[0].text().endswith(": New Provider")

        # Note: After calling add_provider, the selection mechanism may set current_provider to None
        # if the new provider is not yet in the registry. This is current behavior, though possibly
        # not ideal. The main functionality we need to ensure is that the UI elements are properly set up.
        # The provider will be added to the registry when the user saves (accepts) the dialog.

    def test_connection_group_expansion_toggle(self, dialog):
        """Test that the connection group can be expanded/collapsed."""
        original_state = dialog.connection_group.isChecked()
        new_state = not original_state
        
        # Toggle the connection group
        dialog.connection_group.setChecked(new_state)
        
        # Verify it toggled
        assert dialog.connection_group.isChecked() == new_state
        
        # Toggle back to original state
        dialog.connection_group.setChecked(original_state)
        assert dialog.connection_group.isChecked() == original_state

    def test_driver_class_field_accessibility(self, dialog):
        """Test that driver class field is accessible even if initially disabled."""
        # Initially, the field is loaded with provider data
        original_driver = dialog.driver_class_input.text()
        assert original_driver != ""
        
        # Test that we can manually enable and modify it
        dialog.driver_class_input.setEnabled(True)
        dialog.driver_class_input.setText("test.driver.class")
        assert dialog.driver_class_input.text() == "test.driver.class"
        
        # Restore original
        dialog.driver_class_input.setText(original_driver)

    def test_license_prompt_for_manual_drivers(self, dialog):
        """Ensure drivers that require licenses show a checkbox and block actions until accepted."""
        # We expect 'oracle' to be configured as requires_license
        d, download_btn, manual_btn, checkbox, _, _, _, _ = dialog.create_download_dialog('oracle')
        assert checkbox is not None
        assert download_btn.isEnabled() is False
        assert manual_btn.isEnabled() is False

        # Accept the license - UI should enable action buttons
        checkbox.setChecked(True)
        assert download_btn.isEnabled() is True
        assert manual_btn.isEnabled() is True

    def test_no_license_for_maven_drivers(self, dialog):
        """Drivers available via Maven should not require a license checkbox by default."""
        d, download_btn, manual_btn, checkbox, version_choice, specific_input, repo_label, repo_btn = dialog.create_download_dialog('sqlite')
        # sqlite should not require license acceptance
        assert checkbox is None
        assert download_btn.isEnabled() is True
        assert manual_btn.isEnabled() is True

    def test_persistent_license_acceptance_saved(self, temp_config_dir, qapp):
        """Test that accepting a license is persisted to disk under config dir."""
        # Create a fresh dialog within the patched config dir environment
        dlg = ProviderConfigDialog(None)
        d, download_btn, manual_btn, checkbox, _, _, _, _ = dlg.create_download_dialog('oracle')
        assert checkbox is not None

        # Ensure not accepted initially
        from dbutils.gui import license_store
        assert not license_store.is_license_accepted('oracle')

        # Accept and click download
        checkbox.setChecked(True)
        download_btn.click()

        # Now it should be persisted
        assert license_store.is_license_accepted('oracle')

    def test_persistent_license_acceptance_manual(self, temp_config_dir, qapp):
        """License acceptance should also be saved when user opens download page manually."""
        dlg = ProviderConfigDialog(None)
        d, download_btn, manual_btn, checkbox, _, _, _, _ = dlg.create_download_dialog('oracle')

    def test_version_selection_for_maven_drivers(self, dialog):
        # SQLite is maven-backed and should have version controls and repo info
        d, download_btn, manual_btn, checkbox, version_choice, specific_input, repo_label, repo_btn = dialog.create_download_dialog('sqlite')
        assert version_choice is not None
        assert specific_input is not None
        # default should disable specific input
        assert specific_input.isEnabled() is False

        # switching to specific enables input
        version_choice.setCurrentText('specific')
        assert specific_input.isEnabled() is True

    def test_repo_config_persistence(self, temp_config_dir, dialog):
        from dbutils.gui.downloader_prefs import set_maven_repos, get_maven_repos

        set_maven_repos(['https://custom.repo/npm/','https://mirror.example/maven/'])

        d, download_btn, manual_btn, checkbox, version_choice, specific_input, repo_label, repo_btn = dialog.create_download_dialog('sqlite')
        assert 'https://custom.repo/npm/' in repo_label.text()

    def test_perform_download_passes_version(self, temp_config_dir, monkeypatch):
        # Ensure perform_jdbc_download passes requested version to manager
        from dbutils.gui import provider_config_dialog as pcd

        dlg = ProviderConfigDialog(None)

        called = {}

        def fake_download(database_type, on_progress=None, version=None):
            called['database_type'] = database_type
            called['version'] = version
            # create a fake downloaded file
            tmp_driver = os.path.join(os.environ.get('DBUTILS_DRIVER_DIR', '/tmp'), 'sqlite-jdbc-TEST.jar')
            # ensure dir exists
            os.makedirs(os.path.dirname(tmp_driver), exist_ok=True)
            with open(tmp_driver, 'wb') as fh:
                fh.write(b'test')
            return tmp_driver

        monkeypatch.setenv('DBUTILS_DRIVER_DIR', str(temp_config_dir / 'drivers'))
        monkeypatch.setattr('dbutils.gui.jdbc_driver_manager.download_jdbc_driver', fake_download)

        dlg.perform_jdbc_download('sqlite', version='3.42.0.0')

        assert called.get('database_type') == 'sqlite'
        assert called.get('version') == '3.42.0.0'
        assert checkbox is not None

        from dbutils.gui import license_store
        license_store.revoke_license('oracle')
        assert not license_store.is_license_accepted('oracle')

        checkbox.setChecked(True)
        manual_btn.click()

        assert license_store.is_license_accepted('oracle')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])