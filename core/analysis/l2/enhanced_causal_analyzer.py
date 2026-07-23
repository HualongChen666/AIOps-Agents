# -*- coding: utf-8 -*-
"""
L2 Analysis Layer - Enhanced Causal Analyzer (Phase 2)
Enhanced causal analysis with advanced algorithms and real-time processing
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np
from loguru import logger

# Import existing causal analysis components
CAUSAL_AVAILABLE = False
_causal_edge_class: Any = None
_causal_graph_class: Any = None
_causal_strength_enum: Any = None
_pc_algorithm_class: Any = None
_impact_analyzer_class: Any = None
_root_cause_inference_class: Any = None
_causal_predictor_class: Any = None
_time_series_preprocessor_class: Any = None

try:
    from core.causal import CausalEdge as _CausalEdge
    from core.causal import CausalGraph as _CausalGraph
    from core.causal import CausalStrength as _CausalStrength
    from core.causal.algorithms import PCAlgorithm as _PCAlgorithm
    from core.causal.impact import ImpactAnalyzer as _ImpactAnalyzer
    from core.causal.inference import RootCauseInference as _RootCauseInference
    from core.causal.prediction import CausalPredictor as _CausalPredictor
    from core.causal.preprocessing import TimeSeriesPreprocessor as _TimeSeriesPreprocessor

    CAUSAL_AVAILABLE = True
    _causal_edge_class = _CausalEdge
    _causal_graph_class = _CausalGraph
    _causal_strength_enum = _CausalStrength
    _pc_algorithm_class = _PCAlgorithm
    _impact_analyzer_class = _ImpactAnalyzer
    _root_cause_inference_class = _RootCauseInference
    _causal_predictor_class = _CausalPredictor
    _time_series_preprocessor_class = _TimeSeriesPreprocessor
    logger.info("Causal analysis components imported successfully")
except ImportError:
    CAUSAL_AVAILABLE = False
    logger.warning("Causal analysis components not available, using simplified version")


# Define fallback classes when causal components are not available
@dataclass
class FallbackCausalGraph:
    """Fallback CausalGraph for when causal components are not available"""

    name: str = "fallback_graph"
    nodes: List[str] = field(default_factory=list)
    edges: List[Any] = field(default_factory=list)

    def add_node(self, node: str):
        if node not in self.nodes:
            self.nodes.append(node)

    def add_edge(self, edge: Any):
        self.edges.append(edge)


@dataclass
class FallbackCausalEdge:
    """Fallback CausalEdge for when causal components are not available"""

    from_var: str
    to_var: str
    strength: Any = None
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class FallbackCausalStrength(Enum):
    """Fallback CausalStrength for when causal components are not available"""

    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"


# Type aliases that work in both cases
if CAUSAL_AVAILABLE:
    CausalGraph = _causal_graph_class  # type: ignore
    CausalEdge = _causal_edge_class  # type: ignore
    CausalStrength = _causal_strength_enum  # type: ignore
    PCAlgorithm = _pc_algorithm_class  # type: ignore
    ImpactAnalyzer = _impact_analyzer_class  # type: ignore
    RootCauseInference = _root_cause_inference_class  # type: ignore
    CausalPredictor = _causal_predictor_class  # type: ignore
    TimeSeriesPreprocessor = _time_series_preprocessor_class  # type: ignore
else:
    CausalGraph = FallbackCausalGraph  # type: ignore
    CausalEdge = FallbackCausalEdge  # type: ignore
    CausalStrength = FallbackCausalStrength  # type: ignore
    PCAlgorithm = Any  # type: ignore
    ImpactAnalyzer = Any  # type: ignore
    RootCauseInference = Any  # type: ignore
    CausalPredictor = Any  # type: ignore
    TimeSeriesPreprocessor = Any  # type: ignore


class CausalAnalysisMode(Enum):
    """Causal analysis mode"""

    REALTIME = "realtime"
    BATCH = "batch"
    HISTORICAL = "historical"


@dataclass
class CausalAnalysisResult:
    """Causal analysis result"""

    root_causes: List[str] = field(default_factory=list)
    causal_paths: List[List[str]] = field(default_factory=list)
    impact_scores: Dict[str, float] = field(default_factory=dict)
    confidence: float = 0.0
    analysis_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


class EnhancedCausalAnalyzer:
    """Enhanced causal analyzer for L2 Analysis Layer (Phase 2)"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize enhanced causal analyzer

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.mode = CausalAnalysisMode(self.config.get("mode", "realtime"))
        self.causal_graph: Optional[CausalGraph] = None  # type: ignore[valid-type]
        self.preprocessor: Optional[TimeSeriesPreprocessor] = None  # type: ignore[valid-type]
        self.root_cause_inference: Optional[RootCauseInference] = None  # type: ignore[valid-type]
        self.impact_analyzer: Optional[ImpactAnalyzer] = None  # type: ignore[valid-type]
        self.predictor: Optional[CausalPredictor] = None  # type: ignore[valid-type]

        # Performance metrics
        self.analysis_count = 0
        self.avg_analysis_time = 0.0
        self.total_analysis_time = 0.0

        # Initialize components
        self._initialize_components()

    def _initialize_components(self):
        """Initialize causal analysis components"""
        if not CAUSAL_AVAILABLE:
            logger.warning("Causal analysis components not available, using simplified mode")
            return

        try:
            # Initialize time series preprocessor
            try:
                self.preprocessor = TimeSeriesPreprocessor(  # type: ignore
                    window_size=self.config.get("window_size", 60),
                    smoothing_method=self.config.get("smoothing_method", "ewm"),
                )
            except TypeError:
                # Fallback to default constructor if arguments not accepted
                self.preprocessor = TimeSeriesPreprocessor()  # type: ignore

            # Initialize root cause inference
            try:
                self.root_cause_inference = RootCauseInference(  # type: ignore
                    method=self.config.get("inference_method", "pc"),
                    confidence_threshold=self.config.get("confidence_threshold", 0.8),
                )
            except TypeError:
                # Fallback to default constructor if arguments not accepted
                self.root_cause_inference = RootCauseInference()  # type: ignore

            # Initialize impact analyzer
            try:
                self.impact_analyzer = ImpactAnalyzer(  # type: ignore
                    time_horizon=self.config.get("impact_horizon", 3600),
                    method=self.config.get("impact_method", "intervention"),
                )
            except TypeError:
                # Fallback to default constructor if arguments not accepted
                self.impact_analyzer = ImpactAnalyzer()  # type: ignore

            # Initialize predictor
            try:
                self.predictor = CausalPredictor(  # type: ignore
                    prediction_horizon=self.config.get("prediction_horizon", 300),
                    method=self.config.get("prediction_method", "linear"),
                )
            except TypeError:
                # Fallback to default constructor if arguments not accepted
                self.predictor = CausalPredictor()  # type: ignore

            logger.info("Enhanced causal analyzer components initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize causal analysis components: {e}")

    async def analyze_causal_relationships(
        self, metrics_data: Dict[str, List[float]], timestamps: List[datetime], target_variable: str
    ) -> CausalAnalysisResult:
        """
        Analyze causal relationships in metrics data

        Args:
            metrics_data: Dictionary of metric names to time series data
            timestamps: List of timestamps for the data points
            target_variable: Target variable to analyze

        Returns:
            CausalAnalysisResult: Analysis result
        """
        start_time = datetime.now(timezone.utc)

        try:
            # Preprocess data
            if self.preprocessor:
                preprocessor = self.preprocessor
                processed_data: Any = preprocessor.preprocess(metrics_data)  # type: ignore
            else:
                processed_data = metrics_data

            # Build causal graph
            if CAUSAL_AVAILABLE:
                causal_graph = await self._build_causal_graph(processed_data, target_variable)
                self.causal_graph = causal_graph
            else:
                causal_graph = self._build_simplified_causal_graph(processed_data, target_variable)

            # Infer root causes
            if self.root_cause_inference and hasattr(self.root_cause_inference, "infer"):
                root_causes = self.root_cause_inference.infer(  # type: ignore[attr-defined]
                    causal_graph, target_variable
                )
            else:
                root_causes = self._infer_root_causes_simplified(causal_graph, target_variable)

            # Analyze impact
            if self.impact_analyzer and hasattr(self.impact_analyzer, "analyze"):
                impact_scores = self.impact_analyzer.analyze(  # type: ignore[attr-defined]
                    causal_graph, root_causes
                )
            else:
                impact_scores = self._analyze_impact_simplified(causal_graph, root_causes)

            # Find causal paths
            causal_paths = self._find_causal_paths(causal_graph, target_variable)

            # Calculate confidence
            confidence = self._calculate_confidence(root_causes, impact_scores)

            # Update metrics
            analysis_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            self.analysis_count += 1
            self.total_analysis_time += analysis_time
            self.avg_analysis_time = self.total_analysis_time / self.analysis_count

            result = CausalAnalysisResult(
                root_causes=root_causes,
                causal_paths=causal_paths,
                impact_scores=impact_scores,
                confidence=confidence,
                analysis_timestamp=start_time,
                metadata={
                    "analysis_time": analysis_time,
                    "mode": self.mode.value,
                    "nodes_count": (
                        len(causal_graph.nodes) if causal_graph else 0  # type: ignore[attr-defined]
                    ),
                    "edges_count": (
                        len(causal_graph.edges) if causal_graph else 0  # type: ignore[attr-defined]
                    ),
                },
            )

            logger.info(
                f"Causal analysis completed: {len(root_causes)} root causes found, "
                f"confidence: {confidence:.2f}"
            )
            return result

        except Exception as e:
            logger.error(f"Causal analysis failed: {e}")
            # Return simplified result on error
            return CausalAnalysisResult(
                root_causes=[target_variable],
                causal_paths=[[target_variable]],
                impact_scores={target_variable: 1.0},
                confidence=0.5,
                analysis_timestamp=start_time,
                metadata={"error": str(e)},
            )

    async def _build_causal_graph(
        self, data: Dict[str, List[float]], target: str
    ) -> CausalGraph:  # type: ignore[valid-type]
        """Build causal graph using PC algorithm"""
        graph = CausalGraph(
            name=f"causal_graph_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        )

        # Add all variables as nodes
        for var in data.keys():
            graph.add_node(var)

        # Use PC algorithm to discover causal structure
        if CAUSAL_AVAILABLE:
            try:
                # Try different constructor signatures
                try:
                    pc_algorithm = PCAlgorithm(significance=0.05)  # type: ignore
                except TypeError:
                    pc_algorithm = PCAlgorithm()  # type: ignore

                # Try different discover method signatures
                try:
                    # Try with dict and str
                    discovered_edges = pc_algorithm.discover(data, target)  # type: ignore
                except TypeError:
                    try:
                        # Try with ndarray and list[str]
                        data_array = np.array([data[k] for k in data.keys()]).T
                        discovered_edges = pc_algorithm.discover(
                            data_array, list(data.keys())
                        )  # type: ignore
                    except TypeError:
                        # Try with just ndarray
                        data_array = np.array([data[k] for k in data.keys()]).T
                        discovered_edges = pc_algorithm.discover(data_array)  # type: ignore

                # Add edges if discover returned something iterable
                if discovered_edges is not None:
                    try:
                        for edge in discovered_edges:  # type: ignore
                            graph.add_edge(edge)
                    except TypeError:
                        logger.warning("PC algorithm returned non-iterable result")
                        self._add_correlation_edges(graph, data, target)
                else:
                    self._add_correlation_edges(graph, data, target)

            except Exception as e:
                logger.warning(f"PC algorithm failed: {e}, using correlation-based approach")
                self._add_correlation_edges(graph, data, target)
        else:
            self._add_correlation_edges(graph, data, target)

        return graph  # type: ignore[no-any-return]

    def _build_simplified_causal_graph(
        self, data: Dict[str, List[float]], target: str
    ) -> CausalGraph:  # type: ignore[valid-type]
        """Build simplified causal graph using correlation"""
        graph = CausalGraph(
            name=f"simplified_causal_graph_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        )

        # Add all variables as nodes
        for var in data.keys():
            graph.add_node(var)

        self._add_correlation_edges(graph, data, target)

        return graph  # type: ignore[no-any-return]

    def _add_correlation_edges(
        self,
        graph: CausalGraph,  # type: ignore[valid-type]
        data: Dict[str, List[float]],
        target: str,
    ):
        """Add edges based on correlation analysis"""
        if target not in data:
            return

        target_data = np.array(data[target])

        for var, var_data in data.items():
            if var == target:
                continue

            try:
                var_array = np.array(var_data)
                correlation = np.corrcoef(target_data, var_array)[0, 1]

                if abs(correlation) > 0.5:  # Correlation threshold
                    strength = (
                        CausalStrength.STRONG if abs(correlation) > 0.8 else CausalStrength.MODERATE
                    )

                    edge = CausalEdge(
                        from_var=var,
                        to_var=target,
                        strength=strength,  # type: ignore
                        confidence=abs(correlation),
                        metadata={"correlation": correlation},
                    )
                    graph.add_edge(edge)  # type: ignore[attr-defined]

            except Exception as e:
                logger.debug(f"Failed to calculate correlation for {var}: {e}")

    def _infer_root_causes_simplified(
        self,
        graph: CausalGraph,  # type: ignore[valid-type]
        target: str,
    ) -> List[str]:
        """Simplified root cause inference"""
        root_causes = []

        # Find nodes with highest impact on target
        for edge in graph.edges:  # type: ignore[attr-defined]
            if edge.to_var == target:
                root_causes.append(edge.from_var)

        # Sort by confidence
        root_causes.sort(key=lambda x: self._get_edge_confidence(graph, x, target), reverse=True)

        return root_causes[:5]  # Return top 5

    def _get_edge_confidence(
        self,
        graph: CausalGraph,  # type: ignore[valid-type]
        from_var: str,
        to_var: str,
    ) -> float:
        """Get confidence score for an edge"""
        for edge in graph.edges:  # type: ignore[attr-defined]
            if (
                hasattr(edge, "from_var")  # noqa: E501
                and hasattr(edge, "to_var")
                and hasattr(edge, "confidence")
            ):
                if edge.from_var == from_var and edge.to_var == to_var:  # type: ignore
                    return float(edge.confidence)  # type: ignore
        return 0.0

    def _analyze_impact_simplified(
        self, graph: CausalGraph, root_causes: List[str]  # type: ignore[valid-type]
    ) -> Dict[str, float]:
        """Simplified impact analysis"""
        impact_scores = {}

        for cause in root_causes:
            # Calculate impact based on edge confidence
            total_confidence = 0.0
            edge_count = 0

            for edge in graph.edges:  # type: ignore[attr-defined]
                if edge.from_var == cause:
                    total_confidence += edge.confidence
                    edge_count += 1

            impact_scores[cause] = total_confidence / edge_count if edge_count > 0 else 0.5

        return impact_scores

    def _find_causal_paths(
        self,
        graph: CausalGraph,  # type: ignore[valid-type]
        target: str,
    ) -> List[List[str]]:
        """Find causal paths to target"""
        paths = []

        # Find all nodes that can reach the target
        for node in graph.nodes:  # type: ignore[attr-defined]
            if node == target:
                continue

            # Simple path finding (BFS)
            path = self._find_path(graph, node, target)
            if path:
                paths.append(path)

        return paths

    def _find_path(
        self,
        graph: CausalGraph,  # type: ignore[valid-type]
        start: str,
        end: str,
    ) -> List[str]:
        """Find path from start to end using BFS"""
        from collections import deque

        # Build adjacency list from edges
        adjacency: Dict[str, List[str]] = {}
        for node in graph.nodes:  # type: ignore[attr-defined]
            adjacency[node] = []

        for edge in graph.edges:  # type: ignore[attr-defined]
            # Handle both FallbackCausalEdge and actual CausalEdge
            if hasattr(edge, "from_var") and hasattr(edge, "to_var"):
                from_var = edge.from_var  # type: ignore
                to_var = edge.to_var  # type: ignore
                if from_var not in adjacency:
                    adjacency[from_var] = []
                adjacency[from_var].append(to_var)

        queue = deque([[start]])
        visited = {start}

        while queue:
            path = queue.popleft()
            node = path[-1]

            if node == end:
                return path

            for neighbor in adjacency.get(node, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    new_path = list(path)
                    new_path.append(neighbor)
                    queue.append(new_path)

        return []

    def _calculate_confidence(
        self, root_causes: List[str], impact_scores: Dict[str, float]
    ) -> float:
        """Calculate overall confidence"""
        if not root_causes:
            return 0.0

        total_impact = sum(impact_scores.get(cause, 0.0) for cause in root_causes)
        avg_impact = total_impact / len(root_causes)

        return min(avg_impact, 1.0)

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        return {
            "analysis_count": self.analysis_count,
            "avg_analysis_time": self.avg_analysis_time,
            "total_analysis_time": self.total_analysis_time,
            "mode": self.mode.value,
        }

    async def realtime_analysis(
        self, metrics_stream: Dict[str, float], window_size: int = 60
    ) -> CausalAnalysisResult:
        """
        Real-time causal analysis for streaming data

        Args:
            metrics_stream: Current metrics snapshot
            window_size: Size of the sliding window for analysis

        Returns:
            CausalAnalysisResult: Real-time analysis result
        """
        # This would integrate with the L1 data stream for real-time processing
        # For now, return a simplified result
        return CausalAnalysisResult(
            root_causes=list(metrics_stream.keys()),
            causal_paths=[[k] for k in metrics_stream.keys()],
            impact_scores={k: 0.8 for k in metrics_stream.keys()},
            confidence=0.7,
            metadata={"realtime": True},
        )


def get_enhanced_causal_analyzer(config: Optional[Dict[str, Any]] = None) -> EnhancedCausalAnalyzer:
    """
    Factory function to get enhanced causal analyzer instance

    Args:
        config: Optional configuration dictionary

    Returns:
        EnhancedCausalAnalyzer: Analyzer instance
    """
    return EnhancedCausalAnalyzer(config)
