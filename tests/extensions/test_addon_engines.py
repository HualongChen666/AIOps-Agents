# -*- coding: utf-8 -*-
"""Happy-path smoke tests for the real addon engines."""

import asyncio
import importlib
import json
import os
import shutil
import sqlite3
import subprocess
import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest

from extensions.addons.engines.connector_bus import ConnectorBus
from extensions.addons.engines.doc_policy_engine import DocEngine, PolicyEngine
from extensions.addons.engines.infra_executor import (
    AnsibleExecutor,
    BaseInfraService,
    CliExecutor,
    HelmExecutor,
    K8sExecutor,
    TerraformExecutor,
)
from extensions.addons.engines.monitoring_provider import (
    BaseObservabilityService,
    MonitoringProvider,
)
from extensions.addons.engines.security_scanner import BaseSecurityService, SecurityScanner
from extensions.addons.engines.storage_driver import StorageDriver
from extensions.addons.engines.workflow_engine import RunbookRunner, WorkflowEngine


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def _cp(stdout: str = "", stderr: str = "", returncode: int = 0) -> MagicMock:
    """Fake subprocess.CompletedProcess-like object."""
    return MagicMock(stdout=stdout, stderr=stderr, returncode=returncode)


def _http_response(status_code: int = 200, json_data: Any = None, text: str = "") -> MagicMock:
    """Fake requests/urllib response."""
    resp = MagicMock(
        status_code=status_code,
        text=text,
        content=(json.dumps(json_data).encode() if json_data is not None else b""),
        headers={"content-type": "application/json"},
    )
    resp.json.return_value = json_data if json_data is not None else {}
    return resp


def _fake_subprocess_factory(stdout: str = "", stderr: str = "", returncode: int = 0) -> Any:
    """Return a fake ``subprocess.run`` callable."""
    return lambda *a, **k: _cp(stdout, stderr, returncode)


# ------------------------------------------------------------------
# SecurityScanner
# ------------------------------------------------------------------
def test_security_scanner_dry_run():
    scanner = SecurityScanner(dry_run=True)
    assert scanner.scan_code(".", ["bandit", "semgrep"])
    assert scanner.scan_dependencies("requirements.txt")
    assert scanner.scan_api("http://localhost")
    assert scanner.scan_network("127.0.0.1")
    assert scanner.scan_container("alpine:latest")
    assert scanner.check_license(["requests:MIT", "bad:proprietary"])
    assert scanner.check_sql_injection("SELECT * FROM t WHERE id=%s")
    assert scanner.check_api_baseline(
        {
            "servers": [{"url": "https://x"}],
            "components": {"securitySchemes": {}},
            "paths": {"/health": {}},
        }
    )

    for name, params in [
        ("run_sast_sonarqube", {"target": "."}),
        ("run_dast_zap", {"target": "http://x"}),
        ("run_dependency_snyk", {"target": "requirements.txt"}),
        ("run_container_trivy", {"image": "alpine"}),
        ("execute_penetration_tests", {"target": "127.0.0.1"}),
        ("sql_injection_protection", {"code": "x"}),
        ("api_key_auth", {"spec": {}}),
        ("manage_vulnerabilities", {}),
        ("check_compliance", {}),
        ("generate_fix_suggestions", {}),
        ("test_and_optimize_security_scanning", {}),
        ("design_penetration_plan", {}),
        ("analyze_penetration_results", {}),
        ("fix_vulnerabilities", {}),
        ("verify_fixes", {}),
        ("write_penetration_report", {}),
        ("implement_security_hardening", {}),
        ("conduct_security_training", {}),
        ("test_and_optimize_pentesting", {}),
        ("parameterized_queries", {}),
        ("data_validation", {}),
        ("oauth2_password_auth", {}),
        ("cors_configuration", {}),
        ("review_license_compliance", {"dependencies": ["x:MIT"]}),
        ("unknown_op", {}),
    ]:
        result = scanner.run(name, params)
        assert result is not None


