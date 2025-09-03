#!/usr/bin/env python3
"""
Performance Optimization and Resource Management System

Provides intelligent resource management, caching, and performance optimizations.
"""

import hashlib
import os
import pickle
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Tuple

import psutil

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
except ImportError as e:
    print(f"Error: Required packages not found: {e}", file=sys.stderr)
    sys.exit(1)


@dataclass
class SystemResources:
    """System resource information"""

    cpu_count: int
    cpu_percent: float
    memory_total: int
    memory_available: int
    memory_percent: float
    disk_free: int
    disk_total: int
    load_avg: Tuple[float, float, float]

    @property
    def memory_free_gb(self) -> float:
        return self.memory_available / (1024**3)

    @property
    def disk_free_gb(self) -> float:
        return self.disk_free / (1024**3)

    @property
    def recommended_workers(self) -> int:
        """Calculate recommended number of worker threads/processes"""
        # Consider CPU cores, memory, and current load
        base_workers = min(self.cpu_count, 8)  # Cap at 8 for reasonable concurrency

        # Reduce workers if system is under high load
        if self.cpu_percent > 80 or self.memory_percent > 85:
            base_workers = max(1, base_workers // 2)

        # Ensure minimum workers
        return max(1, base_workers)


@dataclass
class PerformanceProfile:
    """Performance configuration profile"""

    name: str
    max_workers: int
    cache_size: int  # MB
    memory_limit: int  # MB
    concurrent_downloads: int
    chunk_size: int  # bytes
    timeout: int  # seconds
    enable_compression: bool = True
    enable_parallel_processing: bool = True
    enable_memory_monitoring: bool = True

    @classmethod
    def auto_detect(cls) -> "PerformanceProfile":
        """Auto-detect optimal performance profile"""
        resources = get_system_resources()

        if resources.memory_free_gb >= 8 and resources.cpu_count >= 8:
            # High performance system
            return cls(
                name="high_performance",
                max_workers=min(resources.cpu_count, 12),
                cache_size=512,
                memory_limit=2048,
                concurrent_downloads=6,
                chunk_size=32768,
                timeout=60,
            )
        elif resources.memory_free_gb >= 4 and resources.cpu_count >= 4:
            # Standard system
            return cls(
                name="standard",
                max_workers=min(resources.cpu_count, 6),
                cache_size=256,
                memory_limit=1024,
                concurrent_downloads=3,
                chunk_size=16384,
                timeout=45,
            )
        else:
            # Resource-constrained system
            return cls(
                name="low_resource",
                max_workers=min(resources.cpu_count, 3),
                cache_size=128,
                memory_limit=512,
                concurrent_downloads=2,
                chunk_size=8192,
                timeout=30,
                enable_parallel_processing=False,
            )


@dataclass
class CacheStats:
    """Cache performance statistics"""

    hits: int = 0
    misses: int = 0
    size: int = 0
    memory_usage: int = 0

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


class PerformanceCache:
    """High-performance caching system with LRU and memory management"""

    def __init__(self, max_size: int = 256 * 1024 * 1024, max_entries: int = 1000):
        self.max_size = max_size
        self.max_entries = max_entries
        self.cache: Dict[str, Any] = {}
        self.access_times: Dict[str, datetime] = {}
        self.entry_sizes: Dict[str, int] = {}
        self.stats = CacheStats()
        self.lock = threading.RLock()

    def _calculate_size(self, obj: Any) -> int:
        """Calculate approximate size of object"""
        try:
            return len(pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL))
        except Exception:
            return sys.getsizeof(obj)

    def _evict_lru(self):
        """Evict least recently used entries"""
        with self.lock:
            while (
                self.stats.memory_usage > self.max_size or len(self.cache) > self.max_entries
            ) and self.cache:

                # Find least recently used entry
                lru_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])

                # Remove entry
                self.stats.memory_usage -= self.entry_sizes.get(lru_key, 0)
                del self.cache[lru_key]
                del self.access_times[lru_key]
                self.entry_sizes.pop(lru_key, None)

    def get(self, key: str) -> Optional[Any]:
        """Get cached value"""
        with self.lock:
            if key in self.cache:
                self.access_times[key] = datetime.now()
                self.stats.hits += 1
                return self.cache[key]

            self.stats.misses += 1
            return None

    def put(self, key: str, value: Any) -> bool:
        """Cache value"""
        with self.lock:
            size = self._calculate_size(value)

            # Don't cache if too large
            if size > self.max_size // 4:
                return False

            # Update existing entry
            if key in self.cache:
                old_size = self.entry_sizes.get(key, 0)
                self.stats.memory_usage = self.stats.memory_usage - old_size + size
            else:
                self.stats.memory_usage += size
                self.stats.size += 1

            self.cache[key] = value
            self.access_times[key] = datetime.now()
            self.entry_sizes[key] = size

            # Evict if necessary
            self._evict_lru()

            return True

    def clear(self):
        """Clear cache"""
        with self.lock:
            self.cache.clear()
            self.access_times.clear()
            self.entry_sizes.clear()
            self.stats = CacheStats()

    def get_stats(self) -> CacheStats:
        """Get cache statistics"""
        with self.lock:
            return CacheStats(
                hits=self.stats.hits,
                misses=self.stats.misses,
                size=len(self.cache),
                memory_usage=self.stats.memory_usage,
            )


