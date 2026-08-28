# -*- coding: utf-8 -*-
"""Test workflow migration to database."""

import pytest
from core.database import SessionLocal
from core.models import Workflow, WorkflowExecution
from extensions.addons.operations.workflow_service.repository import (
    DatabaseWorkflowRepository,
    get_repository,
)


class TestWorkflowMigration:
    """Test workflow migration to database."""

    def test_database_tables_exist(self):
        """Test that workflow tables exist in database."""
        db = SessionLocal()
        try:
            # Check Workflow table
            workflow_table = Workflow.__table__
            assert workflow_table is not None, "Workflow table should exist"
            
            # Check WorkflowExecution table
            execution_table = WorkflowExecution.__table__
            assert execution_table is not None, "WorkflowExecution table should exist"
            
            print("✓ Database tables exist")
        finally:
            db.close()

    def test_database_repository_uses_database(self):
        """Test that DatabaseWorkflowRepository uses database."""
        import asyncio
        
        repository = asyncio.run(get_repository(use_in_memory=False))
        
        assert isinstance(repository, DatabaseWorkflowRepository), \
            "Repository should be DatabaseWorkflowRepository"
        
        print("✓ Database repository is used by default")

    def test_repository_can_save_and_retrieve_task(self):
        """Test that repository can save and retrieve workflow task."""
        from extensions.addons.operations.workflow_service.schemas import (
            WorkflowTask,
            WorkflowStatus,
        )
        import asyncio
        
        # Clean up any existing test data
        db = SessionLocal()
        try:
            db.query(WorkflowExecution).filter(
                WorkflowExecution.id == "test-task-001"
            ).delete()
            db.commit()
        finally:
            db.close()
        
        repository = asyncio.run(get_repository(use_in_memory=False))
        
        # Create a test task
        task = WorkflowTask(
            task_id="test-task-001",
            workflow_id="test-workflow-001",
            status=WorkflowStatus.PENDING,
            params={"test": "data"},
        )
        
        # Save task
        task_id = asyncio.run(repository.save_task(task))
        assert task_id == "test-task-001", "Task ID should match"
        
        # Retrieve task
        retrieved_task = asyncio.run(repository.get_task(task_id))
        assert retrieved_task is not None, "Task should be retrievable"
        assert retrieved_task.task_id == task_id, "Task ID should match"
        assert retrieved_task.workflow_id == "test-workflow-001", "Workflow ID should match"
        
        # Clean up
        asyncio.run(repository.delete_task(task_id))
        
        print("✓ Repository can save and retrieve tasks")

    def test_repository_can_save_and_retrieve_definition(self):
        """Test that repository can save and retrieve workflow definition."""
        from extensions.addons.operations.workflow_service.schemas import (
            WorkflowDefinition,
            WorkflowNode,
        )
        import asyncio
        
        # Clean up any existing test data
        db = SessionLocal()
        try:
            db.query(Workflow).filter(
                Workflow.id == "test-workflow-002"
            ).delete()
            db.commit()
        finally:
            db.close()
        
        repository = asyncio.run(get_repository(use_in_memory=False))
        
        # Create a test definition
        definition = WorkflowDefinition(
            workflow_id="test-workflow-002",
            name="Test Workflow",
            description="A test workflow",
            nodes=[
                WorkflowNode(
                    node_id="node-1",
                    name="Test Node",
                    command="echo 'test'",
                )
            ],
        )
        
        # Save definition
        workflow_id = asyncio.run(repository.save_definition(definition))
        assert workflow_id == "test-workflow-002", "Workflow ID should match"
        
        # Retrieve definition
        retrieved_def = asyncio.run(repository.get_definition(workflow_id))
        assert retrieved_def is not None, "Definition should be retrievable"
        assert retrieved_def.workflow_id == workflow_id, "Workflow ID should match"
        assert retrieved_def.name == "Test Workflow", "Name should match"
        
        # Clean up (delete from database)
        db = SessionLocal()
        try:
            workflow = db.query(Workflow).filter(
                Workflow.id == workflow_id
            ).first()
            if workflow:
                db.delete(workflow)
                db.commit()
        finally:
            db.close()
        
        print("✓ Repository can save and retrieve definitions")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
