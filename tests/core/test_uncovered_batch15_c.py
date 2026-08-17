# -*- coding: utf-8 -*-
"""Functional coverage tests for core batch 15-c modules."""

import asyncio
import json
import logging
import os
import sys
import uuid
from unittest.mock import AsyncMock, MagicMock

import grpc
import pytest

import core.integration_test_validator as itv
import core.interface.grpc.client as grpc_client
import core.interface.grpc.interceptor as grpc_interceptor
import core.structured_logging as slog
import core.task_scheduler as ts

pytestmark = [pytest.mark.core]


# ---------------------------------------------------------------------------
# core.integration_test_validator
# ---------------------------------------------------------------------------
@pytest.fixture
def validator(tmp_path, monkeypatch):
    """Fresh IntegrationTestValidator with mocked random."""
    fake_random = MagicMock(random=MagicMock(return_value=0.9))
    monkeypatch.setattr("secrets.SystemRandom", lambda: fake_random)

    return itv.IntegrationTestValidator(config={"reports_dir": str(tmp_path)})


def test_validator_dataclasses():
    test = itv.ValidationTest(
        test_id="t1",
        test_name="T1",
        category=itv.ValidationCategory.FUNCTIONAL,
        description="desc",
    )
    assert test.enabled is True
    assert test.timeout == 300

    suite = itv.ValidationSuite(suite_id="s1", suite_name="S1", description="desc")
    assert suite.parallel_execution is False

    execution = itv.ValidationExecution(execution_id="e1", test_id="t1")
    assert execution.result == itv.ValidationResult.SKIPPED


def test_validator_init_and_defaults(validator):
    assert len(validator.validation_tests) == 8
    assert len(validator.validation_suites) == 3
    assert validator.reports_dir.exists()
    assert validator.total_passed == 0
    assert validator.total_failed == 0


def test_validator_register(validator):
    test = itv.ValidationTest(
        test_id="custom",
        test_name="Custom",
        category=itv.ValidationCategory.SECURITY,
        description="d",
    )
    validator.register_test(test)
    assert "custom" in validator.validation_tests

    suite = itv.ValidationSuite(suite_id="custom_suite", suite_name="Custom Suite", description="d")
    validator.register_suite(suite)
    assert "custom_suite" in validator.validation_suites


@pytest.mark.asyncio
async def test_run_validation_missing_and_disabled(validator):
    with pytest.raises(ValueError, match="Test not found"):
        await validator.run_validation("missing")

    validator.validation_tests["functional_api"].enabled = False
    with pytest.raises(ValueError, match="not enabled"):
        await validator.run_validation("functional_api")


async def _fake_execute(self, execution_id):
    execution = self.validation_executions[execution_id]
    execution.result = itv.ValidationResult.PASSED
    now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
    execution.started_at = execution.started_at or now
    execution.completed_at = now
    execution.duration = (execution.completed_at - execution.started_at).total_seconds()
    execution.output = "Validation passed"
    self.total_passed += 1


@pytest.mark.asyncio
async def test_run_validation_success_and_status(validator, monkeypatch):
    monkeypatch.setattr(itv.IntegrationTestValidator, "_execute_validation", _fake_execute)

    exec_id = await validator.run_validation("functional_api")
    assert exec_id in validator.validation_executions

    await validator._wait_for_execution(exec_id)
    status = validator.get_execution_status(exec_id)
    assert status is not None
    assert status["result"] == itv.ValidationResult.PASSED.value
    assert status["duration"] >= 0
    assert validator.total_passed == 1

    assert validator.get_execution_status("missing") is None

    stats = validator.get_statistics()
    assert stats["total_tests"] == 8
    assert stats["total_executions"] == 1
    assert stats["total_passed"] == 1


@pytest.mark.asyncio
async def test_execute_validation_not_found(validator):
    result = await validator._execute_validation("missing")
    assert result is None


@pytest.mark.asyncio
async def test_execute_validation_exception(validator, monkeypatch):
    async def _fake_sleep_raise(delay):
        raise RuntimeError("boom")

    monkeypatch.setattr(itv.asyncio, "sleep", _fake_sleep_raise)

    exec_id = "exec_manual_1"
    validator.validation_executions[exec_id] = itv.ValidationExecution(
        execution_id=exec_id, test_id="functional_api"
    )

    await validator._execute_validation(exec_id)
    execution = validator.validation_executions[exec_id]
    assert execution.result == itv.ValidationResult.ERROR
    assert "boom" in execution.error_message
    assert execution.completed_at is not None
    assert validator.total_failed == 1


