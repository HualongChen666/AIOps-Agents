# -*- coding: utf-8 -*-
"""
ITSM Router Tests
ITSM工单管理路由API基础测试
"""

import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

# Mock problematic imports before importing router
sys.modules["core.itsm_engine"] = MagicMock()

from api.itsm_router import create_incident, resolve_incident


@pytest.fixture
def client():
    """创建测试客户端"""
    app = FastAPI()
    # Create a new router without authentication dependencies
    test_router = APIRouter(prefix="/api/itsm", tags=["ITSM"])
    test_router.add_api_route("/incident", create_incident, methods=["POST"])
    test_router.add_api_route("/incident/{incident_id}", resolve_incident, methods=["PATCH"])
    app.include_router(test_router)
    return TestClient(app)


class TestITSMRouter:
    """测试ITSM工单管理路由"""

    def test_create_incident_success(self, client):
        """测试成功创建ITSM工单"""
        with patch("api.itsm_router.SERVICE_NOW_URL", "https://test.service-now.com"):
            with patch("api.itsm_router.SERVICE_NOW_TOKEN", "test_token"):
                response = client.post(
                    "/api/itsm/incident?provider=servicenow", json={"title": "Test"}
                )
                assert response.status_code == 200
                data = response.json()
                assert "status" in data

    def test_create_incident_no_config(self, client):
        """测试配置未完成"""
        with patch("api.itsm_router.SERVICE_NOW_URL", None):
            with patch("api.itsm_router.SERVICE_NOW_TOKEN", None):
                response = client.post(
                    "/api/itsm/incident?provider=servicenow", json={"title": "Test"}
                )
                assert response.status_code == 500

    def test_create_incident_unsupported_provider(self, client):
        """测试不支持的ITSM提供商"""
        response = client.post("/api/itsm/incident?provider=unsupported", json={"title": "Test"})
        assert response.status_code == 400

    def test_create_incident_jira_success(self, client):
        """测试成功创建Jira工单"""
        with patch("api.itsm_router.JIRA_URL", "https://test.jira.com"):
            with patch("api.itsm_router.JIRA_TOKEN", "test_token"):
                response = client.post("/api/itsm/incident?provider=jira", json={"title": "Test"})
                assert response.status_code == 200
                data = response.json()
                assert "status" in data

    def test_create_incident_jira_no_config(self, client):
        """测试Jira配置未完成"""
        with patch("api.itsm_router.JIRA_URL", None):
            with patch("api.itsm_router.JIRA_TOKEN", None):
                response = client.post("/api/itsm/incident?provider=jira", json={"title": "Test"})
                assert response.status_code == 500

    def test_resolve_incident_success(self, client):
        """测试成功解决工单"""
        with patch("api.itsm_router.SERVICE_NOW_URL", "https://test.service-now.com"):
            with patch("api.itsm_router.SERVICE_NOW_TOKEN", "test_token"):
                response = client.patch("/api/itsm/incident/inc-123?provider=servicenow")
                assert response.status_code == 200
                data = response.json()
                assert "status" in data

    def test_resolve_incident_no_config(self, client):
        """测试解决工单配置未完成"""
        with patch("api.itsm_router.SERVICE_NOW_URL", None):
            with patch("api.itsm_router.SERVICE_NOW_TOKEN", None):
                response = client.patch("/api/itsm/incident/inc-123?provider=servicenow")
                assert response.status_code == 500

    def test_resolve_incident_unsupported_provider(self, client):
        """测试解决工单不支持的提供商"""
        response = client.patch("/api/itsm/incident/inc-123?provider=unsupported")
        assert response.status_code == 400


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
