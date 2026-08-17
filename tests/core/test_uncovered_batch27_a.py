# -*- coding: utf-8 -*-
"""Batch 27a coverage tests for zero-coverage core modules."""

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = [pytest.mark.core]


# ---------------------------------------------------------------------------
# core.memory_usage_optimizer
# ---------------------------------------------------------------------------


@pytest.fixture
def mem_mocks(monkeypatch):
    """Mock external deps for MemoryUsageOptimizer."""
    psutil_mod = MagicMock()
    psutil_mod.virtual_memory.return_value = SimpleNamespace(
        total=8_000_000_000,
        used=2_000_000_000,
        available=6_000_000_000,
        percent=25.0,
    )
    monkeypatch.setitem(sys.modules, "psutil", psutil_mod)

    numpy_mod = MagicMock()
    numpy_mod.array = lambda x: x
    numpy_mod.polyfit = MagicMock(return_value=(60.0, 0.0))
    monkeypatch.setitem(sys.modules, "numpy", numpy_mod)

    monkeypatch.setattr("core.memory_usage_optimizer.tracemalloc.start", lambda: None)

    def fake_snapshot():
        tb = [SimpleNamespace(filename="test.py", lineno=1)]
        return SimpleNamespace(
            statistics=lambda kind: [SimpleNamespace(traceback=tb, size=1_048_576, count=5)]
        )

    monkeypatch.setattr("core.memory_usage_optimizer.tracemalloc.take_snapshot", fake_snapshot)
    monkeypatch.setattr("core.memory_usage_optimizer.asyncio.create_task", MagicMock())


def test_memory_usage_optimizer_factory():
    from core.memory_usage_optimizer import (
        MemoryUsageOptimizer,
        get_memory_usage_optimizer,
    )

    optimizer = get_memory_usage_optimizer({"monitoring_interval_seconds": 5})
    assert isinstance(optimizer, MemoryUsageOptimizer)
    assert optimizer.monitoring_interval_seconds == 5


def test_take_memory_snapshot(mem_mocks):
    from core.memory_usage_optimizer import MemoryUsageOptimizer

    optimizer = MemoryUsageOptimizer()
    snapshot = optimizer.take_memory_snapshot("worker")
    assert "worker" in snapshot.snapshot_id
    assert len(optimizer.memory_snapshots) == 1


def test_set_and_check_memory_limits(mem_mocks):
    from core.memory_usage_optimizer import MemoryAction, MemoryUsageOptimizer

    optimizer = MemoryUsageOptimizer()
    assert optimizer.check_memory_limit("missing")["status"] == "no_limit"

    optimizer.set_memory_limit(
        "svc",
        100.0,
        warning_threshold_percent=80.0,
        critical_threshold_percent=95.0,
        action_on_exceed=MemoryAction.COLLECT_GARBAGE,
    )

    optimizer.component_memory["svc"] = 50.0
    assert optimizer.check_memory_limit("svc")["status"] == "normal"

    optimizer.component_memory["svc"] = 85.0
    assert optimizer.check_memory_limit("svc")["status"] == "warning"

    optimizer.component_memory["svc"] = 99.0
    assert optimizer.check_memory_limit("svc")["status"] == "critical"


def test_detect_memory_leaks(mem_mocks):
    from core.memory_usage_optimizer import MemorySnapshot, MemoryUsageOptimizer

    optimizer = MemoryUsageOptimizer()
    now = datetime.now(timezone.utc)
    for i in range(12):
        optimizer.memory_snapshots.append(
            MemorySnapshot(
                snapshot_id=f"s{i}",
                timestamp=now - timedelta(hours=1) + timedelta(minutes=i),
                total_memory_mb=8000.0,
                used_memory_mb=100.0 + i * 20.0,
                available_memory_mb=7000.0,
                memory_percent=30.0,
                gc_objects=1000,
                gc_collections={0: 1, 1: 1, 2: 1},
                metadata={"component": "svc"},
            )
        )

    assert optimizer.detect_memory_leaks("svc")
    assert optimizer.total_leaks_detected >= 1


def test_collect_garbage_and_statistics(mem_mocks):
    from core.memory_usage_optimizer import MemoryUsageOptimizer

    optimizer = MemoryUsageOptimizer()
    result = optimizer.collect_garbage(generation=0)
    assert "collected_objects" in result
    assert optimizer.total_gc_collections == 1

    result = optimizer.collect_garbage()
    assert optimizer.total_gc_collections == 2

    stats = optimizer.get_statistics()
    assert stats["total_gc_collections"] == 2