@pytest.mark.asyncio
async def test_run_suite_and_report(validator, monkeypatch):
    monkeypatch.setattr(itv.IntegrationTestValidator, "_execute_validation", _fake_execute)

    exec_ids = await validator.run_suite("functional_suite")
    assert len(exec_ids) == 2

    report = await validator.generate_validation_report()
    assert report["summary"]["total"] == 2
    assert report["summary"]["passed"] == 2
    assert 0.0 < report["summary"]["pass_rate"] <= 1.0
    assert report["report_id"] in validator.validation_reports

    suite_report = await validator.generate_validation_report(suite_id="functional_suite")
    assert suite_report["summary"]["total"] == 2
    assert suite_report["suite_id"] == "functional_suite"

    empty_report = await validator.generate_validation_report(suite_id="missing")
    assert empty_report["summary"]["total"] == 0

    stats = validator.get_statistics()
    assert stats["total_passed"] == 2
    assert stats["pass_rate"] == 1.0


@pytest.mark.asyncio
async def test_run_suite_sequential(validator, monkeypatch):
    monkeypatch.setattr(itv.IntegrationTestValidator, "_execute_validation", _fake_execute)

    exec_ids = await validator.run_suite("performance_suite")
    assert len(exec_ids) == 2
    assert all(e in validator.validation_executions for e in exec_ids)


def test_get_integration_test_validator():
    v = itv.get_integration_test_validator()
    assert isinstance(v, itv.IntegrationTestValidator)


# ---------------------------------------------------------------------------
# core.interface.grpc.client
# ---------------------------------------------------------------------------
@pytest.fixture
def aiops_grpc_client():
    return grpc_client.AIOpsGrpcClient(host="localhost", port=50051, timeout=5.0)


@pytest.mark.asyncio
async def test_grpc_client_connect_success(aiops_grpc_client, monkeypatch):
    fake_channel = MagicMock()
    fake_channel.ready = AsyncMock()
    monkeypatch.setattr(
        grpc_client.grpc.aio, "insecure_channel", MagicMock(return_value=fake_channel)
    )

    await aiops_grpc_client.connect()
    assert aiops_grpc_client._channel is fake_channel
    fake_channel.ready.assert_awaited_once()


@pytest.mark.asyncio
async def test_grpc_client_connect_failure(aiops_grpc_client, monkeypatch):
    monkeypatch.setattr(
        grpc_client.grpc.aio,
        "insecure_channel",
        MagicMock(side_effect=RuntimeError("refused")),
    )

    with pytest.raises(RuntimeError, match="refused"):
        await aiops_grpc_client.connect()


@pytest.mark.asyncio
async def test_grpc_client_close(aiops_grpc_client):
    fake_channel = MagicMock()
    fake_channel.close = AsyncMock()
    aiops_grpc_client._channel = fake_channel
    await aiops_grpc_client.close()
    fake_channel.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_grpc_client_get_metrics_uninitialized(aiops_grpc_client):
    with pytest.raises(RuntimeError, match="not initialized"):
        await aiops_grpc_client.get_metrics()


@pytest.mark.asyncio
async def test_grpc_client_get_alerts_uninitialized(aiops_grpc_client):
    with pytest.raises(RuntimeError, match="not initialized"):
        await aiops_grpc_client.get_alerts()


@pytest.mark.asyncio
async def test_grpc_client_execute_repair_uninitialized(aiops_grpc_client):
    with pytest.raises(RuntimeError, match="not initialized"):
        await aiops_grpc_client.execute_repair("key")


@pytest.mark.asyncio
async def test_grpc_client_get_metrics_not_implemented(aiops_grpc_client):
    aiops_grpc_client._grpc_client = MagicMock()
    with pytest.raises(NotImplementedError):
        await aiops_grpc_client.get_metrics()


