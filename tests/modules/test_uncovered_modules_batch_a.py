# -*- coding: utf-8 -*-
"""Batch A tests for uncovered modules."""

import asyncio  # noqa: F401  # Imported for test setup
import json  # noqa: F401  # Imported for test setup
import re
import sys  # noqa: F401  # Imported for test setup
import types
import uuid
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional  # noqa: F401  # Imported for test setup

import numpy as np
import pandas as pd
import pytest  # noqa: F401  # Imported for test setup
import torch
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient


def _install_dgl_fakes() -> None:
    if "dgl" in sys.modules:
        return

    class FakeHeteroGraph:
        def __init__(self, data: Any = None):
            self._nodes: Dict[str, int] = {}
            self._edges: Dict[str, Any] = {}

        def add_nodes(self, ntype: str, num_nodes: int = 1) -> None:
            self._nodes[ntype] = self._nodes.get(ntype, 0) + num_nodes

        def num_nodes(self, ntype: str) -> int:
            return self._nodes.get(ntype, 0)

        def add_edges(self, etype: str, src: Any, dst: Any) -> None:
            self._edges.setdefault(etype, []).append((src, dst))

        def num_edges(self, etype: str) -> int:
            return len(self._edges.get(etype, []))

    dgl_mod = types.ModuleType("dgl")
    dgl_mod.heterograph = lambda data=None: FakeHeteroGraph(data)
    dgl_mod.DGLHeteroGraph = FakeHeteroGraph
    sys.modules["dgl"] = dgl_mod

    dglnn_mod = types.ModuleType("dgl.nn")

    class FakeGraphConv:
        def __init__(self, in_feats: Any, out_feats: int):
            self.in_feats = in_feats
            self.out_feats = out_feats

    class FakeHeteroGraphConv:
        def __init__(self, mods: Any, aggregate: str = "mean"):
            self.mods = mods
            self.aggregate = aggregate

        def __call__(self, g: Any, features: Dict[str, torch.Tensor]) -> Dict[str, torch.Tensor]:
            return features

    dglnn_mod.GraphConv = FakeGraphConv
    dglnn_mod.HeteroGraphConv = FakeHeteroGraphConv
    sys.modules["dgl.nn"] = dglnn_mod


def _install_temporalio_fakes() -> None:
    if "temporalio" in sys.modules:
        return

    pkg = types.ModuleType("temporalio")
    pkg.__path__ = []
    sys.modules["temporalio"] = pkg

    for sub in ["activity", "worker", "workflow", "client", "common"]:
        mod = types.ModuleType(f"temporalio.{sub}")
        sys.modules[f"temporalio.{sub}"] = mod
        setattr(pkg, sub, mod)

    def _defn(func: Any = None, *, name: Optional[str] = None) -> Any:
        if func is None:
            return lambda f: f
        return func

    pkg.activity.defn = _defn
    pkg.workflow.defn = _defn
    pkg.workflow.run = lambda func: func
    pkg.workflow.execute_activity = lambda *a, **k: asyncio.sleep(0)
    pkg.common.RetryPolicy = lambda **kwargs: SimpleNamespace(**kwargs)

    class FakeClient:
        @staticmethod
        async def connect(*args: Any, **kwargs: Any) -> "FakeClient":
            return FakeClient()

        async def execute_workflow(self, *args: Any, **kwargs: Any) -> Any:
            return {"status": "completed", "workflow_result": True}

        async def close(self) -> None:
            pass

    pkg.client.Client = FakeClient

    class FakeWorker:
        def __init__(self, *args: Any, **kwargs: Any):
            self._shutdown = False

        async def run(self) -> None:
            self._shutdown = False

        def shutdown(self) -> None:
            self._shutdown = True

    pkg.worker.Worker = FakeWorker


def _install_missing_submodules() -> None:
    if "modules.analyze.capacity.cost" not in sys.modules:
        cost_mod = types.ModuleType("modules.analyze.capacity.cost")
        cost_mod.CostForecaster = type("CostForecaster", (), {})
        sys.modules["modules.analyze.capacity.cost"] = cost_mod
    if "modules.analyze.anomaly.transformer_model" not in sys.modules:
        trans_mod = types.ModuleType("modules.analyze.anomaly.transformer_model")
        trans_mod.TransformerAnomalyDetector = type("TransformerAnomalyDetector", (), {})
        trans_mod.TransformerAnomalyDetectorWrapper = type(
            "TransformerAnomalyDetectorWrapper", (), {}
        )
        trans_mod.create_transformer_model = lambda *a, **k: None
        sys.modules["modules.analyze.anomaly.transformer_model"] = trans_mod


_install_dgl_fakes()
_install_temporalio_fakes()
_install_missing_submodules()

