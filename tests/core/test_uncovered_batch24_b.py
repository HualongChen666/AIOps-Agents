# -*- coding: utf-8 -*-
"""Coverage tests for batch24_b core modules."""

import base64
import importlib.util
import json
import os
from datetime import datetime, timedelta, timezone

import pytest

pytestmark = [pytest.mark.core]

from core.alert_providers.cloudwatch import CloudWatchAlertProvider, _unwrap_sns
from core.alert_providers.pagerduty import (
    PagerDutyAlertProvider,
    _extract_value,
    _safe_float,
)
from core.call_chain_analysis import (
    CallChainAnalysisEngine,
    CallChainNode,
    PerformanceBottleneck,
    Severity,
    get_call_chain_analysis_engine,
)
from core.distributed_storage import (
    DatabaseInstance,
    DatabaseRole,
    DatabaseType,
    DistributedStorageManager,
    ReadWriteRouter,
    RedisClusterAdapter,
    get_distributed_storage_manager,
)
from core.enterprise_features import (
    ComplianceStandard,
    EncryptionLevel,
    EnterpriseFeatures,
    TenantStatus,
)


@pytest.fixture
async def enterprise(monkeypatch):
    """Initialize an EnterpriseFeatures instance with crypto disabled."""
    monkeypatch.setattr("core.enterprise_features.CRYPTO_AVAILABLE", False)
    ef = EnterpriseFeatures()
    await ef.initialize()
    return ef


@pytest.fixture
def distributed_storage(monkeypatch):
    """Provide a DistributedStorageManager with Redis forced into fallback."""
    monkeypatch.setattr("core.distributed_storage.REDIS_AVAILABLE", False)
    monkeypatch.setattr("core.distributed_storage.redis", None)
    return DistributedStorageManager()


def test_pagerduty_helpers():
    assert _safe_float("12.5") == 12.5
    assert _safe_float(None) == 0.0
    assert _safe_float("abc") == 0.0
    assert _extract_value("value is 3.14 in text") == 3.14
    assert _extract_value("no numbers here") == 0.0
    assert _extract_value(123) == 0.0


def test_pagerduty_normalize_payloads():
    provider = PagerDutyAlertProvider()
    assert provider.normalize("invalid") == []
    assert provider.normalize({"messages": []}) == []
    assert len(provider.normalize({})) == 1

    alert = {
        "id": "inc-1",
        "title": "High CPU",
        "description": "CPU at 95%",
        "urgency": "high",
        "status": "triggered",
        "service": {"id": "svc-1", "summary": "web-service", "html_url": "http://svc"},
        "priority": {"name": "P1"},
        "created_at": "2024-01-01T00:00:00Z",
        "value": 95,
    }
    result = provider.normalize([alert])
    assert len(result) == 1
    assert result[0]["source"] == "pagerduty"
    assert result[0]["severity"] == "high"
    assert result[0]["status"] == "firing"
    assert result[0]["service"] == "web-service"
    assert result[0]["value"] == 95.0
    assert result[0]["labels"]["service_id"] == "svc-1"
    assert result[0]["labels"]["priority"] == "P1"


def test_pagerduty_message_wrapping_and_edge_cases():
    provider = PagerDutyAlertProvider()
    out = provider.normalize({"messages": {"title": "wrapped", "service": {}, "urgency": "info"}})
    assert len(out) == 1
    assert out[0]["severity"] == "info"

    out = provider.normalize(
        {"messages": [1, {"title": "keep", "urgency": "warning", "service": {}}]}
    )
    assert len(out) == 1
    assert out[0]["severity"] == "warning"

    out = provider.normalize(
        {
            "title": "fallback",
            "urgency": "page",
            "status": "resolved",
            "service": "not-a-dict",
        }
    )
    assert out[0]["status"] == "resolved"
    assert out[0]["service"] == "pagerduty"

    raw = {
        "title": "t",
        "urgency": "unknown",
        "priority": {},
    }
    alert = provider._normalize_one(raw)
    assert alert["severity"] in ("high", "warning")


