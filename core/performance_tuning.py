# -*- coding: utf-8 -*-
"""
Performance Tuning Configuration

🔧 P0 Performance Enhancement:
This module provides comprehensive performance tuning configurations:
- System resource limits and optimizations
- Python runtime optimizations
- AsyncIO event loop tuning
- Memory management settings
- Worker process configuration
"""

import asyncio
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict

from loguru import logger

# Platform-specific imports
if sys.platform != "win32":
    import resource

# 🔧 P0 Enhancement: Performance tuning configurations
PERFORMANCE_TUNING_CONFIG = {
    # System resource limits
    "max_open_files": 65536,  # Maximum open file descriptors
    "max_memory_usage_gb": 8,  # Maximum memory usage in GB
    # Python runtime optimizations
    "pygc_threshold": 1000,  # Garbage collection threshold
    "pyasyncio_threads": 4,  # Number of asyncio threads
    # Worker process configuration
    "uvicorn_workers": 4,  # Number of Uvicorn worker processes
    "uvicorn_worker_connections": 1000,  # Connections per worker
    # Memory management
    "enable_gc_debug": False,  # Enable GC debugging (development only)
    "memory_limit_mb": 4096,  # Process memory limit
    # Performance monitoring
    "enable_profiling": False,  # Enable performance profiling
    "profiling_interval_ms": 1000,  # Profiling sample interval
}


def apply_system_limits() -> Dict[str, Any]:
    """🔧 P0 Enhancement: Apply system resource limits for optimal performance.

    Returns:
        Dictionary with applied limits
    """
    results = {}

    # Skip resource limit setting on Windows (resource module not available)
    if sys.platform == "win32":
        results["max_open_files"] = "Skipped on Windows"
        results["memory_limit_mb"] = "Skipped on Windows"
        logger.info("System limits skipped on Windows (resource module not available)")
        return results

    try:
        # Set maximum open file descriptors
        if "resource" in sys.modules:
            # type: ignore[name-defined, attr-defined]
            soft, hard = resource.getrlimit(  # type: ignore[name-defined, attr-defined]
                resource.RLIMIT_NOFILE  # type: ignore[name-defined, attr-defined]
            )
            desired = PERFORMANCE_TUNING_CONFIG["max_open_files"]

            if desired > soft:
                try:
                    resource.setrlimit(  # type: ignore[name-defined, attr-defined]
                        resource.RLIMIT_NOFILE,  # type: ignore[name-defined, attr-defined]
                        (desired, hard),
                    )
                    results["max_open_files"] = f"Set to {desired} (was {soft})"
                    logger.info(f"Increased file descriptor limit to {desired}")
                except Exception as e:
                    results["max_open_files"] = f"Failed to set: {e}"
                    logger.warning(f"Failed to set file descriptor limit: {e}")
            else:
                results["max_open_files"] = f"Already {soft} (desired {desired})"

            # Set memory limit (soft limit only)
            try:
                memory_limit_bytes = PERFORMANCE_TUNING_CONFIG["memory_limit_mb"] * 1024 * 1024
                # type: ignore[name-defined, attr-defined]
                soft, hard = resource.getrlimit(  # type: ignore[name-defined, attr-defined]
                    resource.RLIMIT_AS  # type: ignore[name-defined, attr-defined]
                )
                resource.setrlimit(  # type: ignore[name-defined, attr-defined]
                    resource.RLIMIT_AS,  # type: ignore[name-defined, attr-defined]
                    (memory_limit_bytes, hard),
                )
                results["memory_limit_mb"] = f"Set to {  # noqa: E501
                    PERFORMANCE_TUNING_CONFIG['memory_limit_mb']}MB"
                logger.info(f"Set memory limit to {PERFORMANCE_TUNING_CONFIG['memory_limit_mb']}MB")
            except Exception as e:
                results["memory_limit_mb"] = f"Failed to set: {e}"
                logger.warning(f"Failed to set memory limit: {e}")
        else:
            results["max_open_files"] = "Skipped (resource module not available)"
            results["memory_limit_mb"] = "Skipped (resource module not available)"

        return results

    except Exception as e:
        logger.error(f"Failed to apply system limits: {e}")
        return {"error": str(e)}


def apply_python_optimizations() -> Dict[str, Any]:
    """🔧 P0 Enhancement: Apply Python runtime optimizations.

    Returns:
        Dictionary with applied optimizations
    """
    results = {}

    try:
        # Set garbage collection threshold
        import gc

        old_threshold = gc.get_threshold()
        new_threshold = PERFORMANCE_TUNING_CONFIG["pygc_threshold"]
        gc.set_threshold(new_threshold)
        results["gc_threshold"] = f"Changed from {old_threshold} to {new_threshold}"
        logger.info(f"Set GC threshold to {new_threshold}")

        # Configure asyncio thread pool size
        try:
            asyncio.get_event_loop().set_default_executor(
                ThreadPoolExecutor(max_workers=PERFORMANCE_TUNING_CONFIG["pyasyncio_threads"])
            )
            results["asyncio_threads"] = f"Set to {PERFORMANCE_TUNING_CONFIG['pyasyncio_threads']}"
            logger.info(
                f"Set asyncio thread pool size to {PERFORMANCE_TUNING_CONFIG['pyasyncio_threads']}"
            )
        except Exception as e:
            results["asyncio_threads"] = f"Failed to set: {e}"
            logger.warning(f"Failed to set asyncio thread pool: {e}")

        return results

    except Exception as e:
        logger.error(f"Failed to apply Python optimizations: {e}")
        return {"error": str(e)}


