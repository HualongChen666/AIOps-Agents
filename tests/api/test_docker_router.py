# -*- coding: utf-8 -*-
"""
Docker Router Tests
Docker路由API基础测试
"""

import sys
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

sys.modules["core.authentication"] = MagicMock()
sys.modules["core.config"] = MagicMock()
sys.modules["core.config"].DOCKER_HOSTS = [{"host": "localhost", "port": 2375}]
sys.modules["core.docker_collector"] = MagicMock()
sys.modules["core.docker_repair"] = MagicMock()


class DockerRepairRequest(BaseModel):
    host: str
    script_name: str
    args: Dict[str, Any] = {}

    class Config:
        schema_extra = {"example": {"host": "example", "script_name": "example", "args": {}}}


mock_schemas = MagicMock()
mock_schemas.DockerRepairRequest = DockerRepairRequest
sys.modules["api.schemas"] = mock_schemas
sys.modules["api.schemas.repair"] = mock_schemas
from api.docker_router import get_docker_metrics, post_docker_repair


@pytest.fixture
def client():
    """创建测试客户端（绕过认证）"""
    app = FastAPI()
    test_router = APIRouter(prefix="/api/v1/platforms/docker", tags=["Docker"])
    test_router.add_api_route("/metrics", get_docker_metrics, methods=["GET"])
    test_router.add_api_route("/repair", post_docker_repair, methods=["POST"])
    app.include_router(test_router)
    return TestClient(app)


class TestDockerRouter:
    """测试Docker路由"""

    def test_get_docker_metrics_success(self, client):
        """测试成功获取Docker指标"""
        with patch("api.docker_router.collect_docker") as mock_collect:
            mock_collect.return_value = {"container_name": "test", "status": "running"}
            response = client.get("/api/v1/platforms/docker/metrics")
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)

    def test_get_docker_metrics_no_hosts(self, client):
        """测试Docker主机未配置"""
        with patch("api.docker_router.DOCKER_HOSTS", []):
            response = client.get("/api/v1/platforms/docker/metrics")
            assert response.status_code == 400

    def test_get_docker_metrics_error(self, client):
        """测试Docker指标采集错误"""
        with patch("api.docker_router.collect_docker") as mock_collect:
            mock_collect.side_effect = Exception("Collection error")
            response = client.get("/api/v1/platforms/docker/metrics")
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)

    def test_post_docker_repair_success(self, client):
        """测试成功执行Docker修复"""
        with patch("api.docker_router.execute_repair_sync") as mock_repair:

            async def mock_repair_func(host, script_name, args):
                return {"success": True, "output": "Container restarted", "exit_code": 0}

            mock_repair.side_effect = mock_repair_func
            response = client.post(
                "/api/v1/platforms/docker/repair",
                json={"host": "localhost", "script_name": "restart_container", "args": {}},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_post_docker_repair_host_not_found(self, client):
        """测试Docker主机未找到"""
        with patch("api.docker_router.DOCKER_HOSTS", []):
            response = client.post(
                "/api/v1/platforms/docker/repair",
                json={"host": "unknown", "script_name": "restart_container", "args": {}},
            )
            assert response.status_code == 404

    def test_post_docker_repair_error(self, client):
        """测试Docker修复执行错误"""
        with patch("api.docker_router.execute_repair_sync") as mock_repair:

            async def mock_repair_func(host, script_name, args):
                raise Exception("Repair error")

            mock_repair.side_effect = mock_repair_func
            response = client.post(
                "/api/v1/platforms/docker/repair",
                json={"host": "localhost", "script_name": "restart_container", "args": {}},
            )
            assert response.status_code == 500


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
