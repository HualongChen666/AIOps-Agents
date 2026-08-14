# -*- coding: utf-8 -*-
"""Coverage tests for batch 17b core modules."""

import asyncio
import json
import logging
import os
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

import core.db_replication as db_replication
import core.flink_stream_processor as flink_processor
import core.key_management_service as kms
import core.logging.level.sampling_strategy as sampling
import core.retry_enhanced as retry_enhanced
from core.logging.level.level_manager import LogLevel

pytestmark = [pytest.mark.core]


# ---------------------------------------------------------------------------
# db_replication
# ---------------------------------------------------------------------------


def _mock_open_connection():
    reader = AsyncMock()
    writer = AsyncMock()
    writer.close = MagicMock()
    writer.wait_closed = AsyncMock()
    return reader, writer


@pytest.fixture
def rep_env(monkeypatch):
    monkeypatch.setattr(
        db_replication.asyncio,
        "open_connection",
        AsyncMock(return_value=_mock_open_connection()),
    )
    db_replication.configure_replication(
        primary_config={"host": "primary", "port": 5432},
        replicas_config=[{"host": "r0", "port": 5433}, {"host": "r1", "port": 5434}],
        read_write_splitting=True,
        failover_enabled=True,
    )
    yield
    db_replication.configure_replication(
        primary_config={"host": "", "port": 5432},
        replicas_config=[],
        read_write_splitting=False,
        failover_enabled=False,
    )
    db_replication._replication_config["enabled"] = False


def test_db_replication_config_and_getters(rep_env):
    assert db_replication.is_replication_enabled() is True
    assert db_replication.is_read_write_splitting_enabled() is True
    assert db_replication.is_failover_enabled() is True
    primary = db_replication.get_primary_config()
    assert primary == {"host": "primary", "port": 5432}
    assert len(db_replication.get_replica_configs()) == 2
    assert db_replication.get_current_primary() == "primary"
    status = db_replication.get_replication_status()
    assert status["replica_count"] == 2
    assert status["current_primary"] == "primary"


def test_db_replication_getters_when_disabled():
    db_replication._replication_config["enabled"] = False
    assert db_replication.get_primary_config() is None
    assert db_replication.get_replica_configs() == []
    assert db_replication.is_replication_enabled() is False
    db_replication._replication_config["enabled"] = True


def test_db_replication_replica_health_and_healthy_list(rep_env):
    health = db_replication.get_replica_health()
    assert "primary" in health
    assert "replica_0" in health
    assert db_replication.get_healthy_replicas() == ["primary"]


def test_db_replication_check_primary_health(rep_env):
    healthy = asyncio.run(db_replication.check_primary_health())
    assert healthy["status"] == "healthy"
    assert "latency_ms" in healthy


def test_db_replication_check_primary_health_failure(monkeypatch):
    monkeypatch.setattr(
        db_replication.asyncio,
        "open_connection",
        AsyncMock(side_effect=ConnectionRefusedError("down")),
    )
    db_replication.configure_replication(
        primary_config={"host": "p", "port": 5432},
        replicas_config=[{"host": "r0", "port": 5433}],
        failover_enabled=True,
    )
    unhealthy = asyncio.run(db_replication.check_primary_health())
    assert unhealthy["status"] == "unhealthy"
    assert "error" in unhealthy


def test_db_replication_check_replica_health_out_of_range():
    db_replication.configure_replication(
        primary_config={"host": "p", "port": 5432},
        replicas_config=[{"host": "r0", "port": 5433}],
    )
    for idx in (-1, 5):
        result = asyncio.run(db_replication.check_replica_health(idx))
        assert result["status"] == "unhealthy"
        assert result["error"] == "Replica not configured"


