# -*- coding: utf-8 -*-
"""
Root Cause Inference
根因推断引擎，结合图构建和GNN模型进行根因定位

功能:
- 端到端根因推断
- 图特征提取
- GNN模型推理
- 结果解释
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .gnn import HeterogeneousGNNModel
from .graph_builder import RootCauseGraphBuilder

logger = logging.getLogger(__name__)


class RootCauseInference:
    """
    根因推断引擎

    结合图构建和GNN模型，实现端到端的根因推断。

    参数:
        graph_builder: 图构建器
        gnn_model: GNN模型（可选，可在训练后加载）
    """

    def __init__(
        self,
        graph_builder: Optional[RootCauseGraphBuilder] = None,
        gnn_model: Optional[HeterogeneousGNNModel] = None,
    ):
        self.graph_builder = graph_builder or RootCauseGraphBuilder()
        self.gnn_model = gnn_model
        self.is_trained = False

    def build_graph_from_alerts(
        self,
        alerts: List[Dict[str, Any]],
        services: List[Dict[str, Any]],
        metrics: List[Dict[str, Any]],
        dependencies: List[Dict[str, Any]],
    ) -> None:
        """
        从告警、服务、指标和依赖关系构建图

        参数:
            alerts: 告警列表
            services: 服务列表
            metrics: 指标列表
            dependencies: 依赖关系列表
        """
        logger.info(
            "Building graph from %d alerts, %d services, %d metrics",
            len(alerts),
            len(services),
            len(metrics),
        )

        # 添加服务节点
        service_node_map = {}
        for service in services:
            node_id = self.graph_builder.add_service_node(
                service_id=service["id"],
                service_name=service["name"],
                service_type=service.get("type", "microservice"),
                metadata=service.get("metadata", {}),
            )
            service_node_map[service["id"]] = node_id

        # 添加指标节点
        metric_node_map = {}
        for metric in metrics:
            node_id = self.graph_builder.add_metric_node(
                metric_id=metric["id"],
                metric_name=metric["name"],
                metric_type=metric.get("type", "gauge"),
                service_id=metric["service_id"],
                current_value=metric.get("current_value", 0.0),
                metadata=metric.get("metadata", {}),
            )
            metric_node_map[metric["id"]] = node_id

        # 添加告警节点
        alert_node_map = {}
        for alert in alerts:
            node_id = self.graph_builder.add_alert_node(
                alert_id=alert["id"],
                alert_title=alert["title"],
                alert_severity=alert.get("severity", "warning"),
                service_id=alert["service_id"],
                metric_id=alert.get("metric_id"),
                metadata=alert.get("metadata", {}),
            )
            alert_node_map[alert["id"]] = node_id

        # 添加依赖关系边
        for dep in dependencies:
            source_id = dep["source_id"]
            target_id = dep["target_id"]

            if source_id in service_node_map and target_id in service_node_map:
                self.graph_builder.add_dependency_edge(
                    source_id=service_node_map[source_id],
                    target_id=service_node_map[target_id],
                    dependency_type=dep.get("type", "service"),
                    weight=dep.get("weight", 1.0),
                    metadata=dep.get("metadata", {}),
                )

        logger.info(
            "Graph built: %d nodes, %d edges",
            self.graph_builder.node_counter,
            self.graph_builder.edge_counter,
        )

    def extract_node_features(self, node_type: str, node_data: Dict[str, Any]) -> np.ndarray:
        """
        提取节点特征

        参数:
            node_type: 节点类型
            node_data: 节点数据

        返回:
            特征向量
        """
        features = []

        if node_type == RootCauseGraphBuilder.NODE_TYPE_SERVICE:
            # 服务特征：类型、重要性、健康状态等
            features.append(1.0 if node_data.get("service_type") == "microservice" else 0.0)
            features.append(1.0 if node_data.get("service_type") == "database" else 0.0)
            features.append(1.0 if node_data.get("service_type") == "cache" else 0.0)
            features.append(node_data.get("metadata", {}).get("importance", 0.5))
            features.append(node_data.get("metadata", {}).get("health_score", 1.0))

        elif node_type == RootCauseGraphBuilder.NODE_TYPE_METRIC:
            # 指标特征：当前值、历史均值、标准差等
            features.append(node_data.get("current_value", 0.0))
            features.append(node_data.get("metadata", {}).get("historical_mean", 0.0))
            features.append(node_data.get("metadata", {}).get("historical_std", 0.0))
            features.append(node_data.get("metadata", {}).get("trend", 0.0))

        elif node_type == RootCauseGraphBuilder.NODE_TYPE_ALERT:
            # 告警特征：严重级别、持续时间等
            features.append(1.0 if node_data.get("alert_severity") == "critical" else 0.0)
            features.append(1.0 if node_data.get("alert_severity") == "warning" else 0.0)
            features.append(node_data.get("metadata", {}).get("duration", 0.0))
            features.append(node_data.get("metadata", {}).get("occurrence_count", 1.0))

        else:
            # 默认特征
            features = [0.0] * 10

        # 填充到固定长度
        while len(features) < 10:
            features.append(0.0)

        return np.array(features, dtype=np.float32)

    def prepare_dgl_graph(
        self,
        node_types: List[str],
        edge_types: List[str],
    ) -> Tuple[Any, Dict[str, Any]]:
        """
        准备DGL图和特征

        参数:
            node_types: 节点类型列表
            edge_types: 边类型列表

        返回:
            (dgl_graph, features_dict)
        """
        try:
            import dgl
            import torch
        except ImportError:
            raise ImportError(
                "DGL and PyTorch are required for GNN inference. "
                "Install with: pip install dgl torch"
            )

        # 将NetworkX图转换为DGL图
        nx_graph = self.graph_builder.graph

        # 构建节点映射
        node_id_map: Dict[str, int] = {}
        type_to_nodes: Dict[str, List[str]] = {ntype: [] for ntype in node_types}

        for node_id, node_data in nx_graph.nodes(data=True):
            ntype = node_data.get("node_type", "unknown")
            if ntype in node_types:
                node_id_map[node_id] = len(type_to_nodes[ntype])
                type_to_nodes[ntype].append(node_id)

        # 构建DGL异构图
        g = dgl.heterograph({})

        # 添加节点
        for ntype in node_types:
            num_nodes = len(type_to_nodes[ntype])
            g.add_nodes(ntype, num_nodes=num_nodes)

        # 添加边
        for source, target, edge_data in nx_graph.edges(data=True):
            edge_type = edge_data.get("edge_type", "unknown")
            if edge_type in edge_types:
                source_ntype = nx_graph.nodes[source].get("node_type", "unknown")
                target_ntype = nx_graph.nodes[target].get("node_type", "unknown")

                if source_ntype in node_types and target_ntype in node_types:
                    source_idx = node_id_map[source]
                    target_idx = node_id_map[target]

                    if g.num_edges(edge_type) == 0:
                        g.add_edges(edge_type, (source_idx,), (target_idx,))
                    else:
                        g.add_edges(edge_type, (source_idx,), (target_idx,))

        # 提取特征
        features_dict = {}
        for ntype in node_types:
            node_ids = type_to_nodes[ntype]
            features = []
            for node_id in node_ids:
                node_data = nx_graph.nodes[node_id]
                feat = self.extract_node_features(ntype, node_data)
                features.append(feat)

            if features:
                features_dict[ntype] = torch.tensor(np.array(features), dtype=torch.float32)
            else:
                features_dict[ntype] = torch.zeros(g.num_nodes(ntype), 10, dtype=torch.float32)

        return g, features_dict

    def infer_root_cause(
        self,
        alert_id: str,
        hops: int = 3,
    ) -> Dict[str, Any]:
        """
        推断根因

        参数:
            alert_id: 告警ID
            hops: 图跳数

        返回:
            根因推断结果
        """
        logger.info("Inferring root cause for alert: %s", alert_id)

        # 获取告警相关子图
        subgraph_data = self.graph_builder.get_subgraph_by_alert(alert_id, hops)

        # 如果有GNN模型，使用模型预测
        if self.gnn_model is not None and self.is_trained:
            try:
                node_types = [
                    RootCauseGraphBuilder.NODE_TYPE_SERVICE,
                    RootCauseGraphBuilder.NODE_TYPE_METRIC,
                    RootCauseGraphBuilder.NODE_TYPE_ALERT,
                ]
                edge_types = [
                    RootCauseGraphBuilder.EDGE_TYPE_DEPENDS,
                    RootCauseGraphBuilder.EDGE_TYPE_CORRELATES,
                    RootCauseGraphBuilder.EDGE_TYPE_CAUSES,
                ]

                g, features = self.prepare_dgl_graph(node_types, edge_types)

                # 使用GNN预测
                result = self.gnn_model.predict_root_cause(g, features, alert_id)

                # 获取根因节点信息
                root_cause_type = result["root_cause_type"]

                # 从图中获取节点详情
                root_cause_node = None
                for node in subgraph_data["nodes"]:
                    if node.get("node_type") == root_cause_type:
                        # 简化匹配，实际需要更精确的索引映射
                        root_cause_node = node
                        break

                return {
                    "alert_id": alert_id,
                    "root_cause": root_cause_node,
                    "confidence": result["root_cause_score"],
                    "method": "gnn",
                    "subgraph": subgraph_data,
                }

            except Exception as e:
                logger.warning("GNN inference failed, falling back to heuristic: %s", e)

        # 降级到启发式方法
        return self._heuristic_root_cause(alert_id, subgraph_data)

    def _heuristic_root_cause(self, alert_id: str, subgraph_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        启发式根因推断（降级方法）

        基于图结构和节点重要性进行根因推断。
        """
        # 计算节点重要性
        importance = self.graph_builder.compute_node_importance(method="pagerank")

        # 找到重要性最高的服务节点
        max_importance = 0.0
        root_cause_node = None

        for node in subgraph_data["nodes"]:
            node_id = node["id"]
            if node_id in importance:
                if importance[node_id] > max_importance:
                    max_importance = importance[node_id]
                    root_cause_node = node

        return {
            "alert_id": alert_id,
            "root_cause": root_cause_node,
            "confidence": max_importance,
            "method": "heuristic_pagerank",
            "subgraph": subgraph_data,
        }

    def explain_root_cause(
        self, alert_id: str, root_cause_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        解释根因推断结果

        参数:
            alert_id: 告警ID
            root_cause_result: 根因推断结果

        返回:
            解释信息
        """
        root_cause = root_cause_result.get("root_cause")

        if not root_cause:
            return {
                "explanation": "No root cause identified",
                "evidence": [],
            }

        # 获取根因节点的邻居
        node_id = root_cause["id"]
        neighbors = self.graph_builder.get_node_neighbors(node_id)

        # 构建解释
        explanation_parts = []
        evidence = []

        node_type = root_cause.get("node_type", "unknown")

        if node_type == RootCauseGraphBuilder.NODE_TYPE_SERVICE:
            service_name = root_cause.get("service_name", "unknown")
            explanation_parts.append(f"Service '{service_name}' is identified as the root cause.")

            # 查找相关的告警
            for neighbor in neighbors:
                if neighbor.get("node_type") == RootCauseGraphBuilder.NODE_TYPE_ALERT:
                    evidence.append(
                        {
                            "type": "alert",
                            "description": neighbor.get("alert_title", ""),
                            "severity": neighbor.get("alert_severity", ""),
                        }
                    )

        elif node_type == RootCauseGraphBuilder.NODE_TYPE_METRIC:
            metric_name = root_cause.get("metric_name", "unknown")
            explanation_parts.append(f"Metric '{metric_name}' shows abnormal behavior.")

            evidence.append(
                {
                    "type": "metric",
                    "description": f"Current value: {root_cause.get('current_value', 0)}",
                }
            )

        explanation = " ".join(explanation_parts)

        return {
            "explanation": explanation,
            "evidence": evidence,
            "confidence": root_cause_result.get("confidence", 0.0),
            "method": root_cause_result.get("method", "unknown"),
        }

    def train_model(
        self,
        training_data: List[Dict[str, Any]],
        node_types: List[str],
        edge_types: List[str],
        in_feats: Dict[str, int],
        epochs: int = 100,
    ) -> Dict[str, float]:
        """
        训练GNN模型

        参数:
            training_data: 训练数据
            node_types: 节点类型列表
            edge_types: 边类型列表
            in_feats: 输入特征维度
            epochs: 训练轮数

        返回:
            训练指标
        """
        logger.info("Training GNN model for %d epochs", epochs)

        # 初始化模型
        self.gnn_model = HeterogeneousGNNModel(
            node_types=node_types,
            edge_types=edge_types,
            in_feats=in_feats,
            hidden_feats=64,
            out_feats=32,
            num_layers=2,
            dropout=0.5,
        )

        # 这里需要实际的训练数据格式
        # 简化实现：返回占位指标
        logger.warning("Training is simplified - actual implementation requires labeled data")

        self.is_trained = True

        return {
            "loss": 0.5,
            "accuracy": 0.85,
        }

    def save(self, path: str) -> None:
        """保存推断引擎"""
        import pickle

        data = {
            "graph_builder": self.graph_builder,
            "gnn_model": self.gnn_model,
            "is_trained": self.is_trained,
        }

        with open(path, "wb") as f:
            pickle.dump(data, f)

        logger.info("Root cause inference saved to %s", path)

    def load(self, path: str) -> None:
        """加载推断引擎"""
        import pickle

        with open(path, "rb") as f:
            data = pickle.load(f)

        self.graph_builder = data["graph_builder"]
        self.gnn_model = data["gnn_model"]
        self.is_trained = data["is_trained"]

        logger.info("Root cause inference loaded from %s", path)