def test_cloudwatch_direct_alarm():
    provider = CloudWatchAlertProvider()
    payload = {
        "AlarmName": "cpu-alarm",
        "AlarmDescription": "CPU high",
        "NewStateValue": "ALARM",
        "NewStateReason": "Threshold crossed",
        "StateChangeTime": "2024-01-01T00:00:00Z",
        "Trigger": {
            "MetricName": "CPUUtilization",
            "Namespace": "AWS/EC2",
            "Dimensions": [
                {"Name": "InstanceId", "Value": "i-123"},
                {"name": "service", "value": "web"},
            ],
            "Threshold": 80.0,
        },
    }
    alerts = provider.normalize(payload)
    assert len(alerts) == 1
    assert alerts[0]["source"] == "cloudwatch"
    assert alerts[0]["severity"] == "critical"
    assert alerts[0]["status"] == "firing"
    assert alerts[0]["metric"] == "AWS/EC2/CPUUtilization"
    assert alerts[0]["host"] == "i-123"
    assert alerts[0]["service"] == "web"
    assert alerts[0]["value"] == 80.0


def test_cloudwatch_sns_and_variants():
    provider = CloudWatchAlertProvider()
    sns_ok = {
        "Type": "Notification",
        "Message": json.dumps(
            {
                "AlarmName": "mem-alarm",
                "NewStateValue": "OK",
                "Trigger": {"MetricName": "Memory", "Namespace": "AWS/Lambda", "Threshold": 128},
            }
        ),
    }
    alerts = provider.normalize(sns_ok)
    assert len(alerts) == 1
    assert alerts[0]["status"] == "resolved"
    assert alerts[0]["severity"] == "warning"

    sns_bad = {"Type": "Notification", "Message": "not-json"}
    assert provider.normalize(sns_bad) == []

    mixed = provider.normalize([1, {"AlarmName": "x"}])
    assert len(mixed) == 1
    assert mixed[0]["title"] == "x"

    direct = {
        "alarms": {"AlarmName": "a", "Trigger": "bad-trigger"},
    }
    out = provider.normalize(direct)
    assert len(out) == 1
    assert out[0]["title"] == "a"


def test_cloudwatch_unwrap_sns():
    assert _unwrap_sns({"foo": "bar"}) == {"foo": "bar"}
    assert _unwrap_sns({"Type": "Notification", "Message": "plain"}) == "plain"
    nested = {"Type": "Notification", "Message": {"AlarmName": "nested"}}
    assert _unwrap_sns(nested) == {"AlarmName": "nested"}


def test_call_chain_bottlenecks_and_anomalies():
    engine = get_call_chain_analysis_engine({})
    now = datetime.now(timezone.utc)
    service, op = "svc", "op"
    durations = [100.0] * 19 + [3000.0]
    for i, d in enumerate(durations):
        engine.add_call_chain(
            f"trace-{i}",
            [
                CallChainNode(
                    span_id=f"s{i}",
                    parent_span_id=None,
                    operation_name=op,
                    service_name=service,
                    start_time=now,
                    end_time=now,
                    duration_ms=d,
                    self_duration_ms=d,
                    status="OK",
                )
            ],
        )
    bottlenecks = engine.analyze_performance_bottlenecks()
    assert len(bottlenecks) >= 1
    assert isinstance(bottlenecks[0], PerformanceBottleneck)
    assert bottlenecks[0].severity in (Severity.HIGH, Severity.CRITICAL)

    anomalies = engine.analyze_anomalies(threshold=2.0)
    assert len(anomalies) >= 1
    assert any(a.severity == Severity.CRITICAL for a in anomalies)

    stats = engine.get_statistics()
    assert stats["total_analyses"] >= 2
    assert stats["bottlenecks_detected"] >= 1
    assert stats["anomalies_detected"] >= 1


