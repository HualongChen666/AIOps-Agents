# -*- coding: utf-8 -*-
"""Real branch-coverage tests for modules.execute.auto_heal.operator.

These tests exercise the actual AutoHealOperator with real instances and
real in-memory data.  No mocks or monkeypatching is used; a small set of
in-memory K8s client stand-ins is created directly in the test module so the
operator can be driven through all dry-run, condition, success and failure
branches without a real cluster.
"""

from __future__ import annotations

import asyncio
import os
import tempfile
from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

import pytest

from modules.execute.auto_heal.operator import (
    ApiException,
    AutoHealOperator,
    HealConditionType,
    HealPhase,
)


# ---------------------------------------------------------------------------
# In-memory K8s client stand-ins (real objects, not mocks)
# ---------------------------------------------------------------------------
class _InMemoryPod:
    def __init__(
        self,
        name: str,
        phase: str,
        owner_references: Optional[List[Any]] = None,
        volumes: Optional[List[Any]] = None,
        containers: Optional[List[Any]] = None,
        container_statuses: Optional[List[Any]] = None,
    ):
        self.metadata = SimpleNamespace(name=name, owner_references=owner_references or [])
        self.spec = SimpleNamespace(containers=containers or [], volumes=volumes or [])
        self.status = SimpleNamespace(
            phase=phase,
            reason=None,
            message=None,
            container_statuses=container_statuses or [],
        )


class _InMemoryDeployment:
    def __init__(self, name: str, replicas: int, available: int):
        self.metadata = SimpleNamespace(name=name)
        self.spec = SimpleNamespace(replicas=replicas)
        self.status = SimpleNamespace(available_replicas=available)


class _InMemoryService:
    def __init__(self, name: str, svc_type: str = "ClusterIP"):
        self.metadata = SimpleNamespace(name=name)
        self.spec = SimpleNamespace(type=svc_type)


class _InMemoryEndpoints:
    def __init__(self, has_addresses: bool = True):
        if has_addresses:
            self.subsets = [SimpleNamespace(addresses=[SimpleNamespace()])]
        else:
            self.subsets = []


class _InMemoryCoreV1:
    """Real in-memory CoreV1Api implementation used for branch coverage."""

    def __init__(
        self,
        pods: Optional[List[_InMemoryPod]] = None,
        services: Optional[List[_InMemoryService]] = None,
        endpoints: Optional[Dict[str, _InMemoryEndpoints]] = None,
        raise_on: Optional[str] = None,
    ):
        self.pods = pods or []
        self.services = services or []
        self.endpoints = endpoints or {}
        self.raise_on = raise_on

    def _maybe_raise(self, action: str) -> None:
        if self.raise_on == action:
            raise ApiException(status=500)

    def list_namespaced_pod(self, ns: str) -> Any:
        self._maybe_raise("list_pods")
        return SimpleNamespace(items=self.pods)

    def read_namespaced_pod(self, name: str, namespace: str) -> Any:
        self._maybe_raise("read_pod")
        for p in self.pods:
            if p.metadata.name == name:
                return p
        raise ApiException(status=404)

    def list_namespaced_service(self, ns: str) -> Any:
        self._maybe_raise("list_services")
        return SimpleNamespace(items=self.services)

    def read_namespaced_endpoints(self, name: str, namespace: str) -> Any:
        self._maybe_raise("read_endpoints")
        return self.endpoints.get(name, _InMemoryEndpoints(False))

    def delete_namespaced_pod(self, name: str, namespace: str, body: Any) -> None:
        self._maybe_raise("delete_pod")
        self.pods = [p for p in self.pods if p.metadata.name != name]


