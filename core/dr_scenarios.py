# -*- coding: utf-8 -*-
"""
Real Disaster Recovery Scenarios
真实灾难恢复演练场景

定义真实的灾难恢复演练场景和验证步骤。
"""

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Failure type → Chaos Mesh experiment mapping.
#
# ``kind`` is the Chaos Mesh custom resource and ``action`` the action applied
# through :class:`core.chaos_engineering.ChaosMeshInjector`.  The workload the
# failure is injected into is resolved from the environment so the drill hits
# the real objects of the current cluster:
#
#   * ``CHAOS_DB_SERVICE``     – workload hosting the primary database
#   * ``CHAOS_REDIS_SERVICE``  – workload hosting the cache
#   * ``CHAOS_TARGET_SERVICE`` – workload hosting the application
#
# ``extra`` carries the kind specific fields (IOChaos requires a path and an
# errno; ENOSPC/28 reproduces "disk full").
# ---------------------------------------------------------------------------
_FAILURE_SPECS: Dict[str, Dict[str, Any]] = {
    "database_down": {
        "kind": "PodChaos",
        "action": "pod-failure",
        "target_env": "CHAOS_DB_SERVICE",
        "default_target": "postgres",
    },
    "db_down": {
        "kind": "PodChaos",
        "action": "pod-failure",
        "target_env": "CHAOS_DB_SERVICE",
        "default_target": "postgres",
    },
    "redis_down": {
        "kind": "PodChaos",
        "action": "pod-failure",
        "target_env": "CHAOS_REDIS_SERVICE",
        "default_target": "redis",
    },
    "system_down": {
        "kind": "PodChaos",
        "action": "pod-failure",
        "target_env": "CHAOS_TARGET_SERVICE",
        "default_target": "",
    },
    "disk_full": {
        "kind": "IOChaos",
        "action": "fault",
        "target_env": "CHAOS_TARGET_SERVICE",
        "default_target": "",
        "extra": {"volumePath": "/", "path": "*", "errno": 28},
    },
}


