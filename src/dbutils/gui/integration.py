#!/usr/bin/env python3
"""
UI/UX Integration Module

Integration module that unifies all UI/UX cleanup improvements.
This module provides a centralized interface to access all the
UI/UX enhancements and ensures seamless integration.

Features:
- Unified access to all UI/UX modules
- Centralized initialization and configuration
- Performance monitoring dashboard
- Accessibility compliance reporting
- Internationalization management
- Responsive design coordination
"""

from __future__ import annotations
import sys
from typing import Dict, Any, Optional, List, Callable, Tuple
from dataclasses import dataclass
import threading
import logging
from pathlib import Path

# Import all UI/UX modules
from .search_manager import get_search_manager, SearchManager
from .ui_state import get_ui_state_manager, UIStateManager
from .ui_styling import get_ui_styling, UIStyling
from .performance import get_performance_monitor, PerformanceMonitor
from .accessibility import get_accessibility_manager, AccessibilityManager
from .i18n import get_i18n_manager, I18nManager
from .responsive import get_responsive_manager, ResponsiveManager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dbutils.gui.integration")

@dataclass
class IntegrationStatus:
    """Status of the UI/UX integration."""
    initialized: bool = False
    modules_loaded: int = 0
    errors: List[str] = None
    performance_metrics: Dict[str, Any] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.performance_metrics is None:
            self.performance_metrics = {}

