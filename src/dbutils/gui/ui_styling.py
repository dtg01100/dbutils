#!/usr/bin/env python3
"""
UI Styling System

Centralized styling system for the database browser application.
This module addresses the visual consistency issues by providing:
- Consistent color schemes
- Standardized typography
- Unified spacing and layout
- Theme support (light/dark modes)
- CSS generation utilities

Features:
- Theme management with light/dark mode support
- Consistent color palette
- Standardized component styling
- Dynamic theme switching
- Accessibility-aware color schemes
"""

from __future__ import annotations
import json
import os
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum, auto
from dataclasses import dataclass
from pathlib import Path

# Try to import Qt components for theme detection
try:
    from PySide6.QtCore import QSettings
    from PySide6.QtGui import QColor, QPalette
    QT_AVAILABLE = True
except ImportError:
    try:
        from PyQt6.QtCore import QSettings
        from PyQt6.QtGui import QColor, QPalette
        QT_AVAILABLE = True
    except ImportError:
        QT_AVAILABLE = False

class ThemeMode(Enum):
    """Supported theme modes."""
    LIGHT = auto()
    DARK = auto()
    SYSTEM = auto()

class ColorRole(Enum):
    """Color roles for theming."""
    PRIMARY = auto()
    SECONDARY = auto()
    SUCCESS = auto()
    WARNING = auto()
    ERROR = auto()
    INFO = auto()
    BACKGROUND = auto()
    SURFACE = auto()
    TEXT_PRIMARY = auto()
    TEXT_SECONDARY = auto()
    BORDER = auto()
    ACCENT = auto()

@dataclass
class ColorPalette:
    """Color palette for a theme."""
    primary: str = "#3498db"
    secondary: str = "#2ecc71"
    success: str = "#27ae60"
    warning: str = "#f39c12"
    error: str = "#e74c3c"
    info: str = "#3498db"
    background: str = "#ffffff"
    surface: str = "#f8f9fa"
    text_primary: str = "#333333"
    text_secondary: str = "#666666"
    border: str = "#e0e0e0"
    accent: str = "#9b59b6"

@dataclass
class Typography:
    """Typography settings."""
    font_family: str = "'Segoe UI', 'Helvetica Neue', Helvetica, Arial, sans-serif"
    base_size: int = 13
    heading_sizes: Dict[str, int] = None
    line_height: float = 1.5

    def __post_init__(self):
        if self.heading_sizes is None:
            self.heading_sizes = {
                'h1': 24,
                'h2': 20,
                'h3': 18,
                'h4': 16,
                'h5': 14,
                'h6': 12
            }

@dataclass
class Spacing:
    """Spacing system for consistent layouts."""
    base_unit: int = 8
    scale: List[int] = None

    def __post_init__(self):
        if self.scale is None:
            self.scale = [self.base_unit * i for i in range(1, 7)]

    def get(self, level: int) -> int:
        """Get spacing value for a level (1-6)."""
        if 1 <= level <= 6:
            return self.scale[level - 1]
        return self.base_unit

@dataclass
class Theme:
    """Complete UI theme definition."""
    name: str = "Default"
    mode: ThemeMode = ThemeMode.LIGHT
    palette: ColorPalette = None
    typography: Typography = None
    spacing: Spacing = None
    border_radius: int = 4
    shadow_level: int = 1

    def __post_init__(self):
        if self.palette is None:
            self.palette = ColorPalette()
        if self.typography is None:
            self.typography = Typography()
        if self.spacing is None:
            self.spacing = Spacing()