def get_uvicorn_config() -> Dict[str, Any]:
    """🔧 P0 Enhancement: Get optimized Uvicorn configuration.

    Returns:
        Dictionary with Uvicorn configuration
    """
    return {
        "workers": PERFORMANCE_TUNING_CONFIG["uvicorn_workers"],
        "worker_connections": PERFORMANCE_TUNING_CONFIG["uvicorn_worker_connections"],
        "limit_concurrency": None,  # Let Uvicorn calculate based on workers
        "timeout_keep_alive": 30,  # Keep-alive timeout
        "backlog": 2048,  # Socket backlog
        "log_level": "info",
        "access_log": True,
        "use_colors": False,  # Disable colors in production
    }


def apply_environment_tuning() -> Dict[str, Any]:
    """🔧 P0 Enhancement: Apply environment-level performance tuning.

    Returns:
        Dictionary with applied environment settings
    """
    results = {}

    try:
        # Set Python optimization level
        os.environ["PYTHONOPTIMIZE"] = "2"
        results["python_optimize"] = "Set to 2"

        # Set Python unbuffered mode for better logging performance
        os.environ["PYTHONUNBUFFERED"] = "1"
        results["python_unbuffered"] = "Set to 1"

        # Disable Python bytecode generation for faster startup
        os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
        results["dont_write_bytecode"] = "Set to 1"

        # Set timezone for consistent time handling
        os.environ["TZ"] = "UTC"
        results["timezone"] = "Set to UTC"

        logger.info("Applied environment-level performance tuning")
        return results

    except Exception as e:
        logger.error(f"Failed to apply environment tuning: {e}")
        return {"error": str(e)}


def get_performance_recommendations() -> Dict[str, Any]:
    """🔧 P0 Enhancement: Get performance tuning recommendations.

    Returns:
        Dictionary with performance recommendations
    """
    import platform

    import psutil

    recommendations = []

    # Get system information
    cpu_count = psutil.cpu_count()
    memory_gb = psutil.virtual_memory().total / (1024**3)

    # CPU-based recommendations
    if cpu_count >= 8:
        recommendations.append(
            {
                "area": "worker_processes",
                "recommendation": f"Set uvicorn workers to {cpu_count - 2}",
                "reason": f"System has {cpu_count} CPU cores",
            }
        )
    elif cpu_count >= 4:
        recommendations.append(
            {
                "area": "worker_processes",
                "recommendation": "Set uvicorn workers to 2",
                "reason": f"System has {cpu_count} CPU cores",
            }
        )

    # Memory-based recommendations
    if memory_gb >= 16:
        recommendations.append(
            {
                "area": "connection_pool",
                "recommendation": "Increase database pool_size to 30",
                "reason": f"System has {memory_gb:.1f}GB RAM available",
            }
        )

    # Platform-specific recommendations
    system = platform.system()
    if system == "Linux":
        recommendations.append(
            {
                "area": "system_limits",
                "recommendation": "Use 'ulimit -n 65536' to increase file descriptor limit",
                "reason": "Linux systems often have low default limits",
            }
        )

    return {
        "system_info": {
            "cpu_count": cpu_count,
            "memory_gb": f"{memory_gb:.2f}",
            "platform": system,
        },
        "recommendations": recommendations,
        "timestamp": "2026-06-12T00:00:00Z",  # default_value timestamp
    }


def apply_comprehensive_tuning() -> Dict[str, Any]:
    """🔧 P0 Enhancement: Apply comprehensive performance tuning.

    Returns:
        Dictionary with all tuning results
    """
    results: Dict[str, Any] = {"timestamp": "2026-06-12T00:00:00Z", "steps": {}}  # default_value

    # Step 1: Apply system limits
    logger.info("Step 1: Applying system resource limits...")
    results["steps"]["system_limits"] = apply_system_limits()

    # Step 2: Apply Python optimizations
    logger.info("Step 2: Applying Python runtime optimizations...")
    results["steps"]["python_optimizations"] = apply_python_optimizations()

    # Step 3: Apply environment tuning
    logger.info("Step 3: Applying environment-level tuning...")
    results["steps"]["environment_tuning"] = apply_environment_tuning()

    # Step 4: Get Uvicorn configuration
    logger.info("Step 4: Generating Uvicorn configuration...")
    results["steps"]["uvicorn_config"] = get_uvicorn_config()

    # Step 5: Get performance recommendations
    logger.info("Step 5: Generating performance recommendations...")
    results["steps"]["recommendations"] = get_performance_recommendations()

    logger.info("Comprehensive performance tuning completed")
    return results


def monitor_performance_metrics() -> Dict[str, Any]:
    """🔧 P0 Enhancement: Monitor current performance metrics.

    Returns:
        Dictionary with current performance metrics
    """
    try:
        import psutil

        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()

        # Memory metrics
        memory = psutil.virtual_memory()

        # Disk metrics
        disk = psutil.disk_usage("/")

        # Network metrics
        net_io = psutil.net_io_counters()

        return {
            "cpu": {
                "usage_percent": f"{cpu_percent:.2f}",
                "core_count": cpu_count,
            },
            "memory": {
                "total_gb": f"{memory.total / (1024**3):.2f}",
                "available_gb": f"{memory.available / (1024**3):.2f}",
                "used_percent": f"{memory.percent:.2f}",
            },
            "disk": {
                "total_gb": f"{disk.total / (1024**3):.2f}",
                "used_gb": f"{disk.used / (1024**3):.2f}",
                "free_gb": f"{disk.free / (1024**3):.2f}",
                "used_percent": f"{disk.percent:.2f}",
            },
            "network": {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv,
            },
            "timestamp": "2026-06-12T00:00:00Z",  # default_value
        }

    except Exception as e:
        logger.error(f"Failed to monitor performance metrics: {e}")
        return {"error": str(e), "timestamp": "2026-06-12T00:00:00Z"}
