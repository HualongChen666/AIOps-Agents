# -*- coding: utf-8 -*-
"""Coverage tests for batch 19a core modules."""

import asyncio
import logging
from datetime import datetime
from unittest.mock import MagicMock

import pytest

pytestmark = [pytest.mark.core]

import core.telemetry_core as tc
from core.frontend_enhancement import (
    DashboardWidget,
    FrontendEnhancementManager,
    ReportTemplate,
    ThemeType,
    UserPreference,
    ViewMode,
    frontend_enhancement_manager,
)
from core.integration_documentation_manager import (
    IntegrationDiagram,
    IntegrationDocStatus,
    IntegrationDocType,
    IntegrationDocumentation,
    IntegrationDocumentationManager,
    get_integration_documentation_manager,
)
from core.kafka_stream_processor import (
    BackpressureController,
    DataQualityValidator,
    KafkaMessage,
    KafkaStreamProcessor,
    TokenBucket,
    data_quality_validator,
    get_backpressure_controller,
    get_data_quality_validator,
    get_kafka_processor,
    get_token_bucket,
    kafka_processor,
)
from core.logging.level.level_manager import LogLevel
from core.logging.level.routing_strategy import (
    ConditionalRouter,
    FileRouter,
    LogLevelRouter,
    SystemRouter,
)
from core.telemetry_core import (
    get_apm_metrics,
    get_meter,
    get_tracer,
    initialize_telemetry,
    instrument_asyncpg,
    instrument_fastapi,
    instrument_httpx,
    instrument_redis,
    record_apm_metric,
    reset_apm_metrics,
    shutdown_telemetry,
    trace_operation,
)


# ---------------------------------------------------------------------------
# integration_documentation_manager
# ---------------------------------------------------------------------------
def test_integration_doc_defaults_and_factory(tmp_path):
    config = {"docs_dir": str(tmp_path / "integration_docs")}
    manager = IntegrationDocumentationManager(config)
    assert "architecture_overview" in manager.integration_docs
    assert "system_architecture" in manager.integration_diagrams
    assert manager.docs_dir.is_dir()
    assert get_integration_documentation_manager(config)


def test_integration_doc_register_and_get(tmp_path):
    manager = IntegrationDocumentationManager({"docs_dir": str(tmp_path / "docs")})
    doc = IntegrationDocumentation(
        doc_id="d1",
        doc_name="Doc One",
        doc_type=IntegrationDocType.API_REFERENCE,
        component="api",
        content="hello",
    )
    manager.register_documentation(doc)
    assert manager.get_documentation("d1")["doc_name"] == "Doc One"
    assert manager.get_documentation("missing") is None

    diagram = IntegrationDiagram(
        diagram_id="dg1",
        diagram_name="Diagram One",
        diagram_type="flow",
        component="api",
    )
    manager.register_diagram(diagram)
    assert manager.get_diagram("dg1")["diagram_name"] == "Diagram One"
    assert manager.get_diagram("missing") is None


def test_integration_doc_list_and_filter(tmp_path):
    manager = IntegrationDocumentationManager({"docs_dir": str(tmp_path / "docs")})
    docs = manager.list_documentation()
    assert all(isinstance(d, dict) for d in docs)
    assert len(manager.list_documentation(doc_type=IntegrationDocType.ARCHITECTURE)) >= 1
    assert len(manager.list_documentation(component="api")) >= 1
    assert len(manager.list_documentation(status=IntegrationDocStatus.PUBLISHED)) >= 1


def test_integration_doc_async_generate(tmp_path):
    manager = IntegrationDocumentationManager({"docs_dir": str(tmp_path / "docs")})
    arch_id = asyncio.run(manager.generate_architecture_docs())
    flow_id = asyncio.run(manager.generate_data_flow_docs())
    assert arch_id in manager.integration_docs
    assert flow_id in manager.integration_docs
    assert (tmp_path / "docs" / f"{arch_id}.md").exists()
    assert (tmp_path / "docs" / f"{flow_id}.md").exists()
    assert manager.total_docs >= 2
    assert manager.published_docs >= 2


