# -*- coding: utf-8 -*-
"""Real branch tests for core/integration_test_validator.py.

These tests exercise the validator with real data and real function/method
calls only (no mocks/stubs). They target the uncovered branches in
`IntegrationTestValidator` including success/failure paths, missing IDs,
disabled tests/suites, parallel vs sequential suite execution, report
filtering, and exception fallbacks.
"""

import asyncio
import json
import shutil
from pathlib import Path

import pytest

from core.integration_test_validator import (
    IntegrationTestValidator,
    ValidationCategory,
    ValidationExecution,
    ValidationResult,
    ValidationSuite,
    ValidationTest,
    get_integration_test_validator,
)


def _run(coro):
    return asyncio.run(coro)


def _default_validator(tmp_path, config=None):
    if config is None:
        config = {"reports_dir": str(tmp_path / "reports")}
    return IntegrationTestValidator(config)


# ---------------------------------------------------------------------------
# Construction / factory
# ---------------------------------------------------------------------------
def test_factory_and_dataclasses(tmp_path):
    # factory without config covers `config or {}` false path
    v1 = get_integration_test_validator()
    assert isinstance(v1, IntegrationTestValidator)
    assert v1.reports_dir.exists()

    # factory with config covers truthy path
    v2 = get_integration_test_validator({"reports_dir": str(tmp_path / "r2")})
    assert v2.reports_dir == tmp_path / "r2"

    # clean up the default reports directory created above
    shutil.rmtree(v1.reports_dir, ignore_errors=True)

    # dataclass defaults
    test = ValidationTest(
        test_id="t1",
        test_name="T",
        category=ValidationCategory.FUNCTIONAL,
        description="d",
    )
    assert test.enabled is True
    assert test.timeout == 300

    suite = ValidationSuite(suite_id="s1", suite_name="S", description="d")
    assert suite.parallel_execution is False
    assert suite.enabled is True

    execution = ValidationExecution(execution_id="e1", test_id="t1")
    assert execution.result == ValidationResult.SKIPPED


# ---------------------------------------------------------------------------
# Registration and statistics
# ---------------------------------------------------------------------------
def test_register_and_statistics(tmp_path):
    v = _default_validator(tmp_path)
    assert len(v.validation_tests) == 8
    assert len(v.validation_suites) == 3

    # register a disabled test and suite
    disabled_test = ValidationTest(
        test_id="disabled_test",
        test_name="D",
        category=ValidationCategory.RELIABILITY,
        description="d",
        enabled=False,
    )
    v.register_test(disabled_test)
    assert "disabled_test" in v.validation_tests

    disabled_suite = ValidationSuite(
        suite_id="disabled_suite",
        suite_name="D",
        description="d",
        enabled=False,
    )
    v.register_suite(disabled_suite)
    assert "disabled_suite" in v.validation_suites

    stats = v.get_statistics()
    assert stats["total_tests"] == 9
    assert stats["enabled_tests"] == 8
    assert stats["total_suites"] == 4
    assert stats["enabled_suites"] == 3
    assert stats["total_executions"] == 0
    assert stats["pass_rate"] == 0.0


# ---------------------------------------------------------------------------
# run_validation: missing / disabled / pass / fail
# ---------------------------------------------------------------------------
async def _run_validation_errors(validator):
    with pytest.raises(ValueError, match="Test not found"):
        await validator.run_validation("missing_test")

    validator.validation_tests["functional_api"].enabled = False
    try:
        with pytest.raises(ValueError, match="not enabled"):
            await validator.run_validation("functional_api")
    finally:
        validator.validation_tests["functional_api"].enabled = True


def test_run_validation_errors(tmp_path):
    v = _default_validator(tmp_path)
    _run(_run_validation_errors(v))


