# -*- coding: utf-8 -*-
"""Tests for workflow_service scheduler module."""

from datetime import datetime, timedelta

import pytest

from scheduler import WorkflowScheduler
from schemas import (
    ScheduledTask,
    WorkflowRequest,
    WorkflowStatus,
    WorkflowTask,
)


class TestWorkflowScheduler:
    """Test cases for WorkflowScheduler class."""

    def test_scheduler_initialization(self):
        """Test that scheduler initializes correctly."""
        scheduler = WorkflowScheduler()
        assert scheduler.poll_interval == 1.0
        assert len(scheduler._queue) == 0
        assert len(scheduler._schedules) == 0
        assert len(scheduler._handlers) == 0
        assert scheduler._running is False

    def test_scheduler_custom_poll_interval(self):
        """Test scheduler with custom poll interval."""
        scheduler = WorkflowScheduler(poll_interval=0.5)
        assert scheduler.poll_interval == 0.5

    def test_scheduler_zero_poll_interval(self):
        """Test scheduler with zero poll interval."""
        scheduler = WorkflowScheduler(poll_interval=0)
        assert scheduler.poll_interval == 0

    def test_scheduler_large_poll_interval(self):
        """Test scheduler with large poll interval."""
        scheduler = WorkflowScheduler(poll_interval=3600)
        assert scheduler.poll_interval == 3600

    def test_register_handler(self, scheduler):
        """Test registering a handler."""
        async def handler(request):
            return WorkflowTask(
                task_id="test", workflow_id="test", status=WorkflowStatus.PENDING
            )

        scheduler.register_handler(handler)
        assert len(scheduler._handlers) == 1

    def test_register_multiple_handlers(self, scheduler):
        """Test registering multiple handlers."""
        async def handler1(request):
            return WorkflowTask(
                task_id="test1", workflow_id="test", status=WorkflowStatus.PENDING
            )

        async def handler2(request):
            return WorkflowTask(
                task_id="test2", workflow_id="test", status=WorkflowStatus.PENDING
            )

        scheduler.register_handler(handler1)
        scheduler.register_handler(handler2)
        assert len(scheduler._handlers) == 2

    @pytest.mark.asyncio
    async def test_enqueue(self, scheduler, workflow_request):
        """Test enqueuing a workflow request."""
        queued_id = await scheduler.enqueue(workflow_request)
        assert queued_id is not None
        assert queued_id.startswith("SCHEDULED-")
        assert len(scheduler._queue) == 1

    @pytest.mark.asyncio
    async def test_enqueue_multiple(self, scheduler, workflow_request):
        """Test enqueuing multiple workflow requests."""
        queued_id1 = await scheduler.enqueue(workflow_request)
        queued_id2 = await scheduler.enqueue(workflow_request)

        assert queued_id1 != queued_id2
        assert len(scheduler._queue) == 2

    @pytest.mark.asyncio
    async def test_enqueue_generates_unique_ids(self, scheduler, workflow_request):
        """Test that enqueue generates unique IDs."""
        ids = []
        for _ in range(10):
            queued_id = await scheduler.enqueue(workflow_request)
            ids.append(queued_id)

        assert len(set(ids)) == 10  # All IDs should be unique

    @pytest.mark.asyncio
    async def test_schedule(self, scheduler, scheduled_task):
        """Test scheduling a task."""
        schedule_id = await scheduler.schedule(scheduled_task)
        assert schedule_id == scheduled_task.schedule_id
        assert schedule_id in scheduler._schedules
        assert len(scheduler._schedules) == 1

    @pytest.mark.asyncio
    async def test_schedule_sets_next_run(self, scheduler, scheduled_task):
        """Test that schedule sets next_run time."""
        original_next_run = scheduled_task.next_run
        await scheduler.schedule(scheduled_task)

        # next_run should be set to approximately now + 1 second
        assert scheduler._schedules[scheduled_task.schedule_id].next_run is not None
        assert scheduler._schedules[scheduled_task.schedule_id].next_run > datetime.utcnow()

    @pytest.mark.asyncio
    async def test_schedule_multiple(self, scheduler):
        """Test scheduling multiple tasks."""
        for i in range(5):
            task = ScheduledTask(
                schedule_id=f"schedule-{i}",
                workflow_id="workflow-1",
                cron="0 * * * *",
            )
            await scheduler.schedule(task)

        assert len(scheduler._schedules) == 5

    @pytest.mark.asyncio
    async def test_schedule_overwrites_existing(self, scheduler, scheduled_task):
        """Test that scheduling with same ID overwrites existing."""
        await scheduler.schedule(scheduled_task)

        # Update the task and schedule again
        scheduled_task.enabled = False
        await scheduler.schedule(scheduled_task)

        assert scheduler._schedules[scheduled_task.schedule_id].enabled is False

    @pytest.mark.asyncio
    async def test_run_once_empty(self, scheduler):
        """Test run_once when no tasks are scheduled or queued."""
        results = await scheduler.run_once()
        assert results == []

    @pytest.mark.asyncio
    async def test_run_once_with_queue(self, scheduler, workflow_request):
        """Test run_once with queued requests."""
        async def handler(request):
            return WorkflowTask(
                task_id="test", workflow_id=request.workflow_id, status=WorkflowStatus.PENDING
            )

        scheduler.register_handler(handler)
        await scheduler.enqueue(workflow_request)

        results = await scheduler.run_once()

        assert len(results) == 1
        assert len(scheduler._queue) == 0  # Queue should be emptied

    @pytest.mark.asyncio
    async def test_run_once_with_schedule_due(self, scheduler, scheduled_task):
        """Test run_once with due scheduled tasks."""
        async def handler(request):
            return WorkflowTask(
                task_id="test", workflow_id=request.workflow_id, status=WorkflowStatus.PENDING
            )

        scheduler.register_handler(handler)
        # Set next_run to past to make it due
        scheduled_task.next_run = datetime.utcnow() - timedelta(seconds=10)
        await scheduler.schedule(scheduled_task)

        results = await scheduler.run_once()

        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_run_once_with_schedule_not_due(self, scheduler, scheduled_task):
        """Test run_once with scheduled tasks that are not due."""
        async def handler(request):
            return WorkflowTask(
                task_id="test", workflow_id=request.workflow_id, status=WorkflowStatus.PENDING
            )

        scheduler.register_handler(handler)
        # Set next_run to future
        scheduled_task.next_run = datetime.utcnow() + timedelta(seconds=10)
        await scheduler.schedule(scheduled_task)

        results = await scheduler.run_once()

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_run_once_with_disabled_schedule(self, scheduler, scheduled_task):
        """Test run_once with disabled scheduled tasks."""
        async def handler(request):
            return WorkflowTask(
                task_id="test", workflow_id=request.workflow_id, status=WorkflowStatus.PENDING
            )

        scheduler.register_handler(handler)
        scheduled_task.enabled = False
        scheduled_task.next_run = datetime.utcnow() - timedelta(seconds=10)
        await scheduler.schedule(scheduled_task)

        results = await scheduler.run_once()

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_run_once_updates_next_run(self, scheduler, scheduled_task):
        """Test that run_once updates next_run for scheduled tasks."""
        async def handler(request):
            return WorkflowTask(
                task_id="test", workflow_id=request.workflow_id, status=WorkflowStatus.PENDING
            )

        scheduler.register_handler(handler)
        scheduled_task.next_run = datetime.utcnow() - timedelta(seconds=10)
        await scheduler.schedule(scheduled_task)

        await scheduler.run_once()

        # next_run should be updated to future
        assert scheduler._schedules[scheduled_task.schedule_id].next_run > datetime.utcnow()

    @pytest.mark.asyncio
    async def test_run_once_with_multiple_handlers(self, scheduler, workflow_request):
        """Test run_once with multiple registered handlers."""
        call_count = 0

        async def handler1(request):
            nonlocal call_count
            call_count += 1
            return WorkflowTask(
                task_id=f"test{call_count}",
                workflow_id=request.workflow_id,
                status=WorkflowStatus.PENDING,
            )

        async def handler2(request):
            nonlocal call_count
            call_count += 1
            return WorkflowTask(
                task_id=f"test{call_count}",
                workflow_id=request.workflow_id,
                status=WorkflowStatus.PENDING,
            )

        scheduler.register_handler(handler1)
        scheduler.register_handler(handler2)
        await scheduler.enqueue(workflow_request)

        results = await scheduler.run_once()

        # Both handlers should be called
        assert call_count == 2
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_run_once_handler_error(self, scheduler, workflow_request):
        """Test run_once when handler raises an error."""
        async def failing_handler(request):
            raise ValueError("Handler failed")

        scheduler.register_handler(failing_handler)
        await scheduler.enqueue(workflow_request)

        # Should not raise, just log error
        results = await scheduler.run_once()

        assert len(results) == 0
        assert len(scheduler._queue) == 0  # Queue should still be emptied

    @pytest.mark.asyncio
    async def test_run_once_with_queue_and_schedule(self, scheduler, workflow_request, scheduled_task):
        """Test run_once with both queued and scheduled tasks."""
        async def handler(request):
            return WorkflowTask(
                task_id="test", workflow_id=request.workflow_id, status=WorkflowStatus.PENDING
            )

        scheduler.register_handler(handler)
        await scheduler.enqueue(workflow_request)
        scheduled_task.next_run = datetime.utcnow() - timedelta(seconds=10)
        await scheduler.schedule(scheduled_task)

        results = await scheduler.run_once()

        # Should process both queue and schedule
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_start_and_stop(self, scheduler):
        """Test start and stop methods."""
        async def handler(request):
            return WorkflowTask(
                task_id="test", workflow_id="test", status=WorkflowStatus.PENDING
            )

        scheduler.register_handler(handler)

        # Start should set running to True
        start_task = asyncio.create_task(scheduler.start())
        await asyncio.sleep(0.1)  # Give it time to start
        assert scheduler._running is True

        # Stop should set running to False
        scheduler.stop()
        await asyncio.sleep(0.1)  # Give it time to stop
        assert scheduler._running is False

        # Clean up the task
        start_task.cancel()
        try:
            await start_task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_start_processes_queue(self, scheduler, workflow_request):
        """Test that start processes queued items."""
        processed = False

        async def handler(request):
            nonlocal processed
            processed = True
            return WorkflowTask(
                task_id="test", workflow_id=request.workflow_id, status=WorkflowStatus.PENDING
            )

        scheduler.register_handler(handler)
        await scheduler.enqueue(workflow_request)

        # Start briefly
        start_task = asyncio.create_task(scheduler.start())
        await asyncio.sleep(0.2)  # Give it time to process
        scheduler.stop()
        await asyncio.sleep(0.1)

        assert processed is True

        # Clean up
        start_task.cancel()
        try:
            await start_task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_stop_when_not_running(self, scheduler):
        """Test stop when scheduler is not running."""
        # Should not raise an error
        scheduler.stop()
        assert scheduler._running is False

    @pytest.mark.asyncio
    async def test_enqueue_with_different_workflow_ids(self, scheduler):
        """Test enqueuing requests with different workflow IDs."""
        await scheduler.enqueue(WorkflowRequest(workflow_id="workflow-1"))
        await scheduler.enqueue(WorkflowRequest(workflow_id="workflow-2"))
        await scheduler.enqueue(WorkflowRequest(workflow_id="workflow-3"))

        assert len(scheduler._queue) == 3

    @pytest.mark.asyncio
    async def test_schedule_with_different_cron_expressions(self, scheduler):
        """Test scheduling tasks with different cron expressions."""
        cron_expressions = ["0 * * * *", "*/5 * * * *", "0 0 * * *"]
        for i, cron in enumerate(cron_expressions):
            task = ScheduledTask(
                schedule_id=f"schedule-{i}",
                workflow_id="workflow-1",
                cron=cron,
            )
            await scheduler.schedule(task)

        assert len(scheduler._schedules) == 3

    @pytest.mark.asyncio
    async def test_run_once_fifo_queue_order(self, scheduler):
        """Test that queue is processed in FIFO order."""
        execution_order = []

        async def handler(request):
            execution_order.append(request.workflow_id)
            return WorkflowTask(
                task_id="test", workflow_id=request.workflow_id, status=WorkflowStatus.PENDING
            )

        scheduler.register_handler(handler)
        await scheduler.enqueue(WorkflowRequest(workflow_id="first"))
        await scheduler.enqueue(WorkflowRequest(workflow_id="second"))
        await scheduler.enqueue(WorkflowRequest(workflow_id="third"))

        await scheduler.run_once()

        assert execution_order == ["first", "second", "third"]

    @pytest.mark.asyncio
    async def test_run_once_with_params(self, scheduler):
        """Test run_once with request parameters."""
        received_params = None

        async def handler(request):
            nonlocal received_params
            received_params = request.params
            return WorkflowTask(
                task_id="test", workflow_id=request.workflow_id, status=WorkflowStatus.PENDING
            )

        scheduler.register_handler(handler)
        request = WorkflowRequest(
            workflow_id="test", params={"key": "value", "number": 42}
        )
        await scheduler.enqueue(request)

        await scheduler.run_once()

        assert received_params == {"key": "value", "number": 42}

    @pytest.mark.asyncio
    async def test_schedule_with_params(self, scheduler):
        """Test scheduling with task parameters."""
        received_params = None

        async def handler(request):
            nonlocal received_params
            received_params = request.params
            return WorkflowTask(
                task_id="test", workflow_id=request.workflow_id, status=WorkflowStatus.PENDING
            )

        scheduler.register_handler(handler)
        task = ScheduledTask(
            schedule_id="schedule-1",
            workflow_id="workflow-1",
            cron="0 * * * *",
            params={"scheduled": True, "count": 5},
        )
        task.next_run = datetime.utcnow() - timedelta(seconds=10)
        await scheduler.schedule(task)

        await scheduler.run_once()

        assert received_params == {"scheduled": True, "count": 5}

    @pytest.mark.asyncio
    async def test_run_once_empty_queue_with_schedule(self, scheduler, scheduled_task):
        """Test run_once with empty queue but due scheduled tasks."""
        async def handler(request):
            return WorkflowTask(
                task_id="test", workflow_id=request.workflow_id, status=WorkflowStatus.PENDING
            )

        scheduler.register_handler(handler)
        scheduled_task.next_run = datetime.utcnow() - timedelta(seconds=10)
        await scheduler.schedule(scheduled_task)

        results = await scheduler.run_once()

        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_run_once_with_no_handlers(self, scheduler, workflow_request):
        """Test run_once when no handlers are registered."""
        await scheduler.enqueue(workflow_request)

        results = await scheduler.run_once()

        # Should not raise, just process nothing
        assert len(results) == 0
        assert len(scheduler._queue) == 0

    @pytest.mark.asyncio
    async def test_schedule_preserves_task_attributes(self, scheduler):
        """Test that schedule preserves task attributes."""
        task = ScheduledTask(
            schedule_id="schedule-1",
            workflow_id="workflow-1",
            cron="0 * * * *",
            enabled=True,
            params={"key": "value"},
        )
        await scheduler.schedule(task)

        stored = scheduler._schedules[task.schedule_id]
        assert stored.workflow_id == task.workflow_id
        assert stored.cron == task.cron
        assert stored.enabled == task.enabled
        assert stored.params == task.params

    @pytest.mark.asyncio
    async def test_enqueue_preserves_request_attributes(self, scheduler):
        """Test that enqueue preserves request attributes."""
        request = WorkflowRequest(
            workflow_id="workflow-1",
            params={"key": "value"},
            requested_by="user-123",
        )
        await scheduler.enqueue(request)

        # The request should be in the queue
        queued_request = scheduler._queue[0]
        assert queued_request.workflow_id == request.workflow_id
        assert queued_request.params == request.params
        assert queued_request.requested_by == request.requested_by

    @pytest.mark.asyncio
    async def test_run_once_concurrent_schedules(self, scheduler):
        """Test run_once with multiple due scheduled tasks."""
        async def handler(request):
            return WorkflowTask(
                task_id="test", workflow_id=request.workflow_id, status=WorkflowStatus.PENDING
            )

        scheduler.register_handler(handler)

        # Create multiple due schedules
        for i in range(5):
            task = ScheduledTask(
                schedule_id=f"schedule-{i}",
                workflow_id="workflow-1",
                cron="0 * * * *",
            )
            task.next_run = datetime.utcnow() - timedelta(seconds=10)
            await scheduler.schedule(task)

        results = await scheduler.run_once()

        # All due schedules should be processed
        assert len(results) == 5

    @pytest.mark.asyncio
    async def test_scheduler_isolation(self):
        """Test that different scheduler instances are isolated."""
        scheduler1 = WorkflowScheduler()
        scheduler2 = WorkflowScheduler()

        await scheduler1.enqueue(WorkflowRequest(workflow_id="test"))

        assert len(scheduler1._queue) == 1
        assert len(scheduler2._queue) == 0
