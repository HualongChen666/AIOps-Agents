# -*- coding: utf-8 -*-
"""Tests for workflow_service repository module."""

from datetime import datetime

import pytest
from repository import (
    InMemoryWorkflowRepository,
    WorkflowRepository,
    get_repository,
)
from schemas import (
    ScheduledTask,
    TaskPriority,
    WorkflowDefinition,
    WorkflowNode,
    WorkflowRequest,
    WorkflowStatus,
    WorkflowTask,
    WorkflowVersion,
)


class TestInMemoryWorkflowRepository:
    """Test cases for InMemoryWorkflowRepository."""

    @pytest.mark.asyncio
    async def test_repository_initialization(self):
        """Test that repository initializes with empty storage."""
        repo = InMemoryWorkflowRepository()
        assert len(repo._tasks) == 0
        assert len(repo._definitions) == 0
        assert len(repo._versions) == 0
        assert len(repo._schedules) == 0

    @pytest.mark.asyncio
    async def test_save_task(self, workflow_task):
        """Test saving a workflow task."""
        repo = InMemoryWorkflowRepository()
        task_id = await repo.save_task(workflow_task)
        assert task_id == workflow_task.task_id
        assert workflow_task.task_id in repo._tasks

    @pytest.mark.asyncio
    async def test_save_task_updates_timestamp(self, workflow_task):
        """Test that saving a task updates the timestamp."""
        repo = InMemoryWorkflowRepository()
        original_time = workflow_task.updated_at
        await repo.save_task(workflow_task)
        assert repo._tasks[workflow_task.task_id].updated_at >= original_time

    @pytest.mark.asyncio
    async def test_save_task_without_id(self):
        """Test saving a task without task_id raises ValueError."""
        repo = InMemoryWorkflowRepository()
        task = WorkflowTask(task_id="", workflow_id="test", status=WorkflowStatus.PENDING)
        with pytest.raises(ValueError, match="task_id is required"):
            await repo.save_task(task)

    @pytest.mark.asyncio
    async def test_get_task(self, workflow_task):
        """Test retrieving a workflow task."""
        repo = InMemoryWorkflowRepository()
        await repo.save_task(workflow_task)
        retrieved = await repo.get_task(workflow_task.task_id)
        assert retrieved is not None
        assert retrieved.task_id == workflow_task.task_id

    @pytest.mark.asyncio
    async def test_get_task_not_found(self):
        """Test retrieving a non-existent task returns None."""
        repo = InMemoryWorkflowRepository()
        retrieved = await repo.get_task("non-existent")
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_list_tasks_empty(self):
        """Test listing tasks when repository is empty."""
        repo = InMemoryWorkflowRepository()
        tasks = await repo.list_tasks()
        assert tasks == []

    @pytest.mark.asyncio
    async def test_list_tasks_with_data(self, workflow_task):
        """Test listing tasks with data in repository."""
        repo = InMemoryWorkflowRepository()
        await repo.save_task(workflow_task)
        tasks = await repo.list_tasks()
        assert len(tasks) == 1
        assert tasks[0].task_id == workflow_task.task_id

    @pytest.mark.asyncio
    async def test_list_tasks_with_limit(self):
        """Test listing tasks with limit parameter."""
        repo = InMemoryWorkflowRepository()
        for i in range(10):
            task = WorkflowTask(
                task_id=f"task-{i}",
                workflow_id="test",
                status=WorkflowStatus.PENDING,
            )
            await repo.save_task(task)

        tasks = await repo.list_tasks(limit=5)
        assert len(tasks) == 5

    @pytest.mark.asyncio
    async def test_list_tasks_sorted_by_updated_at(self):
        """Test that tasks are sorted by updated_at in descending order."""
        repo = InMemoryWorkflowRepository()
        task1 = WorkflowTask(
            task_id="task-1",
            workflow_id="test",
            status=WorkflowStatus.PENDING,
        )
        await repo.save_task(task1)

        import asyncio

        await asyncio.sleep(0.01)

        task2 = WorkflowTask(
            task_id="task-2",
            workflow_id="test",
            status=WorkflowStatus.PENDING,
        )
        await repo.save_task(task2)

        tasks = await repo.list_tasks()
        assert tasks[0].task_id == "task-2"  # Most recent first
        assert tasks[1].task_id == "task-1"

    @pytest.mark.asyncio
    async def test_update_task(self, workflow_task):
        """Test updating a workflow task."""
        repo = InMemoryWorkflowRepository()
        await repo.save_task(workflow_task)

        updated = await repo.update_task(workflow_task.task_id, {"status": WorkflowStatus.RUNNING})
        assert updated is True

        retrieved = await repo.get_task(workflow_task.task_id)
        assert retrieved.status == WorkflowStatus.RUNNING

    @pytest.mark.asyncio
    async def test_update_task_not_found(self):
        """Test updating a non-existent task returns False."""
        repo = InMemoryWorkflowRepository()
        updated = await repo.update_task("non-existent", {"status": "running"})
        assert updated is False

    @pytest.mark.asyncio
    async def test_update_task_multiple_fields(self, workflow_task):
        """Test updating multiple fields of a task."""
        repo = InMemoryWorkflowRepository()
        await repo.save_task(workflow_task)

        updated = await repo.update_task(
            workflow_task.task_id,
            {
                "status": WorkflowStatus.RUNNING,
                "current_node": "node-1",
                "retry_count": 5,
            },
        )
        assert updated is True

        retrieved = await repo.get_task(workflow_task.task_id)
        assert retrieved.status == WorkflowStatus.RUNNING
        assert retrieved.current_node == "node-1"
        assert retrieved.retry_count == 5

    @pytest.mark.asyncio
    async def test_delete_task(self, workflow_task):
        """Test deleting a workflow task."""
        repo = InMemoryWorkflowRepository()
        await repo.save_task(workflow_task)

        deleted = await repo.delete_task(workflow_task.task_id)
        assert deleted is True
        assert workflow_task.task_id not in repo._tasks

    @pytest.mark.asyncio
    async def test_delete_task_not_found(self):
        """Test deleting a non-existent task returns False."""
        repo = InMemoryWorkflowRepository()
        deleted = await repo.delete_task("non-existent")
        assert deleted is False

    @pytest.mark.asyncio
    async def test_save_definition(self, workflow_definition):
        """Test saving a workflow definition."""
        repo = InMemoryWorkflowRepository()
        definition_id = await repo.save_definition(workflow_definition)
        assert definition_id == workflow_definition.workflow_id
        assert workflow_definition.workflow_id in repo._definitions

    @pytest.mark.asyncio
    async def test_get_definition(self, workflow_definition):
        """Test retrieving a workflow definition."""
        repo = InMemoryWorkflowRepository()
        await repo.save_definition(workflow_definition)
        retrieved = await repo.get_definition(workflow_definition.workflow_id)
        assert retrieved is not None
        assert retrieved.workflow_id == workflow_definition.workflow_id

    @pytest.mark.asyncio
    async def test_get_definition_not_found(self):
        """Test retrieving a non-existent definition returns None."""
        repo = InMemoryWorkflowRepository()
        retrieved = await repo.get_definition("non-existent")
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_list_definitions_empty(self):
        """Test listing definitions when repository is empty."""
        repo = InMemoryWorkflowRepository()
        definitions = await repo.list_definitions()
        assert definitions == []

    @pytest.mark.asyncio
    async def test_list_definitions_with_data(self, workflow_definition):
        """Test listing definitions with data in repository."""
        repo = InMemoryWorkflowRepository()
        await repo.save_definition(workflow_definition)
        definitions = await repo.list_definitions()
        assert len(definitions) == 1
        assert definitions[0].workflow_id == workflow_definition.workflow_id

    @pytest.mark.asyncio
    async def test_list_definitions_with_limit(self):
        """Test listing definitions with limit parameter."""
        repo = InMemoryWorkflowRepository()
        for i in range(10):
            definition = WorkflowDefinition(
                workflow_id=f"workflow-{i}",
                name=f"Workflow {i}",
            )
            await repo.save_definition(definition)

        definitions = await repo.list_definitions(limit=5)
        assert len(definitions) == 5

    @pytest.mark.asyncio
    async def test_list_definitions_sorted_by_workflow_id(self):
        """Test that definitions are sorted by workflow_id."""
        repo = InMemoryWorkflowRepository()
        await repo.save_definition(WorkflowDefinition(workflow_id="workflow-c", name="C"))
        await repo.save_definition(WorkflowDefinition(workflow_id="workflow-a", name="A"))
        await repo.save_definition(WorkflowDefinition(workflow_id="workflow-b", name="B"))

        definitions = await repo.list_definitions()
        assert definitions[0].workflow_id == "workflow-a"
        assert definitions[1].workflow_id == "workflow-b"
        assert definitions[2].workflow_id == "workflow-c"

    @pytest.mark.asyncio
    async def test_save_version(self):
        """Test saving a workflow version."""
        repo = InMemoryWorkflowRepository()
        version = WorkflowVersion(
            version="v1.0.0",
            workflow_id="workflow-1",
            commit_hash="abc123",
            message="Initial version",
        )
        version_id = await repo.save_version("workflow-1", version)
        assert version_id == "v1.0.0"
        assert "workflow-1" in repo._versions
        assert len(repo._versions["workflow-1"]) == 1

    @pytest.mark.asyncio
    async def test_save_version_multiple(self):
        """Test saving multiple versions for a workflow."""
        repo = InMemoryWorkflowRepository()
        for i in range(5):
            version = WorkflowVersion(
                version=f"v{i}.0.0",
                workflow_id="workflow-1",
                commit_hash=f"hash{i}",
                message=f"Version {i}",
            )
            await repo.save_version("workflow-1", version)

        assert len(repo._versions["workflow-1"]) == 5

    @pytest.mark.asyncio
    async def test_list_versions_empty(self):
        """Test listing versions when none exist."""
        repo = InMemoryWorkflowRepository()
        versions = await repo.list_versions("workflow-1")
        assert versions == []

    @pytest.mark.asyncio
    async def test_list_versions_with_data(self):
        """Test listing versions with data."""
        repo = InMemoryWorkflowRepository()
        version = WorkflowVersion(
            version="v1.0.0",
            workflow_id="workflow-1",
            commit_hash="abc123",
            message="Test",
        )
        await repo.save_version("workflow-1", version)

        versions = await repo.list_versions("workflow-1")
        assert len(versions) == 1
        assert versions[0].version == "v1.0.0"

    @pytest.mark.asyncio
    async def test_list_versions_with_limit(self):
        """Test listing versions with limit parameter."""
        repo = InMemoryWorkflowRepository()
        for i in range(10):
            version = WorkflowVersion(
                version=f"v{i}.0.0",
                workflow_id="workflow-1",
                commit_hash=f"hash{i}",
                message=f"Version {i}",
            )
            await repo.save_version("workflow-1", version)

        versions = await repo.list_versions("workflow-1", limit=5)
        assert len(versions) == 5

    @pytest.mark.asyncio
    async def test_list_versions_returns_most_recent(self):
        """Test that list_versions returns the most recent versions."""
        repo = InMemoryWorkflowRepository()
        for i in range(10):
            version = WorkflowVersion(
                version=f"v{i}.0.0",
                workflow_id="workflow-1",
                commit_hash=f"hash{i}",
                message=f"Version {i}",
            )
            await repo.save_version("workflow-1", version)

        versions = await repo.list_versions("workflow-1", limit=3)
        assert versions[0].version == "v7.0.0"
        assert versions[1].version == "v8.0.0"
        assert versions[2].version == "v9.0.0"

    @pytest.mark.asyncio
    async def test_save_schedule(self):
        """Test saving a scheduled task."""
        repo = InMemoryWorkflowRepository()
        schedule = ScheduledTask(
            schedule_id="schedule-1",
            workflow_id="workflow-1",
            cron="0 * * * *",
        )
        schedule_id = await repo.save_schedule(schedule)
        assert schedule_id == "schedule-1"
        assert schedule_id in repo._schedules

    @pytest.mark.asyncio
    async def test_save_schedule_multiple(self):
        """Test saving multiple scheduled tasks."""
        repo = InMemoryWorkflowRepository()
        for i in range(5):
            schedule = ScheduledTask(
                schedule_id=f"schedule-{i}",
                workflow_id="workflow-1",
                cron="0 * * * *",
            )
            await repo.save_schedule(schedule)

        assert len(repo._schedules) == 5

    @pytest.mark.asyncio
    async def test_list_schedules_empty(self):
        """Test listing schedules when none exist."""
        repo = InMemoryWorkflowRepository()
        schedules = await repo.list_schedules()
        assert schedules == []

    @pytest.mark.asyncio
    async def test_list_schedules_with_data(self):
        """Test listing schedules with data."""
        repo = InMemoryWorkflowRepository()
        schedule = ScheduledTask(
            schedule_id="schedule-1",
            workflow_id="workflow-1",
            cron="0 * * * *",
        )
        await repo.save_schedule(schedule)

        schedules = await repo.list_schedules()
        assert len(schedules) == 1
        assert schedules[0].schedule_id == "schedule-1"

    @pytest.mark.asyncio
    async def test_list_schedules_with_limit(self):
        """Test listing schedules with limit parameter."""
        repo = InMemoryWorkflowRepository()
        for i in range(10):
            schedule = ScheduledTask(
                schedule_id=f"schedule-{i}",
                workflow_id="workflow-1",
                cron="0 * * * *",
            )
            await repo.save_schedule(schedule)

        schedules = await repo.list_schedules(limit=5)
        assert len(schedules) == 5

    @pytest.mark.asyncio
    async def test_repository_isolation(self):
        """Test that different repository instances are isolated."""
        repo1 = InMemoryWorkflowRepository()
        repo2 = InMemoryWorkflowRepository()

        task = WorkflowTask(
            task_id="task-1",
            workflow_id="test",
            status=WorkflowStatus.PENDING,
        )
        await repo1.save_task(task)

        assert "task-1" in repo1._tasks
        assert "task-1" not in repo2._tasks

    @pytest.mark.asyncio
    async def test_save_task_overwrites(self, workflow_task):
        """Test that saving a task with same ID overwrites the previous one."""
        repo = InMemoryWorkflowRepository()
        await repo.save_task(workflow_task)

        # Update the task and save again
        workflow_task.status = WorkflowStatus.RUNNING
        await repo.save_task(workflow_task)

        retrieved = await repo.get_task(workflow_task.task_id)
        assert retrieved.status == WorkflowStatus.RUNNING

    @pytest.mark.asyncio
    async def test_save_definition_overwrites(self, workflow_definition):
        """Test that saving a definition with same ID overwrites the previous one."""
        repo = InMemoryWorkflowRepository()
        await repo.save_definition(workflow_definition)

        # Update the definition and save again
        workflow_definition.name = "Updated Name"
        await repo.save_definition(workflow_definition)

        retrieved = await repo.get_definition(workflow_definition.workflow_id)
        assert retrieved.name == "Updated Name"

    @pytest.mark.asyncio
    async def test_update_task_preserves_unchanged_fields(self, workflow_task):
        """Test that update_task preserves fields not in the update dict."""
        repo = InMemoryWorkflowRepository()
        await repo.save_task(workflow_task)

        original_status = workflow_task.status
        original_params = workflow_task.params

        await repo.update_task(workflow_task.task_id, {"current_node": "node-1"})

        retrieved = await repo.get_task(workflow_task.task_id)
        assert retrieved.status == original_status
        assert retrieved.params == original_params
        assert retrieved.current_node == "node-1"

    @pytest.mark.asyncio
    async def test_list_tasks_limit_zero(self):
        """Test listing tasks with limit=0 returns empty list."""
        repo = InMemoryWorkflowRepository()
        task = WorkflowTask(
            task_id="task-1",
            workflow_id="test",
            status=WorkflowStatus.PENDING,
        )
        await repo.save_task(task)

        tasks = await repo.list_tasks(limit=0)
        assert tasks == []

    @pytest.mark.asyncio
    async def test_list_definitions_limit_zero(self):
        """Test listing definitions with limit=0 returns empty list."""
        repo = InMemoryWorkflowRepository()
        definition = WorkflowDefinition(workflow_id="workflow-1", name="Test")
        await repo.save_definition(definition)

        definitions = await repo.list_definitions(limit=0)
        assert definitions == []

    @pytest.mark.asyncio
    async def test_list_schedules_limit_zero(self):
        """Test listing schedules with limit=0 returns empty list."""
        repo = InMemoryWorkflowRepository()
        schedule = ScheduledTask(
            schedule_id="schedule-1",
            workflow_id="workflow-1",
            cron="0 * * * *",
        )
        await repo.save_schedule(schedule)

        schedules = await repo.list_schedules(limit=0)
        assert schedules == []

    @pytest.mark.asyncio
    async def test_large_limit_parameter(self):
        """Test that large limit parameter works correctly."""
        repo = InMemoryWorkflowRepository()
        for i in range(5):
            task = WorkflowTask(
                task_id=f"task-{i}",
                workflow_id="test",
                status=WorkflowStatus.PENDING,
            )
            await repo.save_task(task)

        tasks = await repo.list_tasks(limit=10000)
        assert len(tasks) == 5


