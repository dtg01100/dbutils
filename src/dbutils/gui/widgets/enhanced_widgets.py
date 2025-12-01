"""
Custom Qt widgets for enhanced database browser interface.
"""

try:
    from PySide6.QtWidgets import (
        QWidget,
        QVBoxLayout,
        QHBoxLayout,
        QLabel,
        QPushButton,
        QFrame,
        QSizePolicy,
        QGraphicsOpacityEffect,
    )
    from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect
    from PySide6.QtGui import QFont, QColor, QPalette, QPainter, QBrush, QPen

    QT_AVAILABLE = True
except ImportError:
    try:
        from PyQt6.QtWidgets import (
            QWidget,
            QVBoxLayout,
            QHBoxLayout,
            QLabel,
            QPushButton,
            QFrame,
            QSizePolicy,
            QGraphicsOpacityEffect,
        )
        from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect
        from PyQt6.QtGui import QFont, QColor, QPalette, QPainter, QBrush, QPen

        QT_AVAILABLE = True
    except ImportError:
        QT_AVAILABLE = False


class StatusIndicator(QWidget):
    """Animated status indicator for search operations."""

    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.setup_animation()

    def setup_ui(self):
        """Setup the indicator UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Status icon
        self.status_label = QLabel("🔍")
        self.status_label.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(16)
        self.status_label.setFont(font)
        layout.addWidget(self.status_label)

        # Status text
        self.text_label = QLabel("Ready")
        layout.addWidget(self.text_label)

        # Progress indicator
        self.progress_indicator = QWidget()
        self.progress_indicator.setFixedSize(16, 16)
        self.progress_indicator.setStyleSheet("""
            QWidget {
                border: 2px solid #ccc;
                border-radius: 8px;
                background-color: #f0f0f0;
            }
        """)
        layout.addWidget(self.progress_indicator)

        layout.addStretch()

    def setup_animation(self):
        """Setup the spinning animation."""
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.animate_progress)
        self.animation_angle = 0

    def set_searching(self, is_searching: bool):
        """Set the searching state."""
        if is_searching:
            self.status_label.setText("🔄")
            self.text_label.setText("Searching...")
            self.animation_timer.start(50)  # 20 FPS
        else:
            self.status_label.setText("✅")
            self.text_label.setText("Ready")
            self.animation_timer.stop()
            self.reset_progress()

    def animate_progress(self):
        """Animate the progress indicator."""
        self.animation_angle = (self.animation_angle + 10) % 360
        self.update_progress_style()

    def update_progress_style(self):
        """Update progress indicator style with rotation."""
        color = QColor(52, 152, 219)  # Nice blue
        style = f"""
            QWidget {{
                border: 2px solid {color.name()};
                border-radius: 8px;
                background-color: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 {color.name()}, stop: 1 {color.lighter(150).name()}
                );
            }}
        """
        self.progress_indicator.setStyleSheet(style)

    def reset_progress(self):
        """Reset progress indicator."""
        self.progress_indicator.setStyleSheet("""
            QWidget {
                border: 2px solid #ccc;
                border-radius: 8px;
                background-color: #f0f0f0;
            }
        """)


class EnhancedTableItem(QWidget):
    """Enhanced table item with visual indicators."""

    def __init__(self, table_info, match_type="normal"):
        super().__init__()
        self.table_info = table_info
        self.match_type = match_type
        self.setup_ui()

    def setup_ui(self):
        """Setup the enhanced table item UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        # Table icon based on match type
        icon_label = QLabel()
        if self.match_type == "exact":
            icon_label.setText("🎯")
        elif self.match_type == "prefix":
            icon_label.setText("📍")
        elif self.match_type == "fuzzy":
            icon_label.setText("🔍")
        else:
            icon_label.setText("📋")

        icon_label.setFixedSize(24, 24)
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)

        # Table name
        name_label = QLabel(self.table_info.name)
        font = QFont()
        font.setBold(True)
        font.setPointSize(10)
        name_label.setFont(font)
        layout.addWidget(name_label)

        # Schema label
        schema_label = QLabel(f"[{self.table_info.schema}]")
        schema_label.setStyleSheet("color: #666; font-size: 9px;")
        layout.addWidget(schema_label)

        layout.addStretch()

        # Column count
        # TODO: Get actual column count
        columns_label = QLabel("📊")
        columns_label.setStyleSheet("color: #888; font-size: 12px;")
        layout.addWidget(columns_label)

        # Set hover effect
        self.setStyleSheet("""
            EnhancedTableItem {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                background-color: white;
                margin: 2px;
            }
            EnhancedTableItem:hover {
                border: 1px solid #3498db;
                background-color: #f8f9fa;
            }
        """)

    def enterEvent(self, event):
        """Handle mouse enter for hover effect."""
        self.setStyleSheet("""
            EnhancedTableItem {
                border: 1px solid #3498db;
                background-color: #f8f9fa;
                border-radius: 4px;
                margin: 2px;
            }
        """)

    def leaveEvent(self, event):
        """Handle mouse leave for hover effect."""
        self.setStyleSheet("""
            EnhancedTableItem {
                border: 1px solid #e0e0e0;
                background-color: white;
                border-radius: 4px;
                margin: 2px;
            }
        """)