class ResourceMonitor:
    """System resource monitoring and management"""

    def __init__(self, check_interval: int = 5):
        self.check_interval = check_interval
        self.monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.resource_history: List[SystemResources] = []
        self.max_history = 60  # Keep 5 minutes at 5-second intervals
        self.callbacks: List[Callable[[SystemResources], None]] = []

        # Resource thresholds
        self.cpu_threshold = 90.0
        self.memory_threshold = 90.0
        self.disk_threshold = 95.0

    def add_callback(self, callback: Callable[[SystemResources], None]):
        """Add resource monitoring callback"""
        self.callbacks.append(callback)

    def start_monitoring(self):
        """Start resource monitoring"""
        if self.monitoring:
            return

        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()

    def stop_monitoring(self):
        """Stop resource monitoring"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1)

    def _monitor_loop(self):
        """Resource monitoring loop"""
        while self.monitoring:
            try:
                resources = get_system_resources()

                # Add to history
                self.resource_history.append(resources)
                if len(self.resource_history) > self.max_history:
                    self.resource_history.pop(0)

                # Check thresholds and notify callbacks
                for callback in self.callbacks:
                    try:
                        callback(resources)
                    except Exception as e:
                        print(f"Resource monitor callback error: {e}")

                # Check for resource warnings
                self._check_resource_warnings(resources)

                time.sleep(self.check_interval)

            except Exception as e:
                print(f"Resource monitoring error: {e}")
                time.sleep(self.check_interval)

    def _check_resource_warnings(self, resources: SystemResources):
        """Check for resource threshold violations"""
        warnings = []

        if resources.cpu_percent > self.cpu_threshold:
            warnings.append(f"High CPU usage: {resources.cpu_percent:.1f}%")

        if resources.memory_percent > self.memory_threshold:
            warnings.append(f"High memory usage: {resources.memory_percent:.1f}%")

        if resources.disk_free_gb < 1.0:
            warnings.append(f"Low disk space: {resources.disk_free_gb:.1f}GB free")

        for warning in warnings:
            print(f"⚠ Resource Warning: {warning}")

    def get_current_resources(self) -> SystemResources:
        """Get current system resources"""
        return get_system_resources()

    def get_resource_trend(self, minutes: int = 5) -> Dict[str, float]:
        """Get resource usage trend"""
        if len(self.resource_history) < 2:
            return {}

        # Get samples from specified time period
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        recent_samples = [
            r
            for r in self.resource_history
            if datetime.now()
            - timedelta(seconds=len(self.resource_history) - self.resource_history.index(r))
            >= cutoff_time
        ]

        if len(recent_samples) < 2:
            return {}

        # Calculate trends
        first = recent_samples[0]
        last = recent_samples[-1]

        return {
            "cpu_trend": last.cpu_percent - first.cpu_percent,
            "memory_trend": last.memory_percent - first.memory_percent,
            "load_trend": last.load_avg[0] - first.load_avg[0],
        }


class ParallelProcessor:
    """Parallel processing manager with resource awareness"""

    def __init__(self, performance_profile: PerformanceProfile):
        self.profile = performance_profile
        self.active_tasks: Dict[str, Any] = {}
        self.task_lock = threading.RLock()

        # Resource monitoring
        self.monitor = ResourceMonitor()
        self.monitor.add_callback(self._resource_callback)

        if self.profile.enable_memory_monitoring:
            self.monitor.start_monitoring()

    def _resource_callback(self, resources: SystemResources):
        """Handle resource changes"""
        # Adjust concurrency based on resource usage
        if resources.cpu_percent > 85 or resources.memory_percent > 85:
            # Reduce active tasks if system is under stress
            with self.task_lock:
                if len(self.active_tasks) > 1:
                    # Could implement task throttling here
                    pass

    def execute_parallel(
        self, tasks: List[Callable], max_workers: Optional[int] = None
    ) -> List[Any]:
        """Execute tasks in parallel"""
        if not self.profile.enable_parallel_processing:
            # Execute sequentially
            return [task() for task in tasks]

        if max_workers is None:
            max_workers = self.profile.max_workers

        results = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit tasks
            future_to_task = {}
            for i, task in enumerate(tasks):
                future = executor.submit(self._execute_with_monitoring, f"task_{i}", task)
                future_to_task[future] = i

            # Collect results
            results = [None] * len(tasks)
            for future in as_completed(future_to_task):
                task_id = future_to_task[future]
                try:
                    results[task_id] = future.result()
                except Exception as e:
                    results[task_id] = e

        return results

    def _execute_with_monitoring(self, task_id: str, task: Callable) -> Any:
        """Execute task with resource monitoring"""
        with self.task_lock:
            self.active_tasks[task_id] = {
                "start_time": time.time(),
                "status": "running",
            }

        try:
            result = task()
            with self.task_lock:
                self.active_tasks[task_id]["status"] = "completed"
            return result
        except Exception:
            with self.task_lock:
                self.active_tasks[task_id]["status"] = "failed"
            raise
        finally:
            with self.task_lock:
                self.active_tasks[task_id]["end_time"] = time.time()

    def get_active_tasks(self) -> Dict[str, Any]:
        """Get currently active tasks"""
        with self.task_lock:
            return self.active_tasks.copy()

    def cleanup(self):
        """Cleanup resources"""
        self.monitor.stop_monitoring()


class PerformanceOptimizer:
    """Main performance optimization coordinator"""

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()

        # Auto-detect performance profile
        self.profile = PerformanceProfile.auto_detect()

        # Initialize components
        self.cache = PerformanceCache(
            max_size=self.profile.cache_size * 1024 * 1024, max_entries=1000
        )

        self.processor = ParallelProcessor(self.profile)
        self.monitor = ResourceMonitor()

        # Performance statistics
        self.start_time = time.time()
        self.operation_times: Dict[str, List[float]] = {}

        self.console.print(f"[dim]Performance profile: {self.profile.name}[/dim]")

    def cached_operation(self, key_func: Optional[Callable] = None):
        """Decorator for caching expensive operations"""

        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Generate cache key
                if key_func:
                    cache_key = key_func(*args, **kwargs)
                else:
                    # Default key generation
                    key_parts = [func.__name__]
                    key_parts.extend(str(arg) for arg in args)
                    key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                    cache_key = hashlib.md5("|".join(key_parts).encode()).hexdigest()

                # Try cache first
                cached_result = self.cache.get(cache_key)
                if cached_result is not None:
                    return cached_result

                # Execute and cache result
                start_time = time.time()
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time

                # Record performance
                op_name = func.__name__
                if op_name not in self.operation_times:
                    self.operation_times[op_name] = []
                self.operation_times[op_name].append(execution_time)

                # Cache result
                self.cache.put(cache_key, result)

                return result

            return wrapper

        return decorator

    def parallel_map(
        self, func: Callable, items: List[Any], max_workers: Optional[int] = None
    ) -> List[Any]:
        """Parallel map operation"""
        if not items:
            return []

        if len(items) == 1 or not self.profile.enable_parallel_processing:
            return [func(item) for item in items]

        # Create tasks
        tasks = [lambda item=item: func(item) for item in items]

        return self.processor.execute_parallel(tasks, max_workers)

    def optimize_downloads(self, download_manager) -> None:
        """Apply performance optimizations to download manager"""
        if hasattr(download_manager, "chunk_size"):
            download_manager.chunk_size = self.profile.chunk_size

        if hasattr(download_manager, "timeout"):
            download_manager.timeout = self.profile.timeout

        if hasattr(download_manager, "max_concurrent_downloads"):
            download_manager.max_concurrent_downloads = self.profile.concurrent_downloads

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics"""
        uptime = time.time() - self.start_time
        cache_stats = self.cache.get_stats()
        resources = self.monitor.get_current_resources()

        stats = {
            "uptime_seconds": uptime,
            "profile": self.profile.name,
            "cache": {
                "hit_rate": cache_stats.hit_rate,
                "size": cache_stats.size,
                "memory_mb": cache_stats.memory_usage / (1024 * 1024),
            },
            "resources": {
                "cpu_percent": resources.cpu_percent,
                "memory_percent": resources.memory_percent,
                "memory_free_gb": resources.memory_free_gb,
                "disk_free_gb": resources.disk_free_gb,
                "recommended_workers": resources.recommended_workers,
            },
            "operations": {},
        }

        # Add operation statistics
        for op_name, times in self.operation_times.items():
            if times:
                stats["operations"][op_name] = {
                    "count": len(times),
                    "avg_time": sum(times) / len(times),
                    "total_time": sum(times),
                    "min_time": min(times),
                    "max_time": max(times),
                }

        return stats

    def display_performance_stats(self):
        """Display performance statistics"""
        stats = self.get_performance_stats()

        # System resources
        resources_table = Table(title="System Resources")
        resources_table.add_column("Metric", style="cyan")
        resources_table.add_column("Value", style="green")

        res = stats["resources"]
        resources_table.add_row("CPU Usage", f"{res['cpu_percent']:.1f}%")
        resources_table.add_row("Memory Usage", f"{res['memory_percent']:.1f}%")
        resources_table.add_row("Memory Free", f"{res['memory_free_gb']:.1f}GB")
        resources_table.add_row("Disk Free", f"{res['disk_free_gb']:.1f}GB")
        resources_table.add_row("Recommended Workers", str(res["recommended_workers"]))

        self.console.print(resources_table)

        # Cache performance
        cache_info = stats["cache"]
        cache_panel = Panel(
            f"Hit Rate: {cache_info['hit_rate']:.1%}\n"
            f"Entries: {cache_info['size']}\n"
            f"Memory: {cache_info['memory_mb']:.1f}MB",
            title="Cache Performance",
        )
        self.console.print(cache_panel)

        # Operation performance
        if stats["operations"]:
            ops_table = Table(title="Operation Performance")
            ops_table.add_column("Operation", style="cyan")
            ops_table.add_column("Count", style="yellow")
            ops_table.add_column("Avg Time", style="green")
            ops_table.add_column("Total Time", style="blue")

            for op_name, op_stats in stats["operations"].items():
                ops_table.add_row(
                    op_name,
                    str(op_stats["count"]),
                    f"{op_stats['avg_time']:.3f}s",
                    f"{op_stats['total_time']:.3f}s",
                )

            self.console.print(ops_table)

    def cleanup(self):
        """Cleanup performance optimizer"""
        self.processor.cleanup()
        self.monitor.stop_monitoring()
        self.cache.clear()


