# -*- coding: utf-8 -*-
# core/workflow_repository.py
# Workflow Repository Layer - Database persistence for workflow definitions and executions
# 替换内存存储为数据库持久化，确保数据不丢失

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from core.database import SessionLocal
from core.models import Workflow, WorkflowExecution

logger = logging.getLogger(__name__)


class WorkflowRepository:
    """
    Workflow Repository - 数据库持久化层
    提供工作流定义和执行记录的CRUD操作
    """

    def __init__(self, db: Optional[Session] = None):
        """
        Initialize repository with optional database session
        
        Args:
            db: Optional database session. If None, creates a new session.
        """
        self._db = db
        self._owns_session = db is None

    def _get_db(self) -> Session:
        """Get database session, creating one if needed."""
        if self._db is not None:
            return self._db
        return SessionLocal()

    def _close_db(self, db: Session) -> None:
        """Close database session if we own it."""
        if self._owns_session and db is not None:
            db.close()

    def create_workflow_definition(
        self,
        wf_key: str,
        name: str,
        description: str,
        definition: Dict[str, Any],
        created_by: Optional[str] = None,
    ) -> Workflow:
        """
        Create a new workflow definition in database
        
        Args:
            wf_key: Unique workflow key
            name: Workflow name
            description: Workflow description
            definition: Workflow definition (JSON)
            created_by: Creator username
            
        Returns:
            Created Workflow model instance
            
        Raises:
            ValueError: If workflow with same key already exists
        """
        db = self._get_db()
        try:
            # Check if workflow already exists
            existing = db.query(Workflow).filter(Workflow.id == wf_key).first()
            if existing:
                raise ValueError(f"Workflow '{wf_key}' already exists")

            workflow = Workflow(
                id=wf_key,
                name=name,
                description=description,
                definition=definition,
                status="active",
                version=1,
                created_by=created_by,
            )
            db.add(workflow)
            db.commit()
            db.refresh(workflow)
            logger.info(f"Created workflow definition: {wf_key}")
            return workflow
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create workflow definition {wf_key}: {e}")
            raise
        finally:
            self._close_db(db)

    def get_workflow_definition(self, wf_key: str) -> Optional[Workflow]:
        """
        Get workflow definition by key
        
        Args:
            wf_key: Workflow key
            
        Returns:
            Workflow model instance or None
        """
        db = self._get_db()
        try:
            workflow = db.query(Workflow).filter(Workflow.id == wf_key).first()
            return workflow
        finally:
            self._close_db(db)

    def list_workflow_definitions(
        self, status: Optional[str] = None, limit: int = 1000
    ) -> List[Workflow]:
        """
        List all workflow definitions
        
        Args:
            status: Optional status filter (active, paused, archived)
            limit: Maximum number of results
            
        Returns:
            List of Workflow model instances
        """
        db = self._get_db()
        try:
            query = db.query(Workflow)
            if status:
                query = query.filter(Workflow.status == status)
            workflows = query.order_by(Workflow.created_at.desc()).limit(limit).all()
            return workflows
        finally:
            self._close_db(db)

    def update_workflow_definition(
        self,
        wf_key: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        definition: Optional[Dict[str, Any]] = None,
        status: Optional[str] = None,
    ) -> Optional[Workflow]:
        """
        Update workflow definition
        
        Args:
            wf_key: Workflow key
            name: New name (optional)
            description: New description (optional)
            definition: New definition (optional)
            status: New status (optional)
            
        Returns:
            Updated Workflow model instance or None
            
        Raises:
            ValueError: If workflow not found
        """
        db = self._get_db()
        try:
            workflow = db.query(Workflow).filter(Workflow.id == wf_key).first()
            if not workflow:
                raise ValueError(f"Workflow '{wf_key}' not found")

            if name is not None:
                workflow.name = name
            if description is not None:
                workflow.description = description
            if definition is not None:
                workflow.definition = definition
                workflow.version += 1  # Increment version on definition change
            elif name is not None or description is not None:
                # Only increment version if metadata changed
                workflow.version += 1
            if status is not None:
                workflow.status = status

            db.commit()
            db.refresh(workflow)
            logger.info(f"Updated workflow definition: {wf_key}")
            return workflow
        except ValueError:
            db.rollback()
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to update workflow definition {wf_key}: {e}")
            raise
        finally:
            self._close_db(db)

    def delete_workflow_definition(self, wf_key: str) -> bool:
        """
        Delete workflow definition
        
        Args:
            wf_key: Workflow key
            
        Returns:
            True if deleted, False if not found
            
        Raises:
            ValueError: If workflow not found
        """
        db = self._get_db()
        try:
            workflow = db.query(Workflow).filter(Workflow.id == wf_key).first()
            if not workflow:
                raise ValueError(f"Workflow '{wf_key}' not found")

            db.delete(workflow)
            db.commit()
            logger.info(f"Deleted workflow definition: {wf_key}")
            return True
        except ValueError:
            db.rollback()
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to delete workflow definition {wf_key}: {e}")
            raise
        finally:
            self._close_db(db)

    def create_workflow_execution(
        self,
        workflow_id: str,
        triggered_by: Optional[str] = None,
        trigger_source: Optional[str] = None,
        executor: Optional[str] = None,
    ) -> WorkflowExecution:
        """
        Create a new workflow execution record
        
        Args:
            workflow_id: Workflow key
            triggered_by: Trigger source (user, system, schedule)
            trigger_source: Specific trigger identifier
            executor: Executor username
            
        Returns:
            Created WorkflowExecution model instance
        """
        db = self._get_db()
        try:
            execution_id = f"exec-{uuid.uuid4().hex[:16]}"
            execution = WorkflowExecution(
                id=execution_id,
                workflow_id=workflow_id,
                status="running",
                triggered_by=triggered_by,
                trigger_source=trigger_source,
                executor=executor,
                started_at=datetime.utcnow(),
            )
            db.add(execution)
            db.commit()
            db.refresh(execution)
            logger.info(f"Created workflow execution: {execution_id} for workflow {workflow_id}")
            return execution
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create workflow execution: {e}")
            raise
        finally:
            self._close_db(db)

    def update_workflow_execution(
        self,
        execution_id: str,
        status: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
    ) -> Optional[WorkflowExecution]:
        """
        Update workflow execution status and result
        
        Args:
            execution_id: Execution ID
            status: New status (running, completed, failed, cancelled)
            result: Execution result (JSON)
            error_message: Error message if failed
            
        Returns:
            Updated WorkflowExecution model instance or None
        """
        db = self._get_db()
        try:
            execution = (
                db.query(WorkflowExecution)
                .filter(WorkflowExecution.id == execution_id)
                .first()
            )
            if not execution:
                return None

            if status is not None:
                execution.status = status
                if status in ["completed", "failed", "cancelled"]:
                    execution.completed_at = datetime.utcnow()
                    if execution.started_at:
                        duration = (execution.completed_at - execution.started_at).total_seconds()
                        execution.duration_sec = duration

            if result is not None:
                execution.result = result

            if error_message is not None:
                execution.error_message = error_message

            db.commit()
            db.refresh(execution)
            logger.debug(f"Updated workflow execution: {execution_id}")
            return execution
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to update workflow execution {execution_id}: {e}")
            raise
        finally:
            self._close_db(db)

    def get_workflow_execution(self, execution_id: str) -> Optional[WorkflowExecution]:
        """
        Get workflow execution by ID
        
        Args:
            execution_id: Execution ID
            
        Returns:
            WorkflowExecution model instance or None
        """
        db = self._get_db()
        try:
            execution = (
                db.query(WorkflowExecution)
                .filter(WorkflowExecution.id == execution_id)
                .first()
            )
            return execution
        finally:
            self._close_db(db)

    def list_workflow_executions(
        self, workflow_id: Optional[str] = None, status: Optional[str] = None, limit: int = 100
    ) -> List[WorkflowExecution]:
        """
        List workflow executions
        
        Args:
            workflow_id: Optional workflow ID filter
            status: Optional status filter
            limit: Maximum number of results
            
        Returns:
            List of WorkflowExecution model instances
        """
        db = self._get_db()
        try:
            query = db.query(WorkflowExecution)
            if workflow_id:
                query = query.filter(WorkflowExecution.workflow_id == workflow_id)
            if status:
                query = query.filter(WorkflowExecution.status == status)
            executions = query.order_by(WorkflowExecution.started_at.desc()).limit(limit).all()
            return executions
        finally:
            self._close_db(db)

    def migrate_from_memory(
        self, memory_definitions: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Migrate workflow definitions from memory to database
        Ensures zero data loss during migration
        
        Args:
            memory_definitions: Dictionary of workflow definitions from memory
            
        Returns:
            Migration statistics (total, migrated, skipped, failed)
        """
        stats = {"total": len(memory_definitions), "migrated": 0, "skipped": 0, "failed": 0}
        
        db = self._get_db()
        try:
            for wf_key, definition in memory_definitions.items():
                try:
                    # Check if already exists
                    existing = db.query(Workflow).filter(Workflow.id == wf_key).first()
                    if existing:
                        stats["skipped"] += 1
                        logger.info(f"Workflow {wf_key} already exists, skipping")
                        continue
                    
                    # Create from memory definition
                    workflow = Workflow(
                        id=wf_key,
                        name=definition.get("name", wf_key),
                        description=definition.get("description", ""),
                        definition=definition,
                        status="active",
                        version=1,
                        created_by="migration",
                    )
                    db.add(workflow)
                    stats["migrated"] += 1
                    logger.info(f"Migrated workflow definition: {wf_key}")
                except Exception as e:
                    stats["failed"] += 1
                    logger.error(f"Failed to migrate workflow {wf_key}: {e}")
            
            db.commit()
            logger.info(f"Migration completed: {stats}")
            return stats
        except Exception as e:
            db.rollback()
            logger.error(f"Migration failed: {e}")
            raise
        finally:
            self._close_db(db)


# Global repository instance for backward compatibility
_workflow_repository = WorkflowRepository()


def get_workflow_repository() -> WorkflowRepository:
    """Get global workflow repository instance."""
    return _workflow_repository