from modules.analyze.anomaly.ensemble import EnsembleAnomalyDetector
from modules.analyze.capacity import forecast as forecast_mod
from modules.analyze.capacity.forecast import CapacityForecaster
from modules.analyze.root_cause import causal_service
from modules.analyze.root_cause.causal_graph_builder import (
    CausalGraphBuilder,
    CausalGraphPersistence,
    CausalGraphVisualizer,
    create_causal_graph_builder,
)
from modules.analyze.root_cause.causal_inference import (
    CausalDiscovery,
    CausalGraph,
    CausalRootCauseAnalyzer,
    CounterfactualReasoning,
    DoCalculus,
    create_causal_analyzer,
)
from modules.analyze.root_cause.gnn import GNNTrainer, HeterogeneousGNNModel
from modules.analyze.root_cause.graph_builder import RootCauseGraphBuilder
from modules.analyze.root_cause.inference import RootCauseInference
from modules.analyze.runbook.generator import RunbookGenerator
from modules.execute.scheduler import temporal_worker
from modules.storage.postgres import storage as postgres_storage

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_postgres(monkeypatch):
    tables: Dict[str, List[Dict[str, Any]]] = {}

    def _now():
        return datetime.utcnow()

    class FakeCursor:
        def __init__(self, conn: "FakeConnection", cursor_factory=None):
            self.conn = conn
            self.cursor_factory = cursor_factory

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def execute(self, query: str, params: Any = None) -> None:
            self.conn._exec(query, params or ())

        def fetchone(self) -> Optional[Dict[str, Any]]:
            results = self.conn._last_results
            return results[0] if results else None

        def fetchall(self) -> List[Dict[str, Any]]:
            return self.conn._last_results

    class FakeConnection:
        def __init__(self, pool: "FakePool"):
            self.pool = pool
            self._last_results: List[Dict[str, Any]] = []

        def cursor(self, cursor_factory=None):
            return FakeCursor(self, cursor_factory)

        def commit(self) -> None:
            pass

        def rollback(self) -> None:
            pass

        def _exec(self, query: str, params: tuple) -> None:
            q = query.strip()
            self._last_results = []

            if "bad_table" in q:
                raise RuntimeError("simulated query failure")

            if q.upper().startswith("CREATE TABLE"):
                m = re.search(r"CREATE TABLE IF NOT EXISTS\s+(\w+)", q, re.IGNORECASE)
                if m:
                    tables.setdefault(m.group(1), [])
                return

            if q.upper().startswith("CREATE INDEX"):
                return

            if q.upper().startswith("INSERT INTO"):
                m = re.search(r"INSERT INTO\s+(\w+)", q, re.IGNORECASE)
                table = m.group(1) if m else "unknown"
                tables.setdefault(table, [])

                cols_match = re.search(r"\(([^)]+)\)", q)
                if not cols_match:
                    return
                cols = [c.strip() for c in cols_match.group(1).split(",")]

                values_match = re.search(r"VALUES\s+\(([^)]+)\)", q, re.IGNORECASE)
                if not values_match:
                    return
                tokens = [t.strip() for t in values_match.group(1).split(",")]

                row: Dict[str, Any] = {}
                param_idx = 0
                for col, tok in zip(cols, tokens):
                    if "%s" in tok:
                        row[col] = params[param_idx]
                        param_idx += 1
                    elif "CURRENT_TIMESTAMP" in tok or "DEFAULT" in tok:
                        row[col] = _now()
                    elif tok == "TRUE":
                        row[col] = True
                    elif tok == "FALSE":
                        row[col] = False
                    else:
                        row[col] = tok

                conflict_match = re.search(
                    r"ON CONFLICT\s*\((\w+)\)\s*DO UPDATE SET\s+(.+?)(?:;|$)",
                    q,
                    re.IGNORECASE,
                )
                if conflict_match:
                    conflict_col = conflict_match.group(1)
                    existing = None
                    for r in tables[table]:
                        if r.get(conflict_col) == row.get(conflict_col):
                            existing = r
                            break
                    if existing:
                        assign = conflict_match.group(2)
                        for part in assign.split(","):
                            col_name, expr = part.split("=", 1)
                            col_name = col_name.strip()
                            expr = expr.strip()
                            if "%s" in expr:
                                existing[col_name] = params[param_idx]
                                param_idx += 1
                            elif "CURRENT_TIMESTAMP" in expr:
                                existing[col_name] = _now()
                        return

                tables[table].append(row)

                defaults = {"created_at": _now(), "updated_at": _now()}
                if table == "audit_log":
                    defaults["timestamp"] = _now()
                    defaults["id"] = len(tables[table])
                for col_default, val_default in defaults.items():
                    if col_default not in row:
                        row[col_default] = val_default

                return

            if q.upper().startswith("DELETE FROM"):
                m = re.search(r"DELETE FROM\s+(\w+)\s+WHERE\s+(\w+)\s*=\s*%s", q, re.IGNORECASE)
                if m:
                    table, col = m.group(1), m.group(2)
                    val = params[0] if params else None
                    tables[table] = [r for r in tables.get(table, []) if r.get(col) != val]
                return

            if q.upper().startswith("SELECT"):
                from_match = re.search(r"FROM\s+(\w+)", q, re.IGNORECASE)
                table = from_match.group(1) if from_match else "unknown"
                rows = list(tables.get(table, []))

                where_match = re.search(r"WHERE\s+(.+?)(?:ORDER BY|LIMIT|$)", q, re.IGNORECASE)
                param_idx = 0
                if where_match:
                    where = where_match.group(1)
                    for cond in re.split(r"\s+AND\s+", where, flags=re.IGNORECASE):
                        cond = cond.strip()
                        if cond == "1=1":
                            continue
                        m_eq = re.match(r"(\w+)\s*=\s*%s", cond)
                        if m_eq:
                            col = m_eq.group(1)
                            val = params[param_idx]
                            param_idx += 1
                            rows = [r for r in rows if r.get(col) == val]
                            continue
                        if re.match(r"(\w+)\s*=\s*TRUE", cond):
                            col = re.match(r"(\w+)\s*=\s*TRUE", cond).group(1)
                            rows = [r for r in rows if r.get(col) is True]
                            continue
                        if re.match(r"(\w+)\s*=\s*FALSE", cond):
                            col = re.match(r"(\w+)\s*=\s*FALSE", cond).group(1)
                            rows = [r for r in rows if r.get(col) is False]
                            continue

                if "ORDER BY" in q and "timestamp" in q.lower() and "DESC" in q.upper():
                    rows = sorted(rows, key=lambda r: r.get("timestamp", _now()), reverse=True)

                limit_match = re.search(r"LIMIT\s+(\d+|%s)", q, re.IGNORECASE)
                if limit_match:
                    if limit_match.group(1) == "%s":
                        limit = int(params[param_idx])
                        param_idx += 1
                    else:
                        limit = int(limit_match.group(1))
                    rows = rows[:limit]

                select_match = re.search(r"SELECT\s+(.+?)\s+FROM", q, re.IGNORECASE)
                if select_match:
                    select_cols = [c.strip() for c in select_match.group(1).split(",")]
                    if select_cols[0] == "*":
                        self._last_results = rows
                    else:
                        self._last_results = [
                            {c: r.get(c) for c in select_cols if c in r} for r in rows
                        ]
                else:
                    self._last_results = rows
                return

            if "bad_table" in q:
                raise RuntimeError("simulated query failure")

            # Custom query fallback
            self._last_results = []

    class FakePool:
        def __init__(self, *args, **kwargs):
            self.tables = tables
            self.closed = False

        def getconn(self):
            return FakeConnection(self)

        def putconn(self, conn):
            pass

        def closeall(self):
            self.closed = True

    monkeypatch.setattr(
        postgres_storage,
        "pool",
        SimpleNamespace(SimpleConnectionPool=FakePool),
    )
    monkeypatch.setattr(postgres_storage, "RealDictCursor", object)
    monkeypatch.setattr(postgres_storage, "Json", lambda value: value)

    def _raise(*args, **kwargs):
        raise RuntimeError("simulated query failure")

    return {
        "pool": FakePool,
        "raise_cursor": _raise,
        "tables": tables,
    }


