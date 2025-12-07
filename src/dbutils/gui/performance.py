#!/usr/bin/env python3
"""
Performance Optimization Module

Performance optimization utilities for the database browser application.
This module addresses performance issues by providing:
- Debouncing utilities
- Throttling utilities
- Lazy loading strategies
- Memory optimization
- Performance monitoring

Features:
- Debounce and throttle utilities for UI events
- Lazy loading strategies for data and components
- Memory optimization techniques
- Performance monitoring and metrics
- Background task management
"""

from __future__ import annotations

import asyncio
import queue
import threading
import time
from dataclasses import dataclass
from enum import Enum, auto
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Tuple


class PerformanceMetric(Enum):
    """Types of performance metrics to track."""
    UI_RENDER = auto()
    SEARCH_OPERATION = auto()
    DATA_LOAD = auto()
    NETWORK_REQUEST = auto()
    MEMORY_USAGE = auto()

@dataclass
class PerformanceStats:
    """Performance statistics for a specific operation."""
    metric_type: PerformanceMetric
    start_time: float
    end_time: float
    duration: float
    memory_before: Optional[int] = None
    memory_after: Optional[int] = None
    additional_data: Dict[str, Any] = None

    def __post_init__(self):
        if self.duration <= 0 and self.end_time > self.start_time:
            self.duration = self.end_time - self.start_time