async def _run_many_direct(validator, test_id, n):
    # Use explicitly unique execution IDs to avoid timestamp collisions
    exec_ids = [f"bulk_{i}" for i in range(n)]
    for eid in exec_ids:
        validator.validation_executions[eid] = ValidationExecution(
            execution_id=eid, test_id=test_id
        )
    await asyncio.gather(*(validator._execute_validation(eid) for eid in exec_ids))
    return [validator.get_execution_status(eid) for eid in exec_ids]


def test_validation_pass_and_fail(tmp_path):
    v = _default_validator(tmp_path)
    statuses = _run(_run_many_direct(v, "functional_api", 80))
    results = [s["result"] for s in statuses]

    assert ValidationResult.PASSED.value in results
    assert ValidationResult.FAILED.value in results
    assert v.total_passed > 0
    assert v.total_failed > 0

    for s in statuses:
        assert s["started_at"] is not None
        assert s["completed_at"] is not None
        assert s["duration"] >= 0


# ---------------------------------------------------------------------------
# _execute_validation: not found, missing test, and exception fallback
# ---------------------------------------------------------------------------
async def _execution_missing_and_error(validator):
    # execution id missing -> early return
    assert await validator._execute_validation("no_such_execution") is None

    # test id missing -> graceful ERROR, started_at is set, duration computed
    exec_id = "exec_missing_test"
    validator.validation_executions[exec_id] = ValidationExecution(
        execution_id=exec_id, test_id="definitely_not_present"
    )
    await validator._execute_validation(exec_id)
    execution = validator.validation_executions[exec_id]
    assert execution.result == ValidationResult.ERROR
    assert execution.started_at is not None
    assert execution.completed_at is not None
    assert execution.duration >= 0
    assert "definitely_not_present" in execution.error_message
    assert validator.total_failed == 1


def test_execute_validation_missing_and_error(tmp_path):
    v = _default_validator(tmp_path)
    _run(_execution_missing_and_error(v))


async def _execution_started_at_none(validator):
    exec_id = "exec_none_started"
    validator.validation_executions[exec_id] = ValidationExecution(
        execution_id=exec_id, test_id="functional_api"
    )

    async def tamper():
        await asyncio.sleep(0.1)
        validator.validation_executions[exec_id].started_at = None

    # tamper with started_at so the duration calculation raises;
    # the exception fallback must keep duration at 0.0 because started_at is None
    await asyncio.gather(validator._execute_validation(exec_id), tamper())
    execution = validator.validation_executions[exec_id]
    assert execution.result == ValidationResult.ERROR
    assert execution.started_at is None
    assert execution.completed_at is not None
    assert execution.duration == 0.0
    assert validator.total_failed == 1


def test_execute_validation_started_at_none(tmp_path):
    v = _default_validator(tmp_path)
    _run(_execution_started_at_none(v))


# ---------------------------------------------------------------------------
# _wait_for_execution branches
# ---------------------------------------------------------------------------
async def _wait_branches(validator):
    # missing id breaks immediately
    await validator._wait_for_execution("missing_execution")

    # completed execution breaks on result check
    exec_id = await validator.run_validation("functional_api")
    await validator._wait_for_execution(exec_id)
    status = validator.get_execution_status(exec_id)
    assert status is not None
    assert status["result"] in (
        ValidationResult.PASSED.value,
        ValidationResult.FAILED.value,
    )

    # in-progress execution enters the polling loop before breaking
    exec_id2 = await validator.run_validation("functional_api")
    await validator._wait_for_execution(exec_id2)


def test_wait_for_execution_branches(tmp_path):
    v = _default_validator(tmp_path)
    _run(_wait_branches(v))


# ---------------------------------------------------------------------------
# get_execution_status branches
# ---------------------------------------------------------------------------
def test_get_execution_status_branches(tmp_path):
    v = _default_validator(tmp_path)
    assert v.get_execution_status("missing") is None

    v.validation_executions["e_pending"] = ValidationExecution(
        execution_id="e_pending", test_id="functional_api"
    )
    status = v.get_execution_status("e_pending")
    assert status is not None
    assert status["result"] == ValidationResult.SKIPPED.value
    assert status["started_at"] is None
    assert status["completed_at"] is None


