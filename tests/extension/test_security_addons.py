# -*- coding: utf-8 -*-
"""Tests for the security & compliance addon wrappers around SecurityScanner."""

from __future__ import annotations

import json
import subprocess
from typing import Any, Dict, List

import pytest

from extensions.addons.infrastructure.fastapi_security_service.service import Service as FastApiService
from extensions.addons.infrastructure.open_source_license_service.service import Service as LicenseService
from extensions.addons.security.penetration_testing_service.service import Service as PentestService
from extensions.addons.security.security_audit_service.service import Service as AuditService
from extensions.addons.security.security_scanning_service.service import Service as ScanningService
from extensions.addons.security.sqlalchemy_security_service.service import Service as SqlalchemyService


def _make_output(tool: str) -> str:
    """Return a realistic stdout payload for a mocked security tool."""
    if tool == "bandit":
        return json.dumps(
            {
                "results": [
                    {
                        "test_id": "B105",
                        "issue_text": "Possible hardcoded password",
                        "filename": "app.py",
                        "line_number": 12,
                        "issue_severity": "HIGH",
                    }
                ]
            }
        )
    if tool == "semgrep":
        return json.dumps(
            {
                "results": [
                    {
                        "check_id": "python.sql-injection",
                        "path": "app.py",
                        "start": {"line": 7},
                        "extra": {"message": "Mock SQL injection", "severity": "ERROR"},
                    }
                ]
            }
        )
    if tool == "safety":
        return json.dumps(
            [
                {
                    "package": "requests",
                    "vulnerability": "CVE-2023-32681",
                    "affected": "<2.31.0",
                }
            ]
        )
    if tool == "zap-baseline.py":
        return json.dumps(
            {
                "alerts": [
                    {
                        "alert": "Mock Reflected XSS",
                        "risk": "High",
                        "url": "http://localhost",
                    }
                ]
            }
        )
    if tool == "nmap":
        return (
            '<?xml version="1.0"?>\n'
            "<nmaprun>\n"
            "  <host>\n"
            "    <address addr=\"127.0.0.1\"/>\n"
            "    <ports>\n"
            '      <port portid="443">\n'
            '        <state state="open"/>\n'
            '        <service name="https"/>\n'
            "      </port>\n"
            "    </ports>\n"
            "  </host>\n"
            "</nmaprun>"
        )
    if tool == "trivy":
        return json.dumps(
            {
                "Results": [
                    {
                        "Target": "alpine:latest",
                        "Vulnerabilities": [
                            {
                                "VulnerabilityID": "CVE-2024-0001",
                                "PkgName": "mock-pkg",
                                "Severity": "CRITICAL",
                            }
                        ],
                    }
                ]
            }
        )
    return ""


@pytest.fixture
def mock_run(monkeypatch):
    """Enable real execution and mock subprocess.run with realistic tool output."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")

    def _fake_run(cmd: List[str], *args: Any, **kwargs: Any) -> subprocess.CompletedProcess:
        tool = cmd[0] if cmd else ""
        stdout = _make_output(tool)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout=stdout,
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", _fake_run)


def test_security_scanning_service_run_sast_sonarqube(mock_run):
    params: Dict[str, Any] = {"target": ".", "scanners": ["bandit"]}
    result = ScanningService.execute_operation("run_sast_sonarqube", params)
    assert result["success"] is True
    assert result["status"] == "ok"
    assert isinstance(result["result"], list)
    assert any(item.get("scanner") == "bandit" for item in result["result"])


def test_security_audit_service_run_zap_scan(mock_run):
    params: Dict[str, Any] = {"target": "http://localhost"}
    result = AuditService.execute_operation("run_zap_scan", params)
    assert result["success"] is True
    assert result["status"] == "ok"
    assert isinstance(result["result"], list)
    assert any(alert.get("alert") == "Mock Reflected XSS" for alert in result["result"])


def test_penetration_testing_service_execute_penetration_tests(mock_run):
    params: Dict[str, Any] = {"target": "127.0.0.1"}
    result = PentestService.execute_operation("execute_penetration_tests", params)
    assert result["success"] is True
    assert result["status"] == "ok"
    assert isinstance(result["result"], list)
    assert any(host.get("host") == "127.0.0.1" for host in result["result"])


def test_sqlalchemy_security_service_sql_injection_protection(mock_run):
    params: Dict[str, Any] = {
        "code": "cursor.execute('SELECT * FROM users WHERE id = ' + user_id)"
    }
    result = SqlalchemyService.execute_operation("sql_injection_protection", params)
    assert result["success"] is True
    assert result["status"] == "ok"
    assert isinstance(result["result"], list)
    assert len(result["result"]) >= 1


def test_fastapi_security_service_api_key_auth(mock_run):
    params: Dict[str, Any] = {
        "spec": {
            "servers": [{"url": "https://api.example.com"}],
            "components": {"securitySchemes": {"apiKey": {"type": "apiKey"}}},
            "paths": {"/api/v1/items": {}, "/health": {}},
        }
    }
    result = FastApiService.execute_operation("api_key_auth", params)
    assert result["success"] is True
    assert result["status"] == "ok"
    assert isinstance(result["result"], list)
    assert all(item.get("passed") is True for item in result["result"])


def test_open_source_license_service_review_license_compliance(mock_run):
    params: Dict[str, Any] = {
        "dependencies": [
            {"name": "proprietary-lib", "license": "Proprietary"},
            {"name": "requests", "license": "Apache-2.0"},
        ]
    }
    result = LicenseService.execute_operation("review_license_compliance", params)
    assert result["success"] is True
    assert result["status"] == "ok"
    assert isinstance(result["result"], list)
    assert any(issue.get("package") == "proprietary-lib" for issue in result["result"])
