# -*- coding: utf-8 -*-
"""Targeted coverage tests for the remaining four below-80% modules."""

from __future__ import annotations

import asyncio
import sys
import types
from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import pytest

class _FakeEndpoints:
    def __init__(self, has: bool = True):
        self.subsets = [SimpleNamespace(addresses=[SimpleNamespace()])] if has else []


# ----------------------------------------------------------------------
# Optional-dependency fakes (only install when missing so we don't clobber
# more comprehensive fakes from earlier batch files if they were loaded first).
# ----------------------------------------------------------------------
if "kubernetes" not in sys.modules:
    _k = types.ModuleType("kubernetes")
    _kc = types.ModuleType("kubernetes.client")
    _kcfg = types.ModuleType("kubernetes.config")
    _kr = types.ModuleType("kubernetes.client.rest")
    _k.client = _kc
    _k.config = _kcfg
    _kc.rest = _kr

    class _KApiException(Exception):
        def __init__(self, status: int = 500):
            self.status = status

    class _KConfigException(Exception):
        pass

    class _V1DeleteOptions:
        pass

    class _FakeEndpoints:
        def __init__(self, has: bool = True):
            self.subsets = [SimpleNamespace(addresses=[SimpleNamespace()])] if has else []

    class _FakeCoreV1:
        def __init__(self):
            self.pods: List[Any] = []
            self.services: List[Any] = []
            self.endpoints: Dict[str, Any] = {}

        def list_namespaced_pod(self, ns: str):
            return SimpleNamespace(items=self.pods)

        def list_namespaced_service(self, ns: str):
            return SimpleNamespace(items=self.services)

        def read_namespaced_pod(self, name: str, namespace: str):
            for p in self.pods:
                if p.metadata.name == name:
                    return p
            raise _KApiException(404)

        def read_namespaced_endpoints(self, name: str, namespace: str):
            return self.endpoints.get(name, _FakeEndpoints(False))

        def delete_namespaced_pod(self, name: str, namespace: str, body: Any):
            pass

    class _FakeAppsV1:
        def __init__(self):
            self.deployments: List[Any] = []

        def list_namespaced_deployment(self, ns: str):
            return SimpleNamespace(items=self.deployments)

        def patch_namespaced_deployment(self, name: str, namespace: str, body: Any):
            pass

        def read_namespaced_deployment(self, name: str, namespace: str):
            for d in self.deployments:
                if d.metadata.name == name:
                    return d
            raise _KApiException(404)

    _kc.CoreV1Api = _FakeCoreV1
    _kc.AppsV1Api = _FakeAppsV1
    _kc.V1DeleteOptions = _V1DeleteOptions
    _kr.ApiException = _KApiException
    _kcfg.ConfigException = _KConfigException
    _kcfg.load_kube_config = lambda *a, **k: None
    _kcfg.load_incluster_config = lambda *a, **k: None
    sys.modules["kubernetes"] = _k
    sys.modules["kubernetes.client"] = _kc
    sys.modules["kubernetes.config"] = _kcfg
    sys.modules["kubernetes.client.rest"] = _kr

if "prophet" not in sys.modules:
    _prophet = types.ModuleType("prophet")
    _prophet_diag = types.ModuleType("prophet.diagnostics")

    class _FakeProphet:
        def __init__(self, **params: Any):
            self.params = params
            self._df: Optional[pd.DataFrame] = None

        def fit(self, df: pd.DataFrame):
            self._df = df

        def add_holidays(self, holidays: pd.DataFrame):
            pass

        def make_future_dataframe(self, periods: int, freq: str):
            start = (
                self._df["ds"].max()
                if self._df is not None
                else pd.Timestamp("2024-01-01")
            )
            return pd.DataFrame({"ds": pd.date_range(start, periods=periods, freq=freq)})

        def predict(self, future: pd.DataFrame):
            n = len(future)
            return pd.DataFrame(
                {
                    "ds": future["ds"].values,
                    "yhat": np.linspace(10, 15, n),
                    "yhat_lower": np.linspace(8, 13, n),
                    "yhat_upper": np.linspace(12, 17, n),
                    "trend": np.linspace(10, 15, n),
                    "seasonal": np.zeros(n),
                }
            )

    def _fake_cross_validation(model: Any, initial: str, period: str, horizon: str):
        return pd.DataFrame(
            {
                "ds": pd.date_range("2024-01-01", periods=5, freq="D"),
                "y": [1.0] * 5,
                "yhat": [1.0] * 5,
            }
        )

    def _fake_performance_metrics(df: pd.DataFrame):
        return pd.DataFrame({"rmse": [1.0], "mae": [1.0], "mape": [1.0]})

    _prophet.Prophet = _FakeProphet
    _prophet_diag.cross_validation = _fake_cross_validation
    _prophet_diag.performance_metrics = _fake_performance_metrics
    _prophet.diagnostics = _prophet_diag
    sys.modules["prophet"] = _prophet
    sys.modules["prophet.diagnostics"] = _prophet_diag