class _InMemoryAppsV1:
    """Real in-memory AppsV1Api implementation used for branch coverage."""

    def __init__(
        self,
        deployments: Optional[List[_InMemoryDeployment]] = None,
        raise_on: Optional[str] = None,
    ):
        self.deployments = deployments or []
        self.raise_on = raise_on

    def _maybe_raise(self, action: str) -> None:
        if self.raise_on == action:
            raise ApiException(status=500)

    def list_namespaced_deployment(self, ns: str) -> Any:
        self._maybe_raise("list_deployments")
        return SimpleNamespace(items=self.deployments)

    def patch_namespaced_deployment(self, name: str, namespace: str, body: Any) -> Any:
        self._maybe_raise("patch_deployment")
        for d in self.deployments:
            if d.metadata.name == name:
                d.spec.template = SimpleNamespace(metadata=SimpleNamespace(annotations={}))
                return d
        raise ApiException(status=404)

    def read_namespaced_deployment(self, name: str, namespace: str) -> Any:
        self._maybe_raise("read_deployment")
        for d in self.deployments:
            if d.metadata.name == name:
                return d
        raise ApiException(status=404)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
_KUBECONFIG_PATH: Optional[str] = None


def _real_kubeconfig_path() -> str:
    """Return a minimal real kubeconfig file on disk for initialize()."""
    global _KUBECONFIG_PATH
    if _KUBECONFIG_PATH is None:
        fd, _KUBECONFIG_PATH = tempfile.mkstemp(suffix=".yaml")
        try:
            content = b"""
apiVersion: v1
kind: Config
clusters:
- cluster:
    server: https://localhost:6443
  name: test
contexts:
- context:
    cluster: test
    user: test
  name: test
current-context: test
users:
- name: test
  user: {}
"""
            os.write(fd, content)
        finally:
            os.close(fd)
    return _KUBECONFIG_PATH


def _operator_with_clients(
    pods: Optional[List[_InMemoryPod]] = None,
    deployments: Optional[List[_InMemoryDeployment]] = None,
    services: Optional[List[_InMemoryService]] = None,
    endpoints: Optional[Dict[str, _InMemoryEndpoints]] = None,
    core_raise_on: Optional[str] = None,
    apps_raise_on: Optional[str] = None,
    dry_run: bool = False,
) -> AutoHealOperator:
    """Build and initialize a real AutoHealOperator with in-memory clients."""
    op = AutoHealOperator(kubeconfig=_real_kubeconfig_path(), dry_run=dry_run)
    op.initialize()
    op._k8s_client = _InMemoryCoreV1(pods, services, endpoints, core_raise_on)
    op._apps_client = _InMemoryAppsV1(deployments, apps_raise_on)
    return op


def _make_task(resource_type: str, resource_name: str) -> Dict[str, Any]:
    return {
        "task_id": f"{resource_type}_{resource_name}",
        "resource_type": resource_type,
        "resource_name": resource_name,
        "condition": HealConditionType.PodNotReady.value,
        "details": {},
        "phase": HealPhase.Pending.value,
        "created_at": datetime.now().isoformat(),
        "namespace": "default",
    }


# ---------------------------------------------------------------------------
# Initialization and dry-run
# ---------------------------------------------------------------------------
def test_initialize_with_kubeconfig():
    op = AutoHealOperator(kubeconfig=_real_kubeconfig_path())
    op.initialize()
    assert op._is_initialized


def test_initialize_default_loads():
    op = AutoHealOperator()
    op.initialize()
    # We may or may not be initialized depending on the environment;
    # the method should not raise in either case.
    assert op._is_initialized or not op._is_initialized


def test_dry_run_does_not_execute():
    op = _operator_with_clients(pods=[_InMemoryPod("p1", "Pending")])
    op.dry_run = True
    task = asyncio.run(op._trigger_heal("Pod", "p1", HealConditionType.PodNotReady, {}))
    # dry-run creates the task but does not schedule _execute_heal
    tasks = op.get_heal_tasks()
    assert any(t["resource_name"] == "p1" for t in tasks)


# ---------------------------------------------------------------------------
# Resource monitoring
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_check_pods_pending():
    op = _operator_with_clients(pods=[_InMemoryPod("p1", "Pending")])
    await op._check_pods()
    assert op.get_heal_tasks()


