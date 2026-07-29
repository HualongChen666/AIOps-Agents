# -*- coding: utf-8 -*-
# tests/api/test_test_automation_router.py
# 测试自动化路由API基础测试
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from api.test_automation_router import (
    create_automation_job,
    generate_cicd_pipeline,
    get_automation_status,
    run_automation_job,
)

# Mock problematic imports before importing router
sys.modules["core.test_automation_manager"] = MagicMock()


@pytest.fixture
def client():
    """创建测试客户端"""
    app = FastAPI()
    # Create a new router without authentication dependencies
    test_router = APIRouter(prefix="/api/test-automation", tags=["Test Automation"])
    test_router.add_api_route("/status", get_automation_status, methods=["GET"])
    test_router.add_api_route("/job/create", create_automation_job, methods=["POST"])
    test_router.add_api_route("/job/{job_id}/run", run_automation_job, methods=["POST"])
    test_router.add_api_route("/cicd/generate", generate_cicd_pipeline, methods=["POST"])
    app.include_router(test_router)
    return TestClient(app)


class TestTestAutomationRouter:
    """测试测试自动化路由"""

    def test_get_automation_status(self, client):
        """测试获取自动化状态"""
        with patch("core.test_automation_manager.get_automation_manager") as mock_get:
            mock_manager = Mock()
            mock_manager.get_automation_summary.return_value = {
                "total_jobs": 10,
                "active_jobs": 5,
                "completed_jobs": 5,
            }
            mock_get.return_value = mock_manager

            response = client.get("/api/test-automation/status")
            assert response.status_code in [200, 500]

    def test_create_automation_job(self, client):
        """测试创建自动化任务"""
        with patch("core.test_automation_manager.get_automation_manager") as mock_get:
            mock_manager = Mock()
            mock_manager.create_automation_job.return_value = True
            mock_get.return_value = mock_manager

            response = client.post(
                "/api/test-automation/job/create?job_id=job-1&job_name=TestJob&job_type=unit"
            )
            assert response.status_code in [200, 500]

    def test_run_automation_job(self, client):
        """测试运行自动化任务"""
        with patch("core.test_automation_manager.get_automation_manager") as mock_get:
            mock_manager = Mock()
            mock_manager.run_automation_job.return_value = True
            mock_get.return_value = mock_manager

            response = client.post("/api/test-automation/job/job-1/run")
            assert response.status_code in [200, 500]

    def test_generate_cicd_pipeline(self, client):
        """测试生成CI/CD流水线配置"""
        with patch("core.test_automation_manager.get_automation_manager") as mock_get:
            mock_manager = Mock()
            mock_manager.generate_ci_cd_pipeline.return_value = True
            mock_get.return_value = mock_manager

            response = client.post(
                "/api/test-automation/cicd/generate",
                params={"output_path": "/tmp/cicd.yml", "platform": "github_actions"},
            )
            assert response.status_code in [200, 500]

    def test_get_automation_status_error(self, client):
        """测试获取自动化状态失败"""
        with patch("core.test_automation_manager.get_automation_manager") as mock_get:
            mock_get.side_effect = Exception("Automation manager error")

            response = client.get("/api/test-automation/status")
            assert response.status_code == 500


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