@pytest.fixture
def prophet_forecast(monkeypatch):
    class FakeProphet:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def fit(self, df: pd.DataFrame):
            return self

        def make_future_dataframe(self, periods: int, freq: str = "H") -> pd.DataFrame:
            start = pd.Timestamp("2024-01-01")
            return pd.DataFrame(
                {"ds": pd.date_range(start, periods=periods + 1, freq=freq)[-periods:]}
            )

        def predict(self, future: pd.DataFrame) -> pd.DataFrame:
            n = len(future)
            yhat = np.arange(1, n + 1, dtype=float)
            return pd.DataFrame(
                {
                    "ds": future["ds"].values,
                    "yhat": yhat,
                    "yhat_lower": yhat - 1,
                    "yhat_upper": yhat + 1,
                    "trend": yhat,
                }
            )

    monkeypatch.setattr(forecast_mod, "PROPHET_AVAILABLE", True)
    monkeypatch.setattr(forecast_mod, "Prophet", FakeProphet)


class DummyProphetDetector:
    def __init__(self, **kwargs):
        pass

    def fit(self, data, timestamp_col="timestamp", value_col="value"):
        pass

    def predict(self, data, timestamp_col="timestamp", value_col="value", periods=0):
        ts = data[0]["timestamp"] if data else "2024-01-01T00:00:00"
        return {
            "anomalies": [
                {
                    "timestamp": ts,
                    "severity": 0.8,
                    "predicted_value": 100.0,
                }
            ]
        }


@pytest.fixture
def dummy_prophet_detector(monkeypatch):
    monkeypatch.setattr(
        "modules.analyze.anomaly.ensemble.ProphetAnomalyDetector",
        DummyProphetDetector,
    )


class FakeVectorStore:
    def __init__(self):
        self.is_initialized = False
        self.docs: List[Dict[str, Any]] = []

    def initialize(self):
        self.is_initialized = True

    def search(self, query: str, top_k: int = 5, score_threshold: float = 0.5, **kwargs):
        return [
            {
                "id": str(i),
                "score": 0.9 - i * 0.1,
                "payload": doc.get("metadata", {"content": doc.get("content", "")}),
            }
            for i, doc in enumerate(self.docs[:top_k])
            if 0.9 - i * 0.1 >= score_threshold
        ]

    def add_documents_batch(self, documents: List[Dict[str, Any]]) -> int:
        self.docs.extend(documents)
        return len(documents)


# ---------------------------------------------------------------------------
# Capacity forecast
# ---------------------------------------------------------------------------


def _forecast_data(n: int = 12) -> List[Dict[str, Any]]:
    base = pd.Timestamp("2024-01-01")  # noqa: F841  # Variable for test verification
    return [
        {
            "timestamp": (base + pd.Timedelta(hours=i)).isoformat(),
            "value": float(i + 10),
            "feature": float(i),
        }
        for i in range(n)
    ]


def test_capacity_forecaster_gbm_only(tmp_path):
    data = _forecast_data()
    cf = CapacityForecaster(use_prophet=False, use_gbm=True, gbm_params={"n_estimators": 5})
    cf.fit(data, feature_cols=["feature"])
    result = cf.forecast()  # noqa: F841  # Variable for test verification
    assert result["predictions"] == []
    assert "metrics" in result
    values = [20.0, 21.0]
    util = cf.predict_capacity_utilization(30.0, values)
    assert "utilization" in util
    scaling = cf.recommend_scaling(30.0, values)
    assert scaling["action"] in ("scale_up", "no_action")

    path = tmp_path / "cf.joblib"
    cf.save_model(str(path))
    cf2 = CapacityForecaster()
    cf2.load_model(str(path))
    assert cf2.is_fitted


def test_capacity_forecaster_with_prophet(prophet_forecast):
    data = _forecast_data(15)
    cf = CapacityForecaster(use_prophet=True, use_gbm=False)
    cf.fit(data)
    result = cf.forecast(periods=5, freq="h", return_confidence=False)  # noqa: F841  # Variable for test verification
    assert len(result["predictions"]) == 5
    values = [p["value"] for p in result["predictions"]]
    util = cf.predict_capacity_utilization(10.0, values, threshold=0.5)
    assert util["max_utilization"] >= 0
    scaling = cf.recommend_scaling(10.0, values)
    assert "action" in scaling


def test_capacity_forecaster_errors():
    cf = CapacityForecaster(use_prophet=False, use_gbm=False)
    with pytest.raises(RuntimeError):
        cf.forecast()
    with pytest.raises(ValueError):
        cf._prepare_prophet_data([{"timestamp": "x"}], value_col="missing")
    with pytest.raises(ValueError):
        cf._prepare_gbm_features([{"value": 1.0}])


def test_capacity_utilization_edge_cases():
    cf = CapacityForecaster()
    assert cf.predict_capacity_utilization(0.0, [10.0])["utilization"] == [0.0]
    assert cf.recommend_scaling(100.0, [])["action"] == "no_action"


# ---------------------------------------------------------------------------
# Causal inference
# ---------------------------------------------------------------------------


def _causal_data(n: int = 50, seed: int = 1) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    x = rng.normal(size=n)
    y = 0.5 * x + rng.normal(size=n) * 0.1
    z = 0.3 * y + rng.normal(size=n) * 0.1
    return pd.DataFrame({"service_A": x, "service_B": y, "service_C": z})


def test_causal_graph():
    g = CausalGraph()
    g.add_edge("A", "B", weight=0.5)
    g.add_edge("B", "C", weight=0.3)
    g.add_edge("A", "C", weight=0.2)
    assert g.is_dag()
    assert g.get_parents("C") == {"A", "B"}
    assert g.get_children("A") == {"B", "C"}
    assert g.get_ancestors("C") == {"A", "B"}
    assert g.get_descendants("A") == {"B", "C"}
    adj = g.to_adjacency_matrix()
    assert adj.shape == (3, 3)

    # cycle detection
    g2 = CausalGraph()
    g2.add_edge("A", "B")
    g2.add_edge("B", "C")
    g2.add_edge("C", "A")
    assert not g2.is_dag()


def test_causal_discovery_pc():
    data = _causal_data()
    graph = CausalDiscovery.pc_algorithm(data)
    assert set(graph.nodes) == set(data.columns)


def test_causal_discovery_ges():
    data = _causal_data()
    graph = CausalDiscovery.ges_algorithm(data)
    assert set(graph.nodes) == set(data.columns)


