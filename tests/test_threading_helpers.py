"""
Threading test utilities and helpers for testing thread-safety and race conditions.
"""

import contextlib
import threading
import time
from typing import Callable, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor, Future


class ThreadingTestHelper:
    """Helper class for testing threading scenarios."""

    @staticmethod
    def run_concurrent(
        func: Callable,
        num_threads: int = 5,
        iterations: int = 10,
        timeout: float = 30.0,
    ) -> tuple[int, List[Exception]]:
        """
        Run a function concurrently in multiple threads.

        Args:
            func: Function to run in each thread
            num_threads: Number of concurrent threads
            iterations: Number of iterations per thread
            timeout: Maximum time to wait for completion

        Returns:
            Tuple of (successful_operations, errors)
        """
        errors = []
        successful = [0]

        def thread_work():
            for i in range(iterations):
                try:
                    func(i)
                    successful[0] += 1
                except Exception as e:
                    errors.append(e)

        threads = [threading.Thread(target=thread_work) for _ in range(num_threads)]

        start = time.time()
        for t in threads:
            t.start()

        for t in threads:
            elapsed = time.time() - start
            remaining = timeout - elapsed
            if remaining > 0:
                t.join(timeout=remaining)

        return successful[0], errors

    @staticmethod
    def detect_race_condition(
        func: Callable,
        num_iterations: int = 100,
        num_threads: int = 10,
    ) -> bool:
        """
        Try to detect race conditions by running concurrently.

        Returns True if a race condition (error) was detected.
        """
        _, errors = ThreadingTestHelper.run_concurrent(
            func,
            num_threads=num_threads,
            iterations=num_iterations // num_threads,
            timeout=10.0,
        )
        return len(errors) > 0

    @staticmethod
    @contextlib.contextmanager
    def assert_no_timeout(timeout_sec: float = 30.0):
        """Context manager that fails if block doesn't complete in time."""

        class TimeoutError(Exception):
            pass

        def timeout_handler():
            raise TimeoutError(f"Operation did not complete within {timeout_sec} seconds")

        timer = threading.Timer(timeout_sec, timeout_handler)
        timer.start()

        try:
            yield
        finally:
            timer.cancel()


class DeadlockDetector:
    """Detect potential deadlock scenarios."""

    def __init__(self, timeout: float = 5.0):
        self.timeout = timeout
        self.threads = []
        self.lock = threading.Lock()

    def run_with_timeout(self, func: Callable, *args, **kwargs) -> Any:
        """Run a function with timeout detection."""
        result = []
        error = []

        def target():
            try:
                result.append(func(*args, **kwargs))
            except Exception as e:
                error.append(e)

        thread = threading.Thread(target=target)
        thread.daemon = True
        thread.start()
        thread.join(timeout=self.timeout)

        if thread.is_alive():
            # Thread didn't complete - likely deadlock
            return None, TimeoutError(f"Deadlock detected: thread did not complete in {self.timeout}s")

        if error:
            return None, error[0]

        return result[0] if result else None, None

    def test_no_deadlock(self, func: Callable, *args, **kwargs) -> bool:
        """
        Test if a function completes without deadlock.

        Returns True if function completed successfully (no deadlock).
        """
        _, error = self.run_with_timeout(func, *args, **kwargs)
        return error is None


class RaceConditionSimulator:
    """Simulate and detect race conditions."""

    def __init__(self, barrier_count: int = 0):
        self.barrier = threading.Barrier(barrier_count) if barrier_count > 0 else None
        self.lock = threading.Lock()
        self.errors = []

    def synchronized_threads(self, func: Callable, num_threads: int = 5) -> List[Exception]:
        """
        Run function in synchronized threads (all start at same time).

        Returns list of errors that occurred.
        """
        self.barrier = threading.Barrier(num_threads)
        self.errors = []

        def synchronized_work():
            try:
                self.barrier.wait()  # Wait for all threads to be ready
                func()
            except Exception as e:
                with self.lock:
                    self.errors.append(e)

        threads = [threading.Thread(target=synchronized_work) for _ in range(num_threads)]

        for t in threads:
            t.start()

        for t in threads:
            t.join(timeout=10)

        return self.errors

    def stress_test(self, func: Callable, duration_sec: float = 5.0) -> List[Exception]:
        """
        Stress test a function by calling it repeatedly for duration.

        Returns list of errors that occurred.
        """
        self.errors = []
        stop_flag = threading.Event()

        def work_loop():
            while not stop_flag.is_set():
                try:
                    func()
                except Exception as e:
                    with self.lock:
                        self.errors.append(e)

        threads = [threading.Thread(target=work_loop) for _ in range(5)]

        for t in threads:
            t.start()

        time.sleep(duration_sec)
        stop_flag.set()

        for t in threads:
            t.join(timeout=2)

        return self.errors


class ThreadSafetyValidator:
    """Validate thread safety of operations."""

    @staticmethod
    def validate_atomic_operation(
        get_func: Callable,
        set_func: Callable,
        expected_values: List[Any],
        num_threads: int = 10,
    ) -> bool:
        """
        Validate that an operation is atomic by checking if inconsistent
        states can be observed.

        Returns True if operation appears to be atomic.
        """
        errors = []
        observed = []

        def read_thread():
            for _ in range(100):
                try:
                    value = get_func()
                    if value not in expected_values and value is not None:
                        errors.append(f"Inconsistent value observed: {value}")
                    observed.append(value)
                except Exception as e:
                    errors.append(str(e))

        def write_thread():
            for value in expected_values:
                try:
                    set_func(value)
                except Exception as e:
                    errors.append(str(e))

        readers = [threading.Thread(target=read_thread) for _ in range(num_threads // 2)]
        writers = [threading.Thread(target=write_thread) for _ in range(num_threads // 2)]

        threads = readers + writers
        for t in threads:
            t.start()

        for t in threads:
            t.join(timeout=10)

        return len(errors) == 0


class MemoryLeakDetector:
    """Detect potential memory leaks in threading code."""

    @staticmethod
    def check_thread_resource_cleanup(
        create_func: Callable,
        cleanup_func: Callable,
        iterations: int = 100,
    ) -> bool:
        """
        Check if resources are properly cleaned up after creating/destroying threads.

        Returns True if cleanup appears successful.
        """
        import gc

        initial_threads = threading.active_count()
        initial_objects = len(gc.get_objects())

        for _ in range(iterations):
            resource = create_func()
            cleanup_func(resource)

        # Force garbage collection
        gc.collect()
        time.sleep(0.1)  # Let threads finish

        final_threads = threading.active_count()
        final_objects = len(gc.get_objects())

        # Should be roughly the same (allow small variance)
        thread_delta = final_threads - initial_threads
        object_delta = final_objects - initial_objects

        return thread_delta <= 1 and object_delta < 1000  # Heuristic threshold


if __name__ == "__main__":
    # Example usage
    print("Threading Test Utilities Loaded")