def test_get_memory_trace_and_component_memory(mem_mocks):
    from core.memory_usage_optimizer import MemoryUsageOptimizer

    optimizer = MemoryUsageOptimizer()
    traces = optimizer.get_memory_trace(limit=3)
    assert isinstance(traces, list)

    assert optimizer.get_component_memory("missing") is None


def test_optimize_memory(mem_mocks):
    from core.memory_usage_optimizer import (
        MemoryAction,
        MemorySnapshot,
        MemoryUsageOptimizer,
    )

    optimizer = MemoryUsageOptimizer()
    now = datetime.now(timezone.utc)
    for i in range(12):
        optimizer.memory_snapshots.append(
            MemorySnapshot(
                snapshot_id=f"s{i}",
                timestamp=now - timedelta(hours=1) + timedelta(minutes=i),
                total_memory_mb=8000.0,
                used_memory_mb=100.0 + i * 20.0,
                available_memory_mb=7000.0,
                memory_percent=30.0,
                gc_objects=1000,
                gc_collections={0: 1, 1: 1, 2: 1},
                metadata={"component": "svc"},
            )
        )

    optimizer.set_memory_limit(
        "svc",
        100.0,
        action_on_exceed=MemoryAction.COLLECT_GARBAGE,
    )
    optimizer.component_memory["svc"] = 99.0

    result = optimizer.optimize_memory("svc")
    assert "actions_taken" in result
    assert "garbage_collection" in result["actions_taken"]
    assert "leak_detection" in result["actions_taken"]


def test_get_memory_statistics_empty(mem_mocks):
    from core.memory_usage_optimizer import MemoryUsageOptimizer

    optimizer = MemoryUsageOptimizer()
    optimizer.memory_snapshots.clear()
    stats = optimizer.get_memory_statistics()
    assert "total_memory_mb" in stats


@pytest.mark.asyncio
async def test_start_monitoring(mem_mocks):
    from core.memory_usage_optimizer import MemoryUsageOptimizer

    optimizer = MemoryUsageOptimizer()
    await optimizer.start_monitoring()


# ---------------------------------------------------------------------------
# core.user_training_system
# ---------------------------------------------------------------------------


def test_user_training_system_factory(tmp_path):
    from core.user_training_system import (
        UserTrainingSystem,
        get_user_training_system,
    )

    system = get_user_training_system({"training_dir": str(tmp_path)})
    assert isinstance(system, UserTrainingSystem)


@pytest.mark.asyncio
async def test_user_training_enrollment_and_progress(tmp_path):
    from core.user_training_system import (
        EnrollmentStatus,
        TrainingCourse,
        TrainingModule,
        TrainingStatus,
        TrainingType,
        UserTrainingSystem,
    )

    system = UserTrainingSystem({"training_dir": str(tmp_path)})

    course = TrainingCourse(
        course_id="c_new",
        course_name="New Course",
        training_type=TrainingType.ADVANCED,
        description="desc",
        status=TrainingStatus.PUBLISHED,
    )
    system.register_course(course)
    system.register_module(TrainingModule(module_id="m_new", module_name="M", course_id="c_new"))

    enrollment_id = await system.enroll_user("u2", "c_new")
    assert enrollment_id is not None

    assert await system.update_progress(enrollment_id, 50.0) is True
    assert system.user_enrollments[enrollment_id].status == EnrollmentStatus.IN_PROGRESS

    assert await system.update_progress(enrollment_id, 100.0, score=88.0) is True
    assert system.user_enrollments[enrollment_id].status == EnrollmentStatus.COMPLETED

    assert await system.update_progress("no-such", 10.0) is False

    with pytest.raises(ValueError):
        await system.enroll_user("u2", "no-such-course")


@pytest.mark.asyncio
async def test_user_training_report_and_filters(tmp_path):
    from core.user_training_system import (
        EnrollmentStatus,
        TrainingStatus,
        TrainingType,
        UserTrainingSystem,
    )

    system = UserTrainingSystem({"training_dir": str(tmp_path)})
    enrollment = await system.enroll_user("u3", "onboarding")
    await system.update_progress(enrollment, 100.0)

    assert system.get_course("missing") is None

    published = system.list_courses(status=TrainingStatus.PUBLISHED)
    assert all(c["status"] == "published" for c in published)

    tech = system.list_courses(
        training_type=TrainingType.TECHNICAL, status=TrainingStatus.PUBLISHED
    )
    assert all(c["training_type"] == "technical" for c in tech)

    completed = system.get_user_enrollments(
        user_id="u3", course_id="onboarding", status=EnrollmentStatus.COMPLETED
    )
    assert len(completed) == 1

    report = await system.generate_training_report(user_id="u3")
    assert report["summary"]["completed"] == 1

    report_course = await system.generate_training_report(course_id="onboarding")
    assert report_course["summary"]["total_enrollments"] >= 1

    empty_report = await system.generate_training_report(user_id="noone")
    assert empty_report["summary"]["total_enrollments"] == 0