def test_db_replication_check_replica_and_all(monkeypatch):
    monkeypatch.setattr(
        db_replication.asyncio,
        "open_connection",
        AsyncMock(return_value=_mock_open_connection()),
    )
    db_replication.configure_replication(
        primary_config={"host": "p", "port": 5432},
        replicas_config=[{"host": "r0", "port": 5433}, {"host": "r1", "port": 5434}],
    )
    single = asyncio.run(db_replication.check_replica_health(0))
    assert single["status"] == "healthy"
    all_health = asyncio.run(db_replication.check_all_replicas_health())
    assert all_health["primary"]["status"] == "healthy"
    assert all_health["replica_0"]["status"] == "healthy"
    assert all_health["replica_1"]["status"] == "healthy"


def test_db_replication_failover_and_promote(rep_env):
    # primary becomes unhealthy, one replica healthy
    db_replication._replica_health["primary"] = {"status": "unhealthy"}
    db_replication._replica_health["replica_0"] = {"status": "healthy"}
    assert asyncio.run(db_replication.perform_failover()) is True
    assert db_replication.get_current_primary() == "replica_0"

    # promote without failover enabled returns False
    db_replication._replication_config["failover_enabled"] = False
    assert asyncio.run(db_replication.promote_replica_to_primary(0)) is False
    db_replication._replication_config["failover_enabled"] = True


def test_db_replication_no_healthy_replica_for_failover():
    db_replication.configure_replication(
        primary_config={"host": "p", "port": 5432},
        replicas_config=[{"host": "r0"}],
        failover_enabled=True,
    )
    db_replication._replica_health["primary"] = {"status": "unhealthy"}
    db_replication._replica_health["replica_0"] = {"status": "unhealthy"}
    assert asyncio.run(db_replication.perform_failover()) is False


def test_db_replication_primary_healthy_no_failover_needed():
    db_replication.configure_replication(
        primary_config={"host": "p", "port": 5432},
        replicas_config=[{"host": "r0"}],
        failover_enabled=True,
    )
    db_replication._replica_health["primary"] = {"status": "healthy"}
    assert asyncio.run(db_replication.perform_failover()) is True


# ---------------------------------------------------------------------------
# flink_stream_processor
# ---------------------------------------------------------------------------


def test_flink_job_config_defaults():
    config = flink_processor.FlinkJobConfig(
        job_name="metrics", job_type=flink_processor.FlinkJobType.METRICS_AGGREGATION
    )
    assert config.parallelism == 2
    assert config.checkpoint_interval == 60000
    assert "flink-savepoints" in config.savepoint_path
    assert config.state_backend.startswith("file://")


def test_flink_stream_job_process_and_record_methods():
    for jt in flink_processor.FlinkJobType:
        config = flink_processor.FlinkJobConfig(job_name=f"job-{jt.value}", job_type=jt)
        job = flink_processor.FlinkStreamJob(config)
        assert job.process_stream([{"x": 1}]) == []
        result = job._stub_process([{"value": 1200, "label": "x"}])
        assert len(result) == 1
        if jt == flink_processor.FlinkJobType.METRICS_AGGREGATION:
            assert result[0]["aggregated"] is True
        elif jt == flink_processor.FlinkJobType.ANOMALY_DETECTION:
            assert result[0]["is_anomaly"] is True
        elif jt == flink_processor.FlinkJobType.DATA_CLEANING:
            assert result[0]["cleaned"] is True
        elif jt == flink_processor.FlinkJobType.ALERT_AGGREGATION:
            assert result[0]["aggregation_count"] == 1


def test_flink_stream_job_clean_data_digit():
    config = flink_processor.FlinkJobConfig(
        job_name="clean", job_type=flink_processor.FlinkJobType.DATA_CLEANING
    )
    job = flink_processor.FlinkStreamJob(config)
    out = job._stub_process([{"a": "123", "b": None}])
    assert out[0]["a"] == 123
    assert out[0]["b"] is None
    assert out[0]["cleaned"] is True