class DRScenario:
    """灾难恢复演练场景"""

    def __init__(
        self,
        name: str,
        description: str,
        steps: List[Dict[str, Any]],
        injector: Optional[Any] = None,
    ):
        self.name = name
        self.description = description
        self.steps = steps
        self.status = "pending"
        self.results: List[Dict[str, Any]] = []
        self._namespace = os.getenv("CHAOS_NAMESPACE", "default")
        self._chaos_duration = os.getenv("DR_CHAOS_DURATION", "5m")
        self._injector = injector
        # Chaos experiments that are currently active and must be removed by
        # the recovery step.
        self._active_experiments: List[Tuple[str, str]] = []

    async def execute(self) -> Dict[str, Any]:
        """
        执行演练场景

        Returns:
            执行结果
        """
        logger.info(f"Starting DR scenario: {self.name}")
        self.status = "running"

        results = []
        for i, step in enumerate(self.steps):
            try:
                logger.info(f"Executing step {i + 1}/{len(self.steps)}: {step['description']}")
                result = await self._execute_step(step)
                results.append(
                    {
                        "step": i + 1,
                        "description": step["description"],
                        "status": "success",
                        "result": result,
                    }
                )
            except Exception as e:
                logger.error(f"Step {i + 1} failed: {e}")
                results.append(
                    {
                        "step": i + 1,
                        "description": step["description"],
                        "status": "failed",
                        "error": str(e),
                    }
                )
                self.status = "failed"
                break

        if self.status != "failed":
            self.status = "completed"

        self.results = results
        logger.info(f"DR scenario {self.name} completed with status: {self.status}")

        return {
            "scenario": self.name,
            "status": self.status,
            "results": results,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def _execute_step(self, step: Dict[str, Any]) -> Any:
        """
        执行单个步骤

        Args:
            step: 步骤配置

        Returns:
            步骤结果
        """
        step_type = step.get("type")

        if step_type == "check_database":
            return await self._check_database()
        elif step_type == "check_redis":
            return await self._check_redis()
        elif step_type == "check_api":
            return await self._check_api(step.get("endpoint", "/api/v1/health"))
        elif step_type in ("inject_failure", "simulate_failure"):
            failure_type = step.get("failure_type")
            if failure_type is None:
                return {"status": "error", "error": "failure_type is required"}
            return await self._inject_failure(failure_type)
        elif step_type == "restore_backup":
            return await self._restore_backup()
        else:
            logger.warning(f"Unknown step type: {step_type}")
            return None

    async def _check_database(self) -> Dict[str, Any]:
        """检查数据库连接"""
        try:
            from sqlalchemy import text

            from core.db_engine import AsyncSessionLocal

            async with AsyncSessionLocal() as session:
                await session.execute(text("SELECT 1"))
            return {"status": "healthy", "message": "Database connection successful"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    async def _check_redis(self) -> Dict[str, Any]:
        """检查Redis连接"""
        try:
            import redis

            from config import REDIS_DB, REDIS_HOST, REDIS_PORT

            r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)
            r.ping()
            return {"status": "healthy", "message": "Redis connection successful"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    async def _check_api(self, endpoint: str) -> Dict[str, Any]:
        """检查API端点"""
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.get(f"http://localhost:8000{endpoint}")
                return {"status": "healthy", "status_code": response.status_code}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    def _execution_enabled(self) -> bool:
        """Whether real chaos injection is allowed.

        An explicitly supplied injector counts as opt-in (used by tests and by
        callers that bring their own backend); otherwise the drill requires
        ``DR_EXECUTE_ENABLED=true`` so that mutating a cluster is never implicit.
        """
        if self._injector is not None:
            return True
        return os.getenv("DR_EXECUTE_ENABLED", "false").strip().lower() == "true"

    def _get_injector(self) -> Any:
        """Return the chaos injection backend (Chaos Mesh by default)."""
        if self._injector is not None:
            return self._injector
        from core.chaos_engineering import ChaosMeshInjector

        return ChaosMeshInjector(self._namespace)

    async def _inject_failure(self, failure_type: str) -> Dict[str, Any]:
        """Inject a real Chaos Mesh experiment for ``failure_type``.

        Raises :class:`ValueError` for unknown failure types and
        :class:`RuntimeError` when no target workload is configured, so a
        misconfigured drill fails loudly instead of reporting success.
        """
        if not self._execution_enabled():
            return {
                "status": "disabled",
                "failure_type": failure_type,
                "reason": "DR_EXECUTE_ENABLED is not 'true'",
            }

        spec_definition = _FAILURE_SPECS.get(failure_type)
        if spec_definition is None:
            raise ValueError(
                f"unsupported failure_type '{failure_type}'; "
                f"supported: {', '.join(sorted(_FAILURE_SPECS))}"
            )

        target = (
            os.getenv(spec_definition["target_env"]) or spec_definition["default_target"]
        ).strip()
        if not target:
            raise RuntimeError(
                f"no chaos target configured for '{failure_type}': "
                f"set {spec_definition['target_env']}"
            )

        kind = spec_definition["kind"]
        name = f"dr-{failure_type}-{int(datetime.now(timezone.utc).timestamp())}"
        spec: Dict[str, Any] = {
            "action": spec_definition["action"],
            "mode": "one",
            "duration": self._chaos_duration,
            "selector": {
                "labelSelectors": {"app": target},
                "namespaces": [self._namespace],
            },
        }
        spec.update(spec_definition.get("extra", {}))

        await self._get_injector().apply(kind, name, spec)
        self._active_experiments.append((kind, name))
        logger.warning(f"Injected chaos experiment {kind}/{name} targeting app={target}")

        return {
            "status": "injected",
            "failure_type": failure_type,
            "chaos_kind": kind,
            "experiment": name,
            "target": target,
            "namespace": self._namespace,
            "duration": self._chaos_duration,
        }

    async def _restore_backup(self) -> Dict[str, Any]:
        """Recover the system: delete every chaos experiment this drill injected."""
        if not self._execution_enabled():
            return {"status": "disabled", "reason": "DR_EXECUTE_ENABLED is not 'true'"}

        if not self._active_experiments:
            logger.info("No active chaos experiments to recover")
            return {"status": "restored", "recovered_experiments": []}

        injector = self._get_injector()
        recovered: List[str] = []
        for kind, name in list(self._active_experiments):
            await injector.delete(kind, name)
            self._active_experiments.remove((kind, name))
            recovered.append(f"{kind}/{name}")

        logger.info(f"Removed {len(recovered)} chaos experiments: {recovered}")
        return {"status": "restored", "recovered_experiments": recovered}


# 预定义的演练场景
DR_SCENARIOS = {
    "database_failover": DRScenario(
        name="Database Failover",
        description="模拟数据库故障并验证故障转移",
        steps=[
            {"type": "check_database", "description": "检查主数据库状态"},
            {
                "type": "inject_failure",
                "description": "模拟主数据库故障",
                "failure_type": "database_down",
            },
            {"type": "check_database", "description": "验证备用数据库接管"},
            {"type": "restore_backup", "description": "恢复主数据库"},
        ],
    ),
    "redis_cache_failure": DRScenario(
        name="Redis Cache Failure",
        description="模拟Redis缓存故障并验证降级策略",
        steps=[
            {"type": "check_redis", "description": "检查Redis状态"},
            {
                "type": "inject_failure",
                "description": "模拟Redis故障",
                "failure_type": "redis_down",
            },
            {
                "type": "check_api",
                "description": "验证API降级运行",
                "endpoint": "/api/v1/metrics/summary",
            },
        ],
    ),
    "full_system_recovery": DRScenario(
        name="Full System Recovery",
        description="完整系统恢复演练",
        steps=[
            {"type": "check_database", "description": "检查数据库"},
            {"type": "check_redis", "description": "检查Redis"},
            {"type": "check_api", "description": "检查API健康", "endpoint": "/api/v1/health"},
            {
                "type": "inject_failure",
                "description": "模拟系统故障",
                "failure_type": "system_down",
            },
            {"type": "restore_backup", "description": "恢复系统备份"},
            {"type": "check_database", "description": "验证数据库恢复"},
            {"type": "check_api", "description": "验证API恢复", "endpoint": "/api/v1/health"},
        ],
    ),
}


async def run_dr_scenario(scenario_name: str) -> Dict[str, Any]:
    """
    运行灾难恢复演练场景

    Args:
        scenario_name: 场景名称

    Returns:
        演练结果
    """
    if scenario_name not in DR_SCENARIOS:
        return {"status": "error", "message": f"Scenario not found: {scenario_name}"}

    scenario = DR_SCENARIOS[scenario_name]
    return await scenario.execute()


async def list_dr_scenarios() -> List[Dict[str, Any]]:
    """
    列出所有演练场景

    Returns:
        场景列表
    """
    return [
        {"name": name, "description": scenario.description, "steps_count": len(scenario.steps)}
        for name, scenario in DR_SCENARIOS.items()
    ]