# ----------------------------------------------------------------------
# Imports of the modules under test
# ----------------------------------------------------------------------
from modules.execute.auto_heal.operator import (  # noqa: E402
    AutoHealOperator,
    HealConditionType,
    HealPhase,
)
import modules.execute.auto_heal.operator as _operator_mod  # noqa: E402

from modules.storage.clickhouse.storage import (  # noqa: E402
    ClickHouseStorage,
    create_clickhouse_storage,
)
import modules.storage.clickhouse.storage as _storage_mod  # noqa: E402

from modules.analyze.cost.forecast import CostForecaster  # noqa: E402

from modules.analyze.anomaly.data_preprocessing import (  # noqa: E402
    MultiModalDataPreparer,
    TimeSeriesAugmenter,
    TimeSeriesCleaner,
    TimeSeriesDataLoader,
    TimeSeriesFeatureEngineer,
    TimeSeriesPreprocessingPipeline,
    TimeSeriesScaler,
    TimeSeriesSplitter,
    create_preprocessing_pipeline,
)
import modules.analyze.anomaly.data_preprocessing as _data_mod  # noqa: E402


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
async def _noop_sleep(*a: Any, **k: Any):
    return None


def _httpx_success():
    mod = types.ModuleType("httpx")

    class _Resp:
        status_code = 200
        text = "ok"

        def raise_for_status(self):
            pass

    mod.post = lambda *a, **k: _Resp()
    mod.RequestError = Exception

    class _HTTPStatusError(Exception):
        response = SimpleNamespace(text="boom")

    mod.HTTPStatusError = _HTTPStatusError
    return mod


def _httpx_request_error():
    mod = _httpx_success()

    def _post(*a, **k):
        raise mod.RequestError("boom")

    mod.post = _post
    return mod


def _httpx_status_error():
    mod = _httpx_success()

    def _post(*a, **k):
        raise mod.HTTPStatusError("boom")

    mod.post = _post
    return mod


def _prom_empty():
    mod = types.ModuleType("prometheus_api_client")

    class _EmptyPromConnect:
        def __init__(self, *a: Any, **k: Any):
            pass

        def custom_query_range(self, **kw: Any):
            return []

    mod.PrometheusConnect = _EmptyPromConnect
    return mod


