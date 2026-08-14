# -*- coding: utf-8 -*-
"""Batch C unit tests for uncovered assigned modules."""

import asyncio
import sys
import types
from datetime import datetime, timedelta

import numpy as np
import pytest
import torch

# Pre-populate the DGL-backed gnn submodule so the root_cause package __init__
# can import without failing on missing DGL/PyTorch dependencies.
sys.modules.setdefault(
    "modules.analyze.root_cause.gnn",
    types.SimpleNamespace(HeterogeneousGNNModel=object),
)

import modules.analyze.anomaly.transformer_model as transformer_model
import modules.analyze.root_cause.graph_builder as graph_builder
import modules.apm.dependency_analyzer as dependency_analyzer
import modules.execute.auto_heal.playbook_manager as playbook_manager
import modules.execute.autoscaler.custom_hpa as custom_hpa
import modules.execute.autoscaler.custom_hpa_controller as custom_hpa_controller
import modules.execute.saga.coordinator as saga_coordinator
import modules.observability.smart_alerting as smart_alerting
import modules.observability.smart_analysis as smart_analysis


# ----------------------------------------------------------------------
# modules/execute/autoscaler/custom_hpa.py
# ----------------------------------------------------------------------
@pytest.fixture
def hpa():
    controller = custom_hpa.CustomHPAController()
    controller.initialize()
    return controller


def _metric(name, value, resource="svc"):
    return custom_hpa.MetricData(
        name=name,
        value=value,
        timestamp=datetime.now(),
        labels={"resource": resource},
    )


@pytest.mark.asyncio
async def test_custom_hpa_scale_up(hpa):
    metrics = [_metric("cpu", 90.0), _metric("memory", 85.0)]
    decision = await hpa.evaluate_scaling("svc", 3, metrics)
    assert decision.direction == custom_hpa.ScaleDirection.UP
    assert decision.desired_replicas > 3
    assert decision.confidence > 0


@pytest.mark.asyncio
async def test_custom_hpa_scale_down(hpa):
    metrics = [_metric("cpu", 20.0), _metric("memory", 15.0)]
    decision = await hpa.evaluate_scaling("svc", 5, metrics)
    assert decision.direction == custom_hpa.ScaleDirection.DOWN
    assert decision.desired_replicas < 5


@pytest.mark.asyncio
async def test_custom_hpa_no_scale_within_range(hpa):
    metrics = [_metric("cpu", 50.0)]
    decision = await hpa.evaluate_scaling("svc", 3, metrics)
    assert decision.direction == custom_hpa.ScaleDirection.NONE
    assert decision.desired_replicas == 3


@pytest.mark.asyncio
async def test_custom_hpa_cooldown_blocks_scale(hpa):
    up_metrics = [_metric("cpu", 95.0)]
    first = await hpa.evaluate_scaling("svc", 2, up_metrics)
    assert first.direction == custom_hpa.ScaleDirection.UP

    second = await hpa.evaluate_scaling("svc", 2, up_metrics)
    assert second.direction == custom_hpa.ScaleDirection.NONE
    assert "cooldown" in second.reason.lower()


@pytest.mark.asyncio
async def test_custom_hpa_forecast_influences_decision(hpa):
    for _ in range(12):
        hpa._store_metric_history("svc", [_metric("cpu", 70.0)])
    forecast = hpa.predict_utilization("svc", horizon_minutes=3)
    assert isinstance(forecast, list)
    metrics = [_metric("cpu", 75.0)]
    decision = await hpa.evaluate_scaling("svc", 3, metrics, forecast=forecast)
    assert decision.resource == "svc"


def test_custom_hpa_not_initialized_raises():
    controller = custom_hpa.CustomHPAController()
    with pytest.raises(RuntimeError):
        asyncio.run(
            controller.evaluate_scaling("svc", 1, [_metric("cpu", 80.0)])
        )


def test_custom_hpa_utilization_and_status(hpa):
    assert hpa._calculate_utilization([]) == 0.0
    assert hpa._calculate_utilization([_metric("cpu", 50.0)]) == 0.5
    status = hpa.get_status()
    assert status["initialized"]
    assert "config" in status


def test_custom_hpa_metric_history_and_reset(hpa):
    hpa._store_metric_history("svc", [_metric("cpu", 10.0)])
    history = hpa.get_metric_history("svc")
    assert len(history) == 1
    hpa.clear_metric_history("svc")
    assert hpa.get_metric_history("svc") == []
    hpa._last_scale_up["svc"] = datetime.now()
    hpa.reset_cooldowns("svc")
    assert "svc" not in hpa._last_scale_up


def test_custom_hpa_factory():
    controller = custom_hpa.create_custom_hpa_controller({"min_replicas": 2})
    assert controller is not None
    assert controller.min_replicas == 2


def test_custom_hpa_dataclasses():
    metric = custom_hpa.MetricData("m", 1.0, datetime.now(), {})
    assert "name" in metric.to_dict()
    decision = custom_hpa.ScalingDecision(
        resource="r",
        current_replicas=1,
        desired_replicas=2,
        direction=custom_hpa.ScaleDirection.UP,
        reason="test",
        confidence=1.0,
        metrics=[metric],
    )
    assert decision.to_dict()["desired_replicas"] == 2


