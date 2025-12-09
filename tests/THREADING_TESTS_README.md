# Threading Tests Documentation

## Overview

This directory contains comprehensive test suites for detecting and preventing threading errors in the dbutils database browser application. These tests verify thread safety, race conditions, deadlocks, and proper resource cleanup in concurrent scenarios.

## Test Files

### 1. `test_threading_errors.py` (20 tests)
Core threading safety tests covering general Python threading patterns used throughout the application.

**Test Classes:**

- **TestSearchManagerThreadSafety** (5 tests)
  - `test_concurrent_cache_operations`: Verifies cache is thread-safe under concurrent read/write
  - `test_concurrent_state_updates`: Tests state machine safety with multiple threads
  - `test_cancel_during_concurrent_operations`: Validates cancellation works correctly during active work
  - `test_cache_clear_during_operations`: Ensures cache clearing doesn't corrupt state
  - `test_stats_during_concurrent_operations`: Tests stats collection during concurrent ops

- **TestResponsiveManagerThreadSafety** (2 tests)
  - `test_concurrent_listener_registration`: Verifies listener list is thread-safe
  - `test_concurrent_screen_info_access`: Tests screen info access from multiple threads

- **TestIntegrationThreadSafety** (2 tests)
  - `test_concurrent_initialization_calls`: Multiple calls to initialize don't cause issues
  - `test_concurrent_status_checks`: Status reading during state changes

- **TestLockOrdering** (2 tests)
  - `test_recursive_lock_reentrancy`: RLock properly handles reentrant access
  - `test_no_deadlock_with_multiple_managers`: Multiple locks don't deadlock

- **TestWorkerThreadLifecycle** (3 tests)
  - `test_worker_cleanup_on_cancel`: Cleanup happens properly on cancel
  - `test_worker_cleanup_exception_safety`: Cleanup succeeds even if worker raises
  - `test_multiple_cleanup_calls_safe`: Multiple cleanups don't cause issues

- **TestMemoryAndResourceLeaks** (2 tests)
  - `test_large_concurrent_cache_operations`: No memory leaks with heavy concurrent ops
  - `test_exception_in_thread_cleanup`: Resources cleaned up even with exceptions

- **TestAtomicOperations** (1 test)
  - `test_state_change_atomicity`: State changes are atomic

- **TestConcurrentErrorHandling** (1 test)
  - `test_error_in_one_thread_doesnt_affect_others`: Isolation of errors

- **TestBoundaryConditions** (2 tests)
  - `test_zero_delay_concurrent_operations`: Stress test with no delays
  - `test_many_threads_single_resource`: Many threads accessing same resource

### 2. `test_threading_qt.py` (25 tests)
Qt-specific threading tests for signal/slot safety and worker thread management.

**Test Classes:**

- **TestWorkerSignals** (4 tests)
  - `test_worker_signal_attributes`: Verifies all expected signals exist
  - `test_search_worker_signal_emission`: Tests signal emission
  - `test_data_loader_worker_signal_attributes`: DataLoaderWorker signals
  - `test_table_contents_worker_signal_attributes`: TableContentsWorker signals

- **TestWorkerThreadAffinity** (3 tests)
  - `test_worker_moves_to_thread`: Workers properly move to threads
  - `test_multiple_workers_separate_threads`: Multiple workers in separate threads
  - `test_worker_signal_in_correct_thread`: Signals emitted from correct context

- **TestWorkerLifecycle** (4 tests)
  - `test_worker_initialization`: Workers initialize properly
  - `test_worker_cancel_sets_flag`: Cancel flag works correctly
  - `test_data_loader_worker_initialization`: DataLoaderWorker setup
  - `test_table_contents_worker_initialization`: TableContentsWorker setup

- **TestCrossThreadSignalConnections** (2 tests)
  - `test_cross_thread_signal_connection`: Signals work across thread boundaries
  - `test_auto_vs_direct_connection`: Different connection types work

- **TestWorkerErrorHandling** (3 tests)
  - `test_worker_error_signal`: Error signals work correctly
  - `test_worker_cancel_doesnt_crash`: Canceling is safe
  - `test_exception_in_worker_run`: Exceptions handled gracefully

- **TestWorkerCleanup** (2 tests)
  - `test_worker_cleanup_on_thread_finish`: Proper cleanup when thread ends
  - `test_multiple_worker_cleanup`: Multiple workers cleaned up correctly

- **TestWorkerProgressUpdates** (2 tests)
  - `test_data_loader_progress_signal`: Progress signals work
  - `test_progress_updates_sequential`: Progress updates in order

- **TestWorkerStateTransitions** (2 tests)
  - `test_search_worker_state_transitions`: State transitions correct
  - `test_worker_reusability_after_cancel`: Worker usable after cancel

- **TestSignalSlotConsistency** (2 tests)
  - `test_results_ready_signal_parameters`: Signal params are correct type
  - `test_error_signal_parameters`: Error signal params correct

- **TestWorkerThreadSafety** (1 test)
  - `test_worker_slot_from_different_thread`: Slots callable from other threads

### 3. `test_threading_helpers.py` (Utility Module)
Helper utilities for testing threading scenarios.

**Key Classes:**

