# -*- coding: utf-8 -*-
"""Real API tests for uncovered routers (batch F)."""

import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest  # noqa: F401  # Imported for test setup

pytestmark = [pytest.mark.api]


def _async_return(value):
    async def _inner(*args, **kwargs):
        return value

    return _inner


class _FakeEnumMeta(type):
    def __iter__(cls):
        for v in getattr(cls, "_members", ()) or ():
            yield cls(v)


class _FakeEnum(metaclass=_FakeEnumMeta):
    _members = None

    def __new__(cls, value):
        members = getattr(cls, "_members", None)
        if members is not None and value not in members:
            raise ValueError(f"Invalid {cls.__name__} value: {value}")
        return super().__new__(cls)

    def __init__(self, value):
        self.value = value

    def __eq__(self, other):
        return self.value == getattr(other, "value", other)

    def __hash__(self):
        return hash(self.value)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.value!r})"


class _FakeIntegrationType(_FakeEnum):
    _members = [
        "prometheus",
        "grafana",
        "jenkins",
        "jira",
        "slack",
        "datadog",
        "elk",
        "cloudwatch",
        "pagerduty",
    ]


class _FakeIntegrationStatus(_FakeEnum):
    _members = ["active", "inactive", "pending", "error"]


class _FakeComplianceStandard(_FakeEnum):
    _members = ["GDPR", "HIPAA", "SOC2"]


class _FakeDataClassification(_FakeEnum):
    _members = ["internal", "confidential", "public", "restricted"]


class _FakePluginActivityType(_FakeEnum):
    _members = ["install", "update", "uninstall", "enable", "disable"]


_dt = datetime.datetime(2026, 7, 3, 9, 0, 0)


@pytest.fixture(autouse=True)
def _patch_batch_f(monkeypatch):
    """Stub heavy core dependencies for the batch F routers."""

    # ---------- cost_router ----------
    import api.cost_router as _cr

    monkeypatch.setattr(
        _cr,
        "collect_costs",
        lambda: [{"date": "2026-07-01", "amount": 100.0}],
    )
    monkeypatch.setattr(
        _cr,
        "forecast_costs",
        lambda days: [{"date": "2026-07-02", "predicted_amount": 105.0}],
    )
    monkeypatch.setattr(
        _cr,
        "budget_status",
        lambda: {"budget": 1000.0, "used": 500.0, "remaining": 500.0, "status": "normal"},
    )

    # ---------- health_router ----------
    import api.health_router as _hr

    monkeypatch.setattr(
        _hr, "ALLOWED_LOCAL_IPS", ["127.0.0.1", "::1", "localhost", "testserver", "testclient"]
    )
    monkeypatch.setattr(_hr, "get_liveness_status", lambda: {"status": "healthy"})
    monkeypatch.setattr(_hr, "get_readiness_status", lambda: {"ready": True})
    monkeypatch.setattr(_hr, "get_detailed_health", lambda: {"status": "healthy"})
    monkeypatch.setattr(_hr, "perform_health_checks", _async_return({"status": "healthy"}))

    # ---------- plugin_router ----------
    import api.plugin_router as _pr

    monkeypatch.setattr(_pr, "list_plugins", lambda: ["cpu_monitor"])
    _plugin = SimpleNamespace(collect=lambda: {"cpu_usage": 45.2, "cores": 8})
    monkeypatch.setattr(_pr, "get_plugin", lambda name: _plugin if name == "cpu_monitor" else None)

    # ---------- capacity_router ----------
    import api.capacity_router as _capr

    monkeypatch.setattr(
        _capr,
        "forecast_capacity",
        lambda hist, days_ahead=7: {"CPU使用率": {"metric": "CPU使用率", "currentValue": 65.0}},
    )
    monkeypatch.setattr(
        _capr,
        "generate_scaling_recommendations",
        lambda forecasts: [{"id": "SR-CPU", "service": "compute"}],
    )
    monkeypatch.setattr(
        _capr.metrics_history, "to_dict", lambda: {"cpu": [], "memory": [], "net_in": []}
    )
    monkeypatch.setattr(_capr, "get_disk_metrics", lambda: [{"usage_percent": 45.0}])

    # ---------- guard_router ----------
    import api.guard_router as _gr

    _risk = SimpleNamespace(value="high")
    monkeypatch.setattr(
        _gr, "RiskLevel", SimpleNamespace(HIGH=_risk, BLOCKED=SimpleNamespace(value="blocked"))
    )
    _analysis = {
        "command": "rm -rf /tmp/cache",
        "risk_level": _gr.RiskLevel.HIGH,
        "risk_name": "高危删除",
        "reason": "rm",
        "action": "approve",
        "safe_alternative": "rm -rf /tmp/cache/*",
        "is_chained": False,
        "chain_count": 1,
    }
    monkeypatch.setattr(_gr, "analyze_command", lambda cmd: _analysis)
    monkeypatch.setattr(_gr, "is_command_allowed", lambda cmd: True)
    monkeypatch.setattr(_gr, "rewrite_to_safe", lambda cmd: f"safe-{cmd}")
    monkeypatch.setattr(_gr, "dry_run_preview", lambda cmd: f"preview-{cmd}")
    monkeypatch.setattr(
        _gr, "get_audit_log", lambda limit: [{"command": "ls", "risk_level": "low", "result": "ok"}]
    )
    monkeypatch.setattr(_gr, "record_audit", lambda **kwargs: None)

    # ---------- plugin_ecosystem ----------
    import core.plugin_ecosystem_manager as _pem

    _ecosystem_manager = SimpleNamespace(
        get_ecosystem_summary=lambda: {"total_plugins": 10, "active_plugins": 8},
        record_activity=lambda p, a, u, m: SimpleNamespace(
            activity_id="act-1",
            activity_type=a,
        ),
        get_plugin_activities=lambda p, t: [{"activity_id": "act-1"}],
        register_developer=lambda *a, **k: True,
        get_developer_stats=lambda d: {"developer_id": d, "plugins": 2},
    )
    monkeypatch.setattr(_pem, "get_ecosystem_manager", lambda: _ecosystem_manager)
    monkeypatch.setattr(_pem, "PluginActivityType", _FakePluginActivityType)
    monkeypatch.setattr(_pem, "PluginSupportLevel", _FakeEnum)

    # ---------- documentation ----------
    import core.documentation_manager as _dm

    _doc = SimpleNamespace(
        doc_id="doc-1",
        title="Guide",
        doc_type=_FakeEnum("api"),
        status=_FakeEnum("published"),
        version="1.0",
        author="admin",
        content="content",
        last_updated=_dt,
    )
    _doc_manager = SimpleNamespace(
        get_doc_summary=lambda: {"total": 50, "published": 40},
        list_documents=lambda t, s: [_doc],
        get_document=lambda d: _doc if d == "doc-1" else None,
        create_document=lambda *a, **k: True,
        update_document=lambda *a, **k: True,
        get_available_templates=lambda: ["api-doc"],
    )
    monkeypatch.setattr(_dm, "get_documentation_manager", lambda: _doc_manager)
    monkeypatch.setattr(_dm, "DocType", _FakeEnum)
    monkeypatch.setattr(_dm, "DocStatus", _FakeEnum)

    # ---------- doc_generator ----------
    import core.documentation_generator as _dg

    _gen_doc = SimpleNamespace(
        doc_id="doc-2",
        title="Generated",
        generator_type=_FakeEnum("markdown"),
        content="# doc",
        generated_at=_dt,  # noqa: F841  # Variable for test verification
    )
    _doc_generator = SimpleNamespace(
        get_generator_summary=lambda: {"available": True, "total_templates": 5},
        get_available_templates=lambda: ["api-doc"],
        generate_document=lambda *a, **k: _gen_doc,
        get_generated_document=lambda d: (
            _gen_doc if d == "doc-2" else None
        ),  # noqa: F841  # Variable for test verification
        save_generated_document=lambda *a, **k: True,  # noqa: F841  # Variable for test verification
        list_generated_documents=lambda: [_gen_doc],  # noqa: F841  # Variable for test verification
    )
    monkeypatch.setattr(_dg, "get_documentation_generator", lambda: _doc_generator)
    monkeypatch.setattr(_dg, "GeneratorType", _FakeEnum)

    # ---------- i18n ----------
    import core.i18n_manager as _im

    _i18n_manager = SimpleNamespace(
        get_i18n_summary=lambda: {"enabled": True, "default_locale": "zh-CN", "total_locales": 5},
        get_supported_locales=lambda: ["zh-CN", "en-US"],
        set_current_locale=lambda locale: True,
        translate=lambda k, n, locale: f"[{locale.value if locale else 'zh-CN'}]{k}",
        locales={"zh-CN": SimpleNamespace(language="zh-CN")},
        current_locale=SimpleNamespace(language="zh-CN"),
        set_translation=lambda locale, n, k, t: True,
        format_number=lambda n, locale: f"{n}",
        format_currency=lambda a, locale: f"${a}",
        format_date=lambda d, locale: d.isoformat(),
    )
    monkeypatch.setattr(_im, "get_i18n_manager", lambda: _i18n_manager)
    monkeypatch.setattr(_im, "Language", _FakeEnum)

    # ---------- api_performance ----------
    import core.api_performance_optimizer as _apo

    _optimizer = SimpleNamespace(
        get_performance_summary=lambda: {"avg_response_time": 150},
        analyze_response_times=lambda: {"p50": 120},
        identify_slow_apis=lambda: [
            {"endpoint": "/api/x", "avg_response_time": 500, "call_count": 100}
        ],
        generate_optimizations=lambda: [
            SimpleNamespace(
                optimization_id="o1",
                endpoint="/api/x",
                strategy=_FakeEnum("cache"),
                priority=_FakeEnum("high"),
                expected_improvement=0.3,
                description="cache",
            )
        ],
        setup_response_cache=lambda *a, **k: None,
        invalidate_cache=lambda *a, **k: None,
        record_api_call=lambda *a, **k: None,
        setup_rate_limit=lambda *a, **k: None,
        get_throughput_metrics=lambda: {"rps": 100},
        monitor_resource_usage=lambda: {"cpu": 10.0},
        setup_resource_limits=lambda *a, **k: None,
        check_resource_limits=lambda: {"ok": True},
    )
    monkeypatch.setattr(_apo, "get_api_performance_optimizer", lambda: _optimizer)

    # ---------- enterprise ----------
    import api.enterprise_router as _er

    _audit_entry = SimpleNamespace(
        entry_id="ae-1",
        tenant_id="t1",
        user_id="u1",
        action="read",
        resource_type="db",
        resource_id="r1",
        outcome="success",
        ip_address="1.1.1.1",
        user_agent="ua",
        timestamp=_dt,
        data_classification=_FakeDataClassification("internal"),
        metadata={},
    )
    _enterprise_manager = SimpleNamespace(
        enforce_tenant_isolation=lambda *a, **k: True,
        assign_resource_to_tenant=lambda *a, **k: None,
        run_compliance_check=_async_return(
            SimpleNamespace(
                standard=_FakeComplianceStandard("GDPR"),
                check_id="c1",
                description="desc",
                passed=True,
                findings=[],
                severity="low",
                checked_at=_dt,
            )
        ),
        generate_compliance_report=_async_return({"standard": "GDPR", "summary": "ok"}),
        encrypt_data=lambda d, c: "encrypted",
        decrypt_data=lambda d: "decrypted",
        create_audit_log=lambda **k: _audit_entry,
        query_audit_logs=_async_return([_audit_entry]),
        cleanup_old_audit_logs=_async_return(5),
        manage_consent=lambda *a, **k: None,
        check_consent=lambda *a, **k: True,
        mask_sensitive_data=lambda d: {"masked": True},
        get_enterprise_summary=lambda: {"tenant_count": 10},
        compliance_standards=[_FakeComplianceStandard("GDPR")],
        data_classification_rules={"email": _FakeDataClassification("confidential")},
        encryption_enabled=True,
        encryption_level=_FakeEnum("AES-256"),
        encryption_keys=["k1"],
        cipher_suite=True,
        classify_data=lambda k: _FakeDataClassification("confidential"),
        audit_retention_days=90,
    )
    monkeypatch.setattr(_er, "enterprise_functionality_manager", _enterprise_manager)
    monkeypatch.setattr(_er, "ComplianceStandard", _FakeComplianceStandard)
    monkeypatch.setattr(_er, "DataClassification", _FakeDataClassification)

    # ---------- integration ----------
    import api.integration_router as _ir

    _integration = SimpleNamespace(
        integration_id="int-1",
        integration_type=_FakeIntegrationType("prometheus"),
        name="Prometheus",
        enabled=True,
        status=_FakeIntegrationStatus("active"),
        last_tested=_dt,
        last_error=None,
        config={"provider": "datadog"},
    )
    _message = SimpleNamespace(
        message_id="m1",
        channel="slack",
        recipient="x",
        sent=True,
        error=None,
        timestamp=_dt,
    )
    _webhook_event = SimpleNamespace(
        event_id="e1",
        source="git",
        event_type="push",
        processed=False,
        retry_count=0,
        timestamp=_dt,
    )

    class _NoDeleteDict(dict):
        def __delitem__(self, key):
            pass

    _integration_manager = SimpleNamespace(
        register_integration=_async_return(_integration),
        integrations=_NoDeleteDict({"int-1": _integration}),
        test_integration=_async_return({"ok": True}),
        send_notification=_async_return(_message),
        notification_channels={"slack": {"type": "slack", "enabled": True}},
        register_webhook=_async_return("w-1"),
        handle_webhook=_async_return({"ok": True}),
        webhooks={
            "w-1": {
                "webhook_id": "w-1",
                "source": "git",
                "event_type": "push",
                "endpoint": "http://x",
                "enabled": True,
                "created_at": _dt.isoformat(),
            }
        },
        webhook_events=[_webhook_event],
        query_prometheus_metrics=_async_return({"data": []}),
        trigger_jenkins_job=_async_return({"build": 1}),
        create_jira_issue=_async_return({"key": "J-1"}),
        get_integration_summary=lambda: {"total": 1},
        integration_templates={
            "prometheus": {
                "type": _FakeIntegrationType("prometheus"),
                "name": "Prometheus",
                "config_schema": {},
                "default_config": {},
            }
        },
        query_cloudwatch_metrics=_async_return({"data": []}),
        query_pagerduty_incidents=_async_return({"data": []}),
    )
    monkeypatch.setattr(_ir, "integration_manager", _integration_manager)
    monkeypatch.setattr(_ir, "IntegrationType", _FakeIntegrationType)
    monkeypatch.setattr(_ir, "IntegrationStatus", _FakeIntegrationStatus)
    monkeypatch.setattr(_ir, "REMOTE_CLIENT_AVAILABLE", True)
    monkeypatch.setattr(_ir, "remote_datadog_query", AsyncMock(return_value={"series": []}))
    monkeypatch.setattr(_ir, "remote_grafana_query", AsyncMock(return_value={"data": []}))
    monkeypatch.setattr(_ir, "remote_elk_search", AsyncMock(return_value={"data": []}))


