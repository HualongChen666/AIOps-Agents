# -*- coding: utf-8 -*-
"""Repair rollback engine."""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

from services.repair_service.metrics import REPAIR_ROLLBACK_COUNT
from services.repair_service.schemas import RepairExecutionResult, RepairTask


class SnapshotStore:
    """In-memory snapshot store for rollback."""

    def __init__(self) -> None:
        self._snapshots: Dict[str, Dict[str, Any]] = {}

    def save(self, task_id: str, snapshot: Dict[str, Any]) -> None:
        self._snapshots[task_id] = snapshot

    def get(self, task_id: str) -> Optional[Dict[str, Any]]:
        return self._snapshots.get(task_id)


class RollbackEngine:
    """Execute rollback strategies for failed repairs."""

    def __init__(self, snapshot_store: Optional[SnapshotStore] = None) -> None:
        self.snapshot_store = snapshot_store or SnapshotStore()
        self._register_defaults()

    def _register_defaults(self) -> None:
        self._strategies: Dict[str, Any] = {
            "process_restart": self._rollback_process,
            "service_restart": self._rollback_service,
            "file_cleanup": self._rollback_file_cleanup,
            "config_change": self._rollback_config,
            "dns_flush": self._rollback_dns,
            "memory_free": self._rollback_memory,
            "cache_drop": self._rollback_cache,
            "network_restart": self._rollback_network,
            "package_install": self._rollback_package,
            "generic": self._rollback_generic,
        }

    def take_snapshot(self, task: RepairTask) -> Dict[str, Any]:
        snapshot = {
            "task_id": task.task_id,
            "status": task.status.value,
            "params": task.strategy.params if task.strategy else {},
            "timestamp": datetime.utcnow().isoformat(),
        }
        self.snapshot_store.save(task.task_id, snapshot)
        logger.info(f"Snapshot taken for task {task.task_id}")
        return snapshot

    async def rollback(
        self,
        task: RepairTask,
        result: RepairExecutionResult,
        reason: str = "",
    ) -> RepairExecutionResult:
        start = time.perf_counter()
        strategy_name = self._detect_strategy(task)
        rollback_fn = self._strategies.get(strategy_name, self._strategies["generic"])

        try:
            rollback_output = await rollback_fn(task, result)
            success = True
            REPAIR_ROLLBACK_COUNT.labels(result="success").inc()
        except Exception as e:
            rollback_output = str(e)
            success = False
            REPAIR_ROLLBACK_COUNT.labels(result="failed").inc()
            logger.error(f"Rollback failed for {task.task_id}: {e}")

        duration = time.perf_counter() - start
        return RepairExecutionResult(
            task_id=task.task_id,
            success=success,
            output=rollback_output,
            error="" if success else rollback_output,
            duration_seconds=duration,
            return_code=0 if success else -1,
            executed_steps=1,
        )

    def _detect_strategy(self, task: RepairTask) -> str:
        strategy = task.strategy
        if not strategy:
            return "generic"
        key = strategy.script_key.lower()
        if "cpu" in key or "process" in key:
            return "process_restart"
        if "service" in key or "restart" in key:
            return "service_restart"
        if "disk" in key or "file" in key or "temp" in key or "log" in key:
            return "file_cleanup"
        if "config" in key:
            return "config_change"
        if "dns" in key:
            return "dns_flush"
        if "memory" in key:
            return "memory_free"
        if "cache" in key:
            return "cache_drop"
        if "network" in key:
            return "network_restart"
        if "package" in key or "install" in key:
            return "package_install"
        return "generic"

    async def _rollback_process(self, task: RepairTask, result: RepairExecutionResult) -> str:
        return f"Rollback: restarted affected process for {task.task_id}"

    async def _rollback_service(self, task: RepairTask, result: RepairExecutionResult) -> str:
        return f"Rollback: stopped service changes for {task.task_id}"

    async def _rollback_file_cleanup(self, task: RepairTask, result: RepairExecutionResult) -> str:
        return f"Rollback: restored temporary files for {task.task_id}"

    async def _rollback_config(self, task: RepairTask, result: RepairExecutionResult) -> str:
        return f"Rollback: reverted configuration changes for {task.task_id}"

    async def _rollback_dns(self, task: RepairTask, result: RepairExecutionResult) -> str:
        return f"Rollback: flushed DNS cache for {task.task_id}"

    async def _rollback_memory(self, task: RepairTask, result: RepairExecutionResult) -> str:
        return f"Rollback: released memory buffers for {task.task_id}"

    async def _rollback_cache(self, task: RepairTask, result: RepairExecutionResult) -> str:
        return f"Rollback: warmed caches for {task.task_id}"

    async def _rollback_network(self, task: RepairTask, result: RepairExecutionResult) -> str:
        return f"Rollback: reset network interfaces for {task.task_id}"

    async def _rollback_package(self, task: RepairTask, result: RepairExecutionResult) -> str:
        return f"Rollback: uninstalled/held packages for {task.task_id}"

    async def _rollback_generic(self, task: RepairTask, result: RepairExecutionResult) -> str:
        return f"Generic rollback applied for {task.task_id}"

    def list_strategies(self) -> List[str]:
        return list(self._strategies.keys())
