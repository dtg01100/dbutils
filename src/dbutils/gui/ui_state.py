#!/usr/bin/env python3
"""
UI State Management Module

Centralized state management for the database browser application.
This module addresses the inconsistent UI state management found throughout the codebase
by providing a unified approach to managing application state.

Features:
- Centralized state container
- State change notifications
- Persistent state management
- Undo/redo functionality
- State validation
"""

from __future__ import annotations
import json
import os
import time
from typing import Dict, Any, Optional, List, Callable, Set
from enum import Enum, auto
from dataclasses import dataclass, field
import threading
from pathlib import Path
import weakref
import copy
from abc import ABC, abstractmethod

class UIStateSection(Enum):
    """Sections of UI state that can be managed independently."""
    SEARCH = auto()
    DISPLAY = auto()
    LAYOUT = auto()
    PREFERENCES = auto()
    NAVIGATION = auto()
    DATA = auto()

@dataclass
class StateChange:
    """Represents a change in application state."""
    section: UIStateSection
    key: str
    old_value: Any
    new_value: Any
    timestamp: float = field(default_factory=lambda: time.time())

class StateObserver(ABC):
    """Abstract base class for state observers."""

    @abstractmethod
    def on_state_changed(self, change: StateChange):
        """Called when state changes."""
        pass

