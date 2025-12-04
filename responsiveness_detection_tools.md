# Tools and Techniques for Detecting Application Responsiveness and Hitching

## Overview
Application responsiveness refers to how quickly an application responds to user input, while hitching refers to temporary freezes or delays that make an application feel unresponsive. Here are various tools and techniques to detect these issues in Python applications like dbutils.

## 1. Event Loop Monitoring (for GUI Applications)

### Qt-specific Monitoring
For Qt applications like the dbutils GUI:
```python
import time
from PySide6.QtCore import QTimer

class ResponsivenessMonitor:
    def __init__(self, app):
        self.app = app
        self.last_check = time.time()
        self.hitch_threshold = 0.1  # 100ms threshold for hitches
        
        # Timer to periodically check event loop responsiveness
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self.check_responsiveness)
        self.monitor_timer.start(50)  # Check every 50ms
        
    def check_responsiveness(self):
        now = time.time()
        time_since_last = now - self.last_check
        
        if time_since_last > self.hitch_threshold:
            print(f"HITCH DETECTED: {time_since_last:.3f}s delay")
        
        self.last_check = now
```

### Textual-specific Monitoring
For Textual TUI applications:
```python
from rich.text import Text
from textual.app import App
from textual import work
import time

class ResponsivenessApp(App):
    def __init__(self):
        super().__init__()
        self.last_update = time.time()
        self.hitch_threshold = 0.1
        
    async def on_idle(self):
        now = time.time()
        delay = now - self.last_update
        
        if delay > self.hitch_threshold:
            self.notify(f"Hitch detected: {delay:.3f}s delay")
        
        self.last_update = now
```

## 2. Thread-Based Monitoring

### Watchdog Thread
Monitor the main thread for hitches:
```python
import threading
import time
import signal

class MainThreadMonitor:
    def __init__(self, hitch_threshold=0.1):
        self.hitch_threshold = hitch_threshold
        self.main_thread_alive = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
    def _monitor_loop(self):
        while self.main_thread_alive:
            signal_received = threading.Event()
            start_time = time.time()
            
            # Wait for a signal from main thread
            if not signal_received.wait(self.hitch_threshold):
                # No signal within threshold - hitch detected
                print(f"HITCH: Main thread unresponsive for >{self.hitch_threshold}s")
            
            time.sleep(0.01)  # Check every 10ms
    
    def signal_main_thread_alive(self):
        # Signal that main thread is responsive
        pass
```

## 3. Profiling-Based Detection

### Using cProfile for Responsiveness
```python
import cProfile
import time
from contextlib import contextmanager

@contextmanager
def detect_long_running_functions(timeout=0.1):
    """Context manager that checks for functions running longer than timeout."""
    start = time.perf_counter()
    yield
    duration = time.perf_counter() - start
    
    if duration > timeout:
        print(f"LONG OPERATION DETECTED: {duration:.3f}s")
```

## 4. Input Latency Measurement

Monitor time between user input and response:
```python
import time
from dataclasses import dataclass

@dataclass
class InputResponse:
    input_time: float
    response_time: float
    input_type: str
    latency: float

class InputLatencyMonitor:
    def __init__(self):
        self.pending_inputs = {}
        self.latency_history = []
        self.threshold = 0.1  # 100ms
        
    def record_input(self, input_id, input_type):
        """Call when input is received."""
        self.pending_inputs[input_id] = {
            'time': time.time(),
            'type': input_type
        }
    
    def record_response(self, input_id):
        """Call when response is completed."""
        if input_id in self.pending_inputs:
            input_record = self.pending_inputs.pop(input_id)
            response_time = time.time()
            latency = response_time - input_record['time']
            
            record = InputResponse(
                input_time=input_record['time'],
                response_time=response_time,
                input_type=input_record['type'],
                latency=latency
            )
            
            self.latency_history.append(record)
            
            if latency > self.threshold:
                print(f"HI-RESPONSE: Input {input_record['type']} took {latency:.3f}s")
```

## 5. Frame Rate Monitoring (for GUI Applications)

