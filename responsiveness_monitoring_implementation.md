# Implementation Approaches for Monitoring Responsiveness in dbutils

## Overview
The dbutils application already has sophisticated responsiveness mechanisms, particularly in the Qt GUI. This document outlines additional approaches to monitor and detect responsiveness issues, building on the existing architecture.

## 1. Integration with Existing Qt GUI Architecture

### 1.1 Event Loop Monitor
Add a responsiveness monitor that integrates with the existing Qt event loop:

```python
# File: src/dbutils/gui/responsiveness_monitor.py
import time
from PySide6.QtCore import QTimer, QObject, Signal
from typing import Callable, Optional


class QtResponsivenessMonitor(QObject):
    """Monitor Qt event loop responsiveness and detect hitches."""
    
    # Signals for hitch detection
    hitch_detected = Signal(float)  # duration in seconds
    responsiveness_updated = Signal(float)  # current responsiveness score
    
    def __init__(self, parent=None, hitch_threshold: float = 0.1):
        super().__init__(parent)
        self.hitch_threshold = hitch_threshold
        self.last_check_time = time.time()
        self.response_times = []
        
        # Timer to periodically check responsiveness
        self.monitor_timer = QTimer(self)
        self.monitor_timer.timeout.connect(self._check_responsiveness)
        self.monitor_timer.start(50)  # Check every 50ms
        
    def _check_responsiveness(self):
        """Check if the event loop is responsive."""
        current_time = time.time()
        time_since_last = current_time - self.last_check_time
        
        # Record response time (good or bad)
        self.response_times.append((time_since_last, time.time()))
        
        # Remove old measurements (keep last 5 seconds)
        cutoff_time = current_time - 5.0
        self.response_times = [(rt, t) for rt, t in self.response_times if t > cutoff_time]
        
        # Calculate responsiveness score (0-100, 100 being very responsive)
        if self.response_times:
            avg_response = sum(rt for rt, _ in self.response_times) / len(self.response_times)
            responsiveness_score = max(0, 100 - (avg_response * 500))  # Scale appropriately
            self.responsiveness_updated.emit(responsiveness_score)
        
        if time_since_last > self.hitch_threshold:
            self.hitch_detected.emit(time_since_last)
        
        self.last_check_time = current_time
    
    def get_average_response_time(self) -> float:
        """Get average response time over the last 5 seconds."""
        if not self.response_times:
            return 0.0
        return sum(rt for rt, _ in self.response_times) / len(self.response_times)


# Integration in qt_app.py
class DBBrowserApp(QMainWindow):
    def __init__(self):
        super().__init__()
        # ... existing initialization code ...
        
        # Add responsiveness monitor
        self.responsiveness_monitor = QtResponsivenessMonitor(self)
        self.responsiveness_monitor.hitch_detected.connect(self._on_hitch_detected)
        self.responsiveness_monitor.responsiveness_updated.connect(self._on_responsiveness_update)
    
    def _on_hitch_detected(self, duration: float):
        """Handle hitch detection."""
        print(f"HI-RESPONSE HITCH: UI unresponsive for {duration:.3f}s")
        # Could add visual indicator or logging to file
        
    def _on_responsiveness_update(self, score: float):
        """Handle responsiveness score update."""
        # Update status bar or log based on score
        if score < 70:  # Less responsive
            self.statusBar().showMessage(f"Responsiveness: {score:.1f}%", 2000)
```

### 1.2 Background Task Monitor
Monitor long-running background tasks:

```python
# File: src/dbutils/gui/task_monitor.py
import time
from PySide6.QtCore import QObject, Signal, QTimer
from typing import Dict, Any


class BackgroundTaskMonitor(QObject):
    """Monitor background tasks for responsiveness issues."""
    
    task_slow = Signal(str, float)  # task_name, duration
    task_completed = Signal(str, float)  # task_name, duration
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.active_tasks: Dict[str, float] = {}  # task_id -> start_time
        self.slow_task_threshold = 2.0  # seconds
        
        # Timer to check for slow tasks
        self.check_timer = QTimer(self)
        self.check_timer.timeout.connect(self._check_slow_tasks)
        self.check_timer.start(1000)  # Check every second
    
    def start_task(self, task_id: str):
        """Mark start of a background task."""
        self.active_tasks[task_id] = time.time()
    
    def complete_task(self, task_id: str):
        """Mark completion of a background task."""
        if task_id in self.active_tasks:
            duration = time.time() - self.active_tasks[task_id]
            del self.active_tasks[task_id]
            
            if duration > self.slow_task_threshold:
                self.task_slow.emit(task_id, duration)
            
            self.task_completed.emit(task_id, duration)
    
    def _check_slow_tasks(self):
        """Check for tasks that have been running too long."""
        current_time = time.time()
        slow_tasks = [
            (task_id, current_time - start_time)
            for task_id, start_time in self.active_tasks.items()
            if current_time - start_time > self.slow_task_threshold
        ]
        
        for task_id, duration in slow_tasks:
            self.task_slow.emit(task_id, duration)


# Integration example in data_loader_process.py
class DataLoadingManager:
    def __init__(self):
        # ... existing code ...
        self.task_monitor = BackgroundTaskMonitor()
    
    def start_data_loading(self, schema_filter: str):
        """Start data loading with monitoring."""
        task_id = f"load_data_{schema_filter or 'all'}"
        self.task_monitor.start_task(task_id)
        
        # Start the actual loading
        self._load_data_internal(schema_filter)
    
    def _on_data_loaded(self, schema_filter: str):
        """Handle data loading completion."""
        task_id = f"load_data_{schema_filter or 'all'}"
        self.task_monitor.complete_task(task_id)
```