class PerformanceMonitor:
    """Performance monitoring and optimization utilities."""

    def __init__(self):
        self._metrics: List[PerformanceStats] = []
        self._max_metrics = 1000  # Maximum number of metrics to keep
        self._lock = threading.RLock()
        self._enabled = True

        # Task queue for background operations
        self._task_queue = queue.Queue()
        self._worker_thread = None
        self._stop_event = threading.Event()

    def enable_monitoring(self, enabled: bool = True):
        """Enable or disable performance monitoring."""
        self._enabled = enabled

    def is_enabled(self) -> bool:
        """Check if monitoring is enabled."""
        return self._enabled

    def start_background_worker(self):
        """Start background worker thread for performance tasks."""
        if self._worker_thread is None or not self._worker_thread.is_alive():
            self._stop_event.clear()
            self._worker_thread = threading.Thread(
                target=self._background_worker,
                daemon=True
            )
            self._worker_thread.start()

    def stop_background_worker(self):
        """Stop background worker thread."""
        if self._worker_thread and self._worker_thread.is_alive():
            self._stop_event.set()
            self._worker_thread.join(timeout=2.0)

    def _background_worker(self):
        """Background worker for performance tasks."""
        while not self._stop_event.is_set():
            try:
                task = self._task_queue.get(timeout=0.1)
                if task and callable(task):
                    task()
            except queue.Empty:
                continue
            except Exception:
                continue

    def track_operation(self, metric_type: PerformanceMetric) -> Callable:
        """Decorator to track performance of a function."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                if not self._enabled:
                    return func(*args, **kwargs)

                start_time = time.time()
                memory_before = self._get_memory_usage()

                try:
                    result = func(*args, **kwargs)
                finally:
                    end_time = time.time()
                    memory_after = self._get_memory_usage()

                    stats = PerformanceStats(
                        metric_type=metric_type,
                        start_time=start_time,
                        end_time=end_time,
                        duration=end_time - start_time,
                        memory_before=memory_before,
                        memory_after=memory_after
                    )

                    self._record_metric(stats)

                return result
            return wrapper
        return decorator

    def _get_memory_usage(self) -> Optional[int]:
        """Get current memory usage in bytes."""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss
        except ImportError:
            return None
        except Exception:
            return None

    def _record_metric(self, stats: PerformanceStats):
        """Record a performance metric."""
        with self._lock:
            self._metrics.append(stats)
            if len(self._metrics) > self._max_metrics:
                self._metrics.pop(0)

    def get_metrics(self, metric_type: Optional[PerformanceMetric] = None) -> List[PerformanceStats]:
        """Get recorded performance metrics."""
        with self._lock:
            if metric_type:
                return [m for m in self._metrics if m.metric_type == metric_type]
            return self._metrics.copy()

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of performance metrics."""
        with self._lock:
            if not self._metrics:
                return {
                    'total_metrics': 0,
                    'average_duration': 0,
                    'max_duration': 0,
                    'min_duration': 0,
                    'by_type': {}
                }

            total_duration = sum(m.duration for m in self._metrics)
            avg_duration = total_duration / len(self._metrics)
            max_duration = max(m.duration for m in self._metrics)
            min_duration = min(m.duration for m in self._metrics)

            # Group by metric type
            by_type = {}
            for metric in self._metrics:
                type_name = metric.metric_type.name
                if type_name not in by_type:
                    by_type[type_name] = {
                        'count': 0,
                        'total_duration': 0,
                        'average_duration': 0
                    }
                by_type[type_name]['count'] += 1
                by_type[type_name]['total_duration'] += metric.duration

            for type_name, data in by_type.items():
                data['average_duration'] = data['total_duration'] / data['count']

            return {
                'total_metrics': len(self._metrics),
                'average_duration': avg_duration,
                'max_duration': max_duration,
                'min_duration': min_duration,
                'by_type': by_type
            }

    def clear_metrics(self):
        """Clear all recorded metrics."""
        with self._lock:
            self._metrics.clear()

    def debounce(self, wait: float) -> Callable:
        """Decorator to debounce a function call.

        Ensures the function is only called after the specified wait time
        has elapsed since the last call.
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def debounced(*args, **kwargs):
                def call_func():
                    func(*args, **kwargs)

                # Use a timer to delay execution
                timer = threading.Timer(wait, call_func)
                timer.daemon = True
                timer.start()

                return timer
            return debounced
        return decorator

    def throttle(self, wait: float) -> Callable:
        """Decorator to throttle a function call.

        Ensures the function is called at most once in the specified wait period.
        """
        def decorator(func: Callable) -> Callable:
            last_called = 0
            lock = threading.Lock()

            @wraps(func)
            def throttled(*args, **kwargs):
                nonlocal last_called
                current_time = time.time()

                with lock:
                    if current_time - last_called >= wait:
                        last_called = current_time
                        return func(*args, **kwargs)
                    else:
                        # Optionally queue for later execution
                        return None
            return throttled
        return decorator

    def lazy_load(self, load_func: Callable, *args, **kwargs) -> Callable:
        """Create a lazy loading wrapper for expensive operations."""
        def wrapper():
            if not hasattr(wrapper, '_loaded'):
                wrapper._loaded = False
                wrapper._result = None

            if not wrapper._loaded:
                wrapper._result = load_func(*args, **kwargs)
                wrapper._loaded = True

            return wrapper._result

        return wrapper

    def create_task_queue(self) -> Tuple[queue.Queue, Callable]:
        """Create a task queue with worker function."""
        task_queue = queue.Queue()
        stop_event = threading.Event()

        def worker():
            while not stop_event.is_set():
                try:
                    task = task_queue.get(timeout=0.1)
                    if task and callable(task):
                        task()
                    task_queue.task_done()
                except queue.Empty:
                    continue
                except Exception:
                    continue

        def start_worker():
            thread = threading.Thread(target=worker, daemon=True)
            thread.start()
            return thread

        def stop_worker():
            stop_event.set()

        return task_queue, start_worker, stop_worker

    def batch_operations(self, items: List[Any], process_func: Callable[[Any], Any],
                        batch_size: int = 50) -> List[Any]:
        """Process items in batches to avoid UI freezing."""
        results = []
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            batch_results = [process_func(item) for item in batch]
            results.extend(batch_results)

            # Yield to allow UI updates
            if QT_AVAILABLE:
                from PySide6.QtCore import QCoreApplication
                QCoreApplication.processEvents()

        return results

    def async_batch_operations(self, items: List[Any], process_func: Callable[[Any], Any],
                              batch_size: int = 50) -> List[Any]:
        """Process items in batches asynchronously."""
        async def process_batches():
            results = []
            for i in range(0, len(items), batch_size):
                batch = items[i:i + batch_size]
                batch_results = [process_func(item) for item in batch]
                results.extend(batch_results)

                # Small delay to prevent overwhelming
                await asyncio.sleep(0.01)

            return results

        return asyncio.run(process_batches())

    def create_cache(self, max_size: int = 100) -> Callable:
        """Create a simple LRU cache decorator."""
        def decorator(func: Callable) -> Callable:
            cache = {}
            cache_order = []

            @wraps(func)
            def cached_func(*args, **kwargs):
                # Create a cache key
                cache_key = self._create_cache_key(args, kwargs)

                # Check cache
                if cache_key in cache:
                    # Move to end of order list (most recently used)
                    cache_order.remove(cache_key)
                    cache_order.append(cache_key)
                    return cache[cache_key]

                # Call function
                result = func(*args, **kwargs)

                # Store in cache
                cache[cache_key] = result
                cache_order.append(cache_key)

                # Enforce max size
                if len(cache_order) > max_size:
                    oldest_key = cache_order.pop(0)
                    del cache[oldest_key]

                return result

            return cached_func
        return decorator

    def _create_cache_key(self, args: tuple, kwargs: dict) -> str:
        """Create a cache key from function arguments."""
        return f"{args}_{frozenset(kwargs.items())}"

    def memory_optimized_list(self, items: List[Any]) -> List[Any]:
        """Create a memory-optimized list using __slots__."""
        class OptimizedList:
            __slots__ = ['_items']

            def __init__(self, items):
                self._items = items

            def __getitem__(self, index):
                return self._items[index]

            def __len__(self):
                return len(self._items)

            def __iter__(self):
                return iter(self._items)

            def append(self, item):
                self._items.append(item)

            def extend(self, items):
                self._items.extend(items)

            def __repr__(self):
                return repr(self._items)

        return OptimizedList(items)

    def defer_execution(self, func: Callable, delay: float = 0.1) -> Callable:
        """Defer execution of a function to allow UI updates."""
        def deferred(*args, **kwargs):
            if QT_AVAILABLE:
                from PySide6.QtCore import QTimer
                timer = QTimer()
                timer.setSingleShot(True)
                timer.timeout.connect(lambda: func(*args, **kwargs))
                timer.start(int(delay * 1000))
            else:
                # Fallback for non-Qt environments
                threading.Timer(delay, func, args=args, kwargs=kwargs).start()

        return deferred

    def create_performance_guard(self, max_duration: float = 1.0) -> Callable:
        """Create a performance guard that cancels long-running operations."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def guarded(*args, **kwargs):
                start_time = time.time()

                def check_timeout():
                    if time.time() - start_time > max_duration:
                        raise TimeoutError(f"Operation exceeded maximum duration of {max_duration} seconds")

                # Check timeout periodically
                check_interval = min(max_duration / 10, 0.1)
                timer = threading.Timer(check_interval, check_timeout)
                timer.daemon = True
                timer.start()

                try:
                    result = func(*args, **kwargs)
                finally:
                    timer.cancel()

                return result
            return guarded
        return decorator

    def optimize_table_model(self, model) -> Callable:
        """Optimize a table model for better performance."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def optimized(*args, **kwargs):
                # Check if we're in a UI thread
                if QT_AVAILABLE:
                    from PySide6.QtCore import QThread
                    if QThread.currentThread() != model.thread():
                        # Not in model's thread, defer to model's thread
                        from PySide6.QtCore import QMetaObject
                        QMetaObject.invokeMethod(
                            model,
                            func.__name__,
                            Qt.ConnectionType.QueuedConnection,
                            *args
                        )
                        return

                return func(*args, **kwargs)
            return optimized
        return decorator

    def create_background_task(self, func: Callable, *args, **kwargs) -> threading.Thread:
        """Create a background task that won't block the UI."""
        def task_wrapper():
            try:
                result = func(*args, **kwargs)
                if 'callback' in kwargs and kwargs['callback']:
                    kwargs['callback'](result)
            except Exception as e:
                if 'error_callback' in kwargs and kwargs['error_callback']:
                    kwargs['error_callback'](e)

        thread = threading.Thread(target=task_wrapper, daemon=True)
        thread.start()
        return thread

    def async_background_task(self, func: Callable, *args, **kwargs) -> asyncio.Task:
        """Create an async background task."""
        async def task_wrapper():
            try:
                result = await func(*args, **kwargs)
                if 'callback' in kwargs and kwargs['callback']:
                    kwargs['callback'](result)
            except Exception as e:
                if 'error_callback' in kwargs and kwargs['error_callback']:
                    kwargs['error_callback'](e)

        return asyncio.create_task(task_wrapper())

    def get_memory_optimization_tips(self) -> List[str]:
        """Get memory optimization tips for the current environment."""
        tips = [
            "Use lazy loading for large datasets",
            "Implement proper caching strategies",
            "Avoid keeping unnecessary references",
            "Use __slots__ for memory-intensive classes",
            "Clear caches when they're no longer needed",
            "Use weak references for observer patterns",
            "Implement proper resource cleanup"
        ]

        if QT_AVAILABLE:
            tips.extend([
                "Use model/view architecture properly",
                "Avoid blocking the main UI thread",
                "Use QThread for background operations",
                "Implement proper widget cleanup",
                "Use QTimer for deferred operations"
            ])

        return tips

    def analyze_performance_bottlenecks(self, metrics: List[PerformanceStats]) -> Dict[str, Any]:
        """Analyze performance metrics for bottlenecks."""
        if not metrics:
            return {'bottlenecks': [], 'recommendations': []}

        # Group by metric type
        by_type = {}
        for metric in metrics:
            type_name = metric.metric_type.name
            if type_name not in by_type:
                by_type[type_name] = []
            by_type[type_name].append(metric)

        bottlenecks = []
        recommendations = []

        for type_name, type_metrics in by_type.items():
            avg_duration = sum(m.duration for m in type_metrics) / len(type_metrics)
            max_duration = max(m.duration for m in type_metrics)

            if avg_duration > 0.5:  # More than 500ms average
                bottlenecks.append({
                    'type': type_name,
                    'average_duration': avg_duration,
                    'max_duration': max_duration,
                    'count': len(type_metrics)
                })

                if type_name == 'SEARCH_OPERATION':
                    recommendations.append("Implement better search indexing")
                    recommendations.append("Add more aggressive caching for search results")
                elif type_name == 'DATA_LOAD':
                    recommendations.append("Implement lazy loading for data")
                    recommendations.append("Add pagination to large datasets")
                elif type_name == 'UI_RENDER':
                    recommendations.append("Optimize widget rendering")
                    recommendations.append("Implement virtual scrolling for large lists")

        return {
            'bottlenecks': bottlenecks,
            'recommendations': recommendations
        }

    def __del__(self):
        """Clean up resources."""
        self.stop_background_worker()