def test_flink_stream_job_record_error(monkeypatch):
    config = flink_processor.FlinkJobConfig(
        job_name="agg", job_type=flink_processor.FlinkJobType.METRICS_AGGREGATION
    )
    job = flink_processor.FlinkStreamJob(config)
    monkeypatch.setattr(job, "_aggregate_metrics", lambda r: (_ for _ in ()).throw(TypeError("boom")))
    assert job._process_record({"x": 1}) is None


def test_flink_job_manager_and_global_instance():
    manager = flink_processor.get_flink_job_manager()
    assert manager._initialized is True
    config = flink_processor.FlinkJobConfig(
        job_name="managed", job_type=flink_processor.FlinkJobType.DATA_CLEANING
    )
    job = manager.create_job(config)
    assert manager.get_job("managed") is job
    assert manager.start_job("managed") is True
    assert manager.stop_job("managed") is True
    assert manager.start_job("missing") is False
    assert manager.stop_job("missing") is False
    assert manager.get_job_status("managed") == {}


# ---------------------------------------------------------------------------
# key_management_service
# ---------------------------------------------------------------------------


def test_kms_environment_backend(monkeypatch):
    monkeypatch.setenv("AIOPS_TEST_KEY", "secret")
    backend = kms.EnvironmentKeyBackend()
    assert backend.get_key("test_key") == "secret"
    assert backend.key_exists("test_key") is True
    assert backend.set_key("test_key", "new") is True
    assert os.environ["AIOPS_TEST_KEY"] == "new"
    assert backend.delete_key("test_key") is True
    assert backend.key_exists("test_key") is False
    assert backend.delete_key("test_key") is False

    # fallback without prefix
    monkeypatch.setenv("RAW_KEY", "raw_value")
    assert backend.get_key("RAW_KEY") == "raw_value"
    assert backend.key_exists("RAW_KEY") is True


def test_kms_file_backend_normal(tmp_path):
    file_path = tmp_path / "secrets.json"
    backend = kms.FileKeyBackend(str(file_path))
    assert backend.set_key("api_key", "abc") is True
    assert backend.get_key("api_key") == "abc"
    assert backend.key_exists("api_key") is True
    assert backend.set_key("api_key", "xyz") is True
    assert backend.get_key("api_key") == "xyz"
    assert backend.delete_key("api_key") is True
    assert backend.delete_key("api_key") is False


def test_kms_file_backend_corrupt_load(tmp_path):
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("not json", encoding="utf-8")
    backend = kms.FileKeyBackend(str(bad_file))
    assert backend.get_key("anything") is None


def test_kms_file_backend_save_failure(tmp_path):
    backend = kms.FileKeyBackend(str(tmp_path))
    # tmp_path is a directory, so opening it as a file will fail
    assert backend.set_key("x", "y") is False


def test_kms_service_env_and_required_keys(monkeypatch):
    monkeypatch.setenv("AIOPS_JWT_SECRET_KEY", "jwt")
    monkeypatch.setenv("AIOPS_DATABASE_PASSWORD", "dbpass")
    monkeypatch.setenv("AIOPS_OPENAI_API_KEY", "openai")
    service = kms.KeyManagementService(backend_type="environment")
    assert service.get_key("JWT_SECRET_KEY") == "jwt"
    assert service.get_jwt_secret_key() == "jwt"
    assert service.get_jwt_secret_key(required=False) == "jwt"
    assert service.get_database_password() == "dbpass"
    assert service.get_api_key("openai") == "openai"
    assert service.get_key("missing", default="fallback") == "fallback"
    with pytest.raises(ValueError):
        service.get_key("missing", required=True)


def test_kms_service_file_backend(tmp_path):
    svc = kms.KeyManagementService(
        backend_type="file", file_path=str(tmp_path / "svc.json")
    )
    assert svc.set_key("k1", "v1") is True
    assert svc.get_key("k1") == "v1"
    assert svc.key_exists("k1") is True
    assert svc.delete_key("k1") is True
    assert svc.delete_key("k1") is False


