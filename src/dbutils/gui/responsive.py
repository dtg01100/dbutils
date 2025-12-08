#!/usr/bin/env python3
"""
Responsive Design Module

Responsive design utilities for the database browser application.
This module addresses responsive design issues by providing:
- Layout adaptation strategies
- Screen size detection
- Responsive component behavior
- Breakpoint management
- Device detection

Features:
- Responsive layout management
- Screen size and device detection
- Breakpoint-based behavior
- Flexible layout strategies
- Orientation change handling
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Tuple

# Try to import Qt components for responsive design
try:
    from PySide6.QtCore import QObject, QRect, QSize, Qt, Signal
    from PySide6.QtGui import QGuiApplication, QScreen
    from PySide6.QtWidgets import QApplication, QDesktopWidget, QWidget

    QT_AVAILABLE = True
except ImportError:
    try:
        from PyQt6.QtCore import QObject, QRect, QSize, Qt, Signal
        from PyQt6.QtGui import QGuiApplication, QScreen
        from PyQt6.QtWidgets import QApplication, QDesktopWidget, QWidget

        QT_AVAILABLE = True
    except ImportError:
        QT_AVAILABLE = False


class Breakpoint(Enum):
    """Standard breakpoints for responsive design."""

    XS = auto()  # Extra small (mobile)
    SM = auto()  # Small (tablet)
    MD = auto()  # Medium (small desktop)
    LG = auto()  # Large (desktop)
    XL = auto()  # Extra large (large desktop)


@dataclass
class ScreenInfo:
    """Information about screen size and capabilities."""

    width: int
    height: int
    dpi: int
    device_pixel_ratio: float
    orientation: str  # "portrait" or "landscape"
    breakpoint: Breakpoint


@dataclass
class ResponsiveSettings:
    """Responsive design settings."""

    breakpoints: Dict[Breakpoint, int]
    mobile_breakpoint: int
    tablet_breakpoint: int
    desktop_breakpoint: int
    large_desktop_breakpoint: int


class ResponsiveManager:
    """Responsive design management for the database browser."""

    def __init__(self):
        self._current_screen_info: Optional[ScreenInfo] = None
        self._responsive_settings = self._get_default_settings()
        self._listeners: List[Callable] = []
        self._lock = threading.RLock()

        # Initialize screen monitoring
        if QT_AVAILABLE:
            self._setup_screen_monitoring()

    def _get_default_settings(self) -> ResponsiveSettings:
        """Get default responsive settings."""
        return ResponsiveSettings(
            breakpoints={
                Breakpoint.XS: 576,
                Breakpoint.SM: 768,
                Breakpoint.MD: 992,
                Breakpoint.LG: 1200,
                Breakpoint.XL: 1400,
            },
            mobile_breakpoint=576,
            tablet_breakpoint=768,
            desktop_breakpoint=992,
            large_desktop_breakpoint=1200,
        )

    def _setup_screen_monitoring(self):
        """Setup screen size monitoring."""
        if not QT_AVAILABLE:
            return

        # Initial screen detection
        self._detect_screen_info()

        # Connect to screen change signals if available
        if hasattr(QApplication, "primaryScreenChanged"):
            QApplication.primaryScreenChanged.connect(self._on_screen_changed)

        # Setup timer for periodic checks
        from PySide6.QtCore import QTimer

        self._screen_timer = QTimer()
        self._screen_timer.timeout.connect(self._check_screen_changes)
        self._screen_timer.start(1000)  # Check every second

    def _on_screen_changed(self):
        """Handle screen change events."""
        self._detect_screen_info()
        self._notify_listeners()

    def _check_screen_changes(self):
        """Periodically check for screen changes."""
        if QT_AVAILABLE:
            current_info = self._get_current_screen_info()
            if (
                not self._current_screen_info
                or current_info.width != self._current_screen_info.width
                or current_info.height != self._current_screen_info.height
            ):
                self._current_screen_info = current_info
                self._notify_listeners()

    def _detect_screen_info(self):
        """Detect current screen information."""
        if not QT_AVAILABLE:
            return

        try:
            screen = QApplication.primaryScreen()
            if not screen:
                return

            # Get screen geometry
            geometry = screen.geometry()
            available_geometry = screen.availableGeometry()

            # Determine orientation
            orientation = "portrait" if geometry.height() > geometry.width() else "landscape"

            # Get DPI and device pixel ratio
            dpi = screen.physicalDotsPerInch()
            device_pixel_ratio = screen.devicePixelRatio()

            # Determine breakpoint
            width = available_geometry.width()
            breakpoint = self._determine_breakpoint(width)

            self._current_screen_info = ScreenInfo(
                width=width,
                height=available_geometry.height(),
                dpi=dpi,
                device_pixel_ratio=device_pixel_ratio,
                orientation=orientation,
                breakpoint=breakpoint,
            )

        except Exception:
            # Fallback to default values
            self._current_screen_info = ScreenInfo(
                width=1024,
                height=768,
                dpi=96,
                device_pixel_ratio=1.0,
                orientation="landscape",
                breakpoint=Breakpoint.MD,
            )

    def _get_current_screen_info(self) -> ScreenInfo:
        """Get current screen information."""
        if QT_AVAILABLE:
            try:
                screen = QApplication.primaryScreen()
                if screen:
                    geometry = screen.availableGeometry()
                    width = geometry.width()
                    height = geometry.height()
                    dpi = screen.physicalDotsPerInch()
                    ratio = screen.devicePixelRatio()
                    orientation = "portrait" if height > width else "landscape"
                    breakpoint = self._determine_breakpoint(width)

                    return ScreenInfo(
                        width=width,
                        height=height,
                        dpi=dpi,
                        device_pixel_ratio=ratio,
                        orientation=orientation,
                        breakpoint=breakpoint,
                    )
            except Exception:
                pass

        # Fallback
        return ScreenInfo(
            width=1024, height=768, dpi=96, device_pixel_ratio=1.0, orientation="landscape", breakpoint=Breakpoint.MD
        )

    def _determine_breakpoint(self, width: int) -> Breakpoint:
        """Determine breakpoint based on width."""
        if width < self._responsive_settings.breakpoints[Breakpoint.SM]:
            return Breakpoint.XS
        elif width < self._responsive_settings.breakpoints[Breakpoint.MD]:
            return Breakpoint.SM
        elif width < self._responsive_settings.breakpoints[Breakpoint.LG]:
            return Breakpoint.MD
        elif width < self._responsive_settings.breakpoints[Breakpoint.XL]:
            return Breakpoint.LG
        else:
            return Breakpoint.XL

    def get_screen_info(self) -> ScreenInfo:
        """Get current screen information."""
        with self._lock:
            if not self._current_screen_info:
                self._current_screen_info = self._get_current_screen_info()
            return self._current_screen_info

    def get_current_breakpoint(self) -> Breakpoint:
        """Get current breakpoint."""
        return self.get_screen_info().breakpoint

    def is_mobile(self) -> bool:
        """Check if current device is mobile-sized."""
        breakpoint = self.get_current_breakpoint()
        return breakpoint in [Breakpoint.XS]

    def is_tablet(self) -> bool:
        """Check if current device is tablet-sized."""
        breakpoint = self.get_current_breakpoint()
        return breakpoint in [Breakpoint.SM]

    def is_desktop(self) -> bool:
        """Check if current device is desktop-sized."""
        breakpoint = self.get_current_breakpoint()
        return breakpoint in [Breakpoint.MD, Breakpoint.LG]

    def is_large_desktop(self) -> bool:
        """Check if current device is large desktop-sized."""
        breakpoint = self.get_current_breakpoint()
        return breakpoint in [Breakpoint.XL]

    def is_portrait(self) -> bool:
        """Check if device is in portrait orientation."""
        return self.get_screen_info().orientation == "portrait"

    def is_landscape(self) -> bool:
        """Check if device is in landscape orientation."""
        return self.get_screen_info().orientation == "landscape"

    def get_screen_width(self) -> int:
        """Get current screen width."""
        return self.get_screen_info().width

    def get_screen_height(self) -> int:
        """Get current screen height."""
        return self.get_screen_info().height

    def get_device_pixel_ratio(self) -> float:
        """Get device pixel ratio."""
        return self.get_screen_info().device_pixel_ratio

    def get_dpi(self) -> int:
        """Get screen DPI."""
        return self.get_screen_info().dpi

    def add_responsive_listener(self, listener: Callable):
        """Add a listener for responsive changes."""
        with self._lock:
            if listener not in self._listeners:
                self._listeners.append(listener)

    def remove_responsive_listener(self, listener: Callable):
        """Remove a responsive listener."""
        with self._lock:
            if listener in self._listeners:
                self._listeners.remove(listener)

    def _notify_listeners(self):
        """Notify all listeners of responsive changes."""
        with self._lock:
            for listener in self._listeners:
                try:
                    listener(self.get_screen_info())
                except Exception:
                    # Don't let listener errors break the system
                    pass

    def set_responsive_settings(self, settings: ResponsiveSettings):
        """Update responsive settings."""
        with self._lock:
            self._responsive_settings = settings

    def get_responsive_settings(self) -> ResponsiveSettings:
        """Get current responsive settings."""
        with self._lock:
            return self._responsive_settings

    def get_breakpoint_width(self, breakpoint: Breakpoint) -> int:
        """Get width for a specific breakpoint."""
        with self._lock:
            return self._responsive_settings.breakpoints.get(breakpoint, 0)

    def is_breakpoint_or_wider(self, breakpoint: Breakpoint) -> bool:
        """Check if current width is at least the specified breakpoint."""
        current_breakpoint = self.get_current_breakpoint()
        breakpoint_order = [Breakpoint.XS, Breakpoint.SM, Breakpoint.MD, Breakpoint.LG, Breakpoint.XL]

        current_index = breakpoint_order.index(current_breakpoint)
        target_index = breakpoint_order.index(breakpoint)

        return current_index >= target_index

    def is_breakpoint_or_narrower(self, breakpoint: Breakpoint) -> bool:
        """Check if current width is at most the specified breakpoint."""
        current_breakpoint = self.get_current_breakpoint()
        breakpoint_order = [Breakpoint.XS, Breakpoint.SM, Breakpoint.MD, Breakpoint.LG, Breakpoint.XL]

        current_index = breakpoint_order.index(current_breakpoint)
        target_index = breakpoint_order.index(breakpoint)

        return current_index <= target_index

    def get_responsive_layout_recommendations(self) -> Dict[str, Any]:
        """Get layout recommendations based on current screen size."""
        breakpoint = self.get_current_breakpoint()
        screen_info = self.get_screen_info()

        recommendations = {
            "breakpoint": breakpoint.name,
            "orientation": screen_info.orientation,
            "dock_layout": "stacked",
            "panel_sizes": {},
            "font_scaling": 1.0,
            "spacing": "normal",
        }

        if breakpoint == Breakpoint.XS:  # Mobile
            recommendations.update(
                {
                    "dock_layout": "single_column",
                    "panel_sizes": {
                        "search": "full_width",
                        "tables": "full_width",
                        "columns": "full_width",
                        "contents": "full_width",
                    },
                    "font_scaling": 0.9,
                    "spacing": "compact",
                }
            )
        elif breakpoint == Breakpoint.SM:  # Tablet
            recommendations.update(
                {
                    "dock_layout": "two_column",
                    "panel_sizes": {
                        "search": "full_width",
                        "tables": "left_60",
                        "columns": "right_40",
                        "contents": "full_width",
                    },
                    "font_scaling": 0.95,
                    "spacing": "normal",
                }
            )
        elif breakpoint == Breakpoint.MD:  # Small desktop
            recommendations.update(
                {
                    "dock_layout": "three_column",
                    "panel_sizes": {
                        "search": "top_100",
                        "tables": "left_40",
                        "columns": "middle_30",
                        "contents": "right_30",
                    },
                    "font_scaling": 1.0,
                    "spacing": "normal",
                }
            )
        elif breakpoint == Breakpoint.LG:  # Desktop
            recommendations.update(
                {
                    "dock_layout": "four_column",
                    "panel_sizes": {
                        "search": "top_100",
                        "tables": "left_30",
                        "columns": "middle_left_25",
                        "contents": "middle_right_25",
                        "details": "right_20",
                    },
                    "font_scaling": 1.0,
                    "spacing": "expanded",
                }
            )
        else:  # XL - Large desktop
            recommendations.update(
                {
                    "dock_layout": "five_column",
                    "panel_sizes": {
                        "search": "top_100",
                        "tables": "left_25",
                        "columns": "middle_left_20",
                        "contents": "middle_right_30",
                        "details": "right_25",
                    },
                    "font_scaling": 1.05,
                    "spacing": "expanded",
                }
            )

        return recommendations

    def apply_responsive_styles(self, widget: QWidget):
        """Apply responsive styles to a widget based on current breakpoint."""
        if not QT_AVAILABLE or not widget:
            return

        breakpoint = self.get_current_breakpoint()
        stylesheet = ""

        if breakpoint == Breakpoint.XS:
            stylesheet = """
            /* Mobile styles */
            QWidget {
                font-size: 14px;
                padding: 4px;
            }
            QPushButton {
                min-width: 100px;
                padding: 6px 12px;
            }
            QLineEdit {
                min-height: 32px;
            }
            """
        elif breakpoint == Breakpoint.SM:
            stylesheet = """
            /* Tablet styles */
            QWidget {
                font-size: 14px;
                padding: 6px;
            }
            QPushButton {
                min-width: 120px;
                padding: 8px 16px;
            }
            """
        elif breakpoint == Breakpoint.MD:
            stylesheet = """
            /* Small desktop styles */
            QWidget {
                font-size: 14px;
                padding: 8px;
            }
            """
        elif breakpoint == Breakpoint.LG:
            stylesheet = """
            /* Desktop styles */
            QWidget {
                font-size: 14px;
                padding: 10px;
            }
            """
        else:  # XL
            stylesheet = """
            /* Large desktop styles */
            QWidget {
                font-size: 14px;
                padding: 12px;
            }
            """

        # Apply the stylesheet
        widget.setStyleSheet(widget.styleSheet() + stylesheet)

    def get_device_type(self) -> str:
        """Get the current device type."""
        breakpoint = self.get_current_breakpoint()

        if breakpoint == Breakpoint.XS:
            return "mobile"
        elif breakpoint == Breakpoint.SM:
            return "tablet"
        elif breakpoint in [Breakpoint.MD, Breakpoint.LG]:
            return "desktop"
        else:
            return "large_desktop"

    def get_responsive_font_size(self, base_size: int = 14) -> int:
        """Get font size adjusted for current screen size."""
        breakpoint = self.get_current_breakpoint()

        if breakpoint == Breakpoint.XS:
            return max(12, base_size - 2)
        elif breakpoint == Breakpoint.SM:
            return max(13, base_size - 1)
        elif breakpoint == Breakpoint.MD:
            return base_size
        elif breakpoint == Breakpoint.LG:
            return base_size + 1
        else:  # XL
            return base_size + 2

    def get_responsive_spacing(self, base_spacing: int = 8) -> int:
        """Get spacing adjusted for current screen size."""
        breakpoint = self.get_current_breakpoint()

        if breakpoint == Breakpoint.XS:
            return max(4, base_spacing - 4)
        elif breakpoint == Breakpoint.SM:
            return max(6, base_spacing - 2)
        elif breakpoint == Breakpoint.MD:
            return base_spacing
        elif breakpoint == Breakpoint.LG:
            return base_spacing + 2
        else:  # XL
            return base_spacing + 4

    def create_responsive_layout(self, widget: QWidget, layout_type: str = "auto") -> Optional[QWidget]:
        """Create a responsive layout for a widget."""
        if not QT_AVAILABLE:
            return None

        breakpoint = self.get_current_breakpoint()
        layout = None

        if layout_type == "auto" or layout_type == "stacked":
            from PySide6.QtWidgets import QVBoxLayout

            layout = QVBoxLayout(widget)
        elif layout_type == "grid" or (
            breakpoint in [Breakpoint.MD, Breakpoint.LG, Breakpoint.XL] and layout_type == "auto"
        ):
            from PySide6.QtWidgets import QGridLayout

            layout = QGridLayout(widget)
        else:  # Default to vertical for mobile/tablet
            from PySide6.QtWidgets import QVBoxLayout

            layout = QVBoxLayout(widget)

        if layout:
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(self.get_responsive_spacing())

        return layout

    def get_responsive_dock_sizes(self) -> List[int]:
        """Get recommended dock widget sizes for current screen size."""
        breakpoint = self.get_current_breakpoint()

        if breakpoint == Breakpoint.XS:  # Mobile - single column
            return [100]
        elif breakpoint == Breakpoint.SM:  # Tablet - two column
            return [60, 40]
        elif breakpoint == Breakpoint.MD:  # Small desktop - three column
            return [40, 30, 30]
        elif breakpoint == Breakpoint.LG:  # Desktop - four column
            return [30, 25, 25, 20]
        else:  # XL - large desktop - five column
            return [25, 20, 30, 20, 5]

    def get_responsive_icon_size(self, base_size: int = 24) -> int:
        """Get icon size adjusted for current screen size."""
        breakpoint = self.get_current_breakpoint()

        if breakpoint == Breakpoint.XS:
            return max(16, base_size - 8)
        elif breakpoint == Breakpoint.SM:
            return max(20, base_size - 4)
        elif breakpoint == Breakpoint.MD:
            return base_size
        elif breakpoint == Breakpoint.LG:
            return base_size + 4
        else:  # XL
            return base_size + 8

    def get_responsive_button_size(self) -> Tuple[int, int]:
        """Get recommended button size for current screen size."""
        breakpoint = self.get_current_breakpoint()

        if breakpoint == Breakpoint.XS:
            return (80, 32)  # width, height
        elif breakpoint == Breakpoint.SM:
            return (100, 36)
        elif breakpoint == Breakpoint.MD:
            return (120, 40)
        elif breakpoint == Breakpoint.LG:
            return (140, 44)
        else:  # XL
            return (160, 48)

    def get_responsive_input_size(self) -> Tuple[int, int]:
        """Get recommended input field size for current screen size."""
        breakpoint = self.get_current_breakpoint()

        if breakpoint == Breakpoint.XS:
            return (200, 32)  # width, height
        elif breakpoint == Breakpoint.SM:
            return (250, 36)
        elif breakpoint == Breakpoint.MD:
            return (300, 40)
        elif breakpoint == Breakpoint.LG:
            return (350, 44)
        else:  # XL
            return (400, 48)

    def get_responsive_table_row_height(self) -> int:
        """Get recommended table row height for current screen size."""
        breakpoint = self.get_current_breakpoint()

        if breakpoint == Breakpoint.XS:
            return 28
        elif breakpoint == Breakpoint.SM:
            return 32
        elif breakpoint == Breakpoint.MD:
            return 36
        elif breakpoint == Breakpoint.LG:
            return 40
        else:  # XL
            return 44

    def get_responsive_pagination_size(self) -> Tuple[int, int]:
        """Get recommended pagination control size."""
        breakpoint = self.get_current_breakpoint()

        if breakpoint == Breakpoint.XS:
            return (24, 24)  # width, height
        elif breakpoint == Breakpoint.SM:
            return (28, 28)
        elif breakpoint == Breakpoint.MD:
            return (32, 32)
        elif breakpoint == Breakpoint.LG:
            return (36, 36)
        else:  # XL
            return (40, 40)

    def get_responsive_dialog_size(self, base_width: int = 400, base_height: int = 300) -> Tuple[int, int]:
        """Get recommended dialog size for current screen size."""
        breakpoint = self.get_current_breakpoint()
        screen_width = self.get_screen_width()
        screen_height = self.get_screen_height()

        # Calculate as percentage of screen size
        if breakpoint == Breakpoint.XS:
            width = min(base_width, int(screen_width * 0.9))
            height = min(base_height, int(screen_height * 0.8))
        elif breakpoint == Breakpoint.SM:
            width = min(base_width, int(screen_width * 0.8))
            height = min(base_height, int(screen_height * 0.7))
        elif breakpoint == Breakpoint.MD:
            width = min(base_width, int(screen_width * 0.6))
            height = min(base_height, int(screen_height * 0.6))
        elif breakpoint == Breakpoint.LG:
            width = min(base_width, int(screen_width * 0.5))
            height = min(base_height, int(screen_height * 0.5))
        else:  # XL
            width = min(base_width, int(screen_width * 0.4))
            height = min(base_height, int(screen_height * 0.4))

        return (width, height)

    def get_responsive_font_scaling(self) -> float:
        """Get font scaling factor for current screen size."""
        breakpoint = self.get_current_breakpoint()

        if breakpoint == Breakpoint.XS:
            return 0.8
        elif breakpoint == Breakpoint.SM:
            return 0.9
        elif breakpoint == Breakpoint.MD:
            return 1.0
        elif breakpoint == Breakpoint.LG:
            return 1.1
        else:  # XL
            return 1.2

    def get_responsive_animation_speed(self) -> float:
        """Get recommended animation speed for current screen size."""
        breakpoint = self.get_current_breakpoint()

        if breakpoint == Breakpoint.XS:
            return 0.8  # Faster animations for mobile
        elif breakpoint == Breakpoint.SM:
            return 0.9
        elif breakpoint == Breakpoint.MD:
            return 1.0
        elif breakpoint == Breakpoint.LG:
            return 1.1
        else:  # XL
            return 1.2  # Slightly slower for large screens

    def get_responsive_tooltip_delay(self) -> int:
        """Get recommended tooltip delay in milliseconds."""
        breakpoint = self.get_current_breakpoint()

        if breakpoint == Breakpoint.XS:
            return 500  # Shorter delay for mobile
        elif breakpoint == Breakpoint.SM:
            return 700
        elif breakpoint == Breakpoint.MD:
            return 1000
        elif breakpoint == Breakpoint.LG:
            return 1200
        else:  # XL
            return 1500

    def get_responsive_debounce_delay(self) -> int:
        """Get recommended debounce delay for UI events."""
        breakpoint = self.get_current_breakpoint()

        if breakpoint == Breakpoint.XS:
            return 200  # Shorter delay for mobile
        elif breakpoint == Breakpoint.SM:
            return 250
        elif breakpoint == Breakpoint.MD:
            return 300
        elif breakpoint == Breakpoint.LG:
            return 350
        else:  # XL
            return 400

    def get_responsive_cache_size(self) -> int:
        """Get recommended cache size based on device capabilities."""
        breakpoint = self.get_current_breakpoint()
        memory_factor = 1.0

        # Adjust based on screen size as proxy for device capability
        if breakpoint == Breakpoint.XS:
            memory_factor = 0.5
        elif breakpoint == Breakpoint.SM:
            memory_factor = 0.7
        elif breakpoint == Breakpoint.MD:
            memory_factor = 1.0
        elif breakpoint == Breakpoint.LG:
            memory_factor = 1.2
        else:  # XL
            memory_factor = 1.5

        # Base cache size
        base_cache_size = 100
        return int(base_cache_size * memory_factor)

    def get_responsive_batch_size(self) -> int:
        """Get recommended batch size for data operations."""
        breakpoint = self.get_current_breakpoint()

        if breakpoint == Breakpoint.XS:
            return 20  # Smaller batches for mobile
        elif breakpoint == Breakpoint.SM:
            return 30
        elif breakpoint == Breakpoint.MD:
            return 50
        elif breakpoint == Breakpoint.LG:
            return 100
        else:  # XL
            return 200

    def get_responsive_pagination_size(self) -> int:
        """Get recommended pagination size."""
        breakpoint = self.get_current_breakpoint()

        if breakpoint == Breakpoint.XS:
            return 10  # Smaller pages for mobile
        elif breakpoint == Breakpoint.SM:
            return 15
        elif breakpoint == Breakpoint.MD:
            return 25
        elif breakpoint == Breakpoint.LG:
            return 50
        else:  # XL
            return 100

    def get_responsive_performance_settings(self) -> Dict[str, Any]:
        """Get performance settings optimized for current device."""
        breakpoint = self.get_current_breakpoint()

        settings = {
            "animation_enabled": True,
            "transition_speed": 0.3,
            "cache_size": self.get_responsive_cache_size(),
            "batch_size": self.get_responsive_batch_size(),
            "debounce_delay": self.get_responsive_debounce_delay(),
            "prefetch_enabled": True,
            "image_quality": "high",
        }

        if breakpoint == Breakpoint.XS:  # Mobile optimization
            settings.update(
                {
                    "animation_enabled": False,
                    "transition_speed": 0.2,
                    "prefetch_enabled": False,
                    "image_quality": "medium",
                }
            )
        elif breakpoint == Breakpoint.SM:  # Tablet optimization
            settings.update(
                {"animation_enabled": True, "transition_speed": 0.25, "prefetch_enabled": True, "image_quality": "high"}
            )
        elif breakpoint == Breakpoint.MD:  # Small desktop
            settings.update(
                {"animation_enabled": True, "transition_speed": 0.3, "prefetch_enabled": True, "image_quality": "high"}
            )
        elif breakpoint == Breakpoint.LG:  # Desktop
            settings.update(
                {"animation_enabled": True, "transition_speed": 0.35, "prefetch_enabled": True, "image_quality": "high"}
            )
        else:  # XL - Large desktop
            settings.update(
                {
                    "animation_enabled": True,
                    "transition_speed": 0.4,
                    "prefetch_enabled": True,
                    "image_quality": "high",
                    "cache_size": settings["cache_size"] * 2,
                }
            )

        return settings

    def __del__(self):
        """Clean up responsive design resources."""
        self._listeners.clear()


# Singleton instance for easy access
_responsive_manager_instance = None


def get_responsive_manager() -> ResponsiveManager:
    """Get the singleton responsive manager instance."""
    global _responsive_manager_instance
    if _responsive_manager_instance is None:
        _responsive_manager_instance = ResponsiveManager()
    return _responsive_manager_instance


# Convenience functions for common responsive tasks
def get_current_breakpoint() -> Breakpoint:
    """Get current breakpoint."""
    return get_responsive_manager().get_current_breakpoint()


def is_mobile() -> bool:
    """Check if current device is mobile-sized."""
    return get_responsive_manager().is_mobile()


def is_tablet() -> bool:
    """Check if current device is tablet-sized."""
    return get_responsive_manager().is_tablet()


def is_desktop() -> bool:
    """Check if current device is desktop-sized."""
    return get_responsive_manager().is_desktop()


def get_screen_width() -> int:
    """Get current screen width."""
    return get_responsive_manager().get_screen_width()


def get_screen_height() -> int:
    """Get current screen height."""
    return get_responsive_manager().get_screen_height()


def get_responsive_font_size(base_size: int = 14) -> int:
    """Get responsive font size."""
    return get_responsive_manager().get_responsive_font_size(base_size)


def get_responsive_spacing(base_spacing: int = 8) -> int:
    """Get responsive spacing."""
    return get_responsive_manager().get_responsive_spacing(base_spacing)


def get_responsive_layout_recommendations() -> Dict[str, Any]:
    """Get responsive layout recommendations."""
    return get_responsive_manager().get_responsive_layout_recommendations()


# Responsive decorator for functions
def responsive(func: Callable) -> Callable:
    """Decorator to make a function responsive-aware."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        manager = get_responsive_manager()
        screen_info = manager.get_screen_info()

        # Add screen info to kwargs if not already present
        if "screen_info" not in kwargs:
            kwargs["screen_info"] = screen_info
        if "breakpoint" not in kwargs:
            kwargs["breakpoint"] = screen_info.breakpoint

        return func(*args, **kwargs)

    return wrapper


# Responsive context manager
class ResponsiveContext:
    """Context manager for responsive behavior."""

    def __init__(self, breakpoint: Optional[Breakpoint] = None):
        self.breakpoint = breakpoint
        self.manager = get_responsive_manager()

    def __enter__(self):
        if self.breakpoint:
            # Store original and set new breakpoint
            self.original_breakpoint = self.manager.get_current_breakpoint()
            # Note: We can't actually change the physical screen size,
            # but we can override the detected breakpoint for testing
            return self
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass  # Can't restore physical screen size
