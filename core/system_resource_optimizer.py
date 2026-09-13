# -*- coding: utf-8 -*-
"""
System Resource Optimizer
Integrates memory, CPU, and network optimization modules
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from loguru import logger


def _contains_error(payload: Any) -> bool:
    """Recursively check a (possibly nested) result payload for an error entry."""
    if isinstance(payload, dict):
        if payload.get("error"):
            return True
        return any(_contains_error(value) for value in payload.values())
    if isinstance(payload, (list, tuple)):
        return any(_contains_error(value) for value in payload)
    return False


@dataclass
class SystemResourceStatus:
    """System resource optimization status"""

    memory_optimization_enabled: bool = False
    cpu_optimization_enabled: bool = False
    network_optimization_enabled: bool = False
    last_optimization_run: Optional[datetime] = None
    total_optimizations_applied: int = 0
    current_memory_mb: float = 0.0
    current_cpu_percent: float = 0.0


class SystemResourceOptimizer:
    """
    Unified system resource optimizer
    Integrates memory, CPU, and network optimization
    """

    def __init__(self):
        """Initialize system resource optimizer"""
        self.status = SystemResourceStatus()
        self.memory_optimizer = None
        self.cpu_optimizer = None

        # Try to load optimization modules
        self._load_optimization_modules()

        logger.info("System resource optimizer initialized")

    def _load_optimization_modules(self):
        """Load system resource optimization modules"""
        try:
            from core.memory_usage_optimizer import MemoryUsageOptimizer

            self.memory_optimizer = MemoryUsageOptimizer()
            self.status.memory_optimization_enabled = True
            logger.info("Memory usage optimizer loaded")
        except Exception as e:
            logger.warning(f"Failed to load memory optimizer: {e}")

        try:
            from core.cpu_usage_optimizer import CPUUsageOptimizer

            self.cpu_optimizer = CPUUsageOptimizer()
            self.status.cpu_optimization_enabled = True
            logger.info("CPU usage optimizer loaded")
        except Exception as e:
            logger.warning(f"Failed to load CPU optimizer: {e}")

        # Network optimization is handled at the infrastructure level
        self.status.network_optimization_enabled = True

    def analyze_memory_usage(self) -> Dict[str, Any]:
        """
        Analyze memory usage

        Returns:
            Memory usage analysis
        """
        if not self.memory_optimizer:
            return {"error": "Memory optimizer not available"}

        try:
            # Get current memory snapshot (real MemoryUsageOptimizer API)
            snapshot = self.memory_optimizer.take_memory_snapshot("system")

            # Statistics captured by the optimizer
            statistics = self.memory_optimizer.get_memory_statistics()

            # Detect memory leaks
            leaks = self.memory_optimizer.detect_memory_leaks("system")

            self.status.current_memory_mb = snapshot.used_memory_mb

            return {
                "current_usage_mb": snapshot.used_memory_mb,
                "memory_percent": snapshot.memory_percent,
                "gc_objects": snapshot.gc_objects,
                "statistics": statistics,
                "leaks_detected": len(leaks),
                "leak_details": [
                    {
                        "component": leak.component,
                        "leak_size_mb": leak.leak_size_mb,
                        "severity": leak.severity,
                    }
                    for leak in leaks[:5]
                ],
            }
        except Exception as e:
            logger.error(f"Error analyzing memory usage: {e}")
            return {"error": str(e)}

    def optimize_memory(self) -> Dict[str, Any]:
        """
        Optimize memory usage

        Returns:
            Memory optimization results
        """
        if not self.memory_optimizer:
            return {"error": "Memory optimizer not available"}

        try:
            # Run garbage collection
            gc_result = self.memory_optimizer.collect_garbage()

            # Apply memory optimizations for the system component
            optimization = self.memory_optimizer.optimize_memory("system")

            actions = optimization.get("actions_taken", []) if isinstance(optimization, dict) else []

            return {
                "garbage_collection": gc_result,
                "optimization": optimization,
                "optimizations_applied": len(actions),
            }
        except Exception as e:
            logger.error(f"Error optimizing memory: {e}")
            return {"error": str(e)}

    def analyze_cpu_usage(self) -> Dict[str, Any]:
        """
        Analyze CPU usage

        Returns:
            CPU usage analysis
        """
        if not self.cpu_optimizer:
            return {"error": "CPU optimizer not available"}

        try:
            # Get current CPU snapshot (real CPUUsageOptimizer API)
            snapshot = self.cpu_optimizer.take_cpu_snapshot("system")

            # Statistics captured by the optimizer
            statistics = self.cpu_optimizer.get_cpu_statistics()

            # Detect CPU spikes / sustained high usage
            spike = self.cpu_optimizer.detect_cpu_spike("system")
            high_usage = self.cpu_optimizer.detect_high_usage("system")

            self.status.current_cpu_percent = snapshot.cpu_percent

            return {
                "current_cpu_percent": snapshot.cpu_percent,
                "per_cpu_percent": snapshot.per_cpu_percent,
                "load_average": snapshot.load_average,
                "process_count": snapshot.process_count,
                "statistics": statistics,
                "spike_detected": spike,
                "high_usage_detected": high_usage,
                "spikes_detected": 1 if spike else 0,
            }
        except Exception as e:
            logger.error(f"Error analyzing CPU usage: {e}")
            return {"error": str(e)}

    def optimize_cpu(self) -> Dict[str, Any]:
        """
        Optimize CPU usage

        Returns:
            CPU optimization results
        """
        if not self.cpu_optimizer:
            return {"error": "CPU optimizer not available"}

        try:
            # Apply CPU optimizations (real CPUUsageOptimizer API)
            optimization = self.cpu_optimizer.optimize_cpu("system")

            actions = optimization.get("actions_taken", []) if isinstance(optimization, dict) else []

            return {
                "optimization": optimization,
                "optimizations_applied": len(actions),
            }
        except Exception as e:
            logger.error(f"Error optimizing CPU: {e}")
            return {"error": str(e)}

    def optimize_network(self) -> Dict[str, Any]:
        """
        Optimize network usage

        Returns:
            Network optimization results
        """
        try:
            # Network optimization is primarily handled at infrastructure level
            # Here we provide monitoring and basic optimization recommendations

            import psutil

            # Get network I/O stats
            net_io = psutil.net_io_counters()

            # Get network connections
            connections = psutil.net_connections()

            return {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv,
                "active_connections": len([c for c in connections if c.status == "ESTABLISHED"]),
                "recommendations": [
                    "Enable connection pooling for HTTP clients",
                    "Implement data compression for large payloads",
                    "Use connection keep-alive where appropriate",
                    "Consider CDN for static content delivery",
                ],
            }
        except Exception as e:
            logger.error(f"Error optimizing network: {e}")
            return {"error": str(e)}

    def run_comprehensive_optimization(self) -> Dict[str, Any]:
        """
        Run comprehensive system resource optimization

        Returns:
            Comprehensive optimization results
        """
        results: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "memory_optimization": None,
            "cpu_optimization": None,
            "network_optimization": None,
            "overall_status": "partial",
        }

        # Run memory optimization
        if self.memory_optimizer:
            try:
                results["memory_optimization"] = {
                    "analysis": self.analyze_memory_usage(),
                    "optimization": self.optimize_memory(),
                }
            except Exception as e:
                results["memory_optimization"] = {"error": str(e)}

        # Run CPU optimization
        if self.cpu_optimizer:
            try:
                results["cpu_optimization"] = {
                    "analysis": self.analyze_cpu_usage(),
                    "optimization": self.optimize_cpu(),
                }
            except Exception as e:
                results["cpu_optimization"] = {"error": str(e)}

        # Run network optimization
        try:
            results["network_optimization"] = self.optimize_network()
        except Exception as e:
            results["network_optimization"] = {"error": str(e)}

        # Determine overall status by inspecting nested results for real errors.
        successful_count = sum(
            1
            for result in [
                results["memory_optimization"],
                results["cpu_optimization"],
                results["network_optimization"],
            ]
            if result is not None and not _contains_error(result)
        )

        if successful_count == 3:
            results["overall_status"] = "complete"
        elif successful_count > 0:
            results["overall_status"] = "partial"
        else:
            results["overall_status"] = "failed"

        # Update status
        self.status.last_optimization_run = datetime.now(timezone.utc)
        if successful_count > 0:
            self.status.total_optimizations_applied += 1

        return results

    def get_optimization_status(self) -> Dict[str, Any]:
        """
        Get current optimization status

        Returns:
            Current status
        """
        return {
            "memory_optimization_enabled": self.status.memory_optimization_enabled,
            "cpu_optimization_enabled": self.status.cpu_optimization_enabled,
            "network_optimization_enabled": self.status.network_optimization_enabled,
            "last_optimization_run": (
                self.status.last_optimization_run.isoformat()
                if self.status.last_optimization_run
                else None
            ),
            "total_optimizations_applied": self.status.total_optimizations_applied,
            "current_memory_mb": self.status.current_memory_mb,
            "current_cpu_percent": self.status.current_cpu_percent,
        }

    def get_resource_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive resource summary

        Returns:
            Resource summary
        """
        summary = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "optimization_status": self.get_optimization_status(),
        }

        # Add memory analysis
        if self.memory_optimizer:
            try:
                summary["memory"] = self.analyze_memory_usage()
            except Exception as e:
                summary["memory"] = {"error": str(e)}

        # Add CPU analysis
        if self.cpu_optimizer:
            try:
                summary["cpu"] = self.analyze_cpu_usage()
            except Exception as e:
                summary["cpu"] = {"error": str(e)}

        # Add network analysis
        try:
            summary["network"] = self.optimize_network()
        except Exception as e:
            summary["network"] = {"error": str(e)}

        return summary


# Global instance
_resource_optimizer: Optional[SystemResourceOptimizer] = None


def get_system_resource_optimizer() -> SystemResourceOptimizer:
    """
    Get the global system resource optimizer instance

    Returns:
        SystemResourceOptimizer instance
    """
    global _resource_optimizer
    if _resource_optimizer is None:
        _resource_optimizer = SystemResourceOptimizer()
    return _resource_optimizer