- **ThreadingTestHelper**: High-level utilities for concurrent testing
  - `run_concurrent()`: Run function in multiple threads
  - `detect_race_condition()`: Attempt to detect race conditions
  - `assert_no_timeout()`: Context manager for timeout detection

- **DeadlockDetector**: Detect potential deadlocks
  - `run_with_timeout()`: Run with timeout detection
  - `test_no_deadlock()`: Check for deadlock

- **RaceConditionSimulator**: Simulate race conditions
  - `synchronized_threads()`: Run with barrier synchronization
  - `stress_test()`: Repeated calling to find issues

- **ThreadSafetyValidator**: Validate thread safety
  - `validate_atomic_operation()`: Check for atomic execution

- **MemoryLeakDetector**: Detect resource leaks
  - `check_thread_resource_cleanup()`: Verify cleanup on resource lifecycle

## Running the Tests

### Run all threading tests:
```bash
python3 -m pytest tests/test_threading_errors.py tests/test_threading_qt.py -v
```

### Run specific test class:
```bash
python3 -m pytest tests/test_threading_errors.py::TestSearchManagerThreadSafety -v
```

### Run specific test:
```bash
python3 -m pytest tests/test_threading_errors.py::TestSearchManagerThreadSafety::test_concurrent_cache_operations -v
```

### Run with coverage:
```bash
python3 -m pytest tests/test_threading_errors.py tests/test_threading_qt.py --cov=dbutils.gui --cov-report=html
```

### Run with stress testing (longer):
```bash
python3 -m pytest tests/test_threading_errors.py::TestBoundaryConditions -v --count=5
```

## What These Tests Cover

### Race Conditions
- **Cache operations**: Concurrent cache read/write without corruption
- **State updates**: Multiple threads updating state machine
- **Listener registration**: Adding/removing listeners concurrently
- **Statistics**: Reading stats while they're being updated

### Deadlocks
- **Lock ordering**: Multiple locks used in different orders
- **Reentrant access**: RLock properly handles recursive calls
- **Cross-manager access**: Multiple manager instances don't deadlock

### Resource Cleanup
- **Worker lifecycle**: Workers cleanup properly when cancelled
- **Exception safety**: Cleanup happens even when exceptions occur
- **Memory leaks**: No resource leaks with heavy concurrent ops

### Signal/Slot Safety (Qt-specific)
- **Thread affinity**: Signals/slots work across threads
- **Connection types**: Both auto and direct connections work
- **Parameter passing**: Signal parameters have correct types
- **Error signals**: Error handling works across threads

### Boundary Conditions
- **High concurrency**: Many threads accessing same resource
- **No delays**: Rapid operations don't cause issues
- **Large data**: Heavy concurrent operations don't leak memory

## Interpreting Test Results

### All tests pass ✓
Threading in your changes is safe. Deploy with confidence.

### Test timeouts
Likely deadlock detected. Check lock ordering and nested lock usage.

### Assertion failures
Race condition detected. Review the test output to find the specific issue.

### Memory growth
Potential memory leak in worker/thread cleanup. Check resource lifecycle.

## Common Issues and Solutions

### Deadlock (test times out)
**Cause**: Multiple locks acquired in different orders
**Solution**: Always acquire locks in same order, or use context managers

### Race condition (intermittent failures)
**Cause**: Unsynchronized access to shared state
**Solution**: Protect shared state with locks, use atomic operations where possible

### Signal not received
**Cause**: Signal emitted before slot connected, or thread affinity issue
**Solution**: Connect signals before starting threads, use Qt.ConnectionType.QueuedConnection for cross-thread

### Resource leak
**Cause**: Not calling cleanup, or cleanup blocked by deadlock
**Solution**: Use try/finally or context managers to ensure cleanup

## Adding New Tests

To add threading tests for new features:

1. Identify shared state/resources accessed from multiple threads
2. Add test to appropriate class in `test_threading_errors.py` or `test_threading_qt.py`
3. Use helper utilities from `test_threading_helpers.py`
4. Include both normal and error cases
5. Test boundary conditions with high thread counts

Example:
```python
def test_my_new_feature_thread_safety(self):
    """Test thread safety of new feature."""
    feature = MyNewFeature()
    errors = []
    
    def thread_work():
        try:
            feature.do_something()
        except Exception as e:
            errors.append(e)
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        list(executor.map(lambda x: thread_work(), range(10)))
    
    assert len(errors) == 0, f"Thread safety issues: {errors}"
```

## Test Statistics

- **Total Tests**: 45
- **Core Threading Tests**: 20
- **Qt-specific Tests**: 25
- **Expected Runtime**: < 2 seconds
- **Dependencies**: pytest, PySide6/PyQt6 (for Qt tests)

## CI/CD Integration

These tests should be run:
- ✓ On every commit (fast - < 2 sec)
- ✓ Before release (with stress testing)
- ✓ When modifying threading code
- ✓ When adding new shared state

Add to CI/CD pipeline:
```yaml
- name: Thread Safety Tests
  run: python3 -m pytest tests/test_threading_*.py -v
```

## References

- [Python Threading Best Practices](https://docs.python.org/3/library/threading.html)
- [Qt Threading Documentation](https://doc.qt.io/qt-6/qtcore-thread.html)
- [Race Condition Detection](https://en.wikipedia.org/wiki/Race_condition)
- [Deadlock Prevention](https://en.wikipedia.org/wiki/Deadlock)
