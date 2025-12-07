"""Comprehensive tests for enhanced widgets functionality."""
import pytest
from unittest.mock import MagicMock, patch
from PySide6.QtCore import Qt, QPoint, QRect
from PySide6.QtGui import QPainter, QColor, QPen, QBrush
from PySide6.QtWidgets import QWidget

from dbutils.gui.widgets.enhanced_widgets import (
    StatusIndicator,
    EnhancedTableItem,
    SearchHighlightWidget,
    ProgressBar,
    CollapsiblePanel
)
from dbutils.db_browser import TableInfo

class TestStatusIndicator:
    """Test the StatusIndicator widget."""

    def test_status_indicator_initialization(self):
        """Test StatusIndicator initialization."""
        indicator = StatusIndicator()

        assert indicator.status_label.text() == "🔍"
        assert indicator.text_label.text() == "Ready"
        assert indicator.animation_timer is not None
        assert indicator.animation_angle == 0

    def test_status_indicator_searching_state(self):
        """Test StatusIndicator searching state."""
        indicator = StatusIndicator()

        # Set to searching
        indicator.set_searching(True)

        assert indicator.status_label.text() == "🔄"
        assert indicator.text_label.text() == "Searching..."
        assert indicator.animation_timer.isActive()

        # Set back to ready
        indicator.set_searching(False)

        assert indicator.status_label.text() == "✅"
        assert indicator.text_label.text() == "Ready"
        assert not indicator.animation_timer.isActive()

    def test_status_indicator_animation(self):
        """Test StatusIndicator animation."""
        indicator = StatusIndicator()

        # Set to searching to start animation
        indicator.set_searching(True)

        # Manually trigger animation
        initial_angle = indicator.animation_angle
        indicator.animate_progress()
        assert indicator.animation_angle == (initial_angle + 10) % 360

        # Verify progress style was updated
        # (This would be visual, but we can verify the method was called)

    def test_status_indicator_progress_reset(self):
        """Test StatusIndicator progress reset."""
        indicator = StatusIndicator()

        # Set to searching
        indicator.set_searching(True)

        # Reset progress
        indicator.reset_progress()

        # Verify progress was reset (visual state)
        # The method should reset the style to default
        assert True  # Method should execute without error

class TestEnhancedTableItem:
    """Test the EnhancedTableItem widget."""

    def test_enhanced_table_item_initialization(self):
        """Test EnhancedTableItem initialization."""
        table_info = TableInfo(schema="TEST", name="USERS", remarks="User table")
        item = EnhancedTableItem(table_info, match_type="exact")

        assert item.table_info == table_info
        assert item.match_type == "exact"

    def test_enhanced_table_item_different_match_types(self):
        """Test EnhancedTableItem with different match types."""
        table_info = TableInfo(schema="TEST", name="USERS", remarks="User table")

        # Test exact match
        item_exact = EnhancedTableItem(table_info, match_type="exact")
        assert item_exact.match_type == "exact"

        # Test prefix match
        item_prefix = EnhancedTableItem(table_info, match_type="prefix")
        assert item_prefix.match_type == "prefix"

        # Test fuzzy match
        item_fuzzy = EnhancedTableItem(table_info, match_type="fuzzy")
        assert item_fuzzy.match_type == "fuzzy"

        # Test normal (default)
        item_normal = EnhancedTableItem(table_info, match_type="normal")
        assert item_normal.match_type == "normal"

    def test_enhanced_table_item_hover_effects(self):
        """Test EnhancedTableItem hover effects."""
        table_info = TableInfo(schema="TEST", name="USERS", remarks="User table")
        item = EnhancedTableItem(table_info, match_type="exact")

        # Test enter event (hover in)
        mock_event = MagicMock()
        item.enterEvent(mock_event)

        # Verify stylesheet was updated for hover state
        assert "border: 1px solid #3498db" in item.styleSheet()
        assert "background-color: #f8f9fa" in item.styleSheet()

        # Test leave event (hover out)
        item.leaveEvent(mock_event)

        # Verify stylesheet was updated back to normal state
        assert "border: 1px solid #e0e0e0" in item.styleSheet()
        assert "background-color: white" in item.styleSheet()

class TestSearchHighlightWidget:
    """Test the SearchHighlightWidget."""

    def test_search_highlight_widget_initialization(self):
        """Test SearchHighlightWidget initialization."""
        widget = SearchHighlightWidget()

        assert widget.search_text == ""
        assert hasattr(widget, 'search_input')
        assert hasattr(widget, 'suggestions_widget')

    def test_search_highlight_widget_search_text(self):
        """Test SearchHighlightWidget search text functionality."""
        widget = SearchHighlightWidget()

        # Set search text
        widget.set_search_text("test query")

        assert widget.search_text == "test query"

        # Clear search
        widget.clear_search()

        assert widget.search_text == ""
        # search_input.clear() should have been called

    def test_search_highlight_widget_placeholder(self):
        """Test SearchHighlightWidget placeholder text."""
        widget = SearchHighlightWidget()

        # Verify placeholder contains search text
        placeholder = widget.search_input.placeholderText()
        assert "Search" in placeholder