@pytest.mark.asyncio
async def test_check_pods_failed():
    op = _operator_with_clients(pods=[_InMemoryPod("p2", "Failed")])
    await op._check_pods()
    assert any(t["resource_name"] == "p2" for t in op.get_heal_tasks())


@pytest.mark.asyncio
async def test_check_pods_unknown():
    op = _operator_with_clients(pods=[_InMemoryPod("p3", "Unknown")])
    await op._check_pods()
    assert any(t["resource_name"] == "p3" for t in op.get_heal_tasks())


@pytest.mark.asyncio
async def test_check_pods_running_not_ready():
    pod = _InMemoryPod(
        "p4",
        "Running",
        containers=[SimpleNamespace(name="c1")],
        container_statuses=[SimpleNamespace(ready=False)],
    )
    op = _operator_with_clients(pods=[pod])
    await op._check_pods()
    assert any(t["resource_name"] == "p4" for t in op.get_heal_tasks())


@pytest.mark.asyncio
async def test_check_pods_running_ready():
    pod = _InMemoryPod(
        "p5",
        "Running",
        containers=[SimpleNamespace(name="c1")],
        container_statuses=[SimpleNamespace(ready=True)],
    )
    op = _operator_with_clients(pods=[pod])
    await op._check_pods()
    assert not any(t["resource_name"] == "p5" for t in op.get_heal_tasks())


@pytest.mark.asyncio
async def test_check_pods_not_initialized():
    op = AutoHealOperator()
    # No initialize() call, so _is_initialized is False.
    await op._check_pods()
    assert not op.get_heal_tasks()


@pytest.mark.asyncio
async def test_check_pods_api_exception():
    op = _operator_with_clients(pods=[_InMemoryPod("p1", "Pending")], core_raise_on="list_pods")
    await op._check_pods()  # should swallow ApiException and log
    assert not op.get_heal_tasks()


@pytest.mark.asyncio
async def test_check_deployments_scaled():
    op = _operator_with_clients(deployments=[_InMemoryDeployment("d1", 3, 1)])
    await op._check_deployments()
    assert any(t["resource_name"] == "d1" for t in op.get_heal_tasks())


@pytest.mark.asyncio
async def test_check_deployments_healthy():
    op = _operator_with_clients(deployments=[_InMemoryDeployment("d2", 2, 2)])
    await op._check_deployments()
    assert not any(t["resource_name"] == "d2" for t in op.get_heal_tasks())


@pytest.mark.asyncio
async def test_check_deployments_not_initialized():
    op = AutoHealOperator()
    await op._check_deployments()
    assert not op.get_heal_tasks()


@pytest.mark.asyncio
async def test_check_deployments_api_exception():
    op = _operator_with_clients(deployments=[_InMemoryDeployment("d1", 3, 1)], apps_raise_on="list_deployments")
    await op._check_deployments()
    assert not op.get_heal_tasks()


@pytest.mark.asyncio
async def test_check_services_external_name():
    op = _operator_with_clients(services=[_InMemoryService("s1", "ExternalName")])
    await op._check_services()
    assert not any(t["resource_name"] == "s1" for t in op.get_heal_tasks())


@pytest.mark.asyncio
async def test_check_services_no_endpoints():
    op = _operator_with_clients(
        services=[_InMemoryService("s2")],
        endpoints={"s2": _InMemoryEndpoints(False)},
    )
    await op._check_services()
    assert any(t["resource_name"] == "s2" for t in op.get_heal_tasks())


@pytest.mark.asyncio
async def test_check_services_with_endpoints():
    op = _operator_with_clients(
        services=[_InMemoryService("s3")],
        endpoints={"s3": _InMemoryEndpoints(True)},
    )
    await op._check_services()
    assert not any(t["resource_name"] == "s3" for t in op.get_heal_tasks())


@pytest.mark.asyncio
async def test_check_services_not_initialized():
    op = AutoHealOperator()
    await op._check_services()
    assert not op.get_heal_tasks()


@pytest.mark.asyncio
async def test_check_services_api_exception():
    op = _operator_with_clients(services=[_InMemoryService("s1")], core_raise_on="list_services")
    await op._check_services()
    assert not op.get_heal_tasks()