# ----------------------------------------------------------------------
# Auto-Heal operator
# ----------------------------------------------------------------------
class TestAutoHealOperatorRemaining:
    def test_initialize_with_kubeconfig(self):
        op = AutoHealOperator(kubeconfig="/tmp/k")
        op.initialize()
        assert op._is_initialized

    def test_initialize_incluster_fallback(self, monkeypatch: pytest.MonkeyPatch):
        def _raise(*a: Any, **k: Any):
            raise _operator_mod.config.ConfigException("no in-cluster")

        monkeypatch.setattr(_operator_mod.config, "load_incluster_config", _raise)
        op = AutoHealOperator()
        op.initialize()
        assert op._is_initialized

    def test_initialize_error(self, monkeypatch: pytest.MonkeyPatch):
        def _raise(*a: Any, **k: Any):
            raise RuntimeError("boom")

        monkeypatch.setattr(_operator_mod.config, "load_kube_config", _raise)
        op = AutoHealOperator(kubeconfig="/tmp/k")
        op.initialize()
        assert not op._is_initialized

    @pytest.mark.asyncio
    async def test_monitor_resources_error(self, monkeypatch: pytest.MonkeyPatch):
        op = AutoHealOperator()
        op.initialize()

        async def _boom():
            raise RuntimeError("boom")

        monkeypatch.setattr(op, "_check_pods", _boom)
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(op.monitor_resources(interval=0), timeout=0.05)

    @pytest.mark.asyncio
    async def test_check_deployments(self):
        op = AutoHealOperator()
        op.initialize()

        class D:
            pass

        d = D()
        d.metadata = SimpleNamespace(name="d1")
        d.spec = SimpleNamespace(replicas=3)
        d.status = SimpleNamespace(available_replicas=1)
        op._apps_client.deployments = [d]
        await op._check_deployments()

    @pytest.mark.asyncio
    async def test_check_pods_api_error(self, monkeypatch: pytest.MonkeyPatch):
        op = AutoHealOperator()
        op.initialize()
        # use the ApiException class imported by the operator module

        monkeypatch.setattr(
            op._k8s_client, "list_namespaced_pod", lambda ns: (_ for _ in ()).throw(_operator_mod.ApiException(500))
        )
        await op._check_pods()

    @pytest.mark.asyncio
    async def test_check_deployments_api_error(self, monkeypatch: pytest.MonkeyPatch):
        op = AutoHealOperator()
        op.initialize()
        # use the ApiException class imported by the operator module

        monkeypatch.setattr(
            op._apps_client,
            "list_namespaced_deployment",
            lambda ns: (_ for _ in ()).throw(_operator_mod.ApiException(500)),
        )
        await op._check_deployments()

    @pytest.mark.asyncio
    async def test_check_services_api_error(self, monkeypatch: pytest.MonkeyPatch):
        op = AutoHealOperator()
        op.initialize()
        # use the ApiException class imported by the operator module

        monkeypatch.setattr(
            op._k8s_client, "list_namespaced_service", lambda ns: (_ for _ in ()).throw(_operator_mod.ApiException(500))
        )
        await op._check_services()

    @pytest.mark.asyncio
    async def test_trigger_heal_dry_run(self):
        op = AutoHealOperator(dry_run=True)
        op.initialize()
        await op._trigger_heal("Pod", "p1", HealConditionType.PodNotReady, {})
        assert op.get_heal_tasks()

    @pytest.mark.asyncio
    async def test_execute_heal_pod(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr("asyncio.sleep", _noop_sleep)
        op = AutoHealOperator()
        task = {
            "task_id": "t1",
            "resource_type": "Pod",
            "resource_name": "p1",
            "condition": HealConditionType.PodNotReady.value,
            "details": {},
            "phase": HealPhase.Pending.value,
            "created_at": datetime.now().isoformat(),
            "namespace": "default",
        }
        await op._execute_heal(task)
        assert task["phase"] == HealPhase.Completed.value

    @pytest.mark.asyncio
    async def test_execute_heal_deployment(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr("asyncio.sleep", _noop_sleep)
        op = AutoHealOperator()
        task = {
            "task_id": "t2",
            "resource_type": "Deployment",
            "resource_name": "d1",
            "condition": HealConditionType.PodNotReady.value,
            "details": {},
            "phase": HealPhase.Pending.value,
            "created_at": datetime.now().isoformat(),
            "namespace": "default",
        }
        await op._execute_heal(task)
        assert task["phase"] == HealPhase.Completed.value

    @pytest.mark.asyncio
    async def test_execute_heal_service(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr("asyncio.sleep", _noop_sleep)
        op = AutoHealOperator()
        task = {
            "task_id": "t3",
            "resource_type": "Service",
            "resource_name": "s1",
            "condition": HealConditionType.ServiceDown.value,
            "details": {},
            "phase": HealPhase.Pending.value,
            "created_at": datetime.now().isoformat(),
            "namespace": "default",
        }
        await op._execute_heal(task)
        assert task["phase"] == HealPhase.Completed.value

    @pytest.mark.asyncio
    async def test_execute_heal_exception(self, monkeypatch: pytest.MonkeyPatch):
        async def _boom(task: Any) -> bool:
            raise RuntimeError("boom")

        monkeypatch.setattr("asyncio.sleep", _noop_sleep)
        op = AutoHealOperator()
        monkeypatch.setattr(op, "_heal_pod", _boom)
        task = {
            "task_id": "t4",
            "resource_type": "Pod",
            "resource_name": "p1",
            "condition": HealConditionType.PodNotReady.value,
            "details": {},
            "phase": HealPhase.Pending.value,
            "created_at": datetime.now().isoformat(),
            "namespace": "default",
        }
        await op._execute_heal(task)
        assert task["phase"] == HealPhase.Failed.value
        assert "error" in task

    @pytest.mark.asyncio
    async def test_heal_pod_stateful(self):
        op = AutoHealOperator()
        op.initialize()

        class Ref:
            controller = True
            kind = "StatefulSet"

        class Pod:
            pass

        p = Pod()
        p.metadata = SimpleNamespace(name="p1", owner_references=[Ref()])
        p.spec = SimpleNamespace(containers=[SimpleNamespace()], volumes=[])
        p.status = SimpleNamespace(phase="Running")
        op._k8s_client.pods = [p]
        task = {
            "task_id": "t5",
            "resource_type": "Pod",
            "resource_name": "p1",
            "condition": HealConditionType.PodNotReady.value,
            "details": {},
            "phase": HealPhase.Pending.value,
            "created_at": datetime.now().isoformat(),
            "namespace": "default",
        }
        assert not await op._heal_pod(task)

    @pytest.mark.asyncio
    async def test_heal_pod_pvc_no_controller(self):
        op = AutoHealOperator()
        op.initialize()

        class Ref:
            controller = False
            kind = "ReplicaSet"

        class Pod:
            pass

        p = Pod()
        p.metadata = SimpleNamespace(name="p1", owner_references=[Ref()])
        p.spec = SimpleNamespace(
            containers=[SimpleNamespace()],
            volumes=[SimpleNamespace(persistent_volume_claim=SimpleNamespace())],
        )
        p.status = SimpleNamespace(phase="Running")
        op._k8s_client.pods = [p]
        task = {
            "task_id": "t6",
            "resource_type": "Pod",
            "resource_name": "p1",
            "condition": HealConditionType.PodNotReady.value,
            "details": {},
            "phase": HealPhase.Pending.value,
            "created_at": datetime.now().isoformat(),
            "namespace": "default",
        }
        assert not await op._heal_pod(task)

    @pytest.mark.asyncio
    async def test_heal_pod_api_error(self, monkeypatch: pytest.MonkeyPatch):
        op = AutoHealOperator()
        op.initialize()
        # use the ApiException class imported by the operator module

        class Pod:
            pass

        p = Pod()
        p.metadata = SimpleNamespace(name="p1", owner_references=[])
        p.spec = SimpleNamespace(containers=[SimpleNamespace()], volumes=[])
        p.status = SimpleNamespace(phase="Running")
        op._k8s_client.pods = [p]
        monkeypatch.setattr(
            op._k8s_client,
            "read_namespaced_pod",
            lambda name, namespace: (_ for _ in ()).throw(_operator_mod.ApiException(500)),
        )
        task = {
            "task_id": "t7",
            "resource_type": "Pod",
            "resource_name": "p1",
            "condition": HealConditionType.PodNotReady.value,
            "details": {},
            "phase": HealPhase.Pending.value,
            "created_at": datetime.now().isoformat(),
            "namespace": "default",
        }
        assert not await op._heal_pod(task)

    @pytest.mark.asyncio
    async def test_heal_deployment_initialized(self):
        op = AutoHealOperator()
        op.initialize()

        class D:
            pass

        d = D()
        d.metadata = SimpleNamespace(name="d1")
        op._apps_client.deployments = [d]
        task = {
            "task_id": "t8",
            "resource_type": "Deployment",
            "resource_name": "d1",
            "condition": HealConditionType.PodNotReady.value,
            "details": {},
            "phase": HealPhase.Pending.value,
            "created_at": datetime.now().isoformat(),
            "namespace": "default",
        }
        assert await op._heal_deployment(task)

    @pytest.mark.asyncio
    async def test_heal_service_initialized(self):
        op = AutoHealOperator()
        op.initialize()
        task = {
            "task_id": "t9",
            "resource_type": "Service",
            "resource_name": "s1",
            "condition": HealConditionType.ServiceDown.value,
            "details": {},
            "phase": HealPhase.Pending.value,
            "created_at": datetime.now().isoformat(),
            "namespace": "default",
        }
        assert await op._heal_service(task)

    @pytest.mark.asyncio
    async def test_verify_pod(self):
        op = AutoHealOperator()
        op.initialize()

        class Pod:
            pass

        p = Pod()
        p.metadata = SimpleNamespace(name="p1")
        p.spec = SimpleNamespace()
        p.status = SimpleNamespace(phase="Running")
        op._k8s_client.pods = [p]
        assert await op._verify_pod("p1")

        p2 = Pod()
        p2.metadata = SimpleNamespace(name="p2")
        p2.spec = SimpleNamespace()
        p2.status = SimpleNamespace(phase=None)
        op._k8s_client.pods = [p2]
        assert not await op._verify_pod("p2")

    @pytest.mark.asyncio
    async def test_verify_pod_api_error(self, monkeypatch: pytest.MonkeyPatch):
        op = AutoHealOperator()
        op.initialize()
        # use the ApiException class imported by the operator module

        monkeypatch.setattr(
            op._k8s_client,
            "read_namespaced_pod",
            lambda name, namespace: (_ for _ in ()).throw(_operator_mod.ApiException(500)),
        )
        assert not await op._verify_pod("missing")

    @pytest.mark.asyncio
    async def test_verify_deployment(self):
        op = AutoHealOperator()
        op.initialize()

        class D:
            pass

        d = D()
        d.metadata = SimpleNamespace(name="d1")
        d.spec = SimpleNamespace(replicas=2)
        d.status = SimpleNamespace(available_replicas=2)
        op._apps_client.deployments = [d]
        assert await op._verify_deployment("d1")

    @pytest.mark.asyncio
    async def test_verify_deployment_api_error(self, monkeypatch: pytest.MonkeyPatch):
        op = AutoHealOperator()
        op.initialize()
        # use the ApiException class imported by the operator module

        monkeypatch.setattr(
            op._apps_client,
            "read_namespaced_deployment",
            lambda name, namespace: (_ for _ in ()).throw(_operator_mod.ApiException(500)),
        )
        assert not await op._verify_deployment("missing")

    @pytest.mark.asyncio
    async def test_verify_service(self):
        op = AutoHealOperator()
        op.initialize()
        op._k8s_client.endpoints = {"s1": _FakeEndpoints(True)}
        assert await op._verify_service("s1")

    @pytest.mark.asyncio
    async def test_verify_service_api_error(self, monkeypatch: pytest.MonkeyPatch):
        op = AutoHealOperator()
        op.initialize()
        # use the ApiException class imported by the operator module

        monkeypatch.setattr(
            op._k8s_client,
            "read_namespaced_endpoints",
            lambda name, namespace: (_ for _ in ()).throw(_operator_mod.ApiException(500)),
        )
        assert not await op._verify_service("missing")

    def test_cleanup_completed_tasks(self):
        op = AutoHealOperator()
        now = datetime.now()
        op._heal_tasks = {
            "old": {
                "phase": HealPhase.Completed.value,
                "completed_at": (now - timedelta(hours=2)).isoformat(),
            },
            "recent": {
                "phase": HealPhase.Completed.value,
                "completed_at": (now - timedelta(minutes=5)).isoformat(),
            },
            "failed": {
                "phase": HealPhase.Failed.value,
                "completed_at": (now - timedelta(hours=2)).isoformat(),
            },
            "pending": {
                "phase": HealPhase.Pending.value,
                "created_at": now.isoformat(),
            },
        }
        op._cleanup_completed_tasks()
        assert "old" not in op._heal_tasks
        assert "recent" in op._heal_tasks
        assert "failed" not in op._heal_tasks
        assert "pending" in op._heal_tasks

    def test_get_task_stats(self):
        op = AutoHealOperator()
        op._heal_tasks = {
            "a": {"phase": HealPhase.Pending.value},
            "b": {"phase": HealPhase.Completed.value},
        }
        stats = op.get_task_stats()
        assert stats["total"] == 2
        assert stats["by_phase"][HealPhase.Pending.value] == 1
        assert stats["by_phase"][HealPhase.Completed.value] == 1


# ----------------------------------------------------------------------
# ClickHouse storage
# ----------------------------------------------------------------------
class TestClickHouseStorageRemaining:
    def test_execute_query_http_status_error(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setitem(sys.modules, "httpx", _httpx_status_error())
        s = ClickHouseStorage({})
        with pytest.raises(RuntimeError):
            s._execute_query("SELECT 1")

    def test_store_metric_not_initialized(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setitem(sys.modules, "httpx", _httpx_success())
        s = ClickHouseStorage({"read_only": False})
        assert not asyncio.run(s.store_metric("cpu", 0.5, {}, datetime.now()))

    def test_store_metric_httpx_error(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setitem(sys.modules, "httpx", _httpx_request_error())
        s = ClickHouseStorage({"read_only": False})
        s._is_initialized = True
        assert not asyncio.run(s.store_metric("cpu", 0.5, {}, datetime.now()))

    def test_store_anomaly_not_initialized(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setitem(sys.modules, "httpx", _httpx_success())
        s = ClickHouseStorage({"read_only": False})
        assert not asyncio.run(
            s.store_anomaly("a1", "svc", "critical", "desc", {}, datetime.now())
        )

    def test_store_anomaly_httpx_error(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setitem(sys.modules, "httpx", _httpx_request_error())
        s = ClickHouseStorage({"read_only": False})
        s._is_initialized = True
        assert not asyncio.run(
            s.store_anomaly("a1", "svc", "critical", "desc", {}, datetime.now())
        )

    def test_store_event_not_initialized(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setitem(sys.modules, "httpx", _httpx_success())
        s = ClickHouseStorage({"read_only": False})
        assert not asyncio.run(s.store_event("ev", "src", {}, datetime.now()))

    def test_store_event_httpx_error(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setitem(sys.modules, "httpx", _httpx_request_error())
        s = ClickHouseStorage({"read_only": False})
        s._is_initialized = True
        assert not asyncio.run(s.store_event("ev", "src", {}, datetime.now()))

    def test_query_metrics_invalid(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setitem(sys.modules, "httpx", _httpx_success())
        s = ClickHouseStorage({"read_only": True})
        s._is_initialized = True
        now = datetime.now()
        assert asyncio.run(s.query_metrics("bad name!", now - timedelta(hours=1), now)) == []

    def test_query_metrics_with_filters(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setitem(sys.modules, "httpx", _httpx_success())
        s = ClickHouseStorage({"read_only": True})
        s._is_initialized = True
        now = datetime.now()
        assert (
            asyncio.run(
                s.query_metrics(
                    "cpu",
                    now - timedelta(hours=1),
                    now,
                    filters={"host": "x"},
                )
            )
            == []
        )

    def test_query_anomalies_not_initialized(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setitem(sys.modules, "httpx", _httpx_success())
        s = ClickHouseStorage({"read_only": True})
        now = datetime.now()
        assert asyncio.run(s.query_anomalies(now - timedelta(hours=1), now)) == []

    def test_query_anomalies_with_service_severity(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setitem(sys.modules, "httpx", _httpx_success())
        s = ClickHouseStorage({"read_only": True})
        s._is_initialized = True
        now = datetime.now()
        assert (
            asyncio.run(
                s.query_anomalies(
                    now - timedelta(hours=1),
                    now,
                    service="svc",
                    severity="critical",
                )
            )
            == []
        )

    def test_get_storage_stats_error(self, monkeypatch: pytest.MonkeyPatch):
        s = ClickHouseStorage({})
        s._is_initialized = True
        s._tiers = {"hot": None}
        assert asyncio.run(s.get_storage_stats()) == {}

    def test_move_to_tier(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setitem(sys.modules, "httpx", _httpx_success())
        s = ClickHouseStorage({"read_only": False})
        s._is_initialized = True
        assert asyncio.run(s.move_to_tier("metrics", "cold", datetime.now())) == 0

    def test_move_to_tier_httpx_error(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setitem(sys.modules, "httpx", _httpx_request_error())
        s = ClickHouseStorage({"read_only": False})
        s._is_initialized = True
        assert asyncio.run(s.move_to_tier("metrics", "cold", datetime.now())) == 0

    def test_create_storage_exception(self, monkeypatch: pytest.MonkeyPatch):
        class Bad:
            def __init__(self, *a: Any, **k: Any):
                raise RuntimeError("boom")

        monkeypatch.setattr(_storage_mod, "ClickHouseStorage", Bad)
        assert create_clickhouse_storage({}) is None


# ----------------------------------------------------------------------
# Cost forecast
# ----------------------------------------------------------------------
class TestCostForecasterRemaining:
    @pytest.fixture
    def cost_data(self) -> List[Dict[str, Any]]:
        base = datetime(2024, 1, 1)
        return [
            {
                "timestamp": (base + timedelta(days=i)).isoformat(),
                "cost": float(10 + i),
                "feature_a": float(i),
                "feature_b": float(i * 0.5),
            }
            for i in range(15)
        ]

    def test_prepare_prophet_missing_cost_col(self):
        cf = CostForecaster()
        with pytest.raises(ValueError):
            cf._prepare_prophet_data([{"timestamp": "2024-01-01"}])

    def test_prepare_gbm_auto_features(self, cost_data):
        cf = CostForecaster()
        X, y = cf._prepare_gbm_features(cost_data, "cost")
        assert len(X) == len(cost_data)
        assert cf.feature_names == ["feature_a", "feature_b"]

    def test_prepare_gbm_no_features(self):
        cf = CostForecaster()
        with pytest.raises(ValueError):
            cf._prepare_gbm_features([{"cost": 1.0}], "cost")

    def test_fit_no_models(self, cost_data):
        cf = CostForecaster(use_prophet=False, use_gbm=False)
        cf.fit(cost_data)
        assert cf.is_fitted

    def test_fit_insufficient_prophet(self):
        cf = CostForecaster(use_prophet=True, use_gbm=False)
        data = [{"timestamp": "2024-01-01", "cost": 1.0}]
        cf.fit(data)
        assert cf.is_fitted

    def test_fit_gbm(self, cost_data):
        cf = CostForecaster(use_prophet=False, use_gbm=True)
        cf.fit(cost_data)
        assert cf.is_fitted
        assert cf.gbm_model is not None

    def test_forecast_not_fitted(self):
        cf = CostForecaster()
        with pytest.raises(RuntimeError):
            cf.forecast(periods=3)

    def test_forecast_no_prophet(self, cost_data):
        cf = CostForecaster(use_prophet=False)
        cf.fit(cost_data)
        result = cf.forecast(periods=3)
        assert result["predictions"] == []
        assert "metrics" in result

    def test_recommend_within_budget(self):
        cf = CostForecaster()
        forecast = [{"cost": float(i)} for i in range(5)]
        rec = cf.recommend_cost_optimization(forecast, budget=1000.0)
        assert rec["budget_status"] == "within_budget"

    def test_recommend_no_growth(self):
        cf = CostForecaster()
        forecast = [{"cost": 10.0} for _ in range(5)]
        rec = cf.recommend_cost_optimization(forecast, threshold=0.5)
        assert all(r["type"] != "cost_growth" for r in rec["recommendations"])

    def test_recommend_negative_growth(self):
        cf = CostForecaster()
        forecast = [{"cost": float(10 - i)} for i in range(5)]
        rec = cf.recommend_cost_optimization(forecast, threshold=0.05)
        growth_recs = [r for r in rec["recommendations"] if r["type"] == "cost_growth"]
        assert growth_recs and growth_recs[0]["severity"] == "low"

    def test_recommend_no_peak(self):
        cf = CostForecaster()
        forecast = [{"cost": 10.0} for _ in range(5)]
        rec = cf.recommend_cost_optimization(forecast)
        assert all(r["type"] != "peak_cost" for r in rec["recommendations"])

    def test_compare_empty(self):
        cf = CostForecaster()
        f = [{"timestamp": "2024-01-01T00:00:00", "cost": 1.0}]
        a = [{"timestamp": "2024-01-02T00:00:00", "cost": 2.0}]
        assert "error" in cf.compare_with_actual(f, a)

    def test_save_not_fitted(self):
        cf = CostForecaster()
        with pytest.raises(RuntimeError):
            cf.save_model("x.joblib")


# ----------------------------------------------------------------------
# Data preprocessing
# ----------------------------------------------------------------------
class TestDataPreprocessingRemaining:
    @pytest.fixture
    def sample_df(self) -> pd.DataFrame:
        rng = pd.date_range("2024-01-01", periods=20, freq="h")
        return pd.DataFrame({"timestamp": rng, "value": np.random.rand(20) * 100})

    def test_load_csv_missing_timestamp(self, tmp_path: Path):
        p = tmp_path / "ts.csv"
        pd.DataFrame({"value": [1, 2, 3]}).to_csv(p, index=False)
        with pytest.raises(ValueError):
            TimeSeriesDataLoader.load_from_csv(str(p), timestamp_col="ts")

    def test_load_csv_additional_cols(self, tmp_path: Path):
        p = tmp_path / "ts.csv"
        pd.DataFrame(
            {"timestamp": pd.date_range("2024-01-01", periods=5, freq="h"), "value": [1, 2, 3, 4, 5], "x": [1, 2, 3, 4, 5]}
        ).to_csv(p, index=False)
        df = TimeSeriesDataLoader.load_from_csv(str(p), additional_cols=["x"])
        assert "x" in df.columns

    def test_load_database_invalid_query(self):
        with pytest.raises(ValueError):
            TimeSeriesDataLoader.load_from_database(123, {})

    def test_load_database_missing_param(self):
        with pytest.raises(ValueError):
            TimeSeriesDataLoader.load_from_database("SELECT 1", {"user": "u"})

    def test_load_prometheus_no_data(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setitem(sys.modules, "prometheus_api_client", _prom_empty())
        with pytest.raises(ValueError):
            TimeSeriesDataLoader.load_from_prometheus(
                "up",
                "2024-01-01T00:00:00Z",
                "2024-01-01T01:00:00Z",
            )

    def test_handle_missing_methods(self):
        df = pd.DataFrame({"value": [1.0, np.nan, 3.0, 5.0]})
        assert TimeSeriesCleaner.handle_missing_values(df, method="bfill")["value"].isna().sum() == 0
        assert TimeSeriesCleaner.handle_missing_values(df, method="interpolate")["value"].isna().sum() == 0
        assert TimeSeriesCleaner.handle_missing_values(df, method="drop").shape[0] == 3
        assert TimeSeriesCleaner.handle_missing_values(df, method="zero")["value"].isna().sum() == 0

    def test_remove_outliers_methods(self):
        df = pd.DataFrame({"value": [1.0, 2.0, 3.0, 4.0, 5.0]})
        assert TimeSeriesCleaner.remove_outliers(df, method="zscore").shape[0] == 5
        assert TimeSeriesCleaner.remove_outliers(df, method="isolation").shape[0] <= 5
        with pytest.raises(ValueError):
            TimeSeriesCleaner.remove_outliers(df, method="bad")

    def test_remove_outliers_no_outliers(self):
        df = pd.DataFrame({"value": [1.0, 2.0, 3.0, 4.0]})
        out = TimeSeriesCleaner.remove_outliers(df, threshold=1.5)
        assert len(out) == 4

    def test_resample_aggs(self, sample_df):
        for agg in ["sum", "max", "min", "median"]:
            out = TimeSeriesCleaner.resample(sample_df, freq="2h", agg=agg)
            assert "timestamp" in out.columns
        with pytest.raises(ValueError):
            TimeSeriesCleaner.resample(sample_df, freq="2h", agg="bad")

    def test_time_warp(self):
        data = np.random.rand(10, 2)
        out = TimeSeriesAugmenter.time_warp(data)
        assert out.shape == data.shape

    def test_magnitude_warp(self):
        data = np.random.rand(10, 2)
        out = TimeSeriesAugmenter.magnitude_warp(data)
        assert out.shape == data.shape

    def test_augment_dataset_labels_none(self):
        data = np.random.rand(10, 2)
        out, labels = TimeSeriesAugmenter.augment_dataset(data, None, augment_factor=2)
        assert out.shape[0] == 20
        assert labels is None

    def test_augment_dataset_magnitude_warp(self, monkeypatch: pytest.MonkeyPatch):
        data = np.random.rand(10, 2)
        labels = np.zeros(10)
        monkeypatch.setattr(
            "modules.analyze.anomaly.data_preprocessing.np.random.choice",
            lambda *a, **k: "magnitude_warp",
        )
        out, l = TimeSeriesAugmenter.augment_dataset(data, labels, augment_factor=2)
        assert out.shape[0] == 20

    def test_scaler_3d(self):
        data = np.random.rand(10, 3, 2)
        scaler = TimeSeriesScaler(method="standard")
        out = scaler.fit_transform(data)
        assert out.shape == data.shape
        inv = scaler.inverse_transform(out)
        assert inv.shape == data.shape

    def test_splitter_shuffle(self):
        data = np.random.rand(100, 3)
        labels = np.random.rand(100)
        tr, v, te, tl, vl, tel = TimeSeriesSplitter.train_val_test_split(
            data, labels, 0.7, 0.15, 0.15, shuffle=True
        )
        assert len(tr) + len(v) + len(te) == 100

    def test_pipeline_clean_missing_false(self, sample_df):
        p = TimeSeriesPreprocessingPipeline(clean_missing=False, clean_outliers=False, scale=False)
        out = p.process(sample_df, "timestamp", "value")
        assert isinstance(out, np.ndarray)

    def test_pipeline_clean_outliers(self, sample_df):
        p = TimeSeriesPreprocessingPipeline(clean_outliers=True, scale=False)
        out = p.process(sample_df, "timestamp", "value")
        assert isinstance(out, np.ndarray)

    def test_pipeline_feature_cols_explicit(self, sample_df):
        p = TimeSeriesPreprocessingPipeline(scale=False)
        out = p.process(sample_df, "timestamp", "value", feature_cols=["value"])
        assert out.shape[1] == 1

    def test_pipeline_for_training_augment(self, sample_df):
        labels = np.random.rand(len(sample_df))
        p = TimeSeriesPreprocessingPipeline(scale=False, augment=True, augment_factor=2)
        out, l = p.process_for_training(sample_df, labels, "timestamp", "value")
        assert isinstance(out, np.ndarray)
        assert l is not None and len(l) == len(out)

    def test_prepare_log_features_with_embedding_model(self):
        class FakeEmbed:
            def encode(self, logs, show_progress_bar=False):
                return np.random.rand(len(logs), 8)

        out = MultiModalDataPreparer.prepare_log_features(["a", "b"], embedding_model=FakeEmbed())
        assert out.shape == (2, 8)