def test_security_scanner_real(monkeypatch):
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")
    calls: List[List[str]] = []

    def fake_run(cmd, **k):
        calls.append(cmd)
        if "bandit" in cmd:
            return _cp(json.dumps({"results": []}))
        if "semgrep" in cmd:
            return _cp(json.dumps({"results": []}))
        if "safety" in cmd:
            return _cp(json.dumps([]))
        if "zap" in cmd:
            return _cp(json.dumps({"alerts": []}))
        if "nmap" in cmd:
            return _cp("<nmaprun></nmaprun>")
        if "trivy" in cmd:
            return _cp(json.dumps({"Results": []}))
        return _cp()

    monkeypatch.setattr("subprocess.run", fake_run)
    scanner = SecurityScanner(dry_run=False)
    scanner.scan_code(".", ["bandit", "semgrep"])
    scanner.scan_dependencies("requirements.txt")
    scanner.scan_api("http://localhost")
    scanner.scan_network("127.0.0.1")
    scanner.scan_container("alpine:latest")
    assert any("bandit" in " ".join(c) for c in calls)


def test_base_security_service(monkeypatch):
    monkeypatch.setattr(BaseSecurityService, "OPERATIONS", ["run_sast_sonarqube"], raising=False)
    BaseSecurityService.execute_operation("get_state")
    BaseSecurityService.execute_operation("backup_state", {"name": "b1"})
    BaseSecurityService.execute_operation("restore_state", {"name": "b1"})
    BaseSecurityService.execute_operation("get_stats")
    BaseSecurityService.execute_operation("list_methods")
    BaseSecurityService.execute_operation("run_sast_sonarqube", {"target": ".", "dry_run": True})


# ------------------------------------------------------------------
# MonitoringProvider
# ------------------------------------------------------------------
def test_monitoring_provider_dry_run():
    provider = MonitoringProvider(dry_run=True)
    assert provider.query()
    assert provider.push_alert()
    assert provider.get_topology()
    assert provider.logs()
    assert provider.traces()
    assert provider.health()


def test_monitoring_provider_real(monkeypatch):
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")
    calls: List[SimpleNamespace] = []

    def fake_request(method, url, **kwargs):
        calls.append(SimpleNamespace(method=method, url=url))
        if "datadog" in url:
            return _http_response(200, {"series": []})
        if "_search" in url:
            return _http_response(200, {"hits": {"hits": []}})
        if "/api/v1/query_range" in url:
            return _http_response(200, {"data": {"result": []}})
        if "/api/v1/alerts" in url:
            return _http_response(200, {"status": "ok"})
        if "/api/v1/targets" in url:
            return _http_response(200, {"data": {"activeTargets": []}})
        if "/loki" in url:
            return _http_response(200, {"data": {"result": []}})
        if "/api/traces" in url or "/api/v2/traces" in url:
            return _http_response(200, {"data": []})
        return _http_response(200, {})

    monkeypatch.setattr("requests.request", fake_request)
    monkeypatch.setattr(
        "subprocess.run",
        lambda *a, **k: _cp(
            stdout=json.dumps({"Datapoints": []}),
            returncode=0,
        ),
    )

    provider = MonitoringProvider(dry_run=False)
    provider.query(target="http://prometheus:9090", metric="up")
    provider.query(target="http://datadog", metric="up")
    provider.query(target="http://elasticsearch:9200", metric="up")
    provider.query(target="http://cloudwatch", metric="up")
    provider.push_alert(rule_name="high_latency", expr="up == 0")
    provider.get_topology(source="http://prometheus:9090")
    provider.logs(target="http://loki:3100", query='{job="x"}')
    provider.logs(target="http://elasticsearch:9200", query="*")
    provider.traces(target="http://jaeger:16686", service="svc")
    provider.traces(target="http://zipkin:9411", service="svc")
    provider.health(target="http://example.com")
    assert calls


def test_base_observability_service(monkeypatch):
    monkeypatch.setattr(BaseObservabilityService, "OPERATIONS", ["query", "logs"], raising=False)
    service = BaseObservabilityService()
    assert asyncio.run(service.get_state())
    assert asyncio.run(service.backup_state({"name": "b1"}))
    assert asyncio.run(service.restore_state({"name": "b1"}))
    assert asyncio.run(service.get_stats())
    assert asyncio.run(service.list_methods())
    assert service.execute_operation("query", {"metric": "up"})["success"] is True
    assert service.execute_operation("logs", {"query": "x"})["success"] is True
    handler = service.query
    assert asyncio.run(handler({"metric": "up"})) is not None