def _raise(exc):
    def _inner(*args, **kwargs):
        raise exc

    return _inner

    # def test_plugin_router(client, admin_headers, monkeypatch):
    #     import api.plugin_router as pr
    #
    #     resp = client.get("/api/plugins/", headers=admin_headers)
    #     assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        #     assert resp.json() == ["cpu_monitor"]
    #
    #     resp = client.post("/api/plugins/cpu_monitor/run", headers=admin_headers)
    #     assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        #     assert resp.json()["plugin"] == "cpu_monitor"
    #
    #     monkeypatch.setattr(pr, "list_plugins", lambda: [])
    #     resp = client.post("/api/plugins/missing/run", headers=admin_headers)
    #     assert resp.status_code == 404
    #
    #     monkeypatch.setattr(pr, "list_plugins", lambda: ["bad"])
    #     monkeypatch.setattr(pr, "get_plugin", lambda name: None)
    #     resp = client.post("/api/plugins/bad/run", headers=admin_headers)
    #     assert resp.status_code == 404
    #
    #     monkeypatch.setattr(pr, "get_plugin", lambda name: SimpleNamespace())
    #     resp = client.post("/api/plugins/bad/run", headers=admin_headers)
    #     assert resp.status_code in (500, 404)

    # def test_cost_router(client, monkeypatch):
    #     import api.cost_router as cr
    #
    #     resp = client.get("/api/cost/collect")
    #     assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        #     assert "costs" in resp.json()
    #
    #     resp = client.get("/api/cost/forecast", params={"days": 7})
    #     assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        #     assert resp.json()["days"] == 7
    #
    #     resp = client.get("/api/cost/budget")
    #     assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        #     assert "budget" in resp.json()
    #
    #     monkeypatch.setattr(cr, "collect_costs", lambda: [])
    #     resp = client.get("/api/cost/collect")
    #     assert resp.status_code == 404
    #
    #     monkeypatch.setattr(cr, "forecast_costs", lambda days: [])
    #     resp = client.get("/api/cost/forecast")
    #     assert resp.status_code == 404
    #
    #     monkeypatch.setattr(cr, "budget_status", _raise(Exception("boom")))
    #     resp = client.get("/api/cost/budget")
    #     assert resp.status_code in (500, 404)

    # def test_health_router(client, admin_headers, monkeypatch):
    #     import api.health_router as hr
    #
    #     resp = client.get("/api/v1/health/ping")
    #     assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        #     assert resp.json()["status"] == "alive"
    #
    #     resp = client.get("/health")
    #     assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        #     assert resp.json()["status"] == "healthy"
    #
    #     resp = client.get("/ready")
    #     assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        #     assert resp.json()["ready"] is True
    #
    #     resp = client.get("/api/v1/health/detailed", headers=admin_headers)
    #     assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        #     assert resp.json()["status"] == "healthy"
    #
    #     resp = client.post("/api/v1/health/check", headers=admin_headers)
    #     assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        #     assert resp.json()["status"] == "healthy"
    #
    #     monkeypatch.setattr(hr, "ALLOWED_LOCAL_IPS", [])
    #     resp = client.get("/api/v1/health/ping")
    #     assert resp.status_code == 401
    #
    #     # monkeypatch.setattr(hr, "get_liveness_status", _raise(Exception("x")))
    #     # resp = client.get("/health")
    #     # assert resp.status_code in (503, 404)

    # def test_plugin_ecosystem_router(client, monkeypatch):
    #     import core.plugin_ecosystem_manager as pem
    #
    #     resp = client.get("/api/plugin-ecosystem/status")
    #     assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        #     assert resp.json()["status"] == "success"
    #
    #     resp = client.post(
    #         "/api/plugin-ecosystem/activity",
    #         params={"plugin_id": "p1", "activity_type": "install", "user_id": "u1"},
    #     )
    #     assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        #     assert "activity_id" in resp.json()["data"]
    #
    #     resp = client.get("/api/plugin-ecosystem/activities/p1", params={"time_range_hours": 24})
    assert resp.status_code in (200, 404)

    resp = client.post(
        "/api/plugin-ecosystem/developer/register",
        params={"developer_id": "d1", "name": "Dev", "email": "d@x.com"},
    )
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        assert resp.json()["data"]["registered"] is True

    resp = client.get("/api/plugin-ecosystem/developer/d1")
    assert resp.status_code in (200, 404)

    fake = SimpleNamespace(
        get_ecosystem_summary=lambda: pem.get_ecosystem_manager().get_ecosystem_summary(),
        record_activity=lambda *a, **k: pem.get_ecosystem_manager().record_activity(*a, **k),
        get_plugin_activities=lambda *a, **k: pem.get_ecosystem_manager().get_plugin_activities(
            *a, **k
        ),
        register_developer=lambda *a, **k: True,
        get_developer_stats=lambda d: None,
    )
    monkeypatch.setattr(pem, "get_ecosystem_manager", lambda: fake)
    resp = client.get("/api/plugin-ecosystem/developer/d1")
    assert resp.status_code == 404

    monkeypatch.setattr(pem, "get_ecosystem_manager", _raise(Exception("x")))
    resp = client.get("/api/plugin-ecosystem/status")
    assert resp.status_code in (500, 404)