def test_user_training_statistics():
    from core.user_training_system import UserTrainingSystem

    system = UserTrainingSystem()
    stats = system.get_statistics()
    assert "completion_rate" in stats


# ---------------------------------------------------------------------------
# core.config_validation
# ---------------------------------------------------------------------------


def _make_config(
    env,
    jwt_secret="this-is-32-characters-long-key-for-jwt",
    tls_enabled=False,
    tls_cert="",
    tls_key="",
    db_host="localhost",
    db_name="aiops",
    db_user="user",
    db_pool=5,
    redis_host="localhost",
    ai_enabled=False,
    ai_key="",
    ai_model="gpt-3.5",
    monitoring_enabled=True,
    mfa=False,
    password_policy=False,
    debug=False,
    workers=1,
):
    from core.unified_config import Environment

    return SimpleNamespace(
        environment=Environment(env),
        security=SimpleNamespace(
            jwt_secret_key=jwt_secret,
            tls_enabled=tls_enabled,
            tls_cert_path=tls_cert,
            tls_key_path=tls_key,
            mfa_enabled=mfa,
            password_policy_enabled=password_policy,
        ),
        database=SimpleNamespace(
            host=db_host,
            database=db_name,
            username=db_user,
            pool_size=db_pool,
        ),
        redis=SimpleNamespace(host=redis_host),
        ai=SimpleNamespace(
            enabled=ai_enabled,
            api_key=ai_key,
            model_name=ai_model,
        ),
        monitoring=SimpleNamespace(enabled=monitoring_enabled),
        debug=debug,
        workers=workers,
    )


def test_config_validator_jwt_and_database(monkeypatch):
    from core.config_validation import ConfigValidator, ValidationSeverity

    monkeypatch.setenv("JWT_SECRET_KEY", "dev-secret-key-change-me")
    validator = ConfigValidator()

    # Default secret in development -> warning
    config = _make_config("development", jwt_secret="dev-secret-key-change-me")
    results = validator.validate_config(config)
    assert any(
        r.field == "security.jwt_secret_key" and r.severity == ValidationSeverity.WARNING
        for r in results
    )

    # Default secret in production -> error
    config = _make_config("production", jwt_secret="dev-secret-key-change-me")
    results = validator.validate_config(config)
    assert any(
        r.field == "security.jwt_secret_key" and r.severity == ValidationSeverity.ERROR
        for r in results
    )

    # Short secret
    monkeypatch.setenv("JWT_SECRET_KEY", "some-other-long-secret-key-for-jwt-123")
    config = _make_config("development", jwt_secret="short")
    results = validator.validate_config(config)
    assert any(
        r.field == "security.jwt_secret_key" and r.severity == ValidationSeverity.WARNING
        for r in results
    )

    # Missing database fields
    config = _make_config("development", db_host="", db_name="", db_user="")
    results = validator.validate_config(config)
    assert any(r.field == "database.host" for r in results)
    assert any(r.field == "database.database" for r in results)
    assert any(r.field == "database.username" for r in results)


def test_config_validator_redis_tls_ai(monkeypatch, tmp_path):
    from core.config_validation import ConfigValidator, ValidationSeverity
    from core.unified_config import Environment

    validator = ConfigValidator()

    # Missing redis host
    config = _make_config("development", redis_host="")
    results = validator.validate_config(config)
    assert any(r.field == "redis.host" for r in results)

    # TLS enabled in production with missing files
    cert = tmp_path / "cert.pem"
    key = tmp_path / "key.pem"
    config = _make_config(
        "production",
        tls_enabled=True,
        tls_cert=str(cert),
        tls_key=str(key),
    )
    results = validator.validate_config(config)
    assert any(r.field == "security.tls_cert_path" for r in results)
    assert any(r.field == "security.tls_key_path" for r in results)

    # TLS disabled in production
    config = _make_config("production", tls_enabled=False)
    results = validator.validate_config(config)
    assert any(r.field == "security.tls_enabled" for r in results)

    # AI enabled missing key + gpt-4 in production
    config = _make_config(
        "production",
        ai_enabled=True,
        ai_key="",
        ai_model="gpt-4",
    )
    results = validator.validate_config(config)
    assert any(r.field == "ai.api_key" for r in results)
    assert any(r.field == "ai.model_name" for r in results)

    # AI disabled
    config = _make_config("development", ai_enabled=False)
    results = validator.validate_config(config)
    assert not any(r.field == "ai.api_key" for r in results)


