#!/usr/bin/env python3
"""
UI Components Module

Reusable UI components for the database browser application.
This module extracts common UI elements that were previously duplicated
or scattered throughout the codebase.

Features:
- Reusable widget components
- Consistent styling
- Standardized behavior
- Accessibility support
"""

from __future__ import annotations

from typing import Callable, Optional

# Try to import Qt components
try:
    from PySide6.QtCore import QSize, Qt, Signal, Slot
    from PySide6.QtGui import QColor, QFont, QIcon, QPalette
    from PySide6.QtWidgets import (
        QAction,
        QCheckBox,
        QComboBox,
        QFrame,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMenu,
        QProgressBar,
        QPushButton,
        QSizePolicy,
        QSpacerItem,
        QToolButton,
        QVBoxLayout,
        QWidget,
    )

    QT_AVAILABLE = True
except ImportError:
    try:
        from PyQt6.QtCore import QSize, Qt, Signal, Slot
        from PyQt6.QtGui import QColor, QFont, QIcon, QPalette
        from PyQt6.QtWidgets import (
            QAction,
            QCheckBox,
            QComboBox,
            QFrame,
            QHBoxLayout,
            QLabel,
            QLineEdit,
            QMenu,
            QProgressBar,
            QPushButton,
            QSizePolicy,
            QSpacerItem,
            QToolButton,
            QVBoxLayout,
            QWidget,
        )

        QT_AVAILABLE = True
    except ImportError:
        QT_AVAILABLE = False

