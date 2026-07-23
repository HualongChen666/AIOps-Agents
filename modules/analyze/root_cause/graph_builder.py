# -*- coding: utf-8 -*-
"""
Root Cause Graph Builder
根因推断图构建器，构建异构图用于GNN分析

功能:
- 构建服务拓扑图
- 添加时序指标节点
- 添加告警节点
- 构建异构边关系
- 图特征提取
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple  # noqa: F401

try:
    import networkx as nx

    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False
    nx = None

logger = logging.getLogger(__name__)


class RootCauseGraphBuilder:
    """
    根因推断图构建器

    构建包含服务、指标、告警等节点的异构图，
    用于后续的GNN根因推断。

    参数:
        directed: 是否为有向图，默认True
        multi_graph: 是否允许多重边，默认True
    """

    # 节点类型定义
    NODE_TYPE_SERVICE = "service"
    NODE_TYPE_METRIC = "metric"
    NODE_TYPE_ALERT = "alert"
    NODE_TYPE_HOST = "host"
    NODE_TYPE_CONTAINER = "container"

    # 边类型定义
    EDGE_TYPE_DEPENDS = "depends_on"
    EDGE_TYPE_CONTAINS = "contains"
    EDGE_TYPE_CORRELATES = "correlates"
    EDGE_TYPE_CAUSES = "causes"
    EDGE_TYPE_AFFECTS = "affects"

    def __init__(self, directed: bool = True, multi_graph: bool = True):
        if not NETWORKX_AVAILABLE:
            raise ImportError("networkx is not installed. Install with: pip install networkx")

        self.directed = directed
        self.multi_graph = multi_graph

        if multi_graph:
            self.graph = nx.MultiDiGraph() if directed else nx.MultiGraph()
        else:
            self.graph = nx.DiGraph() if directed else nx.Graph()

        self.node_counter = 0
        self.edge_counter = 0

    def add_service_node(
        self,
        service_id: str,
        service_name: str,
        service_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        添加服务节点

        参数:
            service_id: 服务唯一标识
            service_name: 服务名称
            service_type: 服务类型（microservice, database, cache等）
            metadata: 额外元数据

        返回:
            节点ID
        """
        node_id = f"service_{service_id}"

        self.graph.add_node(
            node_id,
            node_type=self.NODE_TYPE_SERVICE,
            service_id=service_id,
            service_name=service_name,
            service_type=service_type,
            metadata=metadata or {},
            created_at=datetime.now().isoformat(),
        )

        self.node_counter += 1
        logger.debug("Added service node: %s", node_id)

        return node_id

    def add_metric_node(
        self,
        metric_id: str,
        metric_name: str,
        metric_type: str,
        service_id: str,
        current_value: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        添加指标节点

        参数:
            metric_id: 指标唯一标识
            metric_name: 指标名称
            metric_type: 指标类型（cpu, memory, latency等）
            service_id: 关联的服务ID
            current_value: 当前值
            metadata: 额外元数据

        返回:
            节点ID
        """
        node_id = f"metric_{metric_id}"

        self.graph.add_node(
            node_id,
            node_type=self.NODE_TYPE_METRIC,
            metric_id=metric_id,
            metric_name=metric_name,
            metric_type=metric_type,
            service_id=service_id,
            current_value=current_value,
            metadata=metadata or {},
            created_at=datetime.now().isoformat(),
        )

        self.node_counter += 1
        logger.debug("Added metric node: %s", node_id)

        return node_id

    def add_alert_node(
        self,
        alert_id: str,
        alert_title: str,
        alert_severity: str,
        service_id: str,
        metric_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        添加告警节点

        参数:
            alert_id: 告警唯一标识
            alert_title: 告警标题
            alert_severity: 告警严重级别（critical, warning, info）
            service_id: 关联的服务ID
            metric_id: 关联的指标ID
            metadata: 额外元数据

        返回:
            节点ID
        """
        node_id = f"alert_{alert_id}"

        self.graph.add_node(
            node_id,
            node_type=self.NODE_TYPE_ALERT,
            alert_id=alert_id,
            alert_title=alert_title,
            alert_severity=alert_severity,
            service_id=service_id,
            metric_id=metric_id,
            metadata=metadata or {},
            created_at=datetime.now().isoformat(),
        )

        self.node_counter += 1
        logger.debug("Added alert node: %s", node_id)

        return node_id

    def add_host_node(
        self,
        host_id: str,
        host_name: str,
        host_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        添加主机节点

        参数:
            host_id: 主机唯一标识
            host_name: 主机名称
            host_type: 主机类型（vm, baremetal, container等）
            metadata: 额外元数据

        返回:
            节点ID
        """
        node_id = f"host_{host_id}"

        self.graph.add_node(
            node_id,
            node_type=self.NODE_TYPE_HOST,
            host_id=host_id,
            host_name=host_name,
            host_type=host_type,
            metadata=metadata or {},
            created_at=datetime.now().isoformat(),
        )

        self.node_counter += 1
        logger.debug("Added host node: %s", node_id)

        return node_id

    def add_container_node(
        self,
        container_id: str,
        container_name: str,
        host_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        添加容器节点

        参数:
            container_id: 容器唯一标识
            container_name: 容器名称
            host_id: 关联的主机ID
            metadata: 额外元数据

        返回:
            节点ID
        """
        node_id = f"container_{container_id}"

        self.graph.add_node(
            node_id,
            node_type=self.NODE_TYPE_CONTAINER,
            container_id=container_id,
            container_name=container_name,
            host_id=host_id,
            metadata=metadata or {},
            created_at=datetime.now().isoformat(),
        )

        self.node_counter += 1
        logger.debug("Added container node: %s", node_id)

        return node_id

    def add_dependency_edge(
        self,
        source_id: str,
        target_id: str,
        dependency_type: str = "service",
        weight: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        添加依赖关系边

        参数:
            source_id: 源节点ID
            target_id: 目标节点ID
            dependency_type: 依赖类型
            weight: 边权重
            metadata: 额外元数据
        """
        self.graph.add_edge(
            source_id,
            target_id,
            edge_type=self.EDGE_TYPE_DEPENDS,
            dependency_type=dependency_type,
            weight=weight,
            metadata=metadata or {},
            created_at=datetime.now().isoformat(),
        )

        self.edge_counter += 1
        logger.debug("Added dependency edge: %s -> %s", source_id, target_id)

    def add_containment_edge(
        self,
        parent_id: str,
        child_id: str,
        containment_type: str = "host",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        添加包含关系边

        参数:
            parent_id: 父节点ID
            child_id: 子节点ID
            containment_type: 包含类型
            metadata: 额外元数据
        """
        self.graph.add_edge(
            parent_id,
            child_id,
            edge_type=self.EDGE_TYPE_CONTAINS,
            containment_type=containment_type,
            weight=1.0,
            metadata=metadata or {},
            created_at=datetime.now().isoformat(),
        )

        self.edge_counter += 1
        logger.debug("Added containment edge: %s -> %s", parent_id, child_id)

    def add_correlation_edge(
        self,
        metric_id_1: str,
        metric_id_2: str,
        correlation_coefficient: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        添加相关性边

        参数:
            metric_id_1: 指标1节点ID
            metric_id_2: 指标2节点ID
            correlation_coefficient: 相关系数
            metadata: 额外元数据
        """
        self.graph.add_edge(
            metric_id_1,
            metric_id_2,
            edge_type=self.EDGE_TYPE_CORRELATES,
            correlation_coefficient=correlation_coefficient,
            weight=abs(correlation_coefficient),
            metadata=metadata or {},
            created_at=datetime.now().isoformat(),
        )

        self.edge_counter += 1
        logger.debug("Added correlation edge: %s <-> %s", metric_id_1, metric_id_2)

    def add_causal_edge(
        self,
        cause_id: str,
        effect_id: str,
        confidence: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        添加因果关系边

        参数:
            cause_id: 原因节点ID
            effect_id: 结果节点ID
            confidence: 置信度
            metadata: 额外元数据
        """
        self.graph.add_edge(
            cause_id,
            effect_id,
            edge_type=self.EDGE_TYPE_CAUSES,
            confidence=confidence,
            weight=confidence,
            metadata=metadata or {},
            created_at=datetime.now().isoformat(),
        )

        self.edge_counter += 1
        logger.debug("Added causal edge: %s -> %s", cause_id, effect_id)

    def get_subgraph_by_alert(self, alert_id: str, hops: int = 3) -> Dict[str, Any]:
        """
        获取告警相关的子图

        参数:
            alert_id: 告警ID
            hops: 跳数

        返回:
            子图数据
        """
        alert_node_id = f"alert_{alert_id}"

        if alert_node_id not in self.graph:
            raise ValueError(f"Alert node {alert_node_id} not found in graph")

        # 获取hops跳内的所有节点
        nodes = {alert_node_id}
        current_level = {alert_node_id}

        for _ in range(hops):
            next_level = set()
            for node in current_level:
                neighbors = set(self.graph.neighbors(node))
                next_level.update(neighbors)
            nodes.update(next_level)
            current_level = next_level

        # 提取子图
        subgraph = self.graph.subgraph(nodes)

        return self._graph_to_dict(subgraph)

    def get_node_neighbors(
        self, node_id: str, edge_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取节点的邻居

        参数:
            node_id: 节点ID
            edge_type: 边类型过滤

        返回:
            邻居节点列表
        """
        if node_id not in self.graph:
            raise ValueError(f"Node {node_id} not found in graph")

        neighbors = []

        for neighbor in self.graph.neighbors(node_id):
            edge_data = self.graph.get_edge_data(node_id, neighbor)

            # 如果是多图，edge_data是字典
            if self.multi_graph:
                edge_list = edge_data.values() if edge_data else []
            else:
                edge_list = [edge_data] if edge_data else []

            for edge in edge_list:
                if edge_type is None or edge.get("edge_type") == edge_type:
                    neighbor_data = self.graph.nodes[neighbor].copy()
                    neighbor_data["edge_data"] = edge
                    neighbors.append(neighbor_data)

        return neighbors

    def compute_node_importance(self, method: str = "pagerank") -> Dict[str, float]:
        """
        计算节点重要性

        参数:
            method: 计算方法（pagerank, betweenness, degree）

        返回:
            节点重要性字典
        """
        if method == "pagerank":
            importance: Dict[str, float] = nx.pagerank(self.graph)
        elif method == "betweenness":
            importance = nx.betweenness_centrality(self.graph)
        elif method == "degree":
            importance = dict(self.graph.degree())
        else:
            raise ValueError(f"Unknown importance method: {method}")

        return importance

    def find_shortest_path(self, source_id: str, target_id: str) -> List[str]:
        """
        查找最短路径

        参数:
            source_id: 源节点ID
            target_id: 目标节点ID

        返回:
            路径节点ID列表
        """
        if source_id not in self.graph:
            raise ValueError(f"Source node {source_id} not found")
        if target_id not in self.graph:
            raise ValueError(f"Target node {target_id} not found")

        try:
            path: List[str] = nx.shortest_path(self.graph, source_id, target_id)
            return path
        except nx.NetworkXNoPath:
            return []

    def _graph_to_dict(self, graph: nx.Graph) -> Dict[str, Any]:
        """
        将NetworkX图转换为字典格式

        参数:
            graph: NetworkX图对象

        返回:
            图字典
        """
        nodes = []
        for node_id, node_data in graph.nodes(data=True):
            nodes.append(
                {
                    "id": node_id,
                    **node_data,
                }
            )

        edges = []
        for source, target, edge_data in graph.edges(data=True):
            edges.append(
                {
                    "source": source,
                    "target": target,
                    **edge_data,
                }
            )

        return {
            "nodes": nodes,
            "edges": edges,
            "node_count": len(nodes),
            "edge_count": len(edges),
        }

    def to_dict(self) -> Dict[str, Any]:
        """
        将整个图转换为字典格式

        返回:
            图字典
        """
        return self._graph_to_dict(self.graph)

    def to_json(self) -> str:
        """
        将图序列化为JSON字符串

        返回:
            JSON字符串
        """
        return json.dumps(self.to_dict(), indent=2)

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取图统计信息

        返回:
            统计信息字典
        """
        node_types: Dict[str, int] = {}
        for node_data in self.graph.nodes.values():
            node_type = node_data.get("node_type", "unknown")
            node_types[node_type] = node_types.get(node_type, 0) + 1

        edge_types: Dict[str, int] = {}
        for _, _, edge_data in self.graph.edges(data=True):
            edge_type = edge_data.get("edge_type", "unknown")
            edge_types[edge_type] = edge_types.get(edge_type, 0) + 1

        return {
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges(),
            "node_types": node_types,
            "edge_types": edge_types,
            "is_directed": self.directed,
            "is_multi_graph": self.multi_graph,
        }

    def save_graph(self, path: str) -> None:
        """保存图到文件"""
        import pickle

        with open(path, "wb") as f:
            pickle.dump(self.graph, f)
        logger.info("Graph saved to %s", path)

    def load_graph(self, path: str) -> None:
        """从文件加载图"""
        import pickle

        with open(path, "rb") as f:
            self.graph = pickle.load(f)
        self.node_counter = self.graph.number_of_nodes()
        self.edge_counter = self.graph.number_of_edges()
        logger.info("Graph loaded from %s", path)
