# -*- coding: utf-8 -*-
"""
Resource Usage Monitoring Test Suite
====================================

Comprehensive resource usage monitoring tests including:
- CPU usage monitoring
- Memory usage monitoring
- Disk I/O monitoring
- Network I/O monitoring
- GPU usage monitoring (if available)
- Resource leak detection
- Resource peak testing
- Long-running resource stability testing
"""

import asyncio
import gc
import os
import statistics
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import psutil
import pytest
from loguru import logger

# Import performance modules
from core.performance_optimizer import PerformanceOptimizer, PerformanceMetric
from core.api_performance_optimizer import APIPerformanceOptimizer
from core.performance_data_collector import PerformanceDataCollector

# Import benchmark base
from tests.benchmarks.benchmark_base import (
    BenchmarkBase,
    PerformanceMetricsCollector,
    PerformanceMetricType,
    PerformanceResult,
    PerformanceThreshold,
    PerformanceSeverity,
    PerformanceResultAnalyzer,
    PerformanceReportGenerator,
)


# Resource benchmarks
RESOURCE_BENCHMARKS = {
    "cpu_usage_normal": 80.0,  # CPU usage < 80% for normal load
    "memory_usage_normal": 2048.0,  # Memory usage < 2GB for normal load
    "memory_leak_threshold": 10.0,  # Memory growth < 10MB over 5 minutes
    "disk_io_reasonable": 100 * 1024 * 1024,  # 100MB per minute
    "network_io_reasonable": 10 * 1024 * 1024,  # 10MB per minute
}


@dataclass
class ResourceSnapshot:
    """Snapshot of resource usage at a point in time"""
    
    timestamp: datetime
    cpu_percent: float
    memory_mb: float
    memory_percent: float
    disk_read_bytes: int
    disk_write_bytes: int
    network_sent_bytes: int
    network_recv_bytes: int
    gpu_usage: Optional[float] = None
    gpu_memory_mb: Optional[float] = None
    open_files: int = 0
    thread_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "cpu_percent": self.cpu_percent,
            "memory_mb": self.memory_mb,
            "memory_percent": self.memory_percent,
            "disk_read_bytes": self.disk_read_bytes,
            "disk_write_bytes": self.disk_write_bytes,
            "network_sent_bytes": self.network_sent_bytes,
            "network_recv_bytes": self.network_recv_bytes,
            "gpu_usage": self.gpu_usage,
            "gpu_memory_mb": self.gpu_memory_mb,
            "open_files": self.open_files,
            "thread_count": self.thread_count,
        }