def test_do_calculus_and_counterfactual():
    g = CausalGraph()
    g.add_edge("X", "Y", weight=0.7)
    g.add_edge("Y", "Z", weight=0.4)
    rng = np.random.default_rng(2)
    data = pd.DataFrame(
        {
            "X": rng.normal(size=30),
            "Y": rng.normal(size=30),
            "Z": rng.normal(size=30),
        }
    )
    calc = DoCalculus(g)
    intervened = calc.do_intervention("X", 1.0, data)
    assert "Y" in intervened.columns
    effect = calc.estimate_causal_effect("X", "Z", data, treatment_values=[0.0, 1.0])
    assert "ate" in effect
    cf = CounterfactualReasoning(g)
    result = cf.what_if({"Z": data["Z"].mean()}, {"X": 1.0}, "Z", data)  # noqa: F841  # Variable for test verification
    assert "effect" in result
    causes = cf.compute_necessary_causes("Z", data["Z"].mean(), data)
    assert isinstance(causes, list)


def test_causal_root_cause_analyzer():
    data = _causal_data()
    analyzer = create_causal_analyzer(discovery_method="pc", use_counterfactual=True)
    graph = analyzer.learn_causal_graph(data)
    assert graph is not None
    causes = analyzer.identify_root_cause("service_C", data, top_k=3)
    assert isinstance(causes, list)
    explanation = analyzer.explain_root_cause(
        {"node": "service_A", "method": "necessary_cause"},
        "service_C",
        data,
    )
    assert "root_cause" in explanation


def test_causal_analyzer_ges():
    data = _causal_data()
    analyzer = create_causal_analyzer(discovery_method="ges", use_counterfactual=True)
    graph = analyzer.learn_causal_graph(data)
    assert graph is not None


# ---------------------------------------------------------------------------
# Causal graph builder / visualizer
# ---------------------------------------------------------------------------


def test_causal_graph_builder():
    data = _causal_data()
    builder = create_causal_graph_builder(discovery_method="pc")
    graph = builder.build_from_metrics(data)
    assert graph is not None
    analyzer = builder.get_analyzer()
    assert isinstance(analyzer, CausalRootCauseAnalyzer)


def test_causal_graph_visualizer_and_persistence(tmp_path):
    g = CausalGraph()
    g.add_edge("A", "B", weight=0.5)
    g.add_edge("B", "C", weight=0.3)
    json_str = CausalGraphVisualizer.to_json(g)
    g2 = CausalGraphVisualizer.from_json(json_str)
    assert g2.nodes == g.nodes

    allowed_dir = Path.home() / ".aiops"
    allowed_dir.mkdir(parents=True, exist_ok=True)
    path = allowed_dir / f"causal_{uuid.uuid4().hex}.json"
    CausalGraphPersistence.save(g, str(path))
    loaded = CausalGraphPersistence.load(str(path))
    assert loaded.nodes == g.nodes
    path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Causal service
# ---------------------------------------------------------------------------


def _clean_causal_home():
    home = Path.home() / ".aiops"
    home.mkdir(parents=True, exist_ok=True)


def test_causal_analysis_service(tmp_path):
    _clean_causal_home()
    data = _causal_data()
    model_dir = Path.home() / ".aiops" / f"causal_test_{uuid.uuid4().hex}"
    service = causal_service.CausalAnalysisService(
        model_dir=str(model_dir),
        discovery_method="pc",
    )
    assert service.initialize(data)
    causes = service.identify_root_cause("service_C", data)
    assert isinstance(causes, list)
    explanation = service.explain_root_cause(
        {"node": "service_A", "method": "necessary_cause"},
        "service_C",
        data,
    )
    assert "root_cause" in explanation
    path = service.save_model("graph")
    assert Path(path).exists()
    causal_service.shutdown_service()
    assert service.load_model("graph")
    assert service.is_initialized
    causal_service.shutdown_service()


def test_causal_service_router():
    _clean_causal_home()
    causal_service.shutdown_service()
    app = FastAPI()
    app.include_router(causal_service.create_router())
    client = TestClient(app)
    data = {"service_A": [1.0, 2.0], "service_B": [2.0, 3.0], "service_C": [3.0, 4.0]}
    resp = client.post("/root-cause/causal/initialize", json={"metrics_data": data})
    assert resp.status_code in (200, 422)
    resp = client.get("/root-cause/causal/status")
    assert resp.status_code == 200


def test_global_service_helpers():
    _clean_causal_home()
    data = _causal_data()
    causal_service.shutdown_service()
    ok = causal_service.initialize_service(data, discovery_method="pc")
    assert ok
    assert causal_service.get_service().is_initialized
    causal_service.shutdown_service()


# ---------------------------------------------------------------------------
# GNN
# ---------------------------------------------------------------------------


def _sample_gnn_inputs():
    import dgl

    g = dgl.heterograph({})
    g.add_nodes("service", 4)
    g.add_nodes("metric", 3)
    features = {
        "service": torch.randn(4, 5),
        "metric": torch.randn(3, 4),
    }
    return g, features


def test_heterogeneous_gnn_model(tmp_path):
    g, features = _sample_gnn_inputs()
    model = HeterogeneousGNNModel(
        node_types=["service", "metric"],
        edge_types=["depends_on"],
        in_feats={"service": 5, "metric": 4},
        hidden_feats=8,
        out_feats=4,
        num_layers=1,
        dropout=0.1,
    )
    embeddings = model(g, features)
    assert "service" in embeddings
    pred = model.predict_root_cause(g, features, "alert_1")
    assert "root_cause_score" in pred
    attn = model.compute_attention_weights(g, features)
    assert "service" in attn

    save_path = tmp_path / "gnn.pt"
    model.save_model(str(save_path))
    model2 = HeterogeneousGNNModel(
        node_types=["service", "metric"],
        edge_types=["depends_on"],
        in_feats={"service": 5, "metric": 4},
        hidden_feats=8,
        out_feats=4,
        num_layers=1,
        dropout=0.1,
    )
    model2.load_model(str(save_path))
    assert model2.hidden_feats == 8


def test_gnn_trainer():
    g, features = _sample_gnn_inputs()
    model = HeterogeneousGNNModel(
        node_types=["service", "metric"],
        edge_types=["depends_on"],
        in_feats={"service": 5, "metric": 4},
        hidden_feats=8,
        out_feats=4,
        num_layers=1,
    )
    trainer = GNNTrainer(model, learning_rate=0.01)
    labels = {
        "service": torch.randint(0, 2, (4,)),
        "metric": torch.randint(0, 2, (3,)),
    }
    metrics = trainer.train_epoch(g, features, labels)
    assert "loss" in metrics
    eval_metrics = trainer.evaluate(g, features, labels)
    assert "accuracy" in eval_metrics


# ---------------------------------------------------------------------------
# Root cause inference
# ---------------------------------------------------------------------------


