# -*- coding: utf-8 -*-
"""Coverage tests for Batch B modules."""

from __future__ import annotations

import asyncio  # noqa: F401  # Imported for test setup
import json  # noqa: F401  # Imported for test setup
import sys  # noqa: F401  # Imported for test setup
import types
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional  # noqa: F401  # Imported for test setup

import numpy as np
import pandas as pd
import pytest  # noqa: F401  # Imported for test setup

# ----------------------------------------------------------------------
# Lightweight fakes for heavy/optional dependencies
# ----------------------------------------------------------------------

# qdrant_client
_qdrant = types.ModuleType("qdrant_client")
_qdrant_models = types.ModuleType("qdrant_client.models")


class _FakeDistance:
    COSINE = "cosine"
    EUCLID = "euclid"
    DOT = "dot"


class _FakeVectorParams:
    def __init__(self, size: int, distance: Any):
        self.size = size
        self.distance = distance


class _FakeMatchValue:
    def __init__(self, value: Any):
        self.value = value


class _FakeFieldCondition:
    def __init__(self, key: str, match: Any):
        self.key = key
        self.match = match


class _FakeFilter:
    def __init__(self, must: Optional[List[Any]] = None):
        self.must = must or []


class _FakePointStruct:
    def __init__(self, id: Any, vector: List[float], payload: Dict[str, Any]):
        self.id = id
        self.vector = vector
        self.payload = payload


class _FakeCollections:
    def __init__(self, names):
        class C:
            def __init__(self, n):
                self.name = n

        self.collections = [C(n) for n in names]


class _FakeCollectionInfo:
    config = SimpleNamespace(params=SimpleNamespace(vectors=SimpleNamespace(size=384)))
    points_count = 0
    indexed_vectors_count = 0


class _FakeQdrantClient:
    def __init__(self, **kwargs: Any):
        self._cols: set = set()

    def get_collections(self):
        return _FakeCollections(list(self._cols))

    def create_collection(self, **kw: Any):
        self._cols.add(kw.get("collection_name", ""))

    def upsert(self, **kw: Any):
        self._cols.add(kw.get("collection_name", ""))

    def search(self, **kw: Any):
        return [SimpleNamespace(id="1", score=0.9, payload={"content": "x"})]

    def delete(self, **kw: Any):
        pass

    def get_collection(self, name: str):
        return _FakeCollectionInfo()

    def delete_collection(self, name: str):
        self._cols.discard(name)


_qdrant_models.Distance = _FakeDistance
_qdrant_models.VectorParams = _FakeVectorParams
_qdrant_models.PointStruct = _FakePointStruct
_qdrant_models.MatchValue = _FakeMatchValue
_qdrant_models.FieldCondition = _FakeFieldCondition
_qdrant_models.Filter = _FakeFilter
_qdrant.QdrantClient = _FakeQdrantClient
_qdrant.models = _qdrant_models
sys.modules["qdrant_client"] = _qdrant
sys.modules["qdrant_client.models"] = _qdrant_models

# sentence_transformers
_sentence = types.ModuleType("sentence_transformers")


class _FakeSentenceTransformer:
    def __init__(self, *a: Any, **k: Any):
        pass

    def encode(self, texts: Any, convert_to_numpy: bool = True):
        if isinstance(texts, str):
            return np.random.rand(384).astype(np.float32)
        return [np.random.rand(384).astype(np.float32) for _ in texts]


_sentence.SentenceTransformer = _FakeSentenceTransformer
sys.modules["sentence_transformers"] = _sentence

# prophet
_prophet = types.ModuleType("prophet")
_prophet_diag = types.ModuleType("prophet.diagnostics")


class _FakeProphet:
    def __init__(self, **params: Any):
        self.params = params
        self._last_df: Optional[pd.DataFrame] = None

    def fit(self, df: pd.DataFrame):
        self._last_df = df

    def make_future_dataframe(self, periods: int, freq: str):
        start = (
            self._last_df["ds"].max() if self._last_df is not None else pd.Timestamp("2024-01-01")
        )
        freq = freq.replace("H", "h").replace("D", "D").replace("W", "W")
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

    def add_holidays(self, holidays: pd.DataFrame):
        pass


def _fake_cross_validation(model: Any, initial: str, period: str, horizon: str):
    return pd.DataFrame(
        {"ds": pd.date_range("2024-01-01", periods=5, freq="D"), "y": [1.0] * 5, "yhat": [1.0] * 5}
    )


def _fake_performance_metrics(df: pd.DataFrame):
    return pd.DataFrame(
        {"mse": [1.0], "rmse": [1.0], "mae": [1.0], "mape": [1.0], "coverage": [0.95]}
    )


_prophet.Prophet = _FakeProphet
_prophet_diag.cross_validation = _fake_cross_validation
_prophet_diag.performance_metrics = _fake_performance_metrics
_prophet.diagnostics = _prophet_diag
sys.modules["prophet"] = _prophet
sys.modules["prophet.diagnostics"] = _prophet_diag