class UIXIntegration:
    """Centralized integration of all UI/UX cleanup modules."""

    def __init__(self):
        self._initialized = False
        self._lock = threading.RLock()
        self._status = IntegrationStatus()

        # Module instances
        self._search_manager = None
        self._ui_state_manager = None
        self._ui_styling = None
        self._performance_monitor = None
        self._accessibility_manager = None
        self._i18n_manager = None
        self._responsive_manager = None

        # Initialize all modules
        self.initialize()

    def initialize(self):
        """Initialize all UI/UX modules."""
        with self._lock:
            if self._initialized:
                return

            try:
                # Initialize modules in optimal order
                self._ui_state_manager = get_ui_state_manager()
                self._ui_styling = get_ui_styling()
                self._responsive_manager = get_responsive_manager()
                self._i18n_manager = get_i18n_manager()
                self._search_manager = get_search_manager()
                self._performance_monitor = get_performance_monitor()
                self._accessibility_manager = get_accessibility_manager()

                # Configure modules for optimal integration
                self._configure_modules()

                # Update status
                self._status.initialized = True
                self._status.modules_loaded = 7
                self._status.performance_metrics = self.get_performance_metrics()

                logger.info("UI/UX Integration initialized successfully")
                self._initialized = True

            except Exception as e:
                logger.error(f"UI/UX Integration initialization failed: {e}")
                self._status.errors.append(str(e))
                self._initialized = False

    def _configure_modules(self):
        """Configure modules for optimal integration."""
        try:
            # Enable performance monitoring
            self._performance_monitor.enable_monitoring(True)

            # Set reasonable accessibility level
            from .accessibility import AccessibilityLevel
            self._accessibility_manager.set_accessibility_level(AccessibilityLevel.INTERMEDIATE)

            # Apply system language
            self._i18n_manager.apply_system_language()

            # Detect and apply responsive settings
            self._responsive_manager._detect_screen_info()

            # Set default theme based on system preference
            from .ui_styling import ThemeMode
            system_theme = self._ui_styling.detect_system_theme()
            if system_theme == ThemeMode.DARK:
                self._ui_styling.set_theme("dark")
            else:
                self._ui_styling.set_theme("light")

        except Exception as e:
            logger.warning(f"Module configuration warning: {e}")
            self._status.errors.append(f"Configuration warning: {e}")

    def get_status(self) -> IntegrationStatus:
        """Get current integration status."""
        with self._lock:
            return self._status

    def is_initialized(self) -> bool:
        """Check if integration is initialized."""
        with self._lock:
            return self._initialized

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics."""
        if not self._initialized:
            return {}

        return {
            'search_metrics': self._search_manager.get_cache_stats(),
            'state_metrics': self._ui_state_manager.get_state_summary(),
            'performance_metrics': self._performance_monitor.get_metrics_summary(),
            'accessibility_metrics': self._accessibility_manager.get_accessibility_report(),
            'i18n_metrics': self._i18n_manager.get_translation_stats(),
            'responsive_metrics': {
                'breakpoint': self._responsive_manager.get_current_breakpoint().name,
                'screen_width': self._responsive_manager.get_screen_width(),
                'screen_height': self._responsive_manager.get_screen_height(),
                'device_type': self._responsive_manager.get_device_type()
            }
        }

    def get_accessibility_report(self) -> Dict[str, Any]:
        """Get comprehensive accessibility report."""
        if not self._initialized:
            return {'compliance': 'not_initialized'}

        return self._accessibility_manager.get_accessibility_report()

    def get_performance_optimizations(self) -> Dict[str, Any]:
        """Get performance optimization recommendations."""
        if not self._initialized:
            return {'recommendations': []}

        return {
            'memory_tips': self._performance_monitor.get_memory_optimization_tips(),
            'bottleneck_analysis': self._performance_monitor.analyze_performance_bottlenecks(
                self._performance_monitor.get_metrics()
            ),
            'responsive_settings': self._responsive_manager.get_responsive_performance_settings()
        }

    def get_integration_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive integration dashboard."""
        if not self._initialized:
            return {'status': 'not_initialized'}

        return {
            'status': self._status.__dict__,
            'performance': self.get_performance_metrics(),
            'accessibility': self.get_accessibility_report(),
            'optimizations': self.get_performance_optimizations(),
            'modules': {
                'search': self._search_manager is not None,
                'state': self._ui_state_manager is not None,
                'styling': self._ui_styling is not None,
                'performance': self._performance_monitor is not None,
                'accessibility': self._accessibility_manager is not None,
                'i18n': self._i18n_manager is not None,
                'responsive': self._responsive_manager is not None
            }
        }

    def apply_optimizations(self):
        """Apply recommended optimizations."""
        if not self._initialized:
            return False

        try:
            # Apply responsive optimizations
            responsive_settings = self._responsive_manager.get_responsive_performance_settings()
            self._performance_monitor.set_responsive_settings(responsive_settings)

            # Enable all performance features
            self._performance_monitor.start_background_worker()

            # Optimize search caching
            self._search_manager.clear_cache()

            logger.info("Applied UI/UX optimizations")
            return True
        except Exception as e:
            logger.error(f"Failed to apply optimizations: {e}")
            self._status.errors.append(f"Optimization error: {e}")
            return False

    def run_diagnostics(self) -> Dict[str, Any]:
        """Run comprehensive diagnostics."""
        if not self._initialized:
            return {'diagnostics': 'not_initialized'}

        diagnostics = {
            'modules': {},
            'warnings': [],
            'recommendations': []
        }

        # Check each module
        modules_to_check = [
            ('search', self._search_manager),
            ('state', self._ui_state_manager),
            ('styling', self._ui_styling),
            ('performance', self._performance_monitor),
            ('accessibility', self._accessibility_manager),
            ('i18n', self._i18n_manager),
            ('responsive', self._responsive_manager)
        ]

        for name, module in modules_to_check:
            if module is None:
                diagnostics['warnings'].append(f"{name}_module_not_loaded")
                continue

            diagnostics['modules'][name] = {
                'status': 'active',
                'type': type(module).__name__
            }

            # Module-specific checks
            if name == 'search':
                stats = module.get_cache_stats()
                diagnostics['modules'][name]['cache_efficiency'] = stats.get('cache_efficiency', 0)
            elif name == 'performance':
                metrics = module.get_metrics_summary()
                diagnostics['modules'][name]['metrics_count'] = metrics.get('total_metrics', 0)
            elif name == 'accessibility':
                report = module.get_accessibility_report()
                diagnostics['modules'][name]['compliance_level'] = report.get('compliance_level', 'unknown')

        return diagnostics

    def get_search_manager(self) -> SearchManager:
        """Get search manager instance."""
        return self._search_manager

    def get_ui_state_manager(self) -> UIStateManager:
        """Get UI state manager instance."""
        return self._ui_state_manager

    def get_ui_styling(self) -> UIStyling:
        """Get UI styling instance."""
        return self._ui_styling

    def get_performance_monitor(self) -> PerformanceMonitor:
        """Get performance monitor instance."""
        return self._performance_monitor

    def get_accessibility_manager(self) -> AccessibilityManager:
        """Get accessibility manager instance."""
        return self._accessibility_manager

    def get_i18n_manager(self) -> I18nManager:
        """Get i18n manager instance."""
        return self._i18n_manager

    def get_responsive_manager(self) -> ResponsiveManager:
        """Get responsive manager instance."""
        return self._responsive_manager

    def reset_integration(self):
        """Reset integration to default state."""
        with self._lock:
            self._initialized = False
            self._status = IntegrationStatus()

            # Reset individual modules
            if self._search_manager:
                self._search_manager.clear_cache()
            if self._ui_state_manager:
                self._ui_state_manager.reset_state()
            if self._performance_monitor:
                self._performance_monitor.clear_metrics()

            logger.info("UI/UX Integration reset to default state")

    def __del__(self):
        """Clean up resources."""
        try:
            if self._performance_monitor:
                self._performance_monitor.stop_background_worker()
            logger.info("UI/UX Integration cleanup completed")
        except Exception:
            pass

