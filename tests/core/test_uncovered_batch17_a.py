# -*- coding: utf-8 -*-
"""Functional coverage tests for core batch 17-a modules."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

import core.business_metrics as business_metrics
import core.compliance_manager as compliance_manager
import core.l1l2_data_flow_integrator as l1l2_data_flow
import core.module_health_check as module_health_check
import core.plugin_marketplace_manager as plugin_marketplace

pytestmark = [pytest.mark.core]


# ---------------------------------------------------------------------------
# core.module_health_check
# ---------------------------------------------------------------------------
@pytest.fixture
def patch_db(monkeypatch):
    session = AsyncMock()
    session.execute = AsyncMock()
    factory = MagicMock()
    factory.return_value.__aenter__ = AsyncMock(return_value=session)
    factory.return_value.__aexit__ = AsyncMock(return_value=False)
    monkeypatch.setattr("core.db_engine.AsyncSessionLocal", factory)
    return factory


@pytest.fixture
def patch_redis(monkeypatch):
    client = MagicMock()
    client.ping.return_value = True
    monkeypatch.setattr("redis.Redis", client)
    return client


@pytest.fixture
def patch_ai(monkeypatch):
    router = MagicMock()
    monkeypatch.setattr("core.ai_engine.get_llm_router", router)
    return router


async def test_database_health_success(patch_db):
    checker = module_health_check.DatabaseModuleHealth()
    result = await checker.health_check()
    assert result["module"] == "database"
    assert result["status"] == "healthy"
    assert result["message"] == "Database connection successful"


async def test_database_health_failure(monkeypatch):
    factory = MagicMock(side_effect=Exception("db down"))
    monkeypatch.setattr("core.db_engine.AsyncSessionLocal", factory)
    checker = module_health_check.DatabaseModuleHealth()
    result = await checker.health_check()
    assert result["module"] == "database"
    assert result["status"] == "unhealthy"
    assert "db down" in result["error"]


async def test_redis_health_success(patch_redis):
    checker = module_health_check.RedisModuleHealth()
    result = await checker.health_check()
    assert result["module"] == "redis"
    assert result["status"] == "healthy"


async def test_redis_health_failure(monkeypatch):
    monkeypatch.setattr("redis.Redis", MagicMock(side_effect=Exception("redis down")))
    checker = module_health_check.RedisModuleHealth()
    result = await checker.health_check()
    assert result["module"] == "redis"
    assert result["status"] == "unhealthy"


async def test_ai_health_success(patch_ai):
    checker = module_health_check.AIModuleHealth()
    result = await checker.health_check()
    assert result["module"] == "ai_engine"
    assert result["status"] == "healthy"


async def test_ai_health_failure(monkeypatch):
    monkeypatch.setattr("core.ai_engine.get_llm_router", MagicMock(side_effect=Exception("ai down")))
    checker = module_health_check.AIModuleHealth()
    result = await checker.health_check()
    assert result["module"] == "ai_engine"
    assert result["status"] == "unhealthy"


async def test_module_graceful_shutdowns():
    for cls in (
        module_health_check.DatabaseModuleHealth,
        module_health_check.RedisModuleHealth,
        module_health_check.AIModuleHealth,
    ):
        await cls().graceful_shutdown()


async def test_check_all_modules_health_success(monkeypatch, patch_db, patch_redis, patch_ai):
    result = await module_health_check.check_all_modules_health()
    assert "database" in result
    assert "redis" in result
    assert "ai_engine" in result
    assert all(r["status"] == "healthy" for r in result.values())


async def test_check_all_modules_health_exception(monkeypatch):
    class BadHealth(module_health_check.ModuleHealthCheck):
        async def health_check(self):
            raise RuntimeError("boom")

        async def graceful_shutdown(self):
            pass

    monkeypatch.setattr(
        module_health_check,
        "module_health_registry",
        {"bad": BadHealth()},
    )
    result = await module_health_check.check_all_modules_health()
    assert result["bad"]["status"] == "error"
    assert "boom" in result["bad"]["error"]


# ---------------------------------------------------------------------------
# core.plugin_marketplace_manager
# ---------------------------------------------------------------------------
def test_publish_plugin_success():
    mgr = plugin_marketplace.PluginMarketplaceManager()
    code = '"""Safe plugin."""\nprint("hello")\n'
    assert mgr.publish_plugin(
        plugin_id="p1",
        plugin_name="Test Plugin",
        version="1.0.0",
        description="desc",
        author="alice",
        plugin_code=code,
        plugin_config={},
        quality=plugin_marketplace.PluginQuality.VERIFIED,
    )
    assert "p1" in mgr.listings
    assert mgr.listings["p1"].quality == plugin_marketplace.PluginQuality.VERIFIED
    assert mgr.quality_checks["p1"]["syntax_check"] is True
    assert mgr.quality_checks["p1"]["security_check"] is True
    assert mgr.quality_checks["p1"]["documentation_check"] is True
    assert mgr.quality_checks["p1"]["overall_score"] == 1.0


def test_publish_plugin_syntax_error():
    mgr = plugin_marketplace.PluginMarketplaceManager()
    code = "def broken("
    mgr.publish_plugin(
        plugin_id="p2",
        plugin_name="Broken",
        version="1.0.0",
        description="desc",
        author="bob",
        plugin_code=code,
        plugin_config={},
    )
    assert mgr.quality_checks["p2"]["syntax_check"] is False
    assert any("Syntax error" in i for i in mgr.quality_checks["p2"]["issues"])


def test_publish_plugin_unsafe_and_undocumented():
    mgr = plugin_marketplace.PluginMarketplaceManager()
    code = "eval(user_input)"
    mgr.publish_plugin(
        plugin_id="p3",
        plugin_name="Unsafe",
        version="1.0.0",
        description="desc",
        author="mallory",
        plugin_code=code,
        plugin_config={},
    )
    assert mgr.quality_checks["p3"]["security_check"] is False
    assert mgr.quality_checks["p3"]["documentation_check"] is False
    assert any("unsafe" in i.lower() for i in mgr.quality_checks["p3"]["issues"])


def test_approve_reject_download():
    mgr = plugin_marketplace.PluginMarketplaceManager()
    mgr.publish_plugin(
        "p4", "Plugin 4", "1.0.0", "desc", "alice", '"""doc"""\n', {},
    )
    assert mgr.approve_plugin("p4", "reviewer") is True
    assert mgr.listings["p4"].review_status == plugin_marketplace.PluginReviewStatus.APPROVED

    package = mgr.download_plugin("p4")
    assert package is not None
    assert package["plugin_id"] == "p4"
    assert package["download_count"] == 1
    assert mgr.total_downloads == 1

    assert mgr.reject_plugin("p4", "bad quality") is True
    assert mgr.listings["p4"].review_status == plugin_marketplace.PluginReviewStatus.REJECTED


def test_download_not_approved_or_missing():
    mgr = plugin_marketplace.PluginMarketplaceManager()
    mgr.publish_plugin(
        "p5", "Plugin 5", "1.0.0", "desc", "alice", '"""doc"""\n', {},
    )
    assert mgr.download_plugin("p5") is None
    assert mgr.download_plugin("missing") is None


def test_add_review_and_rating_validation():
    mgr = plugin_marketplace.PluginMarketplaceManager()
    mgr.publish_plugin(
        "p6", "Plugin 6", "1.0.0", "desc", "alice", '"""doc"""\n', {},
    )
    assert mgr.add_review("missing", "bob", 3, "ok") is False
    assert mgr.add_review("p6", "bob", 0, "bad") is False
    assert mgr.add_review("p6", "bob", 6, "bad") is False
    assert mgr.add_review("p6", "bob", 4, "great") is True
    assert mgr.listings["p6"].rating == 4.0
    assert mgr.listings["p6"].review_count == 1

    mgr.add_review("p6", "carol", 5, "excellent")
    assert mgr.listings["p6"].rating == 4.5
    assert mgr.total_reviews == 2


def test_get_plugin_listings_and_summary():
    mgr = plugin_marketplace.PluginMarketplaceManager()
    mgr.publish_plugin(
        "p7", "A", "1.0.0", "desc", "alice", '"""doc"""\n', {},
        quality=plugin_marketplace.PluginQuality.COMMUNITY,
    )
    mgr.publish_plugin(
        "p8", "B", "1.0.0", "desc", "bob", '"""doc"""\n', {},
        quality=plugin_marketplace.PluginQuality.CERTIFIED,
    )
    mgr.approve_plugin("p7", "r1")

    community = mgr.get_plugin_listings(quality=plugin_marketplace.PluginQuality.COMMUNITY)
    assert len(community) == 1
    assert community[0]["plugin_id"] == "p7"

    approved = mgr.get_plugin_listings(review_status=plugin_marketplace.PluginReviewStatus.APPROVED)
    assert len(approved) == 1

    assert len(mgr.get_plugin_listings()) == 2

    summary = mgr.get_marketplace_summary()
    assert summary["total_listings"] == 2
    assert summary["approved_plugins"] == 1
    assert summary["pending_reviews"] == 1
    assert "certified" in summary["plugins_by_quality"]


# ---------------------------------------------------------------------------
# core.compliance_manager
# ---------------------------------------------------------------------------
@pytest.fixture
def compliance_mgr(tmp_path):
    return compliance_manager.ComplianceManager({"audit_trail_dir": str(tmp_path)})


async def test_compliance_init_and_default_rules(compliance_mgr):
    rules = compliance_mgr.get_compliance_rules()
    assert len(rules) >= 12
    gdpr = compliance_mgr.get_compliance_rules(
        framework=compliance_manager.ComplianceFramework.GDPR
    )
    assert all(r["framework"] == "gdpr" for r in gdpr.values())


async def test_compliance_register_rule(compliance_mgr):
    rule = compliance_manager.ComplianceRule(
        rule_id="custom_001",
        rule_name="Custom Rule",
        framework=compliance_manager.ComplianceFramework.SOC2,
        description="test",
        severity=compliance_manager.RiskLevel.LOW,
    )
    compliance_mgr.register_rule(rule)
    assert "custom_001" in compliance_mgr.compliance_rules


async def test_run_compliance_check_all(monkeypatch, compliance_mgr):
    monkeypatch.setattr("asyncio.sleep", AsyncMock())
    monkeypatch.setattr("random.random", lambda: 0.9)
    results = await compliance_mgr.run_compliance_check()
    assert len(results) == len(compliance_mgr.compliance_rules)
    assert all(c.status == compliance_manager.ComplianceStatus.COMPLIANT for c in results)


async def test_run_compliance_check_by_rule_and_framework(monkeypatch, compliance_mgr):
    monkeypatch.setattr("asyncio.sleep", AsyncMock())
    monkeypatch.setattr("random.random", lambda: 0.9)
    by_rule = await compliance_mgr.run_compliance_check(rule_id="gdpr_data_minimization")
    assert len(by_rule) == 1
    assert by_rule[0].rule_id == "gdpr_data_minimization"

    by_fw = await compliance_mgr.run_compliance_check(
        framework=compliance_manager.ComplianceFramework.HIPAA
    )
    assert by_fw
    assert all(c.rule_id.startswith("hipaa") for c in by_fw)

    missing = await compliance_mgr.run_compliance_check(rule_id="missing")
    assert missing == []


async def test_run_compliance_check_non_compliant_and_notifications(monkeypatch, compliance_mgr):
    monkeypatch.setattr("asyncio.sleep", AsyncMock())
    monkeypatch.setattr("random.random", lambda: 0.1)
    sync_handler = MagicMock()
    async_handler = AsyncMock()
    compliance_mgr.register_notification_handler(sync_handler)
    compliance_mgr.register_notification_handler(async_handler)

    results = await compliance_mgr.run_compliance_check(rule_id="gdpr_data_minimization")
    assert results[0].status == compliance_manager.ComplianceStatus.NON_COMPLIANT
    assert results[0].findings
    assert results[0].recommendations
    assert compliance_mgr.total_violations > 0
    sync_handler.assert_called_once()
    async_handler.assert_awaited_once()


async def test_compliance_check_exception(monkeypatch, compliance_mgr):
    monkeypatch.setattr("asyncio.sleep", AsyncMock())
    monkeypatch.setattr("random.random", lambda: (_ for _ in ()).throw(Exception("rng error")))
    result = await compliance_mgr.run_compliance_check(rule_id="gdpr_data_minimization")
    assert result[0].status == compliance_manager.ComplianceStatus.UNKNOWN
    assert "rng error" in result[0].findings[0]


async def test_notification_handler_exception(monkeypatch, compliance_mgr):
    monkeypatch.setattr("asyncio.sleep", AsyncMock())
    monkeypatch.setattr("random.random", lambda: 0.1)
    bad_handler = MagicMock(side_effect=Exception("notify fail"))
    compliance_mgr.register_notification_handler(bad_handler)
    results = await compliance_mgr.run_compliance_check(rule_id="gdpr_data_minimization")
    assert results[0].status == compliance_manager.ComplianceStatus.NON_COMPLIANT


async def test_generate_compliance_report(monkeypatch, compliance_mgr, tmp_path):
    monkeypatch.setattr("asyncio.sleep", AsyncMock())
    monkeypatch.setattr("random.random", lambda: 0.9)
    start = datetime.now(timezone.utc) - timedelta(days=1)
    end = datetime.now(timezone.utc)
    report = await compliance_mgr.generate_compliance_report(
        compliance_manager.ComplianceFramework.GDPR, start, end
    )
    assert report.framework == compliance_manager.ComplianceFramework.GDPR
    assert report.overall_status == compliance_manager.ComplianceStatus.COMPLIANT
    assert report.report_id in compliance_mgr.compliance_reports
    assert (tmp_path / f"{report.report_id}.json").exists()


async def test_compliance_check_history(monkeypatch, compliance_mgr):
    monkeypatch.setattr("asyncio.sleep", AsyncMock())
    monkeypatch.setattr("random.random", lambda: 0.9)
    await compliance_mgr.run_compliance_check(rule_id="gdpr_data_minimization")
    await compliance_mgr.run_compliance_check(framework=compliance_manager.ComplianceFramework.GDPR)
    history = compliance_mgr.get_check_history()
    assert len(history) > 0
    filtered = compliance_mgr.get_check_history(rule_id="gdpr_data_minimization")
    assert all(h["rule_id"] == "gdpr_data_minimization" for h in filtered)


def test_compliance_get_statistics(compliance_mgr):
    stats = compliance_mgr.get_statistics()
    assert stats["total_rules"] == len(compliance_mgr.compliance_rules)
    assert stats["violation_rate"] == 0.0


async def test_start_auto_check_loop(monkeypatch, compliance_mgr):
    create_task = MagicMock()
    monkeypatch.setattr("core.compliance_manager.asyncio.create_task", create_task)
    compliance_mgr.auto_check_enabled = False
    await compliance_mgr.start_auto_check_loop()
    create_task.assert_not_called()

    compliance_mgr.auto_check_enabled = True
    await compliance_mgr.start_auto_check_loop()
    create_task.assert_called_once()


# ---------------------------------------------------------------------------
# core.l1l2_data_flow_integrator
# ---------------------------------------------------------------------------
@pytest.fixture
def l1l2_integrator(monkeypatch):
    kafka = MagicMock()
    flink = MagicMock()
    flink.jobs = []
    monitoring = MagicMock()
    monitoring.metrics_collector = MagicMock()
    monkeypatch.setattr("core.l1l2_data_flow_integrator.get_kafka_processor", lambda: kafka)
    monkeypatch.setattr("core.l1l2_data_flow_integrator.get_flink_job_manager", lambda: flink)
    monkeypatch.setattr(
        "core.l1l2_data_flow_integrator.get_monitoring_infrastructure", lambda: monitoring
    )
    return l1l2_data_flow.L1L2DataFlowIntegrator(), kafka, flink, monitoring


def _message(topic, value, msg_id=None):
    value = value.copy()
    value.setdefault("id", msg_id or "id-1")
    return SimpleNamespace(topic=topic, value=value)


def test_l1l2_initialization(l1l2_integrator):
    integrator, kafka, flink, monitoring = l1l2_integrator
    calls = [c[0][0] for c in kafka.register_handler.call_args_list]
    for topic in ("metrics-topic", "logs-topic", "traces-topic", "alerts-topic"):
        assert topic in calls
    assert monitoring is not None


def test_l1l2_handle_metrics_and_analysis(l1l2_integrator):
    integrator, kafka, flink, monitoring = l1l2_integrator
    integrator.register_analysis_handler(
        l1l2_data_flow.AnalysisType.ANOMALY_DETECTION,
        lambda did, data: {"result": 1},
    )
    msg = _message("metrics-topic", {"metric": "cpu", "value": 95})
    integrator._handle_metrics_data(msg)
    assert integrator.data_flow_stats["total_processed"] == 1
    assert integrator.data_flow_stats["total_analyzed"] == 1
    monitoring.metrics_collector.increment_counter.assert_called()
    monitoring.metrics_collector.record_timing.assert_called()


def test_l1l2_handle_logs_data(l1l2_integrator):
    integrator, *_ = l1l2_integrator
    integrator._handle_logs_data(_message("logs-topic", {"message": "error"}))
    assert integrator.data_flow_stats["total_processed"] == 1


def test_l1l2_handle_traces_data(l1l2_integrator):
    integrator, *_ = l1l2_integrator
    integrator._handle_traces_data(_message("traces-topic", {"trace_id": "t1"}))
    assert integrator.data_flow_stats["total_processed"] == 1


def test_l1l2_handle_alerts_data(l1l2_integrator):
    integrator, *_ = l1l2_integrator
    integrator._handle_alerts_data(_message("alerts-topic", {"alert": "high"}))
    assert integrator.data_flow_stats["total_processed"] == 1


def test_l1l2_handler_error(l1l2_integrator):
    integrator, kafka, flink, monitoring = l1l2_integrator
    monitoring.metrics_collector.increment_counter.side_effect = Exception("metrics boom")
    integrator._handle_metrics_data(_message("metrics-topic", {"x": 1}))
    assert integrator.data_flow_stats["total_errors"] == 1


def test_l1l2_analysis_handler_error(l1l2_integrator):
    integrator, *_ = l1l2_integrator
    integrator.register_analysis_handler(
        l1l2_data_flow.AnalysisType.ANOMALY_DETECTION,
        lambda did, data: (_ for _ in ()).throw(ValueError("handler boom")),
    )
    integrator._handle_metrics_data(_message("metrics-topic", {"x": 1}))
    assert integrator.data_flow_stats["total_processed"] == 1


def test_l1l2_send_to_analysis_outer_error(l1l2_integrator, monkeypatch):
    integrator, kafka, flink, monitoring = l1l2_integrator
    monitoring.metrics_collector.record_timing.side_effect = Exception("timing boom")
    integrator._send_to_analysis(
        l1l2_data_flow.AnalysisType.RAG_ANALYSIS,
        "d1",
        {"x": 1},
    )
    assert isinstance(integrator.data_flow_stats["processing_times"], list)


def test_l1l2_start_stop_and_stats(l1l2_integrator):
    integrator, *_ = l1l2_integrator
    assert integrator.start_data_flow() is True
    assert integrator.stop_data_flow() is True
    stats = integrator.get_data_flow_stats()
    assert "avg_processing_time_ms" in stats
    assert "error_rate" in stats
    assert "analysis_rate" in stats


def test_l1l2_send_test_data(l1l2_integrator):
    integrator, kafka, *_ = l1l2_integrator
    kafka.send_message.return_value = True
    assert integrator.send_test_data("topic-x", {"payload": 1}) is True
    kafka.send_message.assert_called_once_with("topic-x", "test_key", {"payload": 1})


def test_l1l2_get_instance():
    instance = l1l2_data_flow.get_l1l2_data_flow_integrator()
    assert isinstance(instance, l1l2_data_flow.L1L2DataFlowIntegrator)


# ---------------------------------------------------------------------------
# core.business_metrics
# ---------------------------------------------------------------------------
def test_business_metrics_record_and_calculate():
    collector = business_metrics.BusinessMetricsCollector(retention_days=7)
    now = datetime.now(timezone.utc)
    collector.record_alert("a1", "critical")
    collector.acknowledge_alert("a1", "oncall-1")
    collector.resolve_alert("a1", auto_healed=True)
    collector._alert_events["a1"].created_at = now - timedelta(hours=1)
    collector._alert_events["a1"].acknowledged_at = now - timedelta(minutes=55)
    collector._alert_events["a1"].resolved_at = now - timedelta(minutes=50)

    collector.record_alert("a2", "warning")
    collector.acknowledge_alert("a2", "oncall-2")
    collector.resolve_alert("a2")
    collector._alert_events["a2"].created_at = now - timedelta(minutes=30)
    collector._alert_events["a2"].acknowledged_at = now - timedelta(minutes=20)
    collector._alert_events["a2"].resolved_at = now - timedelta(minutes=10)

    collector.record_alert("a3", "info")

    metrics = collector.calculate_metrics(time_window=timedelta(hours=2))
    assert metrics.total_alerts == 3
    assert metrics.active_alerts == 1
    assert metrics.resolved_alerts == 2
    assert metrics.auto_healed_alerts == 1
    assert metrics.alert_resolution_rate == (2 / 3 * 100)
    assert metrics.mttr > 0
    assert metrics.mtta > 0
    assert metrics.auto_heal_success_rate == (1 / 2 * 100)


def test_business_metrics_empty():
    collector = business_metrics.BusinessMetricsCollector()
    metrics = collector.calculate_metrics()
    assert metrics.total_alerts == 0


def test_business_metrics_history_and_trend():
    collector = business_metrics.BusinessMetricsCollector()
    now = datetime.now(timezone.utc)
    collector.record_alert("h1", "low")
    collector.resolve_alert("h1")
    collector._alert_events["h1"].created_at = now - timedelta(minutes=10)
    collector._alert_events["h1"].resolved_at = now - timedelta(minutes=5)
    collector.calculate_metrics(time_window=timedelta(hours=1))
    collector.calculate_metrics(time_window=timedelta(hours=1))
    history = collector.get_metrics_history(limit=5)
    assert len(history) == 2
    trend = collector.get_metrics_trend("mttr", hours=24)
    assert len(trend) == 2


def test_business_metrics_cleanup():
    collector = business_metrics.BusinessMetricsCollector(retention_days=1)
    now = datetime.now(timezone.utc)
    old = business_metrics.AlertEvent(
        alert_id="old", created_at=now - timedelta(days=2), severity="low"
    )
    new = business_metrics.AlertEvent(
        alert_id="new", created_at=now, severity="low"
    )
    old_metric = business_metrics.BusinessMetrics(timestamp=now - timedelta(days=2))
    new_metric = business_metrics.BusinessMetrics(timestamp=now)
    collector._alert_events = {"old": old, "new": new}
    collector._metrics_history = [old_metric, new_metric]
    collector.cleanup_old_data()
    assert "old" not in collector._alert_events
    assert "new" in collector._alert_events
    assert len(collector._metrics_history) == 1


def test_business_metrics_alerts_by_severity_and_assignees():
    collector = business_metrics.BusinessMetricsCollector()
    collector.record_alert("s1", "critical")
    collector.record_alert("s2", "critical")
    collector.record_alert("s3", "warning")
    collector.acknowledge_alert("s1", "alice")
    collector.acknowledge_alert("s2", "alice")
    collector.acknowledge_alert("s3", "bob")
    severity_counts = collector.get_alerts_by_severity()
    assert severity_counts["critical"] == 2
    assert severity_counts["warning"] == 1
    top = collector.get_top_assignees(limit=2)
    assert top[0]["assignee"] == "alice"
    assert top[0]["count"] == 2


def test_business_metrics_acknowledge_resolve_missing():
    collector = business_metrics.BusinessMetricsCollector()
    collector.acknowledge_alert("missing", "nobody")
    collector.resolve_alert("missing")
    assert collector._alert_events == {}


async def test_setup_business_metrics():
    result = await business_metrics.setup_business_metrics()
    assert result["status"] == "success"
    assert result["collector"] == "BusinessMetricsCollector"
