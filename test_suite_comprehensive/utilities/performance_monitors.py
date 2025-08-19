"""
Performance monitoring utilities for comprehensive testing.

Provides tools for measuring and tracking system performance during tests.
"""

import time
import psutil
import threading
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from collections import deque

@dataclass
class PerformanceMetric:
    """Single performance measurement."""
    timestamp: float
    cpu_percent: float
    memory_mb: float
    disk_io_read_mb: float
    disk_io_write_mb: float

class PerformanceMonitor:
    """Comprehensive performance monitoring for test scenarios."""
    
    def __init__(self, sample_interval: float = 0.1):
        """Initialize performance monitor.
        
        Args:
            sample_interval: Time between samples in seconds
        """
        self.sample_interval = sample_interval
        self.metrics: List[PerformanceMetric] = []
        self.is_running = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._process = psutil.Process()
        
    def start(self):
        """Start performance monitoring."""
        if self.is_running:
            return
            
        self.is_running = True
        self.metrics.clear()
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        
    def stop(self):
        """Stop performance monitoring."""
        self.is_running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=1.0)
            
    def _monitor_loop(self):
        """Main monitoring loop."""
        while self.is_running:
            try:
                # Get current process metrics
                cpu_percent = self._process.cpu_percent()
                memory_info = self._process.memory_info()
                
                # Get disk I/O if available
                try:
                    io_counters = self._process.io_counters()
                    disk_read_mb = io_counters.read_bytes / 1024 / 1024
                    disk_write_mb = io_counters.write_bytes / 1024 / 1024
                except (AttributeError, psutil.AccessDenied):
                    disk_read_mb = 0.0
                    disk_write_mb = 0.0
                
                metric = PerformanceMetric(
                    timestamp=time.time(),
                    cpu_percent=cpu_percent,
                    memory_mb=memory_info.rss / 1024 / 1024,
                    disk_io_read_mb=disk_read_mb,
                    disk_io_write_mb=disk_write_mb
                )
                
                self.metrics.append(metric)
                
            except Exception as e:
                print(f"Performance monitoring error: {e}")
                
            time.sleep(self.sample_interval)
            
    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary statistics."""
        if not self.metrics:
            return {"error": "No metrics collected"}
            
        memory_values = [m.memory_mb for m in self.metrics]
        cpu_values = [m.cpu_percent for m in self.metrics]
        
        return {
            "duration_seconds": self.metrics[-1].timestamp - self.metrics[0].timestamp,
            "sample_count": len(self.metrics),
            "memory_mb": {
                "min": min(memory_values),
                "max": max(memory_values),
                "avg": sum(memory_values) / len(memory_values),
                "current": memory_values[-1]
            },
            "cpu_percent": {
                "min": min(cpu_values),
                "max": max(cpu_values),
                "avg": sum(cpu_values) / len(cpu_values),
                "current": cpu_values[-1]
            }
        }

class MemoryTracker:
    """Simple memory usage tracker."""
    
    def __init__(self):
        """Initialize memory tracker."""
        self._process = psutil.Process()
        self._measurements = deque(maxlen=1000)  # Keep last 1000 measurements
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        
    def start(self):
        """Start memory tracking."""
        self._monitoring = True
        self._measurements.clear()
        self._monitor_thread = threading.Thread(target=self._track_memory, daemon=True)
        self._monitor_thread.start()
        
    def stop(self):
        """Stop memory tracking."""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=1.0)
            
    def _track_memory(self):
        """Track memory usage in background."""
        while self._monitoring:
            try:
                memory_mb = self._process.memory_info().rss / 1024 / 1024
                self._measurements.append({
                    'timestamp': time.time(),
                    'memory_mb': memory_mb
                })
                time.sleep(0.1)  # Sample every 100ms
            except Exception:
                break
                
    def get_current_usage_mb(self) -> float:
        """Get current memory usage in MB."""
        try:
            return self._process.memory_info().rss / 1024 / 1024
        except Exception:
            return 0.0
            
    def get_peak_usage_mb(self) -> float:
        """Get peak memory usage in MB."""
        if not self._measurements:
            return self.get_current_usage_mb()
        return max(m['memory_mb'] for m in self._measurements)
        
    def get_usage_trend(self) -> List[Dict[str, float]]:
        """Get memory usage trend data."""
        return list(self._measurements)

class BenchmarkTimer:
    """High-precision timer for performance benchmarks."""
    
    def __init__(self, name: str = "benchmark"):
        """Initialize benchmark timer.
        
        Args:
            name: Name of the benchmark
        """
        self.name = name
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        
    def __enter__(self):
        """Context manager entry."""
        self.start_time = time.perf_counter()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.end_time = time.perf_counter()
        
    def elapsed(self) -> float:
        """Get elapsed time in seconds."""
        if self.start_time is None:
            return 0.0
        end = self.end_time if self.end_time else time.perf_counter()
        return end - self.start_time
        
    def elapsed_ms(self) -> float:
        """Get elapsed time in milliseconds."""
        return self.elapsed() * 1000

def measure_function_performance(func, *args, iterations: int = 1, **kwargs) -> Dict[str, Any]:
    """Measure performance of a function call.
    
    Args:
        func: Function to measure
        args: Function arguments  
        iterations: Number of times to run the function
        kwargs: Function keyword arguments
        
    Returns:
        Dictionary with performance metrics
    """
    times = []
    memory_tracker = MemoryTracker()
    memory_tracker.start()
    
    for _ in range(iterations):
        with BenchmarkTimer() as timer:
            result = func(*args, **kwargs)
        times.append(timer.elapsed())
        
    memory_tracker.stop()
    
    return {
        "iterations": iterations,
        "times_seconds": times,
        "min_time": min(times),
        "max_time": max(times),
        "avg_time": sum(times) / len(times),
        "total_time": sum(times),
        "peak_memory_mb": memory_tracker.get_peak_usage_mb(),
        "result": result if iterations == 1 else f"{iterations} results"
    }