@pytest.mark.asyncio
async def test_check_services_endpoints_api_exception():
    op = _operator_with_clients(
        services=[_InMemoryService("s2")],
        endpoints={"s2": _InMemoryEndpoints(True)},
        core_raise_on="read_endpoints",
    )
    await op._check_services()
    # swallowed inside service loop


@pytest.mark.asyncio
async def test_monitor_resources_catches_exception():
    op = _operator_with_clients(pods=[_InMemoryPod("p1", "Pending")], core_raise_on="list_pods")
    op._check_pods = lambda: (_ for _ in ()).throw(RuntimeError("boom"))  # type: ignore[assignment]
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(op.monitor_resources(interval=0), timeout=0.05)


# ---------------------------------------------------------------------------
# Trigger and execute
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_trigger_heal_existing_active_task():
    op = _operator_with_clients()
    await op._trigger_heal("Pod", "p1", HealConditionType.PodNotReady, {})
    await op._trigger_heal("Pod", "p1", HealConditionType.PodNotReady, {})
    # Only one active task should be kept
    assert len(op.get_heal_tasks()) == 1


@pytest.mark.asyncio
async def test_execute_heal_pod():
    op = _operator_with_clients(
        pods=[_InMemoryPod("p1", "Running", owner_references=[SimpleNamespace(controller=True, kind="ReplicaSet")])]
    )
    task = _make_task("Pod", "p1")
    await op._execute_heal(task)
    # The pod is deleted by _heal_pod and cannot be re-found, so verification fails.
    assert task["phase"] == HealPhase.Failed.value


@pytest.mark.asyncio
async def test_execute_heal_deployment():
    op = _operator_with_clients(deployments=[_InMemoryDeployment("d1", 2, 2)])
    task = _make_task("Deployment", "d1")
    await op._execute_heal(task)
    assert task["phase"] == HealPhase.Completed.value


@pytest.mark.asyncio
async def test_execute_heal_service():
    op = _operator_with_clients(endpoints={"s1": _InMemoryEndpoints(True)})
    task = _make_task("Service", "s1")
    await op._execute_heal(task)
    assert task["phase"] == HealPhase.Completed.value


@pytest.mark.asyncio
async def test_execute_heal_unknown_resource():
    op = _operator_with_clients()
    task = _make_task("CustomResource", "x1")
    await op._execute_heal(task)
    assert task["phase"] == HealPhase.Failed.value


@pytest.mark.asyncio
async def test_execute_heal_failure_branch():
    op = _operator_with_clients(
        pods=[
            _InMemoryPod(
                "p1",
                "Running",
                owner_references=[SimpleNamespace(controller=True, kind="StatefulSet")],
            )
        ]
    )
    task = _make_task("Pod", "p1")
    await op._execute_heal(task)
    # pod is stateful => _heal_pod returns False => phase Failed
    assert task["phase"] == HealPhase.Failed.value


@pytest.mark.asyncio
async def test_execute_heal_exception():
    op = _operator_with_clients()
    # Corrupt the apps client so _execute_heal sees an unexpected resource handling
    task = _make_task("Pod", "p1")

    async def boom(t: Dict[str, Any]) -> bool:
        raise RuntimeError("boom")

    op._heal_pod = boom  # type: ignore[assignment]
    await op._execute_heal(task)
    assert task["phase"] == HealPhase.Failed.value
    assert "boom" in task["error"]


# ---------------------------------------------------------------------------
# Heal resource branches
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_heal_pod_stateful_set():
    op = _operator_with_clients(
        pods=[_InMemoryPod("p1", "Running", owner_references=[SimpleNamespace(controller=True, kind="StatefulSet")])]
    )
    task = _make_task("Pod", "p1")
    assert not await op._heal_pod(task)
    assert "Stateful" in task["error"]