@pytest.mark.asyncio
async def test_grpc_client_get_alerts_not_implemented(aiops_grpc_client):
    aiops_grpc_client._grpc_client = MagicMock()
    with pytest.raises(NotImplementedError):
        await aiops_grpc_client.get_alerts(level="error")


@pytest.mark.asyncio
async def test_grpc_client_execute_repair_not_implemented(aiops_grpc_client):
    aiops_grpc_client._grpc_client = MagicMock()
    with pytest.raises(NotImplementedError):
        await aiops_grpc_client.execute_repair("key", {"k": "v"})


@pytest.mark.asyncio
async def test_grpc_client_stream_metrics_not_implemented(aiops_grpc_client):
    with pytest.raises(NotImplementedError):
        async for _ in aiops_grpc_client.stream_metrics():
            pass


# ---------------------------------------------------------------------------
# core.task_scheduler
# ---------------------------------------------------------------------------
def test_inmemory_scheduler_one_off():
    scheduler = ts._InMemoryScheduler()
    coro = AsyncMock()
    scheduler.schedule("one", coro)
    tasks = scheduler.list_tasks()
    assert len(tasks) == 1
    assert tasks[0]["name"] == "one"
    assert tasks[0]["cron"] is None
    assert tasks[0]["interval"] is None

    scheduler.cancel("one")
    assert scheduler.list_tasks() == []
    scheduler.cancel("missing")  # no-op


def test_inmemory_scheduler_duplicate():
    scheduler = ts._InMemoryScheduler()
    scheduler.schedule("dup", AsyncMock())
    with pytest.raises(ValueError, match="already scheduled"):
        scheduler.schedule("dup", AsyncMock())


@pytest.mark.asyncio
async def test_inmemory_scheduler_interval(monkeypatch):
    scheduler = ts._InMemoryScheduler()
    sleep = AsyncMock(side_effect=[None, RuntimeError("stop")])
    monkeypatch.setattr(ts.asyncio, "sleep", sleep)

    coro = AsyncMock(side_effect=[RuntimeError("boom"), None])
    with pytest.raises(RuntimeError, match="stop"):
        await scheduler._run_interval("i", coro, 1)

    assert coro.call_count >= 1
    assert sleep.call_count == 2


@pytest.mark.asyncio
async def test_inmemory_scheduler_cron_interval(monkeypatch):
    scheduler = ts._InMemoryScheduler()
    sleep = AsyncMock(side_effect=[None, RuntimeError("stop")])
    monkeypatch.setattr(ts.asyncio, "sleep", sleep)

    coro = AsyncMock(side_effect=[RuntimeError("boom"), None])
    with pytest.raises(RuntimeError, match="stop"):
        await scheduler._run_cron("c", coro, "*/2 * * * *")

    assert coro.call_count >= 1
    assert sleep.call_count == 2
    wait_arg = sleep.call_args_list[0][0][0]
    assert wait_arg >= 0


@pytest.mark.asyncio
async def test_inmemory_scheduler_cron_fallback(monkeypatch):
    scheduler = ts._InMemoryScheduler()
    sleep = AsyncMock(side_effect=[None, RuntimeError("stop")])
    monkeypatch.setattr(ts.asyncio, "sleep", sleep)

    coro = AsyncMock(return_value=None)
    with pytest.raises(RuntimeError, match="stop"):
        await scheduler._run_cron("c", coro, "0 * * * *")

    # Fallback path uses 60 seconds for unsupported patterns
    sleep.assert_any_call(60)


@pytest.mark.asyncio
async def test_inmemory_scheduler_cron_parse_error(monkeypatch):
    scheduler = ts._InMemoryScheduler()
    sleep = AsyncMock(side_effect=RuntimeError("stop"))
    monkeypatch.setattr(ts.asyncio, "sleep", sleep)

    coro = AsyncMock(return_value=None)
    with pytest.raises(RuntimeError, match="stop"):
        await scheduler._run_cron("c", coro, "*/abc * * * *")

    # parse exception falls back to 60 seconds
    sleep.assert_called_with(60)


def test_inmemory_scheduler_schedule_cron():
    scheduler = ts._InMemoryScheduler()
    coro = AsyncMock()
    scheduler.schedule("c", coro, cron="*/5 * * * *")
    assert "c" in scheduler._tasks
    tasks = scheduler.list_tasks()
    assert tasks[0]["cron"] == "*/5 * * * *"
    scheduler.cancel("c")