def test_call_chain_root_causes():
    engine = get_call_chain_analysis_engine({})
    now = datetime.now(timezone.utc)
    parent = CallChainNode(
        span_id="p1",
        parent_span_id=None,
        operation_name="op",
        service_name="svc",
        start_time=now,
        end_time=now,
        duration_ms=6000.0,
        self_duration_ms=6000.0,
        status="ERROR",
        error_message="timeout connecting to upstream",
    )
    children = [
        CallChainNode(
            span_id=f"c{i+1}",
            parent_span_id="p1",
            operation_name=f"op{i+2}",
            service_name="svc",
            start_time=now,
            end_time=now,
            duration_ms=dur,
            self_duration_ms=dur,
            status="ERROR",
            error_message=msg,
        )
        for i, (dur, msg) in enumerate(
            [
                (1500.0, "connection refused"),
                (600.0, "sql exception"),
                (100.0, "network unreachable"),
                (50.0, "permission denied"),
                (50.0, "generic failure"),
            ]
        )
    ]
    parent.children = children
    engine.add_call_chain("root-trace", [parent])

    causes = engine.analyze_root_causes("root-trace")
    assert len(causes) == 6
    types = {c.issue_type for c in causes}
    assert types == {
        "timeout_error",
        "connection_error",
        "database_error",
        "network_error",
        "authorization_error",
        "application_error",
    }
    sevs = {c.severity for c in causes}
    assert sevs == {Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW}

    child_cause = next(c for c in causes if c.root_cause_operation == "op2")
    assert "parent_error" in child_cause.contributing_factors
    assert "high_duration" in child_cause.contributing_factors

    assert engine.analyze_root_causes("missing") == []


def test_call_chain_empty_and_edge_cases():
    engine = get_call_chain_analysis_engine({})
    now = datetime.now(timezone.utc)
    engine.add_call_chain(
        "t1",
        [
            CallChainNode(
                span_id="s1",
                parent_span_id=None,
                operation_name="op",
                service_name="svc",
                start_time=now,
                end_time=now,
                duration_ms=100.0,
                self_duration_ms=100.0,
                status="OK",
            )
        ],
    )
    assert engine.analyze_anomalies(threshold=2.0) == []
    assert engine.analyze_performance_bottlenecks() == []
    assert engine.get_statistics()["total_services_analyzed"] == 1


def test_call_chain_helpers_directly():
    engine = get_call_chain_analysis_engine({})
    assert engine._calculate_bottleneck_severity(0.1, 100) == Severity.LOW
    assert engine._calculate_bottleneck_severity(0.6, 100) == Severity.MEDIUM
    assert engine._calculate_bottleneck_severity(1.5, 100) == Severity.HIGH
    assert engine._calculate_bottleneck_severity(3.0, 100) == Severity.CRITICAL
    assert engine._calculate_bottleneck_severity(0.1, 6000) == Severity.CRITICAL
    assert engine._calculate_bottleneck_severity(0.1, 1500) == Severity.HIGH
    assert engine._calculate_bottleneck_severity(0.1, 600) == Severity.MEDIUM

    assert engine._calculate_impact_score(1.0, 100) == 38.0
    assert engine._calculate_impact_score(4.0, 2000) == 100.0

    recs = engine._generate_bottleneck_recommendations("svc", "op", 1.5)
    assert len(recs) == 7
    recs_low = engine._generate_bottleneck_recommendations("svc", "op", 0.1)
    assert len(recs_low) == 2

    error_node = CallChainNode(
        span_id="e1",
        parent_span_id=None,
        operation_name="op",
        service_name="svc",
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc),
        duration_ms=6000.0,
        self_duration_ms=6000.0,
        status="ERROR",
        error_message="timeout connecting to upstream",
    )
    assert engine._classify_error(error_node) == "timeout_error"
    assert engine._calculate_error_severity(error_node) == Severity.CRITICAL
    factors = ["high_duration", "parent_error"]
    assert engine._calculate_root_cause_confidence(error_node, factors) == 0.8
    assert engine._generate_root_cause_recommendations("timeout_error", "svc", "op")
    assert engine._generate_root_cause_recommendations("connection_error", "svc", "op")
    assert engine._generate_root_cause_recommendations("database_error", "svc", "op")
    assert engine._generate_root_cause_recommendations("network_error", "svc", "op")
    assert engine._generate_root_cause_recommendations("authorization_error", "svc", "op")
    assert engine._generate_root_cause_recommendations("application_error", "svc", "op")