def test_config_validator_monitoring_security_environment(monkeypatch):
    from core.config_validation import ConfigValidator

    validator = ConfigValidator()

    # Monitoring disabled in production
    config = _make_config("production", monitoring_enabled=False)
    results = validator.validate_config(config)
    assert any(r.field == "monitoring.enabled" for r in results)

    # MFA/password in production
    config = _make_config("production", mfa=False, password_policy=False)
    results = validator.validate_config(config)
    assert any(r.field == "security.mfa_enabled" for r in results)
    assert any(r.field == "security.password_policy_enabled" for r in results)

    # Environment rules: debug and workers in production
    config = _make_config("production", debug=True, workers=1)
    results = validator.validate_config(config)
    assert any(r.field == "debug" for r in results)
    assert any(r.field == "workers" for r in results)

    # Workers ok
    config = _make_config("production", debug=False, workers=4)
    results = validator.validate_config(config)
    assert not any(r.field == "workers" for r in results)


def test_config_validator_custom_and_exception_rules():
    from core.config_validation import ConfigValidator, ValidationResult, ValidationSeverity

    validator = ConfigValidator()

    def custom_rule(config):
        return [
            ValidationResult(
                is_valid=True,
                severity=ValidationSeverity.INFO,
                field="custom",
                message="custom rule",
            )
        ]

    validator.add_custom_rule(custom_rule)
    results = validator.validate_config(
        _make_config("development", jwt_secret="a-long-secret-key-with-32-chars-!!")
    )
    assert any(r.field == "custom" for r in results)

    # Exception in a rule
    validator.validation_rules.append(lambda c: (_ for _ in ()).throw(RuntimeError("boom")))
    results = validator.validate_config(_make_config("development"))
    assert any("Validation rule execution failed" in r.message for r in results)


def test_config_health_checker_and_setup(monkeypatch):
    import core.config_validation as cv
    from core.config_validation import ConfigHealthChecker, setup_config_validation

    checker = ConfigHealthChecker()

    # Direct config
    config = _make_config("development", jwt_secret="a-long-secret-key-with-32-chars-!!")
    health = checker.check_config_health(config)
    assert "healthy" in health
    assert health["environment"] == "development"

    # load_environment_config fallback
    fake_manager = MagicMock()
    fake_manager.load_environment_config.return_value = config
    monkeypatch.setattr(cv, "environment_config_manager", fake_manager)
    health = checker.check_config_health()
    assert health["healthy"] is True

    # Exception path in health check
    monkeypatch.setattr(
        checker.validator, "validate_config", MagicMock(side_effect=RuntimeError("boom"))
    )
    health = checker.check_config_health(config)
    assert health["healthy"] is False

    # Setup success
    monkeypatch.undo()
    monkeypatch.setattr(cv, "environment_config_manager", fake_manager)
    result = setup_config_validation()
    assert result["status"] == "success"

    # Setup error
    monkeypatch.setattr(
        cv.config_health_checker, "check_config_health", MagicMock(side_effect=RuntimeError("x"))
    )
    result = setup_config_validation()
    assert result["status"] == "error"


# ---------------------------------------------------------------------------
# core.data_lifecycle_manager
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_data_lifecycle_retention_and_archive():
    from core.data_lifecycle_manager import (
        DataCategory,
        DataLifecycleManager,
        DataLifecycleRule,
        DataRetentionPolicy,
    )

    manager = DataLifecycleManager()

    assert manager.get_retention_days(DataRetentionPolicy.RETAIN_7_DAYS) == 7
    assert manager.get_retention_days(DataRetentionPolicy.RETAIN_PERMANENT) == -1
    assert manager.get_retention_days(DataRetentionPolicy.IMMEDIATE_DELETE) == 0
    assert manager.get_retention_days("unknown_policy") == 30  # default

    # Archive disabled
    result = await manager.archive_old_data(DataCategory.TEMPORARY)
    assert result["status"] == "skipped"

    # No rule
    result = await manager.archive_old_data("unknown")
    assert result["status"] == "error"

    # Permanent retention while enabled -> skipped at retention check
    manager.add_rule(
        DataLifecycleRule(
            category=DataCategory.BACKUP,
            retention_policy=DataRetentionPolicy.RETAIN_PERMANENT,
            archive_enabled=True,
        )
    )
    result = await manager.archive_old_data(DataCategory.BACKUP)
    assert result["status"] == "skipped"

    # Normal archive
    result = await manager.archive_old_data(DataCategory.ALERTS)
    assert result["status"] == "success"