def _build_inference_graph():
    graph_builder = RootCauseGraphBuilder()
    services = [{"id": "s1", "name": "svc1", "type": "microservice"}]
    metrics = [
        {
            "id": "m1",
            "name": "cpu",
            "type": "gauge",
            "service_id": "s1",
            "current_value": 90.0,
        }
    ]
    alerts = [
        {
            "id": "a1",
            "title": "High CPU",
            "severity": "critical",
            "service_id": "s1",
            "metric_id": "m1",
        }
    ]
    deps = [{"source_id": "s1", "target_id": "s1", "type": "service"}]
    inference = RootCauseInference(graph_builder)
    inference.build_graph_from_alerts(alerts, services, metrics, deps)
    return inference


def test_root_cause_inference_build_and_infer():
    inference = _build_inference_graph()
    assert inference.graph_builder.node_counter > 0
    f_service = inference.extract_node_features(
        RootCauseGraphBuilder.NODE_TYPE_SERVICE,
        {"service_type": "database"},
    )
    assert len(f_service) == 10
    f_unknown = inference.extract_node_features("unknown", {})
    assert len(f_unknown) == 10

    node_types = [
        RootCauseGraphBuilder.NODE_TYPE_SERVICE,
        RootCauseGraphBuilder.NODE_TYPE_METRIC,
        RootCauseGraphBuilder.NODE_TYPE_ALERT,
    ]
    edge_types = [
        RootCauseGraphBuilder.EDGE_TYPE_DEPENDS,
    ]
    in_feats = {nt: 10 for nt in node_types}
    train_result = inference.train_model([], node_types, edge_types, in_feats, epochs=1)  # noqa: F841  # Variable for test verification
    assert "loss" in train_result
    result = inference.infer_root_cause("a1", hops=2)  # noqa: F841  # Variable for test verification
    assert "alert_id" in result
    explanation = inference.explain_root_cause("a1", result)
    assert "explanation" in explanation


def test_root_cause_inference_save_load(tmp_path):
    inference = _build_inference_graph()
    path = tmp_path / "inference.pkl"
    inference.save(str(path))
    inference2 = RootCauseInference()
    inference2.load(str(path))
    assert inference2.is_trained == inference.is_trained


def test_root_cause_inference_prepare_dgl_graph_error():
    inference = _build_inference_graph()
    original = sys.modules.pop("dgl", None)
    try:
        with pytest.raises(ImportError):
            inference.prepare_dgl_graph(["service"], ["depends_on"])
    finally:
        if original is not None:
            sys.modules["dgl"] = original


# ---------------------------------------------------------------------------
# Temporal worker
# ---------------------------------------------------------------------------


def test_task_result():
    r = temporal_worker.TaskResult("id", "success")
    assert r.timestamp is not None


async def _fake_execute_activity(activity, input_data, **kwargs):
    if activity is temporal_worker.detect_anomaly_activity:
        return {
            "status": "success",
            "result": {
                "anomaly_detected": input_data.get("anomaly_detected", True),
                "details": input_data,
            },
        }
    if activity is temporal_worker.root_cause_analysis_activity:
        return {"status": "success", "result": {"root": "cpu"}}
    if activity is temporal_worker.runbook_generation_activity:
        return {"status": "success", "result": {"runbook": {}}}
    if activity is temporal_worker.auto_heal_activity:
        return {"status": "success", "result": {"success": True}}
    if activity is temporal_worker.notify_activity:
        return {"status": "success"}
    return {"status": "success"}


def test_anomaly_detection_workflow(monkeypatch):
    fake_workflow = SimpleNamespace(
        execute_activity=_fake_execute_activity,
        defn=temporal_worker.workflow.defn,
        run=temporal_worker.workflow.run,
    )
    monkeypatch.setattr(temporal_worker, "workflow", fake_workflow)
    result = asyncio.run(  # noqa: F841  # Variable for test verification
        temporal_worker.AnomalyDetectionWorkflow().run({"auto_heal_enabled": True, "context": {}})
    )
    assert result["status"] == "completed"
    assert "heal" in result

    result2 = asyncio.run(
        temporal_worker.AnomalyDetectionWorkflow().run({"auto_heal_enabled": False, "context": {}})
    )
    assert result2["status"] == "completed"

    failure = asyncio.run(
        temporal_worker.AnomalyDetectionWorkflow().run(
            {
                "context": {},
                "anomaly_detected": False,
            }
        )
    )
    # detection reports no anomaly
    assert failure["status"] == "no_anomaly"


def test_auto_scaling_and_backup_workflows():
    result1 = asyncio.run(temporal_worker.AutoScalingWorkflow().run({"target": 10}))
    assert result1["status"] == "completed"
    result2 = asyncio.run(temporal_worker.BackupWorkflow().run({"source": "db"}))
    assert result2["status"] == "completed"


async def _fake_execute_workflow(*args, **kwargs):
    return {"status": "completed"}


async def _fake_close(*args, **kwargs):
    pass


async def _fake_connect(*args, **kwargs):
    return SimpleNamespace(
        execute_workflow=_fake_execute_workflow,
        close=_fake_close,
    )


def test_temporal_workflow_manager(monkeypatch):
    monkeypatch.setattr(temporal_worker.Client, "connect", _fake_connect)

    class FakeWorker:
        def __init__(self, *args, **kwargs):
            self._shutdown = False

        async def run(self):
            self._shutdown = False

        def shutdown(self):
            self._shutdown = True

    monkeypatch.setattr(temporal_worker.worker, "Worker", FakeWorker)

    manager = temporal_worker.TemporalWorkflowManager()
    ok = asyncio.run(manager.connect())
    assert ok is True
    assert manager.client is not None
    start_ok = asyncio.run(manager.start_worker())
    assert start_ok is True
    result = asyncio.run(manager.execute_workflow(temporal_worker.AutoScalingWorkflow, {"x": 1}))  # noqa: F841  # Variable for test verification
    assert result["status"] == "completed"
    asyncio.run(manager.stop_worker())
    assert not manager.is_running
    asyncio.run(manager.close())


def test_create_temporal_manager():
    mgr = temporal_worker.create_temporal_manager()
    assert mgr is not None
    assert isinstance(mgr, temporal_worker.TemporalWorkflowManager)


# ---------------------------------------------------------------------------
# Runbook generator
# ---------------------------------------------------------------------------