## 2. Textual TUI Responsiveness Monitoring

### 2.1 Input Latency Tracking
```python
# File: src/dbutils/textual_responsiveness.py
import time
from collections import deque
from textual.app import App
from textual import on
from textual.events import InputEvent


class ResponsivenessTrackingApp(App):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.input_start_times = {}
        self.latency_history = deque(maxlen=100)  # Keep last 100 measurements
        self.hitch_threshold = 0.1  # 100ms
        
    def track_input_start(self, input_id: str):
        """Call when input is received."""
        self.input_start_times[input_id] = time.time()
    
    def track_input_complete(self, input_id: str):
        """Call when input processing is complete."""
        if input_id in self.input_start_times:
            start_time = self.input_start_times.pop(input_id)
            latency = time.time() - start_time
            
            self.latency_history.append(latency)
            
            if latency > self.hitch_threshold:
                self.log_hitch(f"Input processing hitch: {latency:.3f}s")
    
    def log_hitch(self, message: str):
        """Log responsiveness hitches."""
        timestamp = time.strftime("%H:%M:%S")
        with open("responsiveness_log.txt", "a") as f:
            f.write(f"[{timestamp}] {message}\n")
```

## 3. Database Operation Monitoring

### 3.1 Query Timings
Enhance the existing JDBC query runner with monitoring:

```python
# File: src/dbutils/database_monitor.py
import time
import functools
from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class QueryPerformance:
    sql: str
    duration: float
    timestamp: float
    success: bool
    error: str = ""


class DatabaseMonitor:
    def __init__(self, slow_query_threshold: float = 1.0):
        self.slow_query_threshold = slow_query_threshold
        self.query_history: List[QueryPerformance] = []
        self.active_queries: Dict[str, float] = {}  # query_hash -> start_time
        
    def measure_query(self, sql: str):
        """Decorator to measure query performance."""
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                query_hash = str(hash(sql))
                
                self.active_queries[query_hash] = start_time
                
                try:
                    result = func(*args, **kwargs)
                    duration = time.time() - start_time
                    
                    query_record = QueryPerformance(
                        sql=sql,
                        duration=duration,
                        timestamp=start_time,
                        success=True
                    )
                    
                    self.query_history.append(query_record)
                    
                    if duration > self.slow_query_threshold:
                        self.log_slow_query(query_record)
                    
                    return result
                except Exception as e:
                    duration = time.time() - start_time
                    error_msg = str(e)
                    
                    query_record = QueryPerformance(
                        sql=sql,
                        duration=duration,
                        timestamp=start_time,
                        success=False,
                        error=error_msg
                    )
                    
                    self.query_history.append(query_record)
                    self.log_error_query(query_record)
                    
                    raise
                finally:
                    self.active_queries.pop(query_hash, None)
            return wrapper
        return decorator
    
    def log_slow_query(self, query_record: QueryPerformance):
        """Log slow query for analysis."""
        with open("slow_queries.log", "a") as f:
            f.write(f"SLOW QUERY ({query_record.duration:.3f}s): {query_record.sql[:100]}...\n")
    
    def log_error_query(self, query_record: QueryPerformance):
        """Log failed query for analysis."""
        with open("error_queries.log", "a") as f:
            f.write(f"ERROR QUERY ({query_record.duration:.3f}s): {query_record.error}\n")
    
    def get_responsiveness_score(self, window_minutes: int = 5) -> float:
        """Get responsiveness score based on recent queries."""
        cutoff_time = time.time() - (window_minutes * 60)
        recent_queries = [q for q in self.query_history if q.timestamp > cutoff_time]
        
        if not recent_queries:
            return 100.0  # No queries = perfectly responsive
        
        slow_queries = [q for q in recent_queries if q.duration > self.slow_query_threshold]
        slow_ratio = len(slow_queries) / len(recent_queries)
        
        # Score: 100 = 0% slow queries, 0 = 100% slow queries
        return (1.0 - slow_ratio) * 100


# Integration in utils.py
from .database_monitor import DatabaseMonitor

# Global monitor instance
_db_monitor = DatabaseMonitor(slow_query_threshold=1.0)


@_db_monitor.measure_query(sql="SELECT ...")  # This would need more sophisticated approach
def query_runner_with_monitoring(sql: str) -> List[Dict]:
    """Query runner with performance monitoring."""
    # This would need to be integrated differently since query_runner 
    # is called with the SQL as a parameter
    pass


# Better approach - wrap the call
def monitored_query_runner(sql: str) -> List[Dict]:
    """Query runner with integrated monitoring."""
    query_hash = str(hash(sql))
    
    start_time = time.time()
    try:
        result = query_runner(sql)  # Original function
        duration = time.time() - start_time
        
        query_record = QueryPerformance(
            sql=sql,
            duration=duration,
            timestamp=start_time,
            success=True
        )
        
        # Log slow queries
        if duration > 1.0:  # More than 1 second
            with open("slow_db_queries.log", "a") as f:
                f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] SLOW ({duration:.3f}s): {sql[:100]}...\n")
        
        return result
    except Exception as e:
        duration = time.time() - start_time
        with open("error_db_queries.log", "a") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ERROR ({duration:.3f}s): {e}\n")
        raise
```