def test_call_chain_finders_and_service_error_rate():
    engine = get_call_chain_analysis_engine({})
    now = datetime.now(timezone.utc)
    node = CallChainNode(
        span_id="x1",
        parent_span_id=None,
        operation_name="op",
        service_name="svc",
        start_time=now,
        end_time=now,
        duration_ms=100.0,
        self_duration_ms=100.0,
        status="ERROR",
        error_message="something",
    )
    engine.add_call_chain("t1", [node])
    engine.baseline_data["svc"] = {"error_count": 10, "total_count": 10}
    factors = engine._identify_contributing_factors(node, [node])
    assert "high_service_error_rate" in factors

    nested_child = CallChainNode(
        span_id="c1",
        parent_span_id="x1",
        operation_name="op2",
        service_name="svc",
        start_time=now,
        end_time=now,
        duration_ms=50.0,
        self_duration_ms=50.0,
        status="ERROR",
        error_message="nested error",
    )
    node.children = [nested_child]
    errors = engine._find_error_nodes([node])
    assert len(errors) == 2
    found = engine._find_node_by_id("c1", [node])
    assert found is nested_child
    assert engine._find_node_by_id("nope", [node]) is None


def test_read_write_router():
    router = ReadWriteRouter()
    with pytest.raises(Exception):
        router.get_read_connection()
    with pytest.raises(Exception):
        router.get_write_connection()

    master = DatabaseInstance(
        host="m",
        port=5432,
        role=DatabaseRole.MASTER,
        database_type=DatabaseType.POSTGRESQL,
    )
    router.set_master(master)
    assert router.get_write_connection() == master
    assert router.get_read_connection() == master

    slave = DatabaseInstance(
        host="s1",
        port=5433,
        role=DatabaseRole.SLAVE,
        database_type=DatabaseType.POSTGRESQL,
        weight=2,
    )
    router.add_slave(slave)
    read = router.get_read_connection()
    assert read.role == DatabaseRole.SLAVE

    slave.is_available = False
    assert router.get_read_connection() == master
    slave.is_available = True
    slave.weight = 0
    assert router.get_read_connection() == slave

    router.check_health()
    assert slave.is_available is True


def test_redis_cluster_adapter_fallback(monkeypatch):
    monkeypatch.setattr("core.distributed_storage.REDIS_AVAILABLE", False)
    monkeypatch.setattr("core.distributed_storage.redis", None)
    adapter = RedisClusterAdapter()
    assert adapter.set("k1", "v1") is True
    assert adapter.get("k1") == "v1"
    assert adapter.exists("k1") is True
    assert adapter.delete("k1") is True
    assert adapter.exists("k1") is False
    assert adapter.delete("missing") is False
    assert adapter.get("missing") is None
    assert adapter.get_fallback_data() == {}


def test_distributed_storage_manager(distributed_storage):
    manager = distributed_storage
    manager.configure_master_slave("m", 5432, [("s1", 5433), ("s2", 5434)])
    write = manager.get_write_connection_info()
    assert write["host"] == "m"
    read = manager.get_read_connection_info()
    assert read["role"] == "slave"
    health = manager.health_check()
    assert health["master_available"] is True
    assert health["slaves_count"] == 2
    manager.configure_redis_cluster([("r1", 6379)])


def test_distributed_storage_manager_no_connections(distributed_storage):
    manager = distributed_storage
    read = manager.get_read_connection_info()
    assert "error" in read
    write = manager.get_write_connection_info()
    assert "error" in write


def test_get_distributed_storage_manager(monkeypatch):
    monkeypatch.setattr("core.distributed_storage.REDIS_AVAILABLE", False)
    monkeypatch.setattr("core.distributed_storage.redis", None)
    m1 = get_distributed_storage_manager()
    m2 = get_distributed_storage_manager()
    assert m1 is m2


async def test_enterprise_tenant_crud(enterprise):
    ef = enterprise
    tenant = await ef.create_tenant("t1", {"key": "v"})
    assert tenant.name == "t1"
    assert tenant.status == TenantStatus.ACTIVE
    assert (await ef.get_tenant(tenant.id)) is tenant
    assert await ef.update_tenant(tenant.id, {"name": "t2"}) is True
    assert ef.tenants[tenant.id].name == "t2"
    assert await ef.delete_tenant(tenant.id) is True
    assert await ef.get_tenant(tenant.id) is None

    assert await ef.update_tenant("missing", {}) is False
    assert await ef.delete_tenant("missing") is False
    assert await ef.get_tenant("missing") is None