def test_integration_doc_update(tmp_path):
    manager = IntegrationDocumentationManager({"docs_dir": str(tmp_path / "docs")})
    assert asyncio.run(manager.update_documentation("architecture_overview", "new content")) is True
    assert manager.get_documentation("architecture_overview")["updated_at"] is not None
    assert asyncio.run(manager.update_documentation("missing", "x")) is False


def test_integration_doc_statistics(tmp_path):
    manager = IntegrationDocumentationManager({"docs_dir": str(tmp_path / "docs")})
    stats = manager.get_statistics()
    assert "total_docs" in stats
    assert "published_docs" in stats
    assert "draft_docs" in stats
    assert "total_diagrams" in stats
    assert "by_type" in stats


# ---------------------------------------------------------------------------
# kafka_stream_processor
# ---------------------------------------------------------------------------
def test_kafka_offline_send_consume_clear():
    processor = KafkaStreamProcessor()
    processor.register_handler("metrics-topic", lambda msg: None)
    assert processor.send_message("metrics-topic", "k1", {"v": 1}) is True
    cached = processor.get_cached_messages()
    assert any(m.key == "k1" for m in cached)

    consumed = list(processor.consume_messages("metrics-topic", "g1"))
    assert any(m.key == "k1" for m in consumed)

    processor.clear_stub_messages()
    assert processor.get_stub_messages() == []


def test_kafka_real_producer_send(monkeypatch):
    monkeypatch.setattr("core.kafka_stream_processor.KAFKA_AVAILABLE", True)
    processor = KafkaStreamProcessor()
    producer = MagicMock()
    processor.producer = producer
    assert processor.send_message("metrics-topic", "k1", {"v": 1}) is True
    producer.send.assert_called_once()

    producer.send.side_effect = RuntimeError("boom")
    assert processor.send_message("metrics-topic", "k2", {"v": 2}) is False


def _make_record(topic, value, key=None, headers=None):
    rec = MagicMock()
    rec.value = value
    rec.key = key or b"rk"
    rec.headers = headers or []
    return rec


def _make_topic(topic):
    t = MagicMock()
    t.topic = topic
    return t


def test_kafka_real_consumer_consume(monkeypatch):
    monkeypatch.setattr("core.kafka_stream_processor.KAFKA_AVAILABLE", True)
    processor = KafkaStreamProcessor()
    consumer = MagicMock()
    consumer.subscribe = MagicMock()
    first_batch = {
        _make_topic("metrics-topic"): [
            _make_record("metrics-topic", b'{"value": 1}'),
            _make_record("metrics-topic", b"not-json"),
            _make_record("metrics-topic", {"raw": "data"}),
        ]
    }

    calls = [0]

    def _poll(*args, **kwargs):
        calls[0] += 1
        return first_batch if calls[0] == 1 else {}

    consumer.poll.side_effect = _poll
    processor.consumer = consumer

    msgs = list(processor.consume_messages("metrics-topic", "g1"))
    assert len(msgs) == 3
    assert msgs[0].value == {"value": 1}
    assert msgs[1].value == b"not-json"
    assert msgs[2].value == {"raw": "data"}


def test_kafka_real_consumer_exception_fallback(monkeypatch):
    monkeypatch.setattr("core.kafka_stream_processor.KAFKA_AVAILABLE", True)
    processor = KafkaStreamProcessor()
    consumer = MagicMock()
    consumer.subscribe.side_effect = RuntimeError("kafka down")
    processor.consumer = consumer
    processor.send_message("metrics-topic", "k3", {"v": 3})
    msgs = list(processor.consume_messages("metrics-topic", "g1"))
    assert any(m.key == "k3" for m in msgs)


def test_backpressure_controller():
    bp = BackpressureController(threshold=0.5, max_backoff=60)
    assert bp.check_backpressure(0.1) is False
    for _ in range(10):
        bp.check_backpressure(0.9)
    assert bp.check_backpressure(0.9) is True
    assert bp.get_backoff_delay() >= 0

    for _ in range(120):
        bp.check_backpressure(0.9)
    assert len(bp.load_history) <= 100


def test_token_bucket():
    tb = TokenBucket(capacity=5, rate=1.0)
    assert tb.consume(1) is True
    assert tb.consume(5) is False
    assert tb.get_available_tokens() >= 0