## 4. Comprehensive Monitoring System

### 4.1 Central Monitoring Hub
```python
# File: src/dbutils/monitoring_hub.py
import time
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class ResponsivenessEvent:
    timestamp: float
    event_type: str  # 'hitch', 'slow_query', 'long_operation', etc.
    duration: float
    details: Dict[str, Any]


class MonitoringHub:
    """Central hub for all responsiveness and performance monitoring."""
    
    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or Path("monitoring_output")
        self.output_dir.mkdir(exist_ok=True)
        
        self.events: List[ResponsivenessEvent] = []
        self.session_start_time = time.time()
        
        # Thresholds for different issues
        self.thresholds = {
            'hitch': 0.1,      # 100ms UI unresponsiveness
            'slow_query': 1.0, # 1 second DB query
            'long_operation': 2.0  # 2 second operation
        }
    
    def record_event(self, event_type: str, duration: float, details: Dict[str, Any] = None):
        """Record a responsiveness event."""
        event = ResponsivenessEvent(
            timestamp=time.time(),
            event_type=event_type,
            duration=duration,
            details=details or {}
        )
        
        self.events.append(event)
        
        # Save immediately for crash recovery
        self._save_events()
        
        # Log to console
        print(f"MONITOR: {event_type.upper()} - {duration:.3f}s - {details or ''}")
    
    def _save_events(self):
        """Save events to file."""
        events_file = self.output_dir / "responsiveness_events.json"
        
        with open(events_file, 'w') as f:
            json.dump([
                {
                    'timestamp': e.timestamp,
                    'event_type': e.event_type,
                    'duration': e.duration,
                    'details': e.details
                }
                for e in self.events
            ], f, indent=2)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of monitoring data."""
        total_time = time.time() - self.session_start_time
        total_events = len(self.events)
        
        # Group events by type
        events_by_type: Dict[str, List[ResponsivenessEvent]] = {}
        for event in self.events:
            if event.event_type not in events_by_type:
                events_by_type[event.event_type] = []
            events_by_type[event.event_type].append(event)
        
        # Calculate statistics
        stats = {}
        for event_type, events in events_by_type.items():
            durations = [e.duration for e in events]
            stats[event_type] = {
                'count': len(events),
                'avg_duration': sum(durations) / len(durations) if durations else 0,
                'max_duration': max(durations) if durations else 0,
                'total_duration': sum(durations)
            }
        
        return {
            'session_duration': total_time,
            'total_events': total_events,
            'events_by_type': stats,
            'events_per_minute': (total_events / total_time) * 60 if total_time > 0 else 0
        }
    
    def generate_report(self) -> str:
        """Generate a human-readable report."""
        summary = self.get_summary()
        
        lines = [
            "DBUTILS RESPONSIVENESS MONITORING REPORT",
            "=" * 50,
            f"Session Duration: {summary['session_duration']:.2f}s",
            f"Total Events: {summary['total_events']}",
            f"Events/Minute: {summary['events_per_minute']:.2f}",
            "",
            "EVENT BREAKDOWN:",
        ]
        
        for event_type, stats in summary['events_by_type'].items():
            lines.extend([
                f"  {event_type.upper()}:",
                f"    Count: {stats['count']}",
                f"    Avg Duration: {stats['avg_duration']:.3f}s",
                f"    Max Duration: {stats['max_duration']:.3f}s",
                f"    Total Duration: {stats['total_duration']:.3f}s",
                ""
            ])
        
        return "\n".join(lines)


# Integration example
class DBBrowserApp:
    def __init__(self):
        # ... existing initialization ...
        
        # Initialize monitoring hub
        self.monitoring_hub = MonitoringHub()
        
        # Set up monitors for different subsystems
        self._setup_ui_monitoring()
        self._setup_database_monitoring()
    
    def _setup_ui_monitoring(self):
        """Set up UI responsiveness monitoring."""
        # Qt responsiveness monitor
        self.responsiveness_monitor = QtResponsivenessMonitor(self)
        self.responsiveness_monitor.hitch_detected.connect(
            lambda dur: self.monitoring_hub.record_event(
                'ui_hitch', dur, {'component': 'qt_event_loop'}
            )
        )
    
    def _setup_database_monitoring(self):
        """Set up database responsiveness monitoring."""
        # The database monitor would integrate with query calls
        pass
    
    def closeEvent(self, event):
        """Generate monitoring report on application close."""
        report = self.monitoring_hub.generate_report()
        
        # Save report
        report_file = self.monitoring_hub.output_dir / "final_report.txt"
        with open(report_file, 'w') as f:
            f.write(report)
        
        print("Responsiveness monitoring report saved to:", report_file)
        super().closeEvent(event)
```

