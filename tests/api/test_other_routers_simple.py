# -*- coding: utf-8 -*-
# tests/api/test_other_routers_simple.py
# 其他路由简化测试
import os
import sys
from unittest.mock import Mock
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 批量Mock所有可能的依赖
sys.modules["core.authentication"] = Mock()
sys.modules["core.authentication"].get_current_active_user = Mock()
sys.modules["core.authentication"].role_required = Mock(return_value=lambda: {"role": "admin"})

low_priority_modules = [
    "core.batch",
    "core.chaos",
    "core.cost",
    "core.dashboard",
    "core.docker",
    "core.documentation",
    "core.graphql",
    "core.grpc",
    "core.hitl",
    "core.i18n",
    "core.itsm",
    "core.localization",
    "core.macOS",
    "core.mcp",
    "core.qdrant",
    "core.rag",
    "core.service_discovery",
    "core.service_mesh",
    "core.slack",
    "core.sse",
    "core.stats",
    "core.system_resource",
    "core.test_automation",
    "core.test_coverage",
    "core.test_framework",
    "core.tracing",
    "core.websocket",
    "core.windows_repair",
    "core.workflow_visualization",
]

for module in low_priority_modules:
    sys.modules[module] = Mock()


class TestOtherRouters:
    """其他路由简化测试"""

    def test_routers_import(self):
        """测试路由可以导入"""
        # 测试几个关键路由可以导入
        import api.batch_router  # noqa: E402, F401

        assert True

    def test_router_structure(self):
        """测试路由结构"""
        # 验证API路由文件存在

        api_dir = PROJECT_ROOT / "api"
        router_files = [
            "batch_router.py",
            "chaos_router.py",
            "cost_router.py",
            "dashboard_router.py",
            "docker_router.py",
            "documentation_router.py",
            "graphql_router.py",
            "grpc_router.py",
            "hitl_router.py",
            "i18n_router.py",
            "itsm_router.py",
            "localization_adapter_router.py",
            "localization_resource_router.py",
            "macos_router.py",
            "mcp_router.py",
            "priority_router.py",
            "qdrant_router.py",
            "rag_router.py",
            "rag_history_router.py",
            "service_discovery_router.py",
            "service_mesh_router.py",
            "service_monitoring_router.py",
            "slack_router.py",
            "sse_router.py",
            "stats_router.py",
            "system_resource_router.py",
            "test_automation_router.py",
            "test_coverage_router.py",
            "test_framework_router.py",
            "topology_view_router.py",
            "tracing_router.py",
            "unified_repair_router.py",
            "websocket_router.py",
            "windows_repair_router.py",
            "workflow_visualization_router.py",
        ]

        existing_routers = []
        for router_file in router_files:
            if os.path.exists(os.path.join(api_dir, router_file)):
                existing_routers.append(router_file)

        # 至少应该有一些路由文件存在
        assert len(existing_routers) > 0