```python
import time
from collections import deque

class FrameRateMonitor:
    def __init__(self, window_size=60):
        self.frame_times = deque(maxlen=window_size)
        self.window_size = window_size
        
    def mark_frame(self):
        """Call at the beginning of each frame/update cycle."""
        current_time = time.time()
        
        if self.frame_times:
            frame_time = current_time - self.frame_times[-1]
            self.frame_times.append(current_time)
            
            if len(self.frame_times) > 1:
                avg_frame_time = (self.frame_times[-1] - self.frame_times[0]) / len(self.frame_times)
                fps = 1.0 / avg_frame_time if avg_frame_time > 0 else 0
                
                # Detect hitches (frame time > 3x average)
                if frame_time > avg_frame_time * 3 and frame_time > 0.1:
                    print(f"HITCH: Frame took {frame_time:.3f}s")
        else:
            self.frame_times.append(current_time)
```

## 6. System-Level Monitoring

### Using psutil
```python
import psutil
import time

class SystemMonitor:
    def __init__(self):
        self.process = psutil.Process()
        self.last_cpu_time = (0, 0)  # (user, system)
        self.last_time = time.time()
        
    def check_responsiveness(self):
        # Get current process info
        current_time = time.time()
        cpu_times = self.process.cpu_times()
        
        # Calculate actual CPU usage since last check
        cpu_delta = (cpu_times.user - self.last_cpu_time[0]) + (cpu_times.system - self.last_cpu_time[1])
        time_delta = current_time - self.last_time
        
        if time_delta > 0:
            cpu_usage = cpu_delta / time_delta
            if cpu_usage > 0.9 and time_delta < 0.05:  # High CPU + short interval = likely blocking
                print(f"Potential hitch: High CPU usage ({cpu_usage:.2f})")
        
        self.last_cpu_time = (cpu_times.user, cpu_times.system)
        self.last_time = current_time
```

## 7. Database Query Monitoring

For monitoring database responsiveness in dbutils:
```python
import time
from contextlib import contextmanager

class QueryMonitor:
    def __init__(self, slow_query_threshold=1.0):
        self.slow_query_threshold = slow_query_threshold
        self.query_history = []
        
    @contextmanager
    def timed_query(self, query, query_type="SELECT"):
        start_time = time.time()
        result = None
        error = None
        
        try:
            result = yield  # Execute the actual query
        except Exception as e:
            error = str(e)
        finally:
            end_time = time.time()
            duration = end_time - start_time
            
            query_record = {
                'query': query,
                'type': query_type,
                'duration': duration,
                'error': error,
                'timestamp': start_time
            }
            
            self.query_history.append(query_record)
            
            if duration > self.slow_query_threshold:
                print(f"SLOW QUERY: {query_type} took {duration:.3f}s")
            
            if error:
                print(f"QUERY ERROR: {error} in {duration:.3f}s")
        
        return result
```

## 8. Custom Responsiveness Decorator

```python
import functools
import time
import asyncio

def monitor_responsiveness(threshold=0.1, name="Operation"):
    """Decorator to monitor function responsiveness."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = func(*args, **kwargs)
            duration = time.perf_counter() - start
            
            if duration > threshold:
                print(f"HI-RESPONSE: {name} took {duration:.3f}s")
            
            return result
        return wrapper
    
    # Handle async functions
    def async_decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = await func(*args, **kwargs)
            duration = time.perf_counter() - start
            
            if duration > threshold:
                print(f"HI-RESPONSE: {name} took {duration:.3f}s")
            
            return result
        return async_wrapper
    
    if asyncio.iscoroutinefunction(func):
        return async_decorator(func)
    else:
        return decorator(func)

# Usage:
@monitor_responsiveness(threshold=0.05, name="Table Search")
def search_tables(query):
    # Search operation
    pass
```

## 9. Third-Party Tools

### 1. py-spy
- Samples running Python programs to detect blocking operations
- Command: `py-spy top --pid <pid>` or `py-spy record -o profile.svg --pid <pid>`

### 2. Scalene
- CPU, memory, and GPU profiler that can detect responsiveness issues
- Command: `scalene your_script.py`

### 3. pytracing
- Distributed tracing library that can track request/response times
- Good for monitoring end-to-end responsiveness

### 4. Application Performance Monitoring (APM) Tools
- New Relic Python Agent
- Datadog APM
- Sentry Performance Monitoring

## 10. Platform-Specific Tools

### Linux
- `htop` / `top` for real-time process monitoring
- `strace -p <pid>` to trace system calls that might block
- `perf` for performance profiling

### Windows
- Process Monitor (ProcMon) to see file/registry/registry activity
- Windows Performance Toolkit (wpr.exe)

### macOS
- Activity Monitor
- Instruments application for detailed profiling

These tools and techniques provide comprehensive coverage for detecting responsiveness issues and hitches in the dbutils application, from high-level UI monitoring down to low-level system performance analysis.