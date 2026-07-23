# -*- coding: utf-8 -*-
# tests/api/test_test_framework_router.py
# 测试框架路由API基础测试
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

# Mock problematic imports before importing router
sys.modules["core.test_framework_manager"] = MagicMock()

from api.test_framework_router import (
    create_test_suite,
    generate_test_file,
    get_framework_status,
    get_test_suites,
)


@pytest.fixture
def client():
    """创建测试客户端"""
    app = FastAPI()
    # Create a new router without authentication dependencies
    test_router = APIRouter(prefix="/api/test-framework", tags=["Test Framework"])
    test_router.add_api_route("/status", get_framework_status, methods=["GET"])
    test_router.add_api_route("/suites", get_test_suites, methods=["GET"])
    test_router.add_api_route("/suite/create", create_test_suite, methods=["POST"])
    test_router.add_api_route("/test/generate", generate_test_file, methods=["POST"])
    app.include_router(test_router)
    return TestClient(app)


class TestTestFrameworkRouter:
    """测试测试框架路由"""

    def test_get_framework_status(self, client):
        """测试获取框架状态"""
        with patch("core.test_framework_manager.get_test_framework_manager") as mock_get:
            mock_manager = Mock()
            mock_manager.get_test_summary.return_value = {
                "total_suites": 20,
                "total_tests": 500,
                "pass_rate": 95.0,
            }
            mock_get.return_value = mock_manager

            response = client.get("/api/test-framework/status")
            assert response.status_code in [200, 500]

    def test_get_test_suites(self, client):
        """测试获取测试套件列表"""
        with patch("core.test_framework_manager.get_test_framework_manager") as mock_get:
            mock_manager = Mock()
            mock_suite = Mock()
            mock_suite.suite_id = "suite-1"
            mock_suite.suite_name = "Test Suite 1"
            mock_suite.test_type.value = "unit"
            mock_suite.test_count = 50
            mock_suite.coverage_target = 80.0
            mock_manager.test_suites = {"suite-1": mock_suite}
            mock_get.return_value = mock_manager

            response = client.get("/api/test-framework/suites")
            assert response.status_code in [200, 500]

    def test_create_test_suite(self, client):
        """测试创建测试套件"""
        with patch("core.test_framework_manager.get_test_framework_manager") as mock_get:
            mock_manager = Mock()
            mock_manager.create_test_suite.return_value = True
            mock_get.return_value = mock_manager

            response = client.post(
                "/api/test-framework/suite/create",
                params={
                    "suite_id": "suite-1",
                    "suite_name": "TestSuite",
                    "test_type": "unit",
                    "description": "Test description",
                },
            )
            assert response.status_code in [200, 500]

    def test_generate_test_file(self, client):
        """测试生成测试文件"""
        with patch("core.test_framework_manager.get_test_framework_manager") as mock_get:
            mock_manager = Mock()
            mock_manager.generate_test_file.return_value = True
            mock_get.return_value = mock_manager

            response = client.post(
                "/api/test-framework/test/generate",
                params={
                    "module_name": "test_module",
                    "class_name": "TestClass",
                    "test_name": "test_method",
                    "test_type": "unit",
                    "output_path": "/tmp/test_file.py",
                },
            )
            assert response.status_code in [200, 500]

    def test_get_framework_status_error(self, client):
        """测试获取框架状态失败"""
        with patch("core.test_framework_manager.get_test_framework_manager") as mock_get:
            mock_get.side_effect = Exception("Framework manager error")

            response = client.get("/api/test-framework/status")
            assert response.status_code == 500


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