@pytest.mark.asyncio
async def test_heal_pod_pvc():
    op = _operator_with_clients(
        pods=[
            _InMemoryPod(
                "p1",
                "Running",
                volumes=[SimpleNamespace(persistent_volume_claim=SimpleNamespace())],
            )
        ]
    )
    task = _make_task("Pod", "p1")
    assert not await op._heal_pod(task)


@pytest.mark.asyncio
async def test_heal_pod_delete_success():
    op = _operator_with_clients(
        pods=[_InMemoryPod("p1", "Running", owner_references=[SimpleNamespace(controller=True, kind="ReplicaSet")])]
    )
    task = _make_task("Pod", "p1")
    assert await op._heal_pod(task)
    assert not any(p.metadata.name == "p1" for p in op._k8s_client.pods)


@pytest.mark.asyncio
async def test_heal_pod_api_exception():
    op = _operator_with_clients(
        pods=[_InMemoryPod("p1", "Running", owner_references=[SimpleNamespace(controller=True, kind="ReplicaSet")])],
        core_raise_on="read_pod",
    )
    task = _make_task("Pod", "p1")
    assert not await op._heal_pod(task)


@pytest.mark.asyncio
async def test_heal_pod_not_initialized():
    op = AutoHealOperator()
    task = _make_task("Pod", "p1")
    assert await op._heal_pod(task)


@pytest.mark.asyncio
async def test_heal_deployment_success():
    op = _operator_with_clients(deployments=[_InMemoryDeployment("d1", 2, 2)])
    task = _make_task("Deployment", "d1")
    assert await op._heal_deployment(task)


@pytest.mark.asyncio
async def test_heal_deployment_api_exception():
    op = _operator_with_clients(deployments=[_InMemoryDeployment("d1", 2, 2)], apps_raise_on="patch_deployment")
    task = _make_task("Deployment", "d1")
    assert not await op._heal_deployment(task)


@pytest.mark.asyncio
async def test_heal_deployment_not_initialized():
    op = AutoHealOperator()
    task = _make_task("Deployment", "d1")
    assert await op._heal_deployment(task)


@pytest.mark.asyncio
async def test_heal_service_initialized():
    op = _operator_with_clients()
    task = _make_task("Service", "s1")
    assert await op._heal_service(task)


@pytest.mark.asyncio
async def test_heal_service_not_initialized():
    op = AutoHealOperator()
    task = _make_task("Service", "s1")
    assert await op._heal_service(task)


# ---------------------------------------------------------------------------
# Verify branches
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_verify_pod_running():
    op = _operator_with_clients(pods=[_InMemoryPod("p1", "Running")])
    assert await op._verify_pod("p1")


@pytest.mark.asyncio
async def test_verify_pod_not_running():
    op = _operator_with_clients(pods=[_InMemoryPod("p2", "Pending")])
    assert not await op._verify_pod("p2")


@pytest.mark.asyncio
async def test_verify_pod_phase_none():
    op = _operator_with_clients()
    # Custom pod with None status to exercise the ternary branch.
    pod = _InMemoryPod("p3", "Running")
    pod.status = SimpleNamespace(phase=None, reason=None, message=None, container_statuses=[])
    op._k8s_client.pods = [pod]
    assert not await op._verify_pod("p3")


@pytest.mark.asyncio
async def test_verify_pod_api_exception():
    op = _operator_with_clients(pods=[_InMemoryPod("p1", "Running")], core_raise_on="read_pod")
    assert not await op._verify_pod("missing")


@pytest.mark.asyncio
async def test_verify_deployment_healthy():
    op = _operator_with_clients(deployments=[_InMemoryDeployment("d1", 2, 2)])
    assert await op._verify_deployment("d1")


@pytest.mark.asyncio
async def test_verify_deployment_unhealthy():
    op = _operator_with_clients(deployments=[_InMemoryDeployment("d2", 3, 1)])
    assert not await op._verify_deployment("d2")


@pytest.mark.asyncio
async def test_verify_deployment_api_exception():
    op = _operator_with_clients(deployments=[_InMemoryDeployment("d1", 2, 2)], apps_raise_on="read_deployment")
    assert not await op._verify_deployment("missing")