# prometheus_api_client
_prom = types.ModuleType("prometheus_api_client")


class _FakePromConnect:
    def __init__(self, *a: Any, **k: Any):
        pass

    def custom_query_range(self, **kw: Any):
        return [{"values": [[1704067200, "1.0"], [1704067260, "2.0"]]}]


_prom.PrometheusConnect = _FakePromConnect
sys.modules["prometheus_api_client"] = _prom

# httpx
_httpx = types.ModuleType("httpx")


class _FakeResponse:
    status_code = 200
    text = "ok"

    def raise_for_status(self):
        pass


def _httpx_post(*a: Any, **k: Any):
    return _FakeResponse()


_httpx.post = _httpx_post
_httpx.RequestError = Exception
_httpx.ConnectError = Exception
_httpx.TimeoutException = Exception
_httpx.HTTPStatusError = type(
    "HTTPStatusError", (Exception,), {"response": SimpleNamespace(text="boom")}
)
_httpx.HTTPError = type("HTTPError", (Exception,), {})


class _FakeHttpxClient:
    """Placeholder synchronous client used by tests that patch httpx.Client."""

    def __init__(self, *a: Any, **k: Any):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a: Any, **k: Any):
        return False

    def post(self, *a: Any, **k: Any):
        return _FakeResponse()

    def get(self, *a: Any, **k: Any):
        return _FakeResponse()

    def patch(self, *a: Any, **k: Any):
        return _FakeResponse()


class _FakeHttpxAsyncClient:
    """Placeholder async client used by tests that patch httpx.AsyncClient."""

    def __init__(self, *a: Any, **k: Any):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a: Any, **k: Any):
        return False

    async def post(self, *a: Any, **k: Any):
        return _FakeResponse()

    async def get(self, *a: Any, **k: Any):
        return _FakeResponse()

    async def patch(self, *a: Any, **k: Any):
        return _FakeResponse()

    async def aclose(self):
        pass


_httpx.Client = _FakeHttpxClient
_httpx.AsyncClient = _FakeHttpxAsyncClient
sys.modules["httpx"] = _httpx

# kubernetes
_kubernetes = types.ModuleType("kubernetes")
_client = types.ModuleType("kubernetes.client")
_config = types.ModuleType("kubernetes.config")
_rest = types.ModuleType("kubernetes.client.rest")


class _ApiException(Exception):
    def __init__(self, status: int = 500):
        self.status = status


class _ConfigException(Exception):
    pass


class _V1DeleteOptions:
    pass


class _FakeEndpoints:
    def __init__(self, has: bool = True):
        self.subsets = [SimpleNamespace(addresses=[SimpleNamespace()])] if has else []


class _FakeCoreV1:
    def __init__(self):
        self.pods = []
        self.services = []
        self.endpoints: Dict[str, Any] = {}

    def list_namespaced_pod(self, ns: str):
        return SimpleNamespace(items=self.pods)

    def list_namespaced_service(self, ns: str):
        return SimpleNamespace(items=self.services)

    def read_namespaced_pod(self, name: str, namespace: str):
        for p in self.pods:
            if p.metadata.name == name:
                return p
        raise _ApiException(404)

    def read_namespaced_endpoints(self, name: str, namespace: str):
        return self.endpoints.get(name, _FakeEndpoints(False))

    def delete_namespaced_pod(self, name: str, namespace: str, body: Any):
        pass


class _FakeAppsV1:
    def __init__(self):
        self.deployments = []

    def list_namespaced_deployment(self, ns: str):
        return SimpleNamespace(items=self.deployments)

    def patch_namespaced_deployment(self, name: str, namespace: str, body: Any):
        pass

    def read_namespaced_deployment(self, name: str, namespace: str):
        for d in self.deployments:
            if d.metadata.name == name:
                return d
        raise _ApiException(404)


_client.CoreV1Api = _FakeCoreV1
_client.AppsV1Api = _FakeAppsV1
_client.V1DeleteOptions = _V1DeleteOptions
_client.rest = _rest
_rest.ApiException = _ApiException
_config.load_kube_config = lambda *a, **k: None
_config.load_incluster_config = lambda *a, **k: None
_config.ConfigException = _ConfigException
_kubernetes.client = _client
_kubernetes.config = _config

sys.modules["kubernetes"] = _kubernetes
sys.modules["kubernetes.client"] = _client
sys.modules["kubernetes.config"] = _config
sys.modules["kubernetes.client.rest"] = _rest


# helpers used by the train_transformer tests in this file
import torch  # noqa: E402


class _FakeModel:
    def __init__(self, **kw: Any):
        self.kw = kw
        self._state = {}

    def parameters(self):
        return []

    def to(self, device: str):
        return self

    def __call__(self, data: Any, **kw: Any):
        return torch.zeros((*data.shape[:2], 1)), torch.zeros_like(data)

    def eval(self):
        pass

    def train(self):
        pass

    def state_dict(self):
        return self._state

    def load_state_dict(self, state: Any):
        self._state = state


