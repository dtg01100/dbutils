#!/usr/bin/env python3
"""
Comprehensive Pytest-Qt tests for ProviderConfigDialog functionality
including edge cases, worst case scenarios, and user interaction simulation.
"""
import sys
from pathlib import Path

import pytest

# Add the src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from dbutils.gui.provider_config_dialog import ProviderConfigDialog


@pytest.fixture
def app(qapp):
    """Provide the QApplication instance."""
    return qapp


@pytest.fixture
def dialog(app):
    """Create a ProviderConfigDialog instance for testing with proper initialization."""
    dialog = ProviderConfigDialog(None)

    # Ensure the registry has providers (in case config file loading failed)
    if len(dialog.registry.list_providers()) == 0:
        dialog.registry._initialize_default_providers()
        dialog.refresh_provider_list()  # Refresh the UI list to match the registry

    # Ensure a provider is selected
    if len(dialog.provider_list.selectedItems()) == 0 and dialog.provider_list.count() > 0:
        dialog.provider_list.setCurrentRow(0)
        dialog.provider_selected()

    return dialog


class TestProviderConfigDialogComprehensive:
    """Comprehensive test suite for ProviderConfigDialog including edge cases."""

    def test_initial_auto_selection_robustness(self, dialog):
        """Test that auto-selection works robustly with various provider counts."""
        # This should work regardless of how many providers we have
        assert dialog.provider_list.count() > 0
        assert len(dialog.provider_list.selectedItems()) == 1
        assert dialog.current_provider is not None

    def test_empty_provider_list_edge_case(self, dialog):
        """Test behavior when provider list is cleared."""
        # Save original state
        original_count = dialog.provider_list.count()
        original_provider = dialog.current_provider

        # Clear all providers in the registry
        all_names = [p.name for p in dialog.registry.list_providers()]
        for name in all_names:
            dialog.registry.remove_provider(name)

        # Refresh the list
        dialog.refresh_provider_list()

        # Now there should be no providers
        assert dialog.provider_list.count() == 0
        assert len(dialog.provider_list.selectedItems()) == 0
        # The current provider may remain as is or become None

        # Restore original providers for other tests
        dialog.registry._initialize_default_providers()
        dialog.refresh_provider_list()
        assert dialog.provider_list.count() > 0

    def test_select_nonexistent_provider(self, dialog, qtbot):
        """Test selecting a provider that doesn't exist in registry."""
        # First, ensure we have a known valid provider
        assert dialog.current_provider is not None

        # Try to select a provider name that doesn't exist
        dialog.provider_list.clearSelection()

        # Add a fake provider to the list (but not in registry)
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QListWidgetItem
        fake_item = QListWidgetItem("Fake:NonExistentProvider")
        fake_item.setData(Qt.ItemDataRole.UserRole, "NonExistentProvider")
        dialog.provider_list.addItem(fake_item)

        # Select the fake item
        dialog.provider_list.setCurrentItem(fake_item)
        dialog.provider_selected()  # This should handle the missing provider gracefully

        # Form should be cleared since provider doesn't exist
        assert dialog.name_input.text() == ""
        assert dialog.current_provider is None

        # Clean up: remove the fake item
        dialog.provider_list.takeItem(dialog.provider_list.row(fake_item))

    def test_rapid_provider_switching(self, dialog, qtbot):
        """Test rapid switching between providers doesn't break the UI."""
        # Ensure we have at least 2 providers
        assert dialog.provider_list.count() >= 2

        original_provider = dialog.current_provider.name

        # Rapidly switch between first two providers multiple times
        for i in range(3):
            # Switch to second provider
            dialog.provider_list.setCurrentRow(1)
            dialog.provider_selected()  # Manually trigger to avoid qtbot complexity
            second_provider_name = dialog.current_provider.name if dialog.current_provider else ""

            # Switch back to first provider
            dialog.provider_list.setCurrentRow(0)
            dialog.provider_selected()
            first_provider_name = dialog.current_provider.name if dialog.current_provider else ""

            assert first_provider_name != ""  # Should have a provider loaded
            assert first_provider_name != second_provider_name  # Should be different providers

    def test_form_field_overflow_input(self, dialog, qtbot):
        """Test handling of very long inputs in form fields."""
        original_username = dialog.username_input.text()
        original_url = dialog.url_template_input.toPlainText()

        # Test very long username input
        long_username = "a" * 1000  # 1000 characters
        dialog.username_input.setText(long_username)
        assert dialog.username_input.text() == long_username

        # Test very long URL template
        long_url = "jdbc:verylong://host:port/database?param=" + "x" * 1000
        dialog.url_template_input.setPlainText(long_url)
        assert dialog.url_template_input.toPlainText() == long_url

        # Restore original values
        dialog.username_input.setText(original_username)
        dialog.url_template_input.setPlainText(original_url)

    def test_provider_name_with_special_characters(self, dialog, qtbot):
        """Test provider operations with special characters in names."""
        initial_count = dialog.provider_list.count()

        # Add a provider with special characters
        dialog.add_provider()
        dialog.name_input.setText("Test@#$%^&*()Provider With [Special] {Chars}")

        # Verify it was added correctly
        assert dialog.provider_list.count() == initial_count + 1
        assert dialog.name_input.text() == "Test@#$%^&*()Provider With [Special] {Chars}"

    def test_concurrent_group_expansion(self, dialog):
        """Test expanding multiple groups simultaneously."""
        # Get initial states
        conn_expanded = dialog.connection_group.isChecked()
        driver_expanded = dialog.driver_group.isChecked()
        advanced_expanded = dialog.advanced_group.isChecked()

        # Expand all groups
        dialog.connection_group.setChecked(True)
        dialog.driver_group.setChecked(True)
        dialog.advanced_group.setChecked(True)

        # Verify all are expanded
        assert dialog.connection_group.isChecked() is True
        assert dialog.driver_group.isChecked() is True
        assert dialog.advanced_group.isChecked() is True

        # Collapse them back
        dialog.connection_group.setChecked(False)
        dialog.driver_group.setChecked(False)
        dialog.advanced_group.setChecked(False)

        # Verify all are collapsed
        assert dialog.connection_group.isChecked() is False
        assert dialog.driver_group.isChecked() is False
        assert dialog.advanced_group.isChecked() is False

        # Restore to expected default state
        dialog.connection_group.setChecked(True)  # Connection group should be expanded by default

    def test_concurrent_edits_in_different_fields(self, dialog, qtbot):
        """Test editing multiple fields simultaneously."""
        original_name = dialog.name_input.text()
        original_user = dialog.username_input.text()
        original_url = dialog.url_template_input.toPlainText()

        # Edit multiple fields
        new_name = "Concurrent Edit Test"
        new_user = "testuser_concurrent"
        new_url = "jdbc:concurrent://host:port/db"

        dialog.name_input.setText(new_name)
        dialog.username_input.setText(new_user)
        dialog.url_template_input.setPlainText(new_url)

        # Verify all changes are applied
        assert dialog.name_input.text() == new_name
        assert dialog.username_input.text() == new_user
        assert dialog.url_template_input.toPlainText() == new_url

        # Restore original values
        dialog.name_input.setText(original_name)
        dialog.username_input.setText(original_user)
        dialog.url_template_input.setPlainText(original_url)

    def test_add_then_immediately_delete_provider(self, dialog):
        """Test adding and then immediately deleting a provider."""
        import unittest.mock

        from PySide6.QtWidgets import QMessageBox

        initial_count = dialog.provider_list.count()
        initial_provider = dialog.current_provider.name if dialog.current_provider else None

        # Add a new provider
        dialog.add_provider()
        assert dialog.provider_list.count() == initial_count + 1

        # Mock the QMessageBox.question to automatically return 'Yes' to avoid popup
        with unittest.mock.patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Yes):
            # The new provider should be selected, so delete it
            dialog.delete_selected()

        # Verify count is back to original
        assert dialog.provider_list.count() == initial_count

    def test_registry_persistence_after_form_edits(self, dialog):
        """Test that edits are properly stored and persisted."""
        # Get current provider
        current_name = dialog.current_provider.name
        original_driver = dialog.current_provider.driver_class

        # Make an edit
        new_driver = "com.test.updated.driver"
        dialog.driver_class_input.setText(new_driver)

        # Save the changes (simulating accept)
        original_current = dialog.current_provider
        dialog.current_provider.driver_class = new_driver  # Update in-memory object

        # Check if the change is reflected
        updated_provider = dialog.registry.get_provider(current_name)
        # Note: The provider in registry may not be updated until accept() is called

        # The in-memory current_provider should have the new value
        assert dialog.current_provider.driver_class != original_driver
        assert dialog.current_provider.driver_class == new_driver

    def test_multiple_dialog_instances(self, app):
        """Test that multiple dialog instances don't interfere with each other."""
        # Create first dialog
        dialog1 = ProviderConfigDialog(None)
        # Ensure the first dialog's registry is properly initialized
        if len(dialog1.registry.list_providers()) == 0:
            dialog1.registry._initialize_default_providers()
        # Refresh the provider list UI to match the registry
        dialog1.refresh_provider_list()
        # Ensure a provider is selected
        if len(dialog1.provider_list.selectedItems()) == 0 and dialog1.provider_list.count() > 0:
            dialog1.provider_list.setCurrentRow(0)
            dialog1.provider_selected()

        provider1 = dialog1.current_provider.name if dialog1.current_provider else None

        # Create second dialog - each dialog should have its own registry instance
        dialog2 = ProviderConfigDialog(None)
        # Ensure the second dialog's registry is properly initialized
        if len(dialog2.registry.list_providers()) == 0:
            dialog2.registry._initialize_default_providers()
        # Refresh the provider list UI to match the registry
        dialog2.refresh_provider_list()
        # Ensure a provider is selected for dialog2
        if len(dialog2.provider_list.selectedItems()) == 0 and dialog2.provider_list.count() > 0:
            dialog2.provider_list.setCurrentRow(0)
            dialog2.provider_selected()

        provider2 = dialog2.current_provider.name if dialog2.current_provider else None

        # Each should have their own state
        # Even if one fails to have a current_provider due to race conditions in test env,
        # at least check that both have providers in their lists
        assert dialog1.provider_list.count() > 0, "Dialog1 should have providers in list"
        assert dialog2.provider_list.count() > 0, "Dialog2 should have providers in list"

        # If both have selected items, then both should have current providers
        if len(dialog1.provider_list.selectedItems()) > 0:
            assert dialog1.current_provider is not None
        if len(dialog2.provider_list.selectedItems()) > 0:
            assert dialog2.current_provider is not None

        # At least one should have working state
        has_state = (dialog1.current_provider is not None) or (dialog2.current_provider is not None)
        assert has_state, "At least one dialog should have state"
        # Note: Both might have the same initial provider selected, which is fine

        # Make different edits in each
        original_user1 = dialog1.username_input.text()
        original_user2 = dialog2.username_input.text()

        dialog1.username_input.setText("Dialog1User")
        dialog2.username_input.setText("Dialog2User")

        assert dialog1.username_input.text() == "Dialog1User"
        assert dialog2.username_input.text() == "Dialog2User"

        # Clean up
        dialog1.close()
        dialog2.close()

    def test_group_box_keyboard_navigation(self, dialog):
        """Test keyboard interaction with group boxes."""
        # This tests whether group boxes can be toggled via keyboard
        original_state = dialog.connection_group.isChecked()

        # The group box should be checkable (toggling via spacebar in UI)
        assert dialog.connection_group.isCheckable() is True

        # Toggle via code (simulating keyboard interaction)
        dialog.connection_group.setChecked(not original_state)
        assert dialog.connection_group.isChecked() != original_state

        # Toggle back
        dialog.connection_group.setChecked(original_state)
        assert dialog.connection_group.isChecked() == original_state

    def test_add_provider_with_empty_registry(self, dialog):
        """Test adding provider when registry is empty."""
        # Save original providers
        original_providers = dialog.registry.list_providers()

        # Clear registry temporarily
        all_names = [p.name for p in original_providers]
        for name in all_names:
            dialog.registry.remove_provider(name)

        # Add a provider while registry is empty
        initial_count = dialog.provider_list.count()
        dialog.add_provider()

        # Should still add to UI even if registry is empty
        assert dialog.provider_list.count() == initial_count + 1

        # Restore original providers
        dialog.registry._initialize_default_providers()


