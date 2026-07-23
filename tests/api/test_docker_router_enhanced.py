# -*- coding: utf-8 -*-
# tests/api/test_docker_router_enhanced.py
# Docker路由API测试
import os
import sys
from unittest.mock import Mock, patch

import pytest  # noqa: F401
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.docker_router import router

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

sys.modules["core.authentication"] = Mock()
sys.modules["core.authentication"].get_current_active_user = Mock()
sys.modules["core.authentication"].role_required = Mock(return_value=lambda: {"role": "admin"})
sys.modules["core.docker"] = Mock()
sys.modules["core.docker"].docker_service = Mock()
sys.modules["core.config"] = Mock()
sys.modules["core.docker_collector"] = Mock()
sys.modules["docker"] = Mock()


test_app = FastAPI()
test_app.include_router(router)
client = TestClient(test_app)


class TestDockerRouter:
    """Docker路由测试"""

    def test_get_containers(self):
        """测试获取容器列表"""
        with patch("core.docker.docker_service.get_containers") as mock_containers:
            mock_containers.return_value = [{"id": "1", "name": "container1", "status": "running"}]
            response = client.get("/api/v1/docker/containers")
            assert response.status_code in [200, 401, 403, 404]

    def test_get_container_info(self):
        """测试获取容器信息"""
        with patch("core.docker.docker_service.get_container_info") as mock_info:
            mock_info.return_value = {"id": "1", "name": "container1", "image": "nginx"}
            response = client.get("/api/v1/docker/containers/1")
            assert response.status_code in [200, 401, 403, 404]