if QT_AVAILABLE:

    class BaseUIComponent(QWidget):
        """Base class for all UI components with common functionality."""

        def __init__(self, parent: Optional[QWidget] = None):
            super().__init__(parent)
            self._setup_base_properties()

        def _setup_base_properties(self):
            """Setup common properties for all UI components."""
            # Enable proper accessibility
            self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
            self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

            # Set reasonable size policies
            self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)

        def set_accessible_name(self, name: str):
            """Set accessible name for screen readers."""
            self.setAccessibleName(name)

        def set_accessible_description(self, description: str):
            """Set accessible description for screen readers."""
            self.setAccessibleDescription(description)

    class SearchInput(QWidget):
        """Enhanced search input component with consistent styling and behavior."""

        search_triggered = Signal(str)
        search_cleared = Signal()
        search_changed = Signal(str)

        def __init__(self, parent: Optional[QWidget] = None):
            super().__init__(parent)
            self._setup_ui()
            self._setup_connections()

        def _setup_ui(self):
            """Setup the search input UI."""
            layout = QHBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(6)

            # Search icon
            self.search_icon = QLabel("🔍")
            self.search_icon.setFixedSize(24, 24)
            self.search_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(self.search_icon)

            # Search input field
            self.input_field = QLineEdit()
            self.input_field.setPlaceholderText("Search...")
            self.input_field.setClearButtonEnabled(True)
            layout.addWidget(self.input_field, 1)  # Take remaining space

            # Apply consistent styling
            self._apply_styling()

        def _apply_styling(self):
            """Apply consistent styling to the search input."""
            self.setStyleSheet("""
                SearchInput {
                    border: 1px solid #e0e0e0;
                    border-radius: 6px;
                    background-color: white;
                    padding: 2px;
                }
                QLineEdit {
                    border: none;
                    padding: 4px 8px;
                    font-size: 14px;
                    min-height: 28px;
                }
                QLineEdit:focus {
                    outline: none;
                }
            """)

        def _setup_connections(self):
            """Setup signal connections."""
            self.input_field.textChanged.connect(self._on_text_changed)
            self.input_field.returnPressed.connect(self._on_return_pressed)

        def _on_text_changed(self, text: str):
            """Handle text changes."""
            self.search_changed.emit(text)

        def _on_return_pressed(self):
            """Handle return key press."""
            if self.input_field.text().strip():
                self.search_triggered.emit(self.input_field.text().strip())

        def set_placeholder_text(self, text: str):
            """Set placeholder text."""
            self.input_field.setPlaceholderText(text)

        def set_text(self, text: str):
            """Set search text."""
            self.input_field.setText(text)

        def get_text(self) -> str:
            """Get current search text."""
            return self.input_field.text()

        def clear(self):
            """Clear the search input."""
            self.input_field.clear()
            self.search_cleared.emit()

        def set_focus(self):
            """Set focus to the search input."""
            self.input_field.setFocus()

    class ActionButton(QPushButton):
        """Consistently styled action button."""

        def __init__(self, text: str = "", icon: str = "", parent: Optional[QWidget] = None):
            super().__init__(parent)
            self._text = text
            self._icon = icon
            self._setup_ui()

        def _setup_ui(self):
            """Setup the action button UI."""
            if self._icon:
                self.setText(f"{self._icon} {self._text}")
            else:
                self.setText(self._text)

            # Apply consistent styling
            self.setStyleSheet("""
                ActionButton {
                    padding: 6px 12px;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    background-color: white;
                    min-height: 28px;
                }
                ActionButton:hover {
                    background-color: #f5f5f5;
                    border-color: #ccc;
                }
                ActionButton:pressed {
                    background-color: #e0e0e0;
                }
                ActionButton:disabled {
                    color: #999;
                    background-color: #f9f9f9;
                    border-color: #eee;
                }
            """)

            # Set reasonable size policy
            self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

            # Enable proper accessibility
            self.setAccessibleName(f"Action: {self._text}")

        def set_action_text(self, text: str):
            """Set button text."""
            self._text = text
            if self._icon:
                self.setText(f"{self._icon} {self._text}")
            else:
                self.setText(self._text)
            self.setAccessibleName(f"Action: {self._text}")

    class ToggleSwitch(QWidget):
        """Modern toggle switch component."""

        toggled = Signal(bool)

        def __init__(self, label: str = "", parent: Optional[QWidget] = None):
            super().__init__(parent)
            self._label = label
            self._checked = False
            self._setup_ui()

        def _setup_ui(self):
            """Setup the toggle switch UI."""
            layout = QHBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(8)

            # Label
            if self._label:
                self.label_widget = QLabel(self._label)
                layout.addWidget(self.label_widget)

            # Toggle button
            self.toggle_button = QPushButton()
            self.toggle_button.setCheckable(True)
            self.toggle_button.setChecked(self._checked)
            self.toggle_button.setFixedSize(44, 22)
            self.toggle_button.clicked.connect(self._on_toggled)
            layout.addWidget(self.toggle_button)

            # Apply styling
            self._apply_styling()

        def _apply_styling(self):
            """Apply styling to the toggle switch."""
            self.toggle_button.setStyleSheet("""
                QPushButton {
                    border: none;
                    border-radius: 11px;
                    background-color: #ccc;
                    padding: 0;
                }
                QPushButton:checked {
                    background-color: #4CAF50;
                }
                QPushButton:hover {
                    background-color: #bbb;
                }
                QPushButton:checked:hover {
                    background-color: #45a049;
                }
            """)

        def _on_toggled(self, checked: bool):
            """Handle toggle state change."""
            self._checked = checked
            self.toggled.emit(checked)

        def is_checked(self) -> bool:
            """Get current toggle state."""
            return self._checked

        def set_checked(self, checked: bool):
            """Set toggle state."""
            if self._checked != checked:
                self._checked = checked
                self.toggle_button.setChecked(checked)
                self.toggled.emit(checked)

        def toggle(self):
            """Toggle the current state."""
            self.set_checked(not self._checked)

    class StatusIndicator(QWidget):
        """Status indicator with icon and text."""

        def __init__(self, parent: Optional[QWidget] = None):
            super().__init__(parent)
            self._setup_ui()

        def _setup_ui(self):
            """Setup the status indicator UI."""
            layout = QHBoxLayout(self)
            layout.setContentsMargins(4, 2, 4, 2)
            layout.setSpacing(6)

            # Status icon
            self.icon_label = QLabel("✓")
            self.icon_label.setFixedSize(16, 16)
            self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(self.icon_label)

            # Status text
            self.text_label = QLabel("Ready")
            self.text_label.setStyleSheet("font-size: 12px;")
            layout.addWidget(self.text_label)

            # Spacer to push content to left
            layout.addStretch()

            # Apply styling
            self.setStyleSheet("""
                StatusIndicator {
                    border: 1px solid #e0e0e0;
                    border-radius: 4px;
                    background-color: #f8f8f8;
                    min-height: 24px;
                }
            """)

        def set_status(self, icon: str, text: str, color: Optional[str] = None):
            """Set status with icon and text."""
            self.icon_label.setText(icon)
            self.text_label.setText(text)

            if color:
                self.setStyleSheet(f"""
                    StatusIndicator {{
                        border: 1px solid {color};
                        border-radius: 4px;
                        background-color: rgba({self._hex_to_rgb(color)}, 0.1);
                        min-height: 24px;
                    }}
                """)

        def _hex_to_rgb(self, hex_color: str) -> str:
            """Convert hex color to RGB string."""
            hex_color = hex_color.lstrip("#")
            if len(hex_color) == 3:
                hex_color = "".join([c * 2 for c in hex_color])
            if len(hex_color) != 6:
                return "0, 0, 0"
            return f"{int(hex_color[0:2], 16)}, {int(hex_color[2:4], 16)}, {int(hex_color[4:6], 16)}"

    class SectionHeader(QWidget):
        """Section header with title and optional controls."""

        def __init__(self, title: str, parent: Optional[QWidget] = None):
            super().__init__(parent)
            self._title = title
            self._setup_ui()

        def _setup_ui(self):
            """Setup the section header UI."""
            layout = QHBoxLayout(self)
            layout.setContentsMargins(8, 4, 8, 4)
            layout.setSpacing(8)

            # Title label
            self.title_label = QLabel(self._title)
            font = QFont()
            font.setBold(True)
            font.setPointSize(11)
            self.title_label.setFont(font)
            self.title_label.setStyleSheet("color: #333;")
            layout.addWidget(self.title_label)

            # Spacer
            layout.addStretch()

            # Apply styling
            self.setStyleSheet("""
                SectionHeader {
                    border-bottom: 1px solid #e0e0e0;
                    background-color: #f8f8f8;
                }
            """)

        def set_title(self, title: str):
            """Set section title."""
            self._title = title
            self.title_label.setText(title)

    class LoadingIndicator(QWidget):
        """Loading indicator with spinner animation."""

        def __init__(self, parent: Optional[QWidget] = None):
            super().__init__(parent)
            self._setup_ui()
            self._setup_animation()

        def _setup_ui(self):
            """Setup the loading indicator UI."""
            layout = QHBoxLayout(self)
            layout.setContentsMargins(8, 4, 8, 4)
            layout.setSpacing(8)

            # Spinner
            self.spinner = QLabel("⏳")
            self.spinner.setFixedSize(16, 16)
            self.spinner.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(self.spinner)

            # Loading text
            self.text_label = QLabel("Loading...")
            self.text_label.setStyleSheet("color: #666; font-size: 12px;")
            layout.addWidget(self.text_label)

            # Spacer
            layout.addStretch()

            # Apply styling
            self.setStyleSheet("""
                LoadingIndicator {
                    background-color: #f8f8f8;
                    border: 1px solid #e0e0e0;
                    border-radius: 4px;
                }
            """)

        def _setup_animation(self):
            """Setup spinner animation."""
            self._animation_timer = None
            self._animation_frame = 0
            self._spinner_chars = ["⏳", "⏴", "⏵", "⏶"]

            # Start animation
            self._start_animation()

        def _start_animation(self):
            """Start the spinner animation."""
            if self._animation_timer is None:
                from PySide6.QtCore import QTimer

                self._animation_timer = QTimer(self)
                self._animation_timer.timeout.connect(self._animate_spinner)
                self._animation_timer.start(100)  # 100ms interval

        def _animate_spinner(self):
            """Animate the spinner."""
            self._animation_frame = (self._animation_frame + 1) % len(self._spinner_chars)
            self.spinner.setText(self._spinner_chars[self._animation_frame])

        def set_text(self, text: str):
            """Set loading text."""
            self.text_label.setText(text)

        def show(self):
            """Show the loading indicator."""
            self._start_animation()
            super().show()

        def hide(self):
            """Hide the loading indicator."""
            if self._animation_timer:
                self._animation_timer.stop()
                self._animation_timer = None
            super().hide()

        def __del__(self):
            """Clean up animation timer."""
            if self._animation_timer:
                self._animation_timer.stop()
                self._animation_timer = None

    class ErrorDisplay(QWidget):
        """Error display component with consistent styling."""

        def __init__(self, parent: Optional[QWidget] = None):
            super().__init__(parent)
            self._setup_ui()

        def _setup_ui(self):
            """Setup the error display UI."""
            layout = QHBoxLayout(self)
            layout.setContentsMargins(8, 4, 8, 4)
            layout.setSpacing(8)

            # Error icon
            self.icon_label = QLabel("⚠️")
            self.icon_label.setFixedSize(16, 16)
            self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.icon_label.setStyleSheet("color: #d32f2f; font-size: 14px;")
            layout.addWidget(self.icon_label)

            # Error text
            self.text_label = QLabel("An error occurred")
            self.text_label.setStyleSheet("color: #d32f2f; font-size: 12px;")
            layout.addWidget(self.text_label)

            # Spacer
            layout.addStretch()

            # Apply styling
            self.setStyleSheet("""
                ErrorDisplay {
                    background-color: #ffebee;
                    border: 1px solid #ef9a9a;
                    border-radius: 4px;
                }
            """)

        def set_error(self, text: str):
            """Set error message."""
            self.text_label.setText(text)

        def clear(self):
            """Clear the error display."""
            self.text_label.setText("")

    class InfoPanel(QWidget):
        """Information panel with consistent styling."""

        def __init__(self, title: str = "", parent: Optional[QWidget] = None):
            super().__init__(parent)
            self._title = title
            self._setup_ui()

        def _setup_ui(self):
            """Setup the info panel UI."""
            layout = QVBoxLayout(self)
            layout.setContentsMargins(8, 8, 8, 8)
            layout.setSpacing(6)

            # Title
            if self._title:
                title_label = QLabel(self._title)
                font = QFont()
                font.setBold(True)
                title_label.setFont(font)
                layout.addWidget(title_label)

            # Content area
            self.content_widget = QWidget()
            self.content_layout = QVBoxLayout(self.content_widget)
            self.content_layout.setContentsMargins(0, 0, 0, 0)
            self.content_layout.setSpacing(4)
            layout.addWidget(self.content_widget, 1)

            # Apply styling
            self.setStyleSheet("""
                InfoPanel {
                    background-color: white;
                    border: 1px solid #e0e0e0;
                    border-radius: 6px;
                }
            """)

        def add_content_widget(self, widget: QWidget):
            """Add a widget to the content area."""
            self.content_layout.addWidget(widget)

        def add_content_layout(self, layout: QLayout):
            """Add a layout to the content area."""
            self.content_layout.addLayout(layout)

        def clear_content(self):
            """Clear all content."""
            # Remove all widgets from content layout
            while self.content_layout.count():
                item = self.content_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

        def set_title(self, title: str):
            """Set panel title."""
            self._title = title
            # Would need to update title label if we stored reference to it

    class EmptyState(QWidget):
        """Empty state display with helpful messaging."""

        def __init__(self, message: str = "No items found", parent: Optional[QWidget] = None):
            super().__init__(parent)
            self._message = message
            self._setup_ui()

        def _setup_ui(self):
            """Setup the empty state UI."""
            layout = QVBoxLayout(self)
            layout.setContentsMargins(24, 24, 24, 24)
            layout.setSpacing(12)

            # Icon
            self.icon_label = QLabel("📂")
            self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            font = QFont()
            font.setPointSize(24)
            self.icon_label.setFont(font)
            layout.addWidget(self.icon_label)

            # Message
            self.message_label = QLabel(self._message)
            self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.message_label.setStyleSheet("color: #666; font-size: 14px;")
            layout.addWidget(self.message_label)

            # Optional action button
            self.action_button = None

            # Apply styling
            self.setStyleSheet("""
                EmptyState {
                    background-color: #f8f8f8;
                    border: 1px dashed #ccc;
                    border-radius: 6px;
                }
            """)

        def set_message(self, message: str):
            """Set empty state message."""
            self._message = message
            self.message_label.setText(message)

        def set_icon(self, icon: str):
            """Set empty state icon."""
            self.icon_label.setText(icon)

        def add_action_button(self, text: str, callback: Callable):
            """Add an action button to the empty state."""
            if self.action_button is None:
                self.action_button = ActionButton(text)
                self.action_button.clicked.connect(callback)
                self.layout().addWidget(self.action_button)

    class PaginationControl(QWidget):
        """Pagination control component."""

        page_changed = Signal(int)

        def __init__(self, parent: Optional[QWidget] = None):
            super().__init__(parent)
            self._current_page = 1
            self._total_pages = 1
            self._items_per_page = 25
            self._total_items = 0
            self._setup_ui()

        def _setup_ui(self):
            """Setup the pagination control UI."""
            layout = QHBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(8)

            # First page button
            self.first_button = QToolButton()
            self.first_button.setText("«")
            self.first_button.setFixedSize(28, 28)
            self.first_button.clicked.connect(self._go_to_first_page)
            layout.addWidget(self.first_button)

            # Previous page button
            self.prev_button = QToolButton()
            self.prev_button.setText("‹")
            self.prev_button.setFixedSize(28, 28)
            self.prev_button.clicked.connect(self._go_to_prev_page)
            layout.addWidget(self.prev_button)

            # Page info
            self.page_info = QLabel("Page 1 of 1")
            self.page_info.setStyleSheet("font-size: 12px; padding: 0 8px;")
            layout.addWidget(self.page_info)

            # Next page button
            self.next_button = QToolButton()
            self.next_button.setText("›")
            self.next_button.setFixedSize(28, 28)
            self.next_button.clicked.connect(self._go_to_next_page)
            layout.addWidget(self.next_button)

            # Last page button
            self.last_button = QToolButton()
            self.last_button.setText("»")
            self.last_button.setFixedSize(28, 28)
            self.last_button.clicked.connect(self._go_to_last_page)
            layout.addWidget(self.last_button)

            # Items per page selector
            self.items_per_page_combo = QComboBox()
            self.items_per_page_combo.addItems(["25", "50", "100", "200"])
            self.items_per_page_combo.setCurrentText("25")
            self.items_per_page_combo.currentTextChanged.connect(self._on_items_per_page_changed)
            layout.addWidget(self.items_per_page_combo)

            # Apply styling
            self.setStyleSheet("""
                PaginationControl {
                    background-color: white;
                    border: 1px solid #e0e0e0;
                    border-radius: 4px;
                }
                QToolButton {
                    border: 1px solid #e0e0e0;
                    border-radius: 4px;
                    background-color: white;
                }
                QToolButton:hover {
                    background-color: #f5f5f5;
                }
                QToolButton:disabled {
                    color: #999;
                    background-color: #f9f9f9;
                }
            """)

            # Update button states
            self._update_button_states()

        def _update_button_states(self):
            """Update button enabled/disabled states."""
            self.first_button.setEnabled(self._current_page > 1)
            self.prev_button.setEnabled(self._current_page > 1)
            self.next_button.setEnabled(self._current_page < self._total_pages)
            self.last_button.setEnabled(self._current_page < self._total_pages)

        def _go_to_first_page(self):
            """Go to first page."""
            if self._current_page > 1:
                self._current_page = 1
                self._update_display()
                self.page_changed.emit(self._current_page)

        def _go_to_prev_page(self):
            """Go to previous page."""
            if self._current_page > 1:
                self._current_page -= 1
                self._update_display()
                self.page_changed.emit(self._current_page)

        def _go_to_next_page(self):
            """Go to next page."""
            if self._current_page < self._total_pages:
                self._current_page += 1
                self._update_display()
                self.page_changed.emit(self._current_page)

        def _go_to_last_page(self):
            """Go to last page."""
            if self._current_page < self._total_pages:
                self._current_page = self._total_pages
                self._update_display()
                self.page_changed.emit(self._current_page)

        def _on_items_per_page_changed(self, text: str):
            """Handle items per page change."""
            try:
                new_per_page = int(text)
                if new_per_page != self._items_per_page:
                    self._items_per_page = new_per_page
                    # Recalculate total pages and go to first page
                    self._calculate_total_pages()
                    self._current_page = 1
                    self._update_display()
                    self.page_changed.emit(self._current_page)
            except ValueError:
                pass

        def _calculate_total_pages(self):
            """Calculate total number of pages."""
            if self._total_items == 0:
                self._total_pages = 1
            else:
                self._total_pages = max(1, (self._total_items + self._items_per_page - 1) // self._items_per_page)

        def _update_display(self):
            """Update the display with current page info."""
            self.page_info.setText(f"Page {self._current_page} of {self._total_pages}")
            self._update_button_states()

        def set_total_items(self, total_items: int):
            """Set total number of items."""
            self._total_items = max(0, total_items)
            self._calculate_total_pages()
            self._update_display()

        def set_items_per_page(self, items_per_page: int):
            """Set items per page."""
            if items_per_page != self._items_per_page:
                self._items_per_page = max(1, items_per_page)
                self.items_per_page_combo.setCurrentText(str(self._items_per_page))
                self._calculate_total_pages()
                self._update_display()

        def get_current_page(self) -> int:
            """Get current page number."""
            return self._current_page

        def get_items_per_page(self) -> int:
            """Get items per page."""
            return self._items_per_page

        def get_page_range(self) -> Tuple[int, int]:
            """Get the range of items for the current page (start, end)."""
            start = (self._current_page - 1) * self._items_per_page
            end = start + self._items_per_page
            return start, min(end, self._total_items)

else:
    # Provide dummy implementations when Qt is not available
    class BaseUIComponent:
        pass

    class SearchInput:
        pass

    class ActionButton:
        pass

    class ToggleSwitch:
        pass

    class StatusIndicator:
        pass

    class SectionHeader:
        pass

    class LoadingIndicator:
        pass

    class ErrorDisplay:
        pass

    class InfoPanel:
        pass

    class EmptyState:
        pass

    class PaginationControl:
        pass