def get_system_resources() -> SystemResources:
    """Get current system resource information"""
    try:
        cpu_count = psutil.cpu_count()
        cpu_percent = psutil.cpu_percent(interval=0.1)

        memory = psutil.virtual_memory()
        memory_total = memory.total
        memory_available = memory.available
        memory_percent = memory.percent

        disk = psutil.disk_usage("/")
        disk_free = disk.free
        disk_total = disk.total

        # Load average (Unix-like systems)
        try:
            load_avg = os.getloadavg()
        except (AttributeError, OSError):
            load_avg = (0.0, 0.0, 0.0)

        return SystemResources(
            cpu_count=cpu_count,
            cpu_percent=cpu_percent,
            memory_total=memory_total,
            memory_available=memory_available,
            memory_percent=memory_percent,
            disk_free=disk_free,
            disk_total=disk_total,
            load_avg=load_avg,
        )
    except Exception as e:
        print(f"Error getting system resources: {e}")
        # Return minimal fallback
        return SystemResources(
            cpu_count=1,
            cpu_percent=0.0,
            memory_total=1024 * 1024 * 1024,  # 1GB
            memory_available=512 * 1024 * 1024,  # 512MB
            memory_percent=50.0,
            disk_free=1024 * 1024 * 1024,  # 1GB
            disk_total=10 * 1024 * 1024 * 1024,  # 10GB
            load_avg=(0.0, 0.0, 0.0),
        )


def create_performance_optimizer(
    console: Optional[Console] = None,
) -> PerformanceOptimizer:
    """Factory function to create performance optimizer"""
    return PerformanceOptimizer(console)


if __name__ == "__main__":
    # Test the performance optimization system
    console = Console()
    optimizer = create_performance_optimizer(console)

    # Test cached operation
    @optimizer.cached_operation()
    def expensive_operation(n):
        time.sleep(0.1)  # Simulate work
        return n * n

    # Test operations
    console.print("Testing cached operations...")
    for i in range(5):
        result = expensive_operation(i)
        console.print(f"Result {i}: {result}")

    # Test parallel processing
    console.print("\nTesting parallel processing...")

    def cpu_task(x):
        return sum(range(x * 1000))

    start_time = time.time()
    results = optimizer.parallel_map(cpu_task, list(range(10)))
    parallel_time = time.time() - start_time

    console.print(f"Parallel processing completed in {parallel_time:.3f}s")

    # Show performance statistics
    optimizer.display_performance_stats()

    # Cleanup
    optimizer.cleanup()