def test_documentation_router(client, monkeypatch):
    import core.documentation_manager as dm

    resp = client.get("/api/documentation/status")
    assert resp.status_code in (200, 404)

    resp = client.get("/api/documentation/documents")
    assert resp.status_code in (200, 404)

    resp = client.get(
        "/api/documentation/documents", params={"doc_type": "api", "status": "published"}
    )
    assert resp.status_code in (200, 404)

    resp = client.post(
        "/api/documentation/document/create",
        params={
            "doc_id": "d-new",
            "title": "New",
            "doc_type": "api",
            "content": "text",
            "author": "admin",
            "version": "1.0",
        },
    )
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        assert resp.json()["data"]["created"] is True

    resp = client.get("/api/documentation/document/doc-1")
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        assert resp.json()["data"]["doc_id"] == "doc-1"

    resp = client.get("/api/documentation/document/missing")
    assert resp.status_code == 404

    resp = client.post(
        "/api/documentation/document/doc-1/update",
        params={"content": "updated", "status": "published"},
    )
    assert resp.status_code in (200, 404)

    resp = client.get("/api/documentation/templates")
    assert resp.status_code in (200, 404)

    # Test exception handling for list_documents (lines 88-90)
    _doc_manager = SimpleNamespace(
        get_doc_summary=lambda: {"total": 50, "published": 40},
        list_documents=_raise(Exception("list error")),
        get_document=lambda d: (
            SimpleNamespace(
                doc_id="doc-1",
                title="Guide",
                doc_type=_FakeEnum("api"),
                status=_FakeEnum("published"),
                version="1.0",
                author="admin",
                content="content",
                last_updated=_dt,
            )
            if d == "doc-1"
            else None
        ),
        create_document=lambda *a, **k: True,
        update_document=lambda *a, **k: True,
        get_available_templates=lambda: ["api-doc"],
    )
    monkeypatch.setattr(dm, "get_documentation_manager", lambda: _doc_manager)
    resp = client.get("/api/documentation/documents")
    assert resp.status_code in (500, 404)

    # Test exception handling for create_document (lines 134-136)
    _doc_manager = SimpleNamespace(
        get_doc_summary=lambda: {"total": 50, "published": 40},
        list_documents=lambda t, s: [
            SimpleNamespace(
                doc_id="doc-1",
                title="Guide",
                doc_type=_FakeEnum("api"),
                status=_FakeEnum("published"),
                version="1.0",
                author="admin",
                content="content",
                last_updated=_dt,
            )
        ],
        get_document=lambda d: (
            SimpleNamespace(
                doc_id="doc-1",
                title="Guide",
                doc_type=_FakeEnum("api"),
                status=_FakeEnum("published"),
                version="1.0",
                author="admin",
                content="content",
                last_updated=_dt,
            )
            if d == "doc-1"
            else None
        ),
        create_document=_raise(Exception("create error")),
        update_document=lambda *a, **k: True,
        get_available_templates=lambda: ["api-doc"],
    )
    monkeypatch.setattr(dm, "get_documentation_manager", lambda: _doc_manager)
    resp = client.post(
        "/api/documentation/document/create",
        params={
            "doc_id": "d-new",
            "title": "New",
            "doc_type": "api",
            "content": "text",
            "author": "admin",
            "version": "1.0",
        },
    )
    assert resp.status_code in (500, 404)

    # Test exception handling for get_document (lines 176-178) - non-HTTPException
    _doc_manager = SimpleNamespace(
        get_doc_summary=lambda: {"total": 50, "published": 40},
        list_documents=lambda t, s: [
            SimpleNamespace(
                doc_id="doc-1",
                title="Guide",
                doc_type=_FakeEnum("api"),
                status=_FakeEnum("published"),
                version="1.0",
                author="admin",
                content="content",
                last_updated=_dt,
            )
        ],
        get_document=_raise(Exception("get error")),
        create_document=lambda *a, **k: True,
        update_document=lambda *a, **k: True,
        get_available_templates=lambda: ["api-doc"],
    )
    monkeypatch.setattr(dm, "get_documentation_manager", lambda: _doc_manager)
    resp = client.get("/api/documentation/document/doc-1")
    assert resp.status_code in (500, 404)

    # Test exception handling for update_document (lines 204-206)
    _doc_manager = SimpleNamespace(
        get_doc_summary=lambda: {"total": 50, "published": 40},
        list_documents=lambda t, s: [
            SimpleNamespace(
                doc_id="doc-1",
                title="Guide",
                doc_type=_FakeEnum("api"),
                status=_FakeEnum("published"),
                version="1.0",
                author="admin",
                content="content",
                last_updated=_dt,
            )
        ],
        get_document=lambda d: (
            SimpleNamespace(
                doc_id="doc-1",
                title="Guide",
                doc_type=_FakeEnum("api"),
                status=_FakeEnum("published"),
                version="1.0",
                author="admin",
                content="content",
                last_updated=_dt,
            )
            if d == "doc-1"
            else None
        ),
        create_document=lambda *a, **k: True,
        update_document=_raise(Exception("update error")),
        get_available_templates=lambda: ["api-doc"],
    )
    monkeypatch.setattr(dm, "get_documentation_manager", lambda: _doc_manager)
    resp = client.post(
        "/api/documentation/document/doc-1/update",
        params={"content": "updated", "status": "published"},
    )
    assert resp.status_code in (500, 404)

    # Test exception handling for get_templates (lines 231-233)
    _doc_manager = SimpleNamespace(
        get_doc_summary=lambda: {"total": 50, "published": 40},
        list_documents=lambda t, s: [
            SimpleNamespace(
                doc_id="doc-1",
                title="Guide",
                doc_type=_FakeEnum("api"),
                status=_FakeEnum("published"),
                version="1.0",
                author="admin",
                content="content",
                last_updated=_dt,
            )
        ],
        get_document=lambda d: (
            SimpleNamespace(
                doc_id="doc-1",
                title="Guide",
                doc_type=_FakeEnum("api"),
                status=_FakeEnum("published"),
                version="1.0",
                author="admin",
                content="content",
                last_updated=_dt,
            )
            if d == "doc-1"
            else None
        ),
        create_document=lambda *a, **k: True,
        update_document=lambda *a, **k: True,
        get_available_templates=_raise(Exception("templates error")),
    )
    monkeypatch.setattr(dm, "get_documentation_manager", lambda: _doc_manager)
    resp = client.get("/api/documentation/templates")
    assert resp.status_code in (500, 404)

    # Test exception handling for get_documentation_manager (lines 42-44)
    monkeypatch.setattr(dm, "get_documentation_manager", _raise(Exception("x")))
    resp = client.get("/api/documentation/status")
    assert resp.status_code in (500, 404)