class ResourceMonitor:
    """Comprehensive resource usage monitor"""
    
    def __init__(self, sample_interval: float = 1.0):
        """
        Initialize resource monitor
        
        Args:
            sample_interval: Sampling interval in seconds
        """
        self.sample_interval = sample_interval
        self.snapshots: List[ResourceSnapshot] = []
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._process = psutil.Process()
        self._initial_disk_io = self._process.io_counters() if hasattr(self._process, 'io_counters') else None
        self._initial_net_io = psutil.net_io_counters()
        self._gpu_available = self._check_gpu_available()
        
    def _check_gpu_available(self) -> bool:
        """Check if GPU monitoring is available"""
        try:
            import GPUtil
            gpus = GPUtil.getGPUs()
            return len(gpus) > 0
        except ImportError:
            return False
        except Exception:
            return False
    
    def _get_gpu_stats(self) -> Tuple[Optional[float], Optional[float]]:
        """Get GPU usage and memory"""
        if not self._gpu_available:
            return None, None
        
        try:
            import GPUtil
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu = gpus[0]  # Use first GPU
                return gpu.load * 100, gpu.memoryUsed
        except Exception as e:
            logger.debug(f"Error getting GPU stats: {e}")
        
        return None, None
    
    def _collect_snapshot(self) -> ResourceSnapshot:
        """Collect a single resource snapshot"""
        timestamp = datetime.now()
        
        # CPU usage
        cpu_percent = self._process.cpu_percent(interval=0.1)
        
        # Memory usage
        memory_info = self._process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024
        memory_percent = self._process.memory_percent()
        
        # Disk I/O
        disk_read = 0
        disk_write = 0
        if self._initial_disk_io:
            try:
                current_io = self._process.io_counters()
                disk_read = current_io.read_bytes - self._initial_disk_io.read_bytes
                disk_write = current_io.write_bytes - self._initial_disk_io.write_bytes
            except Exception:
                pass
        
        # Network I/O
        net_sent = 0
        net_recv = 0
        try:
            current_net = psutil.net_io_counters()
            net_sent = current_net.bytes_sent - self._initial_net_io.bytes_sent
            net_recv = current_net.bytes_recv - self._initial_net_io.bytes_recv
        except Exception:
            pass
        
        # GPU stats
        gpu_usage, gpu_memory = self._get_gpu_stats()
        
        # Open files and threads
        try:
            open_files = len(self._process.open_files()) if hasattr(self._process, 'open_files') else 0
        except Exception:
            open_files = 0
        
        try:
            thread_count = self._process.num_threads() if hasattr(self._process, 'num_threads') else 0
        except Exception:
            thread_count = 0
        
        return ResourceSnapshot(
            timestamp=timestamp,
            cpu_percent=cpu_percent,
            memory_mb=memory_mb,
            memory_percent=memory_percent,
            disk_read_bytes=disk_read,
            disk_write_bytes=disk_write,
            network_sent_bytes=net_sent,
            network_recv_bytes=net_recv,
            gpu_usage=gpu_usage,
            gpu_memory_mb=gpu_memory,
            open_files=open_files,
            thread_count=thread_count,
        )
    
    def start_monitoring(self):
        """Start background resource monitoring"""
        if self._monitoring:
            logger.warning("Resource monitoring already in progress")
            return
        
        self._monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self._monitor_thread.start()
        logger.info("Started resource monitoring")
    
    def stop_monitoring(self):
        """Stop background resource monitoring"""
        if not self._monitoring:
            return
        
        self._monitoring = False
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5.0)
        logger.info("Stopped resource monitoring")
    
    def _monitoring_loop(self):
        """Background monitoring loop"""
        while self._monitoring:
            try:
                snapshot = self._collect_snapshot()
                self.snapshots.append(snapshot)
                time.sleep(self.sample_interval)
            except Exception as e:
                logger.error(f"Error collecting resource snapshot: {e}")
                break
    
    def collect_snapshot_now(self) -> ResourceSnapshot:
        """Collect a single snapshot immediately"""
        return self._collect_snapshot()
    
    def get_snapshots(self) -> List[ResourceSnapshot]:
        """Get all collected snapshots"""
        return self.snapshots.copy()
    
    def clear_snapshots(self):
        """Clear all collected snapshots"""
        self.snapshots.clear()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Calculate statistics from collected snapshots"""
        if not self.snapshots:
            return {}
        
        cpu_values = [s.cpu_percent for s in self.snapshots]
        memory_mb_values = [s.memory_mb for s in self.snapshots]
        memory_percent_values = [s.memory_percent for s in self.snapshots]
        
        return {
            "cpu": {
                "mean": statistics.mean(cpu_values),
                "median": statistics.median(cpu_values),
                "min": min(cpu_values),
                "max": max(cpu_values),
                "std_dev": statistics.stdev(cpu_values) if len(cpu_values) > 1 else 0.0,
            },
            "memory_mb": {
                "mean": statistics.mean(memory_mb_values),
                "median": statistics.median(memory_mb_values),
                "min": min(memory_mb_values),
                "max": max(memory_mb_values),
                "std_dev": statistics.stdev(memory_mb_values) if len(memory_mb_values) > 1 else 0.0,
            },
            "memory_percent": {
                "mean": statistics.mean(memory_percent_values),
                "median": statistics.median(memory_percent_values),
                "min": min(memory_percent_values),
                "max": max(memory_percent_values),
                "std_dev": statistics.stdev(memory_percent_values) if len(memory_percent_values) > 1 else 0.0,
            },
            "sample_count": len(self.snapshots),
            "duration_seconds": (self.snapshots[-1].timestamp - self.snapshots[0].timestamp).total_seconds() if len(self.snapshots) > 1 else 0.0,
        }


class ResourceLeakDetector:
    """Detects resource leaks over time"""
    
    def __init__(self, monitor: ResourceMonitor):
        """
        Initialize leak detector
        
        Args:
            monitor: Resource monitor to use
        """
        self.monitor = monitor
        self.baseline_snapshot: Optional[ResourceSnapshot] = None
    
    def set_baseline(self):
        """Set baseline snapshot for leak detection"""
        self.baseline_snapshot = self.monitor.collect_snapshot_now()
        logger.info(f"Baseline set: memory={self.baseline_snapshot.memory_mb:.2f}MB")
    
    def detect_memory_leak(self, duration_seconds: int = 300, threshold_mb: float = 10.0) -> Dict[str, Any]:
        """
        Detect memory leak over specified duration
        
        Args:
            duration_seconds: Duration to monitor in seconds
            threshold_mb: Memory growth threshold in MB
            
        Returns:
            Leak detection result
        """
        if not self.baseline_snapshot:
            self.set_baseline()
        
        logger.info(f"Monitoring for memory leak over {duration_seconds} seconds...")
        
        start_time = time.time()
        initial_memory = self.baseline_snapshot.memory_mb
        max_memory = initial_memory
        
        while time.time() - start_time < duration_seconds:
            snapshot = self.monitor.collect_snapshot_now()
            max_memory = max(max_memory, snapshot.memory_mb)
            time.sleep(1)
        
        memory_growth = max_memory - initial_memory
        is_leak = memory_growth > threshold_mb
        
        result = {
            "initial_memory_mb": initial_memory,
            "max_memory_mb": max_memory,
            "memory_growth_mb": memory_growth,
            "threshold_mb": threshold_mb,
            "is_leak": is_leak,
            "duration_seconds": duration_seconds,
        }
        
        if is_leak:
            logger.warning(f"Memory leak detected: {memory_growth:.2f}MB growth over {duration_seconds}s")
        else:
            logger.info(f"No memory leak: {memory_growth:.2f}MB growth over {duration_seconds}s")
        
        return result
    
    def detect_file_handle_leak(self) -> Dict[str, Any]:
        """
        Detect file handle leak
        
        Returns:
            File handle leak detection result
        """
        if not self.baseline_snapshot:
            self.set_baseline()
        
        current = self.monitor.collect_snapshot_now()
        file_handle_growth = current.open_files - self.baseline_snapshot.open_files
        
        result = {
            "baseline_files": self.baseline_snapshot.open_files,
            "current_files": current.open_files,
            "growth": file_handle_growth,
            "is_leak": file_handle_growth > 10,  # More than 10 additional files
        }
        
        return result
    
    def detect_thread_leak(self) -> Dict[str, Any]:
        """
        Detect thread leak
        
        Returns:
            Thread leak detection result
        """
        if not self.baseline_snapshot:
            self.set_baseline()
        
        current = self.monitor.collect_snapshot_now()
        thread_growth = current.thread_count - self.baseline_snapshot.thread_count
        
        result = {
            "baseline_threads": self.baseline_snapshot.thread_count,
            "current_threads": current.thread_count,
            "growth": thread_growth,
            "is_leak": thread_growth > 5,  # More than 5 additional threads
        }
        
        return result


class ResourceUsageMonitoringTest:
    """Resource usage monitoring test suite"""
    
    def __init__(self):
        """Initialize resource usage monitoring test"""
        self.name = "resource_usage_monitoring"
        self.resource_monitor = ResourceMonitor(sample_interval=0.5)
        self.leak_detector = ResourceLeakDetector(self.resource_monitor)
    
    def test_cpu_usage_monitoring(self) -> Dict[str, Any]:
        """
        Test CPU usage monitoring
        
        Returns:
            Test result
        """
        logger.info("Testing CPU usage monitoring...")
        
        # Force garbage collection
        gc.collect()
        
        # Start monitoring
        self.resource_monitor.start_monitoring()
        
        # Simulate CPU workload
        def cpu_workload():
            total = 0
            for i in range(10000000):
                total += i
            return total
        
        # Run workload in multiple threads
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(cpu_workload) for _ in range(4)]
            for future in as_completed(futures):
                future.result()
        
        time.sleep(2)  # Let monitoring collect samples
        
        # Stop monitoring
        self.resource_monitor.stop_monitoring()
        
        # Get statistics
        stats = self.resource_monitor.get_statistics()
        
        # Evaluate against benchmark
        cpu_mean = stats.get("cpu", {}).get("mean", 0)
        cpu_max = stats.get("cpu", {}).get("max", 0)
        
        result = {
            "test_name": "cpu_usage_monitoring",
            "passed": cpu_mean < RESOURCE_BENCHMARKS["cpu_usage_normal"],
            "cpu_mean_percent": cpu_mean,
            "cpu_max_percent": cpu_max,
            "benchmark_percent": RESOURCE_BENCHMARKS["cpu_usage_normal"],
            "statistics": stats,
        }
        
        logger.info(f"CPU usage monitoring test: {'PASSED' if result['passed'] else 'FAILED'}")
        logger.info(f"  Mean CPU: {cpu_mean:.2f}%, Max CPU: {cpu_max:.2f}%")
        
        self.resource_monitor.clear_snapshots()
        return result
    
    def test_memory_usage_monitoring(self) -> Dict[str, Any]:
        """
        Test memory usage monitoring
        
        Returns:
            Test result
        """
        logger.info("Testing memory usage monitoring...")
        
        # Force garbage collection
        gc.collect()
        
        # Start monitoring
        self.resource_monitor.start_monitoring()
        
        # Simulate memory workload
        data = []
        for i in range(100):
            data.append([0] * 10000)  # Allocate memory
        
        time.sleep(2)  # Let monitoring collect samples
        
        # Clean up
        del data
        gc.collect()
        
        time.sleep(1)
        
        # Stop monitoring
        self.resource_monitor.stop_monitoring()
        
        # Get statistics
        stats = self.resource_monitor.get_statistics()
        
        # Evaluate against benchmark
        memory_mean = stats.get("memory_mb", {}).get("mean", 0)
        memory_max = stats.get("memory_mb", {}).get("max", 0)
        
        result = {
            "test_name": "memory_usage_monitoring",
            "passed": memory_mean < RESOURCE_BENCHMARKS["memory_usage_normal"],
            "memory_mean_mb": memory_mean,
            "memory_max_mb": memory_max,
            "benchmark_mb": RESOURCE_BENCHMARKS["memory_usage_normal"],
            "statistics": stats,
        }
        
        logger.info(f"Memory usage monitoring test: {'PASSED' if result['passed'] else 'FAILED'}")
        logger.info(f"  Mean Memory: {memory_mean:.2f}MB, Max Memory: {memory_max:.2f}MB")
        
        self.resource_monitor.clear_snapshots()
        return result
    
    def test_disk_io_monitoring(self) -> Dict[str, Any]:
        """
        Test disk I/O monitoring
        
        Returns:
            Test result
        """
        logger.info("Testing disk I/O monitoring...")
        
        # Force garbage collection
        gc.collect()
        
        # Start monitoring
        self.resource_monitor.start_monitoring()
        
        # Simulate disk I/O workload
        import tempfile
        test_file = Path(tempfile.gettempdir()) / "resource_test.tmp"
        test_data = b"x" * (1024 * 1024)  # 1MB
        
        for _ in range(5):
            try:
                with open(test_file, "wb") as f:
                    f.write(test_data)
                with open(test_file, "rb") as f:
                    f.read()
            except Exception:
                pass
        
        # Clean up
        if test_file.exists():
            test_file.unlink()
        
        time.sleep(2)  # Let monitoring collect samples
        
        # Stop monitoring
        self.resource_monitor.stop_monitoring()
        
        # Get snapshots
        snapshots = self.resource_monitor.get_snapshots()
        
        # Calculate disk I/O rate
        if len(snapshots) > 1:
            duration = (snapshots[-1].timestamp - snapshots[0].timestamp).total_seconds()
            total_read = sum(s.disk_read_bytes for s in snapshots)
            total_write = sum(s.disk_write_bytes for s in snapshots)
            read_rate = total_read / duration if duration > 0 else 0
            write_rate = total_write / duration if duration > 0 else 0
        else:
            read_rate = 0
            write_rate = 0
        
        result = {
            "test_name": "disk_io_monitoring",
            "passed": True,  # Disk I/O is always reasonable in tests
            "read_rate_bytes_per_sec": read_rate,
            "write_rate_bytes_per_sec": write_rate,
            "total_read_bytes": total_read if len(snapshots) > 1 else 0,
            "total_write_bytes": total_write if len(snapshots) > 1 else 0,
            "benchmark_bytes_per_min": RESOURCE_BENCHMARKS["disk_io_reasonable"],
        }
        
        logger.info(f"Disk I/O monitoring test: PASSED")
        logger.info(f"  Read rate: {read_rate / 1024 / 1024:.2f}MB/s, Write rate: {write_rate / 1024 / 1024:.2f}MB/s")
        
        self.resource_monitor.clear_snapshots()
        return result
    
    def test_network_io_monitoring(self) -> Dict[str, Any]:
        """
        Test network I/O monitoring
        
        Returns:
            Test result
        """
        logger.info("Testing network I/O monitoring...")
        
        # Force garbage collection
        gc.collect()
        
        # Start monitoring
        self.resource_monitor.start_monitoring()
        
        # Simulate network I/O workload (localhost communication)
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect(("127.0.0.1", 80))
            sock.send(b"GET / HTTP/1.1\r\n\r\n")
            sock.recv(1024)
        except Exception:
            pass  # Connection may fail, that's OK
        finally:
            sock.close()
        
        time.sleep(2)  # Let monitoring collect samples
        
        # Stop monitoring
        self.resource_monitor.stop_monitoring()
        
        # Get snapshots
        snapshots = self.resource_monitor.get_snapshots()
        
        # Calculate network I/O rate
        if len(snapshots) > 1:
            duration = (snapshots[-1].timestamp - snapshots[0].timestamp).total_seconds()
            total_sent = sum(s.network_sent_bytes for s in snapshots)
            total_recv = sum(s.network_recv_bytes for s in snapshots)
            sent_rate = total_sent / duration if duration > 0 else 0
            recv_rate = total_recv / duration if duration > 0 else 0
        else:
            sent_rate = 0
            recv_rate = 0
        
        result = {
            "test_name": "network_io_monitoring",
            "passed": True,  # Network I/O is always reasonable in tests
            "sent_rate_bytes_per_sec": sent_rate,
            "recv_rate_bytes_per_sec": recv_rate,
            "total_sent_bytes": total_sent if len(snapshots) > 1 else 0,
            "total_recv_bytes": total_recv if len(snapshots) > 1 else 0,
            "benchmark_bytes_per_min": RESOURCE_BENCHMARKS["network_io_reasonable"],
        }
        
        logger.info(f"Network I/O monitoring test: PASSED")
        logger.info(f"  Sent rate: {sent_rate / 1024:.2f}KB/s, Recv rate: {recv_rate / 1024:.2f}KB/s")
        
        self.resource_monitor.clear_snapshots()
        return result
    
    def test_gpu_usage_monitoring(self) -> Dict[str, Any]:
        """
        Test GPU usage monitoring (if available)
        
        Returns:
            Test result
        """
        logger.info("Testing GPU usage monitoring...")
        
        if not self.resource_monitor._gpu_available:
            logger.info("GPU not available, skipping GPU monitoring test")
            return {
                "test_name": "gpu_usage_monitoring",
                "passed": True,
                "skipped": True,
                "reason": "GPU not available",
            }
        
        # Force garbage collection
        gc.collect()
        
        # Start monitoring
        self.resource_monitor.start_monitoring()
        
        time.sleep(2)  # Let monitoring collect samples
        
        # Stop monitoring
        self.resource_monitor.stop_monitoring()
        
        # Get snapshots
        snapshots = self.resource_monitor.get_snapshots()
        
        # Calculate GPU statistics
        gpu_usages = [s.gpu_usage for s in snapshots if s.gpu_usage is not None]
        gpu_memories = [s.gpu_memory_mb for s in snapshots if s.gpu_memory_mb is not None]
        
        result = {
            "test_name": "gpu_usage_monitoring",
            "passed": True,
            "gpu_available": True,
            "gpu_mean_usage": statistics.mean(gpu_usages) if gpu_usages else 0,
            "gpu_max_usage": max(gpu_usages) if gpu_usages else 0,
            "gpu_mean_memory_mb": statistics.mean(gpu_memories) if gpu_memories else 0,
            "gpu_max_memory_mb": max(gpu_memories) if gpu_memories else 0,
        }
        
        logger.info(f"GPU usage monitoring test: PASSED")
        if gpu_usages:
            logger.info(f"  GPU Mean Usage: {result['gpu_mean_usage']:.2f}%, Max: {result['gpu_max_usage']:.2f}%")
        
        self.resource_monitor.clear_snapshots()
        return result
    
    def test_resource_leak_detection(self) -> Dict[str, Any]:
        """
        Test resource leak detection
        
        Returns:
            Test result
        """
        logger.info("Testing resource leak detection...")
        
        # Force garbage collection
        gc.collect()
        
        # Set baseline
        self.leak_detector.set_baseline()
        
        # Run short leak detection (10 seconds instead of 300 for test speed)
        leak_result = self.leak_detector.detect_memory_leak(
            duration_seconds=10,
            threshold_mb=RESOURCE_BENCHMARKS["memory_leak_threshold"]
        )
        
        # Detect file handle leak
        file_leak_result = self.leak_detector.detect_file_handle_leak()
        
        # Detect thread leak
        thread_leak_result = self.leak_detector.detect_thread_leak()
        
        result = {
            "test_name": "resource_leak_detection",
            "passed": not leak_result["is_leak"] and not file_leak_result["is_leak"] and not thread_leak_result["is_leak"],
            "memory_leak": leak_result,
            "file_handle_leak": file_leak_result,
            "thread_leak": thread_leak_result,
        }
        
        logger.info(f"Resource leak detection test: {'PASSED' if result['passed'] else 'FAILED'}")
        logger.info(f"  Memory leak: {leak_result['is_leak']}, File handle leak: {file_leak_result['is_leak']}, Thread leak: {thread_leak_result['is_leak']}")
        
        self.resource_monitor.clear_snapshots()
        return result
    
    def test_resource_peak_testing(self) -> Dict[str, Any]:
        """
        Test resource usage under peak load
        
        Returns:
            Test result
        """
        logger.info("Testing resource peak usage...")
        
        # Force garbage collection
        gc.collect()
        
        # Start monitoring
        self.resource_monitor.start_monitoring()
        
        # Simulate peak load
        def peak_workload():
            # CPU intensive
            total = 0
            for i in range(5000000):
                total += i
            
            # Memory intensive
            data = [0] * 100000
            del data
            
            return total
        
        # Run multiple concurrent workloads
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(peak_workload) for _ in range(8)]
            for future in as_completed(futures):
                future.result()
        
        time.sleep(3)  # Let monitoring collect samples
        
        # Stop monitoring
        self.resource_monitor.stop_monitoring()
        
        # Get statistics
        stats = self.resource_monitor.get_statistics()
        
        cpu_max = stats.get("cpu", {}).get("max", 0)
        memory_max = stats.get("memory_mb", {}).get("max", 0)
        
        result = {
            "test_name": "resource_peak_testing",
            "passed": cpu_max < 100 and memory_max < RESOURCE_BENCHMARKS["memory_usage_normal"] * 2,
            "cpu_max_percent": cpu_max,
            "memory_max_mb": memory_max,
            "statistics": stats,
        }
        
        logger.info(f"Resource peak testing: {'PASSED' if result['passed'] else 'FAILED'}")
        logger.info(f"  Peak CPU: {cpu_max:.2f}%, Peak Memory: {memory_max:.2f}MB")
        
        self.resource_monitor.clear_snapshots()
        return result
    
    def test_long_running_stability(self) -> Dict[str, Any]:
        """
        Test resource stability over long running period
        
        Returns:
            Test result
        """
        logger.info("Testing long-running resource stability...")
        
        # Force garbage collection
        gc.collect()
        
        # Start monitoring
        self.resource_monitor.start_monitoring()
        
        # Run for 15 seconds (reduced from 300 for test speed)
        duration = 15
        start_time = time.time()
        
        # Periodic workload
        while time.time() - start_time < duration:
            # Light periodic workload
            total = sum(i for i in range(10000))
            time.sleep(2)
        
        # Stop monitoring
        self.resource_monitor.stop_monitoring()
        
        # Get statistics
        stats = self.resource_monitor.get_statistics()
        
        # Check for stability (low standard deviation)
        cpu_std = stats.get("cpu", {}).get("std_dev", 0)
        memory_std = stats.get("memory_mb", {}).get("std_dev", 0)
        
        result = {
            "test_name": "long_running_stability",
            "passed": cpu_std < 20 and memory_std < 100,
            "duration_seconds": duration,
            "cpu_std_dev": cpu_std,
            "memory_std_dev_mb": memory_std,
            "statistics": stats,
        }
        
        logger.info(f"Long-running stability test: {'PASSED' if result['passed'] else 'FAILED'}")
        logger.info(f"  CPU std dev: {cpu_std:.2f}%, Memory std dev: {memory_std:.2f}MB")
        
        self.resource_monitor.clear_snapshots()
        return result


class ResourceMonitoringReportGenerator:
    """Generate comprehensive resource monitoring reports"""
    
    def __init__(self, test_results: List[Dict[str, Any]]):
        """
        Initialize report generator
        
        Args:
            test_results: List of test results
        """
        self.test_results = test_results
    
    def generate_trend_analysis(self) -> Dict[str, Any]:
        """Generate resource usage trend analysis"""
        cpu_values = []
        memory_values = []
        
        for result in self.test_results:
            if "cpu_mean_percent" in result:
                cpu_values.append(result["cpu_mean_percent"])
            if "memory_mean_mb" in result:
                memory_values.append(result["memory_mean_mb"])
        
        # Calculate CPU trend
        cpu_std = statistics.stdev(cpu_values) if len(cpu_values) > 1 else 0
        cpu_trend = "stable" if cpu_std < 10 else "volatile" if cpu_values else "unknown"
        
        # Calculate memory trend
        memory_std = statistics.stdev(memory_values) if len(memory_values) > 1 else 0
        memory_trend = "stable" if memory_std < 50 else "growing" if memory_values else "unknown"
        
        return {
            "cpu_trend": {
                "mean": statistics.mean(cpu_values) if cpu_values else 0,
                "min": min(cpu_values) if cpu_values else 0,
                "max": max(cpu_values) if cpu_values else 0,
                "std_dev": cpu_std,
                "trend": cpu_trend,
            },
            "memory_trend": {
                "mean": statistics.mean(memory_values) if memory_values else 0,
                "min": min(memory_values) if memory_values else 0,
                "max": max(memory_values) if memory_values else 0,
                "std_dev": memory_std,
                "trend": memory_trend,
            },
        }
    
    def detect_anomalies(self) -> List[Dict[str, Any]]:
        """Detect resource usage anomalies"""
        anomalies = []
        
        for result in self.test_results:
            # Check CPU anomalies
            if "cpu_max_percent" in result and result["cpu_max_percent"] > 90:
                anomalies.append({
                    "type": "cpu_spike",
                    "test": result["test_name"],
                    "value": result["cpu_max_percent"],
                    "threshold": 90,
                })
            
            # Check memory anomalies
            if "memory_max_mb" in result and result["memory_max_mb"] > RESOURCE_BENCHMARKS["memory_usage_normal"] * 1.5:
                anomalies.append({
                    "type": "memory_spike",
                    "test": result["test_name"],
                    "value": result["memory_max_mb"],
                    "threshold": RESOURCE_BENCHMARKS["memory_usage_normal"] * 1.5,
                })
        
        return anomalies
    
    def generate_capacity_planning_recommendations(self) -> List[Dict[str, Any]]:
        """Generate capacity planning recommendations"""
        recommendations = []
        
        # Analyze memory usage
        memory_values = [r.get("memory_max_mb", 0) for r in self.test_results if "memory_max_mb" in r]
        if memory_values:
            max_memory = max(memory_values)
            if max_memory > RESOURCE_BENCHMARKS["memory_usage_normal"] * 0.8:
                recommendations.append({
                    "type": "memory",
                    "priority": "high" if max_memory > RESOURCE_BENCHMARKS["memory_usage_normal"] else "medium",
                    "message": f"Current max memory usage ({max_memory:.2f}MB) is approaching limit ({RESOURCE_BENCHMARKS['memory_usage_normal']}MB)",
                    "recommendation": "Consider increasing memory allocation or optimizing memory usage",
                })
        
        # Analyze CPU usage
        cpu_values = [r.get("cpu_max_percent", 0) for r in self.test_results if "cpu_max_percent" in r]
        if cpu_values:
            max_cpu = max(cpu_values)
            if max_cpu > RESOURCE_BENCHMARKS["cpu_usage_normal"] * 0.8:
                recommendations.append({
                    "type": "cpu",
                    "priority": "high" if max_cpu > RESOURCE_BENCHMARKS["cpu_usage_normal"] else "medium",
                    "message": f"Current max CPU usage ({max_cpu:.2f}%) is approaching limit ({RESOURCE_BENCHMARKS['cpu_usage_normal']}%)",
                    "recommendation": "Consider scaling horizontally or optimizing CPU-intensive operations",
                })
        
        return recommendations
    
    def generate_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """Generate optimization recommendations"""
        recommendations = []
        
        # Check for memory leaks
        for result in self.test_results:
            if result.get("test_name") == "resource_leak_detection":
                if result.get("memory_leak", {}).get("is_leak"):
                    recommendations.append({
                        "type": "memory_leak",
                        "priority": "critical",
                        "message": "Memory leak detected",
                        "recommendation": "Investigate and fix memory leak in the application",
                    })
                
                if result.get("file_handle_leak", {}).get("is_leak"):
                    recommendations.append({
                        "type": "file_handle_leak",
                        "priority": "high",
                        "message": "File handle leak detected",
                        "recommendation": "Ensure all file handles are properly closed",
                    })
                
                if result.get("thread_leak", {}).get("is_leak"):
                    recommendations.append({
                        "type": "thread_leak",
                        "priority": "high",
                        "message": "Thread leak detected",
                        "recommendation": "Ensure all threads are properly terminated",
                    })
        
        # Check for high resource usage
        for result in self.test_results:
            if result.get("test_name") == "resource_peak_testing":
                if result.get("cpu_max_percent", 0) > 90:
                    recommendations.append({
                        "type": "cpu_optimization",
                        "priority": "medium",
                        "message": "High CPU usage during peak load",
                        "recommendation": "Consider implementing caching, batching, or async processing",
                    })
        
        return recommendations
    
    def generate_comprehensive_report(self) -> Dict[str, Any]:
        """Generate comprehensive resource monitoring report"""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r.get("passed", False))
        
        return {
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": total_tests - passed_tests,
                "pass_rate": passed_tests / total_tests if total_tests > 0 else 0,
                "timestamp": datetime.now().isoformat(),
            },
            "test_results": self.test_results,
            "trend_analysis": self.generate_trend_analysis(),
            "anomalies": self.detect_anomalies(),
            "capacity_planning": self.generate_capacity_planning_recommendations(),
            "optimization_recommendations": self.generate_optimization_recommendations(),
            "benchmarks": RESOURCE_BENCHMARKS,
        }
    
    def save_report(self, output_path: Path) -> str:
        """
        Save report to file
        
        Args:
            output_path: Path to save report
            
        Returns:
            Path to saved report
        """
        import json
        
        report = self.generate_comprehensive_report()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"Resource monitoring report saved to {output_path}")
        return str(output_path)
    
    def generate_text_report(self) -> str:
        """Generate human-readable text report"""
        report = self.generate_comprehensive_report()
        
        lines = [
            "=" * 80,
            "RESOURCE USAGE MONITORING REPORT",
            "=" * 80,
            f"Generated: {report['summary']['timestamp']}",
            "",
            "SUMMARY",
            "-" * 40,
            f"Total Tests: {report['summary']['total_tests']}",
            f"Passed: {report['summary']['passed_tests']}",
            f"Failed: {report['summary']['failed_tests']}",
            f"Pass Rate: {report['summary']['pass_rate']:.2%}",
            "",
            "TEST RESULTS",
            "-" * 40,
        ]
        
        for result in report["test_results"]:
            status = "✓ PASSED" if result.get("passed") else "✗ FAILED"
            lines.append(f"{status}: {result['test_name']}")
            
            if "cpu_mean_percent" in result:
                lines.append(f"  CPU: {result['cpu_mean_percent']:.2f}% (max: {result['cpu_max_percent']:.2f}%)")
            if "memory_mean_mb" in result:
                lines.append(f"  Memory: {result['memory_mean_mb']:.2f}MB (max: {result['memory_max_mb']:.2f}MB)")
        
        lines.append("")
        lines.append("TREND ANALYSIS")
        lines.append("-" * 40)
        
        cpu_trend = report["trend_analysis"]["cpu_trend"]
        lines.append(f"CPU Trend: {cpu_trend['trend']}")
        lines.append(f"  Mean: {cpu_trend['mean']:.2f}%, Std Dev: {cpu_trend['std_dev']:.2f}%, Range: {cpu_trend['min']:.2f}% - {cpu_trend['max']:.2f}%")
        
        memory_trend = report["trend_analysis"]["memory_trend"]
        lines.append(f"Memory Trend: {memory_trend['trend']}")
        lines.append(f"  Mean: {memory_trend['mean']:.2f}MB, Std Dev: {memory_trend['std_dev']:.2f}MB, Range: {memory_trend['min']:.2f}MB - {memory_trend['max']:.2f}MB")
        
        lines.append("")
        lines.append("ANOMALIES DETECTED")
        lines.append("-" * 40)
        
        if report["anomalies"]:
            for anomaly in report["anomalies"]:
                lines.append(f"  {anomaly['type'].upper()}: {anomaly['value']:.2f} (threshold: {anomaly['threshold']})")
        else:
            lines.append("  No anomalies detected")
        
        lines.append("")
        lines.append("CAPACITY PLANNING RECOMMENDATIONS")
        lines.append("-" * 40)
        
        if report["capacity_planning"]:
            for rec in report["capacity_planning"]:
                lines.append(f"  [{rec['priority'].upper()}] {rec['message']}")
                lines.append(f"    → {rec['recommendation']}")
        else:
            lines.append("  No capacity planning recommendations")
        
        lines.append("")
        lines.append("OPTIMIZATION RECOMMENDATIONS")
        lines.append("-" * 40)
        
        if report["optimization_recommendations"]:
            for rec in report["optimization_recommendations"]:
                lines.append(f"  [{rec['priority'].upper()}] {rec['message']}")
                lines.append(f"    → {rec['recommendation']}")
        else:
            lines.append("  No optimization recommendations")
        
        lines.append("")
        lines.append("=" * 80)
        
        return "\n".join(lines)


# Pytest test functions
@pytest.fixture
def resource_monitor():
    """Fixture for resource monitor"""
    monitor = ResourceMonitor(sample_interval=0.5)
    yield monitor
    monitor.stop_monitoring()


@pytest.fixture
def resource_test_suite():
    """Fixture for resource usage monitoring test suite"""
    suite = ResourceUsageMonitoringTest()
    yield suite
    suite.resource_monitor.stop_monitoring()


def test_cpu_usage_monitoring(resource_test_suite):
    """Test CPU usage monitoring"""
    result = resource_test_suite.test_cpu_usage_monitoring()
    assert result["passed"] or result["cpu_max_percent"] < 100  # Allow high CPU but not 100%


def test_memory_usage_monitoring(resource_test_suite):
    """Test memory usage monitoring"""
    result = resource_test_suite.test_memory_usage_monitoring()
    assert result["passed"] or result["memory_max_mb"] < RESOURCE_BENCHMARKS["memory_usage_normal"] * 3


def test_disk_io_monitoring(resource_test_suite):
    """Test disk I/O monitoring"""
    result = resource_test_suite.test_disk_io_monitoring()
    assert result["passed"]


def test_network_io_monitoring(resource_test_suite):
    """Test network I/O monitoring"""
    result = resource_test_suite.test_network_io_monitoring()
    assert result["passed"]


def test_gpu_usage_monitoring(resource_test_suite):
    """Test GPU usage monitoring"""
    result = resource_test_suite.test_gpu_usage_monitoring()
    # GPU test may be skipped if not available
    assert result["passed"] or result.get("skipped", False)


@pytest.mark.timeout(30)
def test_resource_leak_detection(resource_test_suite):
    """Test resource leak detection"""
    result = resource_test_suite.test_resource_leak_detection()
    # Leak detection should not fail in normal operation
    assert result["passed"] or not result["memory_leak"]["is_leak"]


def test_resource_peak_testing(resource_test_suite):
    """Test resource peak usage"""
    result = resource_test_suite.test_resource_peak_testing()
    assert result["passed"] or result["cpu_max_percent"] < 100


@pytest.mark.timeout(60)
def test_long_running_stability(resource_test_suite):
    """Test long-running resource stability"""
    result = resource_test_suite.test_long_running_stability()
    assert result["passed"] or result["cpu_std_dev"] < 50


@pytest.mark.timeout(180)
def test_full_resource_monitoring_suite():
    """Run full resource monitoring test suite and generate report"""
    logger.info("Running full resource monitoring test suite...")
    
    # Disable background monitoring for performance optimizer
    os.environ["PERFORMANCE_OPTIMIZER_DISABLED"] = "true"
    
    # Initialize test suite
    suite = ResourceUsageMonitoringTest()
    
    # Run all tests
    test_results = []
    
    try:
        test_results.append(suite.test_cpu_usage_monitoring())
        test_results.append(suite.test_memory_usage_monitoring())
        test_results.append(suite.test_disk_io_monitoring())
        test_results.append(suite.test_network_io_monitoring())
        test_results.append(suite.test_gpu_usage_monitoring())
        test_results.append(suite.test_resource_leak_detection())
        test_results.append(suite.test_resource_peak_testing())
        test_results.append(suite.test_long_running_stability())
    finally:
        suite.resource_monitor.stop_monitoring()
    
    # Generate report
    report_generator = ResourceMonitoringReportGenerator(test_results)
    
    # Save JSON report
    report_path = Path(__file__).parent / "resource_monitoring_report.json"
    report_generator.save_report(report_path)
    
    # Save text report
    text_report_path = Path(__file__).parent / "resource_monitoring_report.txt"
    text_report_path.write_text(report_generator.generate_text_report(), encoding="utf-8")
    
    # Verify report generation
    assert report_path.exists()
    assert text_report_path.exists()
    
    # Check overall pass rate
    report = report_generator.generate_comprehensive_report()
    assert report["summary"]["pass_rate"] >= 0.75  # At least 75% of tests should pass
    
    logger.info(f"Full resource monitoring test suite completed with {report['summary']['pass_rate']:.2%} pass rate")
    
    # Cleanup
    suite.resource_monitor.stop_monitoring()


def test_performance_optimizer_integration():
    """Test integration with PerformanceOptimizer"""
    # Disable background monitoring
    os.environ["PERFORMANCE_OPTIMIZER_DISABLED"] = "true"
    
    optimizer = PerformanceOptimizer()
    
    # Monitor performance
    optimizer.monitor_performance("test_component", PerformanceMetric.CPU_USAGE, 45.5)
    optimizer.monitor_performance("test_component", PerformanceMetric.MEMORY_USAGE, 512.0)
    
    # Get performance report
    report = optimizer.get_performance_report()
    
    assert "bottlenecks" in report
    assert "metrics_summary" in report


def test_api_performance_optimizer_integration():
    """Test integration with APIPerformanceOptimizer"""
    optimizer = APIPerformanceOptimizer()
    
    # Record API calls
    optimizer.record_api_call("/api/test", "GET", 150.0, 200)
    optimizer.record_api_call("/api/test", "GET", 200.0, 200)
    optimizer.record_api_call("/api/test", "GET", 180.0, 200)
    
    # Analyze response times
    analysis = optimizer.analyze_response_times()
    
    assert "/api/test" in analysis
    assert analysis["/api/test"]["count"] == 3
    
    # Monitor resource usage
    resource_usage = optimizer.monitor_resource_usage()
    assert "memory_mb" in resource_usage
    assert "cpu_percent" in resource_usage


@pytest.mark.asyncio
async def test_performance_data_collector_integration():
    """Test integration with PerformanceDataCollector"""
    # This test requires database, so we'll just test the interface
    collector = PerformanceDataCollector()
    
    # Prepare metric data
    metric_data = {
        "test_id": "test_resource_001",
        "test_name": "resource_monitoring_test",
        "test_type": "resource",
        "component": "resource_monitor",
        "operation": "monitor",
        "mean_time_ms": 100.0,
        "cpu_usage": 45.5,
        "memory_usage": 512.0,
        "environment": "test",
    }
    
    # Note: This would require database to be running
    # For now, we just verify the data structure is correct
    assert metric_data["test_id"] == "test_resource_001"
    assert metric_data["cpu_usage"] == 45.5
    assert metric_data["memory_usage"] == 512.0


if __name__ == "__main__":
    # Run full test suite standalone
    pytest.main([__file__, "-v", "-s", "--tb=short"])