class UIStateManager:
    """Centralized state management for the database browser UI."""

    def __init__(self):
        self._state: Dict[str, Any] = {}
        self._observers: Set[weakref.ref] = set()
        self._lock = threading.RLock()
        self._change_history: List[StateChange] = []
        self._max_history = 100  # Maximum number of changes to track
        self._initialized = False

        # Initialize default state
        self._initialize_default_state()

    def _initialize_default_state(self):
        """Initialize the application with default state values."""
        with self._lock:
            # Search state
            self._state['search.mode'] = 'tables'
            self._state['search.query'] = ''
            self._state['search.show_non_matching'] = True
            self._state['search.inline_highlight'] = True
            self._state['search.streaming_enabled'] = True
            self._state['search.debounce_delay'] = 150

            # Display state
            self._state['display.schema_filter'] = None
            self._state['display.table_view_mode'] = 'list'
            self._state['display.column_view_mode'] = 'list'
            self._state['display.show_tooltips'] = True
            self._state['display.row_height'] = 30

            # Layout state
            self._state['layout.search_dock_visible'] = True
            self._state['layout.tables_dock_visible'] = True
            self._state['layout.columns_dock_visible'] = True
            self._state['layout.contents_dock_visible'] = False
            self._state['layout.details_dock_visible'] = False

            # Preferences
            self._state['prefs.use_cache'] = True
            self._state['prefs.cache_ttl'] = 3600
            self._state['prefs.auto_refresh'] = False
            self._state['prefs.theme'] = 'light'

            # Navigation
            self._state['nav.selected_table'] = None
            self._state['nav.selected_column'] = None
            self._state['nav.last_search'] = None

            # Data state
            self._state['data.last_refresh'] = None
            self._state['data.schema_count'] = 0
            self._state['data.table_count'] = 0
            self._state['data.column_count'] = 0

            self._initialized = True

    def register_observer(self, observer: StateObserver):
        """Register an observer to be notified of state changes."""
        with self._lock:
            # Use weak reference to avoid memory leaks
            self._observers.add(weakref.ref(observer))

    def unregister_observer(self, observer: StateObserver):
        """Unregister an observer."""
        with self._lock:
            # Remove weak references to the observer
            to_remove = []
            for ref in self._observers:
                if ref() is observer:
                    to_remove.append(ref)

            for ref in to_remove:
                self._observers.discard(ref)

    def _notify_observers(self, change: StateChange):
        """Notify all registered observers of a state change."""
        with self._lock:
            # Clean up dead references
            valid_observers = []
            for ref in self._observers:
                observer = ref()
                if observer is not None:
                    valid_observers.append(ref)
                    try:
                        observer.on_state_changed(change)
                    except Exception:
                        # Don't let observer errors break state management
                        pass

            self._observers = set(valid_observers)

    def get_state(self, key: str, default: Any = None) -> Any:
        """Get a state value with optional default."""
        with self._lock:
            return self._state.get(key, default)

    def set_state(self, key: str, value: Any, section: UIStateSection = None) -> bool:
        """Set a state value and notify observers if changed."""
        with self._lock:
            if not self._initialized:
                # Allow setting state during initialization without notifications
                self._state[key] = value
                return True

            old_value = self._state.get(key)
            if old_value == value:
                return False  # No change

            # Determine section if not provided
            if section is None:
                section = self._infer_section_from_key(key)

            # Create change record
            change = StateChange(
                section=section,
                key=key,
                old_value=old_value,
                new_value=value
            )

            # Update state
            self._state[key] = value

            # Add to history (with limit)
            self._change_history.append(change)
            if len(self._change_history) > self._max_history:
                self._change_history.pop(0)

            # Notify observers
            self._notify_observers(change)

            return True

    def _infer_section_from_key(self, key: str) -> UIStateSection:
        """Infer the state section from a key name."""
        if key.startswith('search.'):
            return UIStateSection.SEARCH
        elif key.startswith('display.'):
            return UIStateSection.DISPLAY
        elif key.startswith('layout.'):
            return UIStateSection.LAYOUT
        elif key.startswith('prefs.'):
            return UIStateSection.PREFERENCES
        elif key.startswith('nav.'):
            return UIStateSection.NAVIGATION
        elif key.startswith('data.'):
            return UIStateSection.DATA
        else:
            return UIStateSection.PREFERENCES  # Default

    def toggle_state(self, key: str) -> bool:
        """Toggle a boolean state value."""
        with self._lock:
            current = self.get_state(key)
            if isinstance(current, bool):
                return self.set_state(key, not current)
            return False

    def reset_state(self, section: UIStateSection = None):
        """Reset state to defaults for a specific section or all sections."""
        with self._lock:
            if section is None:
                # Reset all state
                self._state.clear()
                self._initialize_default_state()
                self._notify_observers(StateChange(
                    section=UIStateSection.PREFERENCES,
                    key='*',
                    old_value=None,
                    new_value='reset'
                ))
            else:
                # Reset specific section
                for key in list(self._state.keys()):
                    if self._infer_section_from_key(key) == section:
                        del self._state[key]

                # Reinitialize the specific section
                if section == UIStateSection.SEARCH:
                    self._initialize_search_state()
                elif section == UIStateSection.DISPLAY:
                    self._initialize_display_state()
                elif section == UIStateSection.LAYOUT:
                    self._initialize_layout_state()
                elif section == UIStateSection.PREFERENCES:
                    self._initialize_preferences_state()
                elif section == UIStateSection.NAVIGATION:
                    self._initialize_navigation_state()
                elif section == UIStateSection.DATA:
                    self._initialize_data_state()

                self._notify_observers(StateChange(
                    section=section,
                    key='*',
                    old_value=None,
                    new_value='reset'
                ))

    def _initialize_search_state(self):
        """Initialize search-related state."""
        self._state['search.mode'] = 'tables'
        self._state['search.query'] = ''
        self._state['search.show_non_matching'] = True
        self._state['search.inline_highlight'] = True
        self._state['search.streaming_enabled'] = True
        self._state['search.debounce_delay'] = 150

    def _initialize_display_state(self):
        """Initialize display-related state."""
        self._state['display.schema_filter'] = None
        self._state['display.table_view_mode'] = 'list'
        self._state['display.column_view_mode'] = 'list'
        self._state['display.show_tooltips'] = True
        self._state['display.row_height'] = 30

    def _initialize_layout_state(self):
        """Initialize layout-related state."""
        self._state['layout.search_dock_visible'] = True
        self._state['layout.tables_dock_visible'] = True
        self._state['layout.columns_dock_visible'] = True
        self._state['layout.contents_dock_visible'] = False
        self._state['layout.details_dock_visible'] = False

    def _initialize_preferences_state(self):
        """Initialize preference-related state."""
        self._state['prefs.use_cache'] = True
        self._state['prefs.cache_ttl'] = 3600
        self._state['prefs.auto_refresh'] = False
        self._state['prefs.theme'] = 'light'

    def _initialize_navigation_state(self):
        """Initialize navigation-related state."""
        self._state['nav.selected_table'] = None
        self._state['nav.selected_column'] = None
        self._state['nav.last_search'] = None

    def _initialize_data_state(self):
        """Initialize data-related state."""
        self._state['data.last_refresh'] = None
        self._state['data.schema_count'] = 0
        self._state['data.table_count'] = 0
        self._state['data.column_count'] = 0

    def get_state_section(self, section: UIStateSection) -> Dict[str, Any]:
        """Get all state values for a specific section."""
        with self._lock:
            result = {}
            for key, value in self._state.items():
                if self._infer_section_from_key(key) == section:
                    result[key] = value
            return result

    def save_state(self, file_path: Optional[str] = None) -> bool:
        """Save current state to a file."""
        if file_path is None:
            # Use default location
            cache_dir = Path.home() / ".cache" / "dbutils"
            cache_dir.mkdir(parents=True, exist_ok=True)
            file_path = cache_dir / "ui_state.json"

        try:
            with self._lock:
                state_copy = copy.deepcopy(self._state)

                # Remove sensitive or transient data
                if 'nav.selected_table' in state_copy:
                    del state_copy['nav.selected_table']
                if 'nav.selected_column' in state_copy:
                    del state_copy['nav.selected_column']

                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(state_copy, f, indent=2, ensure_ascii=False)

            return True
        except Exception:
            return False

    def load_state(self, file_path: Optional[str] = None) -> bool:
        """Load state from a file."""
        if file_path is None:
            # Use default location
            cache_dir = Path.home() / ".cache" / "dbutils"
            file_path = cache_dir / "ui_state.json"

        if not file_path.exists():
            return False

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                saved_state = json.load(f)

            with self._lock:
                # Merge loaded state with current state
                for key, value in saved_state.items():
                    # Only restore valid keys that exist in our schema
                    if key in self._state:
                        self._state[key] = value

            return True
        except Exception:
            return False

    def get_change_history(self, limit: int = 10) -> List[StateChange]:
        """Get recent state changes."""
        with self._lock:
            return self._change_history[-limit:] if limit > 0 else self._change_history.copy()

    def can_undo(self) -> bool:
        """Check if undo is possible."""
        with self._lock:
            return len(self._change_history) > 0

    def undo_last_change(self) -> bool:
        """Undo the last state change."""
        with self._lock:
            if not self._change_history:
                return False

            last_change = self._change_history.pop()
            if last_change.key in self._state:
                # Revert to old value
                self._state[last_change.key] = last_change.old_value

                # Notify observers of the undo
                undo_change = StateChange(
                    section=last_change.section,
                    key=last_change.key,
                    old_value=last_change.new_value,
                    new_value=last_change.old_value
                )
                self._notify_observers(undo_change)

                return True

            return False

    def get_state_summary(self) -> Dict[str, Any]:
        """Get a summary of current state for debugging/diagnostics."""
        with self._lock:
            return {
                'state_count': len(self._state),
                'observer_count': len(self._observers),
                'change_history_count': len(self._change_history),
                'initialized': self._initialized,
                'sections': {
                    section.name: len(self.get_state_section(section))
                    for section in UIStateSection
                }
            }

    def __del__(self):
        """Clean up when state manager is destroyed."""
        self._observers.clear()
        self._change_history.clear()

# Singleton instance for easy access
_ui_state_manager_instance = None

def get_ui_state_manager() -> UIStateManager:
    """Get the singleton UI state manager instance."""
    global _ui_state_manager_instance
    if _ui_state_manager_instance is None:
        _ui_state_manager_instance = UIStateManager()
    return _ui_state_manager_instance