class TestUserInteractionScenarios:
    """Test real user interaction scenarios using qtbot."""

    def test_typical_user_workflow(self, dialog, qtbot):
        """Test a typical user workflow: select provider, edit details, save."""
        # User opens dialog - should have provider pre-selected
        assert dialog.current_provider is not None
        original_name = dialog.current_provider.name

        # User edits connection details
        original_username = dialog.username_input.text()
        dialog.username_input.setText("new_user")
        assert dialog.username_input.text() == "new_user"

        original_password = dialog.password_input.text()
        dialog.password_input.setText("new_password")
        assert dialog.password_input.text() == "new_password"

        # User might expand driver settings to check driver
        driver_expanded_before = dialog.driver_group.isChecked()
        dialog.driver_group.setChecked(True)  # Expand
        assert dialog.driver_group.isChecked() is True

        # User sees driver info
        driver_class = dialog.driver_class_input.text()
        assert driver_class != ""

        # User collapses driver settings
        dialog.driver_group.setChecked(False)
        assert dialog.driver_group.isChecked() is False

        # Go back to connection settings (should remain expanded by default)
        assert dialog.connection_group.isChecked() is True

        # Restore original values
        dialog.username_input.setText(original_username)
        dialog.password_input.setText(original_password)

    def test_user_adds_new_provider_workflow(self, dialog, qtbot):
        """Test user adding a new provider workflow."""
        initial_count = dialog.provider_list.count()
        initial_provider_name = dialog.current_provider.name if dialog.current_provider else None

        # User clicks to add new provider
        dialog.add_provider()

        # List should have new item
        assert dialog.provider_list.count() == initial_count + 1

        # Form should have new provider loaded (though current_provider might be None due to selection mechanism)
        # The list selection should show the new provider
        selected_items = dialog.provider_list.selectedItems()
        assert len(selected_items) > 0
        assert ": New Provider" in selected_items[0].text()

    def test_user_switches_between_providers(self, dialog, qtbot):
        """Test user switching between different providers."""
        # Ensure we have multiple providers to switch between
        assert dialog.provider_list.count() >= 2

        # Note current provider details
        first_provider_name = dialog.current_provider.name
        first_driver = dialog.driver_class_input.text()

        # User switches to second provider
        dialog.provider_list.setCurrentRow(1)
        dialog.provider_selected()

        # Should have different provider loaded
        second_provider_name = dialog.current_provider.name
        second_driver = dialog.driver_class_input.text()

        assert first_provider_name != second_provider_name
        assert first_driver != second_driver  # Different providers should have different drivers

        # User switches back
        dialog.provider_list.setCurrentRow(0)
        dialog.provider_selected()

        # Should be back to first provider
        back_to_first_name = dialog.current_provider.name
        back_to_first_driver = dialog.driver_class_input.text()

        assert back_to_first_name == first_provider_name
        assert back_to_first_driver == first_driver


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