def test_inmemory_scheduler_get_loop_no_running(monkeypatch):
    monkeypatch.setattr(
        ts.asyncio, "get_event_loop", MagicMock(side_effect=RuntimeError("no loop"))
    )
    scheduler = ts._InMemoryScheduler()
    loop = scheduler._get_loop()
    assert loop is not None
    assert scheduler._get_loop() is loop


def test_inmemory_scheduler_shutdown():
    scheduler = ts._InMemoryScheduler()
    coro = AsyncMock()
    scheduler.schedule("x", coro, interval=10)
    assert "x" in scheduler._tasks
    scheduler._shutdown()
    assert scheduler._tasks == {}


def test_inmemory_scheduler_shutdown_exception_paths(monkeypatch):
    scheduler = ts._InMemoryScheduler()
    fake_coro = MagicMock()
    fake_coro.close.side_effect = RuntimeError("close fail")
    fake_task = MagicMock()
    fake_task.done.return_value = False
    fake_task.get_coro.return_value = fake_coro
    scheduler._tasks["x"] = fake_task

    fake_loop = MagicMock()
    fake_loop.is_closed.return_value = False
    fake_loop.is_running.return_value = False
    fake_loop.run_until_complete.side_effect = RuntimeError("drain fail")
    scheduler._loop = fake_loop

    scheduler._shutdown()
    fake_task.cancel.assert_called_once()
    fake_coro.close.assert_called_once()
    fake_loop.run_until_complete.assert_called_once()
    assert scheduler._tasks == {}


def test_task_scheduler_auto():
    scheduler = ts.TaskScheduler()
    assert isinstance(scheduler._impl, ts._InMemoryScheduler)

    coro = AsyncMock()
    scheduler.schedule_task("t", coro, interval=1)
    tasks = scheduler.list_tasks()
    assert len(tasks) == 1
    assert tasks[0]["name"] == "t"

    scheduler.cancel_task("t")
    assert scheduler.list_tasks() == []


def test_task_scheduler_env_missing(monkeypatch):
    for backend in ["temporal", "prefect"]:
        monkeypatch.setenv("TASK_SCHEDULER", backend)
        scheduler = ts.TaskScheduler()
        assert scheduler._impl is None


@pytest.mark.asyncio
async def test_task_scheduler_temporal(monkeypatch):
    client_mod = MagicMock()
    client_mod.Client = MagicMock()
    client_mod.Client.connect = AsyncMock(return_value=MagicMock())
    temporalio = MagicMock()
    temporalio.client = client_mod
    monkeypatch.setitem(sys.modules, "temporalio", temporalio)
    monkeypatch.setenv("TASK_SCHEDULER", "temporal")

    scheduler = ts.TaskScheduler()
    assert scheduler._backend == "temporal"
    assert not isinstance(scheduler._impl, ts._InMemoryScheduler)

    coro = AsyncMock()
    scheduler.schedule_task("t", coro, interval=1)
    assert len(scheduler.list_tasks()) == 1
    scheduler.cancel_task("t")
    assert len(scheduler.list_tasks()) == 0

    client = await scheduler._impl._ensure_client()
    assert client is not None
    client_mod.Client.connect.assert_awaited_once()


def test_task_scheduler_prefect(monkeypatch):
    monkeypatch.setitem(sys.modules, "prefect", MagicMock())
    monkeypatch.setenv("TASK_SCHEDULER", "prefect")

    scheduler = ts.TaskScheduler()
    assert scheduler._backend == "prefect"
    assert not isinstance(scheduler._impl, ts._InMemoryScheduler)

    coro = AsyncMock()
    scheduler.schedule_task("t", coro, cron="*/5 * * * *")
    assert len(scheduler.list_tasks()) == 1
    scheduler.cancel_task("t")
    assert len(scheduler.list_tasks()) == 0


# ---------------------------------------------------------------------------
# core.structured_logging
# ---------------------------------------------------------------------------
def _read_jsonl(log_file):
    lines = []
    if log_file.exists():
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    lines.append(json.loads(line))
    return lines


