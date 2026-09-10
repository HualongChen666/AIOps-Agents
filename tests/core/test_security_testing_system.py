# -*- coding: utf-8 -*-
"""Tests for core/security_testing_system.py."""

import asyncio  # noqa: F401  # Imported for test setup
import json
import subprocess
import types

import pytest  # noqa: F401  # Imported for test setup

from core.security_testing_system import (
    SecurityTest,
    SecurityTestingSystem,
    TestStatus,
    TestType,
    get_security_testing_system,
)

# Genuine bandit JSON report format (``bandit -f json``).
BANDIT_OUTPUT = json.dumps(
    {
        "results": [
            {
                "test_id": "B105",
                "issue_text": "Possible hardcoded password: 'hunter2'",
                "filename": "app.py",
                "line_number": 42,
                "issue_severity": "HIGH",
                "issue_cwe": {
                    "id": 259,
                    "link": "https://cwe.mitre.org/data/definitions/259.html",
                },
                "more_info": "https://bandit.readthedocs.io/en/latest/plugins/b105.html",
            }
        ]
    }
)


def _fake_scanner_run(argv, **kwargs):
    """Stand in for ``subprocess.run`` while keeping the real call contract."""
    assert kwargs.get("shell") is False
    assert kwargs.get("check") is False
    return subprocess.CompletedProcess(argv, 0, stdout=BANDIT_OUTPUT, stderr="")


def _install_fake_scanner(monkeypatch):
    """Make every scanner binary resolvable and emit a real bandit report."""
    import core.security_testing_system as sts

    monkeypatch.setattr(sts, "shutil", types.SimpleNamespace(which=lambda name: f"/fake/{name}"))
    monkeypatch.setattr(
        sts,
        "subprocess",
        types.SimpleNamespace(run=_fake_scanner_run, CompletedProcess=subprocess.CompletedProcess),
    )


def test_get_security_testing_system():
    system = get_security_testing_system()
    assert isinstance(system, SecurityTestingSystem)


def test_register_and_get_test():
    system = SecurityTestingSystem()
    test = SecurityTest(
        test_id="t1",
        test_name="T1",
        test_type=TestType.SAST,
        target="target",
        enabled=True,
    )
    system.register_test(test)
    assert system.security_tests["t1"].test_name == "T1"


@pytest.mark.asyncio
async def test_run_security_test(monkeypatch):
    _install_fake_scanner(monkeypatch)
    system = SecurityTestingSystem()

    result_id = await system.run_security_test("sast_scan")
    assert result_id == "sast_scan"

    # Execute deterministically (the scheduled task may still be pending).
    await system._execute_test("sast_scan")

    result = system.get_test_result("sast_scan")  # noqa: F841  # Variable for test verification
    assert result is not None
    assert result["status"] == TestStatus.COMPLETED.value
    assert result["summary"]["total_vulnerabilities"] == 1
    finding = result["vulnerabilities"][0]
    assert finding["vulnerability_id"] == "B105"
    assert finding["severity"] == "high"
    assert finding["cwe_id"] == "CWE-259"


@pytest.mark.asyncio
async def test_execute_test_without_scanner_fails(monkeypatch):
    """A missing scanner is reported as a failure, never faked as success."""
    import core.security_testing_system as sts

    monkeypatch.setattr(sts, "shutil", types.SimpleNamespace(which=lambda name: None))
    system = SecurityTestingSystem()

    await system._execute_test("sast_scan")

    result = system.get_test_result("sast_scan")
    assert result["status"] == TestStatus.FAILED.value
    assert "no usable security scanner" in result["error_message"]


@pytest.mark.asyncio
async def test_execute_test_requires_explicit_target():
    system = SecurityTestingSystem()

    await system._execute_test("dast_scan")

    result = system.get_test_result("dast_scan")
    assert result["status"] == TestStatus.FAILED.value
    assert "explicit target" in result["error_message"]


def test_vulnerabilities_and_statistics():
    system = SecurityTestingSystem()
    vulns = system.get_vulnerabilities()
    assert isinstance(vulns, list)
    stats = system.get_statistics()
    assert "total_tests" in stats
    assert "total_vulnerabilities" in stats


@pytest.mark.asyncio
async def test_generate_security_report():
    system = SecurityTestingSystem()
    report = await system.generate_security_report()
    assert "total_tests" in report
    assert "total_vulnerabilities" in report
