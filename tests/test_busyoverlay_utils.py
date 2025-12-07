"""Utility tests for BusyOverlay that show how to inject a mock painter.

This test demonstrates overriding the protected BusyOverlay._create_painter
factory to return a MagicMock painter so paintEvent runs using a Mock rather
than a real QPainter (which requires a paint engine).
"""
from unittest.mock import MagicMock

from PySide6.QtGui import QPainter

from dbutils.gui.widgets.enhanced_widgets import BusyOverlay


def test_busyoverlay_painter_injection(qapp):
    """Show how to override _create_painter and assert paintEvent invoked methods.

    The test uses `qapp` fixture (provided by pytest-qt or the conftest.py) to
    ensure a QApplication exists; then overrides `_create_painter` to return a
    MagicMock that mirrors QPainter's API. This avoids painting on a real
    paint engine while asserting that the painting code path executed.
    """
    overlay = BusyOverlay(None, message='Hello Test')

    # Inject a MagicMock painter instance via the factory method
    mock_painter = MagicMock(spec=QPainter)
    overlay._create_painter = lambda: mock_painter

    # Call paintEvent with a dummy event: the overlay should use our mock
    class DummyEvent:
        pass

    overlay.paintEvent(DummyEvent())

    # Verify that a couple of common painter methods were invoked
    assert mock_painter.setRenderHint.called, "setRenderHint not called"
    assert mock_painter.fillRect.called, "fillRect not called"
    assert mock_painter.setPen.called, "setPen not called"
    assert mock_painter.drawText.called, "drawText not called"

    # Last painter reference should be cleared after paintEvent
    assert not hasattr(overlay, '_last_painter')