def test_kms_service_unsupported_backend():
    with pytest.raises(ValueError, match="Unsupported backend type"):
        kms.KeyManagementService(backend_type="vault")


def test_kms_service_cache_and_stats(monkeypatch):
    monkeypatch.setenv("AIOPS_CACHED_KEY", "cached_value")
    svc = kms.KeyManagementService(
        backend_type="environment", cache_ttl=0.01
    )
    assert svc.get_key_with_cache("cached_key") == "cached_value"
    assert svc.get_key_with_cache("cached_key") == "cached_value"
    assert svc.get_cache_stats()["cached_keys"] == 1
    svc.clear_cache()
    assert svc.get_cache_stats()["cached_keys"] == 0
    # Force cache expiration
    assert svc.get_key_with_cache("cached_key") == "cached_value"
    time.sleep(0.02)
    assert svc.get_key_with_cache("cached_key") == "cached_value"
    # use_cache=False bypasses cache
    monkeypatch.setenv("AIOPS_CACHED_KEY", "new_value")
    assert svc.get_key_with_cache("cached_key", use_cache=False) == "new_value"


def test_kms_service_rotate_and_cleanup(tmp_path):
    svc = kms.KeyManagementService(
        backend_type="file", file_path=str(tmp_path / "rot.json")
    )
    assert svc.set_key("db_pass", "old") is True
    assert svc.rotate_key("db_pass", "new", old_value_retention=0) is True
    assert svc.get_key("db_pass") == "new"
    time.sleep(0.05)
    cleaned = svc.cleanup_old_keys()
    assert cleaned == 1
    assert svc.get_cache_stats()["scheduled_rotations"] == 0


def test_kms_global_service(monkeypatch):
    monkeypatch.setenv("AIOPS_GLOB", "val")
    kms.initialize_key_management(backend_type="environment")
    svc = kms.get_key_service()
    assert isinstance(svc, kms.KeyManagementService)
    assert svc.get_key("glob") == "val"


# ---------------------------------------------------------------------------
# retry_enhanced
# ---------------------------------------------------------------------------


def test_retry_calculate_delay_strategies():
    base = retry_enhanced.EnhancedRetry(
        base_delay=1.0, max_delay=5.0, backoff_multiplier=2.0, jitter=False
    )
    assert base.calculate_delay(1) == 1.0
    assert base.calculate_delay(2) == 2.0
    assert base.calculate_delay(3) == 4.0
    assert base.calculate_delay(10) == 5.0  # capped

    fixed = retry_enhanced.EnhancedRetry(
        strategy=retry_enhanced.RetryStrategy.FIXED_DELAY, base_delay=1.5, jitter=False
    )
    assert fixed.calculate_delay(99) == 1.5

    linear = retry_enhanced.EnhancedRetry(
        strategy=retry_enhanced.RetryStrategy.LINEAR_BACKOFF,
        base_delay=1.0,
        max_delay=100.0,
        backoff_multiplier=2.0,
        jitter=False,
    )
    assert linear.calculate_delay(2) == 3.0
    assert linear.calculate_delay(3) == 5.0

    immediate = retry_enhanced.EnhancedRetry(
        strategy=retry_enhanced.RetryStrategy.IMMEDIATE, jitter=False
    )
    assert immediate.calculate_delay(5) == 0.0

    jittered = retry_enhanced.EnhancedRetry(
        base_delay=10.0, jitter=True, jitter_range=0.1
    )
    assert jittered.calculate_delay(1) >= 0.0