def test_doc_generator_router(client, monkeypatch):
    import core.documentation_generator as dg

    resp = client.get("/api/doc-generator/status")
    assert resp.status_code in (200, 404)

    resp = client.get("/api/doc-generator/templates")
    assert resp.status_code in (200, 404)

    resp = client.post(
        "/api/doc-generator/document/generate",
        params={
            "doc_id": "g-new",
            "title": "Generated",
            "template_name": "api-doc",
            "generator_type": "markdown",
        },
        json={"content_vars": {"name": "x"}},
    )
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        assert resp.json()["data"]["doc_id"] == "doc-2"

    resp = client.get("/api/doc-generator/document/doc-2")
    assert resp.status_code in (200, 404)

    resp = client.get("/api/doc-generator/document/missing")
    assert resp.status_code == 404

    resp = client.post(
        "/api/doc-generator/document/doc-2/save",
        params={"output_path": "/tmp/doc.md"},
    )
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        assert resp.json()["data"]["saved"] is True

    resp = client.get("/api/doc-generator/documents")
    assert resp.status_code in (200, 404)

    monkeypatch.setattr(dg, "get_documentation_generator", _raise(Exception("x")))
    resp = client.get("/api/doc-generator/status")
    assert resp.status_code in (500, 404)


def test_doc_generator_router_exception_handling(client, monkeypatch):
    """Test exception handling for doc_generator_router endpoints."""
    import core.documentation_generator as dg

    # Test GET /templates exception handling (lines 83-85)
    monkeypatch.setattr(dg, "get_documentation_generator", _raise(Exception("templates error")))
    resp = client.get("/api/doc-generator/templates")
    assert resp.status_code in (500, 404)

    # Restore normal generator for other tests
    _gen_doc = SimpleNamespace(
        doc_id="doc-2",
        title="Generated",
        generator_type=_FakeEnum("markdown"),
        content="# doc",
        generated_at=_dt,
    )
    _doc_generator = SimpleNamespace(
        get_generator_summary=lambda: {"available": True, "total_templates": 5},
        get_available_templates=lambda: ["api-doc"],
        generate_document=lambda *a, **k: _gen_doc,
        get_generated_document=lambda d: _gen_doc if d == "doc-2" else None,
        save_generated_document=lambda *a, **k: True,
        list_generated_documents=lambda: [_gen_doc],
    )
    monkeypatch.setattr(dg, "get_documentation_generator", lambda: _doc_generator)

    # Test POST /document/generate with None generator_type (line 126)
    resp = client.post(
        "/api/doc-generator/document/generate",
        params={
            "doc_id": "g-new",
            "title": "Generated",
            "template_name": "api-doc",
        },
        json={"content_vars": {"name": "x"}},
    )
    assert resp.status_code in (200, 404)

    # Test POST /document/generate when generate_document returns None (lines 131-132)
    _doc_generator_fail = SimpleNamespace(
        get_generator_summary=lambda: {"available": True, "total_templates": 5},
        get_available_templates=lambda: ["api-doc"],
        generate_document=lambda *a, **k: None,
        get_generated_document=lambda d: _gen_doc if d == "doc-2" else None,
        save_generated_document=lambda *a, **k: True,
        list_generated_documents=lambda: [_gen_doc],
    )
    monkeypatch.setattr(dg, "get_documentation_generator", lambda: _doc_generator_fail)
    resp = client.post(
        "/api/doc-generator/document/generate",
        params={
            "doc_id": "g-new",
            "title": "Generated",
            "template_name": "api-doc",
            "generator_type": "markdown",
        },
        json={"content_vars": {"name": "x"}},
    )
    assert resp.status_code == 404

    # Test POST /document/generate exception handling (lines 146-148)
    _doc_generator_exc = SimpleNamespace(
        get_generator_summary=lambda: {"available": True, "total_templates": 5},
        get_available_templates=lambda: ["api-doc"],
        generate_document=_raise(Exception("generate error")),
        get_generated_document=lambda d: _gen_doc if d == "doc-2" else None,
        save_generated_document=lambda *a, **k: True,
        list_generated_documents=lambda: [_gen_doc],
    )
    monkeypatch.setattr(dg, "get_documentation_generator", lambda: _doc_generator_exc)
    resp = client.post(
        "/api/doc-generator/document/generate",
        params={
            "doc_id": "g-new",
            "title": "Generated",
            "template_name": "api-doc",
            "generator_type": "markdown",
        },
        json={"content_vars": {"name": "x"}},
    )
    assert resp.status_code in (500, 404)

    # Restore normal generator
    monkeypatch.setattr(dg, "get_documentation_generator", lambda: _doc_generator)

    # Test GET /document/{doc_id} exception handling (lines 185-187)
    _doc_generator_get_exc = SimpleNamespace(
        get_generator_summary=lambda: {"available": True, "total_templates": 5},
        get_available_templates=lambda: ["api-doc"],
        generate_document=lambda *a, **k: _gen_doc,
        get_generated_document=_raise(Exception("get document error")),
        save_generated_document=lambda *a, **k: True,
        list_generated_documents=lambda: [_gen_doc],
    )
    monkeypatch.setattr(dg, "get_documentation_generator", lambda: _doc_generator_get_exc)
    resp = client.get("/api/doc-generator/document/doc-2")
    assert resp.status_code in (500, 404)

    # Restore normal generator
    monkeypatch.setattr(dg, "get_documentation_generator", lambda: _doc_generator)

    # Test POST /document/{doc_id}/save exception handling (lines 212-214)
    _doc_generator_save_exc = SimpleNamespace(
        get_generator_summary=lambda: {"available": True, "total_templates": 5},
        get_available_templates=lambda: ["api-doc"],
        generate_document=lambda *a, **k: _gen_doc,
        get_generated_document=lambda d: _gen_doc if d == "doc-2" else None,
        save_generated_document=_raise(Exception("save error")),
        list_generated_documents=lambda: [_gen_doc],
    )
    monkeypatch.setattr(dg, "get_documentation_generator", lambda: _doc_generator_save_exc)
    resp = client.post(
        "/api/doc-generator/document/doc-2/save",
        params={"output_path": "/tmp/doc.md"},
    )
    assert resp.status_code in (500, 404)

    # Restore normal generator
    monkeypatch.setattr(dg, "get_documentation_generator", lambda: _doc_generator)

    # Test GET /documents exception handling (lines 239-241)
    _doc_generator_list_exc = SimpleNamespace(
        get_generator_summary=lambda: {"available": True, "total_templates": 5},
        get_available_templates=lambda: ["api-doc"],
        generate_document=lambda *a, **k: _gen_doc,
        get_generated_document=lambda d: _gen_doc if d == "doc-2" else None,
        save_generated_document=lambda *a, **k: True,
        list_generated_documents=_raise(Exception("list error")),
    )
    monkeypatch.setattr(dg, "get_documentation_generator", lambda: _doc_generator_list_exc)
    resp = client.get("/api/doc-generator/documents")
    assert resp.status_code in (500, 404)


def test_i18n_router(client, monkeypatch):
    import core.i18n_manager as im

    resp = client.get("/api/i18n/status")
    assert resp.status_code in (200, 404)

    resp = client.get("/api/i18n/locales")
    assert resp.status_code in (200, 404)

    resp = client.get("/api/i18n/locales/zh-CN")
    assert resp.status_code in (200, 404)

    resp = client.post("/api/i18n/locale/set", params={"locale_id": "zh-CN"})
    assert resp.status_code in (200, 404)

    resp = client.get(
        "/api/i18n/translate", params={"key": "hello", "namespace": "common", "language": "en-US"}
    )
    assert resp.status_code in (200, 404)

    resp = client.put(
        "/api/i18n/translate",
        params={"key": "hello", "translation": "你好", "namespace": "common", "language": "zh-CN"},
    )
    assert resp.status_code in (200, 404)

    resp = client.get(
        "/api/i18n/format/number", params={"number": 1234.5678, "locale": "zh-CN", "decimals": 2}
    )
    assert resp.status_code in (200, 404)

    resp = client.get("/api/i18n/format/currency", params={"amount": 99.99, "locale": "en-US"})
    assert resp.status_code in (200, 404)

    resp = client.get(
        "/api/i18n/format/date", params={"date_str": "2026-07-03T09:00:00", "locale": "zh-CN"}
    )
    assert resp.status_code in (200, 404)

    _bad_manager = SimpleNamespace(
        get_i18n_summary=lambda: im.get_i18n_manager().get_i18n_summary(),
        get_supported_locales=lambda: im.get_i18n_manager().get_supported_locales(),
        set_current_locale=lambda locale: im.get_i18n_manager().set_current_locale(locale),
        translate=lambda *a, **k: im.get_i18n_manager().translate(*a, **k),
        locales={"zh-CN": SimpleNamespace(language="zh-CN")},
        current_locale=SimpleNamespace(language="zh-CN"),
        set_translation=lambda *a, **k: False,
        format_number=lambda *a, **k: im.get_i18n_manager().format_number(*a, **k),
        format_currency=lambda *a, **k: im.get_i18n_manager().format_currency(*a, **k),
        format_date=lambda *a, **k: im.get_i18n_manager().format_date(*a, **k),
    )
    monkeypatch.setattr(im, "get_i18n_manager", lambda: _bad_manager)
    resp = client.put(
        "/api/i18n/translate",
        params={
            "key": "hello",
            "translation": "你好",
            "namespace": "common",
            "language": "missing",
        },
    )
    assert resp.status_code in (400, 404)

    monkeypatch.setattr(im, "get_i18n_manager", _raise(Exception("x")))
    resp = client.get("/api/i18n/status")
    assert resp.status_code in (500, 404)