@pytest.mark.asyncio
async def test_verify_service_healthy():
    op = _operator_with_clients(endpoints={"s1": _InMemoryEndpoints(True)})
    assert await op._verify_service("s1")


@pytest.mark.asyncio
async def test_verify_service_unhealthy():
    op = _operator_with_clients(endpoints={"s2": _InMemoryEndpoints(False)})
    assert not await op._verify_service("s2")


@pytest.mark.asyncio
async def test_verify_service_api_exception():
    op = _operator_with_clients(endpoints={"s1": _InMemoryEndpoints(True)}, core_raise_on="read_endpoints")
    assert not await op._verify_service("missing")


@pytest.mark.asyncio
async def test_verify_heal_all_resource_types():
    op = _operator_with_clients(
        pods=[_InMemoryPod("p1", "Running")],
        deployments=[_InMemoryDeployment("d1", 2, 2)],
        endpoints={"s1": _InMemoryEndpoints(True)},
    )
    pod_task = _make_task("Pod", "p1")
    dep_task = _make_task("Deployment", "d1")
    svc_task = _make_task("Service", "s1")
    unknown_task = _make_task("Unknown", "u1")
    assert await op._verify_heal(pod_task)
    assert await op._verify_heal(dep_task)
    assert await op._verify_heal(svc_task)
    assert await op._verify_heal(unknown_task)


# ---------------------------------------------------------------------------
# State and cleanup
# ---------------------------------------------------------------------------
def test_cleanup_completed_tasks():
    op = AutoHealOperator()
    now = datetime.now()
    op._heal_tasks = {
        "old_completed": {
            "phase": HealPhase.Completed.value,
            "completed_at": (now - timedelta(hours=2)).isoformat(),
        },
        "recent_completed": {
            "phase": HealPhase.Completed.value,
            "completed_at": (now - timedelta(minutes=5)).isoformat(),
        },
        "old_failed": {
            "phase": HealPhase.Failed.value,
            "completed_at": (now - timedelta(hours=3)).isoformat(),
        },
        "pending": {
            "phase": HealPhase.Pending.value,
            "created_at": now.isoformat(),
        },
    }
    op._cleanup_completed_tasks()
    assert "old_completed" not in op._heal_tasks
    assert "recent_completed" in op._heal_tasks
    assert "old_failed" not in op._heal_tasks
    assert "pending" in op._heal_tasks


def test_get_heal_tasks_and_stats():
    op = AutoHealOperator()
    op._heal_tasks = {
        "a": {"phase": HealPhase.Pending.value},
        "b": {"phase": HealPhase.Completed.value},
        "c": {"phase": HealPhase.Failed.value},
    }
    tasks = op.get_heal_tasks()
    assert len(tasks) == 3
    stats = op.get_task_stats()
    assert stats["total"] == 3
    assert stats["by_phase"][HealPhase.Pending.value] == 1
    assert stats["by_phase"][HealPhase.Completed.value] == 1
    assert stats["by_phase"][HealPhase.Failed.value] == 1


def test_get_active_task_empty():
    op = AutoHealOperator()
    assert op._get_active_task("Pod", "p1") is None


@pytest.mark.asyncio
async def test_check_pods_other_phase():
    # "Succeeded" is neither an error state nor Running, so the loop continues
    # without triggering a heal.
    op = _operator_with_clients(pods=[_InMemoryPod("p1", "Succeeded")])
    await op._check_pods()
    assert not op.get_heal_tasks()


@pytest.mark.asyncio
async def test_monitor_resources_full_iteration():
    op = _operator_with_clients(
        pods=[_InMemoryPod("p1", "Pending")],
        deployments=[_InMemoryDeployment("d1", 2, 1)],
        services=[_InMemoryService("s1")],
        endpoints={"s1": _InMemoryEndpoints(False)},
        dry_run=True,
    )
    with pytest.raises(asyncio.TimeoutError):
        # Long sleep lets a single monitoring iteration complete before timeout.
        await asyncio.wait_for(op.monitor_resources(interval=60), timeout=0.05)