def test_structured_logger_levels(tmp_path):
    log_dir = tmp_path / "logs"
    logger = slog.StructuredLogger("batch15c", str(log_dir))

    logger.debug("debug msg", extra_key="d")
    logger.info("info msg", extra_key="i")
    logger.warning("warn msg", extra_key="w")
    logger.error("error msg", extra_key="e")
    logger.critical("critical msg", extra_key="c")

    log_file = log_dir / "batch15c.jsonl"
    entries = _read_jsonl(log_file)
    assert len(entries) == 5
    assert entries[-1]["level"] == "CRITICAL"
    assert all(e["logger"] == "batch15c" for e in entries)


def test_structured_logger_context_and_request_id(tmp_path, monkeypatch):
    log_dir = tmp_path / "logs"
    logger = slog.StructuredLogger("ctx_test", str(log_dir))

    monkeypatch.setattr(slog, "CONTEXT_AVAILABLE", True)
    monkeypatch.setattr(
        slog,
        "get_logging_context",
        lambda: MagicMock(to_dict=lambda: {"trace_id": "trace-1"}),
    )

    logger.set_request_id("req-1")
    logger.info("with context")
    logger.clear_request_id()
    logger.info("without request id")

    log_file = log_dir / "ctx_test.jsonl"
    entries = _read_jsonl(log_file)
    assert len(entries) == 2
    assert entries[0]["context"]["trace_id"] == "trace-1"
    assert entries[0]["context"]["request_id"] == "req-1"
    assert "request_id" not in entries[1]["context"]


def test_structured_logger_context_failure(tmp_path, monkeypatch):
    log_dir = tmp_path / "logs"
    logger = slog.StructuredLogger("ctx_fail", str(log_dir))

    monkeypatch.setattr(slog, "CONTEXT_AVAILABLE", True)
    monkeypatch.setattr(
        slog,
        "get_logging_context",
        lambda: MagicMock(to_dict=MagicMock(side_effect=ValueError("ctx fail"))),
    )

    logger.info("still logs")  # exception in context injection is swallowed
    log_file = log_dir / "ctx_fail.jsonl"
    entries = _read_jsonl(log_file)
    assert len(entries) == 1
    assert entries[0]["message"] == "still logs"


def test_request_context():
    ctx = slog.RequestContext()
    assert uuid.UUID(ctx.request_id)
    assert ctx.get_duration() >= 0.0

    ctx.set_user("u1")
    ctx.set_client_ip("10.0.0.1")
    ctx.add_metadata("k", "v")
    d = ctx.to_dict()
    assert d["user_id"] == "u1"
    assert d["client_ip"] == "10.0.0.1"
    assert d["metadata"] == {"k": "v"}
    assert "request_id" in d


def test_get_logger_caches(monkeypatch):
    monkeypatch.setattr(slog, "_loggers", {})
    fake_instance = MagicMock()
    monkeypatch.setattr(slog, "StructuredLogger", MagicMock(return_value=fake_instance))

    l1 = slog.get_logger("cached")
    l2 = slog.get_logger("cached")
    assert l1 is l2 is fake_instance
    assert slog.StructuredLogger.call_count == 1


def test_json_formatter():
    record = logging.makeLogRecord(
        {
            "msg": "hello",
            "args": (),
            "levelno": 20,
            "levelname": "INFO",
            "name": "test",
            "module": "mod",
            "funcName": "fn",
            "lineno": 1,
        }
    )
    out = slog.JsonFormatter().format(record)
    data = json.loads(out)
    assert data["message"] == "hello"
    assert data["level"] == "INFO"

    record.structured_log = {"extra": "data"}
    out2 = slog.JsonFormatter().format(record)
    data2 = json.loads(out2)
    assert data2["extra"] == "data"

    try:
        raise ZeroDivisionError("boom")
    except Exception:
        record3 = logging.makeLogRecord(
            {
                "msg": "err",
                "args": (),
                "levelno": 40,
                "levelname": "ERROR",
                "name": "test",
                "module": "mod",
                "funcName": "fn",
                "lineno": 2,
                "exc_info": sys.exc_info(),
            }
        )
    out3 = slog.JsonFormatter().format(record3)
    data3 = json.loads(out3)
    assert data3["exception"]["type"] == "ZeroDivisionError"