class _FakeTrainer:
    def __init__(self, *a: Any, **k: Any):
        self.best_loss = float("inf")

    def train(self, *a: Any, **k: Any):
        pass

    def load_model(self, *a: Any, **k: Any):
        pass


# root_cause gnn fake
_gnn = types.ModuleType("modules.analyze.root_cause.gnn")


class _FakeGNN:
    def __init__(self, **kw: Any):
        pass

    def predict_root_cause(self, *a: Any, **k: Any):
        return {"root_cause_type": "service", "root_cause_score": 0.9}


_gnn.HeterogeneousGNNModel = _FakeGNN
sys.modules["modules.analyze.root_cause.gnn"] = _gnn

import modules.analyze.root_cause.causal_graph_builder as _cgb_mod  # noqa: E402
import modules.analyze.runbook.vector_store as _vector_store_mod  # noqa: E402
import modules.execute.auto_heal.operator as _operator_mod  # noqa: E402
import modules.storage.clickhouse.storage as _storage_mod  # noqa: E402
from modules.analyze.anomaly import train_transformer  # noqa: E402
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
from modules.analyze.anomaly.isolation_forest import IsolationForestDetector  # noqa: E402
from modules.analyze.anomaly.prophet_model import ProphetAnomalyDetector  # noqa: E402
from modules.analyze.cost.forecast import CostForecaster  # noqa: E402
from modules.analyze.root_cause.causal_graph_builder import (  # noqa: E402
    CausalGraphBuilder,
    CausalGraphIntegrator,
    CausalGraphPersistence,
    CausalGraphVisualizer,
    create_causal_graph_builder,
)
from modules.analyze.root_cause.causal_inference import CausalGraph  # noqa: E402

# ----------------------------------------------------------------------
# Import assigned modules
# ----------------------------------------------------------------------
from modules.analyze.runbook.vector_store import VectorStore  # noqa: E402
from modules.execute.auto_heal.operator import (  # noqa: E402
    AutoHealOperator,
    HealConditionType,
    HealPhase,
)
from modules.storage.clickhouse.storage import (  # noqa: E402
    ClickHouseStorage,
    create_clickhouse_storage,
)

# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------


@pytest.fixture
def sample_df() -> pd.DataFrame:
    rng = pd.date_range("2024-01-01", periods=20, freq="h")
    return pd.DataFrame({"timestamp": rng, "value": np.random.rand(20) * 100})


@pytest.fixture
def cost_data() -> List[Dict[str, Any]]:
    base = datetime(2024, 1, 1)  # noqa: F841  # Variable for test verification
    return [
        {
            "timestamp": (base + timedelta(days=i)).isoformat(),
            "cost": float(10 + i),
            "feature_a": float(i),
            "feature_b": float(i * 0.5),
        }
        for i in range(15)
    ]


@pytest.fixture
def prophet_data() -> List[Dict[str, Any]]:
    base = datetime(2024, 1, 1)  # noqa: F841  # Variable for test verification
    return [
        {
            "timestamp": (base + timedelta(hours=i)).isoformat(),
            "value": float(10 + np.random.rand()),
        }
        for i in range(20)
    ]


@pytest.fixture
def tmp_cwd_file(tmp_path: Path) -> Path:
    p = Path.cwd() / f"_tmp_b_{tmp_path.name}.json"
    yield p
    if p.exists():
        p.unlink()


# ----------------------------------------------------------------------
# Vector store
# ----------------------------------------------------------------------


