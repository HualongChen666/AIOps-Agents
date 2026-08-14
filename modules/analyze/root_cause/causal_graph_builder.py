# -*- coding: utf-8 -*-
"""
causal_graph_builder.py
----------------------
因果图谱构建器 - 将因果推断与现有系统集成。

功能：
- 从监控数据构建因果图
- 因果图可视化
- 因果图持久化
- 与现有 GNN 图构建器集成
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

from .causal_inference import (
    CausalDiscovery,
    CausalGraph,
    CausalRootCauseAnalyzer,
    create_causal_analyzer,
)
from .graph_builder import RootCauseGraphBuilder

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# 1️⃣ 因果图谱构建器
# ----------------------------------------------------------------------
class CausalGraphBuilder:
    """因果图谱构建器"""

    def __init__(
        self,
        discovery_method: str = "pc",
        discovery_params: Optional[Dict[str, Any]] = None,
    ):
        """
        Parameters
        ----------
        discovery_method : str
            因果发现方法：'pc', 'ges'
        discovery_params : Dict[str, Any], optional
            因果发现参数
        """
        self.discovery_method = discovery_method
        self.discovery_params = discovery_params or {}
        self.causal_graph: Optional[CausalGraph] = None
        self.analyzer: Optional[CausalRootCauseAnalyzer] = None
        self.node_metadata: Dict[str, Dict[str, Any]] = {}
        self.edge_metadata: Dict[Tuple[str, str], Dict[str, Any]] = {}

    def build_from_metrics(
        self,
        metrics_data: pd.DataFrame,
        service_mapping: Optional[Dict[str, str]] = None,
    ) -> CausalGraph:
        """
        从指标数据构建因果图

        Parameters
        ----------
        metrics_data : pd.DataFrame
            指标数据，列名为指标名称
        service_mapping : Dict[str, str], optional
            指标到服务的映射 {metric_name: service_id}

        Returns
        -------
        CausalGraph
            构建的因果图
        """
        logger.info(f"Building causal graph from {len(metrics_data.columns)} metrics")

        # 数据预处理
        clean_data = self._preprocess_metrics(metrics_data)

        # 因果发现
        if self.discovery_params:
            causal_graph = CausalDiscovery.pc_algorithm(clean_data, **self.discovery_params)
        else:
            causal_graph = CausalDiscovery.pc_algorithm(clean_data)

        self.causal_graph = causal_graph

        # 添加元数据
        if service_mapping:
            for metric in metrics_data.columns:
                if metric in service_mapping:
                    self.node_metadata[metric] = {
                        "type": "metric",
                        "service_id": service_mapping[metric],
                    }

        logger.info(
            f"Causal graph built: {len(causal_graph.nodes)} nodes, "
            f"{sum(len(v) for v in causal_graph.edges.values())} edges"
        )

        return causal_graph

    def build_from_logs(
        self,
        log_data: pd.DataFrame,
        feature_extractor: Optional[Any] = None,
    ) -> CausalGraph:
        """
        从日志数据构建因果图

        Parameters
        ----------
        log_data : pd.DataFrame
            日志数据
        feature_extractor : Any, optional
            特征提取器

        Returns
        -------
        CausalGraph
            构建的因果图
        """
        logger.info("Building causal graph from logs")

        # 提取日志特征
        if feature_extractor is not None:
            features = feature_extractor.extract(log_data)
        else:
            # 简化：使用日志级别和关键词频率
            features = self._extract_log_features(log_data)

        # 因果发现
        causal_graph = CausalDiscovery.pc_algorithm(features)

        self.causal_graph = causal_graph

        return causal_graph

    def build_from_traces(
        self,
        trace_data: pd.DataFrame,
    ) -> CausalGraph:
        """
        从追踪数据构建因果图

        Parameters
        ----------
        trace_data : pd.DataFrame
            追踪数据

        Returns
        -------
        CausalGraph
            构建的因果图
        """
        logger.info("Building causal graph from traces")

        # 提取追踪特征
        features = self._extract_trace_features(trace_data)

        # 因果发现
        causal_graph = CausalDiscovery.pc_algorithm(features)

        self.causal_graph = causal_graph

        return causal_graph

    def build_multimodal(
        self,
        metrics_data: Optional[pd.DataFrame] = None,
        log_data: Optional[pd.DataFrame] = None,
        trace_data: Optional[pd.DataFrame] = None,
    ) -> CausalGraph:
        """
        多模态因果图构建

        Parameters
        ----------
        metrics_data : pd.DataFrame, optional
            指标数据
        log_data : pd.DataFrame, optional
            日志数据
        trace_data : pd.DataFrame, optional
            追踪数据

        Returns
        -------
        CausalGraph
            构建的因果图
        """
        logger.info("Building multimodal causal graph")

        features_list = []
        feature_names = []

        if metrics_data is not None:
            clean_metrics = self._preprocess_metrics(metrics_data)
            features_list.append(clean_metrics)
            feature_names.extend([f"metric_{col}" for col in clean_metrics.columns])

        if log_data is not None:
            log_features = self._extract_log_features(log_data)
            features_list.append(log_features)
            feature_names.extend([f"log_{col}" for col in log_features.columns])

        if trace_data is not None:
            trace_features = self._extract_trace_features(trace_data)
            features_list.append(trace_features)
            feature_names.extend([f"trace_{col}" for col in trace_features.columns])

        # 合并特征
        combined_features = pd.concat(features_list, axis=1)
        combined_features.columns = feature_names

        # 因果发现
        causal_graph = CausalDiscovery.pc_algorithm(combined_features)

        self.causal_graph = causal_graph

        return causal_graph

    def _preprocess_metrics(self, data: pd.DataFrame) -> pd.DataFrame:
        """预处理指标数据"""
        # 处理缺失值
        data = data.ffill().fillna(0)

        # 标准化
        from sklearn.preprocessing import StandardScaler

        scaler = StandardScaler()
        scaled_data = pd.DataFrame(
            scaler.fit_transform(data),
            columns=data.columns,
            index=data.index,
        )

        return scaled_data

    def _extract_log_features(self, log_data: pd.DataFrame) -> pd.DataFrame:
        """提取日志特征"""
        features = pd.DataFrame()

        # 简化特征：日志级别编码
        if "level" in log_data.columns:
            level_map = {"DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 3, "CRITICAL": 4}
            features["log_level"] = log_data["level"].map(level_map).fillna(0)

        # 日志频率
        if "timestamp" in log_data.columns:
            log_data["timestamp"] = pd.to_datetime(log_data["timestamp"])
            features["log_frequency"] = log_data.groupby(
                log_data["timestamp"].dt.floor("1min")
            ).size()

        # 如果没有特征，创建默认特征
        if features.empty:
            features = pd.DataFrame({"log_count": [1]})

        return features.fillna(0)

    def _extract_trace_features(self, trace_data: pd.DataFrame) -> pd.DataFrame:
        """提取追踪特征"""
        features = pd.DataFrame()

        # 简化特征：延迟、错误率
        if "duration" in trace_data.columns:
            features["trace_duration"] = trace_data["duration"]

        if "error" in trace_data.columns:
            features["trace_error"] = trace_data["error"].astype(int)

        # 如果没有特征，创建默认特征
        if features.empty:
            features = pd.DataFrame({"trace_count": [1]})

        return features.fillna(0)

    def get_analyzer(self) -> CausalRootCauseAnalyzer:
        """获取因果分析器"""
        if self.causal_graph is None:
            raise RuntimeError("Causal graph not built. Call build_from_*() first.")

        if self.analyzer is None:
            self.analyzer = create_causal_analyzer(
                discovery_method=self.discovery_method,
                use_counterfactual=True,
            )
            self.analyzer.causal_graph = self.causal_graph
            if self.analyzer.do_calculus is not None:
                self.analyzer.do_calculus = self.analyzer.do_calculus.__class__(self.causal_graph)
            if self.analyzer.use_counterfactual and self.analyzer.counterfactual is not None:
                self.analyzer.counterfactual = self.analyzer.counterfactual.__class__(
                    self.causal_graph
                )

        return self.analyzer


# ----------------------------------------------------------------------
# 2️⃣ 因果图可视化
# ----------------------------------------------------------------------
class CausalGraphVisualizer:
    """因果图可视化"""

    @staticmethod
    def to_networkx(causal_graph: CausalGraph) -> Any:
        """转换为 NetworkX 图"""
        try:
            import networkx as nx
        except ImportError:
            raise ImportError("NetworkX is required for visualization")

        nx_graph = nx.DiGraph()

        # 添加节点
        for node in causal_graph.nodes:
            nx_graph.add_node(node)

        # 添加边
        for parent, children in causal_graph.edges.items():
            for child in children:
                weight = causal_graph.edge_weights.get((parent, child), 1.0)
                nx_graph.add_edge(parent, child, weight=weight)

        return nx_graph

    @staticmethod
    def plot(
        causal_graph: CausalGraph,
        output_path: Optional[str] = None,
        figsize: Tuple[int, int] = (12, 8),
    ):
        """
        绘制因果图

        Parameters
        ----------
        causal_graph : CausalGraph
            因果图
        output_path : str, optional
            输出路径
        figsize : Tuple[int, int]
            图形大小
        """
        try:
            import matplotlib.pyplot as plt
            import networkx as nx
        except ImportError:
            raise ImportError("Matplotlib and NetworkX are required for visualization")

        nx_graph = CausalGraphVisualizer.to_networkx(causal_graph)

        plt.figure(figsize=figsize)

        # 使用 spring 布局
        pos = nx.spring_layout(nx_graph, k=1, iterations=50)

        # 绘制节点
        nx.draw_networkx_nodes(nx_graph, pos, node_size=500, node_color="lightblue")

        # 绘制边
        nx.draw_networkx_edges(nx_graph, pos, edge_color="gray", arrows=True)

        # 绘制标签
        nx.draw_networkx_labels(nx_graph, pos, font_size=10)

        # 绘制边权重
        edge_labels = nx.get_edge_attributes(nx_graph, "weight")
        nx.draw_networkx_edge_labels(nx_graph, pos, edge_labels)

        plt.title("Causal Graph")
        plt.axis("off")

        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches="tight")
            logger.info(f"Graph saved to {output_path}")
        else:
            plt.show()

        plt.close()

    @staticmethod
    def to_json(causal_graph: CausalGraph) -> str:
        """转换为 JSON"""
        data = {
            "nodes": list(causal_graph.nodes),
            "edges": [
                {
                    "source": parent,
                    "target": child,
                    "weight": causal_graph.edge_weights.get((parent, child), 1.0),
                }
                for parent, children in causal_graph.edges.items()
                for child in children
            ],
        }
        return json.dumps(data, indent=2)

    @staticmethod
    def from_json(json_str: str) -> CausalGraph:
        """从 JSON 加载因果图"""
        data = json.loads(json_str)

        causal_graph = CausalGraph()

        for node in data["nodes"]:
            causal_graph.add_node(node)

        for edge in data["edges"]:
            causal_graph.add_edge(
                edge["source"],
                edge["target"],
                edge.get("weight", 1.0),
            )

        return causal_graph


# ----------------------------------------------------------------------
# 3️⃣ 因果图持久化
# ----------------------------------------------------------------------
class CausalGraphPersistence:
    """因果图持久化"""

    @staticmethod
    def save(
        causal_graph: CausalGraph,
        path: Union[str, Path],
        format: str = "json",
    ):
        """
        保存因果图

        Parameters
        ----------
        causal_graph : CausalGraph
            因果图
        path : Union[str, Path]
            保存路径
        format : str
            格式：'json', 'pickle'（不推荐，存在安全风险）
        """
        path = Path(path)

        # 安全检查：防止路径遍历攻击
        path = path.resolve()

        # 确保路径在允许的目录内
        allowed_dirs = [Path.cwd(), Path.home() / ".aiops"]
        if not any(str(path).startswith(str(d.resolve())) for d in allowed_dirs):
            logger.error(f"Invalid save path (outside allowed directories): {path}")
            raise ValueError(f"Invalid save path: {path}")

        path.parent.mkdir(parents=True, exist_ok=True)

        if format == "json":
            json_str = CausalGraphVisualizer.to_json(causal_graph)
            path.write_text(json_str)
        elif format == "pickle":
            import pickle

            logger.warning("Pickle format is not recommended due to security risks")
            with open(path, "wb") as f:
                pickle.dump(causal_graph, f)
        else:
            raise ValueError(f"Unknown format: {format}")

        logger.info(f"Causal graph saved to {path}")

    @staticmethod
    def load(
        path: Union[str, Path],
        format: str = "json",
    ) -> CausalGraph:
        """
        加载因果图

        Parameters
        ----------
        path : Union[str, Path]
            文件路径
        format : str
            格式：'json', 'pickle'（不推荐，存在安全风险）

        Returns
        -------
        CausalGraph
            因果图
        """
        path = Path(path)

        # 安全检查：防止路径遍历攻击
        path = path.resolve()
        allowed_dirs = [Path.cwd(), Path.home() / ".aiops"]
        if not any(str(path).startswith(str(d.resolve())) for d in allowed_dirs):
            logger.error(f"Invalid load path (outside allowed directories): {path}")
            raise ValueError(f"Invalid load path: {path}")

        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        if format == "json":
            json_str = path.read_text()
            return CausalGraphVisualizer.from_json(json_str)
        elif format == "pickle":
            import pickle

            logger.warning("Pickle format is not recommended due to security risks")
            with open(path, "rb") as f:
                result = pickle.load(f)
                if not isinstance(result, CausalGraph):
                    raise TypeError(f"Expected CausalGraph, got {type(result)}")
                return result
        else:
            raise ValueError(f"Unknown format: {format}")


# ----------------------------------------------------------------------
# 4️⃣ 与现有系统集成
# ----------------------------------------------------------------------
class CausalGraphIntegrator:
    """因果图与现有系统集成"""

    def __init__(
        self,
        graph_builder: RootCauseGraphBuilder,
        causal_builder: CausalGraphBuilder,
    ):
        """
        Parameters
        ----------
        graph_builder : RootCauseGraphBuilder
            现有图构建器
        causal_builder : CausalGraphBuilder
            因果图构建器
        """
        self.graph_builder = graph_builder
        self.causal_builder = causal_builder

    def build_integrated_graph(
        self,
        alerts: List[Dict[str, Any]],
        services: List[Dict[str, Any]],
        metrics: List[Dict[str, Any]],
        dependencies: List[Dict[str, Any]],
        metrics_data: pd.DataFrame,
    ) -> Tuple[Any, CausalGraph]:
        """
        构建集成图

        Returns
        -------
        graph_builder_graph : Any
            现有图构建器的图
        causal_graph : CausalGraph
            因果图
        """
        # 构建现有图
        from .inference import RootCauseInference

        inference = RootCauseInference(self.graph_builder)
        inference.build_graph_from_alerts(alerts, services, metrics, dependencies)

        # 构建因果图
        causal_graph = self.causal_builder.build_from_metrics(metrics_data)

        return self.graph_builder.graph, causal_graph

    def merge_graphs(
        self,
        nx_graph: Any,
        causal_graph: CausalGraph,
    ) -> Any:
        """
        合并两个图

        Parameters
        ----------
        nx_graph : Any
            NetworkX 图
        causal_graph : CausalGraph
            因果图

        Returns
        -------
        merged_graph : Any
            合并后的图
        """
        try:
            import networkx  # noqa: F401
        except ImportError:
            raise ImportError("NetworkX is required")

        merged = nx_graph.copy()

        # 添加因果图的边
        for parent, children in causal_graph.edges.items():
            for child in children:
                if parent in merged.nodes and child in merged.nodes:
                    weight = causal_graph.edge_weights.get((parent, child), 1.0)
                    if merged.has_edge(parent, child):
                        # 合并权重
                        merged[parent][child]["weight"] = (
                            merged[parent][child].get("weight", 1.0) + weight
                        ) / 2
                    else:
                        merged.add_edge(parent, child, weight=weight, type="causal")

        return merged


# ----------------------------------------------------------------------
# 5️⃣ 工厂函数
# ----------------------------------------------------------------------
def create_causal_graph_builder(
    discovery_method: str = "pc",
    discovery_params: Optional[Dict[str, Any]] = None,
) -> CausalGraphBuilder:
    """创建因果图构建器"""
    return CausalGraphBuilder(
        discovery_method=discovery_method,
        discovery_params=discovery_params,
    )


# ----------------------------------------------------------------------
# 6️⃣ CLI 用于快速测试
# ----------------------------------------------------------------------
if __name__ == "__main__":  # pragma: no cover

    logging.basicConfig(level=logging.INFO)

    # 生成测试数据
    logger.info("Creating test data")
    np.random.seed(42)
    n_samples = 1000

    X = np.random.randn(n_samples)
    Y = 0.5 * X + np.random.randn(n_samples) * 0.5
    Z = 0.3 * Y + np.random.randn(n_samples) * 0.7

    metrics_data = pd.DataFrame(
        {
            "service_A": X,
            "service_B": Y,
            "service_C": Z,
        }
    )

    # 测试因果图构建
    logger.info("Testing causal graph builder")
    builder = create_causal_graph_builder()
    causal_graph = builder.build_from_metrics(metrics_data)

    logger.info(f"Causal graph: {len(causal_graph.nodes)} nodes")

    # 测试可视化
    logger.info("Testing visualization")
    visualizer = CausalGraphVisualizer()
    json_str = visualizer.to_json(causal_graph)
    logger.info(f"JSON output: {json_str[:200]}...")

    # 测试持久化
    logger.info("Testing persistence")
    CausalGraphPersistence.save(causal_graph, "test_causal_graph.json")
    loaded_graph = CausalGraphPersistence.load("test_causal_graph.json")
    logger.info(f"Loaded graph: {len(loaded_graph.nodes)} nodes")

    # 清理
    Path("test_causal_graph.json").unlink()

    logger.info("Test passed!")