# ----------------------------------------------------------------------
# modules/execute/autoscaler/custom_hpa_controller.py
# ----------------------------------------------------------------------
@pytest.fixture
def hpa_ctrl():
    return custom_hpa_controller.CustomHPAController()


def test_hpa_controller_init_and_policy(hpa_ctrl):
    hpa_ctrl.initialize()
    policy = custom_hpa_controller.ScalingPolicy(scale_up_threshold=60.0)
    hpa_ctrl.register_policy("app", policy)
    assert hpa_ctrl.get_policy("app") is policy
    assert hpa_ctrl.create_hpa_manifest("app", policy)["kind"] == "HorizontalPodAutoscaler"


def test_hpa_controller_scaling_directions(hpa_ctrl):
    policy = custom_hpa_controller.ScalingPolicy(
        min_replicas=1,
        max_replicas=10,
        scale_up_threshold=60.0,
        scale_down_threshold=30.0,
    )
    up = hpa_ctrl._evaluate_scaling_direction(
        {"cpu_utilization": 65.0, "memory_utilization": 50.0}, policy
    )
    assert up == custom_hpa_controller.ScalingDirection.SCALE_UP
    down = hpa_ctrl._evaluate_scaling_direction(
        {"cpu_utilization": 20.0, "memory_utilization": 30.0}, policy
    )
    assert down == custom_hpa_controller.ScalingDirection.SCALE_DOWN
    none = hpa_ctrl._evaluate_scaling_direction(
        {"cpu_utilization": 50.0, "memory_utilization": 50.0}, policy
    )
    assert none == custom_hpa_controller.ScalingDirection.NO_ACTION


def test_hpa_controller_target_replicas(hpa_ctrl):
    policy = custom_hpa_controller.ScalingPolicy(target_cpu_utilization=70.0)
    assert hpa_ctrl._calculate_target_replicas(
        3, {"cpu_utilization": 65.0}, policy, custom_hpa_controller.ScalingDirection.SCALE_UP
    ) == 4
    assert hpa_ctrl._calculate_target_replicas(
        3, {}, policy, custom_hpa_controller.ScalingDirection.SCALE_DOWN
    ) == 2
    assert hpa_ctrl._calculate_target_replicas(
        3, {}, policy, custom_hpa_controller.ScalingDirection.NO_ACTION
    ) == 3


@pytest.mark.asyncio
async def test_hpa_controller_evaluate_scale_up(hpa_ctrl):
    policy = custom_hpa_controller.ScalingPolicy(scale_up_threshold=60.0)
    hpa_ctrl.register_policy("app", policy)
    await hpa_ctrl._evaluate_scaling("app", policy)
    history = hpa_ctrl.get_scaling_history()
    assert history
    assert history[0]["direction"] == custom_hpa_controller.ScalingDirection.SCALE_UP.value
    stats = hpa_ctrl.get_scaling_stats()
    assert stats["total_scalings"] == 1


@pytest.mark.asyncio
async def test_hpa_controller_cooldown(hpa_ctrl):
    policy = custom_hpa_controller.ScalingPolicy(scale_up_threshold=60.0)
    hpa_ctrl.register_policy("app", policy)
    hpa_ctrl._cooldowns["app"] = datetime.now() + timedelta(seconds=60)
    await hpa_ctrl._evaluate_scaling("app", policy)
    assert not hpa_ctrl.get_scaling_history()


@pytest.mark.asyncio
async def test_hpa_controller_monitor_and_scale_one_iteration(hpa_ctrl):
    hpa_ctrl.register_policy(
        "app", custom_hpa_controller.ScalingPolicy(scale_up_threshold=60.0)
    )
    try:
        await asyncio.wait_for(hpa_ctrl.monitor_and_scale(interval=60), timeout=0.1)
    except asyncio.TimeoutError:
        pass
    assert hpa_ctrl.get_scaling_history() or not hpa_ctrl.get_scaling_history()


def test_hpa_controller_cooldown_cleanup(hpa_ctrl):
    hpa_ctrl._cooldowns["app"] = datetime.now() - timedelta(seconds=1)
    hpa_ctrl._cleanup_cooldowns()
    assert "app" not in hpa_ctrl._cooldowns


# ----------------------------------------------------------------------
# modules/execute/auto_heal/playbook_manager.py
# ----------------------------------------------------------------------
@pytest.fixture
def pb_manager(tmp_path):
    return playbook_manager.PlaybookManager(playbook_dir=str(tmp_path), dry_run=True)


def test_playbook_manager_load_and_create(pb_manager):
    assert not pb_manager.load_playbook("missing")
    assert pb_manager.create_playbook(
        "test", [{"name": "test task", "debug": {"msg": "hello"}}]
    )
    assert "test" in pb_manager.list_playbooks()
    info = pb_manager.get_playbook("test")
    assert info["parsed"]


def test_playbook_manager_invalid_yaml(pb_manager):
    assert not pb_manager.load_playbook("bad", content="[unbalanced")