class TestGetRepository:
    """Test cases for get_repository function."""

    @pytest.mark.asyncio
    async def test_get_repository_default(self):
        """Test get_repository with default parameters."""
        repo = await get_repository()
        assert isinstance(repo, InMemoryWorkflowRepository)

    @pytest.mark.asyncio
    async def test_get_repository_in_memory_true(self):
        """Test get_repository with use_in_memory=True."""
        repo = await get_repository(use_in_memory=True)
        assert isinstance(repo, InMemoryWorkflowRepository)

    @pytest.mark.asyncio
    async def test_get_repository_in_memory_false(self):
        """Test get_repository with use_in_memory=False (still returns in-memory for now)."""
        repo = await get_repository(use_in_memory=False)
        # Currently, the function always returns InMemoryWorkflowRepository
        assert isinstance(repo, InMemoryWorkflowRepository)

    @pytest.mark.asyncio
    async def test_get_repository_returns_new_instance(self):
        """Test that get_repository returns a new instance each time."""
        repo1 = await get_repository()
        repo2 = await get_repository()
        assert repo1 is not repo2


class TestWorkflowRepositoryAbstract:
    """Test cases for WorkflowRepository abstract class."""

    def test_workflow_repository_is_abstract(self):
        """Test that WorkflowRepository is an abstract class."""
        from abc import ABC

        assert issubclass(WorkflowRepository, ABC)

    def test_workflow_repository_has_abstract_methods(self):
        """Test that WorkflowRepository has required abstract methods."""
        abstract_methods = [
            "save_task",
            "get_task",
            "list_tasks",
            "update_task",
            "delete_task",
            "save_definition",
            "get_definition",
            "list_definitions",
        ]
        for method in abstract_methods:
            assert hasattr(WorkflowRepository, method)

    def test_cannot_instantiate_workflow_repository_directly(self):
        """Test that WorkflowRepository cannot be instantiated directly."""
        with pytest.raises(TypeError):
            WorkflowRepository()