def test_data_quality_validator():
    dv = DataQualityValidator()
    dv.register_validator("metrics", lambda data: "value" in data)
    assert dv.validate({"value": 1}, "metrics") is True
    assert dv.validate({"other": 1}, "metrics") is False
    dv.register_validator("broken", lambda data: 1 / 0)
    assert dv.validate({}, "broken") is False
    assert dv.validate({"x": 1}, "unknown") is True

    stats = dv.get_validation_stats()
    assert "valid_rate" in stats
    assert stats["total_validations"] > 0


def test_kafka_global_getters():
    assert isinstance(get_kafka_processor(), KafkaStreamProcessor)
    assert isinstance(get_backpressure_controller(), BackpressureController)
    assert isinstance(get_token_bucket(), TokenBucket)
    assert isinstance(get_data_quality_validator(), DataQualityValidator)


# ---------------------------------------------------------------------------
# logging/level/routing_strategy
# ---------------------------------------------------------------------------
def _record(level):
    return logging.LogRecord(
        name="test",
        level=level,
        pathname="",
        lineno=0,
        msg="test message",
        args=(),
        exc_info=None,
    )


def test_log_level_router():
    router = LogLevelRouter(
        level_routes={LogLevel.INFO: ["console"]},
        default_routes=["file"],
    )
    assert router.route(_record(logging.INFO)) == ["console"]
    assert router.route(_record(logging.ERROR)) == ["file"]

    router.add_level_route(LogLevel.ERROR, ["email"])
    assert router.route(_record(logging.ERROR)) == ["email"]
    router.remove_level_route(LogLevel.ERROR)
    assert router.route(_record(logging.ERROR)) == ["file"]
    router.set_default_routes(["default"])
    assert router.route(_record(logging.WARNING)) == ["default"]


def test_file_router(tmp_path):
    log_dir = str(tmp_path / "logs")
    router = FileRouter(base_dir=log_dir)
    assert router.route(_record(logging.INFO)) == [str(tmp_path / "logs" / "app.log")]

    router.set_level_file(LogLevel.ERROR, "error.log")
    assert router.get_file_path(LogLevel.ERROR).endswith("error.log")
    assert router.get_file_path(LogLevel.INFO).endswith("app.log")
    router.set_default_file("default.log")
    assert router.get_file_path(LogLevel.INFO).endswith("default.log")
    assert router.route(_record(logging.INFO)) == [router.get_file_path(LogLevel.INFO)]


def test_system_router():
    router = SystemRouter(default_systems=["syslog"])
    router.add_system_route("elk", LogLevel.INFO)
    router.add_system_route("elk", LogLevel.ERROR, enabled=True)
    assert "elk" in router.route(_record(logging.INFO))
    assert "elk" in router.route(_record(logging.ERROR))
    assert router.route(_record(logging.WARNING)) == ["syslog"]

    router.remove_system_route("elk", LogLevel.INFO)
    assert router.route(_record(logging.INFO)) == ["syslog"]

    router.set_default_systems(["cloudwatch"])
    assert router.route(_record(logging.CRITICAL)) == ["cloudwatch"]

    router.set_system_config("elk", {"host": "localhost"})
    assert router.get_system_config("elk") == {"host": "localhost"}
    assert router.get_system_config("missing") is None


def test_conditional_router():
    router = ConditionalRouter(default_routes=["fallback"])
    router.add_condition(lambda r: r.levelno == logging.INFO, ["info-target"])
    router.add_condition(lambda r: True, [])
    assert router.route(_record(logging.INFO)) == ["info-target"]
    assert router.route(_record(logging.ERROR)) == ["fallback"]
    router.set_default_routes(["new-fallback"])
    assert router.route(_record(logging.ERROR)) == ["new-fallback"]


# ---------------------------------------------------------------------------
# frontend_enhancement
# ---------------------------------------------------------------------------
def test_user_preferences():
    mgr = FrontendEnhancementManager()
    pref = mgr.get_user_preferences("u1")
    assert isinstance(pref, UserPreference)

    updated = mgr.update_user_preferences("u1", {"language": "en-US", "theme": ThemeType.DARK})
    assert updated.language == "en-US"
    assert updated.theme == ThemeType.DARK

    exported = mgr.export_user_preferences("u1")
    assert exported["user_id"] == "u1"
    assert exported["language"] == "en-US"

    imported = mgr.import_user_preferences(
        "u2",
        {
            "theme": "dark",
            "view_mode": "list",
            "language": "fr-FR",
        },
    )
    assert imported.theme == ThemeType.DARK
    assert imported.view_mode == ViewMode.LIST