class SearchHighlightWidget(QWidget):
    """Widget with search highlighting capabilities."""

    def __init__(self):
        super().__init__()
        self.search_text = ""
        self.setup_ui()

    def setup_ui(self):
        """Setup the search highlight widget."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Search input with enhanced styling
        if QT_AVAILABLE:
            from PySide6.QtWidgets import QLineEdit

            self.search_input = QLineEdit()
        else:
            # Fallback for testing without Qt
            class QLineEdit:
                def __init__(self):
                    pass

                def setPlaceholderText(self, text):
                    pass

                def setStyleSheet(self, style):
                    pass

            self.search_input = QLineEdit()

        self.search_input.setPlaceholderText("🔍 Search tables, columns, or SQL...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                padding: 8px 12px;
                border: 2px solid #ddd;
                border-radius: 6px;
                font-size: 14px;
                background-color: white;
            }
            QLineEdit:focus {
                border: 2px solid #3498db;
                background-color: #f8f9fa;
            }
        """)
        layout.addWidget(self.search_input)

        # Search suggestions (placeholder for future enhancement)
        self.suggestions_widget = QWidget()
        self.suggestions_widget.setVisible(False)
        layout.addWidget(self.suggestions_widget)

    def set_search_text(self, text: str):
        """Set search text and highlight matches."""
        self.search_text = text.lower()
        # TODO: Implement highlighting logic

    def clear_search(self):
        """Clear the search."""
        self.search_input.clear()
        self.search_text = ""


class ProgressBar(QWidget):
    """Custom progress bar with enhanced styling."""

    def __init__(self):
        super().__init__()
        self.value = 0
        self.maximum = 100
        self.setup_ui()

    def setup_ui(self):
        """Setup the progress bar UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Progress container
        self.progress_container = QWidget()
        progress_layout = QVBoxLayout(self.progress_container)
        progress_layout.setContentsMargins(0, 0, 0, 0)

        # Progress bar
        self.progress_bar = QWidget()
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setStyleSheet("""
            QWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: #f0f0f0;
            }
        """)
        progress_layout.addWidget(self.progress_bar)

        # Progress text
        self.progress_text = QLabel("0%")
        self.progress_text.setAlignment(Qt.AlignCenter)
        self.progress_text.setStyleSheet("color: #666; font-size: 11px;")
        progress_layout.addWidget(self.progress_text)

        layout.addWidget(self.progress_container)

    def set_value(self, value: int):
        """Set the progress value."""
        self.value = max(0, min(value, self.maximum))
        self.update_progress()

    def set_maximum(self, maximum: int):
        """Set the maximum value."""
        self.maximum = maximum
        self.update_progress()

    def update_progress(self):
        """Update the progress display."""
        percentage = (self.value / self.maximum) * 100 if self.maximum > 0 else 0

        # Update progress bar fill
        fill_percentage = percentage / 100
        self.progress_bar.setStyleSheet(f"""
            QWidget {{
                border: 1px solid #ddd;
                border-radius: 4px;
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #3498db, stop: {fill_percentage} #3498db,
                    stop: {fill_percentage + 0.001} #f0f0f0, stop: 1 #f0f0f0
                );
            }}
        """)

        # Update text
        self.progress_text.setText(f"{percentage:.0f}%")


class CollapsiblePanel(QWidget):
    """Collapsible panel widget."""

    def __init__(self, title: str, collapsed: bool = False):
        super().__init__()
        self.title = title
        self.is_collapsed = collapsed
        self.setup_ui()

    def setup_ui(self):
        """Setup the collapsible panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header with toggle button
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(8, 4, 8, 4)

        self.toggle_button = QPushButton(f"{'▶' if self.is_collapsed else '▼'} {self.title}")
        self.toggle_button.setStyleSheet("""
            QPushButton {
                border: none;
                background-color: transparent;
                text-align: left;
                padding: 4px 8px;
                font-weight: bold;
                color: #333;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
                border-radius: 4px;
            }
        """)
        self.toggle_button.clicked.connect(self.toggle_collapse)
        header_layout.addWidget(self.toggle_button)

        header_layout.addStretch()
        layout.addWidget(header_widget)

        # Content area
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(8, 4, 8, 4)

        layout.addWidget(self.content_widget)

        # Set initial state
        self.update_collapse_state()

    def toggle_collapse(self):
        """Toggle the collapsed state."""
        self.is_collapsed = not self.is_collapsed
        self.update_collapse_state()

    def update_collapse_state(self):
        """Update the visual state based on collapse."""
        # Update button text
        self.toggle_button.setText(f"{'▶' if self.is_collapsed else '▼'} {self.title}")

        # Update content visibility
        self.content_widget.setVisible(not self.is_collapsed)

    def add_widget(self, widget: QWidget):
        """Add a widget to the content area."""
        self.content_layout.addWidget(widget)

    def add_layout(self, layout):
        """Add a layout to the content area."""
        self.content_layout.addLayout(layout)