def test_retry_should_retry_conditions():
    er = retry_enhanced.EnhancedRetry()
    assert er.should_retry(ConnectionError()) is True
    assert er.should_retry(TimeoutError()) is True
    assert er.should_retry(ValueError("plain")) is False

    class ServerErr(Exception):
        status_code = 500

    class RateLimit(Exception):
        status_code = 429

    assert er.should_retry(ServerErr()) is True
    assert er.should_retry(RateLimit()) is True

    er_custom = retry_enhanced.EnhancedRetry(
        retry_on=lambda e: not isinstance(e, ConnectionError)
    )
    assert er_custom.should_retry(ConnectionError()) is False
    assert er_custom.should_retry(TimeoutError()) is True

    er_exc = retry_enhanced.EnhancedRetry(
        retry_on_exceptions=(RuntimeError,)
    )
    assert er_exc.should_retry(RuntimeError()) is True
    assert er_exc.should_retry(ConnectionError()) is False


def test_retry_condition_helpers():
    cond = retry_enhanced.RetryCondition
    assert cond.is_retryable_exception(OSError()) is True
    assert cond.is_server_error(type("E", (Exception,), {"status_code": 503})()) is True
    assert cond.is_rate_limited(type("E", (Exception,), {"status_code": 429})()) is True
    assert cond.is_server_error(ValueError()) is False
    custom = cond.custom_condition(lambda e: "retry" in str(e).lower())
    assert custom(ValueError("retry me")) is True


def test_retry_sync_wrapper_success_after_retry():
    calls = []

    @retry_enhanced.retry_with_enhanced_retry(
        max_attempts=3,
        base_delay=0.0,
        jitter=False,
        strategy=retry_enhanced.RetryStrategy.IMMEDIATE,
    )
    def flaky():
        calls.append(1)
        if len(calls) < 2:
            raise ConnectionError("nope")
        return "ok"

    assert flaky() == "ok"
    assert len(calls) == 2


def test_retry_sync_wrapper_non_retryable_raises():
    @retry_enhanced.retry_with_enhanced_retry(
        max_attempts=2, base_delay=0.0, jitter=False
    )
    def always_bad():
        raise RuntimeError("not retryable")

    with pytest.raises(RuntimeError):
        always_bad()


def test_retry_sync_wrapper_callback_and_deadline():
    callback_log = []

    def callback(attempt, exc, delay):
        callback_log.append((attempt, type(exc).__name__, delay))

    def once():
        if len(callback_log) == 0:
            raise ConnectionError("fail")
        return "done"

    once_wrapped = retry_enhanced.EnhancedRetry(
        max_attempts=3,
        base_delay=0.0,
        jitter=False,
        on_retry_callback=callback,
    )(once)

    assert once_wrapped() == "done"
    assert len(callback_log) == 1

    # Deadline exceeded before first call
    def slow():
        raise ConnectionError("fail")

    slow_wrapped = retry_enhanced.EnhancedRetry(
        max_attempts=1,
        deadline=-1.0,
        base_delay=0.0,
        jitter=False,
    )(slow)

    with pytest.raises(TimeoutError):
        slow_wrapped()


def test_retry_async_wrapper():
    @retry_enhanced.retry_with_enhanced_retry(
        max_attempts=2,
        base_delay=0.0,
        jitter=False,
        strategy=retry_enhanced.RetryStrategy.IMMEDIATE,
    )
    async def a_flaky():
        a_flaky.calls = getattr(a_flaky, "calls", 0) + 1
        if a_flaky.calls < 2:
            raise TimeoutError("nope")
        return "async-ok"

    assert asyncio.run(a_flaky()) == "async-ok"


def test_retry_metrics():
    m = retry_enhanced.RetryMetrics()
    m.record_attempt("op1", 1, 0.1)
    m.record_attempt("op1", 2, 0.2)
    m.record_success("op1")
    m.record_failure("op1")
    data = m.get_metrics("op1")
    assert data["total_attempts"] == 2
    assert data["success_count"] == 1
    assert data["failure_count"] == 1
    assert data["total_retry_delay"] == pytest.approx(0.3)
    all_data = m.get_all_metrics()
    assert "op1" in all_data