async def test_enterprise_tenant_limit(enterprise):
    ef = enterprise
    ef.max_tenants = 0
    with pytest.raises(ValueError):
        await ef.create_tenant("overflow", {})


async def test_enterprise_permissions(enterprise):
    ef = enterprise
    tenant = await ef.create_tenant("perm-tenant", {})
    perm = await ef.grant_permission("u1", tenant.id, {"read", "write"}, ["admin"])
    assert perm.user_id == "u1"
    assert await ef.check_permission("u1", tenant.id, "read") is True
    assert await ef.check_permission("u1", tenant.id, "delete") is False
    assert await ef.check_permission("u2", tenant.id, "read") is False

    expired = await ef.grant_permission(
        "u2",
        tenant.id,
        {"read"},
        [],
        expires_at=datetime.now() - timedelta(days=1),
    )
    assert await ef.check_permission("u2", tenant.id, "read") is False

    assert await ef.revoke_permission("u1", tenant.id) is True
    assert await ef.revoke_permission("u1", tenant.id) is False


async def test_enterprise_delete_cleanup(enterprise):
    ef = enterprise
    tenant = await ef.create_tenant("cleanup", {})
    await ef.grant_permission("u1", tenant.id, {"read"}, ["user"])
    rec = await ef._assess_requirement(ComplianceStandard.SOC2, "access_control")
    rec.evidence["tenant_id"] = tenant.id
    sso = await ef.configure_sso_provider("oauth2", {"name": "oauth"})
    ef.sso_sessions["sess1"] = {
        "tenant_id": tenant.id,
        "user_id": "u1",
        "provider_id": sso.id,
    }
    assert await ef.delete_tenant(tenant.id) is True
    assert tenant.id not in ef.tenants
    assert not any(k.endswith(f":{tenant.id}") for k in ef.user_permissions)
    assert not any(s.get("tenant_id") == tenant.id for s in ef.sso_sessions.values())
    assert not any(r.evidence.get("tenant_id") == tenant.id for r in ef.compliance_records.values())


async def test_enterprise_compliance(enterprise):
    ef = enterprise
    for std in [ComplianceStandard.SOC2, ComplianceStandard.GDPR, ComplianceStandard.ISO27001]:
        result = await ef.assess_compliance(std)
        assert result["standard"] == std.value
        assert result["overall_status"] in ("compliant", "partial")

    unsupported = await ef.assess_compliance(ComplianceStandard.HIPAA)
    assert "error" in unsupported

    fresh = EnterpriseFeatures()
    result = await fresh.assess_compliance(ComplianceStandard.HIPAA)
    assert "error" in result


async def test_enterprise_audit_logs(enterprise):
    ef = enterprise
    tenant = await ef.create_tenant("audit", {})
    await ef.update_tenant(tenant.id, {"name": "audit2"})

    logs = await ef.query_audit_logs(tenant_id=tenant.id)
    assert len(logs) >= 1
    assert len(await ef.query_audit_logs(tenant_id=tenant.id, limit=1)) == 1
    assert len(await ef.query_audit_logs(user_id="system")) >= 1
    assert len(await ef.query_audit_logs(action="create_tenant")) >= 1

    now = datetime.now()
    assert (
        len(
            await ef.query_audit_logs(
                start_time=now - timedelta(days=1), end_time=now + timedelta(days=1)
            )
        )
        >= 1
    )

    ef.audit_retention_days = -1
    await ef.cleanup_old_audit_logs()
    assert len(ef.audit_logs) == 0


