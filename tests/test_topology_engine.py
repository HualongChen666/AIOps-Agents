# -*- coding: utf-8 -*-
# tests/test_topology_engine.py
# 拓扑引擎单元测试
import asyncio  # noqa: F401
from datetime import datetime  # noqa: F401
from unittest.mock import AsyncMock, MagicMock, patch  # noqa: F401

import pytest

from core.topology_engine import (
    add_edge,
    add_node,
    build_topology,
    get_impact_analysis,
    get_node_dependencies,
    get_topology,
    remove_edge,
    remove_node,
)


class TestTopologyBuilding:
    """拓扑构建测试"""

    @pytest.mark.asyncio
    async def test_build_topology_success(self, mock_logger):
        """测试拓扑构建成功"""
        nodes = [
            {"id": "node-1", "type": "service", "name": "nginx"},
            {"id": "node-2", "type": "service", "name": "postgres"},
        ]
        edges = [
            {"source": "node-1", "target": "node-2", "type": "depends_on"},
        ]

        with patch("core.topology_engine.logger", mock_logger):
            # Mock 数据库操作
            with patch(
                "core.topology_engine.insert_topology", AsyncMock(return_value="topology-001")
            ):
                result = await build_topology(nodes, edges)

                # 验证构建成功
                assert result["success"] is True
                assert "topology_id" in result

    @pytest.mark.asyncio
    async def test_build_topology_with_invalid_nodes(self, mock_logger):
        """测试无效节点构建"""
        nodes = [
            {"id": "", "type": "service", "name": "nginx"},  # 无效 ID
        ]
        edges = []

        with patch("core.topology_engine.logger", mock_logger):
            result = await build_topology(nodes, edges)

            # 验证构建失败
            assert result["success"] is False
            assert "invalid" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_build_topology_with_circular_dependency(self, mock_logger):
        """测试循环依赖检测"""
        nodes = [
            {"id": "node-1", "type": "service", "name": "service-a"},
            {"id": "node-2", "type": "service", "name": "service-b"},
        ]
        edges = [
            {"source": "node-1", "target": "node-2", "type": "depends_on"},
            {"source": "node-2", "target": "node-1", "type": "depends_on"},  # 循环依赖
        ]

        with patch("core.topology_engine.logger", mock_logger):
            result = await build_topology(nodes, edges)

            # 验证循环依赖被检测
            assert result["success"] is False
            assert "circular" in result["error"].lower()


class TestTopologyQuery:
    """拓扑查询测试"""

    @pytest.mark.asyncio
    async def test_get_topology_success(self, mock_logger):
        """测试获取拓扑成功"""
        topology_id = "topology-001"

        with patch("core.topology_engine.logger", mock_logger):
            # Mock 数据库查询
            with patch(
                "core.topology_engine.query_topology",
                AsyncMock(
                    return_value={
                        "id": topology_id,
                        "nodes": [
                            {"id": "node-1", "type": "service", "name": "nginx"},
                        ],
                        "edges": [],
                    }
                ),
            ):
                result = await get_topology(topology_id)

                # 验证获取成功
                assert result["success"] is True
                assert result["topology"]["id"] == topology_id

    @pytest.mark.asyncio
    async def test_get_topology_not_found(self, mock_logger):
        """测试拓扑不存在"""
        topology_id = "nonexistent-topology"

        with patch("core.topology_engine.logger", mock_logger):
            # Mock 数据库查询返回 None
            with patch("core.topology_engine.query_topology", AsyncMock(return_value=None)):
                result = await get_topology(topology_id)

                # 验证拓扑不存在
                assert result["success"] is False
                assert "not found" in result["error"].lower()