# ---------------------------------------------------------------------------
# sampling_strategy
# ---------------------------------------------------------------------------


def _make_record(levelno):
    return logging.LogRecord("test", levelno, __file__, 1, "msg", (), None, None)


def test_ratio_sampler():
    sampler = sampling.RatioSampler(sampling_rate=1.0, seed=123)
    assert sampler.should_sample(_make_record(logging.INFO)) is True
    assert sampler.get_sampling_rate() == 1.0
    sampler.set_sampling_rate(0.0)
    assert sampler.should_sample(_make_record(logging.INFO)) is False
    with pytest.raises(ValueError):
        sampling.RatioSampler(sampling_rate=2.0)
    with pytest.raises(ValueError):
        sampler.set_sampling_rate(-0.1)


def test_dynamic_sampler(monkeypatch):
    monkeypatch.setattr(sampling._rand, "random", lambda: 0.05)
    sampler = sampling.DynamicSampler(
        initial_rate=0.5, min_rate=0.1, max_rate=1.0, adjustment_interval=0.0
    )
    # Immediate adjustment path via should_sample
    assert sampler.should_sample(_make_record(logging.INFO)) is True
    assert sampler.get_sampling_rate() == 0.5

    sampler.set_rate_adjustment_callback(lambda rate: 0.2)
    monkeypatch.setattr(sampling, "time", type("T", (), {"time": lambda: 999.0}))
    assert sampler.should_sample(_make_record(logging.INFO)) is True
    with pytest.raises(ValueError):
        sampling.DynamicSampler(min_rate=0.5, max_rate=0.1)
    with pytest.raises(ValueError):
        sampler.set_sampling_rate(5.0)


def test_level_based_sampler(monkeypatch):
    monkeypatch.setattr(sampling._rand, "random", lambda: 0.2)
    sampler = sampling.LevelBasedSampler()
    assert sampler.should_sample(_make_record(logging.INFO)) is True
    assert sampler.get_level_sampling_rate(LogLevel.INFO) == 0.5
    sampler.set_level_sampling_rate(LogLevel.INFO, 1.0)
    assert sampler.get_level_sampling_rate(LogLevel.INFO) == 1.0
    sampler.set_default_rate(0.5)
    assert sampler.get_sampling_rate() == 0.5
    with pytest.raises(ValueError):
        sampler.set_default_rate(1.5)
    with pytest.raises(ValueError):
        sampler.set_level_sampling_rate(LogLevel.DEBUG, -1.0)

    # Default rates validation path
    with pytest.raises(ValueError):
        sampling.LevelBasedSampler(level_rates={LogLevel.INFO: 2.0})


def test_composite_sampler():
    always_true = sampling.RatioSampler(sampling_rate=1.0)
    always_false = sampling.RatioSampler(sampling_rate=0.0)

    and_sampler = sampling.CompositeSampler(samplers=[always_true, always_false], operator="AND")
    assert and_sampler.should_sample(_make_record(logging.INFO)) is False

    or_sampler = sampling.CompositeSampler(samplers=[always_true, always_false], operator="OR")
    assert or_sampler.should_sample(_make_record(logging.INFO)) is True

    invalid = sampling.CompositeSampler(samplers=[always_true, always_false], operator="XOR")
    assert invalid.should_sample(_make_record(logging.INFO)) is False

    assert and_sampler.get_sampling_rate() == 0.5
    empty = sampling.CompositeSampler()
    assert empty.get_sampling_rate() == 1.0
    assert empty.should_sample(_make_record(logging.INFO)) is True

    and_sampler.add_sampler(always_true)
    and_sampler.remove_sampler(always_false)
    assert always_false not in and_sampler.samplers
    and_sampler.remove_sampler(always_false)  # no-op


def test_log_sampler_abstract():
    class Dummy(sampling.LogSampler):
        pass

    with pytest.raises(TypeError):
        Dummy()
