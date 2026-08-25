# -*- coding: utf-8 -*-
"""Real branch coverage tests for core.task_scheduler.

No mocks are used; every test instantiates real scheduler objects and drives
them with real in-memory data / real asyncio event loops.
"""

import asyncio  # noqa: F401  # Imported for test setup
import atexit
import os  # noqa: F401  # Imported for test setup
from contextlib import contextmanager
from datetime import datetime, timezone

import pytest  # noqa: F401  # Imported for test setup

from core.task_scheduler import TaskScheduler, _InMemoryScheduler


@contextmanager
def env_var(key: str, value: str):
    """Temporarily set an environment variable, restoring it on exit."""
    old = os.environ.get(key)
    os.environ[key] = value
    try:
        yield
    finally:
        if old is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = old


def test_in_memory_get_loop_creates_on_runtime_error():
    """_get_loop creates a new loop when no event loop is available."""
    try:
        old_loop = asyncio.get_event_loop()
    except RuntimeError:
        old_loop = None
    else:
        if old_loop is not None and old_loop.is_closed():
            old_loop = None

    s = _InMemoryScheduler()
    try:
        asyncio.set_event_loop(None)
        loop = s._get_loop()
        assert isinstance(loop, asyncio.AbstractEventLoop)
        assert s._loop is loop
        s._shutdown()
        atexit.unregister(s._shutdown)
        loop.close()
    finally:
        if old_loop is not None and not old_loop.is_closed():
            asyncio.set_event_loop(old_loop)
        else:
            asyncio.set_event_loop(None)


def test_in_memory_schedule_one_off_cancel_and_metadata():
    """Exercise one-off scheduling, duplicate guard, cancel and list_tasks."""

    async def body():
        s = _InMemoryScheduler()
        results = []

        async def job():
            await asyncio.sleep(0)
            results.append(1)

        s.schedule("one", job)
        await s._tasks["one"]
        assert results == [1]

        # list_tasks returns real metadata
        tasks = s.list_tasks()
        assert len(tasks) == 1
        assert tasks[0]["name"] == "one"
        assert tasks[0]["cron"] is None
        assert tasks[0]["interval"] is None
        assert "created_at" in tasks[0]

        # Cancel removes the entry
        s.cancel("one")
        assert s.list_tasks() == []

        # Cancelling an unknown name is a no-op
        s.cancel("missing")

        # Duplicate name raises
        s.schedule("dup", job)
        dup_task = s._tasks["dup"]
        with pytest.raises(ValueError):
            s.schedule("dup", job)

        # Cancel the pending duplicate task and consume its cancellation
        s.cancel("dup")
        with pytest.raises(asyncio.CancelledError):
            await dup_task

        s._shutdown()
        atexit.unregister(s._shutdown)

    asyncio.run(body())


def test_in_memory_interval_runs():
    """_run_interval successfully executes a periodic coroutine."""

    async def body():
        s = _InMemoryScheduler()
        counts = []

        async def job():
            counts.append(1)

        s.schedule("tick", job, interval=0.05)
        try:
            await asyncio.wait_for(s._tasks["tick"], timeout=0.3)
        except asyncio.TimeoutError:
            pass
        assert len(counts) >= 3
        s._shutdown()
        atexit.unregister(s._shutdown)

    asyncio.run(body())


def test_in_memory_interval_handles_exception():
    """_run_interval catches exceptions from the coroutine and keeps running."""

    async def body():
        s = _InMemoryScheduler()
        calls = []

        async def flaky():
            if len(calls) == 0:
                calls.append("fail")
                raise RuntimeError("boom")
            calls.append("ok")

        s.schedule("flaky", flaky, interval=0.05)
        try:
            await asyncio.wait_for(s._tasks["flaky"], timeout=0.3)
        except asyncio.TimeoutError:
            pass
        assert "ok" in calls
        s._shutdown()
        atexit.unregister(s._shutdown)

    asyncio.run(body())


async def _wait_for_second(target: int):
    """Busy-wait until the clock hits the requested UTC second."""
    while datetime.now(timezone.utc).second != target:
        await asyncio.sleep(0.05)


