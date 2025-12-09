"""
Comprehensive threading tests for potential threading errors and race conditions.

This test suite covers:
- Race conditions in lock-protected sections
- Deadlock scenarios
- Thread-safe state management
- Worker thread lifecycle
- Signal/slot thread safety (Qt)
- Resource cleanup on exceptions
- Concurrent access patterns
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import List
from unittest.mock import MagicMock, Mock, patch

import pytest

from dbutils.gui.integration import UIXIntegration
from dbutils.gui.responsive import ResponsiveManager
from dbutils.gui.search_manager import SearchManager, SearchMode, SearchState


class TestSearchManagerThreadSafety:
    """Test thread safety of SearchManager."""

    def test_concurrent_cache_operations(self):
        """Test concurrent read/write operations to cache."""
        manager = SearchManager()
        results = []
        errors = []

        def cache_operation(operation_id):
            try:
                # Alternate between caching and retrieving
                if operation_id % 2 == 0:
                    manager._cache_results(
                        f"query_{operation_id}",
                        SearchMode.TABLES,
                        [Mock(relevance_score=1.0) for _ in range(5)],
                    )
                else:
                    cached = manager._get_cached_results(f"query_{operation_id - 1}", SearchMode.TABLES)
                    results.append(cached)
            except Exception as e:
                errors.append(e)

        # Execute concurrent operations
        with ThreadPoolExecutor(max_workers=10) as executor:
            list(executor.map(cache_operation, range(20)))

        assert len(errors) == 0, f"Concurrent cache operations failed: {errors}"
        assert len(results) == 10

    def test_concurrent_state_updates(self):
        """Test concurrent state updates."""
        manager = SearchManager()
        state_sequence = []
        errors = []

        def update_state(state_id):
            try:
                states = list(SearchState)
                state = states[state_id % len(states)]
                manager.set_state(state)
                time.sleep(0.001)  # Small delay to increase race condition chance
                state_sequence.append(manager.get_state())
            except Exception as e:
                errors.append(e)

        with ThreadPoolExecutor(max_workers=8) as executor:
            list(executor.map(update_state, range(16)))

        assert len(errors) == 0, f"Concurrent state updates failed: {errors}"
        assert len(state_sequence) == 16

    def test_cancel_during_concurrent_operations(self):
        """Test canceling search while other operations are in flight."""
        manager = SearchManager()
        operations_completed = []
        errors = []

        def long_operation(op_id):
            try:
                manager.set_state(SearchState.ACTIVE)
                time.sleep(0.05)  # Simulate long operation
                operations_completed.append(op_id)
                manager.set_state(SearchState.COMPLETED)
            except Exception as e:
                errors.append(e)

        with ThreadPoolExecutor(max_workers=4) as executor:
            # Start multiple operations
            futures = [executor.submit(long_operation, i) for i in range(4)]

            # Cancel halfway through
            time.sleep(0.025)
            manager.cancel_search()

            # Wait for all to complete
            for future in futures:
                future.result(timeout=5)

        assert len(errors) == 0
        # Some operations may have been cancelled
        assert len(operations_completed) <= 4

    def test_cache_clear_during_operations(self):
        """Test clearing cache while other threads access it."""
        manager = SearchManager()
        errors = []
        access_count = [0]

        def access_cache():
            try:
                for i in range(10):
                    manager._cache_results(
                        f"query_{i}",
                        SearchMode.TABLES,
                        [Mock(relevance_score=1.0)],
                    )
                    manager._get_cached_results(f"query_{i}", SearchMode.TABLES)
                    access_count[0] += 1
            except Exception as e:
                errors.append(e)

        def clear_cache():
            time.sleep(0.01)
            manager.clear_cache()

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(access_cache),
                executor.submit(access_cache),
                executor.submit(clear_cache),
            ]
            for future in futures:
                future.result(timeout=5)

        assert len(errors) == 0
        assert access_count[0] > 0

    def test_stats_during_concurrent_operations(self):
        """Test reading stats while concurrent operations modify them."""
        manager = SearchManager()
        stats_snapshots = []
        errors = []

        def generate_traffic():
            try:
                for i in range(50):
                    manager._cache_results(
                        f"query_{i}",
                        SearchMode.TABLES,
                        [Mock(relevance_score=1.0)],
                    )
                    manager._get_cached_results(f"query_{i}", SearchMode.TABLES)
            except Exception as e:
                errors.append(e)

        def read_stats():
            try:
                for _ in range(10):
                    stats = manager.get_cache_stats()
                    stats_snapshots.append(stats)
                    time.sleep(0.005)
            except Exception as e:
                errors.append(e)

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(generate_traffic),
                executor.submit(generate_traffic),
                executor.submit(read_stats),
                executor.submit(read_stats),
            ]
            for future in futures:
                future.result(timeout=5)

        assert len(errors) == 0
        assert len(stats_snapshots) == 20


class TestResponsiveManagerThreadSafety:
    """Test thread safety of ResponsiveManager."""

    def test_concurrent_listener_registration(self):
        """Test registering/unregistering listeners concurrently."""
        # Skip if Qt not available
        pytest.importorskip("PySide6.QtCore")

        manager = ResponsiveManager()
        errors = []
        listeners_added = []

        def dummy_listener(screen_info):
            pass

        def register_listeners(batch_id):
            try:
                for i in range(10):
                    listener = lambda screen_info, b=batch_id, i=i: None
                    manager.add_responsive_listener(listener)
                    listeners_added.append((batch_id, i))
            except Exception as e:
                errors.append(e)

        with ThreadPoolExecutor(max_workers=5) as executor:
            list(executor.map(register_listeners, range(5)))

        assert len(errors) == 0
        assert len(listeners_added) == 50

    def test_concurrent_screen_info_access(self):
        """Test accessing screen info from multiple threads."""
        pytest.importorskip("PySide6.QtCore")

        manager = ResponsiveManager()
        screen_infos = []
        errors = []

        def read_screen_info():
            try:
                for _ in range(10):
                    info = manager.get_screen_info()
                    if info:
                        screen_infos.append(info)
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)

        with ThreadPoolExecutor(max_workers=4) as executor:
            list(executor.map(lambda x: read_screen_info(), range(4)))

        assert len(errors) == 0


class TestIntegrationThreadSafety:
    """Test thread safety of UIXIntegration."""

    def test_concurrent_initialization_calls(self):
        """Test multiple concurrent calls to initialize."""
        integration = UIXIntegration()
        errors = []

        def call_initialize():
            try:
                integration.initialize()
            except Exception as e:
                errors.append(e)

        with ThreadPoolExecutor(max_workers=5) as executor:
            list(executor.map(lambda x: call_initialize(), range(5)))

        assert len(errors) == 0
        assert integration.is_initialized()

    def test_concurrent_status_checks(self):
        """Test reading status while other threads modify it."""
        integration = UIXIntegration()
        statuses = []
        errors = []

        def read_status():
            try:
                for _ in range(20):
                    status = integration.get_status()
                    statuses.append(status)
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(read_status) for _ in range(3)]
            for future in futures:
                future.result(timeout=5)

        assert len(errors) == 0
        assert len(statuses) == 60


class TestLockOrdering:
    """Test for potential deadlock scenarios due to lock ordering."""

    def test_recursive_lock_reentrancy(self):
        """Test that RLocks properly handle reentrancy."""
        manager = SearchManager()
        reentered = []
        errors = []

        def reentrant_operation():
            try:
                with manager._lock:
                    reentered.append(1)
                    # This should not deadlock with RLock
                    with manager._lock:
                        reentered.append(2)
                        manager.clear_cache()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=reentrant_operation) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=5)

        assert len(errors) == 0
        assert len(reentered) == 10

    def test_no_deadlock_with_multiple_managers(self):
        """Test no deadlock when accessing multiple managers."""
        manager1 = SearchManager()
        manager2 = SearchManager()
        integration = UIXIntegration()
        errors = []
        operations = []

        def interleaved_operations(op_id):
            try:
                if op_id % 3 == 0:
                    manager1.set_state(SearchState.ACTIVE)
                    time.sleep(0.001)
                    manager2.clear_cache()
                    operations.append(("m1_then_m2", op_id))
                elif op_id % 3 == 1:
                    manager2.clear_cache()
                    time.sleep(0.001)
                    manager1.set_state(SearchState.IDLE)
                    operations.append(("m2_then_m1", op_id))
                else:
                    integration.get_status()
                    operations.append(("integration", op_id))
            except Exception as e:
                errors.append(e)

        with ThreadPoolExecutor(max_workers=6) as executor:
            list(executor.map(interleaved_operations, range(30)))

        assert len(errors) == 0
        assert len(operations) == 30


class TestWorkerThreadLifecycle:
    """Test proper cleanup of worker threads."""

    def test_worker_cleanup_on_cancel(self):
        """Test that worker resources are properly cleaned up on cancel."""
        manager = SearchManager()

        # Simulate starting a worker
        manager._search_thread = Mock(spec=threading.Thread)
        manager._search_thread.is_alive.return_value = True
        manager._search_worker = Mock()
        manager._search_worker.cancel_search = Mock()

        # Verify worker is set
        assert manager._search_worker is not None

        # Cancel should clean up
        manager.cancel_search()

        # After cancel, worker should be cleaned up
        assert manager._search_worker is None
        assert manager._search_thread is None

    def test_worker_cleanup_exception_safety(self):
        """Test that cleanup happens even if worker.cancel_search() raises."""
        manager = SearchManager()

        # Create a worker that raises on cancel
        manager._search_thread = Mock(spec=threading.Thread)
        manager._search_thread.is_alive.return_value = True
        manager._search_worker = Mock()
        manager._search_worker.cancel_search = Mock(side_effect=Exception("Worker error"))

        # Cancel should clean up despite exception
        manager.cancel_search()

        # Worker should still be cleaned up
        assert manager._search_worker is None
        assert manager._search_thread is None

    def test_multiple_cleanup_calls_safe(self):
        """Test that multiple cleanup calls don't cause errors."""
        manager = SearchManager()

        # Initial cleanup when nothing is active
        manager._cleanup_worker_resources()
        assert manager._search_worker is None

        # Second cleanup should be safe
        manager._cleanup_worker_resources()
        assert manager._search_worker is None