class UIStyling:
    """Centralized styling system for the database browser."""

    def __init__(self):
        self._themes: Dict[str, Theme] = {}
        self._current_theme_name: str = "default"
        self._initialized = False

        # Initialize with default themes
        self._initialize_default_themes()

    def _initialize_default_themes(self):
        """Initialize default light and dark themes."""
        # Light theme
        light_theme = Theme(
            name="light",
            mode=ThemeMode.LIGHT,
            palette=ColorPalette(
                background="#ffffff",
                surface="#f8f9fa",
                text_primary="#333333",
                text_secondary="#666666",
                border="#e0e0e0"
            )
        )

        # Dark theme
        dark_theme = Theme(
            name="dark",
            mode=ThemeMode.DARK,
            palette=ColorPalette(
                primary="#3a86ff",
                secondary="#8338ec",
                success="#32a852",
                warning="#ffb800",
                error="#ff5630",
                info="#00b8d9",
                background="#1a1a1a",
                surface="#2d2d2d",
                text_primary="#f0f0f0",
                text_secondary="#b0b0b0",
                border="#3a3a3a",
                accent="#ff8c00"
            ),
            typography=Typography(
                font_family="'Segoe UI', 'Helvetica Neue', Helvetica, Arial, sans-serif",
                base_size=13,
                heading_sizes={
                    'h1': 24, 'h2': 20, 'h3': 18, 'h4': 16, 'h5': 14, 'h6': 12
                }
            )
        )

        self._themes = {
            "light": light_theme,
            "dark": dark_theme
        }

        self._current_theme_name = "light"
        self._initialized = True

    def add_theme(self, theme: Theme):
        """Add a custom theme."""
        self._themes[theme.name] = theme

    def set_theme(self, theme_name: str) -> bool:
        """Set the current theme by name."""
        if theme_name in self._themes:
            self._current_theme_name = theme_name
            return True
        return False

    def get_current_theme(self) -> Theme:
        """Get the current theme."""
        return self._themes.get(self._current_theme_name)

    def get_theme_names(self) -> List[str]:
        """Get list of available theme names."""
        return list(self._themes.keys())

    def toggle_theme(self) -> str:
        """Toggle between light and dark themes."""
        current = self._current_theme_name
        if current == "light":
            self.set_theme("dark")
        else:
            self.set_theme("light")
        return self._current_theme_name

    def get_color(self, role: ColorRole) -> str:
        """Get color for a specific role."""
        theme = self.get_current_theme()
        if theme:
            if role == ColorRole.PRIMARY:
                return theme.palette.primary
            elif role == ColorRole.SECONDARY:
                return theme.palette.secondary
            elif role == ColorRole.SUCCESS:
                return theme.palette.success
            elif role == ColorRole.WARNING:
                return theme.palette.warning
            elif role == ColorRole.ERROR:
                return theme.palette.error
            elif role == ColorRole.INFO:
                return theme.palette.info
            elif role == ColorRole.BACKGROUND:
                return theme.palette.background
            elif role == ColorRole.SURFACE:
                return theme.palette.surface
            elif role == ColorRole.TEXT_PRIMARY:
                return theme.palette.text_primary
            elif role == ColorRole.TEXT_SECONDARY:
                return theme.palette.text_secondary
            elif role == ColorRole.BORDER:
                return theme.palette.border
            elif role == ColorRole.ACCENT:
                return theme.palette.accent
        return "#3498db"  # Fallback color

    def generate_css(self, component_type: str = "global") -> str:
        """Generate CSS for a specific component type or global styles."""
        theme = self.get_current_theme()
        if not theme:
            return ""

        palette = theme.palette
        spacing = theme.spacing
        typography = theme.typography

        # Base CSS that applies to all components
        base_css = f"""
        /* Base Theme Colors */
        :root {{
            --color-primary: {palette.primary};
            --color-secondary: {palette.secondary};
            --color-success: {palette.success};
            --color-warning: {palette.warning};
            --color-error: {palette.error};
            --color-info: {palette.info};
            --color-background: {palette.background};
            --color-surface: {palette.surface};
            --color-text-primary: {palette.text_primary};
            --color-text-secondary: {palette.text_secondary};
            --color-border: {palette.border};
            --color-accent: {palette.accent};

            --font-family: {typography.font_family};
            --font-size-base: {typography.base_size}px;
            --line-height: {typography.line_height};

            --spacing-base: {spacing.base_unit}px;
            --border-radius: {theme.border_radius}px;

            --shadow-level: {theme.shadow_level};
        }}

        /* Base Typography */
        * {{
            font-family: var(--font-family);
            font-size: var(--font-size-base);
            line-height: var(--line-height);
        }}

        /* Common Component Styles */
        QWidget {{
            background-color: var(--color-background);
            color: var(--color-text-primary);
        }}

        QLabel {{
            color: var(--color-text-primary);
        }}

        QLineEdit, QComboBox, QSpinBox {{
            border: 1px solid var(--color-border);
            border-radius: var(--border-radius);
            padding: calc(var(--spacing-base) * 0.5);
            background-color: var(--color-surface);
            color: var(--color-text-primary);
            min-height: 28px;
        }}

        QPushButton {{
            border: 1px solid var(--color-border);
            border-radius: var(--border-radius);
            padding: calc(var(--spacing-base) * 0.5) calc(var(--spacing-base));
            background-color: var(--color-surface);
            color: var(--color-text-primary);
            min-height: 28px;
        }}

        QPushButton:hover {{
            background-color: rgba(0, 0, 0, 0.05);
            border-color: var(--color-primary);
        }}

        QPushButton:pressed {{
            background-color: rgba(0, 0, 0, 0.1);
        }}

        QPushButton:disabled {{
            color: var(--color-text-secondary);
            background-color: var(--color-surface);
            border-color: var(--color-border);
            opacity: 0.6;
        }}

        /* Table Styles */
        QTableView, QTreeView, QListView {{
            border: 1px solid var(--color-border);
            border-radius: var(--border-radius);
            background-color: var(--color-surface);
            alternate-background-color: rgba(0, 0, 0, 0.02);
        }}

        QHeaderView::section {{
            background-color: var(--color-surface);
            border: none;
            border-bottom: 1px solid var(--color-border);
            padding: calc(var(--spacing-base) * 0.75);
            min-height: 32px;
        }}

        /* Scrollbar Styles */
        QScrollBar:vertical, QScrollBar:horizontal {{
            border: none;
            background: var(--color-surface);
            width: 10px;
            margin: 0;
        }}

        QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
            background: var(--color-border);
            min-height: 20px;
            border-radius: calc(var(--border-radius) / 2);
        }}

        QScrollBar::add-line, QScrollBar::sub-line {{
            background: none;
            border: none;
        }}

        /* Progress Bar Styles */
        QProgressBar {{
            border: 1px solid var(--color-border);
            border-radius: var(--border-radius);
            background-color: var(--color-surface);
            text-align: center;
        }}

        QProgressBar::chunk {{
            background-color: var(--color-primary);
            border-radius: calc(var(--border-radius) - 1);
        }}

        /* Checkbox and Radio Button Styles */
        QCheckBox, QRadioButton {{
            spacing: 8px;
        }}

        QCheckBox::indicator, QRadioButton::indicator {{
            width: 16px;
            height: 16px;
        }}

        QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
            background-color: var(--color-primary);
            border: 1px solid var(--color-primary);
        }}

        /* Tab Widget Styles */
        QTabWidget::pane {{
            border: 1px solid var(--color-border);
            border-radius: var(--border-radius);
            background-color: var(--color-surface);
        }}

        QTabBar::tab {{
            padding: calc(var(--spacing-base)) calc(var(--spacing-base) * 1.5);
            border: none;
            background-color: transparent;
            color: var(--color-text-secondary);
        }}

        QTabBar::tab:selected, QTabBar::tab:hover {{
            color: var(--color-text-primary);
            background-color: var(--color-surface);
        }}

        /* ToolTip Styles */
        QToolTip {{
            background-color: var(--color-surface);
            color: var(--color-text-primary);
            border: 1px solid var(--color-border);
            border-radius: var(--border-radius);
            padding: calc(var(--spacing-base) * 0.75);
            opacity: 250;
        }}
        """

        # Component-specific CSS
        if component_type == "search":
            return base_css + self._generate_search_css()
        elif component_type == "table":
            return base_css + self._generate_table_css()
        elif component_type == "form":
            return base_css + self._generate_form_css()
        elif component_type == "dialog":
            return base_css + self._generate_dialog_css()
        else:
            return base_css

    def _generate_search_css(self) -> str:
        """Generate search-specific CSS."""
        theme = self.get_current_theme()
        if not theme:
            return ""

        return f"""
        /* Search Component Styles */
        .search-container {{
            border: 1px solid var(--color-border);
            border-radius: var(--border-radius);
            background-color: var(--color-surface);
            padding: var(--spacing-base);
        }}

        .search-input {{
            border: 1px solid var(--color-border);
            border-radius: calc(var(--border-radius) * 2);
            padding: calc(var(--spacing-base) * 0.75);
            background-color: white;
            min-height: 36px;
        }}

        .search-icon {{
            color: var(--color-text-secondary);
            padding: 0 calc(var(--spacing-base) * 0.5);
        }}

        .search-results {{
            background-color: var(--color-surface);
            border: 1px solid var(--color-border);
            border-radius: var(--border-radius);
        }}

        .search-result-item {{
            padding: calc(var(--spacing-base) * 0.75);
            border-bottom: 1px solid var(--color-border);
        }}

        .search-result-item:hover {{
            background-color: rgba(0, 0, 0, 0.03);
        }}

        .search-highlight {{
            background-color: rgba(255, 215, 0, 0.3);
            border-radius: 2px;
            padding: 0 2px;
        }}
        """

    def _generate_table_css(self) -> str:
        """Generate table-specific CSS."""
        theme = self.get_current_theme()
        if not theme:
            return ""

        return f"""
        /* Table Component Styles */
        .table-container {{
            border: 1px solid var(--color-border);
            border-radius: var(--border-radius);
            background-color: var(--color-surface);
        }}

        .table-header {{
            background-color: var(--color-surface);
            border-bottom: 1px solid var(--color-border);
            font-weight: 600;
            padding: calc(var(--spacing-base) * 0.75);
        }}

        .table-row {{
            border-bottom: 1px solid var(--color-border);
            padding: calc(var(--spacing-base) * 0.75);
        }}

        .table-row:hover {{
            background-color: rgba(0, 0, 0, 0.03);
        }}

        .table-row.selected {{
            background-color: rgba(var(--color-primary), 0.1);
            border-left: 3px solid var(--color-primary);
        }}

        .table-cell {{
            padding: calc(var(--spacing-base) * 0.5);
        }}

        .table-pagination {{
            background-color: var(--color-surface);
            border-top: 1px solid var(--color-border);
            padding: calc(var(--spacing-base) * 0.75);
        }}
        """

    def _generate_form_css(self) -> str:
        """Generate form-specific CSS."""
        theme = self.get_current_theme()
        if not theme:
            return ""

        return f"""
        /* Form Component Styles */
        .form-container {{
            background-color: var(--color-surface);
            border: 1px solid var(--color-border);
            border-radius: var(--border-radius);
            padding: var(--spacing-base);
        }}

        .form-group {{
            margin-bottom: calc(var(--spacing-base) * 1.5);
        }}

        .form-label {{
            display: block;
            margin-bottom: calc(var(--spacing-base) * 0.5);
            font-weight: 500;
            color: var(--color-text-primary);
        }}

        .form-control {{
            border: 1px solid var(--color-border);
            border-radius: var(--border-radius);
            padding: calc(var(--spacing-base) * 0.75);
            background-color: white;
            min-height: 32px;
        }}

        .form-control:focus {{
            border-color: var(--color-primary);
            outline: none;
            box-shadow: 0 0 0 2px rgba(var(--color-primary), 0.1);
        }}

        .form-control.error {{
            border-color: var(--color-error);
        }}

        .form-help-text {{
            color: var(--color-text-secondary);
            font-size: 12px;
            margin-top: calc(var(--spacing-base) * 0.5);
        }}

        .form-actions {{
            display: flex;
            justify-content: flex-end;
            gap: var(--spacing-base);
            margin-top: calc(var(--spacing-base) * 1.5);
            padding-top: calc(var(--spacing-base) * 1.5);
            border-top: 1px solid var(--color-border);
        }}
        """

    def _generate_dialog_css(self) -> str:
        """Generate dialog-specific CSS."""
        theme = self.get_current_theme()
        if not theme:
            return ""

        return f"""
        /* Dialog Component Styles */
        .dialog-container {{
            background-color: var(--color-background);
            border: 1px solid var(--color-border);
            border-radius: calc(var(--border-radius) * 1.5);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        }}

        .dialog-header {{
            background-color: var(--color-surface);
            border-bottom: 1px solid var(--color-border);
            padding: var(--spacing-base);
            border-radius: calc(var(--border-radius) * 1.5) calc(var(--border-radius) * 1.5) 0 0;
        }}

        .dialog-title {{
            font-size: {self.get_current_theme().typography.heading_sizes['h3']}px;
            font-weight: 600;
            color: var(--color-text-primary);
            margin: 0;
        }}

        .dialog-content {{
            padding: var(--spacing-base);
            background-color: var(--color-background);
        }}

        .dialog-footer {{
            background-color: var(--color-surface);
            border-top: 1px solid var(--color-border);
            padding: calc(var(--spacing-base) * 0.75);
            border-radius: 0 0 calc(var(--border-radius) * 1.5) calc(var(--border-radius) * 1.5);
        }}

        .dialog-actions {{
            display: flex;
            justify-content: flex-end;
            gap: var(--spacing-base);
        }}
        """

    def get_typography_css(self, element: str = "body") -> str:
        """Get CSS for a specific typography element."""
        theme = self.get_current_theme()
        if not theme:
            return ""

        if element == "body":
            return f"""
            font-family: {theme.typography.font_family};
            font-size: {theme.typography.base_size}px;
            line-height: {theme.typography.line_height};
            color: var(--color-text-primary);
            """
        elif element in theme.typography.heading_sizes:
            size = theme.typography.heading_sizes[element]
            return f"""
            font-family: {theme.typography.font_family};
            font-size: {size}px;
            font-weight: 600;
            line-height: {theme.typography.line_height};
            color: var(--color-text-primary);
            margin: 0 0 calc(var(--spacing-base) * 0.75) 0;
            """
        else:
            return ""

    def get_spacing_css(self, level: int = 1) -> str:
        """Get CSS for spacing at a specific level."""
        theme = self.get_current_theme()
        if not theme:
            return "0"

        spacing = theme.spacing.get(level)
        return f"{spacing}px"

    def apply_theme_to_widget(self, widget, theme_name: Optional[str] = None):
        """Apply theme to a Qt widget."""
        if not QT_AVAILABLE:
            return False

        if theme_name:
            self.set_theme(theme_name)

        theme = self.get_current_theme()
        if not theme:
            return False

        try:
            # Apply theme colors to widget palette
            palette = widget.palette()

            # Window colors
            palette.setColor(QPalette.ColorRole.Window, QColor(theme.palette.background))
            palette.setColor(QPalette.ColorRole.WindowText, QColor(theme.palette.text_primary))

            # Base colors
            palette.setColor(QPalette.ColorRole.Base, QColor(theme.palette.surface))
            palette.setColor(QPalette.ColorRole.Text, QColor(theme.palette.text_primary))

            # Button colors
            palette.setColor(QPalette.ColorRole.Button, QColor(theme.palette.surface))
            palette.setColor(QPalette.ColorRole.ButtonText, QColor(theme.palette.text_primary))

            # Highlight colors
            palette.setColor(QPalette.ColorRole.Highlight, QColor(theme.palette.primary))
            palette.setColor(QPalette.ColorRole.HighlightedText, QColor("white"))

            widget.setPalette(palette)

            # Apply stylesheet
            widget.setStyleSheet(self.generate_css())

            return True
        except Exception:
            return False

    def save_theme(self, theme: Theme, file_path: Optional[str] = None) -> bool:
        """Save a theme to a file."""
        if file_path is None:
            # Use default location
            cache_dir = Path.home() / ".cache" / "dbutils" / "themes"
            cache_dir.mkdir(parents=True, exist_ok=True)
            file_path = cache_dir / f"{theme.name}.json"

        try:
            theme_data = {
                'name': theme.name,
                'mode': theme.mode.name,
                'palette': {
                    'primary': theme.palette.primary,
                    'secondary': theme.palette.secondary,
                    'success': theme.palette.success,
                    'warning': theme.palette.warning,
                    'error': theme.palette.error,
                    'info': theme.palette.info,
                    'background': theme.palette.background,
                    'surface': theme.palette.surface,
                    'text_primary': theme.palette.text_primary,
                    'text_secondary': theme.palette.text_secondary,
                    'border': theme.palette.border,
                    'accent': theme.palette.accent
                },
                'typography': {
                    'font_family': theme.typography.font_family,
                    'base_size': theme.typography.base_size,
                    'heading_sizes': theme.typography.heading_sizes,
                    'line_height': theme.typography.line_height
                },
                'spacing': {
                    'base_unit': theme.spacing.base_unit,
                    'scale': theme.spacing.scale
                },
                'border_radius': theme.border_radius,
                'shadow_level': theme.shadow_level
            }

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(theme_data, f, indent=2, ensure_ascii=False)

            return True
        except Exception:
            return False

    def load_theme(self, theme_name: str, file_path: Optional[str] = None) -> Optional[Theme]:
        """Load a theme from a file."""
        if file_path is None:
            # Use default location
            cache_dir = Path.home() / ".cache" / "dbutils" / "themes"
            file_path = cache_dir / f"{theme_name}.json"

        if not file_path.exists():
            return None

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                theme_data = json.load(f)

            # Convert to Theme object
            palette_data = theme_data['palette']
            palette = ColorPalette(
                primary=palette_data['primary'],
                secondary=palette_data['secondary'],
                success=palette_data['success'],
                warning=palette_data['warning'],
                error=palette_data['error'],
                info=palette_data['info'],
                background=palette_data['background'],
                surface=palette_data['surface'],
                text_primary=palette_data['text_primary'],
                text_secondary=palette_data['text_secondary'],
                border=palette_data['border'],
                accent=palette_data['accent']
            )

            typography_data = theme_data['typography']
            typography = Typography(
                font_family=typography_data['font_family'],
                base_size=typography_data['base_size'],
                heading_sizes=typography_data['heading_sizes'],
                line_height=typography_data['line_height']
            )

            spacing_data = theme_data['spacing']
            spacing = Spacing(
                base_unit=spacing_data['base_unit'],
                scale=spacing_data['scale']
            )

            theme = Theme(
                name=theme_data['name'],
                mode=ThemeMode[theme_data['mode']],
                palette=palette,
                typography=typography,
                spacing=spacing,
                border_radius=theme_data['border_radius'],
                shadow_level=theme_data['shadow_level']
            )

            return theme
        except Exception:
            return None

    def get_theme_summary(self) -> Dict[str, Any]:
        """Get a summary of current theme settings."""
        theme = self.get_current_theme()
        if not theme:
            return {}

        return {
            'name': theme.name,
            'mode': theme.mode.name,
            'colors': {
                'primary': theme.palette.primary,
                'background': theme.palette.background,
                'text': theme.palette.text_primary
            },
            'typography': {
                'font_family': theme.typography.font_family,
                'base_size': theme.typography.base_size
            },
            'spacing': {
                'base_unit': theme.spacing.base_unit
            }
        }

    def detect_system_theme(self) -> ThemeMode:
        """Detect system theme preference."""
        if not QT_AVAILABLE:
            return ThemeMode.LIGHT

        try:
            # Try to detect system theme preference
            settings = QSettings("HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize", QSettings.Format.NativeFormat)
            if settings.contains("AppsUseLightTheme"):
                light_theme = settings.value("AppsUseLightTheme") == 1
                return ThemeMode.LIGHT if light_theme else ThemeMode.DARK
        except Exception:
            pass

        # Fallback to light theme
        return ThemeMode.LIGHT

    def apply_system_theme(self):
        """Apply theme based on system preference."""
        system_theme = self.detect_system_theme()
        if system_theme == ThemeMode.DARK:
            self.set_theme("dark")
        else:
            self.set_theme("light")

# Singleton instance for easy access
_ui_styling_instance = None

def get_ui_styling() -> UIStyling:
    """Get the singleton UI styling instance."""
    global _ui_styling_instance
    if _ui_styling_instance is None:
        _ui_styling_instance = UIStyling()
    return _ui_styling_instance