class TestNodeManagement:
    """节点管理测试"""

    @pytest.mark.asyncio
    async def test_add_node_success(self, mock_logger):
        """测试添加节点成功"""
        node = {
            "id": "node-3",
            "type": "service",
            "name": "redis",
        }

        with patch("core.topology_engine.logger", mock_logger):
            # Mock 数据库操作
            with patch("core.topology_engine.insert_node", AsyncMock(return_value=True)):
                result = await add_node(node)

                # 验证添加成功
                assert result["success"] is True

    @pytest.mark.asyncio
    async def test_add_node_duplicate(self, mock_logger):
        """测试添加重复节点"""
        node = {
            "id": "node-1",  # 已存在的节点
            "type": "service",
            "name": "nginx",
        }

        with patch("core.topology_engine.logger", mock_logger):
            # Mock 数据库操作返回 False（已存在）
            with patch("core.topology_engine.insert_node", AsyncMock(return_value=False)):
                result = await add_node(node)

                # 验证添加失败
                assert result["success"] is False
                assert "duplicate" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_remove_node_success(self, mock_logger):
        """测试移除节点成功"""
        node_id = "node-1"

        with patch("core.topology_engine.logger", mock_logger):
            # Mock 数据库操作
            with patch("core.topology_engine.delete_node", AsyncMock(return_value=True)):
                result = await remove_node(node_id)

                # 验证移除成功
                assert result["success"] is True

    @pytest.mark.asyncio
    async def test_remove_node_with_dependencies(self, mock_logger):
        """测试移除有依赖的节点"""
        node_id = "node-1"

        with patch("core.topology_engine.logger", mock_logger):
            # Mock 依赖检查
            with patch(
                "core.topology_engine.get_node_dependencies",
                AsyncMock(
                    return_value=[
                        {"source": "node-2", "target": "node-1"},
                    ]
                ),
            ):
                result = await remove_node(node_id)

                # 验证移除失败（有依赖）
                assert result["success"] is False
                assert "dependencies" in result["error"].lower()


class TestEdgeManagement:
    """边管理测试"""

    @pytest.mark.asyncio
    async def test_add_edge_success(self, mock_logger):
        """测试添加边成功"""
        edge = {
            "source": "node-1",
            "target": "node-2",
            "type": "depends_on",
        }

        with patch("core.topology_engine.logger", mock_logger):
            # Mock 数据库操作
            with patch("core.topology_engine.insert_edge", AsyncMock(return_value=True)):
                result = await add_edge(edge)

                # 验证添加成功
                assert result["success"] is True

    @pytest.mark.asyncio
    async def test_add_edge_invalid_nodes(self, mock_logger):
        """测试添加无效节点的边"""
        edge = {
            "source": "nonexistent-node",
            "target": "node-2",
            "type": "depends_on",
        }

        with patch("core.topology_engine.logger", mock_logger):
            # Mock 节点检查
            with patch("core.topology_engine.node_exists", AsyncMock(return_value=False)):
                result = await add_edge(edge)

                # 验证添加失败
                assert result["success"] is False
                assert "node not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_remove_edge_success(self, mock_logger):
        """测试移除边成功"""
        edge_id = "edge-1"

        with patch("core.topology_engine.logger", mock_logger):
            # Mock 数据库操作
            with patch("core.topology_engine.delete_edge", AsyncMock(return_value=True)):
                result = await remove_edge(edge_id)

                # 验证移除成功
                assert result["success"] is True


class TestDependencyAnalysis:
    """依赖分析测试"""

    @pytest.mark.asyncio
    async def test_get_node_dependencies(self, mock_logger):
        """测试获取节点依赖"""
        node_id = "node-1"

        with patch("core.topology_engine.logger", mock_logger):
            # Mock 数据库查询
            with patch(
                "core.topology_engine.query_dependencies",
                AsyncMock(
                    return_value=[
                        {"source": "node-1", "target": "node-2", "type": "depends_on"},
                        {"source": "node-1", "target": "node-3", "type": "depends_on"},
                    ]
                ),
            ):
                dependencies = await get_node_dependencies(node_id)

                # 验证依赖列表
                assert len(dependencies) == 2
                assert all(dep["source"] == node_id for dep in dependencies)

    @pytest.mark.asyncio
    async def test_get_impact_analysis(self, mock_logger):
        """测试影响分析"""
        node_id = "node-1"

        with patch("core.topology_engine.logger", mock_logger):
            # Mock 依赖查询
            with patch(
                "core.topology_engine.query_dependencies",
                AsyncMock(
                    return_value=[
                        {"source": "node-2", "target": "node-1", "type": "depends_on"},
                        {"source": "node-3", "target": "node-1", "type": "depends_on"},
                    ]
                ),
            ):
                # Mock 递归依赖查询
                with patch(
                    "core.topology_engine.get_transitive_dependencies",
                    AsyncMock(
                        return_value=[
                            "node-2",
                            "node-3",
                            "node-4",
                            "node-5",
                        ]
                    ),
                ):
                    impact = await get_impact_analysis(node_id)

                    # 验证影响分析
                    assert "direct_impact" in impact
                    assert "transitive_impact" in impact
                    assert len(impact["direct_impact"]) == 2
                    assert len(impact["transitive_impact"]) == 4