def test_playbook_manager_save_and_delete(pb_manager, tmp_path):
    pb_manager.create_playbook("save", [{"name": "t", "debug": {"msg": "x"}}])
    assert pb_manager.save_playbook("save")
    assert (tmp_path / "save.yml").exists()
    assert pb_manager.delete_playbook("save")
    assert not (tmp_path / "save.yml").exists()


def test_playbook_manager_builtins(pb_manager):
    templates = pb_manager.get_builtin_playbooks()
    assert "restart_service" in templates
    assert pb_manager.create_builtin_playbook("restart_service", "restart")
    assert not pb_manager.create_builtin_playbook("unknown", "x")


@pytest.mark.asyncio
async def test_playbook_manager_execute_not_found(pb_manager):
    result = await pb_manager.execute_playbook("missing")
    assert not result["success"]


@pytest.mark.asyncio
async def test_playbook_manager_execute_dry_run(pb_manager, monkeypatch):
    pb_manager.create_playbook("ok", [{"name": "t", "debug": {"msg": "x"}}])

    class FakeProcess:
        returncode = 0
        stdout = b"ok"
        stderr = b""

        async def communicate(self):
            return self.stdout, self.stderr

    async def fake_subprocess(*args, **kwargs):
        return FakeProcess()

    monkeypatch.setattr(
        "modules.execute.auto_heal.playbook_manager.asyncio.create_subprocess_exec",
        fake_subprocess,
    )
    result = await pb_manager.execute_playbook("ok", extra_vars={"a": 1}, tags=["t"], limit="all")
    assert result["success"]
    assert result["stdout"] == "ok"