# Singleton instance for easy access
_integration_instance = None

def get_integration() -> UIXIntegration:
    """Get the singleton integration instance."""
    global _integration_instance
    if _integration_instance is None:
        _integration_instance = UIXIntegration()
    return _integration_instance

def initialize_ui_ux_integration() -> UIXIntegration:
    """Initialize and return the UI/UX integration instance."""
    return get_integration()

# Convenience functions for common integration tasks
def get_integration_status() -> IntegrationStatus:
    """Get current integration status."""
    return get_integration().get_status()

def get_integration_dashboard() -> Dict[str, Any]:
    """Get comprehensive integration dashboard."""
    return get_integration().get_integration_dashboard()

def apply_ui_ux_optimizations() -> bool:
    """Apply UI/UX optimizations."""
    return get_integration().apply_optimizations()

def run_ui_ux_diagnostics() -> Dict[str, Any]:
    """Run UI/UX diagnostics."""
    return get_integration().run_diagnostics()

# Integration test function
def test_integration() -> Dict[str, Any]:
    """Test the UI/UX integration."""
    integration = get_integration()

    test_results = {
        'initialized': integration.is_initialized(),
        'modules_loaded': integration.get_status().modules_loaded,
        'errors': len(integration.get_status().errors),
        'performance_metrics_available': len(integration.get_performance_metrics()) > 0,
        'accessibility_report_available': len(integration.get_accessibility_report()) > 0,
        'diagnostics_available': len(integration.run_diagnostics()) > 0
    }

    # Test individual module access
    try:
        search = integration.get_search_manager()
        state = integration.get_ui_state_manager()
        styling = integration.get_ui_styling()
        perf = integration.get_performance_monitor()
        access = integration.get_accessibility_manager()
        i18n = integration.get_i18n_manager()
        resp = integration.get_responsive_manager()

        test_results['module_access'] = all([
            search is not None,
            state is not None,
            styling is not None,
            perf is not None,
            access is not None,
            i18n is not None,
            resp is not None
        ])
    except Exception:
        test_results['module_access'] = False

    return test_results

# Auto-initialize on import
if __name__ == "__main__":
    # When run directly, initialize and show status
    integration = initialize_ui_ux_integration()
    status = integration.get_status()
    print(f"UI/UX Integration Status: {status.initialized} ({status.modules_loaded} modules)")
    if status.errors:
        print(f"Errors: {status.errors}")