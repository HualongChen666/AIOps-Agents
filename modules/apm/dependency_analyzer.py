# -*- coding: utf-8 -*-
"""
dependency_analyzer.py
----------------------
APM 依赖分析和拓扑模块。

功能：
- 自动发现服务依赖
- 构建完整依赖拓扑
- 识别关键路径
- 依赖健康度评估
- 拓扑可视化
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# 1️⃣ 依赖类型枚举
# ----------------------------------------------------------------------
class DependencyType(Enum):
    """依赖类型"""

    SYNC = "sync"  # 同步调用
    ASYNC = "async"  # 异步调用
    DATABASE = "database"  # 数据库依赖
    CACHE = "cache"  # 缓存依赖
    MESSAGE_QUEUE = "message_queue"  # 消息队列
    EXTERNAL_API = "external_api"  # 外部 API


# ----------------------------------------------------------------------
# 2️⃣ 健康状态枚举
# ----------------------------------------------------------------------
class HealthStatus(Enum):
    """健康状态"""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


# ----------------------------------------------------------------------
# 3️⃣ 服务节点定义
# ----------------------------------------------------------------------
@dataclass
class ServiceNode:
    """服务节点"""

    id: str
    name: str
    type: str = "microservice"
    health: HealthStatus = HealthStatus.UNKNOWN
    metrics: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "health": self.health.value,
            "metrics": self.metrics,
            "metadata": self.metadata,
        }


# ----------------------------------------------------------------------
# 4️⃣ 依赖边定义
# ----------------------------------------------------------------------
@dataclass
class DependencyEdge:
    """依赖边"""

    source: str
    target: str
    dependency_type: DependencyType
    weight: float = 1.0
    latency: Optional[float] = None
    error_rate: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "source": self.source,
            "target": self.target,
            "dependency_type": self.dependency_type.value,
            "weight": self.weight,
            "latency": self.latency,
            "error_rate": self.error_rate,
            "metadata": self.metadata,
        }


# ----------------------------------------------------------------------
# 5️⃣ 依赖拓扑图
# ----------------------------------------------------------------------
class DependencyTopology:
    """依赖拓扑图"""

    def __init__(self):
        self.nodes: Dict[str, ServiceNode] = {}
        self.edges: List[DependencyEdge] = []
        self.adjacency: Dict[str, Set[str]] = defaultdict(set)
        self.reverse_adjacency: Dict[str, Set[str]] = defaultdict(set)

    def add_node(self, node: ServiceNode):
        """添加节点"""
        self.nodes[node.id] = node
        logger.debug(f"Added node: {node.id}")

    def add_edge(self, edge: DependencyEdge):
        """添加边"""
        self.edges.append(edge)
        self.adjacency[edge.source].add(edge.target)
        self.reverse_adjacency[edge.target].add(edge.source)
        logger.debug(f"Added edge: {edge.source} -> {edge.target}")

    def get_dependencies(self, node_id: str) -> Set[str]:
        """获取依赖（下游）"""
        return self.adjacency.get(node_id, set())

    def get_dependents(self, node_id: str) -> Set[str]:
        """获取被依赖（上游）"""
        return self.reverse_adjacency.get(node_id, set())

    def get_all_dependencies(self, node_id: str) -> Set[str]:
        """获取所有依赖（递归）"""
        all_deps = set()
        queue = deque(self.get_dependencies(node_id))

        while queue:
            current = queue.popleft()
            if current not in all_deps:
                all_deps.add(current)
                queue.extend(self.get_dependencies(current))

        return all_deps

    def get_all_dependents(self, node_id: str) -> Set[str]:
        """获取所有被依赖（递归）"""
        all_dependents = set()
        queue = deque(self.get_dependents(node_id))

        while queue:
            current = queue.popleft()
            if current not in all_dependents:
                all_dependents.add(current)
                queue.extend(self.get_dependents(current))

        return all_dependents

    def find_critical_path(self, start_node: str, end_node: str) -> List[str]:
        """查找关键路径（基于权重）"""
        # 使用 Dijkstra 算法
        distances = {node_id: float("inf") for node_id in self.nodes}
        distances[start_node] = 0
        previous = {}
        visited = set()

        for _ in range(len(self.nodes)):
            # 选择未访问的最小距离节点
            current = min(
                (node for node in self.nodes if node not in visited),
                key=lambda n: distances[n],
                default=None,
            )

            if current is None or current == end_node:
                break

            visited.add(current)

            # 更新邻居距离
            for neighbor in self.get_dependencies(current):
                if neighbor in visited:
                    continue

                # 查找边权重
                edge = next(
                    (e for e in self.edges if e.source == current and e.target == neighbor),
                    None,
                )
                weight = edge.weight if edge else 1.0

                new_distance = distances[current] + weight
                if new_distance < distances[neighbor]:
                    distances[neighbor] = new_distance
                    previous[neighbor] = current

        # 重建路径
        if end_node not in previous and start_node != end_node:
            return []

        path = []
        current = end_node
        while current != start_node:
            path.append(current)
            current = previous.get(current)
            if current is None:
                return []
        path.append(start_node)
        path.reverse()

        return path

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "nodes": [node.to_dict() for node in self.nodes.values()],
            "edges": [edge.to_dict() for edge in self.edges],
        }


# ----------------------------------------------------------------------
# 6️⃣ 依赖发现器
# ----------------------------------------------------------------------
class DependencyDiscoverer:
    """依赖发现器"""

    def __init__(self):
        from typing import Callable

        self.discovery_methods: Dict[str, Callable[..., DependencyTopology]] = {
            "trace": self._discover_from_traces,
            "config": self._discover_from_config,
            "metrics": self._discover_from_metrics,
        }

    def discover(
        self,
        method: str = "trace",
        **kwargs,
    ) -> DependencyTopology:
        """
        发现依赖

        Parameters
        ----------
        method : str
            发现方法：'trace', 'config', 'metrics'
        **kwargs
            发现参数

        Returns
        -------
        DependencyTopology
            依赖拓扑
        """
        if method not in self.discovery_methods:
            raise ValueError(f"Unknown discovery method: {method}")

        return self.discovery_methods[method](**kwargs)

    def _discover_from_traces(
        self,
        trace_data: List[Dict[str, Any]],
    ) -> DependencyTopology:
        """从追踪数据发现依赖"""
        topology = DependencyTopology()

        for trace in trace_data:
            spans = trace.get("spans", [])

            for i, span in enumerate(spans):
                # 添加服务节点
                service_id = span.get("service_id", f"service_{i}")
                service_name = span.get("service_name", f"Service {i}")

                if service_id not in topology.nodes:
                    topology.add_node(
                        ServiceNode(
                            id=service_id,
                            name=service_name,
                        )
                    )

                # 添加依赖边
                if i > 0:
                    parent_span = spans[i - 1]
                    parent_id = parent_span.get("service_id", f"service_{i - 1}")

                    # 确定依赖类型
                    dep_type = DependencyType.SYNC
                    if span.get("kind") == "producer":
                        dep_type = DependencyType.ASYNC
                    elif span.get("kind") == "client":
                        dep_type = DependencyType.EXTERNAL_API

                    topology.add_edge(
                        DependencyEdge(
                            source=parent_id,
                            target=service_id,
                            dependency_type=dep_type,
                            latency=span.get("duration"),
                        )
                    )

        logger.info(f"Discovered {len(topology.nodes)} nodes from traces")
        return topology

    def _discover_from_config(
        self,
        config_data: Dict[str, Any],
    ) -> DependencyTopology:
        """从配置发现依赖"""
        topology = DependencyTopology()

        # 解析服务配置
        services = config_data.get("services", [])

        for service_config in services:
            service_id = service_config.get("id")
            service_name = service_config.get("name")

            if service_id not in topology.nodes:
                topology.add_node(
                    ServiceNode(
                        id=service_id,
                        name=service_name,
                    )
                )

            # 解析依赖
            dependencies = service_config.get("dependencies", [])

            for dep in dependencies:
                dep_id = dep.get("id")
                dep_type_str = dep.get("type", "sync")

                # 确定依赖类型
                try:
                    dep_type = DependencyType(dep_type_str)
                except ValueError:
                    dep_type = DependencyType.SYNC

                # 添加依赖服务节点
                if dep_id not in topology.nodes:
                    topology.add_node(
                        ServiceNode(
                            id=dep_id,
                            name=dep.get("name", dep_id),
                        )
                    )

                topology.add_edge(
                    DependencyEdge(
                        source=service_id,
                        target=dep_id,
                        dependency_type=dep_type,
                    )
                )

        logger.info(f"Discovered {len(topology.nodes)} nodes from config")
        return topology

    def _discover_from_metrics(
        self,
        metrics_data: Dict[str, Any],
    ) -> DependencyTopology:
        """从指标数据发现依赖"""
        topology = DependencyTopology()

        # 基于调用关系推断依赖
        call_relationships = metrics_data.get("call_relationships", [])

        for rel in call_relationships:
            source = rel.get("source")
            target = rel.get("target")
            call_count = rel.get("call_count", 0)

            if call_count == 0:
                continue

            # 添加节点
            if source not in topology.nodes:
                topology.add_node(ServiceNode(id=source, name=source))

            if target not in topology.nodes:
                topology.add_node(ServiceNode(id=target, name=target))

            # 添加边
            topology.add_edge(
                DependencyEdge(
                    source=source,
                    target=target,
                    dependency_type=DependencyType.SYNC,
                    weight=call_count,
                )
            )

        logger.info(f"Discovered {len(topology.nodes)} nodes from metrics")
        return topology


# ----------------------------------------------------------------------
# 7️⃣ 依赖健康度评估器
# ----------------------------------------------------------------------
class DependencyHealthAssessor:
    """依赖健康度评估器"""

    def __init__(self, topology: DependencyTopology):
        """
        Parameters
        ----------
        topology : DependencyTopology
            依赖拓扑
        """
        self.topology = topology

    def assess_node_health(
        self,
        node_id: str,
        metrics: Dict[str, Any],
    ) -> HealthStatus:
        """
        评估节点健康度

        Parameters
        ----------
        node_id : str
            节点 ID
        metrics : Dict[str, Any]
            指标数据

        Returns
        -------
        HealthStatus
            健康状态
        """
        # 基于指标评估
        error_rate = metrics.get("error_rate", 0)
        latency = metrics.get("latency", 0)
        availability = metrics.get("availability", 1.0)

        if error_rate > 0.05 or availability < 0.95:
            return HealthStatus.UNHEALTHY
        elif error_rate > 0.01 or latency > 1000:
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.HEALTHY

    def assess_dependency_health(
        self,
        edge: DependencyEdge,
    ) -> HealthStatus:
        """
        评估依赖健康度

        Parameters
        ----------
        edge : DependencyEdge
            依赖边

        Returns
        -------
        HealthStatus
            健康状态
        """
        if edge.error_rate is not None:
            if edge.error_rate > 0.05:
                return HealthStatus.UNHEALTHY
            elif edge.error_rate > 0.01:
                return HealthStatus.DEGRADED

        if edge.latency is not None:
            if edge.latency > 5000:  # 5秒
                return HealthStatus.UNHEALTHY
            elif edge.latency > 1000:  # 1秒
                return HealthStatus.DEGRADED

        return HealthStatus.HEALTHY

    def assess_topology_health(self) -> Dict[str, HealthStatus]:
        """评估整个拓扑健康度"""
        health_status = {}

        for node_id, node in self.topology.nodes.items():
            health_status[node_id] = node.health

        return health_status

    def identify_critical_nodes(self) -> List[str]:
        """识别关键节点（被依赖最多的节点）"""
        dependency_counts = {
            node_id: len(self.topology.get_dependents(node_id)) for node_id in self.topology.nodes
        }

        # 按被依赖数量排序
        sorted_nodes = sorted(
            dependency_counts.items(),
            key=lambda x: x[1],
            reverse=True,
        )

        return [node_id for node_id, _ in sorted_nodes]


# ----------------------------------------------------------------------
# 8️⃣ 拓扑可视化
# ----------------------------------------------------------------------
class TopologyVisualizer:
    """拓扑可视化"""

    @staticmethod
    def to_networkx(topology: DependencyTopology) -> Any:
        """转换为 NetworkX 图"""
        try:
            import networkx as nx
        except ImportError:
            raise ImportError("NetworkX is required for visualization")

        nx_graph = nx.DiGraph()

        # 添加节点
        for node_id, node in topology.nodes.items():
            nx_graph.add_node(
                node_id,
                name=node.name,
                health=node.health.value,
            )

        # 添加边
        for edge in topology.edges:
            nx_graph.add_edge(
                edge.source,
                edge.target,
                type=edge.dependency_type.value,
                weight=edge.weight,
            )

        return nx_graph

    @staticmethod
    def plot(
        topology: DependencyTopology,
        output_path: Optional[str] = None,
        figsize: Tuple[int, int] = (16, 12),
    ):
        """
        绘制拓扑图

        Parameters
        ----------
        topology : DependencyTopology
            依赖拓扑
        output_path : str, optional
            输出路径
        figsize : Tuple[int, int]
            图形大小
        """
        try:
            import matplotlib.pyplot as plt
            import networkx as nx
        except ImportError:
            raise ImportError("Matplotlib and NetworkX are required")

        nx_graph = TopologyVisualizer.to_networkx(topology)

        plt.figure(figsize=figsize)

        # 使用分层布局
        pos = nx.spring_layout(nx_graph, k=2, iterations=50)

        # 根据健康状态着色
        color_map = {
            "healthy": "green",
            "degraded": "yellow",
            "unhealthy": "red",
            "unknown": "gray",
        }

        node_colors = [
            color_map.get(nx_graph.nodes[n].get("health", "unknown"), "gray")
            for n in nx_graph.nodes()
        ]

        # 绘制节点
        nx.draw_networkx_nodes(
            nx_graph,
            pos,
            node_color=node_colors,
            node_size=1000,
        )

        # 绘制边
        nx.draw_networkx_edges(nx_graph, pos, edge_color="gray", arrows=True)

        # 绘制标签
        nx.draw_networkx_labels(
            nx_graph,
            pos,
            labels={n: nx_graph.nodes[n].get("name", n) for n in nx_graph.nodes()},
            font_size=8,
        )

        plt.title("Service Dependency Topology")
        plt.axis("off")

        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches="tight")
            logger.info(f"Topology saved to {output_path}")
        else:
            plt.show()

        plt.close()

    @staticmethod
    def to_json(topology: DependencyTopology) -> str:
        """转换为 JSON"""
        return json.dumps(topology.to_dict(), indent=2, ensure_ascii=False)

    @staticmethod
    def from_json(json_str: str) -> DependencyTopology:
        """从 JSON 加载拓扑"""
        data = json.loads(json_str)

        topology = DependencyTopology()

        # 添加节点
        for node_data in data.get("nodes", []):
            node = ServiceNode(
                id=node_data["id"],
                name=node_data["name"],
                type=node_data.get("type", "microservice"),
                health=HealthStatus(node_data.get("health", "unknown")),
                metrics=node_data.get("metrics", {}),
                metadata=node_data.get("metadata", {}),
            )
            topology.add_node(node)

        # 添加边
        for edge_data in data.get("edges", []):
            edge = DependencyEdge(
                source=edge_data["source"],
                target=edge_data["target"],
                dependency_type=DependencyType(edge_data["dependency_type"]),
                weight=edge_data.get("weight", 1.0),
                latency=edge_data.get("latency"),
                error_rate=edge_data.get("error_rate"),
                metadata=edge_data.get("metadata", {}),
            )
            topology.add_edge(edge)

        return topology


# ----------------------------------------------------------------------
# 9️⃣ 综合依赖分析器
# ----------------------------------------------------------------------
class DependencyAnalyzer:
    """综合依赖分析器"""

    def __init__(self):
        self.topology: Optional[DependencyTopology] = None
        self.discoverer = DependencyDiscoverer()
        self.health_assessor: Optional[DependencyHealthAssessor] = None

    def discover_topology(
        self,
        method: str = "trace",
        **kwargs,
    ) -> DependencyTopology:
        """
        发现依赖拓扑

        Parameters
        ----------
        method : str
            发现方法
        **kwargs
            发现参数

        Returns
        -------
        DependencyTopology
            依赖拓扑
        """
        self.topology = self.discoverer.discover(method, **kwargs)
        self.health_assessor = DependencyHealthAssessor(self.topology)
        return self.topology

    def analyze_dependencies(
        self,
        node_id: str,
    ) -> Dict[str, Any]:
        """
        分析依赖

        Parameters
        ----------
        node_id : str
            节点 ID

        Returns
        -------
        Dict[str, Any]
            分析结果
        """
        if self.topology is None:
            raise RuntimeError("Topology not discovered. Call discover_topology() first.")

        direct_deps = self.topology.get_dependencies(node_id)
        all_deps = self.topology.get_all_dependencies(node_id)
        direct_dependents = self.topology.get_dependents(node_id)
        all_dependents = self.topology.get_all_dependents(node_id)

        return {
            "node_id": node_id,
            "direct_dependencies": list(direct_deps),
            "all_dependencies": list(all_deps),
            "direct_dependents": list(direct_dependents),
            "all_dependents": list(all_dependents),
            "dependency_count": len(all_deps),
            "dependent_count": len(all_dependents),
        }

    def get_critical_path(
        self,
        start_node: str,
        end_node: str,
    ) -> List[str]:
        """
        获取关键路径

        Parameters
        ----------
        start_node : str
            起始节点
        end_node : str
            结束节点

        Returns
        -------
        List[str]
            关键路径
        """
        if self.topology is None:
            raise RuntimeError("Topology not discovered. Call discover_topology() first.")

        return self.topology.find_critical_path(start_node, end_node)

    def get_health_report(self) -> Dict[str, Any]:
        """获取健康报告"""
        if self.topology is None or self.health_assessor is None:
            raise RuntimeError("Topology not discovered. Call discover_topology() first.")

        health_status = self.health_assessor.assess_topology_health()
        critical_nodes = self.health_assessor.identify_critical_nodes()

        return {
            "health_status": {k: v.value for k, v in health_status.items()},
            "critical_nodes": critical_nodes,
            "total_nodes": len(self.topology.nodes),
            "total_edges": len(self.topology.edges),
        }


# ----------------------------------------------------------------------
# 🔟 工厂函数
# ----------------------------------------------------------------------
def create_dependency_analyzer() -> DependencyAnalyzer:
    """创建依赖分析器"""
    return DependencyAnalyzer()


# ----------------------------------------------------------------------
# 1️⃣1️⃣ CLI 用于快速测试
# ----------------------------------------------------------------------
if __name__ == "__main__":  # pragma: no cover

    logging.basicConfig(level=logging.INFO)

    # 测试依赖分析器
    logger.info("Testing dependency analyzer")

    analyzer = create_dependency_analyzer()

    # 测试从配置发现
    config_data = {
        "services": [
            {
                "id": "service_a",
                "name": "Service A",
                "dependencies": [
                    {"id": "service_b", "name": "Service B", "type": "sync"},
                    {"id": "database", "name": "Database", "type": "database"},
                ],
            },
            {
                "id": "service_b",
                "name": "Service B",
                "dependencies": [
                    {"id": "cache", "name": "Cache", "type": "cache"},
                ],
            },
        ],
    }

    topology = analyzer.discover_topology("config", config_data=config_data)

    logger.info(f"Discovered topology: {len(topology.nodes)} nodes, {len(topology.edges)} edges")

    # 测试依赖分析
    analysis = analyzer.analyze_dependencies("service_a")
    logger.info(f"Dependency analysis: {analysis}")

    # 测试健康报告
    health_report = analyzer.get_health_report()
    logger.info(f"Health report: {health_report}")

    logger.info("Test passed!")