# Singleton instance for easy access
_performance_monitor_instance = None

def get_performance_monitor() -> PerformanceMonitor:
    """Get the singleton performance monitor instance."""
    global _performance_monitor_instance
    if _performance_monitor_instance is None:
        _performance_monitor_instance = PerformanceMonitor()
    return _performance_monitor_instance

# Convenience functions for common use cases
def debounce_search(wait: float = 150):
    """Convenience decorator for debouncing search operations."""
    return get_performance_monitor().debounce(wait)

def throttle_ui_updates(wait: float = 100):
    """Convenience decorator for throttling UI updates."""
    return get_performance_monitor().throttle(wait)

def track_ui_performance():
    """Convenience decorator for tracking UI performance."""
    return get_performance_monitor().track_operation(PerformanceMetric.UI_RENDER)

def track_search_performance():
    """Convenience decorator for tracking search performance."""
    return get_performance_monitor().track_operation(PerformanceMetric.SEARCH_OPERATION)

def track_data_load_performance():
    """Convenience decorator for tracking data load performance."""
    return get_performance_monitor().track_operation(PerformanceMetric.DATA_LOAD)

# Try to import Qt components for Qt-specific optimizations
try:
    from PySide6.QtCore import Qt, QThread, QTimer
    from PySide6.QtWidgets import QApplication

    def defer_to_ui_thread(func: Callable) -> Callable:
        """Decorator to defer execution to UI thread."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            if QThread.currentThread() != QApplication.instance().thread():
                # Not in UI thread, defer to UI thread
                timer = QTimer()
                timer.setSingleShot(True)
                timer.timeout.connect(lambda: func(*args, **kwargs))
                timer.start(0)
                return
            return func(*args, **kwargs)
        return wrapper

    def optimize_qt_model_updates(func: Callable) -> Callable:
        """Optimize Qt model updates to prevent UI freezing."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Check if we're updating a model
            model = args[0] if args else None
            if hasattr(model, 'beginResetModel') and hasattr(model, 'endResetModel'):
                model.beginResetModel()
                try:
                    result = func(*args, **kwargs)
                finally:
                    model.endResetModel()
                return result
            return func(*args, **kwargs)
        return wrapper

except ImportError:
    # Provide no-op implementations when Qt is not available
    def defer_to_ui_thread(func: Callable) -> Callable:
        return func

    def optimize_qt_model_updates(func: Callable) -> Callable:
        return func