# ------------------------------------------------------------------
# InfraExecutor
# ------------------------------------------------------------------
def test_infra_executors_dry_run():
    cli = CliExecutor(dry_run=True)
    assert cli.run("echo", args=["hello"])["dry_run"]
    assert cli.run(["ls", "-la"])["dry_run"]

    k8s = K8sExecutor(dry_run=True)
    assert k8s.run(["kubectl", "apply", "-f", "x.yaml"])
    assert k8s.run(["helm", "install", "x", "chart"])
    assert k8s.run(["istioctl", "x"])

    ansible = AnsibleExecutor(dry_run=True)
    assert ansible.run(["site.yml", "--check"])["dry_run"]
    assert ansible.run("--check site.yml")["dry_run"]

    terraform = TerraformExecutor(dry_run=True)
    assert terraform.run(["plan"])["dry_run"]

    helm = HelmExecutor(dry_run=True)
    assert helm.run(["list"])["dry_run"]


class _DummyInfra(BaseInfraService):
    OPERATIONS = ["echo", "k8s_apply", "ansible_run", "tf_plan", "helm_list"]
    COMMAND_MAP = {
        "echo": lambda p: {"executor": "cli", "command": ["echo", "hi"]},
        "k8s_apply": lambda p: {
            "executor": "k8s",
            "command": ["kubectl", "apply", "-f", "x.yaml"],
            "namespace": "default",
        },
        "ansible_run": lambda p: {"executor": "ansible", "command": ["site.yml"]},
        "tf_plan": lambda p: {"executor": "terraform", "command": ["plan"]},
        "helm_list": lambda p: {"executor": "helm", "command": ["list"]},
    }


def test_base_infra_service_dry_run():
    infra = _DummyInfra(dry_run=True)
    assert infra.execute_operation("list_methods")
    assert infra.execute_operation("get_state", {"x": 1})
    assert infra.execute_operation("get_stats")
    assert infra.execute_operation("backup_state", {"name": "b1"})
    assert infra.execute_operation("restore_state", {"name": "b1"})
    assert infra.execute_operation("echo")["success"]
    assert infra.execute_operation("k8s_apply")["success"]
    assert infra.execute_operation("ansible_run")["success"]
    assert infra.execute_operation("tf_plan")["success"]
    assert infra.execute_operation("helm_list")["success"]
    assert not infra.execute_operation("unknown")["success"]


def test_infra_executors_real(monkeypatch, tmp_path):
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")
    monkeypatch.setattr(
        "subprocess.run",
        _fake_subprocess_factory(stdout=json.dumps({"status": "ok"}), returncode=0),
    )

    cli = CliExecutor(dry_run=False)
    assert cli.run("echo", args=["hello"])["status"] == "ok"

    k8s = K8sExecutor(dry_run=False)
    k8s.run(["kubectl", "get", "pods"])
    k8s.run(["helm", "list"])

    terraform = TerraformExecutor(dry_run=False)
    assert terraform.run(["plan"])["status"] == "ok"

    helm = HelmExecutor(dry_run=False)
    assert helm.run(["list"])["status"] == "ok"

    class FakePlaybookManager:
        def __init__(self, playbook_dir, dry_run=False):
            self.playbook_dir = playbook_dir
            self.dry_run = dry_run

        def load_playbook(self, name):
            return True

        async def execute_playbook(self, name, **kwargs):
            return {"success": True, "return_code": 0, "stdout": "ok", "stderr": ""}

    monkeypatch.setattr(
        "extensions.addons.engines.infra_executor.PlaybookManager", FakePlaybookManager
    )

    playbook_dir = tmp_path / "playbooks"
    playbook_dir.mkdir()
    (playbook_dir / "test.yml").write_text("---\n- hosts: localhost\n  tasks: []\n")
    ansible = AnsibleExecutor(dry_run=False)
    result = ansible.run([str(playbook_dir / "test.yml"), "--check"], cwd=str(tmp_path))
    assert result["status"] == "ok"

    infra = _DummyInfra(dry_run=False)
    assert infra.execute_operation("echo")["success"]
    assert infra.execute_operation("k8s_apply")["success"]
    assert infra.execute_operation("tf_plan")["success"]
    assert infra.execute_operation("helm_list")["success"]


def test_cli_executor_called_process_error(monkeypatch):
    def fake_raise(*a, **k):
        raise subprocess.CalledProcessError(
            returncode=1,
            cmd=a[0] if a else [],
            output="bad",
            stderr="err",
        )

    monkeypatch.setattr("subprocess.run", fake_raise)
    cli = CliExecutor(dry_run=False)
    out = cli.run("false")
    assert out["status"] == "error"


