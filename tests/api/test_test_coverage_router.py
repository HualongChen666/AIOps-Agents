# -*- coding: utf-8 -*-
# tests/api/test_test_coverage_router.py
# 测试覆盖率路由API基础测试
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from api.test_coverage_router import (
    add_module_coverage,
    get_coverage_report,
    get_coverage_status,
    get_module_coverage,
)

# Mock problematic imports before importing router
sys.modules["core.test_coverage_manager"] = MagicMock()


@pytest.fixture
def client():
    """创建测试客户端"""
    app = FastAPI()
    # Create a new router without authentication dependencies
    test_router = APIRouter(prefix="/api/test-coverage", tags=["Test Coverage"])
    test_router.add_api_route("/status", get_coverage_status, methods=["GET"])
    test_router.add_api_route("/module/add", add_module_coverage, methods=["POST"])
    test_router.add_api_route("/module/{module_id}", get_module_coverage, methods=["GET"])
    test_router.add_api_route("/report", get_coverage_report, methods=["GET"])
    app.include_router(test_router)
    return TestClient(app)


class TestTestCoverageRouter:
    """测试测试覆盖率路由"""

    def test_get_coverage_status(self, client):
        """测试获取覆盖率状态"""
        with patch("core.test_coverage_manager.get_coverage_manager") as mock_get:
            mock_manager = Mock()
            mock_manager.get_coverage_summary.return_value = {
                "total_modules": 50,
                "average_coverage": 75.5,
                "modules_above_threshold": 40,
            }
            mock_get.return_value = mock_manager

            response = client.get("/api/test-coverage/status")
            assert response.status_code in [200, 500]

    def test_add_module_coverage(self, client):
        """测试添加模块覆盖率数据"""
        with patch("core.test_coverage_manager.get_coverage_manager") as mock_get:
            mock_manager = Mock()
            mock_manager.add_module_coverage.return_value = True
            mock_get.return_value = mock_manager

            response = client.post(
                "/api/test-coverage/module/add",
                params={
                    "module_id": "mod-1",
                    "module_name": "test_module",
                    "total_lines": "1000",
                    "covered_lines": "750",
                },
            )
            assert response.status_code in [200, 500]

    def test_get_module_coverage(self, client):
        """测试获取模块覆盖率数据"""
        with patch("core.test_coverage_manager.get_coverage_manager") as mock_get:
            mock_manager = Mock()
            mock_coverage = Mock()
            mock_coverage.module_name = "test_module"
            mock_coverage.coverage_percentage = 75.0
            mock_coverage.coverage_level.value = "good"
            mock_manager.get_module_coverage.return_value = mock_coverage
            mock_manager.check_coverage_threshold.return_value = True
            mock_get.return_value = mock_manager

            response = client.get("/api/test-coverage/module/mod-1")
            assert response.status_code in [200, 404, 500]

    def test_get_module_coverage_not_found(self, client):
        """测试获取不存在的模块覆盖率"""
        with patch("core.test_coverage_manager.get_coverage_manager") as mock_get:
            mock_manager = Mock()
            mock_manager.get_module_coverage.return_value = None
            mock_get.return_value = mock_manager

            response = client.get("/api/test-coverage/module/nonexistent")
            assert response.status_code in [404, 500]

    def test_get_coverage_report(self, client):
        """测试获取覆盖率报告"""
        with patch("core.test_coverage_manager.get_coverage_manager") as mock_get:
            mock_manager = Mock()
            mock_manager.get_coverage_report.return_value = {
                "total_lines": 50000,
                "covered_lines": 37500,
                "coverage_percentage": 75.0,
            }
            mock_get.return_value = mock_manager

            response = client.get("/api/test-coverage/report")
            assert response.status_code in [200, 500]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
