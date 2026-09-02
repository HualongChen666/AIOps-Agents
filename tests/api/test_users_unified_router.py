# -*- coding: utf-8 -*-
# tests/api/test_users_unified_router.py
# 统一用户路由器集成测试

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch

from api.users_unified_router import router
from core.authentication import UserInDB, create_access_token, get_password_hash


@pytest.fixture
def app():
    """创建测试应用"""
    from fastapi import FastAPI
    
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    """创建测试客户端"""
    return TestClient(app)


@pytest.mark.smoke
def test_list_users_unauthorized(client):
    """测试未授权访问用户列表"""
    response = client.get("/api/v1/users/")
    assert response.status_code == 401


@pytest.mark.smoke
def test_create_user_unauthorized(client):
    """测试未授权创建用户"""
    response = client.post(
        "/api/v1/users/",
        json={
            "username": "newuser",
            "password": "NewPassword123!",
            "email": "new@example.com",
        },
    )
    assert response.status_code == 401


@pytest.mark.smoke
def test_get_current_user_unauthorized(client):
    """测试未授权获取当前用户信息"""
    response = client.get("/api/v1/users/me")
    assert response.status_code == 401