def test_theme_management():
    mgr = FrontendEnhancementManager()
    light = mgr.get_theme_config(ThemeType.LIGHT)
    assert "primary_color" in light
    assert mgr.get_theme_config(ThemeType.CUSTOM) == light

    custom = mgr.create_custom_theme("c1", "My Theme", {"primary_color": "#000"})
    assert custom["theme_id"] == "c1"
    assert mgr.get_theme_config(ThemeType.LIGHT)["primary_color"] != "#000"


def test_dashboard_management():
    mgr = FrontendEnhancementManager()
    widgets = mgr.get_dashboard_config("dash1")
    assert len(widgets) == 4

    widget = DashboardWidget(
        widget_id="w1",
        widget_type="test",
        title="Test",
        position={"x": 0, "y": 0, "width": 1, "height": 1},
    )
    mgr.add_dashboard_widget("dash1", widget)
    assert len(mgr.get_dashboard_config("dash1")) == 5

    assert mgr.update_dashboard_widget("dash1", "w1", {"title": "Updated"}) is not None
    assert mgr.update_dashboard_widget("dash1", "missing", {}) is None
    assert mgr.update_dashboard_widget("missing", "w1", {}) is None

    assert mgr.remove_dashboard_widget("dash1", "w1") is True
    assert mgr.remove_dashboard_widget("missing", "w1") is False


def test_report_templates():
    mgr = FrontendEnhancementManager()
    template = mgr.create_report_template(
        template_id="r1",
        name="Daily",
        description="Daily report",
        data_sources=["metrics", "alerts", "topology"],
        visualization_config={"type": "bar"},
        format="csv",
        schedule="0 0 * * *",
    )
    assert isinstance(template, ReportTemplate)

    report = mgr.generate_report("r1", {"start": "2026-01-01"})
    assert report["template_id"] == "r1"
    assert report["filters"]["start"] == "2026-01-01"
    assert "metrics" in report["data"]

    assert "error" in mgr.generate_report("missing", {})


def test_responsive_and_accessibility():
    mgr = FrontendEnhancementManager()
    assert mgr.get_responsive_config(0)["grid_columns"] == 1
    assert mgr.get_responsive_config(700)["grid_columns"] == 2
    assert mgr.get_responsive_config(800)["grid_columns"] == 2
    assert mgr.get_responsive_config(1100)["grid_columns"] == 3
    assert mgr.get_responsive_config(1300)["grid_columns"] == 4
    assert mgr.get_responsive_config(2000)["grid_columns"] == 4

    mgr.update_accessibility_settings("u3", {"high_contrast": True})
    assert mgr.get_accessibility_settings("u3") == {"high_contrast": True}


def test_frontend_summary():
    mgr = FrontendEnhancementManager()
    summary = mgr.get_frontend_summary()
    assert "user_preferences_count" in summary
    assert "dashboard_configs_count" in summary
    assert "report_templates_count" in summary
    assert "available_themes" in summary


def test_frontend_global_instance():
    assert isinstance(frontend_enhancement_manager, FrontendEnhancementManager)