# ---------------------------------------------------------------------------
# run_suite branches: missing, disabled, parallel, sequential, unknown tests
# ---------------------------------------------------------------------------
async def _run_suite_branches(validator):
    # suite not found
    with pytest.raises(ValueError, match="Suite not found"):
        await validator.run_suite("missing_suite")

    # suite disabled
    validator.validation_suites["security_suite"].enabled = False
    try:
        with pytest.raises(ValueError, match="not enabled"):
            await validator.run_suite("security_suite")
    finally:
        validator.validation_suites["security_suite"].enabled = True

    # parallel execution (default functional_suite)
    ids = await validator.run_suite("functional_suite")
    assert len(ids) == 2
    for eid in ids:
        status = validator.get_execution_status(eid)
        assert status is not None
        assert status["result"] in (
            ValidationResult.PASSED.value,
            ValidationResult.FAILED.value,
        )

    # sequential execution with one test
    seq = ValidationSuite(
        suite_id="seq_one",
        suite_name="Sequential one",
        description="d",
        tests=["reliability_uptime"],
        parallel_execution=False,
    )
    validator.register_suite(seq)
    ids = await validator.run_suite("seq_one")
    assert len(ids) == 1

    # parallel suite with an unknown test (covers `if test_id in validation_tests` false)
    unknown_par = ValidationSuite(
        suite_id="unknown_parallel",
        suite_name="Unknown Parallel",
        description="d",
        tests=["missing_test_id"],
        parallel_execution=True,
    )
    validator.register_suite(unknown_par)
    ids = await validator.run_suite("unknown_parallel")
    assert ids == []

    # sequential suite with an unknown test
    unknown_seq = ValidationSuite(
        suite_id="unknown_seq",
        suite_name="Unknown Sequential",
        description="d",
        tests=["missing_test_id"],
        parallel_execution=False,
    )
    validator.register_suite(unknown_seq)
    ids = await validator.run_suite("unknown_seq")
    assert ids == []


def test_run_suite_branches(tmp_path):
    v = _default_validator(tmp_path)
    _run(_run_suite_branches(v))


# ---------------------------------------------------------------------------
# generate_validation_report branches
# ---------------------------------------------------------------------------
async def _report_branches(validator):
    # no suite_id, no executions -> total 0 -> pass_rate 0.0
    report = await validator.generate_validation_report()
    assert report["summary"]["total"] == 0
    assert report["summary"]["pass_rate"] == 0.0
    assert report["suite_id"] is None

    # create a single-test sequential suite and run it
    seq = ValidationSuite(
        suite_id="seq_one",
        suite_name="Sequential one",
        description="d",
        tests=["reliability_uptime"],
        parallel_execution=False,
    )
    validator.register_suite(seq)
    await validator.run_suite("seq_one")

    # valid suite filter
    report = await validator.generate_validation_report(suite_id="seq_one")
    assert report["summary"]["total"] == 1
    assert report["suite_id"] == "seq_one"
    assert 0.0 <= report["summary"]["pass_rate"] <= 1.0

    # invalid suite filter -> total 0
    report = await validator.generate_validation_report(suite_id="missing_suite")
    assert report["summary"]["total"] == 0
    assert report["summary"]["pass_rate"] == 0.0

    # all executions (no suite_id) now has total > 0
    report = await validator.generate_validation_report()
    assert report["summary"]["total"] >= 1
    assert report["report_id"] in validator.validation_reports

    # report file was written to disk
    report_path = validator.reports_dir / f"{report['report_id']}.json"
    assert report_path.exists()
    data = json.loads(report_path.read_text())
    assert data["report_id"] == report["report_id"]


def test_generate_validation_report_branches(tmp_path):
    v = _default_validator(tmp_path)
    _run(_report_branches(v))