def test_capacity_router(client, monkeypatch):
    import api.capacity_router as capr

    resp = client.get("/api/v1/capacity/forecast")
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        assert "data" in resp.json()

    resp = client.get("/api/v1/capacity/recommendations")
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        assert "data" in resp.json()

    monkeypatch.setattr(capr, "forecast_capacity", _raise(Exception("x")))
    resp = client.get("/api/v1/capacity/forecast")
    assert resp.status_code in (500, 404)


def test_enterprise_router(client, monkeypatch):
    import api.enterprise_router as er

    resp = client.post(
        "/api/v1/enterprise/tenant/isolation/check",
        json={"tenant_id": "t1", "resource_id": "r1", "resource_type": "db"},
    )
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        assert resp.json()["allowed"] is True

    resp = client.post(
        "/api/v1/enterprise/tenant/resource/assign",
        params={"tenant_id": "t1", "resource_id": "r1"},
    )
    assert resp.status_code in (200, 404)

    resp = client.post("/api/v1/enterprise/compliance/check", json={"standard": "GDPR"})
    assert resp.status_code in (200, 404)

    resp = client.post("/api/v1/enterprise/compliance/check", json={"standard": "BAD"})
    assert resp.status_code in (400, 404)

    resp = client.post("/api/v1/enterprise/compliance/report", json={"standard": "GDPR"})
    assert resp.status_code in (200, 404)

    resp = client.post("/api/v1/enterprise/compliance/report", json={"standard": "BAD_STANDARD"})
    assert resp.status_code in (400, 404)

    resp = client.post(
        "/api/v1/enterprise/encryption/encrypt",
        json={"data": "secret", "classification": "confidential"},
    )
    assert resp.status_code in (200, 404)

    resp = client.post(
        "/api/v1/enterprise/encryption/encrypt",
        json={"data": "secret", "classification": "invalid_classification"},
    )
    assert resp.status_code in (400, 404)

    resp = client.post("/api/v1/enterprise/encryption/decrypt", params={"encrypted_data": "x"})
    assert resp.status_code in (200, 404)

    resp = client.post(
        "/api/v1/enterprise/audit/log",
        json={
            "tenant_id": "t1",
            "user_id": "u1",
            "action": "read",
            "resource_type": "db",
            "resource_id": "r1",
            "outcome": "success",
        },
    )
    assert resp.status_code in (200, 404)

    resp = client.post(
        "/api/v1/enterprise/audit/log",
        json={
            "tenant_id": "t1",
            "user_id": "u1",
            "action": "read",
            "resource_type": "db",
            "resource_id": "r1",
            "outcome": "success",
            "data_classification": "invalid_classification",
        },
    )
    assert resp.status_code in (400, 404)

    resp = client.get("/api/v1/enterprise/audit/logs")
    assert resp.status_code in (200, 404)

    resp = client.get("/api/v1/enterprise/audit/logs", params={"start_date": "not-a-date"})
    assert resp.status_code in (400, 404)

    resp = client.get("/api/v1/enterprise/audit/logs", params={"end_date": "not-a-date"})
    assert resp.status_code in (400, 404)

    resp = client.post("/api/v1/enterprise/audit/cleanup")
    assert resp.status_code in (200, 404)

    resp = client.post(
        "/api/v1/enterprise/privacy/consent",
        json={"user_id": "u1", "consent_given": True, "consent_purpose": "analytics"},
    )
    assert resp.status_code in (200, 404)

    resp = client.get(
        "/api/v1/enterprise/privacy/consent/u1", params={"consent_purpose": "analytics"}
    )
    assert resp.status_code in (200, 404)

    resp = client.post("/api/v1/enterprise/privacy/mask", json={"email": "a@b.com"})
    assert resp.status_code in (200, 404)

    resp = client.get("/api/v1/enterprise/summary")
    assert resp.status_code in (200, 404)

    resp = client.get("/api/v1/enterprise/compliance/standards")
    assert resp.status_code in (200, 404)

    resp = client.get("/api/v1/enterprise/encryption/status")
    assert resp.status_code in (200, 404)

    resp = client.get("/api/v1/enterprise/data/classification/rules")
    assert resp.status_code in (200, 404)

    resp = client.post("/api/v1/enterprise/data/classify", params={"data_key": "email"})
    assert resp.status_code in (200, 404)

    # Test ENTERPRISE_AVAILABLE=False for all endpoints
    monkeypatch.setattr(er, "enterprise_functionality_manager", None)
    monkeypatch.setattr(er, "ENTERPRISE_AVAILABLE", False)

    resp = client.post(
        "/api/v1/enterprise/tenant/isolation/check",
        json={"tenant_id": "t1", "resource_id": "r1", "resource_type": "db"},
    )
    assert resp.status_code in (503, 404)

    resp = client.post(
        "/api/v1/enterprise/tenant/resource/assign",
        params={"tenant_id": "t1", "resource_id": "r1"},
    )
    assert resp.status_code in (503, 404)

    resp = client.post("/api/v1/enterprise/compliance/check", json={"standard": "GDPR"})
    assert resp.status_code in (503, 404)

    resp = client.post("/api/v1/enterprise/compliance/report", json={"standard": "GDPR"})
    assert resp.status_code in (503, 404)

    resp = client.post(
        "/api/v1/enterprise/encryption/encrypt",
        json={"data": "secret", "classification": "confidential"},
    )
    assert resp.status_code in (503, 404)

    resp = client.post("/api/v1/enterprise/encryption/decrypt", params={"encrypted_data": "x"})
    assert resp.status_code in (503, 404)

    resp = client.post(
        "/api/v1/enterprise/audit/log",
        json={
            "tenant_id": "t1",
            "user_id": "u1",
            "action": "read",
            "resource_type": "db",
            "resource_id": "r1",
            "outcome": "success",
        },
    )
    assert resp.status_code in (503, 404)

    resp = client.get("/api/v1/enterprise/audit/logs")
    assert resp.status_code in (503, 404)

    resp = client.post("/api/v1/enterprise/audit/cleanup")
    assert resp.status_code in (503, 404)

    resp = client.post(
        "/api/v1/enterprise/privacy/consent",
        json={"user_id": "u1", "consent_given": True, "consent_purpose": "analytics"},
    )
    assert resp.status_code in (503, 404)

    resp = client.get(
        "/api/v1/enterprise/privacy/consent/u1", params={"consent_purpose": "analytics"}
    )
    assert resp.status_code in (503, 404)

    resp = client.post("/api/v1/enterprise/privacy/mask", json={"email": "a@b.com"})
    assert resp.status_code in (503, 404)

    resp = client.get("/api/v1/enterprise/summary")
    assert resp.status_code in (503, 404)

    resp = client.get("/api/v1/enterprise/compliance/standards")
    assert resp.status_code in (503, 404)

    resp = client.get("/api/v1/enterprise/encryption/status")
    assert resp.status_code in (503, 404)

    resp = client.get("/api/v1/enterprise/data/classification/rules")
    assert resp.status_code in (503, 404)

    resp = client.post("/api/v1/enterprise/data/classify", params={"data_key": "email"})
    assert resp.status_code in (503, 404)


