# -*- coding: utf-8 -*-
"""Targeted functional coverage tests for core.environment_config,
core.performance_scheduler, core.crypto, core.priority.assessor and
core.model_fine_tuner.
"""

import asyncio
import types
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from cryptography.fernet import Fernet

import core.crypto as crypto
import core.environment_config as env_config
import core.model_fine_tuner as fine_tuner
import core.performance_scheduler as perf_sched
import core.priority.assessor as assessor

pytestmark = [pytest.mark.core]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def env_fakes(monkeypatch):
    """Provide a fake ConfigManager/Config for environment_config tests."""

    class FakeSecurity:
        jwt_secret_key = "prod-secret-key"
        tls_enabled = True

    class FakeAppConfig:
        environment = None
        debug = None
        workers = None
        security = FakeSecurity()

    class FakeConfigManager:
        def __init__(self):
            pass

        def load_config(self, file_path):
            return FakeAppConfig()

    monkeypatch.setattr(env_config, "ConfigManager", FakeConfigManager)
    monkeypatch.setattr(env_config, "setup_unified_configuration", lambda config_file: {"ok": True})
    return FakeAppConfig


@pytest.fixture
def perf_fakes(monkeypatch):
    """Provide fake scheduler and performance sub-system components."""

    class FakeScheduler:
        def __init__(self):
            self.jobs = []
            self.started = False
            self.stopped = False

        def add_job(self, func, trigger=None, **kwargs):
            self.jobs.append((func, kwargs))

        def start(self):
            self.started = True

        def shutdown(self):
            self.stopped = True

    class FakeCollector:
        pass

    class FakeDetector:
        get_active_regressions = AsyncMock(return_value=[{"id": "r1"}])

    class FakeReportGenerator:
        generate_daily_report = AsyncMock(return_value={"report_type": "daily"})
        generate_weekly_report = AsyncMock(return_value={"report_type": "weekly"})
        generate_monthly_report = AsyncMock(return_value={"report_type": "monthly"})

    monkeypatch.setattr(perf_sched, "AsyncIOScheduler", FakeScheduler)
    monkeypatch.setattr(perf_sched, "PerformanceDataCollector", FakeCollector)
    monkeypatch.setattr(perf_sched, "PerformanceRegressionDetector", FakeDetector)
    monkeypatch.setattr(perf_sched, "PerformanceReportGenerator", FakeReportGenerator)
    return {
        "scheduler": FakeScheduler,
        "detector": FakeDetector,
        "report_generator": FakeReportGenerator,
    }


@pytest.fixture
def crypto_reset(monkeypatch):
    """Reset the lazy Fernet singleton between crypto tests."""
    monkeypatch.setattr(crypto, "_fernet", None)
    monkeypatch.setenv("SNAPSHOT_ENCRYPTION_ENABLED", "true")
    return None


@pytest.fixture
def tuner(tmp_path, monkeypatch):
    """Provide a ModelFineTuner using temp directories."""
    cfg = {
        "models_dir": str(tmp_path / "models"),
        "checkpoints_dir": str(tmp_path / "checkpoints"),
    }
    return fine_tuner.ModelFineTuner(cfg)


@pytest.fixture
def fast_fine_tuner_asyncio(monkeypatch):
    """Replace fine_tuner.asyncio so training sleeps complete instantly."""

    class FakeAsyncio:
        create_task = staticmethod(asyncio.create_task)

        @staticmethod
        async def sleep(delay, result=None):
            return result

    monkeypatch.setattr(fine_tuner, "asyncio", FakeAsyncio)
    return FakeAsyncio


# ---------------------------------------------------------------------------
# core.environment_config
# ---------------------------------------------------------------------------


def test_detect_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("ENVIRONMENT", "staging")
    manager = env_config.EnvironmentConfigManager(tmp_path)
    assert manager.get_current_environment() == env_config.Environment.STAGING

    monkeypatch.setenv("ENVIRONMENT", "not_an_env")
    manager2 = env_config.EnvironmentConfigManager(tmp_path)
    assert manager2.get_current_environment() == env_config.Environment.DEVELOPMENT


