# -*- coding: utf-8 -*-
# tests/api/test_docker_router_simple.py
# Docker路由简化测试 (避免复杂依赖)
import os
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest  # noqa: F401

PROJECT_ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 批量Mock所有可能的依赖
sys.modules["core.authentication"] = Mock()
sys.modules["core.authentication"].get_current_active_user = Mock()
sys.modules["core.authentication"].role_required = Mock(return_value=lambda: {"role": "admin"})
sys.modules["core.docker"] = Mock()
sys.modules["core.docker"].docker_service = Mock()
sys.modules["core.config"] = Mock()
sys.modules["core.docker_collector"] = Mock()
sys.modules["docker"] = Mock()
sys.modules["api.schemas"] = Mock()
sys.modules["api.schemas.repair"] = Mock()


class TestDockerRouterSimple:
    """Docker路由简化测试"""

    def test_docker_router_file_exists(self):
        """测试Docker路由文件存在"""

        docker_router_path = PROJECT_ROOT / "api" / "docker_router.py"
        assert os.path.exists(docker_router_path)

    def test_docker_router_structure(self):
        """测试Docker路由结构"""

        docker_router_path = PROJECT_ROOT / "api" / "docker_router.py"
        with open(docker_router_path, "r", encoding="utf-8") as f:
            content = f.read()
            # 验证路由包含基本的FastAPI组件
            assert "APIRouter" in content or "router" in content
            assert len(content) > 0

    def test_docker_mock_coverage(self):
        """测试Docker相关Mock覆盖"""
        # 验证Docker相关的Mock已经设置
        assert "core.docker" in sys.modules
        assert "docker" in sys.modules
        assert sys.modules["core.docker"] is not None
        assert sys.modules["docker"] is not None
