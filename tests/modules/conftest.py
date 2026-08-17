# -*- coding: utf-8 -*-
"""Shared lightweight fakes for optional dependencies used by tests/modules."""

from __future__ import annotations

import importlib
import sys
import types
from datetime import datetime
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import torch

# ----------------------------------------------------------------------
# sentence_transformers
# ----------------------------------------------------------------------
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


# ----------------------------------------------------------------------
# qdrant_client
# ----------------------------------------------------------------------
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


# ----------------------------------------------------------------------
# prophet
# ----------------------------------------------------------------------
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
        start = self._df["ds"].max() if self._df is not None else pd.Timestamp("2024-01-01")
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


def _fake_cross_validation(model: Any, initial: str, period: str, horizon: str):
    return pd.DataFrame(
        {
            "ds": pd.date_range("2024-01-01", periods=5, freq="D"),
            "y": [1.0] * 5,
            "yhat": [1.0] * 5,
        }
    )


def _fake_performance_metrics(df: pd.DataFrame):
    return pd.DataFrame(
        {"mse": [1.0], "rmse": [1.0], "mae": [1.0], "mape": [1.0], "coverage": [1.0]}
    )


_prophet.Prophet = _FakeProphet
_prophet_diag.cross_validation = _fake_cross_validation
_prophet_diag.performance_metrics = _fake_performance_metrics
_prophet.diagnostics = _prophet_diag
sys.modules["prophet"] = _prophet
sys.modules["prophet.diagnostics"] = _prophet_diag


# ----------------------------------------------------------------------
# prometheus_api_client
# ----------------------------------------------------------------------
_prom = types.ModuleType("prometheus_api_client")


class _FakePromConnect:
    def __init__(self, *a: Any, **k: Any):
        pass

    def custom_query_range(self, **kw: Any):
        return [{"values": [[1704067200, "1.0"], [1704067260, "2.0"]]}]


_prom.PrometheusConnect = _FakePromConnect
sys.modules["prometheus_api_client"] = _prom


# ----------------------------------------------------------------------
# kubernetes
# ----------------------------------------------------------------------
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

# Ensure the auto-heal operator binds to the fake kubernetes client above.
import modules.execute.auto_heal.operator as _operator_module  # noqa: E402

importlib.reload(_operator_module)