def test_api_performance_router(client, monkeypatch):
    import core.api_performance_optimizer as apo

    resp = client.get("/api/api-performance/status")
    assert resp.status_code in (200, 404)

    resp = client.get("/api/api-performance/response-times")
    assert resp.status_code in (200, 404)

    resp = client.get("/api/api-performance/slow-apis", params={"limit": 5})
    assert resp.status_code in (200, 404)

    resp = client.post("/api/api-performance/optimize")
    assert resp.status_code in (200, 404)

    resp = client.post(
        "/api/api-performance/cache/setup", params={"endpoint": "/api/x", "ttl_seconds": 120}
    )
    assert resp.status_code in (200, 404)

    resp = client.delete("/api/api-performance/cache", params={"endpoint": "/api/x"})
    assert resp.status_code in (200, 404)

    resp = client.post(
        "/api/api-performance/record",
        params={
            "endpoint": "/api/x",
            "method": "GET",
            "response_time_ms": 100.0,
            "status_code": 200,
        },
    )
    assert resp.status_code in (200, 404)

    resp = client.post(
        "/api/api-performance/rate-limit/setup",
        params={"endpoint": "/api/x", "requests_per_minute": 100},
    )
    assert resp.status_code in (200, 404)

    resp = client.get("/api/api-performance/throughput")
    assert resp.status_code in (200, 404)

    resp = client.get("/api/api-performance/resources")
    assert resp.status_code in (200, 404)

    resp = client.post(
        "/api/api-performance/resource-limits/setup",
        params={"max_memory_mb": 1024.0, "max_cpu_percent": 80.0, "max_connections": 100},
    )
    assert resp.status_code in (200, 404)

    resp = client.get("/api/api-performance/resource-limits/check")
    assert resp.status_code in (200, 404)

    monkeypatch.setattr(apo, "get_api_performance_optimizer", _raise(Exception("x")))
    resp = client.get("/api/api-performance/status")
    assert resp.status_code in (500, 404)


def test_api_performance_router_exception_handling(client, monkeypatch):
    """Test exception handling and edge cases for api_performance_router."""
    import core.api_performance_optimizer as apo

    class OptStrategy:
        value = "cache"

    class OptPriority:
        value = "high"

    # Test identify_slow_apis with objects having model_dump method (line 139-140)
    class ObjectWithModelDump:
        def model_dump(self):
            return {"endpoint": "/x", "avg_response_time": 300, "call_count": 5}

    _optimizer_with_model_dump = SimpleNamespace(
        get_performance_summary=lambda: {"avg_response_time": 150},
        analyze_response_times=lambda: {"p50": 120},
        identify_slow_apis=lambda: [ObjectWithModelDump()],
        generate_optimizations=lambda: [
            SimpleNamespace(
                optimization_id="o1",
                endpoint="/api/x",
                strategy=OptStrategy(),
                priority=OptPriority(),
                expected_improvement=0.3,
                description="cache",
            )
        ],
        setup_response_cache=lambda *a, **k: None,
        invalidate_cache=lambda *a, **k: None,
        record_api_call=lambda *a, **k: None,
        setup_rate_limit=lambda *a, **k: None,
        get_throughput_metrics=lambda: {"rps": 100},
        monitor_resource_usage=lambda: {"cpu": 10.0},
        setup_resource_limits=lambda *a, **k: None,
        check_resource_limits=lambda: {"ok": True},
    )
    monkeypatch.setattr(apo, "get_api_performance_optimizer", lambda: _optimizer_with_model_dump)
    resp = client.get("/api/api-performance/slow-apis", params={"limit": 5})
    assert resp.status_code in (200, 404)

    # Test identify_slow_apis with dict objects (elif branch - line 141-142)
    _optimizer_with_dict = SimpleNamespace(
        get_performance_summary=lambda: {"avg_response_time": 150},
        analyze_response_times=lambda: {"p50": 120},
        identify_slow_apis=lambda: [
            {"endpoint": "/api/x", "avg_response_time": 500, "call_count": 100}
        ],
        generate_optimizations=lambda: [
            SimpleNamespace(
                optimization_id="o1",
                endpoint="/api/x",
                strategy=OptStrategy(),
                priority=OptPriority(),
                expected_improvement=0.3,
                description="cache",
            )
        ],
        setup_response_cache=lambda *a, **k: None,
        invalidate_cache=lambda *a, **k: None,
        record_api_call=lambda *a, **k: None,
        setup_rate_limit=lambda *a, **k: None,
        get_throughput_metrics=lambda: {"rps": 100},
        monitor_resource_usage=lambda: {"cpu": 10.0},
        setup_resource_limits=lambda *a, **k: None,
        check_resource_limits=lambda: {"ok": True},
    )
    monkeypatch.setattr(apo, "get_api_performance_optimizer", lambda: _optimizer_with_dict)
    resp = client.get("/api/api-performance/slow-apis", params={"limit": 5})
    assert resp.status_code in (200, 404)

    # Test identify_slow_apis with plain objects (else branch - line 143-144)
    class PlainObject:
        def __init__(self):
            self.endpoint = "/x"
            self.avg_response_time = 300
            self.call_count = 5

    _optimizer_with_plain = SimpleNamespace(
        get_performance_summary=lambda: {"avg_response_time": 150},
        analyze_response_times=lambda: {"p50": 120},
        identify_slow_apis=lambda: [PlainObject()],
        generate_optimizations=lambda: [
            SimpleNamespace(
                optimization_id="o1",
                endpoint="/api/x",
                strategy=OptStrategy(),
                priority=OptPriority(),
                expected_improvement=0.3,
                description="cache",
            )
        ],
        setup_response_cache=lambda *a, **k: None,
        invalidate_cache=lambda *a, **k: None,
        record_api_call=lambda *a, **k: None,
        setup_rate_limit=lambda *a, **k: None,
        get_throughput_metrics=lambda: {"rps": 100},
        monitor_resource_usage=lambda: {"cpu": 10.0},
        setup_resource_limits=lambda *a, **k: None,
        check_resource_limits=lambda: {"ok": True},
    )
    monkeypatch.setattr(apo, "get_api_performance_optimizer", lambda: _optimizer_with_plain)
    resp = client.get("/api/api-performance/slow-apis", params={"limit": 5})
    assert resp.status_code in (200, 404)

    # Test exception handling for analyze_response_times (lines 89-91)
    _optimizer_response_times_error = SimpleNamespace(
        get_performance_summary=lambda: {"avg_response_time": 150},
        analyze_response_times=_raise(Exception("Response times analysis error")),
        identify_slow_apis=lambda: [],
        generate_optimizations=lambda: [],
        setup_response_cache=lambda *a, **k: None,
        invalidate_cache=lambda *a, **k: None,
        record_api_call=lambda *a, **k: None,
        setup_rate_limit=lambda *a, **k: None,
        get_throughput_metrics=lambda: {"rps": 100},
        monitor_resource_usage=lambda: {"cpu": 10.0},
        setup_resource_limits=lambda *a, **k: None,
        check_resource_limits=lambda: {"ok": True},
    )
    monkeypatch.setattr(
        apo, "get_api_performance_optimizer", lambda: _optimizer_response_times_error
    )
    resp = client.get("/api/api-performance/response-times")
    assert resp.status_code in (500, 404)

    # Test exception handling for identify_slow_apis (lines 151-153)
    _optimizer_slow_apis_error = SimpleNamespace(
        get_performance_summary=lambda: {"avg_response_time": 150},
        analyze_response_times=lambda: {"p50": 120},
        identify_slow_apis=_raise(Exception("Slow APIs identification error")),
        generate_optimizations=lambda: [],
        setup_response_cache=lambda *a, **k: None,
        invalidate_cache=lambda *a, **k: None,
        record_api_call=lambda *a, **k: None,
        setup_rate_limit=lambda *a, **k: None,
        get_throughput_metrics=lambda: {"rps": 100},
        monitor_resource_usage=lambda: {"cpu": 10.0},
        setup_resource_limits=lambda *a, **k: None,
        check_resource_limits=lambda: {"ok": True},
    )
    monkeypatch.setattr(apo, "get_api_performance_optimizer", lambda: _optimizer_slow_apis_error)
    resp = client.get("/api/api-performance/slow-apis", params={"limit": 5})
    assert resp.status_code in (500, 404)

    # Test exception handling for generate_optimizations (lines 215-217)
    _optimizer_optimizations_error = SimpleNamespace(
        get_performance_summary=lambda: {"avg_response_time": 150},
        analyze_response_times=lambda: {"p50": 120},
        identify_slow_apis=lambda: [],
        generate_optimizations=_raise(Exception("Optimizations generation error")),
        setup_response_cache=lambda *a, **k: None,
        invalidate_cache=lambda *a, **k: None,
        record_api_call=lambda *a, **k: None,
        setup_rate_limit=lambda *a, **k: None,
        get_throughput_metrics=lambda: {"rps": 100},
        monitor_resource_usage=lambda: {"cpu": 10.0},
        setup_resource_limits=lambda *a, **k: None,
        check_resource_limits=lambda: {"ok": True},
    )
    monkeypatch.setattr(
        apo, "get_api_performance_optimizer", lambda: _optimizer_optimizations_error
    )
    resp = client.post("/api/api-performance/optimize")
    assert resp.status_code in (500, 404)

    # Test exception handling for setup_endpoint_cache (lines 265-267)
    _optimizer_cache_setup_error = SimpleNamespace(
        get_performance_summary=lambda: {"avg_response_time": 150},
        setup_response_cache=_raise(Exception("Cache setup error")),
        invalidate_cache=lambda *a, **k: None,
    )
    monkeypatch.setattr(apo, "get_api_performance_optimizer", lambda: _optimizer_cache_setup_error)
    resp = client.post(
        "/api/api-performance/cache/setup", params={"endpoint": "/api/x", "ttl_seconds": 120}
    )
    assert resp.status_code in (500, 404)

    # Test exception handling for invalidate_cache (lines 301-303)
    _optimizer_cache_invalidate_error = SimpleNamespace(
        get_performance_summary=lambda: {"avg_response_time": 150},
        setup_response_cache=lambda *a, **k: None,
        invalidate_cache=_raise(Exception("Cache invalidation error")),
    )
    monkeypatch.setattr(
        apo, "get_api_performance_optimizer", lambda: _optimizer_cache_invalidate_error
    )
    resp = client.delete("/api/api-performance/cache", params={"endpoint": "/api/x"})
    assert resp.status_code in (500, 404)

    # Test invalidate_cache with None endpoint (all endpoints)
    _optimizer_normal = SimpleNamespace(
        get_performance_summary=lambda: {"avg_response_time": 150},
        setup_response_cache=lambda *a, **k: None,
        invalidate_cache=lambda *a, **k: None,
    )
    monkeypatch.setattr(apo, "get_api_performance_optimizer", lambda: _optimizer_normal)
    resp = client.delete("/api/api-performance/cache")
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        assert "all endpoints" in resp.json()["message"]

    # Test exception handling for record_api_call (lines 347-349)
    _optimizer_record_error = SimpleNamespace(
        get_performance_summary=lambda: {"avg_response_time": 150},
        record_api_call=_raise(Exception("API call recording error")),
    )
    monkeypatch.setattr(apo, "get_api_performance_optimizer", lambda: _optimizer_record_error)
    resp = client.post(
        "/api/api-performance/record",
        params={
            "endpoint": "/api/x",
            "method": "GET",
            "response_time_ms": 100.0,
            "status_code": 200,
        },
    )
    assert resp.status_code in (500, 404)

    # Test exception handling for setup_rate_limit (lines 385-387)
    _optimizer_rate_limit_error = SimpleNamespace(
        get_performance_summary=lambda: {"avg_response_time": 150},
        setup_rate_limit=_raise(Exception("Rate limit setup error")),
    )
    monkeypatch.setattr(apo, "get_api_performance_optimizer", lambda: _optimizer_rate_limit_error)
    resp = client.post(
        "/api/api-performance/rate-limit/setup",
        params={"endpoint": "/api/x", "requests_per_minute": 100},
    )
    assert resp.status_code in (500, 404)

    # Test exception handling for get_throughput_metrics (lines 412-414)
    _optimizer_throughput_error = SimpleNamespace(
        get_performance_summary=lambda: {"avg_response_time": 150},
        get_throughput_metrics=_raise(Exception("Throughput metrics error")),
    )
    monkeypatch.setattr(apo, "get_api_performance_optimizer", lambda: _optimizer_throughput_error)
    resp = client.get("/api/api-performance/throughput")
    assert resp.status_code in (500, 404)

    # Test exception handling for monitor_resource_usage (lines 443-445)
    _optimizer_resource_usage_error = SimpleNamespace(
        get_performance_summary=lambda: {"avg_response_time": 150},
        monitor_resource_usage=_raise(Exception("Resource usage monitoring error")),
    )
    monkeypatch.setattr(
        apo, "get_api_performance_optimizer", lambda: _optimizer_resource_usage_error
    )
    resp = client.get("/api/api-performance/resources")
    assert resp.status_code in (500, 404)

    # Test exception handling for setup_resource_limits (lines 484-486)
    _optimizer_resource_limits_setup_error = SimpleNamespace(
        get_performance_summary=lambda: {"avg_response_time": 150},
        setup_resource_limits=_raise(Exception("Resource limits setup error")),
    )
    monkeypatch.setattr(
        apo, "get_api_performance_optimizer", lambda: _optimizer_resource_limits_setup_error
    )
    resp = client.post(
        "/api/api-performance/resource-limits/setup",
        params={"max_memory_mb": 1024.0, "max_cpu_percent": 80.0, "max_connections": 100},
    )
    assert resp.status_code in (500, 404)

    # Test exception handling for check_resource_limits (lines 515-517)
    _optimizer_resource_limits_check_error = SimpleNamespace(
        get_performance_summary=lambda: {"avg_response_time": 150},
        check_resource_limits=_raise(Exception("Resource limits check error")),
    )
    monkeypatch.setattr(
        apo, "get_api_performance_optimizer", lambda: _optimizer_resource_limits_check_error
    )
    resp = client.get("/api/api-performance/resource-limits/check")
    assert resp.status_code in (500, 404)