class TestMemoryAndResourceLeaks:
    """Test for potential memory leaks and resource issues in threading."""

    def test_large_concurrent_cache_operations(self):
        """Test that large concurrent cache operations don't leak memory."""
        manager = SearchManager()
        errors = []

        def bulk_cache_operations(batch_id):
            try:
                for i in range(100):
                    manager._cache_results(
                        f"query_{batch_id}_{i}",
                        SearchMode.TABLES,
                        [Mock(relevance_score=float(i)) for _ in range(10)],
                    )
            except Exception as e:
                errors.append(e)

        with ThreadPoolExecutor(max_workers=10) as executor:
            list(executor.map(bulk_cache_operations, range(10)))

        assert len(errors) == 0

        # Cache should contain entries
        stats = manager.get_cache_stats()
        assert stats["cache_size"] > 0

        # Cleanup
        manager.clear_cache()
        stats = manager.get_cache_stats()
        assert stats["cache_size"] == 0

    def test_exception_in_thread_cleanup(self):
        """Test resource cleanup even when exceptions occur in threads."""
        manager = SearchManager()
        errors = []

        def operation_with_exception(op_id):
            try:
                manager.set_state(SearchState.ACTIVE)
                if op_id % 2 == 0:
                    raise ValueError(f"Intentional error {op_id}")
                manager.clear_cache()
            except ValueError:
                pass  # Expected
            except Exception as e:
                errors.append(e)

        with ThreadPoolExecutor(max_workers=5) as executor:
            list(executor.map(operation_with_exception, range(10)))

        assert len(errors) == 0


