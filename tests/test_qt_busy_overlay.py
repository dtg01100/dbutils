"""Comprehensive tests for BusyOverlay widget functionality."""

from unittest.mock import MagicMock

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QWidget

from dbutils.gui.widgets.enhanced_widgets import BusyOverlay


class TestBusyOverlay:
    """Test the BusyOverlay widget functionality."""

    def test_busy_overlay_initialization(self):
        """Test BusyOverlay initialization."""
        parent = QWidget()
        overlay = BusyOverlay(parent, "Loading data...")

        assert overlay.parent() == parent
        assert overlay._message == "Loading data..."
        assert not overlay.isVisible()
        assert overlay._angle == 0
        assert overlay._timer is not None

    def test_busy_overlay_show_with_message(self):
        """Test showing BusyOverlay with a custom message."""
        parent = QWidget()
        parent.resize(200, 200)
        overlay = BusyOverlay(parent, "Initial message")

        # Show with default message
        overlay.show_with_message()
        assert overlay.isVisible()
        assert overlay._message == "Initial message"

        # Show with custom message
        overlay.show_with_message("Custom loading message")
        assert overlay._message == "Custom loading message"
        assert overlay.isVisible()

    def test_busy_overlay_hide(self):
        """Test hiding BusyOverlay."""
        parent = QWidget()
        overlay = BusyOverlay(parent)

        # Show first
        overlay.show_with_message("Loading...")
        assert overlay.isVisible()

        # Hide
        overlay.hide()
        assert not overlay.isVisible()

    def test_busy_overlay_animation(self):
        """Test BusyOverlay animation functionality."""
        parent = QWidget()
        overlay = BusyOverlay(parent)

        # Manually trigger animation tick
        initial_angle = overlay._angle
        overlay._tick()
        assert overlay._angle == (initial_angle + 6) % 360

    def test_busy_overlay_event_filter(self):
        """Test BusyOverlay event filter for parent resizing."""
        parent = QWidget()
        parent.resize(300, 200)
        overlay = BusyOverlay(parent)

        # Create a mock event
        mock_event = MagicMock()
        mock_event.type.return_value = Qt.EventType.Resize

        # Test event filter
        result = overlay.eventFilter(parent, mock_event)
        assert not result  # Should return False to allow event to continue

    def test_busy_overlay_paint_event(self):
        """Test BusyOverlay paint event."""
        parent = QWidget()
        parent.resize(400, 300)
        overlay = BusyOverlay(parent, "Processing...")

        # Create a mock painter and inject via the overlay's painter factory
        mock_painter = MagicMock(spec=QPainter)
        overlay._create_painter = lambda: mock_painter

        # Create a mock event
        mock_event = MagicMock()

        # Call paintEvent
        overlay.paintEvent(mock_event)

        # Verify painter methods were called
        mock_painter.setRenderHint.assert_called()
        mock_painter.fillRect.assert_called()
        mock_painter.setPen.assert_called()
        mock_painter.setBrush.assert_called()
        mock_painter.drawArc.assert_called()
        mock_painter.setFont.assert_called()
        mock_painter.drawText.assert_called()

    def test_busy_overlay_message_update(self):
        """Test updating BusyOverlay message."""
        parent = QWidget()
        overlay = BusyOverlay(parent, "Initial message")

        # Update message
        overlay.set_message("New message")
        assert overlay._message == "New message"

    def test_busy_overlay_geometry_update(self):
        """Test BusyOverlay geometry updates with parent."""
        parent = QWidget()
        parent.resize(500, 400)
        overlay = BusyOverlay(parent)

        # Show overlay
        overlay.show_with_message("Loading...")

        # Verify geometry matches parent
        assert overlay.geometry() == parent.rect()

        # Resize parent
        parent.resize(600, 450)

        # Trigger event filter to update geometry
        mock_event = MagicMock()
        mock_event.type.return_value = Qt.EventType.Resize
        overlay.eventFilter(parent, mock_event)

        # Verify geometry updated
        assert overlay.geometry() == parent.rect()

    def test_busy_overlay_fade_animation(self):
        """Test BusyOverlay fade animation properties."""
        parent = QWidget()
        overlay = BusyOverlay(parent)

        # Check fade animation properties
        assert overlay._fade is not None
        assert overlay._fade.duration() == 150
        assert overlay._fade.startValue() == 0.0
        assert overlay._fade.endValue() == 1.0

    def test_busy_overlay_timer_properties(self):
        """Test BusyOverlay timer properties."""
        parent = QWidget()
        overlay = BusyOverlay(parent)

        # Check timer properties
        assert overlay._timer is not None
        assert overlay._timer.interval() == 16  # ~60 FPS

    def test_busy_overlay_without_parent(self):
        """Test BusyOverlay without a parent."""
        overlay = BusyOverlay(None, "Standalone overlay")

        assert overlay.parent() is None
        assert overlay._message == "Standalone overlay"
        assert not overlay.isVisible()

        # Should still be able to show/hide
        overlay.show_with_message("Standalone loading")
        assert overlay.isVisible()
        assert overlay._message == "Standalone loading"

        overlay.hide()
        assert not overlay.isVisible()

    def test_busy_overlay_multiple_show_calls(self):
        """Test multiple show calls on BusyOverlay."""
        parent = QWidget()
        overlay = BusyOverlay(parent, "First message")

        # First show
        overlay.show_with_message("First message")
        assert overlay.isVisible()
        assert overlay._message == "First message"

        # Second show with different message
        overlay.show_with_message("Second message")
        assert overlay.isVisible()
        assert overlay._message == "Second message"

        # Hide and show again
        overlay.hide()
        assert not overlay.isVisible()

        overlay.show_with_message("Third message")
        assert overlay.isVisible()
        assert overlay._message == "Third message"
