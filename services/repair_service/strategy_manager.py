# -*- coding: utf-8 -*-
"""Repair strategy management and rule engine."""

from __future__ import annotations

import fnmatch
from typing import Dict, List, Optional

from services.repair_service.schemas import (
    PlatformType,
    RepairRequest,
    RepairStatus,
    RepairStrategy,
    RepairTask,
    RiskLevel,
)


class RepairStrategyManager:
    """Rule engine for repair strategy management."""

    def __init__(self) -> None:
        self._strategies: Dict[str, RepairStrategy] = {}
        self._exact_index: Dict[tuple[str, str], List[RepairStrategy]] = {}
        self._wildcard_strategies: List[RepairStrategy] = []
        self._register_defaults()
        self._build_index()

    def _build_index(self) -> None:
        """Index strategies for O(1) exact metric lookup."""
        self._exact_index.clear()
        self._wildcard_strategies.clear()
        for strategy in self._strategies.values():
            metric_pattern = strategy.conditions.get("metric", "")
            if "*" in metric_pattern:
                self._wildcard_strategies.append(strategy)
                continue
            platform = strategy.conditions.get("platform", "*")
            key = (platform, metric_pattern.lower())
            self._exact_index.setdefault(key, []).append(strategy)

    def _register_defaults(self) -> None:
        """Register 20+ built-in repair strategies."""
        defaults: List[RepairStrategy] = [
            RepairStrategy(
                name="cpu_high_linux",
                conditions={"metric": "cpu_percent", "platform": "linux"},
                script_key="cpu_high",
                platform=PlatformType.LINUX,
                risk_level=RiskLevel.MEDIUM,
            ),
            RepairStrategy(
                name="cpu_high_windows",
                conditions={"metric": "cpu_percent", "platform": "windows"},
                script_key="cpu_high",
                platform=PlatformType.WINDOWS,
                risk_level=RiskLevel.MEDIUM,
            ),
            RepairStrategy(
                name="memory_high_linux",
                conditions={"metric": "memory_percent", "platform": "linux"},
                script_key="memory_high",
                platform=PlatformType.LINUX,
                risk_level=RiskLevel.LOW,
            ),
            RepairStrategy(
                name="memory_high_windows",
                conditions={"metric": "memory_percent", "platform": "windows"},
                script_key="memory_high",
                platform=PlatformType.WINDOWS,
                risk_level=RiskLevel.LOW,
            ),
            RepairStrategy(
                name="disk_high_linux",
                conditions={"metric": "disk_percent", "platform": "linux"},
                script_key="disk_high",
                platform=PlatformType.LINUX,
                risk_level=RiskLevel.MEDIUM,
            ),
            RepairStrategy(
                name="disk_high_windows",
                conditions={"metric": "disk_percent", "platform": "windows"},
                script_key="disk_high",
                platform=PlatformType.WINDOWS,
                risk_level=RiskLevel.MEDIUM,
            ),
            RepairStrategy(
                name="service_restart_linux",
                conditions={"metric": "service_down", "platform": "linux"},
                script_key="service_restart",
                platform=PlatformType.LINUX,
                risk_level=RiskLevel.HIGH,
            ),
            RepairStrategy(
                name="service_restart_windows",
                conditions={"metric": "service_down", "platform": "windows"},
                script_key="service_restart",
                platform=PlatformType.WINDOWS,
                risk_level=RiskLevel.HIGH,
            ),
            RepairStrategy(
                name="docker_restart",
                conditions={"metric": "container_down", "platform": "docker"},
                script_key="service_restart",
                platform=PlatformType.DOCKER,
                risk_level=RiskLevel.HIGH,
            ),
            RepairStrategy(
                name="k8s_pod_restart",
                conditions={"metric": "pod_crash", "platform": "kubernetes"},
                script_key="service_restart",
                platform=PlatformType.KUBERNETES,
                risk_level=RiskLevel.HIGH,
            ),
            RepairStrategy(
                name="network_latency",
                conditions={"metric": "latency_high"},
                script_key="flush_dns",
                platform=PlatformType.LINUX,
                risk_level=RiskLevel.LOW,
            ),
            RepairStrategy(
                name="dns_flush",
                conditions={"metric": "dns_failure"},
                script_key="flush_dns",
                platform=PlatformType.LINUX,
                risk_level=RiskLevel.LOW,
            ),
            RepairStrategy(
                name="log_cleanup",
                conditions={"metric": "log_volume_high"},
                script_key="disk_high",
                platform=PlatformType.LINUX,
                risk_level=RiskLevel.MEDIUM,
            ),
            RepairStrategy(
                name="temp_cleanup",
                conditions={"metric": "temp_space_high"},
                script_key="disk_high",
                platform=PlatformType.LINUX,
                risk_level=RiskLevel.LOW,
            ),
            RepairStrategy(
                name="zombie_process",
                conditions={"metric": "zombie_process"},
                script_key="cpu_high",
                platform=PlatformType.LINUX,
                risk_level=RiskLevel.MEDIUM,
            ),
            RepairStrategy(
                name="high_swap",
                conditions={"metric": "swap_high"},
                script_key="memory_high",
                platform=PlatformType.LINUX,
                risk_level=RiskLevel.LOW,
            ),
            RepairStrategy(
                name="kubelet_restart",
                conditions={"metric": "kubelet_unhealthy", "platform": "kubernetes"},
                script_key="service_restart",
                platform=PlatformType.KUBERNETES,
                risk_level=RiskLevel.HIGH,
            ),
            RepairStrategy(
                name="docker_daemon_restart",
                conditions={"metric": "docker_unhealthy", "platform": "docker"},
                script_key="service_restart",
                platform=PlatformType.DOCKER,
                risk_level=RiskLevel.HIGH,
            ),
            RepairStrategy(
                name="macos_memory_pressure",
                conditions={"metric": "memory_pressure", "platform": "macos"},
                script_key="memory_high",
                platform=PlatformType.MACOS,
                risk_level=RiskLevel.LOW,
            ),
            RepairStrategy(
                name="macos_cpu_pressure",
                conditions={"metric": "cpu_pressure", "platform": "macos"},
                script_key="cpu_high",
                platform=PlatformType.MACOS,
                risk_level=RiskLevel.MEDIUM,
            ),
            RepairStrategy(
                name="generic_service_restart",
                conditions={"metric": "*service*"},
                script_key="service_restart",
                platform=PlatformType.LINUX,
                risk_level=RiskLevel.HIGH,
            ),
            RepairStrategy(
                name="generic_high_load",
                conditions={"metric": "load_high"},
                script_key="cpu_high",
                platform=PlatformType.LINUX,
                risk_level=RiskLevel.MEDIUM,
            ),
        ]
        for s in defaults:
            self._strategies[s.name] = s

    def add_strategy(self, strategy: RepairStrategy) -> None:
        self._strategies[strategy.name] = strategy
        self._build_index()

    def get_strategy(self, name: str) -> Optional[RepairStrategy]:
        return self._strategies.get(name)

    def list_strategies(self) -> List[RepairStrategy]:
        return sorted(self._strategies.values(), key=lambda s: s.priority, reverse=True)

    def match(self, request: RepairRequest) -> Optional[RepairStrategy]:
        """Match a request to the best strategy using indexed lookup."""
        candidates: List[tuple[int, RepairStrategy]] = []
        metric = request.metric.lower() if request.metric else ""
        platform = request.platform.value

        for key in ((platform, metric), ("*", metric)):
            for strategy in self._exact_index.get(key, []):
                score = 20 + (10 if strategy.conditions.get("platform") else 0)
                candidates.append((score, strategy))

        for strategy in self._wildcard_strategies:
            score = self._score(strategy, request)
            if score > 0:
                candidates.append((score, strategy))

        if not candidates:
            return None
        candidates.sort(key=lambda x: (x[0], x[1].priority), reverse=True)
        return candidates[0][1]

    def _score(self, strategy: RepairStrategy, request: RepairRequest) -> int:
        score = 0
        conditions = strategy.conditions
        if conditions.get("platform") == request.platform.value:
            score += 10
        metric_pattern = conditions.get("metric", "")
        if metric_pattern and request.metric:
            if fnmatch.fnmatch(request.metric.lower(), metric_pattern.lower()):
                score += 20
            elif metric_pattern.lower() in request.metric.lower():
                score += 10
        return score

    def create_task_from_request(
        self,
        request: RepairRequest,
        task_id: str,
    ) -> RepairTask:
        strategy = self.match(request)
        return RepairTask(
            task_id=task_id,
            alert_id=request.alert_id,
            host=request.host,
            platform=request.platform,
            status=RepairStatus.PENDING,
            strategy=strategy,
            runbook=None,
        )