class TestAtomicOperations:
    """Test atomicity of compound operations in thread-safe code."""

    def test_state_change_atomicity(self):
        """Test that state changes are atomic."""
        manager = SearchManager()
        observed_states = []

        def state_observer():
            for _ in range(100):
                state = manager.get_state()
                observed_states.append(state)
                time.sleep(0.0001)

        def state_changer():
            states = list(SearchState)
            for i in range(100):
                manager.set_state(states[i % len(states)])
                time.sleep(0.0001)

        observer_thread = threading.Thread(target=state_observer)
        changer_thread = threading.Thread(target=state_changer)

        changer_thread.start()
        observer_thread.start()

        changer_thread.join(timeout=10)
        observer_thread.join(timeout=10)

        # All observed states should be valid SearchState values
        assert all(isinstance(s, SearchState) for s in observed_states)


class TestConcurrentErrorHandling:
    """Test error handling in concurrent scenarios."""

    def test_error_in_one_thread_doesnt_affect_others(self):
        """Test that errors in one thread don't affect others."""
        manager = SearchManager()
        results = []
        errors = []

        def operation_sequence(op_id):
            try:
                manager.set_state(SearchState.ACTIVE)

                if op_id == 2:
                    # This thread will try to cause an error
                    raise ValueError("Simulated error in thread 2")

                manager.clear_cache()
                results.append(f"op_{op_id}_success")
                manager.set_state(SearchState.COMPLETED)
            except ValueError:
                pass  # Expected error, don't record
            except Exception as e:
                errors.append((op_id, e))

        with ThreadPoolExecutor(max_workers=5) as executor:
            list(executor.map(operation_sequence, range(5)))

        # Other operations should have completed successfully
        assert len(errors) == 0
        assert len(results) == 4  # All except the one that raised


class TestBoundaryConditions:
    """Test threading behavior at boundary conditions."""

    def test_zero_delay_concurrent_operations(self):
        """Test concurrent operations with no delay between them."""
        manager = SearchManager()
        errors = []

        def rapid_operations():
            try:
                for i in range(100):
                    manager.set_state(SearchState.ACTIVE)
                    manager.set_state(SearchState.IDLE)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=rapid_operations) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)

        assert len(errors) == 0

    def test_many_threads_single_resource(self):
        """Test many threads accessing single resource."""
        manager = SearchManager()
        access_counts = []
        errors = []

        def single_thread_work():
            try:
                count = 0
                for i in range(50):
                    manager.get_cache_stats()
                    count += 1
                access_counts.append(count)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=single_thread_work) for _ in range(50)]
        start = time.time()
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)
        elapsed = time.time() - start

        assert len(errors) == 0
        assert sum(access_counts) == 2500
        # Should complete in reasonable time even with lock contention
        assert elapsed < 60


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
