#!/usr/bin/env python3
"""
Accessibility Improvements Module

Accessibility utilities for the database browser application.
This module addresses accessibility issues by providing:
- Screen reader support
- Keyboard navigation enhancements
- High contrast modes
- Accessibility auditing
- ARIA attribute management

Features:
- Accessibility auditing and reporting
- Keyboard navigation utilities
- Screen reader optimization
- High contrast theme support
- Accessibility compliance checking
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

# Try to import Qt components for accessibility features
try:
    from PySide6.QtCore import QObject, Qt, Signal
    from PySide6.QtGui import QAccessible, QAccessibleEvent, QAccessibleInterface
    from PySide6.QtWidgets import QApplication, QWidget

    QT_AVAILABLE = True
except ImportError:
    try:
        from PyQt6.QtCore import QObject, Qt, Signal
        from PyQt6.QtGui import QAccessible, QAccessibleEvent, QAccessibleInterface
        from PyQt6.QtWidgets import QApplication, QWidget

        QT_AVAILABLE = True
    except ImportError:
        QT_AVAILABLE = False


class AccessibilityLevel(Enum):
    """Accessibility compliance levels."""

    BASIC = auto()
    INTERMEDIATE = auto()
    ADVANCED = auto()
    WCAG_A = auto()
    WCAG_AA = auto()
    WCAG_AAA = auto()


class AccessibilityIssue(Enum):
    """Types of accessibility issues."""

    MISSING_LABEL = auto()
    POOR_CONTRAST = auto()
    MISSING_ALT_TEXT = auto()
    KEYBOARD_NAVIGATION = auto()
    FOCUS_MANAGEMENT = auto()
    SCREEN_READER = auto()
    COLOR_DEPENDENCY = auto()
    TEXT_SCALING = auto()
    ANIMATION = auto()


@dataclass
class AccessibilityAuditResult:
    """Result of an accessibility audit."""

    widget: Any
    issue_type: AccessibilityIssue
    severity: str  # "low", "medium", "high"
    description: str
    suggested_fix: str
    element_identifier: Optional[str] = None


class AccessibilityManager:
    """Accessibility management for the database browser UI."""

    def __init__(self):
        self._accessibility_level = AccessibilityLevel.INTERMEDIATE
        self._high_contrast_mode = False
        self._screen_reader_optimized = False
        self._keyboard_navigation_enabled = True
        self._audit_results: List[AccessibilityAuditResult] = []
        self._accessibility_warnings: Set[str] = set()

        # Initialize accessibility features
        self._initialize_accessibility_features()

    def _initialize_accessibility_features(self):
        """Initialize accessibility features."""
        if QT_AVAILABLE:
            try:
                # Enable Qt accessibility features
                QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling)
                QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)

                # Set accessibility interface if available
                if hasattr(QAccessible, "setFactory"):
                    QAccessible.setFactory(self._create_accessible_factory())
            except Exception:
                # Gracefully handle any Qt accessibility API issues
                pass

    def _create_accessible_factory(self):
        """Create accessible interface factory."""

        class AccessibleFactory(QAccessible.Factory):
            def create(self, object: str, interface: QAccessibleInterface) -> QAccessibleInterface:
                # Create enhanced accessible interface
                return EnhancedAccessibleInterface(object, interface)

        return AccessibleFactory()

    def set_accessibility_level(self, level: AccessibilityLevel):
        """Set the accessibility compliance level."""
        self._accessibility_level = level
        self._update_accessibility_settings()

    def get_accessibility_level(self) -> AccessibilityLevel:
        """Get current accessibility compliance level."""
        return self._accessibility_level

    def enable_high_contrast_mode(self, enabled: bool = True):
        """Enable or disable high contrast mode."""
        self._high_contrast_mode = enabled
        if enabled:
            self._apply_high_contrast_styles()

    def is_high_contrast_enabled(self) -> bool:
        """Check if high contrast mode is enabled."""
        return self._high_contrast_mode

    def optimize_for_screen_reader(self, enabled: bool = True):
        """Optimize UI for screen readers."""
        self._screen_reader_optimized = enabled
        if enabled:
            self._apply_screen_reader_optimizations()

    def is_screen_reader_optimized(self) -> bool:
        """Check if screen reader optimizations are enabled."""
        return self._screen_reader_optimized

    def enable_keyboard_navigation(self, enabled: bool = True):
        """Enable or disable enhanced keyboard navigation."""
        self._keyboard_navigation_enabled = enabled

    def is_keyboard_navigation_enabled(self) -> bool:
        """Check if keyboard navigation is enabled."""
        return self._keyboard_navigation_enabled

    def _update_accessibility_settings(self):
        """Update accessibility settings based on compliance level."""
        if self._accessibility_level in [
            AccessibilityLevel.WCAG_A,
            AccessibilityLevel.WCAG_AA,
            AccessibilityLevel.WCAG_AAA,
        ]:
            self.enable_high_contrast_mode(True)
            self.optimize_for_screen_reader(True)
            self.enable_keyboard_navigation(True)
        elif self._accessibility_level == AccessibilityLevel.ADVANCED:
            self.enable_high_contrast_mode(False)
            self.optimize_for_screen_reader(True)
            self.enable_keyboard_navigation(True)
        elif self._accessibility_level == AccessibilityLevel.INTERMEDIATE:
            self.enable_high_contrast_mode(False)
            self.optimize_for_screen_reader(False)
            self.enable_keyboard_navigation(True)
        else:  # BASIC
            self.enable_high_contrast_mode(False)
            self.optimize_for_screen_reader(False)
            self.enable_keyboard_navigation(False)

    def _apply_high_contrast_styles(self):
        """Apply high contrast styles to UI elements."""
        if QT_AVAILABLE:
            # Apply high contrast stylesheet
            stylesheet = """
            /* High Contrast Mode */
            QWidget {
                background-color: #000000;
                color: #FFFFFF;
            }

            QLineEdit, QComboBox, QTextEdit {
                background-color: #000000;
                color: #FFFFFF;
                border: 2px solid #FFFFFF;
            }

            QPushButton {
                background-color: #000000;
                color: #FFFFFF;
                border: 2px solid #FFFFFF;
            }

            QPushButton:hover {
                background-color: #FFFFFF;
                color: #000000;
            }

            QTableView, QListView, QTreeView {
                background-color: #000000;
                color: #FFFFFF;
                border: 2px solid #FFFFFF;
                alternate-background-color: #333333;
            }

            QHeaderView::section {
                background-color: #111111;
                color: #FFFFFF;
                border: 1px solid #FFFFFF;
            }

            QToolTip {
                background-color: #000000;
                color: #FFFFFF;
                border: 2px solid #FFFFFF;
            }
            """

            # Apply to all widgets
            for widget in QApplication.allWidgets():
                widget.setStyleSheet(widget.styleSheet() + stylesheet)

    def _apply_screen_reader_optimizations(self):
        """Apply optimizations for screen readers."""
        if QT_AVAILABLE:
            # Ensure all widgets have proper accessible names and descriptions
            for widget in QApplication.allWidgets():
                self._ensure_accessible_properties(widget)

    def _ensure_accessible_properties(self, widget: QWidget):
        """Ensure a widget has proper accessible properties."""
        if not widget.accessibleName():
            # Generate accessible name based on widget type and content
            name = self._generate_accessible_name(widget)
            widget.setAccessibleName(name)

        if not widget.accessibleDescription() and hasattr(widget, "toolTip"):
            widget.setAccessibleDescription(widget.toolTip() or "")

    def _generate_accessible_name(self, widget: QWidget) -> str:
        """Generate an accessible name for a widget."""
        widget_type = widget.metaObject().className()
        text = ""

        # Try to get text from common widget types
        if hasattr(widget, "text") and widget.text():
            text = widget.text()
        elif hasattr(widget, "title") and widget.title():
            text = widget.title()
        elif hasattr(widget, "windowTitle") and widget.windowTitle():
            text = widget.windowTitle()

        if text:
            return f"{widget_type}: {text}"
        else:
            return widget_type

    def audit_accessibility(self, widget: Optional[QWidget] = None) -> List[AccessibilityAuditResult]:
        """Perform an accessibility audit on a widget or the entire application."""
        results = []

        if widget is None and QT_AVAILABLE:
            # Audit all widgets
            for w in QApplication.allWidgets():
                results.extend(self._audit_widget(w))
        elif widget is not None:
            results.extend(self._audit_widget(widget))

        self._audit_results = results
        return results

    def _audit_widget(self, widget: QWidget) -> List[AccessibilityAuditResult]:
        """Audit a single widget for accessibility issues."""
        results = []
        widget_type = widget.metaObject().className()

        # Check for missing accessible name
        if not widget.accessibleName():
            results.append(
                AccessibilityAuditResult(
                    widget=widget,
                    issue_type=AccessibilityIssue.MISSING_LABEL,
                    severity="medium",
                    description=f"{widget_type} is missing accessible name",
                    suggested_fix="Add setAccessibleName() with descriptive text",
                    element_identifier=self._get_widget_identifier(widget),
                )
            )

        # Check for poor color contrast (simplified check)
        if hasattr(widget, "palette"):
            bg_color = widget.palette().color(widget.backgroundRole())
            text_color = widget.palette().color(widget.foregroundRole())

            if self._calculate_contrast_ratio(bg_color, text_color) < 4.5:
                results.append(
                    AccessibilityAuditResult(
                        widget=widget,
                        issue_type=AccessibilityIssue.POOR_CONTRAST,
                        severity="high",
                        description=f"{widget_type} has poor color contrast",
                        suggested_fix="Adjust colors to meet WCAG contrast requirements",
                        element_identifier=self._get_widget_identifier(widget),
                    )
                )

        # Check for keyboard navigation issues
        if widget.focusPolicy() not in [Qt.FocusPolicy.StrongFocus, Qt.FocusPolicy.WheelFocus]:
            results.append(
                AccessibilityAuditResult(
                    widget=widget,
                    issue_type=AccessibilityIssue.KEYBOARD_NAVIGATION,
                    severity="low",
                    description=f"{widget_type} may not be keyboard accessible",
                    suggested_fix="Set appropriate focus policy",
                    element_identifier=self._get_widget_identifier(widget),
                )
            )

        return results

    def _get_widget_identifier(self, widget: QWidget) -> str:
        """Get a unique identifier for a widget."""
        identifier_parts = []

        # Add widget type
        identifier_parts.append(widget.metaObject().className())

        # Add object name if available
        if widget.objectName():
            identifier_parts.append(f"name={widget.objectName()}")

        # Add text if available
        if hasattr(widget, "text") and widget.text():
            identifier_parts.append(f"text={widget.text()[:20]}...")

        return " | ".join(identifier_parts)

    def _calculate_contrast_ratio(self, color1: QColor, color2: QColor) -> float:
        """Calculate contrast ratio between two colors."""

        def get_luminance(color: QColor) -> float:
            r, g, b = color.red() / 255.0, color.green() / 255.0, color.blue() / 255.0

            # Apply gamma correction
            r = r / 12.92 if r <= 0.03928 else ((r + 0.055) / 1.055) ** 2.4
            g = g / 12.92 if g <= 0.03928 else ((g + 0.055) / 1.055) ** 2.4
            b = b / 12.92 if b <= 0.03928 else ((b + 0.055) / 1.055) ** 2.4

            return 0.2126 * r + 0.7152 * g + 0.0722 * b

        l1 = get_luminance(color1)
        l2 = get_luminance(color2)

        # Ensure l1 is the lighter color
        if l1 < l2:
            l1, l2 = l2, l1

        return (l1 + 0.05) / (l2 + 0.05)

    def get_accessibility_issues(self) -> List[AccessibilityAuditResult]:
        """Get current accessibility issues."""
        return self._audit_results.copy()

    def get_accessibility_warnings(self) -> Set[str]:
        """Get accessibility warnings."""
        return self._accessibility_warnings.copy()

    def add_accessibility_warning(self, warning: str):
        """Add an accessibility warning."""
        self._accessibility_warnings.add(warning)

    def clear_accessibility_warnings(self):
        """Clear all accessibility warnings."""
        self._accessibility_warnings.clear()

    def get_accessibility_report(self) -> Dict[str, Any]:
        """Generate an accessibility compliance report."""
        # Count issues by type and severity
        by_type = {}
        by_severity = {"low": 0, "medium": 0, "high": 0}

        for issue in self._audit_results:
            type_name = issue.issue_type.name
            if type_name not in by_type:
                by_type[type_name] = 0
            by_type[type_name] += 1

            by_severity[issue.severity] += 1

        # Determine compliance level
        compliance_level = self._determine_compliance_level()

        return {
            "compliance_level": compliance_level.name,
            "total_issues": len(self._audit_results),
            "issues_by_type": by_type,
            "issues_by_severity": by_severity,
            "warnings": list(self._accessibility_warnings),
            "recommendations": self._get_recommendations(compliance_level),
        }

    def _determine_compliance_level(self) -> AccessibilityLevel:
        """Determine accessibility compliance level based on audit results."""
        if len(self._audit_results) == 0:
            return AccessibilityLevel.WCAG_AAA
        elif len(self._audit_results) <= 3:
            return AccessibilityLevel.WCAG_AA
        elif len(self._audit_results) <= 10:
            return AccessibilityLevel.WCAG_A
        elif len(self._audit_results) <= 20:
            return AccessibilityLevel.ADVANCED
        elif len(self._audit_results) <= 50:
            return AccessibilityLevel.INTERMEDIATE
        else:
            return AccessibilityLevel.BASIC

    def _get_recommendations(self, current_level: AccessibilityLevel) -> List[str]:
        """Get recommendations based on current compliance level."""
        recommendations = []

        if current_level == AccessibilityLevel.BASIC:
            recommendations.extend(
                [
                    "Add accessible names to all interactive elements",
                    "Ensure proper color contrast for all text",
                    "Implement keyboard navigation for all features",
                    "Add alt text for all images and icons",
                    "Test with screen readers",
                ]
            )
        elif current_level == AccessibilityLevel.INTERMEDIATE:
            recommendations.extend(
                [
                    "Improve color contrast for better readability",
                    "Add ARIA attributes where needed",
                    "Test keyboard navigation thoroughly",
                    "Add focus indicators for all interactive elements",
                    "Test with multiple screen readers",
                ]
            )
        elif current_level == AccessibilityLevel.ADVANCED:
            recommendations.extend(
                [
                    "Fine-tune keyboard navigation",
                    "Add skip navigation links",
                    "Implement proper heading hierarchy",
                    "Add language attributes",
                    "Test with users with disabilities",
                ]
            )
        elif current_level == AccessibilityLevel.WCAG_A:
            recommendations.extend(
                [
                    "Address remaining contrast issues",
                    "Ensure all functionality is keyboard accessible",
                    "Add text alternatives for all non-text content",
                    "Test with various assistive technologies",
                    "Conduct user testing with diverse users",
                ]
            )
        elif current_level == AccessibilityLevel.WCAG_AA:
            recommendations.extend(
                [
                    "Maintain current accessibility standards",
                    "Conduct regular accessibility audits",
                    "Stay updated with WCAG guidelines",
                    "Train team on accessibility best practices",
                    "Involve users with disabilities in testing",
                ]
            )
        else:  # WCAG_AAA
            recommendations.extend(
                [
                    "Maintain excellent accessibility standards",
                    "Conduct frequent accessibility reviews",
                    "Stay ahead of accessibility trends",
                    "Share best practices with the community",
                    "Continue user testing and feedback",
                ]
            )

        return recommendations

    def add_keyboard_shortcut(self, widget: QWidget, key_sequence: str, callback: Callable, description: str):
        """Add a keyboard shortcut to a widget with accessibility description."""
        if QT_AVAILABLE and hasattr(widget, "addAction"):
            action = QAction(widget)
            action.setShortcut(key_sequence)
            action.triggered.connect(callback)
            action.setStatusTip(description)
            action.setToolTip(f"Shortcut: {key_sequence} - {description}")
            widget.addAction(action)

            # Add to accessibility properties
            current_desc = widget.accessibleDescription() or ""
            new_desc = f"{current_desc} Shortcut: {key_sequence} - {description}"
            widget.setAccessibleDescription(new_desc)

    def ensure_focus_indicator(self, widget: QWidget):
        """Ensure a widget has proper focus indicators."""
        if QT_AVAILABLE:
            # Add focus policy if not set
            if widget.focusPolicy() == Qt.FocusPolicy.NoFocus:
                widget.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

            # Add stylesheet for focus indicator
            current_style = widget.styleSheet() or ""
            focus_style = """
            QWidget:focus {
                border: 2px solid #3498db;
                outline: none;
            }
            """
            widget.setStyleSheet(current_style + focus_style)

    def add_aria_attributes(self, widget: QWidget, attributes: Dict[str, str]):
        """Add ARIA attributes to a widget."""
        if QT_AVAILABLE:
            # Store ARIA attributes in widget properties
            for attr, value in attributes.items():
                widget.setProperty(f"aria-{attr}", value)

            # Update accessible description with ARIA attributes
            aria_desc = "ARIA: " + ", ".join(f"{k}={v}" for k, v in attributes.items())
            current_desc = widget.accessibleDescription() or ""
            widget.setAccessibleDescription(f"{current_desc} {aria_desc}".strip())

    def create_accessible_tooltip(self, widget: QWidget, tooltip_text: str, extended_description: str = ""):
        """Create an accessible tooltip with extended description."""
        if QT_AVAILABLE:
            # Set standard tooltip
            widget.setToolTip(tooltip_text)

            # Set accessible description with extended info
            full_desc = f"{tooltip_text}"
            if extended_description:
                full_desc += f"\n\n{extended_description}"
            widget.setAccessibleDescription(full_desc)

    def test_color_contrast(self, bg_color: str, text_color: str) -> Tuple[float, str]:
        """Test color contrast and return ratio and compliance level."""
        try:
            from PySide6.QtGui import QColor

            bg_qcolor = QColor(bg_color)
            text_qcolor = QColor(text_color)

            ratio = self._calculate_contrast_ratio(bg_qcolor, text_qcolor)

            if ratio >= 7.0:
                compliance = "WCAG AAA"
            elif ratio >= 4.5:
                compliance = "WCAG AA"
            elif ratio >= 3.0:
                compliance = "WCAG A"
            else:
                compliance = "Fails WCAG"

            return ratio, compliance
        except Exception:
            return 0.0, "Invalid colors"

    def get_accessibility_guidelines(self) -> Dict[str, List[str]]:
        """Get accessibility guidelines by category."""
        return {
            "General": [
                "Ensure all functionality is keyboard accessible",
                "Provide text alternatives for non-text content",
                "Make content adaptable and distinguishable",
                "Ensure content is readable and understandable",
            ],
            "Visual": [
                "Use sufficient color contrast (4.5:1 minimum)",
                "Don't rely solely on color to convey information",
                "Provide clear visual focus indicators",
                "Ensure text is resizable up to 200% without loss of content",
            ],
            "Keyboard": [
                "All functionality should be operable via keyboard",
                "Provide visible focus indicators",
                "Ensure logical tab order",
                "Provide keyboard shortcuts for frequent actions",
            ],
            "Screen Readers": [
                "Use proper semantic HTML equivalents",
                "Provide descriptive labels and names",
                "Use ARIA attributes appropriately",
                "Ensure dynamic content changes are announced",
            ],
            "Forms": [
                "Associate labels with form controls",
                "Provide clear error messages",
                "Group related form elements",
                "Provide instructions and help text",
            ],
        }

    def check_wcag_compliance(self) -> Dict[str, bool]:
        """Check WCAG compliance for key criteria."""
        compliance = {"perceivable": True, "operable": True, "understandable": True, "robust": True}

        # Check for basic compliance issues
        if len(self._audit_results) > 0:
            for issue in self._audit_results:
                if issue.severity == "high":
                    if issue.issue_type in [AccessibilityIssue.MISSING_LABEL, AccessibilityIssue.POOR_CONTRAST]:
                        compliance["perceivable"] = False
                    elif issue.issue_type == AccessibilityIssue.KEYBOARD_NAVIGATION:
                        compliance["operable"] = False

        return compliance

    def __del__(self):
        """Clean up accessibility resources."""
        self._audit_results.clear()
        self._accessibility_warnings.clear()


class EnhancedAccessibleInterface(QAccessibleInterface):
    """Enhanced accessible interface with additional features."""

    def __init__(self, object: str, interface: QAccessibleInterface):
        super().__init__(object, interface)
        self._object = object
        self._base_interface = interface

    def text(self, textType: QAccessible.Text) -> str:
        """Get accessible text with enhanced descriptions."""
        base_text = self._base_interface.text(textType)

        # Add additional context for screen readers
        if textType == QAccessible.Text.Name:
            return self._enhance_name(base_text)
        elif textType == QAccessible.Text.Description:
            return self._enhance_description(base_text)
        else:
            return base_text

    def _enhance_name(self, name: str) -> str:
        """Enhance the accessible name with additional context."""
        if not name:
            return ""

        # Add widget type for better context
        widget = self.object()
        if hasattr(widget, "metaObject"):
            widget_type = widget.metaObject().className()
            return f"{widget_type}: {name}"

        return name

    def _enhance_description(self, description: str) -> str:
        """Enhance the accessible description with additional context."""
        if not description:
            return ""

        # Add keyboard shortcuts if available
        widget = self.object()
        if hasattr(widget, "shortcut"):
            shortcut = widget.shortcut().toString()
            if shortcut:
                description += f" Shortcut: {shortcut}"

        return description

    def role(self) -> QAccessible.Role:
        """Get the accessible role with enhanced detection."""
        base_role = self._base_interface.role()

        # Try to provide more specific roles
        widget = self.object()
        if hasattr(widget, "metaObject"):
            class_name = widget.metaObject().className()

            if "Button" in class_name:
                return QAccessible.Role.Button
            elif "CheckBox" in class_name:
                return QAccessible.Role.CheckBox
            elif "ComboBox" in class_name:
                return QAccessible.Role.ComboBox
            elif "LineEdit" in class_name:
                return QAccessible.Role.EditableText
            elif "Table" in class_name:
                return QAccessible.Role.Table
            elif "Tree" in class_name:
                return QAccessible.Role.Tree

        return base_role

    def state(self) -> QAccessible.State:
        """Get the accessible state with enhanced detection."""
        base_state = self._base_interface.state()

        # Add additional states based on widget properties
        widget = self.object()

        if hasattr(widget, "isEnabled") and not widget.isEnabled():
            base_state.disabled = True

        if hasattr(widget, "hasFocus") and widget.hasFocus():
            base_state.focused = True

        if hasattr(widget, "isChecked") and widget.isChecked():
            base_state.checked = True

        return base_state


# Singleton instance for easy access
_accessibility_manager_instance = None


def get_accessibility_manager() -> AccessibilityManager:
    """Get the singleton accessibility manager instance."""
    global _accessibility_manager_instance
    if _accessibility_manager_instance is None:
        _accessibility_manager_instance = AccessibilityManager()
    return _accessibility_manager_instance


# Convenience functions for common accessibility tasks
def ensure_widget_accessibility(widget: QWidget, name: str = "", description: str = ""):
    """Ensure a widget has proper accessibility properties."""
    if QT_AVAILABLE and widget:
        if name:
            widget.setAccessibleName(name)
        if description:
            widget.setAccessibleDescription(description)

        # Ensure proper focus policy
        if widget.focusPolicy() == Qt.FocusPolicy.NoFocus:
            widget.setFocusPolicy(Qt.FocusPolicy.StrongFocus)


def add_accessible_tooltip(widget: QWidget, tooltip: str, description: str = ""):
    """Add accessible tooltip to a widget."""
    if QT_AVAILABLE and widget:
        widget.setToolTip(tooltip)
        if description:
            current_desc = widget.accessibleDescription() or ""
            widget.setAccessibleDescription(f"{current_desc} {description}".strip())


def check_accessibility_compliance(widget: Optional[QWidget] = None) -> Dict[str, Any]:
    """Check accessibility compliance for a widget or application."""
    manager = get_accessibility_manager()
    return manager.get_accessibility_report()


def run_accessibility_audit(widget: Optional[QWidget] = None) -> List[AccessibilityAuditResult]:
    """Run accessibility audit and return results."""
    manager = get_accessibility_manager()
    return manager.audit_accessibility(widget)