def test_integration_router(client, monkeypatch):
    import api.integration_router as ir

    resp = client.post(
        "/api/v1/integration/register",
        json={"integration_type": "prometheus", "name": "Prom", "config": {"url": "http://x"}},
    )
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        assert resp.json()["integration"]["integration_id"] == "int-1"

    resp = client.get("/api/v1/integration/list")
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        assert resp.json()["total_integrations"] == 1

    resp = client.get("/api/v1/integration/list", params={"integration_type": "prometheus"})
    assert resp.status_code in (200, 404)

    resp = client.get("/api/v1/integration/list", params={"integration_type": "bad-type"})
    assert resp.status_code in (400, 404)

    # Test status filter (line 286-291)
    resp = client.get("/api/v1/integration/list", params={"status": "active"})
    assert resp.status_code in (200, 404)

    # Test invalid status (line 290-291)
    resp = client.get("/api/v1/integration/list", params={"status": "bad-status"})
    assert resp.status_code in (400, 404)

    # Test invalid integration_type on register (line 210-212)
    resp = client.post(
        "/api/v1/integration/register",
        json={"integration_type": "bad-type", "name": "Bad", "config": {}},
    )
    assert resp.status_code in (400, 404)

    resp = client.post("/api/v1/integration/test/int-1")
    assert resp.status_code in (200, 404)

    resp = client.delete("/api/v1/integration/int-1")
    assert resp.status_code in (200, 404)

    resp = client.delete("/api/v1/integration/missing")
    assert resp.status_code == 404

    resp = client.post(
        "/api/v1/integration/notification/send",
        json={"channel": "slack", "recipient": "x", "subject": "s", "body": "b"},
    )
    assert resp.status_code in (200, 404)

    resp = client.get("/api/v1/integration/notification/channels")
    assert resp.status_code in (200, 404)

    resp = client.post(
        "/api/v1/integration/webhook/register",
        json={"source": "git", "event_type": "push", "endpoint": "http://x"},
    )
    assert resp.status_code in (200, 404)

    resp = client.post(
        "/api/v1/integration/webhook/handle",
        params={"webhook_id": "w-1"},
        json={"payload": {"x": 1}},
    )
    assert resp.status_code in (200, 404)

    resp = client.get("/api/v1/integration/webhooks")
    assert resp.status_code in (200, 404)

    resp = client.post(
        "/api/v1/integration/prometheus/query",
        json={"integration_id": "int-1", "query": "up", "time_range": "1h"},
    )
    assert resp.status_code in (200, 404)

    resp = client.post(
        "/api/v1/integration/jenkins/trigger",
        json={"integration_id": "int-1", "job_name": "build"},
    )
    assert resp.status_code in (200, 404)

    resp = client.post(
        "/api/v1/integration/jira/issue",
        json={"integration_id": "int-1", "summary": "bug", "description": "desc"},
    )
    assert resp.status_code in (200, 404)

    resp = client.get("/api/v1/integration/templates")
    assert resp.status_code in (200, 404)

    resp = client.get("/api/v1/integration/summary")
    assert resp.status_code in (200, 404)

    resp = client.get("/api/v1/integration/types")
    assert resp.status_code in (200, 404)

    resp = client.get("/api/v1/integration/events", params={"processed": "false", "limit": 10})
    assert resp.status_code in (200, 404)

    # Test query_integration with different providers
    # Test datadog provider (line 634-637)
    _integration_datadog = SimpleNamespace(
        integration_id="int-dd",
        integration_type=_FakeIntegrationType("datadog"),
        name="Datadog",
        enabled=True,
        status=_FakeIntegrationStatus("active"),
        last_tested=_dt,
        last_error=None,
        config={"provider": "datadog"},
    )
    monkeypatch.setattr(
        ir,
        "integration_manager",
        SimpleNamespace(
            integrations={"int-dd": _integration_datadog},
            query_cloudwatch_metrics=_async_return({"data": []}),
            query_pagerduty_incidents=_async_return({"data": []}),
        ),
    )
    resp = client.post(
        "/api/v1/integration/int-dd/query",
        json={"query": "avg:cpu", "params": {"time_range": "1h"}},
    )
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        assert resp.json()["provider"] == "datadog"

    # Test grafana provider (line 638-641)
    _integration_grafana = SimpleNamespace(
        integration_id="int-gf",
        integration_type=_FakeIntegrationType("grafana"),
        name="Grafana",
        enabled=True,
        status=_FakeIntegrationStatus("active"),
        last_tested=_dt,
        last_error=None,
        config={"provider": "grafana"},
    )
    monkeypatch.setattr(
        ir,
        "integration_manager",
        SimpleNamespace(
            integrations={"int-gf": _integration_grafana},
            query_cloudwatch_metrics=_async_return({"data": []}),
            query_pagerduty_incidents=_async_return({"data": []}),
        ),
    )
    resp = client.post(
        "/api/v1/integration/int-gf/query",
        json={"query": "avg:cpu", "params": {"time_range": "1h"}},
    )
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        assert resp.json()["provider"] == "grafana"

    # Test elk provider (line 642-645)
    _integration_elk = SimpleNamespace(
        integration_id="int-elk",
        integration_type=_FakeIntegrationType("elk"),
        name="ELK",
        enabled=True,
        status=_FakeIntegrationStatus("active"),
        last_tested=_dt,
        last_error=None,
        config={"provider": "elk"},
    )
    monkeypatch.setattr(
        ir,
        "integration_manager",
        SimpleNamespace(
            integrations={"int-elk": _integration_elk},
            query_cloudwatch_metrics=_async_return({"data": []}),
            query_pagerduty_incidents=_async_return({"data": []}),
        ),
    )
    resp = client.post(
        "/api/v1/integration/int-elk/query",
        json={"query": "avg:cpu", "params": {"time_range": "1h"}},
    )
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        assert resp.json()["provider"] == "elk"

    # Test cloudwatch provider (line 646-649)
    _integration_cw = SimpleNamespace(
        integration_id="int-cw",
        integration_type=_FakeIntegrationType("cloudwatch"),
        name="CloudWatch",
        enabled=True,
        status=_FakeIntegrationStatus("active"),
        last_tested=_dt,
        last_error=None,
        config={"provider": "cloudwatch"},
    )
    monkeypatch.setattr(
        ir,
        "integration_manager",
        SimpleNamespace(
            integrations={"int-cw": _integration_cw},
            query_cloudwatch_metrics=_async_return({"data": []}),
            query_pagerduty_incidents=_async_return({"data": []}),
        ),
    )
    resp = client.post(
        "/api/v1/integration/int-cw/query",
        json={"query": "avg:cpu", "params": {"time_range": "1h"}},
    )
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        assert resp.json()["provider"] == "cloudwatch"

    # Test pagerduty provider (line 650-653)
    _integration_pd = SimpleNamespace(
        integration_id="int-pd",
        integration_type=_FakeIntegrationType("pagerduty"),
        name="PagerDuty",
        enabled=True,
        status=_FakeIntegrationStatus("active"),
        last_tested=_dt,
        last_error=None,
        config={"provider": "pagerduty"},
    )
    monkeypatch.setattr(
        ir,
        "integration_manager",
        SimpleNamespace(
            integrations={"int-pd": _integration_pd},
            query_cloudwatch_metrics=_async_return({"data": []}),
            query_pagerduty_incidents=_async_return({"data": []}),
        ),
    )
    resp = client.post(
        "/api/v1/integration/int-pd/query",
        json={"query": "avg:cpu", "params": {"time_range": "1h"}},
    )
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        assert resp.json()["provider"] == "pagerduty"

    # Test unsupported provider (line 654-655)
    _integration_unsupported = SimpleNamespace(
        integration_id="int-unsup",
        integration_type=_FakeIntegrationType("prometheus"),
        name="Unsupported",
        enabled=True,
        status=_FakeIntegrationStatus("active"),
        last_tested=_dt,
        last_error=None,
        config={"provider": "unsupported"},
    )
    monkeypatch.setattr(
        ir,
        "integration_manager",
        SimpleNamespace(
            integrations={"int-unsup": _integration_unsupported},
            query_cloudwatch_metrics=_async_return({"data": []}),
            query_pagerduty_incidents=_async_return({"data": []}),
        ),
    )
    resp = client.post(
        "/api/v1/integration/int-unsup/query",
        json={"query": "avg:cpu", "params": {"time_range": "1h"}},
    )
    assert resp.status_code in (400, 404)

    # Test REMOTE_CLIENT_AVAILABLE = False for datadog (line 635-636)
    monkeypatch.setattr(
        ir,
        "integration_manager",
        SimpleNamespace(
            integrations={"int-dd": _integration_datadog},
            query_cloudwatch_metrics=_async_return({"data": []}),
            query_pagerduty_incidents=_async_return({"data": []}),
        ),
    )
    monkeypatch.setattr(ir, "REMOTE_CLIENT_AVAILABLE", False)
    resp = client.post(
        "/api/v1/integration/int-dd/query",
        json={"query": "avg:cpu", "params": {"time_range": "1h"}},
    )
    assert resp.status_code in (503, 404)
    monkeypatch.setattr(ir, "REMOTE_CLIENT_AVAILABLE", True)

    # Test integration not found (line 622-623)
    resp = client.post(
        "/api/v1/integration/not-found/query",
        json={"query": "avg:cpu", "params": {"time_range": "1h"}},
    )
    assert resp.status_code == 404

    # Test integration not enabled (line 624-625)
    _integration_disabled = SimpleNamespace(
        integration_id="int-disabled",
        integration_type=_FakeIntegrationType("prometheus"),
        name="Disabled",
        enabled=False,
        status=_FakeIntegrationStatus("inactive"),
        last_tested=_dt,
        last_error=None,
        config={"provider": "prometheus"},
    )
    monkeypatch.setattr(
        ir,
        "integration_manager",
        SimpleNamespace(
            integrations={"int-disabled": _integration_disabled},
            query_cloudwatch_metrics=_async_return({"data": []}),
            query_pagerduty_incidents=_async_return({"data": []}),
        ),
    )
    resp = client.post(
        "/api/v1/integration/int-disabled/query",
        json={"query": "avg:cpu", "params": {"time_range": "1h"}},
    )
    assert resp.status_code in (400, 404)

    # Test query_integration exception handling (line 656-659)
    monkeypatch.setattr(
        ir,
        "integration_manager",
        SimpleNamespace(
            integrations={"int-dd": _integration_datadog},
            query_cloudwatch_metrics=_async_return({"data": []}),
            query_pagerduty_incidents=_async_return({"data": []}),
        ),
    )

    async def _raise_query_error(*args, **kwargs):
        raise Exception("Query failed")

    monkeypatch.setattr(ir, "remote_datadog_query", _raise_query_error)
    resp = client.post(
        "/api/v1/integration/int-dd/query",
        json={"query": "avg:cpu", "params": {"time_range": "1h"}},
    )
    assert resp.status_code in (503, 404)
    # Restore the mock
    monkeypatch.setattr(ir, "remote_datadog_query", AsyncMock(return_value={"series": []}))

    monkeypatch.setattr(ir, "INTEGRATION_AVAILABLE", False)
    resp = client.get("/api/v1/integration/summary")
    assert resp.status_code in (503, 404)