def test_runbook_generator():
    store = FakeVectorStore()
    gen = RunbookGenerator(vector_store=store, llm_provider="local")
    gen.initialize()
    alert = {
        "title": "High CPU",
        "description": "CPU usage high",
        "severity": "critical",
        "service": "svc1",
        "metric": "cpu",
        "current_value": 95.0,
        "threshold": 80.0,
    }
    result = gen.generate_runbook(alert, context={"cluster": "c1"})  # noqa: F841  # Variable for test verification
    assert "runbook" in result
    quality = gen.evaluate_runbook_quality(result["runbook"], alert)
    assert 0 <= quality["quality_score"] <= 1
    indexed = gen.index_historical_cases(
        [{"id": "c1", "content": "reboot fixed issue", "metadata": {}}]
    )
    assert indexed == 1


def test_runbook_generator_llm_branches():
    gen = RunbookGenerator(vector_store=FakeVectorStore(), llm_provider="local")
    gen.initialize()
    prompt = "test"
    fallback = gen._call_llm(prompt)
    assert "problem_summary" in json.loads(fallback)

    gen.llm_provider = "openai"
    fake_client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(
                create=lambda *a, **k: SimpleNamespace(
                    choices=[
                        SimpleNamespace(
                            message=SimpleNamespace(content=json.dumps({"problem_summary": "x"}))
                        )
                    ]
                )
            )
        )
    )
    gen.openai_client = fake_client
    openai_result = gen._call_llm(prompt)  # noqa: F841  # Variable for test verification
    assert "problem_summary" in json.loads(openai_result)

    gen.llm_provider = "claude"
    fake_claude = SimpleNamespace(
        messages=SimpleNamespace(
            create=lambda *a, **k: SimpleNamespace(
                content=[SimpleNamespace(text=json.dumps({"problem_summary": "x"}))]
            )
        )
    )
    gen.claude_client = fake_claude
    claude_result = gen._call_llm(prompt)  # noqa: F841  # Variable for test verification
    assert "problem_summary" in json.loads(claude_result)


def test_runbook_parser():
    gen = RunbookGenerator(vector_store=FakeVectorStore())
    valid = json.dumps(
        {
            "problem_summary": "x",
            "root_cause_analysis": "x",
            "immediate_actions": ["a"],
            "long_term_solutions": ["b"],
            "verification_steps": ["c"],
            "rollback_plan": ["d"],
            "risk_assessment": "x",
        }
    )
    assert "problem_summary" in gen._parse_runbook(valid)
    bad = "not json {valid"
    parsed = gen._parse_runbook(bad)
    assert "raw_response" in parsed


# ---------------------------------------------------------------------------
# Anomaly ensemble
# ---------------------------------------------------------------------------


def _ensemble_data(n: int = 12) -> List[Dict[str, Any]]:
    base = pd.Timestamp("2024-01-01")  # noqa: F841  # Variable for test verification
    return [
        {
            "timestamp": (base + pd.Timedelta(hours=i)).isoformat(),
            "value": float(i),
            "feature": float(i % 5),
        }
        for i in range(n)
    ]


@pytest.mark.parametrize("voting", ["hard", "soft", "weighted"])
def test_ensemble_anomaly_detector(voting, dummy_prophet_detector):
    data = _ensemble_data()
    detector = EnsembleAnomalyDetector(
        voting=voting,
        prophet_weight=0.5,
        isolation_weight=0.5,
        threshold=0.4,
        isolation_params={"n_estimators": 10, "max_samples": "auto"},
    )
    detector.fit(data, value_col="value", feature_cols=["feature"])
    result = detector.predict(data, value_col="value", feature_cols=["feature"])  # noqa: F841  # Variable for test verification
    assert "anomalies" in result
    assert voting in result["metrics"]["voting_method"]

    with pytest.raises(RuntimeError):
        detector2 = EnsembleAnomalyDetector()
        detector2.predict(data)


def test_ensemble_unknown_voting(dummy_prophet_detector):
    detector = EnsembleAnomalyDetector(voting="unknown")
    data = _ensemble_data()
    detector.is_fitted = True
    detector.prophet_detector = SimpleNamespace(predict=lambda *a, **k: {"anomalies": []})
    detector.isolation_detector = SimpleNamespace(predict=lambda *a, **k: {"anomalies": []})
    with pytest.raises(ValueError):
        detector.predict(data)


def test_ensemble_save_load(tmp_path, dummy_prophet_detector):
    data = _ensemble_data()
    detector = EnsembleAnomalyDetector()
    detector.fit(data, value_col="value", feature_cols=["feature"])
    path = tmp_path / "ensemble.joblib"
    detector.save_model(str(path))
    detector2 = EnsembleAnomalyDetector()
    detector2.load_model(str(path))
    assert detector2.is_fitted


# ---------------------------------------------------------------------------
# PostgreSQL storage
# ---------------------------------------------------------------------------


def test_postgresql_storage_crud(fake_postgres):
    storage = postgres_storage.PostgreSQLStorage()
    ok = storage.initialize()
    assert ok is True
    assert storage._is_initialized

    assert storage.store_metadata("k1", {"a": 1})
    meta = storage.get_metadata("k1")
    assert meta == {"a": 1}
    assert storage.delete_metadata("k1")

    assert storage.store_policy("p1", "alert", {"rule": "x"}, enabled=True)
    policy = storage.get_policy("p1")
    assert policy is not None
    assert policy["name"] == "p1"
    policies = storage.list_policies(policy_type="alert")
    assert len(policies) == 1

    assert storage.store_configuration("cfg", "val", "desc")
    cfg = storage.get_configuration("cfg")
    assert cfg == "val"

    assert storage.log_audit("create", "admin", "policy", "p1", {"detail": 1})
    audits = storage.query_audit_log(actor="admin", limit=10)
    assert len(audits) == 1
    assert audits[0]["actor"] == "admin"

    results = storage.execute_query("SELECT * FROM metadata WHERE key = %s", ("k1",))
    assert isinstance(results, list)

    storage.close()
    assert not storage._is_initialized


def test_postgresql_storage_errors(fake_postgres):
    storage = postgres_storage.PostgreSQLStorage()
    storage.initialize()
    # force a query failure inside a context manager to cover rollback
    with pytest.raises(RuntimeError):
        with storage.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM bad_table")

    # public methods catch errors and return False/None
    import modules.storage.postgres.storage as pgs

    original_pool = pgs.pool  # noqa: F841  # Variable for test verification
    try:
        pgs.pool = SimpleNamespace(SimpleConnectionPool=lambda *a, **k: _FailPool())
        storage2 = postgres_storage.PostgreSQLStorage()
        assert storage2.initialize() is False
        assert storage2.store_metadata("x", {}) is False
        assert storage2.get_metadata("x") is None
    finally:
        pgs.pool = original_pool  # noqa: F841  # Variable for test verification