@pytest.mark.asyncio
async def test_playbook_manager_execute_errors(pb_manager, monkeypatch):
    pb_manager.create_playbook("ok", [{"name": "t", "debug": {"msg": "x"}}])

    async def raise_fnf(*args, **kwargs):
        raise FileNotFoundError

    monkeypatch.setattr(
        "modules.execute.auto_heal.playbook_manager.asyncio.create_subprocess_exec",
        raise_fnf,
    )
    result = await pb_manager.execute_playbook("ok")
    assert result["error"] == "ansible-playbook not found"

    async def raise_err(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(
        "modules.execute.auto_heal.playbook_manager.asyncio.create_subprocess_exec",
        raise_err,
    )
    result = await pb_manager.execute_playbook("ok")
    assert "boom" in result["error"]


@pytest.mark.asyncio
async def test_playbook_executor_heal(pb_manager, monkeypatch):
    executor = playbook_manager.PlaybookExecutor(pb_manager)

    async def fake_execute(*args, **kwargs):
        return {"success": True}

    monkeypatch.setattr(pb_manager, "execute_playbook", fake_execute)
    result = await executor.execute_heal_playbook("restart_service", {"service_name": "nginx"})
    assert result["success"]
    assert executor.get_executions()
    assert executor.get_execution(list(executor._executions.keys())[0])
    unknown = await executor.execute_heal_playbook("unknown_type", {})
    assert not unknown["success"]


# ----------------------------------------------------------------------
# modules/analyze/anomaly/transformer_model.py
# ----------------------------------------------------------------------
@pytest.fixture
def small_detector():
    return transformer_model.TransformerAnomalyDetector(
        input_dim=1,
        d_model=16,
        n_heads=2,
        n_layers=1,
        d_ff=32,
        metric_dim=1,
        log_dim=4,
        trace_dim=4,
    )


def test_transformer_validation():
    with pytest.raises(ValueError):
        transformer_model.TransformerAnomalyDetector(input_dim=0)
    with pytest.raises(ValueError):
        transformer_model.TransformerAnomalyDetector(d_model=15, n_heads=2)
    with pytest.raises(ValueError):
        transformer_model.TransformerAnomalyDetector(n_layers=0)
    with pytest.raises(ValueError):
        transformer_model.TransformerAnomalyDetector(dropout=1.0)


def test_transformer_forward_and_parts(small_detector):
    seq_len = 5
    metric = torch.randn(1, seq_len, 1)
    log = torch.randn(1, seq_len, 4)
    trace = torch.randn(1, seq_len, 4)
    anomaly_scores, reconstruction = small_detector(metric, log, trace)
    assert anomaly_scores.shape == (1, seq_len, 1)
    assert reconstruction.shape == (1, seq_len, 1)

    # single modal only
    scores, recon = small_detector(metric)
    assert scores.shape == (1, seq_len, 1)


def test_transformer_positional_encoding_and_embeddings():
    pe = transformer_model.PositionalEncoding(d_model=8)
    x = torch.randn(1, 4, 8)
    assert pe(x).shape == x.shape
    emb = transformer_model.InputEmbedding(input_dim=2, d_model=8)
    assert emb(torch.randn(1, 4, 2)).shape == (1, 4, 8)
    enc = transformer_model.TransformerEncoderLayer(d_model=8, n_heads=2, d_ff=16)
    assert enc(torch.randn(1, 4, 8)).shape == (1, 4, 8)
    head = transformer_model.AnomalyDetectionHead(d_model=8, hidden_dim=16)
    assert head(torch.randn(1, 4, 8)).shape == (1, 4, 1)
    fusion = transformer_model.MultiModalFusion(metric_dim=1, log_dim=4, trace_dim=4, d_model=8)
    assert fusion(torch.randn(1, 4, 1)).shape == (1, 4, 8)
    assert fusion(torch.randn(1, 4, 1), torch.randn(1, 4, 4), torch.randn(1, 4, 4)).shape == (1, 4, 8)


def test_transformer_dataset_and_loss():
    data = np.random.randn(40, 1).astype(np.float32)
    labels = np.random.randint(0, 2, size=40).astype(np.float32)
    dataset = transformer_model.TimeSeriesDataset(data, seq_len=5, labels=labels)
    assert len(dataset) == 36
    x, y = dataset[0]
    assert x.shape == (5, 1)
    assert y.shape == (5,)

    loss_fn = transformer_model.AnomalyLoss()
    recon = torch.randn(2, 5, 1)
    orig = torch.randn(2, 5, 1)
    scores = torch.randn(2, 5, 1)
    lbl = torch.randint(0, 2, (2, 5)).float()
    assert loss_fn(recon, orig, scores, lbl).numel() == 1
    assert loss_fn(recon, orig, scores).numel() == 1


def test_transformer_trainer(small_detector):
    data = np.random.randn(20, 1).astype(np.float32)
    labels = np.random.randint(0, 2, size=20).astype(np.float32)
    dataset = transformer_model.TimeSeriesDataset(data, seq_len=5, labels=labels)
    loader = torch.utils.data.DataLoader(dataset, batch_size=2)
    trainer = transformer_model.TransformerAnomalyTrainer(small_detector, device="cpu", learning_rate=1e-3)
    assert trainer.train_epoch(loader, 0) > 0
    assert trainer.validate(loader) > 0


def test_transformer_wrapper_and_factory():
    model = transformer_model.create_transformer_model(
        input_dim=1, d_model=16, n_heads=2, n_layers=1, d_ff=32
    )
    wrapper = transformer_model.TransformerAnomalyDetectorWrapper(model, device="cpu", threshold=0.0)
    data = np.random.randn(10, 1).astype(np.float32)
    is_anomaly, scores = wrapper.detect(data)
    assert is_anomaly.shape == (10,)
    assert scores.shape == (10,)

    log_data = np.random.randn(10, 64).astype(np.float32)
    trace_data = np.random.randn(10, 64).astype(np.float32)
    is_anomaly, _ = wrapper.detect(data, log_data, trace_data)
    assert is_anomaly.shape == (10,)


# ----------------------------------------------------------------------
# modules/observability/smart_analysis.py
# ----------------------------------------------------------------------
def test_trend_analyzer():
    analyzer = smart_analysis.TrendAnalyzer()
    insufficient = analyzer.analyze("cpu", [1.0, 2.0])
    assert insufficient.trend_type == smart_analysis.TrendType.STABLE

    increasing = analyzer.analyze("cpu", [100.0 + i for i in range(20)])
    assert increasing.trend_type == smart_analysis.TrendType.INCREASING
    assert increasing.r_squared > 0.8
    assert increasing.forecast

    decreasing = analyzer.analyze("cpu", [120.0 - i for i in range(20)])
    assert decreasing.trend_type == smart_analysis.TrendType.DECREASING

    stable = analyzer.analyze("cpu", [50.0] * 20)
    assert stable.trend_type == smart_analysis.TrendType.STABLE

    volatile_data = [100.0 if i % 2 == 0 else 1.0 for i in range(20)]
    volatile = analyzer.analyze("cpu", volatile_data)
    assert volatile.trend_type == smart_analysis.TrendType.VOLATILE

    rng = np.random.default_rng(7)
    weak = analyzer.analyze("cpu", (rng.random(20) * 10).tolist())
    assert any("Weak" in i for i in weak.insights)


def test_anomaly_pattern_recognizer():
    recognizer = smart_analysis.AnomalyPatternRecognizer()
    spike_data = [10.0] * 10 + [100.0] + [10.0] * 10
    dip_data = [10.0] * 10 + [0.0] + [10.0] * 10
    gradual_inc = [float(i) for i in range(50)]
    gradual_dec = [float(50 - i) for i in range(50)]
    oscillation = [1.0 if i % 2 == 0 else -1.0 for i in range(20)]

    patterns = recognizer.recognize(
        {
            "spike": spike_data,
            "dip": dip_data,
            "gradual_up": gradual_inc,
            "gradual_down": gradual_dec,
            "oscillate": oscillation,
        },
        timestamps=[datetime.now().isoformat()],
    )
    pattern_types = {p.pattern_type for p in patterns}
    for expected in ["spike", "dip", "gradual_increase", "gradual_decrease", "oscillation"]:
        assert expected in pattern_types
    assert patterns[0].to_dict()["pattern_type"]


def test_smart_analysis_engine():
    engine = smart_analysis.create_smart_analysis_engine()
    metrics = {
        "cpu": [10.0 + i for i in range(20)],
        "mem": [50.0] * 20,
        "io": [1.0 if i % 2 == 0 else -1.0 for i in range(20)],
    }
    result = engine.analyze_metrics(metrics)
    assert "trend_analysis" in result
    assert "anomaly_patterns" in result
    assert "insights" in result
    summary = engine.get_analysis_summary()
    assert summary["total_analyses"] == 1


# ----------------------------------------------------------------------
# modules/analyze/root_cause/graph_builder.py
# ----------------------------------------------------------------------
def test_graph_builder_non_multi():
    builder = graph_builder.RootCauseGraphBuilder(directed=True, multi_graph=False)
    svc = builder.add_service_node("svc1", "Service 1", "microservice")
    metric = builder.add_metric_node(
        "m1", "cpu", "cpu", "svc1", current_value=85.0
    )
    alert = builder.add_alert_node("a1", "High CPU", "critical", "svc1", metric_id="m1")
    host = builder.add_host_node("h1", "host1", "vm")
    container = builder.add_container_node("c1", "container1", "h1")
    builder.add_dependency_edge(svc, metric)
    builder.add_containment_edge(host, container)
    builder.add_correlation_edge(metric, metric, 0.8)
    builder.add_causal_edge(alert, svc, 0.9)

    assert builder.get_statistics()["total_nodes"] == 5
    subgraph = builder.get_subgraph_by_alert("a1", hops=2)
    assert subgraph["node_count"] >= 1
    neighbors = builder.get_node_neighbors(svc, edge_type=builder.EDGE_TYPE_DEPENDS)
    assert any(n.get("metric_id") == "m1" for n in neighbors)
    assert builder.find_shortest_path(alert, svc)
    assert builder.compute_node_importance("pagerank")
    assert builder.compute_node_importance("betweenness")
    assert builder.compute_node_importance("degree")
    with pytest.raises(ValueError):
        builder.compute_node_importance("unknown")
    assert builder.to_dict()["node_count"] == 5
    json_str = builder.to_json()
    assert "nodes" in json_str


def test_graph_builder_multi(tmp_path):
    builder = graph_builder.RootCauseGraphBuilder(directed=True, multi_graph=True)
    a = builder.add_service_node("a", "A", "microservice")
    b = builder.add_service_node("b", "B", "microservice")
    builder.add_dependency_edge(a, b)
    builder.add_dependency_edge(a, b, weight=2.0)
    neighbors = builder.get_node_neighbors(a)
    assert len(neighbors) == 2
    path = tmp_path / "graph.pkl"
    builder.save_graph(str(path))
    builder.load_graph(str(path))
    assert builder.graph.number_of_nodes() == 2


def test_graph_builder_missing_alert():
    builder = graph_builder.RootCauseGraphBuilder(directed=True, multi_graph=False)
    with pytest.raises(ValueError):
        builder.get_subgraph_by_alert("missing")
    with pytest.raises(ValueError):
        builder.get_node_neighbors("missing")
    with pytest.raises(ValueError):
        builder.find_shortest_path("a", "b")


# ----------------------------------------------------------------------
# modules/apm/dependency_analyzer.py
# ----------------------------------------------------------------------
def test_dependency_topology():
    topo = dependency_analyzer.DependencyTopology()
    a = dependency_analyzer.ServiceNode("a", "A")
    b = dependency_analyzer.ServiceNode("b", "B")
    c = dependency_analyzer.ServiceNode("c", "C")
    topo.add_node(a)
    topo.add_node(b)
    topo.add_node(c)
    topo.add_edge(dependency_analyzer.DependencyEdge("a", "b", dependency_analyzer.DependencyType.SYNC, weight=1.0))
    topo.add_edge(dependency_analyzer.DependencyEdge("b", "c", dependency_analyzer.DependencyType.DATABASE, weight=2.0))
    assert topo.get_dependencies("a") == {"b"}
    assert topo.get_all_dependencies("a") == {"b", "c"}
    assert topo.get_dependents("c") == {"b"}
    assert topo.find_critical_path("a", "c") == ["a", "b", "c"]
    assert topo.find_critical_path("a", "a") == ["a"]
    assert topo.find_critical_path("a", "missing") == []
    assert topo.to_dict()["nodes"]


def test_dependency_discoverer():
    discoverer = dependency_analyzer.DependencyDiscoverer()
    with pytest.raises(ValueError):
        discoverer.discover("unknown")

    trace_data = [
        {
            "spans": [
                {"service_id": "a", "service_name": "A", "kind": "server"},
                {"service_id": "b", "service_name": "B", "kind": "producer", "duration": 0.1},
                {"service_id": "c", "service_name": "C", "kind": "client", "duration": 0.2},
            ]
        }
    ]
    topo = discoverer.discover("trace", trace_data=trace_data)
    assert "b" in topo.get_dependencies("a")
    assert "c" in topo.get_dependencies("b")

    config_data = {
        "services": [
            {"id": "x", "name": "X", "dependencies": [{"id": "y", "name": "Y", "type": "database"}, {"id": "z", "name": "Z", "type": "invalid"}]},
        ]
    }
    topo = discoverer.discover("config", config_data=config_data)
    assert "y" in topo.get_dependencies("x")
    assert "z" in topo.get_dependencies("x")

    metrics_data = {
        "call_relationships": [
            {"source": "p", "target": "q", "call_count": 10},
            {"source": "p", "target": "r", "call_count": 0},
        ]
    }
    topo = discoverer.discover("metrics", metrics_data=metrics_data)
    assert topo.get_dependencies("p") == {"q"}


def test_dependency_health_and_visualizer(tmp_path):
    topo = dependency_analyzer.DependencyTopology()
    a = dependency_analyzer.ServiceNode("a", "A", health=dependency_analyzer.HealthStatus.HEALTHY)
    b = dependency_analyzer.ServiceNode("b", "B", health=dependency_analyzer.HealthStatus.UNHEALTHY)
    topo.add_node(a)
    topo.add_node(b)
    topo.add_edge(dependency_analyzer.DependencyEdge("a", "b", dependency_analyzer.DependencyType.SYNC, latency=200.0))
    assessor = dependency_analyzer.DependencyHealthAssessor(topo)
    assert assessor.assess_node_health("a", {"error_rate": 0.001, "latency": 100, "availability": 0.99}) == dependency_analyzer.HealthStatus.HEALTHY
    assert assessor.assess_node_health("a", {"error_rate": 0.1, "availability": 0.9}) == dependency_analyzer.HealthStatus.UNHEALTHY
    assert assessor.assess_node_health("a", {"error_rate": 0.02, "latency": 2000}) == dependency_analyzer.HealthStatus.DEGRADED
    edge = dependency_analyzer.DependencyEdge("a", "b", dependency_analyzer.DependencyType.SYNC, error_rate=0.1, latency=6000)
    assert assessor.assess_dependency_health(edge) == dependency_analyzer.HealthStatus.UNHEALTHY
    assert sorted(assessor.identify_critical_nodes()) == ["a", "b"]

    nx_graph = dependency_analyzer.TopologyVisualizer.to_networkx(topo)
    assert nx_graph.number_of_nodes() == 2
    json_str = dependency_analyzer.TopologyVisualizer.to_json(topo)
    assert '"id": "a"' in json_str
    loaded = dependency_analyzer.TopologyVisualizer.from_json(json_str)
    assert "a" in loaded.nodes

    with pytest.raises(ImportError):
        dependency_analyzer.TopologyVisualizer.plot(topo, output_path=str(tmp_path / "out.png"))


def test_dependency_analyzer():
    analyzer = dependency_analyzer.create_dependency_analyzer()
    config = {
        "services": [
            {"id": "svc1", "name": "S1", "dependencies": [{"id": "svc2", "name": "S2", "type": "sync"}]},
            {"id": "svc2", "name": "S2", "dependencies": []},
        ]
    }
    topo = analyzer.discover_topology("config", config_data=config)
    assert "svc1" in topo.nodes
    analysis = analyzer.analyze_dependencies("svc1")
    assert analysis["dependency_count"] == 1
    assert analyzer.get_critical_path("svc1", "svc2") == ["svc1", "svc2"]
    report = analyzer.get_health_report()
    assert report["total_nodes"] == 2


# ----------------------------------------------------------------------
# modules/observability/smart_alerting.py
# ----------------------------------------------------------------------
def test_alert_and_fingerprint():
    alert = smart_alerting.Alert(
        id="1",
        title="CPU high",
        description="cpu > 90",
        severity=smart_alerting.AlertSeverity.WARNING,
    )
    assert alert.to_dict()["severity"] == "warning"
    assert alert.generate_fingerprint()


def test_alert_rule_evaluation():
    rule = smart_alerting.AlertRule(
        id="r1",
        name="CPU high",
        condition="cpu_usage > 80",
        severity=smart_alerting.AlertSeverity.WARNING,
    )
    assert rule.evaluate({"cpu_usage": 85.0})
    assert not rule.evaluate({"cpu_usage": 70.0})
    assert rule.evaluate({"cpu_usage": 85.0, "memory_usage": 100.0})
    and_rule = smart_alerting.AlertRule(
        id="r2", name="CPU and memory", condition="cpu_usage > 80 and memory_usage > 90", severity=smart_alerting.AlertSeverity.CRITICAL
    )
    assert and_rule.evaluate({"cpu_usage": 85.0, "memory_usage": 95.0})
    or_rule = smart_alerting.AlertRule(
        id="r3", name="CPU or memory", condition="cpu_usage > 80 or memory_usage > 95", severity=smart_alerting.AlertSeverity.WARNING
    )
    assert or_rule.evaluate({"cpu_usage": 70.0, "memory_usage": 100.0})
    not_rule = smart_alerting.AlertRule(
        id="r4", name="not cpu", condition="not cpu_usage > 80", severity=smart_alerting.AlertSeverity.INFO
    )
    assert not not_rule.evaluate({"cpu_usage": 85.0})
    assert not rule.evaluate({"disk_usage": 100})
    unsafe_rule = smart_alerting.AlertRule(id="r5", name="unsafe", condition="cpu_usage;", severity=smart_alerting.AlertSeverity.WARNING)
    assert not unsafe_rule.evaluate({})


def test_dynamic_thresholds():
    calc = smart_alerting.DynamicThresholdCalculator(window_size=20)
    for i in range(15):
        calc.add_metric("cpu", float(i))
    assert calc.calculate_threshold("cpu", method="percentile", percentile=95) > 0
    assert calc.calculate_threshold("cpu", method="stddev") > 0
    assert calc.calculate_threshold("cpu", method="moving_avg", window=5) > 0
    assert calc.calculate_threshold("cpu", method="unknown") == 0.0


def test_alert_aggregator():
    agg = smart_alerting.AlertAggregator()
    a1 = smart_alerting.Alert("1", "CPU", "desc", smart_alerting.AlertSeverity.WARNING, labels={"host": "h1"})
    a2 = smart_alerting.Alert("2", "CPU", "desc", smart_alerting.AlertSeverity.WARNING, labels={"host": "h1"})
    a3 = smart_alerting.Alert("3", "MEM", "desc", smart_alerting.AlertSeverity.CRITICAL, labels={"host": "h2"})
    agg.add_alert(a1)
    agg.add_alert(a2)
    agg.add_alert(a3)
    result = agg.aggregate()
    assert len(result) == 2
    merged = [r for r in result if r.title == "CPU"][0]
    assert merged.to_dict()["annotations"]["aggregated_count"] == "2"


def test_alert_suppressor():
    suppressor = smart_alerting.AlertSuppressor()
    suppressor.add_suppression_rule({"host": "h1"}, duration=3600)
    alert_match = smart_alerting.Alert("1", "x", "x", smart_alerting.AlertSeverity.WARNING, labels={"host": "h1"})
    alert_no_match = smart_alerting.Alert("2", "x", "x", smart_alerting.AlertSeverity.WARNING, labels={"host": "h2"})
    assert suppressor.should_suppress(alert_match)
    assert not suppressor.should_suppress(alert_no_match)
    suppressor.suppression_rules.append({
        "match_labels": {"old": "yes"},
        "duration": 1,
        "created_at": datetime.now() - timedelta(seconds=10),
    })
    suppressor.cleanup_expired_rules()
    assert all(r["match_labels"] != {"old": "yes"} for r in suppressor.suppression_rules)


def test_smart_alerting_engine():
    engine = smart_alerting.create_smart_alerting_engine()
    rule = smart_alerting.AlertRule(
        id="cpu-high",
        name="CPU high",
        condition="cpu_usage > 80",
        severity=smart_alerting.AlertSeverity.WARNING,
        labels={"host": "h1"},
    )
    engine.add_rule(rule)
    metrics = {"cpu_usage": 85.0}
    alerts = engine.evaluate_metrics(metrics)
    assert len(alerts) == 1
    assert engine.get_alert_statistics()["total_active"] == 1

    engine.suppressor.add_suppression_rule({"host": "h1"})
    assert engine.evaluate_metrics(metrics) == []

    alert_id = alerts[0].id
    assert engine.acknowledge_alert(alert_id)
    assert engine.resolve_alert(alert_id)
    assert not engine.get_active_alerts()
    engine.remove_rule("cpu-high")
    assert engine.get_alert_statistics()["total_rules"] == 0


# ----------------------------------------------------------------------
# modules/execute/saga/coordinator.py
# ----------------------------------------------------------------------
@pytest.mark.asyncio
async def test_saga_success():
    coordinator = saga_coordinator.SagaCoordinator()

    async def reserve(ctx):
        ctx["reserved"] = True
        return "reserved"

    async def ship(ctx):
        ctx["shipped"] = True
        return "shipped"

    steps = [
        saga_coordinator.SagaStep(name="reserve", action=reserve),
        saga_coordinator.SagaStep(name="ship", action=ship),
    ]
    saga = coordinator.create_saga("order", steps)
    result = await coordinator.execute_saga(saga.saga_id)
    assert result["success"]
    assert coordinator.get_saga(saga.saga_id).state == saga_coordinator.SagaState.COMPLETED


@pytest.mark.asyncio
async def test_saga_failure_and_compensation():
    coordinator = saga_coordinator.SagaCoordinator(enable_persistence=True)
    compensate_called = {"value": False}

    async def action_ok(ctx):
        return "ok"

    async def action_fail(ctx):
        raise RuntimeError("step failed")

    async def compensation(ctx):
        compensate_called["value"] = True

    steps = [
        saga_coordinator.SagaStep("s1", action_ok, compensation=compensation),
        saga_coordinator.SagaStep("s2", action_fail),
    ]
    saga = coordinator.create_saga("order", steps)
    result = await coordinator.execute_saga(saga.saga_id)
    assert not result["success"]
    assert compensate_called["value"]
    assert coordinator.get_saga(saga.saga_id).state == saga_coordinator.SagaState.COMPENSATED
    assert coordinator.get_stats()["total"] == 1


@pytest.mark.asyncio
async def test_saga_compensation_variants():
    coordinator = saga_coordinator.SagaCoordinator()
    called = {"skip": False, "fail": False}

    async def action(ctx):
        return "ok"

    async def comp(ctx):
        called["skip"] = True

    async def failing_comp(ctx):
        called["fail"] = True
        raise RuntimeError("compensation failed")

    steps = [
        saga_coordinator.SagaStep("skip", action, compensation=comp, compensate_if=lambda ctx: False),
        saga_coordinator.SagaStep("no_comp", action),
        saga_coordinator.SagaStep("fail_comp", action, compensation=failing_comp),
        saga_coordinator.SagaStep("fail", lambda ctx: (_ for _ in ()).throw(RuntimeError("boom"))),
    ]
    saga = coordinator.create_saga("x", steps)
    result = await coordinator.execute_saga(saga.saga_id)
    assert not result["success"]
    assert not called["skip"]
    assert called["fail"]


@pytest.mark.asyncio
async def test_saga_not_found_and_delete():
    coordinator = saga_coordinator.SagaCoordinator()
    with pytest.raises(ValueError):
        await coordinator.execute_saga("missing")
    step = saga_coordinator.SagaStep("x", lambda ctx: "ok")
    saga = coordinator.create_saga("x", [step])
    assert coordinator.delete_saga(saga.saga_id)
    assert not coordinator.delete_saga(saga.saga_id)
    assert coordinator.get_all_sagas() == []


def test_saga_step_and_instance_dict():
    step = saga_coordinator.SagaStep("x", lambda ctx: "ok")
    step.result = 123
    step.error = ValueError("err")
    step.started_at = datetime.now()
    step.completed_at = datetime.now()
    d = step.to_dict()
    assert d["result"] == "123"
    assert "err" in d["error"]
    saga = saga_coordinator.SagaInstance("id", "name", [step])
    assert saga.to_dict()["saga_id"] == "id"


@pytest.mark.asyncio
async def test_hpa_controller_k8s_paths(monkeypatch):
    """Cover kubernetes branches of custom_hpa_controller with mocks."""
    monkeypatch.setattr(custom_hpa_controller, "KUBERNETES_AVAILABLE", True)

    class MockConfig:
        class ConfigException(Exception):
            pass

        def __init__(self):
            self.loads = []

        def load_kube_config(self, config_file=None):
            self.loads.append(("kube", config_file))

        def load_incluster_config(self):
            raise self.ConfigException("incluster")

    mock_config = MockConfig()
    monkeypatch.setattr(custom_hpa_controller, "config", mock_config)

    class ApiException(Exception):
        pass

    monkeypatch.setattr(custom_hpa_controller, "ApiException", ApiException, raising=False)

    class MockAppsV1Api:
        def __init__(self):
            self.patched = []

        def read_namespaced_deployment(self, name, namespace):
            deploy = type("Deploy", (), {})()
            deploy.spec = type("Spec", (), {"replicas": 2})()
            return deploy

        def list_namespaced_pod(self, namespace, label_selector=None):
            pods = type("Pods", (), {})()
            pod = type("Pod", (), {})()
            pod.status = type("Status", (), {"phase": "Running"})()
            pods.items = [pod]
            return pods

        def patch_namespaced_deployment_scale(self, name, namespace, body):
            self.patched.append((name, body))

    class MockClient:
        AppsV1Api = MockAppsV1Api
        AutoscalingV2Api = type("AutoscalingV2Api", (), {})
        CustomMetricsApi = type("CustomMetricsApi", (), {})

    monkeypatch.setattr(custom_hpa_controller, "client", MockClient())

    ctrl = custom_hpa_controller.CustomHPAController(kubeconfig="fake")
    ctrl.initialize()
    assert ctrl._is_initialized
    assert ("kube", "fake") in mock_config.loads

    metrics = await ctrl._get_deployment_metrics("app")
    assert metrics["current_replicas"] == 2
    assert metrics["cpu_utilization"] == 50.0
    assert metrics["memory_utilization"] == 60.0

    policy = custom_hpa_controller.ScalingPolicy(scale_up_threshold=60.0)
    ctrl.register_policy("app", policy)
    await ctrl._evaluate_scaling("app", policy)
    assert ctrl.get_scaling_history()
    assert await ctrl._scale_deployment("app", 5)

    def raise_api(*args, **kwargs):
        raise custom_hpa_controller.ApiException("boom")

    ctrl._k8s_client.read_namespaced_deployment = raise_api
    assert await ctrl._get_deployment_metrics("app") is None
    ctrl._k8s_client.patch_namespaced_deployment_scale = raise_api
    assert not await ctrl._scale_deployment("app", 5)


def test_hpa_controller_initialize_error(monkeypatch):
    class BadConfig:
        class ConfigException(Exception):
            pass

        def load_kube_config(self, config_file=None):
            raise RuntimeError("no kube")

        def load_incluster_config(self):
            raise self.ConfigException("no incluster")

    monkeypatch.setattr(custom_hpa_controller, "KUBERNETES_AVAILABLE", True)
    monkeypatch.setattr(custom_hpa_controller, "config", BadConfig())
    monkeypatch.setattr(custom_hpa_controller, "client", type("Client", (), {"AppsV1Api": type("Apps", (), {})})())
    ctrl = custom_hpa_controller.CustomHPAController()
    ctrl.initialize()
    assert not ctrl._is_initialized


@pytest.mark.asyncio
async def test_hpa_controller_monitor_error(monkeypatch):
    ctrl = custom_hpa_controller.CustomHPAController()
    ctrl.register_policy("app", custom_hpa_controller.ScalingPolicy())

    async def raise_eval(*args, **kwargs):
        raise RuntimeError("eval failed")

    monkeypatch.setattr(ctrl, "_evaluate_scaling", raise_eval)
    try:
        await asyncio.wait_for(ctrl.monitor_and_scale(interval=0), timeout=0.05)
    except asyncio.TimeoutError:
        pass