class TestTopologyValidation:
    """拓扑验证测试"""

    @pytest.mark.asyncio
    async def test_validate_topology_valid(self, mock_logger):
        """测试验证有效拓扑"""
        topology = {
            "nodes": [
                {"id": "node-1", "type": "service"},
                {"id": "node-2", "type": "service"},
            ],
            "edges": [
                {"source": "node-1", "target": "node-2"},
            ],
        }

        with patch("core.topology_engine.logger", mock_logger):
            from core.topology_engine import validate_topology

            result = validate_topology(topology)

            # 验证拓扑有效
            assert result["valid"] is True

    @pytest.mark.asyncio
    async def test_validate_topology_orphan_nodes(self, mock_logger):
        """测试验证孤立节点"""
        topology = {
            "nodes": [
                {"id": "node-1", "type": "service"},
                {"id": "node-2", "type": "service"},
            ],
            "edges": [],  # 没有边，节点孤立
        }

        with patch("core.topology_engine.logger", mock_logger):
            from core.topology_engine import validate_topology

            result = validate_topology(topology)

            # 验证拓扑有警告
            assert result["valid"] is True
            assert "warnings" in result
            assert len(result["warnings"]) > 0


class TestTopologyCaching:
    """拓扑缓存测试"""

    @pytest.mark.asyncio
    async def test_topology_cache_hit(self, mock_logger):
        """测试拓扑缓存命中"""
        topology_id = "topology-001"

        with patch("core.topology_engine.logger", mock_logger):
            # Mock 缓存
            with patch("core.topology_engine._topology_cache", {topology_id: {"id": topology_id}}):
                result = await get_topology(topology_id)

                # 验证从缓存获取
                assert result["success"] is True
                assert result["from_cache"] is True

    @pytest.mark.asyncio
    async def test_topology_cache_miss(self, mock_logger):
        """测试拓扑缓存未命中"""
        topology_id = "topology-001"

        with patch("core.topology_engine.logger", mock_logger):
            # Mock 缓存为空
            with patch("core.topology_engine._topology_cache", {}):
                # Mock 数据库查询
                with patch(
                    "core.topology_engine.query_topology",
                    AsyncMock(
                        return_value={
                            "id": topology_id,
                            "nodes": [],
                            "edges": [],
                        }
                    ),
                ):
                    result = await get_topology(topology_id)

                    # 验证从数据库获取
                    assert result["success"] is True
                    assert result["from_cache"] is False


class TestTopologyErrorHandling:
    """拓扑错误处理测试"""

    @pytest.mark.asyncio
    async def test_build_topology_with_db_error(self, mock_logger):
        """测试数据库错误处理"""
        nodes = [{"id": "node-1", "type": "service"}]
        edges = []

        with patch("core.topology_engine.logger", mock_logger):
            # Mock 数据库操作失败
            with patch(
                "core.topology_engine.insert_topology", AsyncMock(side_effect=Exception("DB error"))
            ):
                result = await build_topology(nodes, edges)

                # 验证错误被捕获
                assert result["success"] is False
                # 验证日志记录
                mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_get_topology_with_invalid_id(self, mock_logger):
        """测试无效 ID 处理"""
        topology_id = ""

        with patch("core.topology_engine.logger", mock_logger):
            result = await get_topology(topology_id)

            # 验证无效 ID 处理
            assert result["success"] is False
            assert "invalid" in result["error"].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
