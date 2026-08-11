# -*- coding: utf-8 -*-
"""Tests for core/security_testing_system.py."""

import asyncio

import pytest

from core.security_testing_system import (
    SecurityTest,
    SecurityTestingSystem,
    TestStatus,
    TestType,
    get_security_testing_system,
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
async def test_run_security_test():
    system = SecurityTestingSystem()
    result_id = await system.run_security_test("sast_scan")
    assert result_id == "sast_scan"
    await asyncio.sleep(0)
    result = system.get_test_result("sast_scan")
    assert result is not None
    assert result["status"] in (TestStatus.RUNNING.value, TestStatus.COMPLETED.value)


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