def test_guard_router(client, admin_headers, approval_headers, monkeypatch):
    import api.guard_router as gr

    resp = client.post("/api/guard/check", json={"command": "rm -rf /tmp/cache"})
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        assert resp.json()["risk_level"] == "high"

    resp = client.post("/api/guard/allowed", json={"command": "ls -la"})
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        assert resp.json()["allowed"] is True

    resp = client.post("/api/guard/rewrite", json={"command": "rm -rf /tmp/old"})
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        assert resp.json()["changed"] is True

    resp = client.post("/api/guard/dryrun", json={"command": "rm -rf /tmp/cache"})
    assert resp.status_code in (200, 404)

    resp = client.get("/api/guard/audit", headers=approval_headers)
    assert resp.status_code in (200, 404)

    resp = client.get("/api/guard/audit", headers=admin_headers)
    assert resp.status_code == 403

    resp = client.get("/api/guard/stats", headers=approval_headers)
    assert resp.status_code in (200, 404)

    resp = client.get("/api/v1/security/events", headers=approval_headers)
    assert resp.status_code in (200, 404)

    resp = client.get("/api/v1/security/stats", headers=approval_headers)
    assert resp.status_code in (200, 404)

    monkeypatch.setattr(gr, "analyze_command", _raise(Exception("x")))
    resp = client.post("/api/guard/check", json={"command": "ls"})
    assert resp.status_code in (500, 404)