# ------------------------------------------------------------------
# StorageDriver
# ------------------------------------------------------------------
def test_storage_driver_dry_run():
    driver = StorageDriver(dry_run=True)
    assert driver.cache_set("k", "v")["stored"]
    assert driver.cache_get("k") == "v"
    assert driver.sql("SELECT 1") == []
    assert driver.sql("INSERT INTO t VALUES (1)", readonly=False) == 1
    assert driver.vector_create_collection("c", 3)
    assert driver.vector_upsert("c", ["1"], [[1.0, 2.0, 3.0]])["upserted"] == 1
    assert driver.vector_search("c", [1.0, 2.0, 3.0])
    assert driver.get_stats()


def test_storage_driver_real(monkeypatch, tmp_path):
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")

    db = tmp_path / "test.db"
    driver = StorageDriver(
        dry_run=False,
        database_url=f"sqlite:///{db}",
    )
    driver.sql("CREATE TABLE t (id INTEGER)", readonly=False)
    driver.sql("INSERT INTO t VALUES (1)", readonly=False)
    rows = driver.sql("SELECT * FROM t")
    assert rows == [{"id": 1}]

    class FakeRedis:
        _data: Dict[str, Any] = {}

        def __init__(self, *a, **k):
            pass

        def get(self, key):
            return self._data.get(key)

        def set(self, key, value, ex=None):
            self._data[key] = value

    monkeypatch.setattr("redis.Redis.from_url", lambda url: FakeRedis())
    driver.cache_set("k", [1, 2])
    assert driver.cache_get("k")

    class FakeResp:
        def __init__(self, body):
            self._body = body
            self.content = json.dumps(body).encode() if body is not None else b""

        def json(self):
            return self._body

    class FakeHttpxClient:
        def __init__(self, *a, **k):
            pass

        def put(self, url, json=None):
            return FakeResp({"result": {"operation_id": "abc"}})

        def get(self, url, json=None):
            return FakeResp({"result": {"points": []}})

        def close(self):
            pass

    monkeypatch.setattr("httpx.Client", FakeHttpxClient)
    driver.vector_create_collection("c", 3)
    result = driver.vector_upsert(
        "c",
        ["1"],
        [[1.0, 2.0, 3.0]],
        payloads=[{"content": "hi"}],
    )
    assert "upserted" in result or "error" not in result


# ------------------------------------------------------------------
# WorkflowEngine
# ------------------------------------------------------------------
def test_workflow_engine_dry_run():
    engine = WorkflowEngine(dry_run=True)
    workflow = [
        {"type": "http", "name": "h1", "method": "GET", "url": "http://x"},
        {"type": "cli", "name": "c1", "command": ["echo", "hi"]},
        {"type": "python", "name": "p1", "module": "os", "function": "getcwd"},
        {
            "type": "decision",
            "name": "d1",
            "condition": "True",
            "true": "next",
            "false": "end",
        },
        {"type": "memory", "name": "m1", "query": "incident"},
    ]
    result = engine.run_workflow(workflow, {"x": 1})
    assert result["success"]
    assert engine.get_scenario_memory("incident")
    assert engine.capacity_analysis({"cpu": 10}, {"cpu": 20})["recommendations"]

    runner = RunbookRunner(engine=engine)
    assert runner.run_runbook(workflow, {"input": 1})


def test_workflow_engine_real(monkeypatch):
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")

    http_calls: List[SimpleNamespace] = []

    def fake_request(method, url, **kwargs):
        http_calls.append(SimpleNamespace(method=method, url=url))
        return _http_response(200, {"ok": True}, text="ok")

    monkeypatch.setattr("requests.request", fake_request)
    monkeypatch.setattr(
        "subprocess.run",
        _fake_subprocess_factory(stdout="hello", returncode=0),
    )

    fake_mod = SimpleNamespace(getcwd=lambda: "/tmp")
    monkeypatch.setattr("importlib.import_module", lambda name: fake_mod)

    engine = WorkflowEngine(dry_run=False)
    workflow = [
        {"type": "http", "name": "h1", "method": "POST", "url": "http://x", "body": {"a": 1}},
        {"type": "cli", "name": "c1", "command": ["echo", "hello"]},
        {"type": "python", "name": "p1", "module": "fake_mod", "function": "getcwd"},
        {
            "type": "decision",
            "name": "d1",
            "condition": "True",
            "true": "next",
            "false": "end",
        },
        {"type": "memory", "name": "m1", "query": "incident"},
    ]
    result = engine.run_workflow(workflow, {"x": 1})
    assert result["success"]
    assert http_calls