## 5. Command-Line Monitoring Options

### 5.1 Add monitoring flags to command-line tools
```python
# Example integration in main_launcher.py
def main():
    parser = argparse.ArgumentParser(description="Smart DB Browser Launcher")
    
    # ... existing arguments ...
    
    # Monitoring options
    monitoring_group = parser.add_argument_group("Monitoring")
    monitoring_group.add_argument(
        "--monitor-responsiveness", 
        action="store_true", 
        help="Enable responsiveness monitoring"
    )
    monitoring_group.add_argument(
        "--monitor-output-dir",
        type=str,
        default="monitoring_output",
        help="Directory for monitoring output files"
    )
    monitoring_group.add_argument(
        "--hitch-threshold",
        type=float,
        default=0.1,
        help="Hitch threshold in seconds (default: 0.1)"
    )
    
    args = parser.parse_args()
    
    # Initialize monitoring if requested
    if args.monitor_responsiveness:
        from dbutils.monitoring_hub import MonitoringHub
        monitoring_hub = MonitoringHub(output_dir=Path(args.monitor_output_dir))
        
        # Set thresholds
        monitoring_hub.thresholds['hitch'] = args.hitch_threshold

# Similar integration points in other command-line tools
```

## 6. Real-time Dashboard (Optional)

For advanced monitoring, consider a real-time dashboard:

```python
# File: src/dbutils/dashboard.py
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import threading
from pathlib import Path


class MonitoringDashboardHandler(BaseHTTPRequestHandler):
    def __init__(self, monitoring_hub, *args, **kwargs):
        self.monitoring_hub = monitoring_hub
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            html = '''
            <!DOCTYPE html>
            <html>
            <head>
                <title>DBUtils Responsiveness Dashboard</title>
                <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            </head>
            <body>
                <h1>DBUtils Responsiveness Dashboard</h1>
                <div>
                    <canvas id="responseChart" width="400" height="200"></canvas>
                </div>
                <div id="stats"></div>
                <script>
                    // Real-time updates would go here
                </script>
            </body>
            </html>
            '''
            self.wfile.write(html.encode())
        
        elif self.path == '/api/stats':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            stats = self.monitoring_hub.get_summary()
            self.wfile.write(json.dumps(stats).encode())


def start_monitoring_dashboard(monitoring_hub, port=8080):
    """Start a simple web dashboard for monitoring."""
    def run_server():
        server = HTTPServer(('localhost', port), 
                          lambda *args, **kwargs: MonitoringDashboardHandler(monitoring_hub, *args, **kwargs))
        server.serve_forever()
    
    dashboard_thread = threading.Thread(target=run_server, daemon=True)
    dashboard_thread.start()
    
    print(f"Monitoring dashboard started at http://localhost:{port}")
```

This comprehensive monitoring system would provide both passive monitoring that logs issues for analysis and active monitoring that provides immediate feedback when responsiveness problems occur.