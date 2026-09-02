# -*- coding: utf-8 -*-
# tests/core/test_workflow_repository.py
# Workflow Repository单元测试
# 测试数据库持久化功能，确保零数据丢失

import pytest
from datetime import datetime
from sqlalchemy.orm import Session

from core.database import SessionLocal, engine, Base
from core.models import Workflow, WorkflowExecution
from core.workflow_repository import WorkflowRepository


@pytest.fixture(scope="function")
def db_session():
    """创建测试数据库会话"""
    # 使用内存数据库避免并行测试冲突
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    # 创建内存数据库引擎
    test_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=test_engine)
    
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
        test_engine.dispose()


@pytest.fixture(scope="function")
def repository(db_session):
    """创建Repository实例"""
    return WorkflowRepository(db=db_session)


class TestWorkflowRepository:
    """Workflow Repository测试类"""
    
    def test_create_workflow_definition(self, repository):
        """测试创建工作流定义"""
        # 准备测试数据
        wf_key = "test-workflow"
        name = "测试工作流"
        description = "这是一个测试工作流"
        definition = {
            "name": name,
            "description": description,
            "steps": [
                {"key": "step1", "title": "步骤1", "desc": "描述1"},
                {"key": "step2", "title": "步骤2", "desc": "描述2"},
            ],
            "time": "1.0s",
            "rate": "99.0%",
        }
        
        # 执行创建
        workflow = repository.create_workflow_definition(
            wf_key=wf_key,
            name=name,
            description=description,
            definition=definition,
            created_by="test_user",
        )
        
        # 验证结果
        assert workflow is not None
        assert workflow.id == wf_key
        assert workflow.name == name
        assert workflow.description == description
        assert workflow.status == "active"
        assert workflow.version == 1
        assert workflow.created_by == "test_user"
    
    def test_create_duplicate_workflow_definition(self, repository):
        """测试创建重复的工作流定义"""
        # 准备测试数据
        wf_key = "test-workflow"
        name = "测试工作流"
        definition = {"name": name, "steps": []}
        
        # 第一次创建
        repository.create_workflow_definition(
            wf_key=wf_key,
            name=name,
            description="",
            definition=definition,
        )
        
        # 第二次创建应该失败
        with pytest.raises(ValueError, match="already exists"):
            repository.create_workflow_definition(
                wf_key=wf_key,
                name=name,
                description="",
                definition=definition,
            )
    
    def test_get_workflow_definition(self, repository):
        """测试获取工作流定义"""
        # 准备测试数据
        wf_key = "test-workflow"
        name = "测试工作流"
        definition = {"name": name, "steps": []}
        
        # 创建工作流
        repository.create_workflow_definition(
            wf_key=wf_key,
            name=name,
            description="",
            definition=definition,
        )
        
        # 获取工作流
        workflow = repository.get_workflow_definition(wf_key)
        
        # 验证结果
        assert workflow is not None
        assert workflow.id == wf_key
        assert workflow.name == name
    
    def test_get_nonexistent_workflow_definition(self, repository):
        """测试获取不存在的工作流定义"""
        workflow = repository.get_workflow_definition("nonexistent")
        assert workflow is None
    
    def test_list_workflow_definitions(self, repository):
        """测试列出工作流定义"""
        # 创建多个工作流
        for i in range(3):
            repository.create_workflow_definition(
                wf_key=f"test-workflow-{i}",
                name=f"测试工作流{i}",
                description="",
                definition={"name": f"测试工作流{i}", "steps": []},
            )
        
        # 列出工作流
        workflows = repository.list_workflow_definitions()
        
        # 验证结果
        assert len(workflows) == 3
    
    def test_list_workflow_definitions_with_status_filter(self, repository):
        """测试按状态过滤工作流定义"""
        # 创建不同状态的工作流
        repository.create_workflow_definition(
            wf_key="active-workflow",
            name="活跃工作流",
            description="",
            definition={"name": "活跃工作流", "steps": []},
        )
        repository.create_workflow_definition(
            wf_key="paused-workflow",
            name="暂停工作流",
            description="",
            definition={"name": "暂停工作流", "steps": []},
        )
        
        # 更新一个工作流的状态
        repository.update_workflow_definition("paused-workflow", status="paused")
        
        # 列出活跃的工作流
        active_workflows = repository.list_workflow_definitions(status="active")
        
        # 验证结果
        assert len(active_workflows) == 1
        assert active_workflows[0].id == "active-workflow"
    
    def test_update_workflow_definition(self, repository):
        """测试更新工作流定义"""
        # 创建工作流
        wf_key = "test-workflow"
        repository.create_workflow_definition(
            wf_key=wf_key,
            name="原始名称",
            description="原始描述",
            definition={"name": "原始名称", "steps": []},
        )
        
        # 更新工作流
        updated_workflow = repository.update_workflow_definition(
            wf_key=wf_key,
            name="更新名称",
            description="更新描述",
        )
        
        # 验证结果
        assert updated_workflow is not None
        assert updated_workflow.name == "更新名称"
        assert updated_workflow.description == "更新描述"
        assert updated_workflow.version == 2  # 版本应该递增（metadata变更）
    
    def test_update_nonexistent_workflow_definition(self, repository):
        """测试更新不存在的工作流定义"""
        with pytest.raises(ValueError, match="not found"):
            repository.update_workflow_definition("nonexistent", name="新名称")
    
    def test_delete_workflow_definition(self, repository):
        """测试删除工作流定义"""
        # 创建工作流
        wf_key = "test-workflow"
        repository.create_workflow_definition(
            wf_key=wf_key,
            name="测试工作流",
            description="",
            definition={"name": "测试工作流", "steps": []},
        )
        
        # 删除工作流
        result = repository.delete_workflow_definition(wf_key)
        
        # 验证结果
        assert result is True
        
        # 验证工作流已被删除
        workflow = repository.get_workflow_definition(wf_key)
        assert workflow is None
    
    def test_delete_nonexistent_workflow_definition(self, repository):
        """测试删除不存在的工作流定义"""
        with pytest.raises(ValueError, match="not found"):
            repository.delete_workflow_definition("nonexistent")
    
    def test_create_workflow_execution(self, repository):
        """测试创建工作流执行记录"""
        # 创建工作流定义
        wf_key = "test-workflow"
        repository.create_workflow_definition(
            wf_key=wf_key,
            name="测试工作流",
            description="",
            definition={"name": "测试工作流", "steps": []},
        )
        
        # 创建执行记录
        execution = repository.create_workflow_execution(
            workflow_id=wf_key,
            triggered_by="user",
            trigger_source="manual",
            executor="test_user",
        )
        
        # 验证结果
        assert execution is not None
        assert execution.workflow_id == wf_key
        assert execution.status == "running"
        assert execution.triggered_by == "user"
        assert execution.executor == "test_user"
        assert execution.started_at is not None
    
    def test_update_workflow_execution(self, repository):
        """测试更新工作流执行记录"""
        # 创建工作流定义和执行记录
        wf_key = "test-workflow"
        repository.create_workflow_definition(
            wf_key=wf_key,
            name="测试工作流",
            description="",
            definition={"name": "测试工作流", "steps": []},
        )
        execution = repository.create_workflow_execution(workflow_id=wf_key)
        
        # 更新执行记录
        updated_execution = repository.update_workflow_execution(
            execution_id=execution.id,
            status="completed",
            result={"success": True},
        )
        
        # 验证结果
        assert updated_execution is not None
        assert updated_execution.status == "completed"
        assert updated_execution.result == {"success": True}
        assert updated_execution.completed_at is not None
        assert updated_execution.duration_sec is not None
    
    def test_get_workflow_execution(self, repository):
        """测试获取工作流执行记录"""
        # 创建工作流定义和执行记录
        wf_key = "test-workflow"
        repository.create_workflow_definition(
            wf_key=wf_key,
            name="测试工作流",
            description="",
            definition={"name": "测试工作流", "steps": []},
        )
        execution = repository.create_workflow_execution(workflow_id=wf_key)
        
        # 获取执行记录
        retrieved_execution = repository.get_workflow_execution(execution.id)
        
        # 验证结果
        assert retrieved_execution is not None
        assert retrieved_execution.id == execution.id
        assert retrieved_execution.workflow_id == wf_key
    
    def test_list_workflow_executions(self, repository):
        """测试列出工作流执行记录"""
        # 创建工作流定义
        wf_key = "test-workflow"
        repository.create_workflow_definition(
            wf_key=wf_key,
            name="测试工作流",
            description="",
            definition={"name": "测试工作流", "steps": []},
        )
        
        # 创建多个执行记录
        for _ in range(3):
            repository.create_workflow_execution(workflow_id=wf_key)
        
        # 列出执行记录
        executions = repository.list_workflow_executions(workflow_id=wf_key)
        
        # 验证结果
        assert len(executions) == 3
    
    def test_migrate_from_memory(self, repository):
        """测试从内存迁移工作流定义"""
        # 准备内存数据
        memory_definitions = {
            "workflow1": {
                "name": "工作流1",
                "description": "描述1",
                "steps": [{"key": "step1", "title": "步骤1"}],
            },
            "workflow2": {
                "name": "工作流2",
                "description": "描述2",
                "steps": [{"key": "step2", "title": "步骤2"}],
            },
        }
        
        # 执行迁移
        stats = repository.migrate_from_memory(memory_definitions)
        
        # 验证结果
        assert stats["total"] == 2
        assert stats["migrated"] == 2
        assert stats["skipped"] == 0
        assert stats["failed"] == 0
        
        # 验证数据库中的数据
        workflows = repository.list_workflow_definitions()
        assert len(workflows) == 2
        
        # 验证已存在的工作流不会被重复迁移
        stats2 = repository.migrate_from_memory(memory_definitions)
        assert stats2["skipped"] == 2
        assert stats2["migrated"] == 0
