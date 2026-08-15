# -*- coding: utf-8 -*-
"""Happy-path tests for the security addon Service.execute_operation wrappers."""

import subprocess

import pytest

from extensions.addons.security.penetration_testing_service.service import Service as PenetrationTestingService
from extensions.addons.security.security_audit_service.service import Service as SecurityAuditService
from extensions.addons.security.security_scanning_service.service import Service as SecurityScanningService
from extensions.addons.security.sqlalchemy_security_service.service import Service as SQLAlchemySecurityService


@pytest.fixture(autouse=True)
def _no_real_external_calls(monkeypatch):
    """Block real subprocess/network calls even if dry_run were disabled."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "false")
    fake_result = type("_CompletedProcess", (), {
        "stdout": "",
        "stderr": "",
        "returncode": 0,
    })()
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: fake_result)


def _assert_service_result(result, feature):
    assert isinstance(result, dict)
    assert result.get("success") is True
    assert result.get("status") == "ok"
    assert result.get("feature") == feature
    assert "result" in result
    assert "message" in result


def test_penetration_testing_service_design_penetration_plan():
    service = PenetrationTestingService(dry_run=True)
    result = service.execute_operation(
        "design_penetration_plan",
        {"target": "127.0.0.1", "dry_run": True},
    )
    _assert_service_result(result, "design_penetration_plan")
    assert result["result"].get("target") == "127.0.0.1"
    assert "phases" in result["result"]


def test_security_audit_service_run_zap_scan():
    service = SecurityAuditService(dry_run=True)
    result = service.execute_operation(
        "run_zap_scan",
        {"target": "http://example.com", "dry_run": True},
    )
    _assert_service_result(result, "run_zap_scan")
    assert isinstance(result["result"], list)
    assert result["result"]


def test_security_scanning_service_manage_vulnerabilities():
    service = SecurityScanningService(dry_run=True)
    result = service.execute_operation(
        "manage_vulnerabilities",
        {"dry_run": True},
    )
    _assert_service_result(result, "manage_vulnerabilities")
    assert "total" in result["result"]
    assert "by_severity" in result["result"]
    assert isinstance(result["result"].get("top_priorities"), list)


def test_sqlalchemy_security_service_parameterized_queries():
    service = SQLAlchemySecurityService(dry_run=True)
    result = service.execute_operation(
        "parameterized_queries",
        {"dry_run": True},
    )
    _assert_service_result(result, "parameterized_queries")
    assert "recommendation" in result["result"]