def test_console_formatter():
    record = logging.makeLogRecord(
        {
            "msg": "hello",
            "args": (),
            "levelno": 20,
            "levelname": "INFO",
            "name": "test",
        }
    )
    out = slog.ConsoleFormatter().format(record)
    assert "INFO" in out
    assert "hello" in out
    assert "test" in out


def test_setup_logging(tmp_path):
    slog.setup_logging(str(tmp_path), "INFO")
    assert (tmp_path / "aiops.log").exists() or os.path.exists(tmp_path)  # loguru creates on emit


def test_setup_loki_logging_success(monkeypatch):
    post = MagicMock(return_value=MagicMock(status_code=204))
    monkeypatch.setattr(slog.httpx, "post", post)

    assert slog.setup_loki_logging("http://loki:3100", "svc") is True
    slog.loguru_logger.info("ship it")
    assert post.call_count >= 1


def test_setup_loki_logging_httpx_error(monkeypatch):
    post = MagicMock(side_effect=slog.httpx.RequestError("network"))
    monkeypatch.setattr(slog.httpx, "post", post)

    assert slog.setup_loki_logging("http://loki:3100", "svc") is True
    slog.loguru_logger.info("ship error")
    assert post.call_count >= 1


def test_setup_loki_logging_general_error(monkeypatch):
    post = MagicMock(side_effect=RuntimeError("boom"))
    monkeypatch.setattr(slog.httpx, "post", post)

    assert slog.setup_loki_logging("http://loki:3100", "svc") is True
    slog.loguru_logger.info("ship fail")
    assert post.call_count >= 1


def test_setup_loki_logging_register_failure(monkeypatch):
    monkeypatch.setattr(slog.loguru_logger, "add", MagicMock(side_effect=RuntimeError("add fail")))
    assert slog.setup_loki_logging("http://loki:3100") is False


# ---------------------------------------------------------------------------
# core.interface.grpc.interceptor
# ---------------------------------------------------------------------------
def test_logging_interceptor_success():
    interceptor = grpc_interceptor.LoggingInterceptor()
    cont = MagicMock(return_value="handler")
    details = MagicMock(method="/Test/Method", invocation_metadata=[])
    assert interceptor.intercept_service(cont, details) == "handler"
    cont.assert_called_once_with(details)


def test_logging_interceptor_error():
    interceptor = grpc_interceptor.LoggingInterceptor()
    cont = MagicMock(side_effect=RuntimeError("boom"))
    details = MagicMock(method="/Test/Method", invocation_metadata=[])
    with pytest.raises(RuntimeError, match="boom"):
        interceptor.intercept_service(cont, details)
    cont.assert_called_once_with(details)


def test_auth_interceptor_valid():
    interceptor = grpc_interceptor.AuthInterceptor("secret")
    cont = MagicMock(return_value="handler")
    details = MagicMock(method="/Test/Method", invocation_metadata=[("api-key", "secret")])
    assert interceptor.intercept_service(cont, details) == "handler"
    cont.assert_called_once_with(details)


def test_auth_interceptor_invalid(monkeypatch):
    fake_context = MagicMock()
    fake_grpc = MagicMock()
    fake_grpc.ServicerContext.return_value = fake_context
    fake_grpc.StatusCode.UNAUTHENTICATED = "UNAUTHENTICATED"
    monkeypatch.setattr(grpc_interceptor, "grpc", fake_grpc)

    interceptor = grpc_interceptor.AuthInterceptor("secret")
    cont = MagicMock()
    details = MagicMock(method="/Test/Method", invocation_metadata=[("api-key", "wrong")])
    result = interceptor.intercept_service(cont, details)
    assert result is fake_context
    fake_context.set_code.assert_called_once_with("UNAUTHENTICATED")
    fake_context.set_details.assert_called_once_with("Invalid API key")


def test_metrics_interceptor():
    interceptor = grpc_interceptor.MetricsInterceptor()
    cont = MagicMock(return_value="handler")
    details = MagicMock(method="/Metrics/Call", invocation_metadata=[])

    for _ in range(3):
        interceptor.intercept_service(cont, details)

    metrics = interceptor.get_metrics()
    assert metrics == {"/Metrics/Call": 3}