def test_get_config_file_and_availability(tmp_path):
    (tmp_path / "development.yaml").write_text("dev")
    (tmp_path / "test.yaml").write_text("test")

    dev_manager = env_config.EnvironmentConfigManager(tmp_path)
    assert dev_manager.get_config_file_path().endswith("development.yaml")

    test_manager = env_config.EnvironmentConfigManager(tmp_path)
    # ENVIRONMENT is not modified, default is development, so create production manager
    # by instantiating with an explicit env monkeypatch is not possible here because
    # the environment is resolved at init time. We assert the path helper logic.
    available = test_manager.list_available_environments()
    assert available["development"] is True
    assert available["test"] is True
    assert available["production"] is False


def test_config_file_fallback_and_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    (tmp_path / "development.yaml").write_text("dev")
    manager = env_config.EnvironmentConfigManager(tmp_path)
    assert manager.get_config_file_path().endswith("development.yaml")

    monkeypatch.setenv("ENVIRONMENT", "staging")
    empty = tmp_path / "empty"
    empty.mkdir()
    manager2 = env_config.EnvironmentConfigManager(empty)
    assert manager2.get_config_file_path() is None


def test_load_environment_config(env_fakes, tmp_path, monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    (tmp_path / "production.yaml").write_text("prod")
    manager = env_config.EnvironmentConfigManager(tmp_path)
    config = manager.load_environment_config()
    assert config.environment == env_config.Environment.PRODUCTION
    assert config.debug is False
    assert config.workers == 4

    monkeypatch.setenv("ENVIRONMENT", "staging")
    (tmp_path / "staging.yaml").write_text("stg")
    manager2 = env_config.EnvironmentConfigManager(tmp_path)
    config2 = manager2.load_environment_config()
    assert config2.workers == 2

    monkeypatch.setenv("ENVIRONMENT", "development")
    (tmp_path / "development.yaml").write_text("dev")
    manager3 = env_config.EnvironmentConfigManager(tmp_path)
    config3 = manager3.load_environment_config()
    assert config3.debug is True
    assert config3.workers == 1


def test_validate_environment_config_valid(env_fakes, tmp_path, monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    (tmp_path / "production.yaml").write_text("prod")
    manager = env_config.EnvironmentConfigManager(tmp_path)
    result = manager.validate_environment_config()
    assert result["config_file_exists"] is True
    assert result["valid"] is True
    assert len(result["validation_errors"]) == 0


def test_validate_environment_config_invalid(env_fakes, tmp_path, monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("JWT_SECRET_KEY", "dev-secret-key-change-me")
    (tmp_path / "production.yaml").write_text("prod")

    class BadSecurity:
        jwt_secret_key = "dev-secret-key-change-me"
        tls_enabled = False

    class BadAppConfig:
        environment = None
        debug = True
        workers = None
        security = BadSecurity()

    manager = env_config.EnvironmentConfigManager(tmp_path)
    bad_config = BadAppConfig()
    monkeypatch.setattr(manager, "load_environment_config", lambda: bad_config)
    result = manager.validate_environment_config()
    assert result["valid"] is False
    assert any("Debug mode" in e for e in result["validation_errors"])
    assert any("JWT secret" in e for e in result["validation_errors"])
    assert any("TLS" in e for e in result["validation_errors"])


def test_validate_environment_config_missing_file(tmp_path, monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    empty = tmp_path / "missing"
    empty.mkdir()
    manager = env_config.EnvironmentConfigManager(empty)
    result = manager.validate_environment_config()
    assert result["config_file_exists"] is False
    assert "valid" not in result


def test_setup_environment_configuration(monkeypatch, env_fakes, tmp_path):
    monkeypatch.setenv("ENVIRONMENT", "development")
    (tmp_path / "development.yaml").write_text("dev")
    manager = env_config.EnvironmentConfigManager(tmp_path)
    monkeypatch.setattr(env_config, "environment_config_manager", manager)
    result = env_config.setup_environment_configuration()
    assert result["status"] == "success"
    assert result["environment"] == "development"
    assert result["unified_config_setup"]["ok"] is True


def test_setup_environment_configuration_error(monkeypatch):
    fake_manager = MagicMock()
    fake_manager.validate_environment_config.side_effect = RuntimeError("boom")
    monkeypatch.setattr(env_config, "environment_config_manager", fake_manager)
    result = env_config.setup_environment_configuration()
    assert result["status"] == "error"
    assert "boom" in result["error"]


# ---------------------------------------------------------------------------
# core.performance_scheduler
# ---------------------------------------------------------------------------


def test_performance_scheduler_lifecycle(perf_fakes):
    scheduler = perf_sched.PerformanceTaskScheduler()
    scheduler.setup_jobs()
    assert len(scheduler.scheduler.jobs) == 6
    scheduler.start()
    assert scheduler.scheduler.started is True
    scheduler.shutdown()
    assert scheduler.scheduler.stopped is True


@pytest.mark.asyncio
async def test_collect_daily_metrics(perf_fakes):
    scheduler = perf_sched.PerformanceTaskScheduler()
    await scheduler.collect_daily_metrics()


@pytest.mark.asyncio
async def test_detect_daily_regressions(perf_fakes):
    scheduler = perf_sched.PerformanceTaskScheduler()
    await scheduler.detect_daily_regressions()
    perf_fakes["detector"].get_active_regressions.assert_awaited()

    perf_fakes["detector"].get_active_regressions = AsyncMock(return_value=[])
    await scheduler.detect_daily_regressions()


@pytest.mark.asyncio
async def test_generate_daily_report(perf_fakes):
    scheduler = perf_sched.PerformanceTaskScheduler()
    await scheduler.generate_daily_report()
    perf_fakes["report_generator"].generate_daily_report.assert_awaited()


@pytest.mark.asyncio
async def test_generate_weekly_report(perf_fakes):
    scheduler = perf_sched.PerformanceTaskScheduler()
    await scheduler.generate_weekly_report()
    perf_fakes["report_generator"].generate_weekly_report.assert_awaited()


@pytest.mark.asyncio
async def test_generate_monthly_report(perf_fakes):
    scheduler = perf_sched.PerformanceTaskScheduler()
    await scheduler.generate_monthly_report()
    perf_fakes["report_generator"].generate_monthly_report.assert_awaited()


@pytest.mark.asyncio
async def test_generate_report_failure(monkeypatch, perf_fakes):
    scheduler = perf_sched.PerformanceTaskScheduler()
    broken = MagicMock()
    broken.generate_daily_report = AsyncMock(side_effect=RuntimeError("report failed"))
    monkeypatch.setattr(scheduler, "report_generator", broken)
    await scheduler.generate_daily_report()


@pytest.mark.asyncio
async def test_cleanup_old_metrics(perf_fakes):
    scheduler = perf_sched.PerformanceTaskScheduler()
    await scheduler.cleanup_old_metrics()


def test_get_task_scheduler():
    assert perf_sched.get_task_scheduler() is perf_sched.task_scheduler


# ---------------------------------------------------------------------------
# core.crypto
# ---------------------------------------------------------------------------


def test_encryption_disabled(crypto_reset, monkeypatch):
    monkeypatch.setenv("SNAPSHOT_ENCRYPTION_ENABLED", "false")
    assert crypto.encrypt_snapshot("hello") == "PLAINTEXT::hello"
    assert crypto.decrypt_snapshot("PLAINTEXT::hello") == "hello"


def test_encrypt_decrypt_roundtrip(crypto_reset, monkeypatch):
    key = Fernet.generate_key().decode("ascii")
    monkeypatch.setenv("SNAPSHOT_ENCRYPTION_KEY", key)
    original = "sensitive payload"
    encrypted = crypto.encrypt_snapshot(original)
    assert not encrypted.startswith(crypto._PLAINTEXT_PREFIX)
    assert crypto.decrypt_snapshot(encrypted) == original


def test_decrypt_plaintext_marker(crypto_reset):
    assert crypto.decrypt_snapshot("PLAINTEXT::visible") == "visible"


def test_decrypt_invalid_data(crypto_reset, monkeypatch, caplog):
    key = Fernet.generate_key().decode("ascii")
    monkeypatch.setenv("SNAPSHOT_ENCRYPTION_KEY", key)
    assert crypto.decrypt_snapshot("not-valid-token") == "not-valid-token"


def test_derive_key_from_seed(crypto_reset, monkeypatch):
    monkeypatch.delenv("SNAPSHOT_ENCRYPTION_KEY", raising=False)
    monkeypatch.setenv("JWT_SECRET_KEY", "seed-key-123")
    assert crypto.encrypt_snapshot("hello").startswith(crypto._PLAINTEXT_PREFIX) is False
    assert crypto.decrypt_snapshot(crypto.encrypt_snapshot("hello")) == "hello"


def test_invalid_encryption_key(crypto_reset, monkeypatch):
    monkeypatch.setenv("SNAPSHOT_ENCRYPTION_KEY", "not-a-valid-key")
    assert crypto.encrypt_snapshot("plain") == "PLAINTEXT::plain"


def test_production_requires_key(crypto_reset, monkeypatch):
    monkeypatch.delenv("SNAPSHOT_ENCRYPTION_KEY", raising=False)
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    monkeypatch.delenv("INTERNAL_API_KEY", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setattr(crypto, "_ENV_PROD", True)
    monkeypatch.setattr(crypto, "_fernet", None)
    with pytest.raises(RuntimeError, match="must be set in production"):
        crypto._get_fernet()


# ---------------------------------------------------------------------------
# core.priority.assessor
# ---------------------------------------------------------------------------


def test_assess_services():
    a = assessor.BusinessImpactAssessor()
    critical = a.assess("payment")
    assert critical.criticality == assessor.BusinessCriticality.CRITICAL

    high = a.assess("api", affected_users=1000, revenue_per_minute=100, sla_violation=True)
    assert high.criticality == assessor.BusinessCriticality.HIGH

    medium = a.assess("cache")
    assert medium.criticality == assessor.BusinessCriticality.MEDIUM

    low = a.assess("logging")
    assert low.criticality == assessor.BusinessCriticality.LOW

    unknown = a.assess("unknown")
    assert unknown.criticality == assessor.BusinessCriticality.LOW


def test_revenue_and_sla_factors():
    a = assessor.BusinessImpactAssessor()
    impact = a.assess(
        "database",
        affected_users=50000,
        revenue_per_minute=15000,
        sla_violation=True,
    )
    assert impact.revenue_impact == 15000 * 60
    assert impact.sla_impact is True
    assert 0.0 <= impact.impact_score <= 1.0
    assert "criticality" in impact.factors


def test_batch_assess():
    a = assessor.BusinessImpactAssessor()
    alerts = [
        {"service": "auth", "affected_users": 100},
        {"service": "cache"},
    ]
    results = a.batch_assess(alerts)
    assert len(results) == 2
    assert results[0].service == "auth"


def test_higher_criticality():
    a = assessor.BusinessImpactAssessor()
    assert (
        a._higher_criticality(
            assessor.BusinessCriticality.LOW,
            assessor.BusinessCriticality.HIGH,
        )
        == assessor.BusinessCriticality.HIGH
    )


# ---------------------------------------------------------------------------
# core.model_fine_tuner
# ---------------------------------------------------------------------------


def test_fine_tuner_init(tuner, tmp_path):
    assert (tmp_path / "models").exists()
    assert (tmp_path / "checkpoints").exists()
    assert tuner.get_statistics()["total_jobs"] == 0


@pytest.mark.asyncio
async def test_start_fine_tuning_and_progress(tuner, fast_fine_tuner_asyncio):
    cfg = fine_tuner.TrainingConfig(
        model_name="t5-small",
        model_type=fine_tuner.ModelType.LANGUAGE_MODEL,
        fine_tuning_method=fine_tuner.FineTuningMethod.LORA,
        num_epochs=1,
    )
    ds = fine_tuner.TrainingDataset(dataset_id="ds-1", dataset_path="data.json")
    job_id = await tuner.start_fine_tuning(cfg, ds)
    assert job_id.startswith("ft_")
    assert job_id in tuner.training_jobs

    # Allow the background task to complete with zero-duration sleeps.
    for _ in range(20):
        status = tuner.training_jobs[job_id].status
        if status == fine_tuner.TrainingStatus.COMPLETED:
            break
        await asyncio.sleep(0)

    progress = tuner.get_training_progress(job_id)
    assert progress["status"] == "completed"
    assert progress["completed_at"] is not None
    assert tuner.get_statistics()["completed_jobs"] == 1


@pytest.mark.asyncio
async def test_execute_training_failure(tuner, fast_fine_tuner_asyncio, monkeypatch):
    cfg = fine_tuner.TrainingConfig(
        model_name="t5-small",
        model_type=fine_tuner.ModelType.LANGUAGE_MODEL,
        fine_tuning_method=fine_tuner.FineTuningMethod.LORA,
    )
    ds = fine_tuner.TrainingDataset(dataset_id="ds-2", dataset_path="data.json")
    job_id = await tuner.start_fine_tuning(cfg, ds)
    monkeypatch.setattr(
        tuner, "_prepare_training", AsyncMock(side_effect=RuntimeError("prep failed"))
    )
    await tuner._execute_training(job_id)
    progress = tuner.get_training_progress(job_id)
    assert progress["status"] == "failed"
    assert "prep failed" in progress["error_message"]


@pytest.mark.asyncio
async def test_cancel_training(tuner, fast_fine_tuner_asyncio, monkeypatch):
    cfg = fine_tuner.TrainingConfig(
        model_name="t5-small",
        model_type=fine_tuner.ModelType.LANGUAGE_MODEL,
        fine_tuning_method=fine_tuner.FineTuningMethod.LORA,
    )
    ds = fine_tuner.TrainingDataset(dataset_id="ds-3", dataset_path="data.json")
    monkeypatch.setattr(tuner, "_execute_training", AsyncMock())
    job_id = await tuner.start_fine_tuning(cfg, ds)
    assert await tuner.cancel_training(job_id) is True
    assert tuner.training_jobs[job_id].status == fine_tuner.TrainingStatus.CANCELLED
    assert await tuner.cancel_training("missing") is False
    assert await tuner.cancel_training(job_id) is False


@pytest.mark.asyncio
async def test_list_and_export_jobs(tuner, fast_fine_tuner_asyncio, tmp_path, monkeypatch):
    cfg = fine_tuner.TrainingConfig(
        model_name="bert",
        model_type=fine_tuner.ModelType.LANGUAGE_MODEL,
        fine_tuning_method=fine_tuner.FineTuningMethod.ADAPTER,
        num_epochs=1,
    )
    ds = fine_tuner.TrainingDataset(dataset_id="ds-4", dataset_path="data.json")
    job_id = await tuner.start_fine_tuning(cfg, ds)
    for _ in range(20):
        if tuner.training_jobs[job_id].status == fine_tuner.TrainingStatus.COMPLETED:
            break
        await asyncio.sleep(0)

    all_jobs = tuner.list_training_jobs()
    assert any(j["job_id"] == job_id for j in all_jobs)

    completed_jobs = tuner.list_training_jobs(fine_tuner.TrainingStatus.COMPLETED)
    assert len(completed_jobs) >= 1

    export_path = await tuner.export_model(job_id, export_format="pytorch")
    assert export_path is not None
    assert Path(export_path).name == "model.pytorch"

    pending_job = fine_tuner.TrainingConfig(
        model_name="pending",
        model_type=fine_tuner.ModelType.LANGUAGE_MODEL,
        fine_tuning_method=fine_tuner.FineTuningMethod.PROMPT_TUNING,
    )
    monkeypatch.setattr(tuner, "_execute_training", AsyncMock())
    pending_id = await tuner.start_fine_tuning(pending_job, ds)
    assert await tuner.export_model(pending_id) is None
    assert await tuner.export_model("unknown") is None


def test_get_statistics_and_factory():
    t = fine_tuner.get_model_fine_tuner({"device": "cpu"})
    stats = t.get_statistics()
    assert stats["success_rate"] == 0.0
    assert stats["active_jobs"] == 0
