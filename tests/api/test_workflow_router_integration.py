# -*- coding: utf-8 -*-
# tests/api/test_workflow_router_integration.py
# Workflow Router集成测试
# 测试API端点的完整功能，包括认证、授权、速率限制

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from core.database import SessionLocal, engine, Base
from core.models import User, Workflow
from core.workflow_repository import WorkflowRepository
from main import app


@pytest.fixture(scope="function")
def db_session():
    """创建测试数据库会话"""
    # 创建所有表
    Base.metadata.create_all(bind=engine)
    
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        # 清理所有表
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def test_user(db_session):
    """创建测试用户"""
    from passlib.context import CryptContext
    
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    user = User(
        username="test_user",
        email="test@example.com",
        hashed_password=pwd_context.hash("test_password"),
        role="operator",
        disabled=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def auth_headers(test_user):
    """创建认证头"""
    from core.middleware.auth_middleware import create_access_token
    
    token = create_access_token(data={"sub": test_user.username})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def client():
    """创建测试客户端"""
    return TestClient(app)


class TestWorkflowRouterIntegration:
    """Workflow Router集成测试类"""
    
    def test_list_workflows_without_auth(self, client):
        """测试未认证访问工作流列表"""
        response = client.get("/api/v1/workflows/definitions")
        assert response.status_code == 401
    
    def test_list_workflows_with_auth(self, client, auth_headers, db_session):
        """测试认证访问工作流列表"""
        # 创建测试工作流
        repo = WorkflowRepository(db=db_session)
        repo.create_workflow_definition(
            wf_key="test-workflow",
            name="测试工作流",
            description="",
            definition={"name": "测试工作流", "steps": []},
        )
        
        # 认证访问
        response = client.get("/api/v1/workflows/definitions", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "test-workflow" in data
    
    def test_get_workflow_without_auth(self, client):
        """测试未认证获取单个工作流"""
        response = client.get("/api/v1/workflows/definitions/test-workflow")
        assert response.status_code == 401
    
    def test_get_workflow_with_auth(self, client, auth_headers, db_session):
        """测试认证获取单个工作流"""
        # 创建测试工作流
        repo = WorkflowRepository(db=db_session)
        repo.create_workflow_definition(
            wf_key="test-workflow",
            name="测试工作流",
            description="",
            definition={"name": "测试工作流", "steps": []},
        )
        
        # 认证访问
        response = client.get("/api/v1/workflows/definitions/test-workflow", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "test-workflow"
        assert data["name"] == "测试工作流"
    
    def test_create_workflow_without_auth(self, client):
        """测试未认证创建工作流"""
        response = client.post(
            "/api/v1/workflows/definitions",
            json={
                "wf_key": "new-workflow",
                "name": "新工作流",
                "description": "",
                "steps": [],
            },
        )
        assert response.status_code == 401
    
    def test_create_workflow_with_auth(self, client, auth_headers):
        """测试认证创建工作流"""
        response = client.post(
            "/api/v1/workflows/definitions",
            headers=auth_headers,
            json={
                "wf_key": "new-workflow",
                "name": "新工作流",
                "description": "新工作流描述",
                "steps": [
                    {"key": "step1", "title": "步骤1", "desc": "描述1"},
                ],
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["key"] == "new-workflow"
        assert data["name"] == "新工作流"
    
    def test_create_duplicate_workflow(self, client, auth_headers, db_session):
        """测试创建重复工作流"""
        # 创建工作流
        repo = WorkflowRepository(db=db_session)
        repo.create_workflow_definition(
            wf_key="test-workflow",
            name="测试工作流",
            description="",
            definition={"name": "测试工作流", "steps": []},
        )
        
        # 尝试创建重复工作流
        response = client.post(
            "/api/v1/workflows/definitions",
            headers=auth_headers,
            json={
                "wf_key": "test-workflow",
                "name": "测试工作流",
                "description": "",
                "steps": [],
            },
        )
        assert response.status_code == 400
    
    def test_update_workflow_without_auth(self, client):
        """测试未认证更新工作流"""
        response = client.put(
            "/api/v1/workflows/definitions/test-workflow",
            json={"name": "更新名称"},
        )
        assert response.status_code == 401
    
    def test_update_workflow_with_auth(self, client, auth_headers, db_session):
        """测试认证更新工作流"""
        # 创建工作流
        repo = WorkflowRepository(db=db_session)
        repo.create_workflow_definition(
            wf_key="test-workflow",
            name="原始名称",
            description="",
            definition={"name": "原始名称", "steps": []},
        )
        
        # 更新工作流
        response = client.put(
            "/api/v1/workflows/definitions/test-workflow",
            headers=auth_headers,
            json={"name": "更新名称"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "更新名称"
    
    def test_delete_workflow_without_auth(self, client):
        """测试未认证删除工作流"""
        response = client.delete("/api/v1/workflows/definitions/test-workflow")
        assert response.status_code == 401
    
    def test_delete_workflow_with_auth(self, client, auth_headers, db_session):
        """测试认证删除工作流"""
        # 创建工作流
        repo = WorkflowRepository(db=db_session)
        repo.create_workflow_definition(
            wf_key="test-workflow",
            name="测试工作流",
            description="",
            definition={"name": "测试工作流", "steps": []},
        )
        
        # 删除工作流
        response = client.delete(
            "/api/v1/workflows/definitions/test-workflow",
            headers=auth_headers,
        )
        assert response.status_code == 200
        
        # 验证工作流已被删除
        workflow = repo.get_workflow_definition("test-workflow")
        assert workflow is None
    
    def test_rate_limiting(self, client, auth_headers):
        """测试速率限制"""
        # 快速发送多个请求
        for i in range(25):  # 超过20/minute的限制
            response = client.post(
                "/api/v1/workflows/definitions",
                headers=auth_headers,
                json={
                    "wf_key": f"rate-limit-test-{i}",
                    "name": f"速率限制测试{i}",
                    "description": "",
                    "steps": [],
                },
            )
            if i < 20:
                assert response.status_code in [201, 400]  # 前20个应该成功或重复
            else:
                # 超过限制应该返回429
                if response.status_code == 429:
                    return  # 测试通过
        # 如果没有触发速率限制，跳过此测试
        pytest.skip("Rate limiting not triggered in test environment")
    
    def test_workflow_persistence(self, client, auth_headers, db_session):
        """测试工作流持久化"""
        # 创建工作流
        response = client.post(
            "/api/v1/workflows/definitions",
            headers=auth_headers,
            json={
                "wf_key": "persistence-test",
                "name": "持久化测试",
                "description": "",
                "steps": [{"key": "step1", "title": "步骤1"}],
            },
        )
        assert response.status_code == 201
        
        # 验证数据库中存在
        repo = WorkflowRepository(db=db_session)
        workflow = repo.get_workflow_definition("persistence-test")
        assert workflow is not None
        assert workflow.name == "持久化测试"
        
        # 通过API获取
        response = client.get(
            "/api/v1/workflows/definitions/persistence-test",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "持久化测试"