class _FailPool:
    def __init__(self, *args, **kwargs):
        pass

    def getconn(self):
        raise RuntimeError("bad pool")

    def putconn(self, conn):
        pass

    def closeall(self):
        pass


def test_create_postgres_storage(fake_postgres):
    storage = postgres_storage.create_postgres_storage()
    assert storage is not None


# ---------------------------------------------------------------------------
# Extra coverage for public helpers
# ---------------------------------------------------------------------------


def test_causal_graph_builder_other_builds():
    builder = create_causal_graph_builder(discovery_method="pc")
    metrics = _causal_data()
    log_data = pd.DataFrame(
        {
            "level": ["INFO", "ERROR", "INFO"],
            "timestamp": pd.date_range("2024-01-01", periods=3),
            "message": ["a", "b", "c"],
        }
    )
    builder.build_from_logs(log_data)
    trace_data = pd.DataFrame({"duration": [1.0, 2.0], "error": [0, 1]})
    builder.build_from_traces(trace_data)
    builder.build_multimodal(metrics_data=metrics, log_data=log_data, trace_data=trace_data)
    assert builder.causal_graph is not None


# ---------------------------------------------------------------------------
# Additional coverage for below-80% modules
# ---------------------------------------------------------------------------


def test_temporal_activities(monkeypatch):
    # core fakes
    core_pkg = types.ModuleType("core")
    core_pkg.__path__ = []
    monkeypatch.setitem(sys.modules, "core", core_pkg)

    class AnomalyDetector:
        async def detect(self, input_data):
            return {"anomaly_detected": True}

    class AutoHealEngine:
        async def heal(self, input_data):
            return {"success": True}

    class RunbookGeneratorCore:
        async def generate(self, input_data):
            return {"runbook": {}}

    class NotificationEngine:
        async def send(self, input_data):
            return {"sent": True}

    monkeypatch.setitem(
        sys.modules, "core.anomaly_detection", SimpleNamespace(AnomalyDetector=AnomalyDetector)
    )
    monkeypatch.setitem(
        sys.modules, "core.auto_heal", SimpleNamespace(AutoHealEngine=AutoHealEngine)
    )
    monkeypatch.setitem(
        sys.modules,
        "core.runbook_generator",
        SimpleNamespace(RunbookGenerator=RunbookGeneratorCore),
    )
    monkeypatch.setitem(
        sys.modules, "core.notify_engine", SimpleNamespace(NotificationEngine=NotificationEngine)
    )

    async def _analyze(self, input_data):
        return {"root": "cpu"}

    monkeypatch.setattr(RootCauseInference, "analyze", _analyze, raising=False)

    assert asyncio.run(temporal_worker.detect_anomaly_activity({}))["status"] == "success"
    assert asyncio.run(temporal_worker.root_cause_analysis_activity({}))["status"] == "success"
    assert asyncio.run(temporal_worker.auto_heal_activity({}))["status"] == "success"
    assert asyncio.run(temporal_worker.runbook_generation_activity({}))["status"] == "success"
    assert asyncio.run(temporal_worker.notify_activity({}))["status"] == "success"


def test_anomaly_detection_workflow_failure(monkeypatch):
    async def _fail(activity, input_data, **kwargs):
        if activity is temporal_worker.detect_anomaly_activity:
            return {"status": "failed"}
        return {"status": "success"}

    fake_workflow = SimpleNamespace(
        execute_activity=_fail,
        defn=temporal_worker.workflow.defn,
        run=temporal_worker.workflow.run,
    )
    monkeypatch.setattr(temporal_worker, "workflow", fake_workflow)
    result = asyncio.run(temporal_worker.AnomalyDetectionWorkflow().run({"context": {}}))  # noqa: F841  # Variable for test verification
    assert result["status"] == "failed"


def test_temporal_workflow_manager_branches(monkeypatch):
    # connect returns False
    monkeypatch.setattr(
        temporal_worker.Client,
        "connect",
        lambda *a, **k: (_ for _ in ()).throw(ConnectionError("x")),
    )
    manager = temporal_worker.TemporalWorkflowManager()
    assert asyncio.run(manager.connect()) is False

    # start_worker returns False
    async def _ok_connect(*args, **kwargs):
        return SimpleNamespace(execute_workflow=_fake_execute_workflow, close=_fake_close)

    monkeypatch.setattr(temporal_worker.Client, "connect", _ok_connect)
    monkeypatch.setattr(
        temporal_worker.worker, "Worker", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x"))
    )
    manager2 = temporal_worker.TemporalWorkflowManager()
    assert asyncio.run(manager2.connect()) is True
    assert asyncio.run(manager2.start_worker()) is False

    # execute_workflow re-raises
    async def _bad_client(*args, **kwargs):
        return SimpleNamespace(
            execute_workflow=lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x")),
            close=lambda *a, **k: None,
        )

    monkeypatch.setattr(temporal_worker.Client, "connect", _bad_client)
    monkeypatch.setattr(temporal_worker.worker, "Worker", lambda *a, **k: SimpleNamespace())
    manager3 = temporal_worker.TemporalWorkflowManager()
    asyncio.run(manager3.connect())
    with pytest.raises(RuntimeError):
        asyncio.run(manager3.execute_workflow(temporal_worker.AutoScalingWorkflow, {"x": 1}))

    # close catches exception
    async def _bad_close(*args, **kwargs):
        return SimpleNamespace(
            execute_workflow=_fake_execute_workflow,
            close=lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x")),
        )

    monkeypatch.setattr(temporal_worker.Client, "connect", _bad_close)
    manager4 = temporal_worker.TemporalWorkflowManager()
    asyncio.run(manager4.connect())
    with pytest.raises(RuntimeError):
        asyncio.run(manager4.close())


def test_create_temporal_manager_failure(monkeypatch):
    class _Raise:
        def __init__(self, *a, **k):
            raise RuntimeError("x")

    monkeypatch.setattr(temporal_worker, "TemporalWorkflowManager", _Raise)
    assert temporal_worker.create_temporal_manager() is None