@pytest.mark.asyncio
async def test_data_lifecycle_cleanup_and_delete():
    from core.data_lifecycle_manager import DataCategory, DataLifecycleManager

    manager = DataLifecycleManager()

    result = await manager.cleanup_temp_data()
    assert result["status"] == "success"

    result = await manager._delete_expired_data(DataCategory.METRICS, 30)
    assert result["status"] == "success"
    assert "deleted_count" in result

    result = await manager._simulate_delete(DataCategory.METRICS, datetime.now(timezone.utc))
    assert result == 0


@pytest.mark.asyncio
async def test_data_lifecycle_apply_and_rules(monkeypatch):
    import core.query_optimization as qo
    from core.data_lifecycle_manager import (
        DataCategory,
        DataLifecycleManager,
        setup_data_lifecycle,
    )

    manager = DataLifecycleManager()

    # Force cache cleanup success path
    monkeypatch.setattr(qo, "query_cache", MagicMock(cleanup_expired=MagicMock()))
    cache_ok = await manager._cleanup_temporary_cache(datetime.now(timezone.utc))
    assert cache_ok is True

    # Apply known and unknown categories
    result = await manager.apply_retention_policy(DataCategory.METRICS)
    assert result["status"] == "success"

    result = await manager.apply_retention_policy(DataCategory.CONFIGURATION)
    assert result["status"] == "success"

    result = await manager.apply_retention_policy("unknown")
    assert result["status"] == "error"

    rules = manager.get_rules()
    assert DataCategory.ALERTS in rules

    setup = await setup_data_lifecycle()
    assert setup["status"] == "success"


# ---------------------------------------------------------------------------
# core.test_framework_manager
# ---------------------------------------------------------------------------


def test_test_framework_manager():
    from core.test_framework_manager import (
        TestFrameworkManager,
        TestStatus,
        TestType,
        get_test_framework_manager,
    )

    m1 = get_test_framework_manager()
    m2 = get_test_framework_manager()
    assert m1 is m2

    manager = TestFrameworkManager({"default_coverage_target": 90.0})
    assert manager.default_coverage_target == 90.0

    # Create suite
    assert manager.create_test_suite("s1", "Suite 1", TestType.UNIT, "desc") is True
    assert manager.create_test_suite("s1", "Suite 1 dup", TestType.UNIT, "desc") is False

    # Add cases
    assert manager.add_test_case("t1", "s1", "Test 1", "d", TestType.UNIT) is True
    assert manager.add_test_case("t1", "s1", "Test 1 dup", "d", TestType.UNIT) is False
    assert manager.add_test_case("t2", "missing", "", "", TestType.UNIT) is False

    # Update status
    manager.test_cases["t1"].status = TestStatus.PASSED

    # Run suite
    report = manager.run_test_suite("s1")
    assert report is not None
    assert report.suite_id == "s1"

    missing_report = manager.run_test_suite("missing")
    assert missing_report is None

    summary = manager.get_test_summary()
    assert summary["total_suites"] == 1
    assert summary["cases_by_status"]["passed"] == 1


def test_generate_test_file(tmp_path):
    from core.test_framework_manager import TestFrameworkManager, TestType

    manager = TestFrameworkManager()
    out = tmp_path / "test_unit.py"
    assert manager.generate_test_file("module", "Class", "do_it", TestType.UNIT, str(out)) is True
    assert out.exists()

    assert (
        manager.generate_test_file(
            "module", "Class", "do_it", TestType.INTEGRATION, str(tmp_path / "test_int.py")
        )
        is True
    )

    assert (
        manager.generate_test_file(
            "module", "Class", "do_it", TestType.END_TO_END, str(tmp_path / "test_e2e.py")
        )
        is True
    )

    # Missing template
    del manager.test_templates["unit"]
    assert (
        manager.generate_test_file(
            "module", "Class", "do_it", TestType.UNIT, str(tmp_path / "missing.py")
        )
        is False
    )

    # Template formatting error
    manager.test_templates["broken"] = "{missing_key}"
    assert (
        manager.generate_test_file(
            "module", "Class", "do_it", MagicMock(value="broken"), str(tmp_path / "broken.py")
        )
        is False
    )