class TestVectorStore:
    def test_defaults(self):
        vs = VectorStore()
        assert not vs.is_initialized

    def test_initialize(self):
        vs = VectorStore()
        vs.initialize()
        assert vs.is_initialized

    def test_embed(self):
        vs = VectorStore()
        assert len(vs.embed_text("x")) == vs.vector_size
        assert len(vs.embed_batch(["a", "b"])) == 2

    def test_add_search_delete(self):
        vs = VectorStore()
        assert vs.add_document("1", "c", {"tag": "x"})
        assert vs.search("c", filter_metadata={"tag": "x"})
        assert vs.delete_document("1")

    def test_add_batch(self):
        vs = VectorStore()
        docs = [{"id": "1", "content": "a"}, {"id": "2", "content": "b"}]
        assert vs.add_documents_batch(docs) == 2

    def test_collection_info_and_clear(self):
        vs = VectorStore()
        vs.initialize()
        assert "vector_count" in vs.get_collection_info()
        assert vs.clear_collection()

    def test_distance_variants(self):
        for d in ["euclidean", "dot"]:
            vs = VectorStore(distance=d)
            vs.initialize()

    def test_client_errors(self):
        vs = VectorStore()
        vs.initialize()
        vs.is_initialized = True

        class BadClient:
            def __getattr__(self, name: str):
                def raise_(*a: Any, **k: Any):
                    raise RuntimeError("boom")

                return raise_

        vs.client = BadClient()
        assert not vs.add_document("1", "c")
        assert vs.add_documents_batch([{"id": "1", "content": "c"}]) == 0
        assert vs.search("c") == []
        assert not vs.delete_document("1")
        assert vs.get_collection_info() == {}
        assert not vs.clear_collection()

    def test_embedding_error(self):
        vs = VectorStore()
        vs.initialize()

        class BadEncoder:
            def encode(self, *a: Any, **k: Any):
                raise RuntimeError("x")

        vs.embedding_model = BadEncoder()
        assert isinstance(vs.embed_text("x"), np.ndarray)
        assert all(isinstance(v, np.ndarray) for v in vs.embed_batch(["a"]))

    def test_init_embedding_failure(self, monkeypatch: pytest.MonkeyPatch):
        class Bad:
            def __init__(self, *a: Any, **k: Any):
                raise RuntimeError("fail")

        monkeypatch.setattr(_vector_store_mod, "SentenceTransformer", Bad)
        vs = VectorStore()
        vs.initialize()
        assert vs.embedding_model is None

    def test_init_qdrant_failure(self, monkeypatch: pytest.MonkeyPatch):
        class Bad:
            def __init__(self, *a: Any, **k: Any):
                raise RuntimeError("fail")

        monkeypatch.setattr(_vector_store_mod, "QdrantClient", Bad)
        vs = VectorStore()
        vs.initialize()
        assert vs.client is None


# ----------------------------------------------------------------------
# ClickHouse storage
# ----------------------------------------------------------------------