async def test_enterprise_sso(monkeypatch, enterprise):
    ef = enterprise
    saml = await ef.configure_sso_provider("saml", {"name": "saml"})
    oauth = await ef.configure_sso_provider(
        "oauth2",
        {"name": "oauth", "userinfo_endpoint": "http://example.com/userinfo"},
    )
    oidc = await ef.configure_sso_provider("oidc", {"name": "oidc"})
    other = await ef.configure_sso_provider("ldap", {"name": "ldap"})

    assert await ef.authenticate_sso("missing", {}) is None
    assert await ef.authenticate_sso(saml.id, {}) is None
    assert await ef.authenticate_sso(other.id, {"access_token": "x"}) is None

    no_token = await ef.authenticate_sso(oauth.id, {})
    assert no_token is None

    payload = {"sub": "user1", "email": "u@example.com", "name": "User"}
    b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    id_token = f"header.{b64}.sig"

    # Patch httpx only if available; otherwise the import exception path is exercised.
    if importlib.util.find_spec("httpx") is not None:

        class FakeResponse:
            def __init__(self, json_data=None, status=200):
                self.status_code = status
                self._json = json_data or {}

            def json(self):
                return self._json

        class FakeAsyncClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return None

            async def get(self, *args, **kwargs):
                return FakeResponse({"tenant_id": "t1"})

        monkeypatch.setattr("httpx.AsyncClient", FakeAsyncClient)

    result = await ef.authenticate_sso(oauth.id, {"access_token": "tok", "id_token": id_token})
    assert result is not None
    assert result["authenticated"] is True
    assert result["user_id"] == "user1"
    assert result["provider"] == "oauth2"

    oidc_result = await ef.authenticate_sso(oidc.id, {"access_token": "tok2"})
    assert oidc_result is not None
    assert oidc_result["authenticated"] is True


async def test_enterprise_statistics(enterprise):
    ef = enterprise
    await ef.create_tenant("stat", {})
    stats = await ef.get_enterprise_statistics()
    assert stats["total_tenants"] == 1
    assert stats["active_tenants"] == 1
    assert stats["encryption_level"] == "aes256"


async def test_enterprise_initialize_encryption_and_crypto(monkeypatch):
    # Patch crypto deps so _initialize_encryption can run without real cryptography.
    import base64 as real_base64

    class FakeFernet:
        def __init__(self, key):
            self.key = key

        def encrypt(self, data: bytes) -> bytes:
            return b"enc:" + data

        def decrypt(self, data: bytes) -> bytes:
            return data[4:]

    monkeypatch.setattr("core.enterprise_features.CRYPTO_AVAILABLE", True)
    monkeypatch.setattr("core.enterprise_features.os", os)
    monkeypatch.setattr("core.enterprise_features.base64", real_base64)
    monkeypatch.setattr("core.enterprise_features.Fernet", FakeFernet)

    ef = EnterpriseFeatures()
    await ef.initialize()
    assert "fernet" in ef.encryption_keys

    assert await ef.encrypt_data("plain") != "plain"
    assert await ef.decrypt_data(await ef.encrypt_data("plain")) == "plain"

    ef.encryption_level = EncryptionLevel.BASE64
    b64 = await ef.encrypt_data("hello")
    assert b64 == real_base64.b64encode(b"hello").decode()
    assert await ef.decrypt_data(b64) == "hello"

    ef.encryption_level = EncryptionLevel.RSA4096
    assert await ef.encrypt_data("rsa") == "rsa"
    assert await ef.decrypt_data("rsa") == "rsa"

    ef.encryption_level = EncryptionLevel.NONE
    assert await ef.encrypt_data("none") == "none"
    assert await ef.decrypt_data("none") == "none"


async def test_enterprise_id_token_parse_failure(monkeypatch, enterprise):
    ef = enterprise
    oauth = await ef.configure_sso_provider("oauth2", {"name": "oauth"})
    result = await ef.authenticate_sso(
        oauth.id, {"access_token": "tok", "id_token": "not.valid.base64"}
    )
    assert result is not None
    assert result["authenticated"] is True


async def test_enterprise_missing_fernet_key(monkeypatch, enterprise):
    import base64 as real_base64

    class FakeFernet:
        def __init__(self, key):
            self.key = key

        def encrypt(self, data: bytes) -> bytes:
            return b"enc:" + data

        def decrypt(self, data: bytes) -> bytes:
            return data[4:]

    monkeypatch.setattr("core.enterprise_features.CRYPTO_AVAILABLE", True)
    monkeypatch.setattr("core.enterprise_features.base64", real_base64)
    monkeypatch.setattr("core.enterprise_features.Fernet", FakeFernet)

    ef = enterprise
    ef.encryption_level = EncryptionLevel.AES256
    # no fernet key set, falls back to plain data
    assert await ef.encrypt_data("plain") == "plain"
    assert await ef.decrypt_data("plain") == "plain"