def test_causal_service_error_paths_and_router():
    causal_service.shutdown_service()
    _clean_causal_home()

    data = _causal_data()
    service = causal_service.CausalAnalysisService()

    with pytest.raises(HTTPException):
        service.identify_root_cause("service_C", data)
    with pytest.raises(HTTPException):
        service.explain_root_cause({"node": "x"}, "service_C", data)
    with pytest.raises(HTTPException):
        service.estimate_causal_effect("service_A", "service_C", data)
    with pytest.raises(HTTPException):
        service.counterfactual_query({}, {}, "service_C", data)
    with pytest.raises(HTTPException):
        service.save_model()

    # initialize failure
    class _FailBuilder:
        def build_from_metrics(self, *args, **kwargs):
            raise RuntimeError("x")

        def get_analyzer(self):
            pass

    import modules.analyze.root_cause.causal_service as cs_mod

    original = cs_mod.create_causal_graph_builder
    cs_mod.create_causal_graph_builder = lambda **k: _FailBuilder()
    try:
        svc = causal_service.CausalAnalysisService()
        assert svc.initialize(data) is False
    finally:
        cs_mod.create_causal_graph_builder = original

    # load not found and bad file
    svc2 = causal_service.CausalAnalysisService(
        model_dir=str(Path.home() / ".aiops" / f"causal_nf_{uuid.uuid4().hex}")
    )
    assert svc2.load_model("missing") is False
    svc2.model_dir.mkdir(parents=True, exist_ok=True)
    (svc2.model_dir / "bad.json").write_text("not json")
    assert svc2.load_model("bad") is False

    # router endpoints
    causal_service.shutdown_service()
    app = FastAPI()
    app.include_router(causal_service.create_router())
    client = TestClient(app)

    payload = {
        "service_A": data["service_A"].tolist(),
        "service_B": data["service_B"].tolist(),
        "service_C": data["service_C"].tolist(),
    }
    resp = client.post("/root-cause/causal/initialize", json=payload)
    assert resp.status_code == 200
    resp = client.get("/root-cause/causal/status")
    assert resp.status_code == 200
    resp = client.post("/root-cause/causal/model/save")
    assert resp.status_code == 200
    resp = client.post("/root-cause/causal/model/load", params={"name": "saved_graph"})
    assert resp.status_code == 200
    resp = client.post(
        "/root-cause/causal/root-cause", params={"alert_var": "service_C"}, json=payload
    )
    assert resp.status_code == 200
    causal_service.shutdown_service()


def test_runbook_more_branches(monkeypatch):
    alert = {
        "title": "High CPU",
        "description": "CPU usage high",
        "severity": "critical",
        "service": "svc1",
        "metric": "cpu",
        "current_value": 95.0,
        "threshold": 80.0,
    }

    # openai generate
    gen = RunbookGenerator(vector_store=FakeVectorStore(), llm_provider="openai")
    gen.is_initialized = True
    gen.openai_client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(
                create=lambda *a, **k: SimpleNamespace(
                    choices=[
                        SimpleNamespace(
                            message=SimpleNamespace(content=json.dumps({"problem_summary": "x"}))
                        )
                    ]
                )
            )
        )
    )
    result = gen.generate_runbook(alert)  # noqa: F841  # Variable for test verification
    assert result["success"] is True

    # claude generate
    gen2 = RunbookGenerator(vector_store=FakeVectorStore(), llm_provider="claude")
    gen2.is_initialized = True
    gen2.claude_client = SimpleNamespace(
        messages=SimpleNamespace(
            create=lambda *a, **k: SimpleNamespace(
                content=[SimpleNamespace(text=json.dumps({"problem_summary": "x"}))]
            )
        )
    )
    result2 = gen2.generate_runbook(alert)
    assert result2["success"] is True

    # fallback on llm failure
    gen3 = RunbookGenerator(vector_store=FakeVectorStore(), llm_provider="openai")
    gen3.is_initialized = True

    def _bad_call(prompt):
        raise RuntimeError("llm fail")

    gen3._call_llm = _bad_call
    result3 = gen3.generate_runbook(alert)
    assert result3["success"] is False
    assert "runbook" in result3

    # quality evaluation
    q = gen.evaluate_runbook_quality({"problem_summary": "High CPU"}, alert)
    assert q["passed"] is False

    # empty retrieve
    assert gen.retrieve_relevant_cases({"title": "x"}) == []

    # build prompt with context and rag
    prompt = gen._build_prompt(alert, {"cluster": "c1"}, [{"score": 0.9, "content": "case"}])
    assert "Alert Information" in prompt


def test_root_cause_inference_extra():
    # GNN path that finds a root cause node
    inference = _build_inference_graph()
    inference.gnn_model = SimpleNamespace(
        predict_root_cause=lambda g, features, alert_id: {
            "root_cause_type": "service",
            "root_cause_score": 0.9,
            "all_scores": {},
        }
    )
    inference.is_trained = True
    result = inference.infer_root_cause("a1", hops=2)  # noqa: F841  # Variable for test verification
    assert result["method"] == "gnn"
    explanation = inference.explain_root_cause("a1", result)
    assert "explanation" in explanation

    # metric root cause explanation
    metric_result = {  # noqa: F841  # Variable for test verification
        "root_cause": {
            "id": "metric_m1",
            "node_type": RootCauseGraphBuilder.NODE_TYPE_METRIC,
            "metric_name": "cpu",
            "current_value": 90.0,
        },
        "confidence": 0.8,
        "method": "gnn",
    }
    explanation2 = inference.explain_root_cause("a1", metric_result)
    assert "Metric" in explanation2["explanation"]

    # heuristic fallback
    inference2 = _build_inference_graph()
    inference2.gnn_model = None
    heuristic = inference2.infer_root_cause("a1", hops=2)
    assert heuristic["method"] == "heuristic_pagerank"

    # prepare dgl graph with missing node type (zero features branch)
    inference3 = _build_inference_graph()
    g, features = inference3.prepare_dgl_graph(["service", "missing"], ["depends_on"])
    assert "service" in features
    assert "missing" in features


def test_postgresql_storage_extra(fake_postgres, monkeypatch):
    storage = postgres_storage.PostgreSQLStorage()
    storage.initialize()

    # get_connection on uninitialized storage
    storage2 = postgres_storage.PostgreSQLStorage()
    with pytest.raises(RuntimeError):
        with storage2.get_connection():
            pass

    # all public methods degrade gracefully when get_connection raises
    def _raise():
        raise RuntimeError("conn fail")

    monkeypatch.setattr(storage, "get_connection", _raise)
    assert storage.store_metadata("k", {}) is False
    assert storage.get_metadata("k") is None
    assert storage.get_policy("p") is None
    assert storage.list_policies() == []
    assert storage.get_configuration("c") is None
    assert storage.log_audit("a", "b") is False
    assert storage.query_audit_log() == []
    assert storage.execute_query("SELECT * FROM metadata") == []

    # close failure is swallowed
    storage3 = postgres_storage.PostgreSQLStorage()
    storage3.initialize()
    storage3._pool.closeall = lambda: (_ for _ in ()).throw(RuntimeError("x"))
    with pytest.raises(RuntimeError):
        storage3.close()
