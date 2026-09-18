# -*- coding: utf-8 -*-
"""
behavior_monitor.py
-------------------
Agent behavior anomaly detection (O21).

Tracks per-agent execution metrics such as iteration count, tool call
frequency, repeated tool usage and error rate. When thresholds are
exceeded an anomaly alert is emitted so the orchestrator can take
action (e.g. terminate the agent or raise a HITL approval).

Enhanced with z-score based anomaly detection and performance optimization.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# 导入配置和算法模块
try:
    from behavior_monitor_config import load_config, get_current_environment, BehaviorMonitorConfig
    from core.agent.monitoring_config_validator import ConfigValidator
    from core.agent.monitoring_config_analyzer import ConfigAnalyzer
    from core.agent.monitoring_algorithms import WelfordStats, RobustAnomalyDetector, HybridSwitcher
    from core.agent.monitoring_performance import ShardedStatsManager
    Z_SCORE_ENABLED = True
except ImportError:
    Z_SCORE_ENABLED = False
    logger.warning("z-score功能依赖模块未加载，将使用固定阈值模式")


@dataclass
class _AgentMetrics:
    agent_id: str
    iterations: int = 0
    tool_calls: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    actions: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    errors: int = 0
    start_time: float = field(default_factory=time.time)
    alerts: List[Dict[str, Any]] = field(default_factory=list)


class BehaviorMonitor:
    """Lightweight in-memory behavior monitor for autonomous agents."""

    # Thresholds
    MAX_ITERATIONS = 50
    MAX_TOTAL_TOOL_CALLS = 100
    MAX_TOOL_REPETITIONS = 10
    MAX_ERRORS = 10
    MAX_EXECUTION_TIME_SECONDS = 300

    def __init__(self, config: Optional[BehaviorMonitorConfig] = None):
        self._metrics: Dict[str, _AgentMetrics] = {}
        self._thresholds = {
            "max_iterations": self.MAX_ITERATIONS,
            "max_total_tool_calls": self.MAX_TOTAL_TOOL_CALLS,
            "max_tool_repetitions": self.MAX_TOOL_REPETITIONS,
            "max_errors": self.MAX_ERRORS,
            "max_execution_time_seconds": self.MAX_EXECUTION_TIME_SECONDS,
        }

        # z-score功能相关
        self._z_score_enabled = Z_SCORE_ENABLED

        # 性能监控（始终初始化）
        self._performance_metrics = {
            "check_anomaly_calls": 0,
            "total_check_time": 0.0,
            "z_score_checks": 0,
            "fixed_threshold_checks": 0
        }

        if self._z_score_enabled:
            # 加载和验证配置
            self.config = config or load_config(get_current_environment())
            is_valid, errors = ConfigValidator.validate_config(self.config)
            if not is_valid:
                logger.error(f"配置参数无效: {errors}")
                self._z_score_enabled = False
            else:
                ConfigValidator.log_config_summary(self.config)
                # 分析配置合理性
                memory_analysis = ConfigAnalyzer.analyze_memory_requirements(self.config)
                logger.info(f"内存需求分析: {memory_analysis}")

            # 初始化算法组件
            if self._z_score_enabled:
                self._stats_manager = ShardedStatsManager(num_shards=4)
                self._anomaly_detector = RobustAnomalyDetector()
                self._switcher = HybridSwitcher()
                self._stats_baselines: Dict[str, Dict[str, WelfordStats]] = {}

    def _get_or_create(self, agent_id: str) -> _AgentMetrics:
        if agent_id not in self._metrics:
            self._metrics[agent_id] = _AgentMetrics(agent_id=agent_id)
        return self._metrics[agent_id]

    def set_thresholds(self, **kwargs) -> None:
        """Override default thresholds (e.g. for testing)."""
        self._thresholds.update(kwargs)

    def record_iteration(self, agent_id: str) -> None:
        """Record one execution iteration."""
        metrics = self._get_or_create(agent_id)
        metrics.iterations += 1

    def record_tool_call(self, agent_id: str, tool_name: str) -> None:
        """Record a tool invocation."""
        metrics = self._get_or_create(agent_id)
        metrics.tool_calls[tool_name] += 1

    def record_action(self, agent_id: str, action_key: str) -> None:
        """Record a concrete action signature (goal + tool + normalized params)."""
        metrics = self._get_or_create(agent_id)
        metrics.actions[action_key] += 1

    def record_error(self, agent_id: str) -> None:
        """Record an execution error."""
        metrics = self._get_or_create(agent_id)
        metrics.errors += 1

    def check_anomaly(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Check whether the agent has exceeded any behavior threshold."""
        # 性能监控
        import time
        start_time = time.perf_counter()

        try:
            # 如果启用z-score功能，根据条件选择检测方法
            if self._z_score_enabled and self._should_use_z_score(agent_id):
                self._performance_metrics["z_score_checks"] += 1
                return self._check_anomaly_z_score(agent_id)
            else:
                self._performance_metrics["fixed_threshold_checks"] += 1
                return self._check_anomaly_fixed_threshold(agent_id)
        finally:
            # 更新性能指标
            elapsed = time.perf_counter() - start_time
            self._performance_metrics["check_anomaly_calls"] += 1
            self._performance_metrics["total_check_time"] += elapsed

    def _should_use_z_score(self, agent_id: str) -> bool:
        """判断是否应该使用z-score（混合切换条件）"""
        if not self._z_score_enabled:
            return False

        if agent_id not in self._metrics:
            return False

        metrics = self._metrics[agent_id]

        # 检查样本数量
        sample_count = metrics.iterations
        if sample_count < self.config.min_samples_for_z_score:
            return False

        # 检查时间跨度
        elapsed_days = (time.time() - metrics.start_time) / (24 * 3600)

        # 使用切换器判断
        should_switch, reason = self._switcher.should_use_z_score(sample_count, elapsed_days)
        logger.debug(f"z-score切换判断: {reason}")

        return should_switch

    def _update_stats_baseline(self, agent_id: str) -> None:
        """更新统计基线"""
        if agent_id not in self._metrics:
            return

        metrics = self._metrics[agent_id]

        # 更新各项指标的统计基线
        iterations_stats = self._stats_manager.get_or_create(agent_id, "iterations")
        iterations_stats.update(metrics.iterations)

        total_tool_calls = sum(metrics.tool_calls.values())
        tool_calls_stats = self._stats_manager.get_or_create(agent_id, "tool_calls")
        tool_calls_stats.update(total_tool_calls)

        errors_stats = self._stats_manager.get_or_create(agent_id, "errors")
        errors_stats.update(metrics.errors)

    def _check_anomaly_z_score(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """使用z-score进行异常检测"""
        metrics = self._get_or_create(agent_id)
        alerts: List[str] = []

        # 更新统计基线
        self._update_stats_baseline(agent_id)

        # 检查迭代次数
        iterations_stats = self._stats_manager.get_or_create(agent_id, "iterations")
        iterations_result = self._anomaly_detector.detect_with_fallback(
            metrics.iterations,
            iterations_stats,
            fixed_threshold=self._thresholds["max_iterations"]
        )

        if iterations_result["is_anomaly"]:
            severity = self._anomaly_detector.get_severity_from_z_score(
                iterations_result.get("z_score", 0)
            )
            alerts.append(
                f"iterations anomaly (z-score: {iterations_result.get('z_score', 0):.2f}, "
                f"severity: {severity}, method: {iterations_result['method']})"
            )

        # 检查工具调用总数
        total_tool_calls = sum(metrics.tool_calls.values())
        tool_calls_stats = self._stats_manager.get_or_create(agent_id, "tool_calls")
        tool_calls_result = self._anomaly_detector.detect_with_fallback(
            total_tool_calls,
            tool_calls_stats,
            fixed_threshold=self._thresholds["max_total_tool_calls"]
        )

        if tool_calls_result["is_anomaly"]:
            severity = self._anomaly_detector.get_severity_from_z_score(
                tool_calls_result.get("z_score", 0)
            )
            alerts.append(
                f"tool calls anomaly (z-score: {tool_calls_result.get('z_score', 0):.2f}, "
                f"severity: {severity}, method: {tool_calls_result['method']})"
            )

        # 检查错误次数
        errors_stats = self._stats_manager.get_or_create(agent_id, "errors")
        errors_result = self._anomaly_detector.detect_with_fallback(
            metrics.errors,
            errors_stats,
            fixed_threshold=self._thresholds["max_errors"]
        )

        if errors_result["is_anomaly"]:
            severity = self._anomaly_detector.get_severity_from_z_score(
                errors_result.get("z_score", 0)
            )
            alerts.append(
                f"errors anomaly (z-score: {errors_result.get('z_score', 0):.2f}, "
                f"severity: {severity}, method: {errors_result['method']})"
            )

        if alerts:
            elapsed = time.time() - metrics.start_time
            anomaly = {
                "agent_id": agent_id,
                "level": "warning",
                "detection_method": "z_score",
                "messages": alerts,
                "metrics": {
                    "iterations": metrics.iterations,
                    "iterations_z_score": iterations_result.get("z_score"),
                    "tool_calls": dict(metrics.tool_calls),
                    "total_tool_calls": total_tool_calls,
                    "tool_calls_z_score": tool_calls_result.get("z_score"),
                    "errors": metrics.errors,
                    "errors_z_score": errors_result.get("z_score"),
                    "elapsed_seconds": elapsed,
                },
                "timestamp": time.time(),
            }
            metrics.alerts.append(anomaly)
            logger.warning(f"Agent behavior anomaly detected (z-score): {anomaly}")
            return anomaly

        return None

    def _check_anomaly_fixed_threshold(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """使用固定阈值进行异常检测（原有逻辑）"""
        metrics = self._get_or_create(agent_id)
        alerts: List[str] = []

        if metrics.iterations > self._thresholds["max_iterations"]:
            alerts.append(
                f"iteration limit exceeded ({metrics.iterations}/"
                f"{self._thresholds['max_iterations']})"
            )

        total_tool_calls = sum(metrics.tool_calls.values())
        if total_tool_calls > self._thresholds["max_total_tool_calls"]:
            alerts.append(
                f"total tool call limit exceeded ({total_tool_calls}/"
                f"{self._thresholds['max_total_tool_calls']})"
            )

        for tool_name, count in metrics.tool_calls.items():
            if count > self._thresholds["max_tool_repetitions"]:
                alerts.append(
                    f"repeated tool '{tool_name}' usage ({count}/"
                    f"{self._thresholds['max_tool_repetitions']})"
                )

        # Parameter-level loop detection: same goal + tool + normalized params
        for action_key, count in metrics.actions.items():
            if count > self._thresholds["max_tool_repetitions"]:
                alerts.append(
                    f"repeated action signature ({count}/"
                    f"{self._thresholds['max_tool_repetitions']})"
                )

        if metrics.errors > self._thresholds["max_errors"]:
            alerts.append(
                f"error limit exceeded ({metrics.errors}/" f"{self._thresholds['max_errors']})"
            )

        elapsed = time.time() - metrics.start_time
        if elapsed > self._thresholds["max_execution_time_seconds"]:
            alerts.append(
                f"execution time exceeded ({elapsed:.1f}s/"
                f"{self._thresholds['max_execution_time_seconds']}s)"
            )

        if alerts:
            anomaly = {
                "agent_id": agent_id,
                "level": "warning",
                "detection_method": "fixed_threshold",
                "messages": alerts,
                "metrics": {
                    "iterations": metrics.iterations,
                    "tool_calls": dict(metrics.tool_calls),
                    "total_tool_calls": total_tool_calls,
                    "errors": metrics.errors,
                    "elapsed_seconds": elapsed,
                },
                "timestamp": time.time(),
            }
            metrics.alerts.append(anomaly)
            logger.warning(f"Agent behavior anomaly detected: {anomaly}")
            return anomaly

        return None

    def get_summary(self, agent_id: Optional[str] = None) -> Dict[str, Any]:
        """Return current behavior metrics, optionally filtered by agent."""
        if agent_id:
            metrics = self._metrics.get(agent_id)
            if not metrics:
                return {"agent_id": agent_id, "found": False}
            return {
                "agent_id": agent_id,
                "found": True,
                "iterations": metrics.iterations,
                "tool_calls": dict(metrics.tool_calls),
                "errors": metrics.errors,
                "alerts": metrics.alerts,
                "elapsed_seconds": time.time() - metrics.start_time,
            }

        return {
            agent_id: {
                "iterations": m.iterations,
                "tool_calls": dict(m.tool_calls),
                "errors": m.errors,
                "alerts": m.alerts,
                "elapsed_seconds": time.time() - m.start_time,
            }
            for agent_id, m in self._metrics.items()
        }

    def reset(self, agent_id: Optional[str] = None) -> None:
        """Reset metrics for one or all agents."""
        if agent_id:
            self._metrics.pop(agent_id, None)
            # 同时清理统计基线
            if self._z_score_enabled and agent_id in self._stats_baselines:
                del self._stats_baselines[agent_id]
        else:
            self._metrics.clear()
            if self._z_score_enabled:
                self._stats_baselines.clear()

    def get_performance_metrics(self) -> Dict[str, Any]:
        """获取性能监控指标"""
        avg_check_time = 0.0
        if self._performance_metrics["check_anomaly_calls"] > 0:
            avg_check_time = (
                self._performance_metrics["total_check_time"] /
                self._performance_metrics["check_anomaly_calls"]
            )

        return {
            "z_score_enabled": self._z_score_enabled,
            "check_anomaly_calls": self._performance_metrics["check_anomaly_calls"],
            "avg_check_time_seconds": avg_check_time,
            "z_score_checks": self._performance_metrics["z_score_checks"],
            "fixed_threshold_checks": self._performance_metrics["fixed_threshold_checks"],
            "z_score_usage_rate": (
                self._performance_metrics["z_score_checks"] /
                self._performance_metrics["check_anomaly_calls"]
                if self._performance_metrics["check_anomaly_calls"] > 0 else 0
            )
        }


# Global monitor instance
_global_behavior_monitor = BehaviorMonitor()


def get_behavior_monitor() -> BehaviorMonitor:
    """Get the global behavior monitor instance."""
    return _global_behavior_monitor