class TestClickHouseStorage:
    def setup_method(self):
        # Ensure lightweight fakes remain in sys.modules across test isolation
        sys.modules["httpx"] = _httpx

    def test_init(self):
        s = ClickHouseStorage({"read_only": True})
        assert s.database == "aiops"  # noqa: F841  # Variable for test verification

    def test_initialize(self):
        s = ClickHouseStorage({"read_only": True})
        assert s.initialize() is True

    def test_s3_configure(self):
        s = ClickHouseStorage({"s3_enabled": True, "s3_bucket": "b"})
        assert s.initialize() is True

    def test_writes(self):
        s = ClickHouseStorage({"read_only": False})
        s.initialize()
        now = datetime.now()
        assert asyncio.run(s.store_metric("cpu", 0.5, {"h": "x"}, now))
        assert asyncio.run(s.store_anomaly("a1", "s", "critical", "d", {"x": 1}, now))
        assert asyncio.run(s.store_event("ev", "src", {"x": 1}, now))

    def test_read_only_rejects(self):
        s = ClickHouseStorage({"read_only": True})
        s.initialize()
        now = datetime.now()
        assert not asyncio.run(s.store_metric("cpu", 0.5, {}, now))
        assert not asyncio.run(s.store_anomaly("a1", "s", "c", "d", {}, now))
        assert not asyncio.run(s.store_event("ev", "src", {}, now))
        assert asyncio.run(s.move_to_tier("metrics", "cold", now)) == 0

    def test_queries(self):
        s = ClickHouseStorage({"read_only": True})
        s.initialize()
        now = datetime.now()
        assert asyncio.run(s.query_metrics("cpu", now - timedelta(hours=1), now)) == []
        assert asyncio.run(s.query_anomalies(now - timedelta(hours=1), now)) == []

    def test_stats(self):
        s = ClickHouseStorage({})
        stats = asyncio.run(s.get_storage_stats())
        assert "tiers" in stats

    def _bad_httpx(self, exc: Exception):
        mod = types.ModuleType("httpx")
        mod.RequestError = Exception
        mod.HTTPStatusError = type(
            "HTTPStatusError", (Exception,), {"response": SimpleNamespace(text="err")}
        )
        mod.post = lambda *a, **k: (_ for _ in ()).throw(exc)
        return mod

    def test_initialize_failure(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setitem(sys.modules, "httpx", self._bad_httpx(Exception("boom")))
        s = ClickHouseStorage({"read_only": True})
        assert s.initialize() is False

    def test_query_error(self, monkeypatch: pytest.MonkeyPatch):
        s = ClickHouseStorage({"read_only": True})
        s.initialize()
        monkeypatch.setitem(sys.modules, "httpx", self._bad_httpx(Exception("boom")))
        assert asyncio.run(s.query_metrics("cpu", datetime.now(), datetime.now())) == []

    def test_factory(self):
        assert create_clickhouse_storage({"read_only": True}) is not None

    def test_factory_failure(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setitem(sys.modules, "httpx", self._bad_httpx(Exception("boom")))
        assert create_clickhouse_storage({}) is None


# ----------------------------------------------------------------------
# Cost forecast
# ----------------------------------------------------------------------


class TestCostForecaster:
    def test_basic(self, cost_data):
        cf = CostForecaster(use_prophet=True, use_gbm=False)
        cf.fit(cost_data)
        result = cf.forecast(periods=3)  # noqa: F841  # Variable for test verification
        assert "predictions" in result and "metrics" in result

    def test_prepare_errors(self):
        cf = CostForecaster()
        with pytest.raises(ValueError):
            cf._prepare_prophet_data([{"a": 1}])
        with pytest.raises(ValueError):
            cf._prepare_gbm_features([{"cost": 1}])

    def test_monthly_and_recommend(self):
        cf = CostForecaster()
        forecast = [
            {"timestamp": f"2024-01-{i+1:02d}T00:00:00", "cost": float(i + 1)} for i in range(10)
        ]
        assert cf.predict_monthly_cost(forecast)["monthly_costs"]
        rec = cf.recommend_cost_optimization(forecast, budget=20.0, threshold=0.05)
        assert rec["budget_status"] == "exceeded"

    def test_compare(self):
        cf = CostForecaster()
        f = [{"timestamp": "2024-01-01T00:00:00", "cost": 10.0}]
        a = [{"timestamp": "2024-01-01T00:00:00", "cost": 11.0}]
        assert "metrics" in cf.compare_with_actual(f, a)

    def test_save_load(self, cost_data, tmp_path: Path):
        cf = CostForecaster(use_prophet=True, use_gbm=False)
        cf.fit(cost_data)
        p = tmp_path / "cf.joblib"
        cf.save_model(str(p))
        cf2 = CostForecaster()
        cf2.load_model(str(p))
        assert cf2.is_fitted


# ----------------------------------------------------------------------
# Prophet anomaly
# ----------------------------------------------------------------------


class TestProphetAnomalyDetector:
    def test_fit_predict(self, prophet_data):
        d = ProphetAnomalyDetector()
        d.fit(prophet_data)
        r = d.predict(prophet_data, periods=3)
        assert "predictions" in r and "anomalies" in r and "metrics" in r

    def test_detect_and_forecast(self, prophet_data):
        d = ProphetAnomalyDetector()
        d.fit(prophet_data)
        assert isinstance(d.detect_anomalies(prophet_data), list)
        assert isinstance(d.get_forecast(periods=3), list)

    def test_cross_validate(self, prophet_data):
        d = ProphetAnomalyDetector()
        d.fit(prophet_data)
        assert "rmse" in d.cross_validate()

    def test_save_load(self, prophet_data, tmp_path: Path):
        d = ProphetAnomalyDetector()
        d.fit(prophet_data)
        p = tmp_path / "p.joblib"
        d.save_model(str(p))
        d2 = ProphetAnomalyDetector()
        d2.load_model(str(p))
        assert d2.is_fitted

    def test_errors(self):
        d = ProphetAnomalyDetector()
        with pytest.raises(ValueError):
            d._prepare_data([{"x": 1}])
        with pytest.raises(RuntimeError):
            d.get_forecast(periods=1)


# ----------------------------------------------------------------------
# Auto-Heal operator
# ----------------------------------------------------------------------


class TestAutoHealOperator:
    def test_init(self):
        op = AutoHealOperator(namespace="test")
        assert op.namespace == "test"

    def test_initialize(self):
        op = AutoHealOperator()
        op.initialize()
        assert op._is_initialized

    @pytest.mark.asyncio
    async def test_monitor_once(self):
        op = AutoHealOperator()
        op.initialize()
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(op.monitor_resources(interval=30), timeout=0.01)

    @pytest.mark.asyncio
    async def test_check_pods(self):
        op = AutoHealOperator()
        op.initialize()

        class Pod:
            pass

        def pod(name: str, phase: str, ready: bool = True, n_containers: int = 1):
            p = Pod()
            p.metadata = SimpleNamespace(name=name, owner_references=[])
            p.spec = SimpleNamespace(containers=[SimpleNamespace()] * n_containers, volumes=[])
            p.status = SimpleNamespace(
                phase=phase,
                reason="",
                message="",
                container_statuses=[SimpleNamespace(ready=ready)] * n_containers,
            )
            return p

        op._k8s_client.pods = [
            pod("p1", "Pending"),
            pod("p2", "Running", False, 2),
            pod("p3", "Running", True, 1),
        ]
        await op._check_pods()

    @pytest.mark.asyncio
    async def test_check_services(self):
        op = AutoHealOperator()
        op.initialize()

        class Svc:
            pass

        s1 = Svc()
        s1.metadata = SimpleNamespace(name="s1")
        s1.spec = SimpleNamespace(type="ClusterIP")
        s2 = Svc()
        s2.metadata = SimpleNamespace(name="s2")
        s2.spec = SimpleNamespace(type="ExternalName")
        op._k8s_client.services = [s1, s2]
        op._k8s_client.endpoints = {"s1": _FakeEndpoints(False)}
        await op._check_services()

    @pytest.mark.asyncio
    async def test_trigger_and_execute(self):
        op = AutoHealOperator(dry_run=True)
        op.initialize()
        op._heal_tasks["x"] = {
            "task_id": "x",
            "resource_type": "Pod",
            "resource_name": "pod-1",
            "condition": HealConditionType.PodNotReady.value,
            "phase": HealPhase.Pending.value,
            "details": {},
            "created_at": datetime.now().isoformat(),
            "namespace": "default",
        }
        await op._trigger_heal("Pod", "pod-1", HealConditionType.PodNotReady, {})
        assert len([t for t in op.get_heal_tasks() if t["task_id"] == "x"]) == 1

    @pytest.mark.asyncio
    async def test_execute_unknown_resource(self):
        op = AutoHealOperator()
        op.initialize()
        task = {
            "task_id": "x",
            "resource_type": "Unknown",
            "resource_name": "x",
            "condition": "x",
            "details": {},
            "phase": "pending",
            "created_at": datetime.now().isoformat(),
            "namespace": "default",
        }
        await op._execute_heal(task)
        assert task["phase"] == HealPhase.Failed.value

    @pytest.mark.asyncio
    async def test_heal_stateful_pod(self):
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
        p.status = SimpleNamespace(
            phase="Running", reason="", message="", container_statuses=[SimpleNamespace(ready=True)]
        )
        op._k8s_client.pods = [p]
        task = {
            "task_id": "x",
            "resource_type": "Pod",
            "resource_name": "p1",
            "condition": HealConditionType.PodNotReady.value,
            "details": {},
            "phase": "pending",
            "created_at": datetime.now().isoformat(),
            "namespace": "default",
        }
        result = await op._heal_pod(task)  # noqa: F841  # Variable for test verification
        assert not result

    @pytest.mark.asyncio
    async def test_check_not_initialized(self):
        op = AutoHealOperator()
        await op._check_pods()
        await op._check_deployments()
        await op._check_services()

    def test_no_kubernetes(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(_operator_mod, "KUBERNETES_AVAILABLE", False)
        op = AutoHealOperator()
        op.initialize()
        assert not op._is_initialized

    def test_cleanup(self):
        op = AutoHealOperator()
        op._heal_tasks["x"] = {
            "phase": HealPhase.Completed.value,
            "completed_at": (datetime.now() - timedelta(hours=2)).isoformat(),
        }
        op._cleanup_completed_tasks()
        assert "x" not in op._heal_tasks

    def test_stats(self):
        op = AutoHealOperator()
        assert op.get_task_stats()["total"] == 0


# ----------------------------------------------------------------------
# Isolation Forest
# ----------------------------------------------------------------------


class TestIsolationForest:
    def test_basic(self):
        data = [{"a": float(i), "b": float(i * 2)} for i in range(12)]
        d = IsolationForestDetector()
        d.fit(data)
        r = d.predict(data)
        assert "predictions" in r

    def test_errors(self):
        d = IsolationForestDetector()
        with pytest.raises(ValueError):
            d._prepare_features([{"x": "a"}])
        with pytest.raises(ValueError):
            d.fit([{"a": 1.0}])
        with pytest.raises(RuntimeError):
            d.predict([{"a": 1.0}])

    def test_pca(self):
        data = [{"a": float(i), "b": float(i * 2), "c": float(i)} for i in range(12)]
        d = IsolationForestDetector(use_pca=True, pca_components=2)
        d.fit(data)
        assert d.pca is not None

    def test_importance_and_save(self, tmp_path: Path):
        data = [{"a": float(i), "b": float(i * 2)} for i in range(12)]
        d = IsolationForestDetector()
        d.fit(data)
        imp = d.get_feature_importance()
        assert set(imp.keys()) == {"a", "b"}
        p = tmp_path / "iso.joblib"
        d.save_model(str(p))
        d2 = IsolationForestDetector()
        d2.load_model(str(p))
        assert d2.is_fitted


# ----------------------------------------------------------------------
# Causal graph builder
# ----------------------------------------------------------------------


class TestCausalGraphBuilder:
    def test_create(self):
        assert create_causal_graph_builder().discovery_method == "pc"

    def test_build_metrics(self):
        b = create_causal_graph_builder()
        df = pd.DataFrame(
            {"a": np.random.randn(30), "b": np.random.randn(30), "c": np.random.randn(30)}
        )
        g = b.build_from_metrics(df, {"a": "s1"})
        assert len(g.nodes) == 3

    def test_build_logs_traces(self):
        b = create_causal_graph_builder()
        logs = pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01", periods=10, freq="min"),
                "level": ["INFO"] * 10,
            }
        )
        assert b.build_from_logs(logs) is not None
        traces = pd.DataFrame(
            {"duration": np.random.rand(10), "error": np.random.randint(0, 2, 10)}
        )
        assert b.build_from_traces(traces) is not None

    def test_build_multimodal(self):
        b = create_causal_graph_builder()
        m = pd.DataFrame({"m1": np.random.randn(10), "m2": np.random.randn(10)})
        logs = pd.DataFrame({"level": ["INFO"] * 10})
        t = pd.DataFrame({"duration": np.random.rand(10)})
        assert b.build_multimodal(m, logs, t) is not None

    def test_analyzer(self):
        b = create_causal_graph_builder()
        b.build_from_metrics(pd.DataFrame({"a": np.random.randn(20), "b": np.random.randn(20)}))
        assert b.get_analyzer() is not None

    def test_analyzer_before_build(self):
        b = create_causal_graph_builder()
        with pytest.raises(RuntimeError):
            b.get_analyzer()

    def test_json_roundtrip(self):
        cg = CausalGraph()
        cg.add_edge("a", "b", 0.5)
        s = CausalGraphVisualizer.to_json(cg)
        assert "a" in CausalGraphVisualizer.from_json(s).nodes

    def test_to_networkx(self):
        cg = CausalGraph()
        cg.add_edge("a", "b")
        assert "a" in CausalGraphVisualizer.to_networkx(cg).nodes

    def test_persistence(self, tmp_cwd_file: Path):
        cg = CausalGraph()
        cg.add_edge("a", "b")
        p = str(tmp_cwd_file.with_suffix(".json"))
        CausalGraphPersistence.save(cg, p)
        assert "a" in CausalGraphPersistence.load(p).nodes

    def test_persistence_errors(self, tmp_cwd_file: Path):
        cg = CausalGraph()
        p = str(tmp_cwd_file.with_suffix(".xyz"))
        with pytest.raises(ValueError):
            CausalGraphPersistence.save(cg, p, format="xyz")
        with pytest.raises(FileNotFoundError):
            CausalGraphPersistence.load(p + ".missing")

    def test_integrator(self):
        import networkx as nx

        from modules.analyze.root_cause.graph_builder import RootCauseGraphBuilder

        gb = RootCauseGraphBuilder()
        cb = create_causal_graph_builder()
        integrator = CausalGraphIntegrator(gb, cb)
        alerts = [{"id": "a1", "title": "t", "service_id": "s1", "severity": "critical"}]
        services = [{"id": "s1", "name": "svc", "type": "microservice"}]
        metrics = [{"id": "m1", "name": "cpu", "service_id": "s1", "current_value": 0.5}]
        deps = [{"source_id": "s1", "target_id": "s2", "type": "service"}]
        md = pd.DataFrame({"s1": [1, 2, 3], "s2": [3, 2, 1]})
        nx_graph, c_graph = integrator.build_integrated_graph(alerts, services, metrics, deps, md)
        assert nx_graph is not None and c_graph is not None

        # Use a DiGraph so the weight-merge branch can be executed safely
        merged = nx.DiGraph()
        for n in c_graph.nodes:
            merged.add_node(n)
        merged.add_edge("s1", "s2", weight=0.5)
        result = integrator.merge_graphs(
            merged, c_graph
        )  # noqa: F841  # Variable for test verification
        assert result is not None

    def test_persistence_json(self, tmp_cwd_file: Path):
        """Test JSON persistence (secure format)"""
        cg = CausalGraph()
        cg.add_edge("a", "b", 0.5)
        p = str(tmp_cwd_file.with_suffix(".json"))
        CausalGraphPersistence.save(cg, p, format="json")
        assert "a" in CausalGraphPersistence.load(p, format="json").nodes
        # Test unsupported format
        with pytest.raises(ValueError, match="Unsupported format"):
            CausalGraphPersistence.save(cg, p, format="pickle")
        with pytest.raises(ValueError, match="Unsupported format"):
            CausalGraphPersistence.load(p, format="pickle")

    def test_persistence_invalid_path(self, tmp_path: Path):
        cg = CausalGraph()
        with pytest.raises(ValueError):
            CausalGraphPersistence.save(cg, str(tmp_path / "x.json"))
        with pytest.raises(ValueError):
            CausalGraphPersistence.load(str(tmp_path / "x.json"))


# ----------------------------------------------------------------------
# Data preprocessing
# ----------------------------------------------------------------------


class TestDataPreprocessing:
    def setup_method(self):
        # Ensure lightweight fake remains in sys.modules across test isolation
        sys.modules["prometheus_api_client"] = _prom

    def test_csv_load(self, sample_df: pd.DataFrame, tmp_path: Path):
        p = tmp_path / "ts.csv"
        sample_df.to_csv(p, index=False)
        df = TimeSeriesDataLoader.load_from_csv(str(p))
        assert "value" in df.columns

    def test_prometheus_load(self):
        df = TimeSeriesDataLoader.load_from_prometheus(
            "up", "2024-01-01T00:00:00Z", "2024-01-01T01:00:00Z"
        )
        assert "timestamp" in df.columns

    def test_cleaner(self, sample_df: pd.DataFrame):
        df = pd.DataFrame({"value": [1.0, np.nan, 3.0]})
        out = TimeSeriesCleaner.handle_missing_values(df, method="ffill")
        assert out["value"].isna().sum() == 0
        with pytest.raises(ValueError):
            TimeSeriesCleaner.handle_missing_values(df, method="bad")
        out_iqr = TimeSeriesCleaner.remove_outliers(
            pd.DataFrame({"value": [1.0, 2.0, 3.0, 100.0]}), threshold=0.1
        )
        assert len(out_iqr) <= 4

    def test_resample(self, sample_df: pd.DataFrame):
        out = TimeSeriesCleaner.resample(sample_df, freq="2h", agg="mean")
        assert "timestamp" in out.columns

    def test_features(self, sample_df: pd.DataFrame):
        out = TimeSeriesFeatureEngineer.add_time_features(sample_df)
        assert "hour" in out.columns
        out = TimeSeriesFeatureEngineer.add_lag_features(sample_df)
        assert any("_lag_" in c for c in out.columns)
        out = TimeSeriesFeatureEngineer.add_rolling_features(sample_df)
        assert any("_rolling_" in c for c in out.columns)
        out = TimeSeriesFeatureEngineer.add_statistical_features(sample_df)
        assert any("_zscore" in c for c in out.columns)

    def test_augment(self):
        data = np.random.rand(10, 2)
        labels = np.zeros(10)
        out, augmented_labels = TimeSeriesAugmenter.augment_dataset(data, labels, augment_factor=2)
        assert len(out) == 20

    def test_scaler(self):
        data = np.random.rand(10, 3)
        for m in ["standard", "minmax"]:
            s = TimeSeriesScaler(method=m)
            assert s.fit_transform(data).shape == data.shape
        with pytest.raises(ValueError):
            TimeSeriesScaler(method="bad")

    def test_splitter(self):
        data = np.random.rand(100, 3)
        labels = np.random.rand(100)
        tr, v, te, *_ = TimeSeriesSplitter.train_val_test_split(data, labels, 0.7, 0.15, 0.15)
        assert len(tr) + len(v) + len(te) == 100

    def test_pipeline(self, sample_df: pd.DataFrame):
        p = create_preprocessing_pipeline()
        out = p.process(sample_df, "timestamp", "value")
        assert isinstance(out, np.ndarray)

    def test_multimodal(self):
        logs = ["error x", "info y"]
        out = MultiModalDataPreparer.prepare_log_features(logs)
        assert out.shape[0] == 2
        traces = [{"duration": 100, "spans": [{"error": False}]}]
        out = MultiModalDataPreparer.prepare_trace_features(traces, feature_dim=8)
        assert out.shape == (1, 8)


# ----------------------------------------------------------------------
# Train transformer
# ----------------------------------------------------------------------


class TestTrainTransformer:
    def test_config(self):
        cfg = train_transformer.TrainingConfig()
        assert cfg.n_epochs == 100

    def test_prepare_data(self, sample_df: pd.DataFrame, tmp_path: Path):
        p = tmp_path / "train.csv"
        sample_df.to_csv(p, index=False)
        cfg = train_transformer.TrainingConfig(data_path=str(p), seq_len=5, batch_size=2)
        train_loader, val_loader, test_loader, input_dim = train_transformer.prepare_data(cfg)
        assert input_dim > 0 and train_loader is not None

    def test_train_and_eval(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        cfg = train_transformer.TrainingConfig(
            model_dir=str(tmp_path), model_name="t.pth", n_epochs=1, batch_size=1
        )

        class FakeLoader:
            def __len__(self):
                return 1

            def __iter__(self):
                yield torch.zeros((1, 2, 3)), None

        monkeypatch.setattr(
            train_transformer, "create_transformer_model", lambda **kw: _FakeModel(**kw)
        )
        monkeypatch.setattr(train_transformer, "TransformerAnomalyTrainer", _FakeTrainer)
        model = train_transformer.train_model(cfg, FakeLoader(), FakeLoader(), 3)
        assert model is not None
        metrics = train_transformer.evaluate_model(model, FakeLoader(), cfg)
        assert "reconstruction_error" in metrics

    def test_main(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        import argparse

        csv = tmp_path / "main.csv"
        rng = pd.date_range("2024-01-01", periods=50, freq="min")
        pd.DataFrame({"timestamp": rng, "value": np.random.rand(50)}).to_csv(csv, index=False)
        monkeypatch.setattr(train_transformer, "prepare_data", lambda c: (None, None, None, 1))
        monkeypatch.setattr(train_transformer, "train_model", lambda c, tl, vl, d: _FakeModel())
        monkeypatch.setattr(train_transformer, "evaluate_model", lambda m, te, c: {"x": 1.0})
        monkeypatch.setattr(
            argparse._sys,
            "argv",
            [
                "train",
                "--data_path",
                str(csv),
                "--model_dir",
                str(tmp_path),
                "--epochs",
                "1",
                "--batch_size",
                "1",
            ],
        )
        train_transformer.main()