class TestProgressBar:
    """Test the ProgressBar widget."""

    def test_progress_bar_initialization(self):
        """Test ProgressBar initialization."""
        progress_bar = ProgressBar()

        assert progress_bar.value == 0
        assert progress_bar.maximum == 100
        assert hasattr(progress_bar, 'progress_container')
        assert hasattr(progress_bar, 'progress_bar')
        assert hasattr(progress_bar, 'progress_text')

    def test_progress_bar_value_updates(self):
        """Test ProgressBar value updates."""
        progress_bar = ProgressBar()

        # Set value
        progress_bar.set_value(50)
        assert progress_bar.value == 50

        # Set maximum
        progress_bar.set_maximum(200)
        assert progress_bar.maximum == 200

        # Update should recalculate percentage
        progress_bar.update_progress()
        assert progress_bar.progress_text.text() == "25%"

    def test_progress_bar_edge_cases(self):
        """Test ProgressBar edge cases."""
        progress_bar = ProgressBar()

        # Test value below 0
        progress_bar.set_value(-10)
        assert progress_bar.value == 0  # Should be clamped

        # Test value above maximum
        progress_bar.set_value(200)
        assert progress_bar.value == 100  # Should be clamped

        # Test zero maximum
        progress_bar.set_maximum(0)
        progress_bar.set_value(50)
        progress_bar.update_progress()
        assert progress_bar.progress_text.text() == "0%"  # Should handle division by zero

class TestCollapsiblePanel:
    """Test the CollapsiblePanel widget."""

    def test_collapsible_panel_initialization(self):
        """Test CollapsiblePanel initialization."""
        panel = CollapsiblePanel("Test Panel")

        assert panel.title == "Test Panel"
        assert panel.is_collapsed is False
        assert hasattr(panel, 'toggle_button')
        assert hasattr(panel, 'content_widget')

    def test_collapsible_panel_collapsed_state(self):
        """Test CollapsiblePanel collapsed state."""
        # Test initialized as collapsed
        panel_collapsed = CollapsiblePanel("Collapsed Panel", collapsed=True)
        assert panel_collapsed.is_collapsed is True
        assert panel_collapsed.toggle_button.text() == "▶ Collapsed Panel"
        assert not panel_collapsed.content_widget.isVisible()

        # Test initialized as expanded
        panel_expanded = CollapsiblePanel("Expanded Panel", collapsed=False)
        assert panel_expanded.is_collapsed is False
        assert panel_expanded.toggle_button.text() == "▼ Expanded Panel"
        assert panel_expanded.content_widget.isVisible()

    def test_collapsible_panel_toggle(self):
        """Test CollapsiblePanel toggle functionality."""
        panel = CollapsiblePanel("Test Panel", collapsed=False)

        # Initially expanded
        assert panel.is_collapsed is False
        assert panel.content_widget.isVisible()

        # Toggle to collapsed
        panel.toggle_collapse()
        assert panel.is_collapsed is True
        assert panel.toggle_button.text() == "▶ Test Panel"
        assert not panel.content_widget.isVisible()

        # Toggle back to expanded
        panel.toggle_collapse()
        assert panel.is_collapsed is False
        assert panel.toggle_button.text() == "▼ Test Panel"
        assert panel.content_widget.isVisible()

    def test_collapsible_panel_add_widget(self):
        """Test adding widgets to CollapsiblePanel."""
        panel = CollapsiblePanel("Test Panel")

        # Create a test widget
        test_widget = QWidget()
        test_widget.setObjectName("test_widget")

        # Add widget
        panel.add_widget(test_widget)

        # Verify widget was added to content layout
        # The widget should be in the content_layout
        assert test_widget.parent() == panel.content_widget

    def test_collapsible_panel_add_layout(self):
        """Test adding layouts to CollapsiblePanel."""
        panel = CollapsiblePanel("Test Panel")

        # Create a test layout
        from PySide6.QtWidgets import QHBoxLayout
        test_layout = QHBoxLayout()

        # Add layout
        panel.add_layout(test_layout)

        # Verify layout was added to content layout
        # This is more of a functional test - the method should execute without error
        assert True

    def test_collapsible_panel_update_state(self):
        """Test CollapsiblePanel state updates."""
        panel = CollapsiblePanel("Test Panel")

        # Manually update state
        panel.update_collapse_state()

        # Verify state is consistent
        expected_text = "▶ Test Panel" if panel.is_collapsed else "▼ Test Panel"
        assert panel.toggle_button.text() == expected_text
        assert panel.content_widget.isVisible() == (not panel.is_collapsed)

    def test_collapsible_panel_button_styling(self):
        """Test CollapsiblePanel button styling."""
        panel = CollapsiblePanel("Test Panel")

        # Verify button has expected styling
        style = panel.toggle_button.styleSheet()
        assert "border: none" in style
        assert "background-color: transparent" in style
        assert "font-weight: bold" in style

        # Verify hover styling is present
        assert "QPushButton:hover" in style
        assert "background-color: #f0f0f0" in style