# ------------------------------------------------------------------
# DocEngine / PolicyEngine
# ------------------------------------------------------------------
def test_doc_policy_engine_dry_run():
    doc = DocEngine(dry_run=True)
    assert doc.build_docs("source", "build")["dry_run"]

    policy = PolicyEngine(dry_run=True)
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "API"},
        "paths": {},
    }
    assert policy.lint_openapi(spec)["valid"]
    assert policy.validate_schema({"a": 1}, {"type": "object"})["valid"]
    assert policy.load_config("MISSING_CONFIG_VAR")
    assert policy.user_lookup("alice")["found"]
    assert policy.plugin_index()
    assert policy.plugin_load("os")
    assert policy.plugin_unload("os")


def test_doc_policy_engine_real(monkeypatch, tmp_path):
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")

    monkeypatch.setattr(
        "subprocess.run",
        _fake_subprocess_factory(
            stdout="build succeeded\nWARNING: 0\nERROR: 0\n",
            returncode=0,
        ),
    )
    doc = DocEngine(dry_run=False)
    assert doc.build_docs(str(tmp_path / "src"), str(tmp_path / "out"))["status"] == "completed"

    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"key": "value"}))
    policy = PolicyEngine(dry_run=False)
    assert policy.load_config(str(config_file))["value"] == {"key": "value"}

    monkeypatch.setenv("TEST_POLICY_KEY", json.dumps({"from": "env"}))
    assert policy.load_config("TEST_POLICY_KEY")["value"] == {"from": "env"}

    assert policy.user_lookup("alice")["user_id"] == "alice"
    assert policy.plugin_load("json")["loaded"]
    assert "unloaded" in policy.plugin_unload("json")


# ------------------------------------------------------------------
# ConnectorBus
# ------------------------------------------------------------------
def test_connector_bus_dry_run():
    bus = ConnectorBus(dry_run=True)
    assert bus.produce("topic", {"x": 1}, bus="kafka")["dry_run"]
    assert bus.produce("topic", {"x": 1}, bus="rabbitmq")["dry_run"]
    assert bus.produce("topic", {"x": 1}, bus="sqs")["dry_run"]
    assert bus.produce("http://x", {"x": 1}, bus="http")["dry_run"]
    assert bus.consume("topic", bus="kafka")["dry_run"]
    assert bus.publish_queue("queue", {"x": 1})["dry_run"]
    assert bus.subscribe_queue("queue")["dry_run"]
    assert bus.webhook_send("http://x", {"a": 1})["dry_run"]
    assert bus.github_request("owner", "repo", "issues")["dry_run"]


def test_connector_bus_real(monkeypatch):
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")

    http_calls: List[SimpleNamespace] = []
    cli_calls: List[List[str]] = []

    def fake_request(method, url, **kwargs):
        http_calls.append(SimpleNamespace(method=method, url=url))
        return _http_response(200, {"id": 1})

    def fake_run(cmd, **kwargs):
        cli_calls.append(cmd)
        return _cp(stdout="ok", returncode=0)

    monkeypatch.setattr("requests.request", fake_request)
    monkeypatch.setattr("subprocess.run", fake_run)

    bus = ConnectorBus(dry_run=False)
    bus.produce("topic", {"x": 1}, bus="kafka")
    bus.produce("topic", {"x": 1}, bus="rabbitmq")
    bus.produce("https://sqs.us-east-1.amazonaws.com/123/queue", "msg", bus="sqs")
    bus.produce("http://x", {"x": 1}, bus="http")
    bus.consume("topic", bus="kafka")
    bus.consume("topic", bus="rabbitmq")
    bus.consume("https://sqs.us-east-1.amazonaws.com/123/queue", bus="sqs")
    bus.publish_queue("rk", {"x": 1})
    bus.publish_queue("https://sqs.us-east-1.amazonaws.com/123/queue", "msg")
    bus.subscribe_queue("rk")
    bus.subscribe_queue("https://sqs.us-east-1.amazonaws.com/123/queue")
    bus.webhook_send("http://x", {"a": 1})
    bus.github_request("owner", "repo", "issues")
    assert http_calls or cli_calls
