# -*- coding: utf-8 -*-
"""
L3 Processing Layer - Causal Graph
Provides causal analysis and root cause propagation modeling

Phase 4 集成: 完整的因果图分析、PC/GES算法、根因推断、影响分析、预测性分析
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union

from loguru import logger

# Define local CausalStrength enum for fallback (defined before import to avoid redefinition)


class _FallbackCausalStrength(str, Enum):
    """Strength of causal relationship (fallback)"""

    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"


# Create a component CausalEdge class for type checking when import fails
class _FallbackCausalEdge:
    """Fallback CausalEdge for type checking when import fails"""

    def __init__(
        self,
        from_var: str,
        to_var: str,
        strength: Union[_FallbackCausalStrength, float] = _FallbackCausalStrength.MODERATE,
        lag: int = 0,
    ):
        self.from_var = from_var
        self.to_var = to_var
        # Convert float to CausalStrength if needed
        if isinstance(strength, float):
            if strength >= 0.6:
                self.strength = _FallbackCausalStrength.STRONG
            elif strength >= 0.4:
                self.strength = _FallbackCausalStrength.MODERATE
            else:
                self.strength = _FallbackCausalStrength.WEAK
        else:
            self.strength = strength
        self.lag = lag
        self.confidence: float = 0.5


# Phase 4 集成: 导入完整的因果图分析组件
CAUSAL_ANALYSIS_AVAILABLE = False
try:
    from core.causal import CausalGraph as FullCausalGraph
    from core.causal.graph import CausalEdge, CausalStrength
    from core.causal.impact import ImpactAnalyzer
    from core.causal.inference import RootCauseInference
    from core.causal.prediction import CausalPredictor
    from core.causal.preprocessing import TimeSeriesPreprocessor

    CAUSAL_ANALYSIS_AVAILABLE = True
    logger.info("Phase 4 完整因果图分析组件已导入")
except ImportError:
    logger.warning("Phase 4 完整因果图分析组件不可用，使用简化版本")
    # Use fallback classes
    CausalEdge = _FallbackCausalEdge  # type: ignore
    CausalStrength = _FallbackCausalStrength  # type: ignore

# Use the appropriate CausalEdge class based on availability
CausalEdgeClass = CausalEdge  # type: ignore


class CausalNode:
    """Node in the causal graph"""

    def __init__(self, id: str, name: str, node_type: str = "metric"):
        self.id = id
        self.name = name
        self.node_type = node_type
        self.value: Optional[float] = None
        self.timestamp: Optional[datetime] = None
        self.children: Set[str] = set()
        self.parents: Set[str] = set()
        self.anomaly_score: float = 0.0
        self.is_anomaly: bool = False

    def add_child(self, child_id: str) -> None:
        """Add a child node"""
        self.children.add(child_id)

    def add_parent(self, parent_id: str) -> None:
        """Add a parent node"""
        self.parents.add(parent_id)


class CausalGraph:
    """
    Causal Graph for L3 Processing Layer

    Phase 4 集成: 完整的因果图分析支持

    This graph provides:
    - Causal relationship modeling
    - Root cause propagation analysis
    - Anomaly propagation tracking
    - Impact analysis
    - PC/GES 算法支持 (if available)
    - 根因推断引擎 (if available)
    - 影响分析模块 (if available)
    - 预测性分析 (if available)
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        config = config or {}
        self.config = config
        self.nodes: Dict[str, CausalNode] = {}
        self.edges: List[CausalEdgeClass] = []  # type: ignore
        self._is_initialized = True

        # Phase 4 集成: 初始化完整因果图分析组件
        self._full_causal_graph: Optional[FullCausalGraph] = None
        self._root_cause_inference: Optional[RootCauseInference] = None
        self._impact_analyzer: Optional[ImpactAnalyzer] = None
        self._causal_predictor: Optional[CausalPredictor] = None
        self._preprocessor: Optional[TimeSeriesPreprocessor] = None

        if CAUSAL_ANALYSIS_AVAILABLE:
            try:
                self._full_causal_graph = FullCausalGraph("l3_causal_graph")
                self._root_cause_inference = RootCauseInference(self._full_causal_graph)
                self._impact_analyzer = ImpactAnalyzer(self._full_causal_graph)
                self._causal_predictor = CausalPredictor(self._full_causal_graph)
                self._preprocessor = TimeSeriesPreprocessor()
                logger.info("Phase 4 完整因果图分析组件已初始化")
            except Exception as e:
                logger.warning(f"因果图分析组件初始化失败: {e}")

        logger.info("Causal Graph initialized for L3 Layer")

    def add_node(self, node: CausalNode) -> None:
        """Add a node to the graph"""
        self.nodes[node.id] = node
        logger.debug(f"Added node: {node.id}")

    def add_edge(self, edge: CausalEdgeClass) -> None:  # type: ignore
        """Add an edge to the graph"""
        self.edges.append(edge)

        # Update node relationships
        if edge.from_var in self.nodes:
            self.nodes[edge.from_var].add_child(edge.to_var)
        if edge.to_var in self.nodes:
            self.nodes[edge.to_var].add_parent(edge.from_var)

        logger.debug(f"Added edge: {edge.from_var} -> {edge.to_var}")

    def get_node(self, node_id: str) -> Optional[CausalNode]:
        """Get a node by ID"""
        return self.nodes.get(node_id)

    def get_children(self, node_id: str) -> List[CausalNode]:
        """Get all child nodes"""
        if node_id not in self.nodes:
            return []
        return [self.nodes[cid] for cid in self.nodes[node_id].children]

    def get_parents(self, node_id: str) -> List[CausalNode]:
        """Get all parent nodes"""
        if node_id not in self.nodes:
            return []
        return [self.nodes[pid] for pid in self.nodes[node_id].parents]

    def find_root_causes(self, anomaly_node_id: str, max_depth: int = 5) -> List[Dict[str, Any]]:
        """
        Find potential root causes for an anomaly

        Args:
            anomaly_node_id: ID of the anomalous node
            max_depth: Maximum depth to search

        Returns:
            List of potential root causes with confidence scores
        """
        root_causes = []
        visited = set()

        def dfs(node_id: str, depth: int, path_strength: float) -> None:
            if depth > max_depth or node_id in visited:
                return

            visited.add(node_id)
            node = self.get_node(node_id)

            if not node:
                return

            # Check if this could be a root cause
            if len(node.parents) == 0 or node.is_anomaly:
                root_causes.append(
                    {
                        "node_id": node_id,
                        "node_name": node.name,
                        "confidence": path_strength,
                        "depth": depth,
                        "path": path_strength,
                    }
                )

            # Traverse parents
            for parent in self.get_parents(node_id):
                edge_strength = self._get_edge_strength(parent.id, node_id)
                dfs(parent.id, depth + 1, path_strength * edge_strength)

        dfs(anomaly_node_id, 0, 1.0)

        # Sort by confidence
        def get_confidence(item: Dict[str, Any]) -> float:
            conf = item["confidence"]
            if isinstance(conf, (int, float)):
                return float(conf)
            return 0.0

        root_causes.sort(key=get_confidence, reverse=True)

        return root_causes

    def _get_edge_strength(self, source_id: str, target_id: str) -> float:
        """Get the strength of an edge as a float value"""
        for edge in self.edges:
            if edge.from_var == source_id and edge.to_var == target_id:
                # Convert CausalStrength enum to float
                if isinstance(edge.strength, CausalStrength):
                    strength_map = {
                        "weak": 0.25,
                        "moderate": 0.5,
                        "strong": 0.75,
                    }
                    return strength_map.get(edge.strength.value, 0.5)
                else:
                    # Handle case where strength might be a float or other type
                    try:
                        return float(edge.strength)  # type: ignore
                    except (TypeError, ValueError):
                        return 0.5
        return 0.5

    def propagate_anomaly(self, anomaly_node_id: str, anomaly_score: float) -> Dict[str, Any]:
        """
        Propagate an anomaly through the causal graph

        Args:
            anomaly_node_id: ID of the anomalous node
            anomaly_score: Anomaly score (0-1)

        Returns:
            Propagation results
        """
        affected_nodes = []
        visited = set()

        def propagate(node_id: str, current_score: float) -> None:
            if node_id in visited or current_score < 0.1:
                return

            visited.add(node_id)
            node = self.get_node(node_id)

            if not node:
                return

            node.anomaly_score = current_score
            node.is_anomaly = current_score > 0.5

            affected_nodes.append(
                {"node_id": node_id, "node_name": node.name, "anomaly_score": current_score}
            )

            # Propagate to children
            for child in self.get_children(node_id):
                edge_strength = self._get_edge_strength(node_id, child.id)
                propagate(child.id, current_score * edge_strength)

        propagate(anomaly_node_id, anomaly_score)

        return {
            "source_node": anomaly_node_id,
            "affected_count": len(affected_nodes),
            "affected_nodes": affected_nodes,
        }

    def analyze_impact(self, node_id: str, impact_threshold: float = 0.3) -> Dict[str, Any]:
        """
        Analyze the impact of a node failure

        Args:
            node_id: ID of the node
            impact_threshold: Minimum impact score to consider

        Returns:
            Impact analysis results
        """
        impacted_nodes = []
        visited = set()

        def dfs(current_id: str, impact_score: float) -> None:
            if current_id in visited or impact_score < impact_threshold:
                return

            visited.add(current_id)
            node = self.get_node(current_id)

            if not node:
                return

            impacted_nodes.append(
                {"node_id": current_id, "node_name": node.name, "impact_score": impact_score}
            )

            # Propagate impact to children
            for child in self.get_children(current_id):
                edge_strength = self._get_edge_strength(current_id, child.id)
                dfs(child.id, impact_score * edge_strength)

        dfs(node_id, 1.0)

        return {
            "source_node": node_id,
            "impacted_count": len(impacted_nodes),
            "impacted_nodes": impacted_nodes,
        }

    def build_system_topology(self) -> None:
        """Build a system topology from configured hosts plus base components."""
        from config import DOCKER_HOSTS, K8S_HOSTS, LINUX_HOSTS, WIN_HOSTS

        metric_nodes = [
            CausalNode("cpu", "CPU Usage", "metric"),
            CausalNode("memory", "Memory Usage", "metric"),
            CausalNode("disk", "Disk I/O", "metric"),
            CausalNode("network", "Network I/O", "metric"),
        ]
        for node in metric_nodes:
            self.add_node(node)

        base_services = [
            CausalNode("app", "Application", "service"),
            CausalNode("db", "Database", "service"),
            CausalNode("cache", "Cache", "service"),
            CausalNode("api", "API Gateway", "service"),
        ]
        for node in base_services:
            self.add_node(node)

        host_groups = {
            "linux": LINUX_HOSTS.get("hosts", []) if isinstance(LINUX_HOSTS, dict) else [],
            "k8s": K8S_HOSTS if isinstance(K8S_HOSTS, list) else [],
            "docker": DOCKER_HOSTS if isinstance(DOCKER_HOSTS, list) else [],
            "windows": WIN_HOSTS if isinstance(WIN_HOSTS, list) else [],
        }
        for platform, hosts in host_groups.items():
            for host_entry in hosts:
                if not isinstance(host_entry, dict):
                    continue
                host_id = host_entry.get("host") or host_entry.get(
                    "hostname") or host_entry.get("name")
                if not host_id:
                    continue
                node_id = f"host:{host_id}"
                self.add_node(CausalNode(node_id, host_id, "host"))
                self.add_edge(CausalEdgeClass("cpu", node_id, CausalStrength.MODERATE))
                self.add_edge(CausalEdgeClass("memory", node_id, CausalStrength.MODERATE))
                self.add_edge(CausalEdgeClass("disk", node_id, CausalStrength.MODERATE))
                self.add_edge(CausalEdgeClass("network", node_id, CausalStrength.MODERATE))
                self.add_edge(CausalEdgeClass(node_id, "app", CausalStrength.MODERATE))

        base_edges = [
            CausalEdgeClass("disk", "db", CausalStrength.STRONG),
            CausalEdgeClass("db", "app", CausalStrength.STRONG),
            CausalEdgeClass("cache", "app", CausalStrength.MODERATE),
            CausalEdgeClass("network", "api", CausalStrength.STRONG),
            CausalEdgeClass("api", "app", CausalStrength.STRONG),
        ]
        for edge in base_edges:
            self.add_edge(edge)

        logger.info(f"Built system topology with {len(self.nodes)} nodes")

    def get_status(self) -> Dict[str, Any]:
        """Get graph status"""
        return {
            "initialized": self._is_initialized,
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
        }


# Global singleton instance
_causal_graph: Optional[CausalGraph] = None


def get_causal_graph() -> Optional[CausalGraph]:
    """Get global causal graph instance"""
    return _causal_graph


def init_causal_graph(config: Dict[str, Any]) -> CausalGraph:
    """Initialize global causal graph"""
    global _causal_graph
    _causal_graph = CausalGraph(config)
    return _causal_graph