# ---------------------------------------------------------------------------
# telemetry_core
# ---------------------------------------------------------------------------
def _patch_telemetry(monkeypatch):
    """Helper to make telemetry_core believe OpenTelemetry is available."""
    monkeypatch.setattr(tc, "OTEL_AVAILABLE", True)
    monkeypatch.setattr(tc, "_tracer_provider", MagicMock(), raising=False)
    monkeypatch.setattr(tc, "_meter_provider", MagicMock(), raising=False)
    monkeypatch.setattr(tc, "trace", MagicMock(name="trace"), raising=False)
    monkeypatch.setattr(tc, "metrics", MagicMock(name="metrics"), raising=False)
    monkeypatch.setattr(tc, "TracerProvider", MagicMock(name="TracerProvider"), raising=False)
    monkeypatch.setattr(tc, "MeterProvider", MagicMock(name="MeterProvider"), raising=False)
    monkeypatch.setattr(tc, "Resource", MagicMock(name="Resource"), raising=False)
    monkeypatch.setattr(tc, "OTLPSpanExporter", MagicMock(name="OTLPSpanExporter"), raising=False)
    monkeypatch.setattr(
        tc, "OTLPMetricExporter", MagicMock(name="OTLPMetricExporter"), raising=False
    )
    monkeypatch.setattr(
        tc, "BatchSpanProcessor", MagicMock(name="BatchSpanProcessor"), raising=False
    )
    monkeypatch.setattr(
        tc, "ConsoleSpanExporter", MagicMock(name="ConsoleSpanExporter"), raising=False
    )
    monkeypatch.setattr(
        tc,
        "PeriodicExportingMetricReader",
        MagicMock(name="PeriodicExportingMetricReader"),
        raising=False,
    )
    monkeypatch.setattr(
        tc, "FastAPIInstrumentor", MagicMock(name="FastAPIInstrumentor"), raising=False
    )
    monkeypatch.setattr(
        tc, "HTTPXClientInstrumentor", MagicMock(name="HTTPXClientInstrumentor"), raising=False
    )
    monkeypatch.setattr(
        tc, "AsyncPGInstrumentor", MagicMock(name="AsyncPGInstrumentor"), raising=False
    )
    monkeypatch.setattr(tc, "RedisInstrumentor", MagicMock(name="RedisInstrumentor"), raising=False)


def test_telemetry_not_available():
    assert tc.OTEL_AVAILABLE is False
    assert initialize_telemetry() is False
    assert get_tracer("test") is None
    assert get_meter("test") is None
    instrument_fastapi(None)
    instrument_httpx()
    instrument_asyncpg()
    instrument_redis()
    shutdown_telemetry()
    with trace_operation(None, "op") as span:
        assert span is None


def test_telemetry_initialize_and_use(monkeypatch):
    _patch_telemetry(monkeypatch)
    assert initialize_telemetry() is True
    assert get_tracer("test") is tc.trace.get_tracer.return_value
    assert get_meter("test") is tc.metrics.get_meter.return_value

    tracer = get_tracer("test")
    span = MagicMock()
    tracer.start_as_current_span.return_value.__enter__.return_value = span
    with trace_operation(tracer, "op", key="value") as s:
        assert s is span

    instrument_fastapi(MagicMock())
    instrument_httpx()
    instrument_asyncpg()
    instrument_redis()
    shutdown_telemetry()


def test_telemetry_initialize_failure(monkeypatch):
    _patch_telemetry(monkeypatch)
    tc.Resource.create.side_effect = RuntimeError("resource error")
    assert initialize_telemetry() is False


def test_telemetry_otlp_span_exporter_fallback(monkeypatch):
    _patch_telemetry(monkeypatch)
    tc.OTLPSpanExporter.side_effect = RuntimeError("export error")
    assert initialize_telemetry(enable_console_export=True) is True
    tc.ConsoleSpanExporter.assert_called_once()


def test_apm_metrics(monkeypatch):
    _patch_telemetry(monkeypatch)
    reset_apm_metrics()

    # make meter return a mock with counter.add
    meter = MagicMock()
    tc.metrics.get_meter.return_value = meter
    tc._meter_provider = MagicMock()
    record_apm_metric("request_count", 10)
    record_apm_metric("error_count", 2, {"service": "api"})
    record_apm_metric("slow_request_count", 1, {"service": "api"})

    metrics = get_apm_metrics()
    assert metrics["request_count"] == 10
    assert metrics["error_count"] == 2
    assert metrics["slow_request_count"] == 1
    assert "%" in metrics["error_rate"]
    assert "%" in metrics["slow_request_rate"]

    tc._apm_metrics["request_count"] = None
    record_apm_metric("request_count", 1)
    assert tc._apm_metrics["request_count"] == 1

    reset_apm_metrics()
    assert get_apm_metrics()["request_count"] == 0


def test_apm_metric_otel_exception(monkeypatch):
    _patch_telemetry(monkeypatch)
    reset_apm_metrics()
    tc.metrics.get_meter.side_effect = RuntimeError("meter error")
    tc._meter_provider = MagicMock()
    record_apm_metric("request_count", 5)
    assert get_apm_metrics()["request_count"] == 5