def test_in_memory_cron_star_executes_and_catches_coro_errors():
    """_run_cron with '*/N' executes the coroutine and catches coroutine exceptions."""

    async def body():
        s = _InMemoryScheduler()
        counts = []
        errors = []

        async def job():
            counts.append(1)

        async def boom():
            errors.append(1)
            raise RuntimeError("cron boom")

        await _wait_for_second(58)
        t1 = s._get_loop().create_task(s._run_cron("cron_ok", job, "*/1"))
        t2 = s._get_loop().create_task(s._run_cron("cron_boom", boom, "*/1"))
        await asyncio.gather(
            asyncio.wait_for(t1, timeout=2.2),
            asyncio.wait_for(t2, timeout=2.2),
            return_exceptions=True,
        )
        assert len(counts) >= 1
        assert len(errors) >= 1
        s._shutdown()
        atexit.unregister(s._shutdown)

    asyncio.run(body())


def test_in_memory_cron_parsing_branches():
    """_run_cron falls back to 60s for unsupported and malformed cron strings."""

    async def body():
        s = _InMemoryScheduler()

        async def job():
            pass

        # else branch: not '*/...'
        t1 = s._get_loop().create_task(s._run_cron("plain", job, "* * * * *"))
        try:
            await asyncio.wait_for(t1, timeout=0.1)
        except asyncio.TimeoutError:
            pass

        # except branch: '*/foo' cannot be parsed as int
        t2 = s._get_loop().create_task(s._run_cron("bad", job, "*/foo"))
        try:
            await asyncio.wait_for(t2, timeout=0.1)
        except asyncio.TimeoutError:
            pass

        s._shutdown()
        atexit.unregister(s._shutdown)

    asyncio.run(body())


def test_in_memory_shutdown_states():
    """_shutdown handles None, open/non-running and closed event loops."""
    s1 = _InMemoryScheduler()
    s1._shutdown()  # _loop is None
    atexit.unregister(s1._shutdown)

    s2 = _InMemoryScheduler()
    loop = s2._get_loop()
    asyncio.set_event_loop(loop)

    async def job():
        await asyncio.sleep(1000)

    pending = loop.create_task(
        s2._run_interval("long", job, 1000)
    )  # noqa: F841  # Variable for test verification
    s2._tasks["long"] = pending
    s2._shutdown()  # open, not running, pending task
    atexit.unregister(s2._shutdown)
    assert s2._tasks == {}
    pending.exception()  # consume the (expected) unretrieved exception
    loop.close()

    s3 = _InMemoryScheduler()
    loop3 = s3._get_loop()
    loop3.close()
    s3._shutdown()  # _loop closed
    atexit.unregister(s3._shutdown)
    asyncio.set_event_loop(None)


def test_task_scheduler_auto_uses_in_memory_backend():
    """TaskScheduler with TASK_SCHEDULER=auto falls back to _InMemoryScheduler."""

    async def body():
        with env_var("TASK_SCHEDULER", "auto"):
            ts = TaskScheduler()
            assert isinstance(ts._impl, _InMemoryScheduler)

            results = []

            async def job():
                results.append(1)

            ts.schedule_task("one", job)
            await asyncio.sleep(0)
            assert results == [1]

            assert ts.list_tasks()[0]["name"] == "one"

            ts.schedule_task("per", job, interval=60)
            ts.schedule_task("cr", job, cron="*/5")
            names = {t["name"] for t in ts.list_tasks()}
            assert {"one", "per", "cr"} == names

            ts.cancel_task("one")
            ts.cancel_task("per")
            ts.cancel_task("cr")
            assert ts.list_tasks() == []

            ts.cancel_task("missing")  # no-op

            ts._impl._shutdown()
            atexit.unregister(ts._impl._shutdown)

    asyncio.run(body())


def test_task_scheduler_temporal_missing():
    """Explicit temporal backend without the SDK leaves _impl as None."""
    with env_var("TASK_SCHEDULER", "temporal"):
        ts = TaskScheduler()
        assert ts._backend == "temporal"
        assert ts._impl is None
        with pytest.raises(AttributeError):
            ts.schedule_task("x", lambda: None)


def test_task_scheduler_prefect_missing():
    """Explicit prefect backend without the SDK leaves _impl as None."""
    with env_var("TASK_SCHEDULER", "prefect"):
        ts = TaskScheduler()
        assert ts._backend == "prefect"
        assert ts._impl is None
        with pytest.raises(AttributeError):
            ts.list_tasks()
