# -*- coding: utf-8 -*-
import logging

"""
Root Cause Intelligence Module
==============================

Advanced root cause analysis with real-time topology discovery, historical pattern matching,
and automated verification mechanisms.

Key Features:
- Real-time topology discovery and dynamic updates
- Cross-layer tracking with completeness support
- Historical pattern matching algorithms
- Enhanced causal analysis accuracy
- Root cause prediction capabilities
- Automated root cause verification
"""

from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set

try:
    from loguru import logger
except ImportError:
    import logging

    logger = logging.getLogger("root_cause_intelligence")

# ============================================================
# 根因诊断阈值与限制
# ============================================================
# 置信度低于该值时不得自动执行修复，必须升级人工
EXECUTION_CONFIDENCE_THRESHOLD: float = 0.75
# 置信度低于该值时建议升级，不建议给出确定性结论
ESCALATION_CONFIDENCE_THRESHOLD: float = 0.60
# 单次诊断最多生成候选数
MAX_ROOT_CAUSE_CANDIDATES: int = 5
# 假设-验证循环最大步数
MAX_DIAGNOSIS_STEPS: int = 5
# 变更影响窗口（分钟）：告警时间与变更时间在此窗口内视为相关
CHANGE_CORRELATION_WINDOW_MINUTES: int = 15

# Import existing causal analysis components
try:
    pass

    CAUSAL_AVAILABLE = True
except ImportError:
    CAUSAL_AVAILABLE = False
    logger.warning("Causal analysis components not available, using simplified version")

# Try to import ML libraries
try:
    from sklearn.ensemble import GradientBoostingRegressor, RandomForestClassifier
    from sklearn.preprocessing import StandardScaler

    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    logger.warning("ML libraries not available, using rule-based fallback")


class TopologyLayer(Enum):
    """Topology layers for cross-layer tracking"""

    APPLICATION = "application"
    SERVICE = "service"
    INFRASTRUCTURE = "infrastructure"
    NETWORK = "network"
    STORAGE = "storage"


@dataclass
class TopologyNode:
    """Represents a node in the system topology"""

    node_id: str
    name: str
    layer: TopologyLayer
    dependencies: Set[str] = field(default_factory=set)
    dependents: Set[str] = field(default_factory=set)
    health_status: str = "healthy"
    last_updated: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RootCauseHypothesis:
    """Hypothesis for root cause analysis"""

    hypothesis_id: str
    root_cause: str
    confidence: float
    evidence: List[str] = field(default_factory=list)
    causal_path: List[str] = field(default_factory=list)
    impact_score: float = 0.0
    verification_status: str = "pending"  # pending, verified, rejected
    verification_timestamp: Optional[datetime] = None
    predicted_impact: Dict[str, float] = field(default_factory=dict)
    # 可验证性：如果该假设成立，应该观察到什么
    expected_observations: List[str] = field(default_factory=list)
    # 缺少什么数据才能确认/排除该假设
    missing_data: List[str] = field(default_factory=list)
    # 推荐的后续动作（包括 escalate）
    recommended_action: str = ""  # e.g. "auto_heal", "escalate", "collect_more_data"
    # 是否需要在执行前人工审批
    requires_approval: bool = False
    # 多根因标记
    is_multi_root: bool = False


@dataclass
class HistoricalPattern:
    """Historical root cause pattern for matching"""

    pattern_id: str
    symptom_signature: str
    root_cause: str
    frequency: int
    last_occurrence: datetime
    confidence: float
    resolution_time_avg: float = 0.0
    effectiveness_score: float = 0.0


class RootCauseIntelligenceEngine:
    """
    Advanced root cause analysis engine with real-time topology discovery
    and historical pattern matching
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize root cause intelligence engine

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # Topology management
        self.topology_graph: Dict[str, TopologyNode] = {}
        self.topology_layers: Dict[TopologyLayer, Set[str]] = defaultdict(set)
        self.topology_update_queue: deque[Any] = deque(maxlen=1000)

        # Historical patterns
        self.historical_patterns: Dict[str, HistoricalPattern] = {}
        self.pattern_matcher: Optional[Any] = None

        # Root cause hypotheses
        self.active_hypotheses: Dict[str, RootCauseHypothesis] = {}
        self.hypothesis_history: List[RootCauseHypothesis] = []

        # ML components
        self.pattern_classifier: Optional[Any] = None
        self.impact_predictor: Optional[Any] = None
        self.scaler: Optional[Any] = StandardScaler() if ML_AVAILABLE else None

        # Verification mechanisms
        self.verification_results: Dict[str, Dict[str, Any]] = {}

        # Initialize components
        self._initialize_components()

        logger.info("Root Cause Intelligence Engine initialized")

    def _initialize_components(self) -> None:
        """Initialize ML and analysis components"""
        if ML_AVAILABLE:
            try:
                self.pattern_classifier = RandomForestClassifier(
                    n_estimators=100, max_depth=10, random_state=42
                )
                self.impact_predictor = GradientBoostingRegressor(
                    n_estimators=100, max_depth=5, random_state=42
                )
                logger.info("ML components initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize ML components: {e}")

    async def discover_topology_realtime(
        self,
        metrics_data: Dict[str, Any],
        alert: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Real-time topology discovery based on current metrics, alert and system state.

        Args:
            metrics_data: Current system metrics and state information
            alert: Optional alert whose source/affected components should be added to topology

        Returns:
            Discovered topology structure
        """
        logger.info("Starting real-time topology discovery")

        # Extract nodes from metrics data and alert context
        discovered_nodes = self._extract_nodes_from_metrics(metrics_data, alert)

        # Update topology graph
        topology_updates: List[tuple] = []
        for node_data in discovered_nodes:
            node_id = node_data.get("id", node_data.get("host", "unknown"))

            if node_id not in self.topology_graph:
                # New node discovered
                node = TopologyNode(
                    node_id=node_id,
                    name=node_data.get("name", node_id),
                    layer=self._infer_layer(node_data),
                    metadata=node_data,
                )
                self.topology_graph[node_id] = node
                topology_updates.append(("add", node))
                logger.info(f"Discovered new topology node: {node_id}")
            else:
                # Update existing node
                existing_node = self.topology_graph[node_id]
                existing_node.last_updated = datetime.now()
                existing_node.health_status = node_data.get("health", "healthy")
                existing_node.metadata.update(node_data)
                topology_updates.append(("update", existing_node))

        # Discover dependencies based on communication patterns
        await self._discover_dependencies(metrics_data, alert)

        # Organize by layers
        self._organize_by_layers()

        # Queue updates for processing
        for update in topology_updates:
            self.topology_update_queue.append(update)

        return {
            "discovered_nodes": len(discovered_nodes),
            "total_nodes": len(self.topology_graph),
            "updates": len(topology_updates),
            "topology_summary": self._get_topology_summary(),
        }

    @staticmethod
    def _is_abnormal(metrics_data: Dict[str, Any]) -> bool:
        """Heuristic to decide if a metric snapshot indicates an unhealthy node."""
        thresholds = {
            "dns_resolution_error_rate": 0.0,
            "dns_lookup_time_ms": 500.0,
            "slow_query_rate": 0.0,
            "avg_query_duration_ms": 500.0,
            "memory_usage_percent": 85.0,
            "cpu_usage_percent": 90.0,
            "error_rate": 0.05,
        }
        for key, threshold in thresholds.items():
            value = metrics_data.get(key)
            if isinstance(value, (int, float)) and value > threshold:
                return True
        last_state = metrics_data.get("last_state", {})
        if isinstance(last_state, dict) and "OOMKilled" in str(last_state):
            return True
        return False

    def _extract_nodes_from_metrics(
        self,
        metrics_data: Dict[str, Any],
        alert: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Extract topology nodes from metrics data and alert context."""
        nodes: List[Dict[str, Any]] = []

        # Extract host information
        if "hosts" in metrics_data:
            for host_info in metrics_data["hosts"]:
                nodes.append(
                    {
                        "id": host_info.get("hostname", "unknown"),
                        "name": host_info.get("hostname", "unknown"),
                        "type": "host",
                        "health": host_info.get("health", "healthy"),
                        "metrics": host_info.get("metrics", {}),
                    }
                )

        # Extract service information
        if "services" in metrics_data:
            for service_info in metrics_data["services"]:
                nodes.append(
                    {
                        "id": service_info.get("name", "unknown"),
                        "name": service_info.get("name", "unknown"),
                        "type": "service",
                        "health": service_info.get("health", "healthy"),
                        "port": service_info.get("port", None),
                    }
                )

        # Extract application components
        if "applications" in metrics_data:
            for app_info in metrics_data["applications"]:
                nodes.append(
                    {
                        "id": app_info.get("name", "unknown"),
                        "name": app_info.get("name", "unknown"),
                        "type": "application",
                        "health": app_info.get("health", "healthy"),
                    }
                )

        # Derive nodes from flat symptom-specific metrics
        abnormal = self._is_abnormal(metrics_data)
        flat_identities = {
            "service": "service",
            "source": "service",
            "target": "network",
            "database": "storage",
            "pod_name": "host",
            "node_name": "host",
            "host": "host",
            "node": "host",
        }
        for key, node_type in flat_identities.items():
            value = metrics_data.get(key)
            if value and isinstance(value, (str, int)):
                node_id = str(value)
                if not any(n["id"] == node_id for n in nodes):
                    nodes.append(
                        {
                            "id": node_id,
                            "name": node_id,
                            "type": node_type,
                            "health": "unhealthy" if abnormal else "healthy",
                        }
                    )

        # Add alert source/affected nodes if not already present
        if isinstance(alert, dict):
            for attr in ("service", "source", "host"):
                src = alert.get(attr)
                if src and isinstance(src, str):
                    if not any(n["id"] == src for n in nodes):
                        nodes.append(
                            {
                                "id": src,
                                "name": src,
                                "type": "service",
                                "health": "unhealthy",
                            }
                        )
            for affected_key in ("affected_services", "affected_components"):
                affected = alert.get(affected_key) or []
                if isinstance(affected, str):
                    affected = [affected]
                for a in affected:
                    if a and isinstance(a, str) and not any(n["id"] == a for n in nodes):
                        nodes.append(
                            {
                                "id": a,
                                "name": a,
                                "type": "service",
                                "health": "unhealthy",
                            }
                        )

        return nodes

    def _infer_layer(self, node_data: Dict[str, Any]) -> TopologyLayer:
        """Infer topology layer from node data"""
        node_type = node_data.get("type", "unknown")

        layer_mapping = {
            "application": TopologyLayer.APPLICATION,
            "service": TopologyLayer.SERVICE,
            "host": TopologyLayer.INFRASTRUCTURE,
            "network": TopologyLayer.NETWORK,
            "storage": TopologyLayer.STORAGE,
        }

        return layer_mapping.get(node_type, TopologyLayer.INFRASTRUCTURE)

    async def _discover_dependencies(
        self,
        metrics_data: Dict[str, Any],
        alert: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Discover dependencies between nodes based on communication patterns."""

        def _add_edge(source: Optional[str], target: Optional[str]) -> None:
            if not source or not target:
                return
            if source in self.topology_graph and target in self.topology_graph:
                self.topology_graph[source].dependencies.add(target)
                self.topology_graph[target].dependents.add(source)

        # Extract network connections
        if "network_connections" in metrics_data:
            for connection in metrics_data["network_connections"]:
                _add_edge(connection.get("source"), connection.get("target"))

        # Extract service dependencies
        if "service_dependencies" in metrics_data:
            for dep in metrics_data["service_dependencies"]:
                _add_edge(dep.get("service"), dep.get("depends_on"))

        # Derive flat metric relationships
        source = (
            (alert.get("service") if isinstance(alert, dict) else None)
            or metrics_data.get("service")
            or metrics_data.get("source")
        )
        for target_key in ("target", "database"):
            _add_edge(source, metrics_data.get(target_key))
        _add_edge(metrics_data.get("pod_name"), metrics_data.get("node_name"))

    def _organize_by_layers(self) -> None:
        """Organize nodes by topology layers"""
        self.topology_layers.clear()

        for node_id, node in self.topology_graph.items():
            self.topology_layers[node.layer].add(node_id)

    def _get_topology_summary(self) -> Dict[str, Any]:
        """Get summary of current topology"""
        return {
            "total_nodes": len(self.topology_graph),
            "layers": {layer.value: len(nodes) for layer, nodes in self.topology_layers.items()},
            "health_distribution": self._get_health_distribution(),
        }

    def _get_health_distribution(self) -> Dict[str, int]:
        """Get distribution of health statuses across nodes"""
        distribution: Dict[str, int] = defaultdict(int)  # type: ignore
        for node in self.topology_graph.values():
            distribution[node.health_status] += 1
        return dict(distribution)

    async def perform_cross_layer_tracking(
        self, alert: Dict[str, Any], max_depth: int = 5
    ) -> List[str]:
        """
        Perform cross-layer tracking to find a complete causal path.

        The returned causal path ends at the most likely root cause node,
        selected from upstream dependencies and affected components, instead of
        simply taking the first node visited by BFS.

        Args:
            alert: Alert to trace
            max_depth: Maximum depth for tracking

        Returns:
            Complete causal path across layers ending at selected root cause
        """
        logger.info(f"Performing cross-layer tracking for alert: {alert.get('id')}")

        # Start from the alert source (support host, source, service, etc.)
        source_node = (
            alert.get("host")
            or alert.get("source")
            or alert.get("service")
            or alert.get("source_node")
            or "unknown"
        )

        if source_node not in self.topology_graph:
            logger.warning(f"Source node {source_node} not found in topology")
            return [source_node]

        # Explore both upstream dependencies and downstream dependents
        distances, predecessors = self._bfs_reachable(
            source=source_node,
            max_depth=max_depth,
            use_dependencies=True,
            use_dependents=True,
        )

        if not distances:
            return [source_node]

        affected = alert.get("affected_services", []) or alert.get("affected_components", [])
        if isinstance(affected, str):
            affected = [affected]

        # Score candidate end nodes by depth, health, and affected membership
        candidate_scores: Dict[str, float] = {}
        for node, depth in distances.items():
            if node == source_node:
                continue
            score = depth * 0.2
            node_obj = self.topology_graph.get(node)
            if node_obj and node_obj.health_status != "healthy":
                score += 0.5
            if node in affected:
                score += 0.3
            # Prefer upstream dependencies (likely roots) over downstream dependents
            if node_obj and source_node in node_obj.dependents:
                score += 0.2
            candidate_scores[node] = score

        if not candidate_scores:
            return [source_node]

        best_root = max(candidate_scores, key=lambda node: candidate_scores[node])

        # Reconstruct shortest path from source to the selected root
        path: List[str] = []
        current: Optional[str] = best_root
        while current is not None:
            path.append(current)
            current = predecessors.get(current)
        path.reverse()

        logger.info(
            f"Cross-layer tracking completed: selected root {best_root}, path length {len(path)}"
        )
        return path

    def _bfs_reachable(
        self,
        source: str,
        max_depth: int,
        use_dependencies: bool = True,
        use_dependents: bool = False,
    ) -> tuple[Dict[str, int], Dict[str, Optional[str]]]:
        """BFS helper returning {node: distance} and {node: predecessor}.

        Dependencies are upstream (what source depends on); dependents are
        downstream (what depends on source).
        """
        distances: Dict[str, int] = {}
        predecessors: Dict[str, Optional[str]] = {}

        if source not in self.topology_graph:
            return distances, predecessors

        queue: deque[tuple[str, int]] = deque([(source, 0)])
        distances[source] = 0
        predecessors[source] = None

        while queue:
            current, depth = queue.popleft()
            if depth >= max_depth:
                continue
            node_obj = self.topology_graph.get(current)
            if not node_obj:
                continue
            neighbors: List[str] = []
            if use_dependencies:
                neighbors.extend(node_obj.dependencies)
            if use_dependents:
                neighbors.extend(node_obj.dependents)
            for neighbor in neighbors:
                if neighbor not in self.topology_graph or neighbor in distances:
                    continue
                distances[neighbor] = depth + 1
                predecessors[neighbor] = current
                queue.append((neighbor, depth + 1))

        return distances, predecessors

    async def _find_common_upstream_dependency(
        self,
        source_nodes: List[str],
        max_depth: int = 5,
    ) -> Optional[str]:
        """Find the closest common upstream dependency for multiple source nodes.

        Used to detect cascade failures where multiple downstream services are
        impacted by the same root cause.
        """
        if len(source_nodes) < 2:
            return None

        upstream_sets: List[Set[str]] = []
        for source in source_nodes:
            if source not in self.topology_graph:
                continue
            distances, _ = self._bfs_reachable(
                source=source,
                max_depth=max_depth,
                use_dependencies=True,
                use_dependents=False,
            )
            upstream_sets.append(set(distances.keys()) - {source})

        if not upstream_sets:
            return None

        common = set.intersection(*upstream_sets)
        if not common:
            return None

        # Pick the common node with the smallest maximum distance from sources
        best_node: Optional[str] = None
        best_score = float("inf")
        for node in common:
            max_node_depth = 0
            for source in source_nodes:
                if source not in self.topology_graph:
                    continue
                distances, _ = self._bfs_reachable(
                    source=source,
                    max_depth=max_depth,
                    use_dependencies=True,
                    use_dependents=False,
                )
                if node in distances:
                    max_node_depth = max(max_node_depth, distances[node])
            if max_node_depth < best_score:
                best_score = max_node_depth
                best_node = node

        return best_node

    async def match_historical_patterns(
        self, current_symptoms: Dict[str, Any]
    ) -> List[HistoricalPattern]:
        """
        Match current symptoms against historical patterns

        Args:
            current_symptoms: Current system symptoms and alerts

        Returns:
            List of matching historical patterns ranked by confidence
        """
        logger.info("Matching current symptoms against historical patterns")

        if not self.historical_patterns:
            logger.warning("No historical patterns available")
            return []

        # Create signature for current symptoms
        current_signature = self._create_symptom_signature(current_symptoms)

        # Match against historical patterns
        matched_patterns = []
        for pattern_id, pattern in self.historical_patterns.items():
            similarity_score = self._calculate_signature_similarity(
                current_signature, pattern.symptom_signature
            )

            if similarity_score > 0.5:  # Similarity threshold
                matched_patterns.append((pattern, similarity_score))

        # Sort by similarity score
        matched_patterns.sort(key=lambda x: x[1], reverse=True)

        logger.info(f"Found {len(matched_patterns)} matching historical patterns")
        return [pattern for pattern, _ in matched_patterns]

    def _create_symptom_signature(self, symptoms: Dict[str, Any]) -> str:
        """Create signature from symptoms for pattern matching"""
        signature_parts = []

        # Add alert types
        alerts = symptoms.get("alerts", [])
        alert_types = sorted(
            set(alert.get("alert_type", alert.get("category", "unknown")) for alert in alerts)
        )
        signature_parts.append(f"alerts:{','.join(alert_types)}")

        # Add affected hosts
        hosts = sorted(set(alert.get("host", "unknown") for alert in alerts))
        signature_parts.append(f"hosts:{','.join(hosts)}")

        # Add metrics patterns
        metrics = symptoms.get("metrics", {})
        for metric_name, metric_value in metrics.items():
            if isinstance(metric_value, (int, float)):
                status = "high" if metric_value > 90 else "low" if metric_value < 10 else "normal"
                signature_parts.append(f"{metric_name}:{status}")

        return "|".join(signature_parts)

    def _calculate_signature_similarity(self, sig1: str, sig2: str) -> float:
        """Calculate similarity between two symptom signatures"""
        # Simple Jaccard similarity
        set1 = set(sig1.split("|"))
        set2 = set(sig2.split("|"))

        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))

        return intersection / union if union > 0 else 0.0

    def learn_historical_pattern(
        self,
        symptoms: Dict[str, Any],
        root_cause: str,
        resolution_time: float,
        effectiveness: float,
    ) -> None:
        """
        Learn a new historical pattern from resolved incident

        Args:
            symptoms: Symptoms that led to the incident
            root_cause: Identified root cause
            resolution_time: Time taken to resolve
            effectiveness: Effectiveness score of the resolution
        """
        signature = self._create_symptom_signature(symptoms)
        pattern_id = f"pattern_{hash(signature)}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # Check if similar pattern exists
        for existing_pattern in self.historical_patterns.values():
            similarity = self._calculate_signature_similarity(
                signature, existing_pattern.symptom_signature
            )
            if similarity > 0.8:
                # Update existing pattern
                existing_pattern.frequency += 1
                existing_pattern.last_occurrence = datetime.now()
                existing_pattern.confidence = min(1.0, existing_pattern.confidence + 0.1)
                existing_pattern.resolution_time_avg = (
                    existing_pattern.resolution_time_avg * 0.9 + resolution_time * 0.1
                )
                existing_pattern.effectiveness_score = (
                    existing_pattern.effectiveness_score * 0.9 + effectiveness * 0.1
                )
                logger.info(f"Updated existing pattern: {existing_pattern.pattern_id}")
                return

        # Create new pattern
        new_pattern = HistoricalPattern(
            pattern_id=pattern_id,
            symptom_signature=signature,
            root_cause=root_cause,
            frequency=1,
            last_occurrence=datetime.now(),
            confidence=0.5,
            resolution_time_avg=resolution_time,
            effectiveness_score=effectiveness,
        )

        self.historical_patterns[pattern_id] = new_pattern
        logger.info(f"Learned new historical pattern: {pattern_id}")

    async def analyze_root_causes_enhanced(
        self,
        alert: Dict[str, Any],
        metrics_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> List[RootCauseHypothesis]:
        """
        Enhanced root cause analysis with hypothesis-verification loop,
        confidence thresholds, excluded-hypothesis filtering, and multi-root support.

        Args:
            alert: Alert to analyze
            metrics_data: Current metrics data
            context: Additional context (correlated_alerts, change_events, verification_data, etc.)

        Returns:
            List of root cause hypotheses ranked by confidence, with execution gating flags
        """
        context = context or {}
        max_steps = context.get("max_steps", MAX_DIAGNOSIS_STEPS)
        execution_threshold = context.get(
            "execution_confidence_threshold", EXECUTION_CONFIDENCE_THRESHOLD
        )
        escalation_threshold = context.get(
            "escalation_confidence_threshold", ESCALATION_CONFIDENCE_THRESHOLD
        )
        excluded_ids = set(context.get("excluded_hypothesis_ids", []))
        verification_data = context.get(
            "verification_data",
            metrics_data.get("verification_data") if isinstance(metrics_data, dict) else None,
        )
        related_alerts = context.get("correlated_alerts", [])
        change_events = context.get("change_events", [])

        logger.info(f"Performing enhanced root cause analysis for alert: {alert.get('id')}")

        # Refresh topology from current metrics and alert data
        if metrics_data:
            try:
                await self.discover_topology_realtime(metrics_data, alert)
            except Exception as e:
                logger.warning(f"Topology discovery failed during analysis: {e}")

        affected = alert.get("affected_services", []) or alert.get("affected_components", [])
        if isinstance(affected, str):
            affected = [affected]

        all_candidates: List[RootCauseHypothesis] = []
        seen_roots: Set[str] = set()

        # Hypothesis generation with a step cap and excluded-hypothesis filtering
        for step in range(max_steps):
            step_candidates = await self._generate_candidates(
                alert=alert,
                metrics_data=metrics_data,
                affected=affected,
                related_alerts=related_alerts,
                change_events=change_events,
                excluded_ids=excluded_ids,
                seen_roots=seen_roots,
            )
            if not step_candidates:
                break

            for hypothesis in step_candidates:
                if hypothesis.hypothesis_id in excluded_ids:
                    continue
                seen_roots.add(hypothesis.root_cause)
                all_candidates.append(hypothesis)

            # If a high-confidence verified candidate is found, continue one more step
            # to detect multi-root scenarios, then stop.
            if any(c.confidence >= execution_threshold for c in all_candidates) and step >= 1:
                break

            if len(all_candidates) >= MAX_ROOT_CAUSE_CANDIDATES:
                break

        # Verification loop
        verified_candidates: List[RootCauseHypothesis] = []
        for hypothesis in all_candidates[:MAX_ROOT_CAUSE_CANDIDATES]:
            try:
                if verification_data:
                    await self.verify_root_cause(hypothesis, verification_data)
            except Exception as e:
                logger.warning(f"Verification failed for {hypothesis.hypothesis_id}: {e}")

            if (
                hypothesis.hypothesis_id in excluded_ids
                or hypothesis.verification_status == "rejected"
            ):
                excluded_ids.add(hypothesis.hypothesis_id)
                continue
            verified_candidates.append(hypothesis)

        # Sort by confidence
        verified_candidates.sort(key=lambda h: h.confidence, reverse=True)

        # Apply confidence-based gating
        for hypothesis in verified_candidates:
            if hypothesis.confidence >= execution_threshold:
                hypothesis.recommended_action = "auto_heal"
                hypothesis.requires_approval = False
            elif hypothesis.confidence >= escalation_threshold:
                hypothesis.recommended_action = "collect_more_data"
                hypothesis.requires_approval = True
            else:
                hypothesis.recommended_action = "escalate"
                hypothesis.requires_approval = True

        # Multi-root detection: if multiple high-confidence roots exist, surface it.
        # Change-event candidates are triggers, not independent root components, so exclude them.
        # Also skip a candidate whose root string is already contained in a higher-confidence
        # scenario candidate (e.g. "orders" inside "slow_sql_after_release_orders").
        sorted_by_conf = sorted(verified_candidates, key=lambda h: h.confidence, reverse=True)
        high_conf_roots: List[RootCauseHypothesis] = []
        for h in sorted_by_conf:
            if (
                h.confidence < escalation_threshold
                or h.is_multi_root
                or h.hypothesis_id.startswith("change_")
                or h.hypothesis_id == "escalate"
            ):
                continue
            if any(
                h.root_cause != kept.root_cause and h.root_cause in kept.root_cause
                for kept in high_conf_roots
            ):
                continue
            high_conf_roots.append(h)
        if len(high_conf_roots) >= 2:
            multi_conf = sum(h.confidence for h in high_conf_roots[:3]) / len(high_conf_roots[:3])
            multi_root = RootCauseHypothesis(
                hypothesis_id="multi_root",
                root_cause="multiple_root_causes",
                confidence=min(multi_conf, 0.95),
                evidence=[
                    f"Multiple high-confidence root causes detected: "
                    f"{', '.join(h.root_cause for h in high_conf_roots[:3])}"
                ],
                expected_observations=[
                    "Multiple independent components should show abnormal metrics simultaneously",
                    "A single remediation action should not fully resolve the incident",
                ],
                missing_data=[
                    "Confirm each candidate root cause independently",
                    "Check whether failures are causally linked or coincidental",
                ],
                is_multi_root=True,
                verification_status="pending",
                recommended_action="escalate",
                requires_approval=True,
            )
            verified_candidates.insert(0, multi_root)

        # Escalation guard: if top candidate is too weak, recommend escalation
        if not verified_candidates or verified_candidates[0].confidence < escalation_threshold:
            escalation = RootCauseHypothesis(
                hypothesis_id="escalate",
                root_cause="unknown",
                confidence=0.0,
                evidence=["All candidates below confidence threshold or required data missing"],
                expected_observations=[],
                missing_data=[
                    "additional metrics",
                    "topology data",
                    "verification data",
                    "historical patterns",
                ],
                verification_status="pending",
                recommended_action="escalate",
                requires_approval=True,
            )
            verified_candidates.append(escalation)

        final_candidates = verified_candidates[:MAX_ROOT_CAUSE_CANDIDATES]

        # Store active hypotheses and update history
        for hypothesis in final_candidates:
            self.active_hypotheses[hypothesis.hypothesis_id] = hypothesis
        self.hypothesis_history.extend(final_candidates)

        logger.info(f"Generated {len(final_candidates)} final root cause hypotheses")
        return final_candidates

    @staticmethod
    def _detect_scenario(
        alert: Dict[str, Any],
        metrics_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """根据告警与指标识别三类典型故障场景。"""
        text = (
            f"{alert.get('title', '')} {alert.get('description', '')} "
            f"{alert.get('category', '')} {alert.get('alert_type', '')}"
        ).lower()
        for keyword in ["dns", "domain", "resolution", "域名", "解析"]:
            if keyword in text:
                return "dns"
        for keyword in ["sql", "query", "slow", "慢查询", "数据库", "database"]:
            if keyword in text:
                return "sql"
        for keyword in ["oom", "oomkilled", "killed", "memory", "内存"]:
            if keyword in text:
                return "oom"

        if isinstance(metrics_data, dict):
            keys = " ".join(str(k).lower() for k in metrics_data.keys())
            if any(k in keys for k in ["dns_resolution_error_rate", "dns_lookup_time_ms"]):
                return "dns"
            if any(k in keys for k in ["slow_query_rate", "avg_query_duration_ms"]):
                return "sql"
            if any(k in keys for k in ["memory_usage_percent", "last_state", "oom"]):
                return "oom"

        return "generic"

    def _generate_scenario_candidates(
        self,
        alert: Dict[str, Any],
        metrics_data: Dict[str, Any],
        change_events: List[Dict[str, Any]],
        seen_roots: Set[str],
    ) -> List[RootCauseHypothesis]:
        """针对 DNS/SQL/OOM 三类典型症状生成根因候选。"""
        candidates: List[RootCauseHypothesis] = []
        scenario = self._detect_scenario(alert, metrics_data)
        if scenario == "generic":
            return candidates

        # Helper to pull numeric values from the merged metrics data
        def _num(key: str) -> Optional[float]:
            value = metrics_data.get(key)
            if isinstance(value, (int, float)):
                return float(value)
            return None

        # 1. DNS 解析超时
        if scenario == "dns":
            target = metrics_data.get("target") or alert.get("service") or "downstream"
            dns_error = _num("dns_resolution_error_rate")
            dns_latency = _num("dns_lookup_time_ms")
            confidence = 0.75
            if dns_error is not None and dns_error > 1.0:
                confidence = min(confidence + 0.15, 0.95)
            if dns_latency is not None and dns_latency > 1000:
                confidence = min(confidence + 0.15, 0.95)
            # Increase confidence if a recent deployment/change touched the target
            recent_change = any(
                str(change.get("target", "")).lower() in str(target).lower()
                or str(target).lower() in str(change.get("target", "")).lower()
                for change in change_events
            )
            if recent_change:
                confidence = min(confidence + 0.1, 0.98)

            root = f"dns_resolution_failure_{target}"
            if root not in seen_roots:
                h = RootCauseHypothesis(
                    hypothesis_id=f"dns_failure_{target}",
                    root_cause=root,
                    confidence=confidence,
                    evidence=[
                        f"Detected DNS/network symptoms for {target}",
                        f"dns_resolution_error_rate={dns_error}, dns_lookup_time_ms={dns_latency}",
                    ],
                    expected_observations=[
                        f"DNS lookups for {target} should time out or fail",
                        f"Downstream calls dependent on {target} should show errors/latency spikes",
                        f"Pod/container CPU/memory for {target} should remain normal",
                    ],
                    missing_data=[
                        "Packet captures or DNS server logs",
                        "CoreDNS/External DNS metrics",
                        "Network path traces between caller and target",
                    ],
                    causal_path=[alert.get("service", "caller"), target, "dns_resolver"],
                    verification_status="pending",
                )
                candidates.append(h)
                seen_roots.add(root)

        # 2. 发布后的慢 SQL
        elif scenario == "sql":
            database = metrics_data.get("database") or alert.get("service") or "database"
            slow_rate = _num("slow_query_rate")
            avg_duration = _num("avg_query_duration_ms")
            active_conn = _num("active_connections")
            confidence = 0.75
            if slow_rate is not None and slow_rate > 1.0:
                confidence = min(confidence + 0.15, 0.95)
            if avg_duration is not None and avg_duration > 1000:
                confidence = min(confidence + 0.15, 0.95)
            recent_change = any(
                str(change.get("target", "")).lower() in str(database).lower()
                or str(database).lower() in str(change.get("target", "")).lower()
                or str(change.get("type", "")).lower() in ["deploy", "release", "rollback"]
                for change in change_events
            )
            if recent_change:
                confidence = min(confidence + 0.15, 0.98)

            root = f"slow_sql_after_release_{database}"
            if root not in seen_roots:
                h = RootCauseHypothesis(
                    hypothesis_id=f"sql_slow_{database}",
                    root_cause=root,
                    confidence=confidence,
                    evidence=[
                        f"Detected database symptoms for {database}",
                        f"slow_query_rate={slow_rate}, avg_query_duration_ms={avg_duration}",
                    ],
                    expected_observations=[
                        f"SQL execution time for {database} should spike after a recent change",
                        "Slow query log should contain queries from the new release",
                        f"Connection pool saturation may be visible if active_connections={active_conn} is high",  # noqa: E501
                    ],
                    missing_data=[
                        "Slow query log / pg_stat_statements",
                        "Query execution plan diffs before/after release",
                        "Schema/index change history for the release",
                    ],
                    causal_path=[alert.get("service", "app"), database],
                    verification_status="pending",
                )
                candidates.append(h)
                seen_roots.add(root)

        # 3. Pod OOM / 宿主机内存压力
        elif scenario == "oom":
            pod_name = metrics_data.get("pod_name") or alert.get("pod") or "unknown-pod"
            namespace = metrics_data.get("namespace") or "default"
            node_name = metrics_data.get("node_name") or alert.get("node") or "unknown-node"
            memory_usage = _num("memory_usage_percent")
            mem_usage_bytes = _num("memory_usage_bytes")
            last_state = metrics_data.get("last_state", {})
            oom_detected = (isinstance(last_state, dict) and "OOMKilled" in str(last_state)) or (
                memory_usage is not None and memory_usage > 90
            )
            confidence = 0.7 if oom_detected else 0.5

            root = f"pod_oom_{pod_name}"
            if root not in seen_roots:
                h = RootCauseHypothesis(
                    hypothesis_id=f"oom_pod_{pod_name}_{namespace}",
                    root_cause=root,
                    confidence=confidence,
                    evidence=[
                        f"Detected OOM symptoms for pod {pod_name}/{namespace}",
                        f"memory_usage_percent={memory_usage}, memory_usage_bytes={mem_usage_bytes}",  # noqa: E501
                        f"last_state={last_state}",
                    ],
                    expected_observations=[
                        f"Pod {pod_name} should show exit code 137 or OOMKilled",
                        "Container memory working set should approach or exceed limit",
                        f"Host {node_name} memory pressure may coincide if multi-tenant",
                    ],
                    missing_data=[
                        f"Container memory limit and usage for {pod_name}",
                        f"Node {node_name} memory stats and kernel OOM killer logs",
                        "Memory leak profiling or heap dump of the affected pod",
                    ],
                    causal_path=[alert.get("service", "app"), pod_name, node_name],
                    verification_status="pending",
                )
                candidates.append(h)
                seen_roots.add(root)

            # Secondary candidate: host-level memory pressure
            node_memory = _num("memory_usage_percent")
            edac = _num("edac_correctable_errors")
            mce = _num("mce_errors")
            if node_memory is not None and node_memory > 85:
                root2 = f"host_memory_pressure_{node_name}"
                if root2 not in seen_roots:
                    h2 = RootCauseHypothesis(
                        hypothesis_id=f"oom_host_{node_name}",
                        root_cause=root2,
                        confidence=min(node_memory / 100.0 + 0.1, 0.9),
                        evidence=[
                            f"Node {node_name} memory usage at {node_memory}%",
                            f"EDAC={edac}, MCE={mce}",
                        ],
                        expected_observations=[
                            f"Other pods on {node_name} may also be OOMKilled",
                            "System-level memory reclaim / swap usage should be high",
                        ],
                        missing_data=[
                            f"Node {node_name} memory pressure and reclaim metrics",
                            "EC2/VM instance type and co-tenant noisy neighbor data",
                        ],
                        causal_path=[pod_name, node_name, "memory_capacity"],
                        verification_status="pending",
                    )
                    candidates.append(h2)
                    seen_roots.add(root2)

        return candidates

    async def _generate_candidates(
        self,
        alert: Dict[str, Any],
        metrics_data: Dict[str, Any],
        affected: List[str],
        related_alerts: List[Dict[str, Any]],
        change_events: List[Dict[str, Any]],
        excluded_ids: Set[str],
        seen_roots: Set[str],
    ) -> List[RootCauseHypothesis]:
        """Generate a batch of root cause candidates from multiple sources."""
        candidates: List[RootCauseHypothesis] = []

        # 1. Historical pattern candidates
        symptoms = {
            "alerts": [alert] + related_alerts[:20],
            "metrics": metrics_data,
            "change_events": change_events,
        }
        pattern_matches = await self.match_historical_patterns(symptoms)
        for pattern in pattern_matches[:3]:
            if pattern.root_cause in seen_roots:
                continue
            h = RootCauseHypothesis(
                hypothesis_id=f"pattern_{pattern.pattern_id}",
                root_cause=pattern.root_cause,
                confidence=pattern.confidence * 0.8,
                evidence=[f"Historical pattern match: {pattern.pattern_id}"],
                verification_status="pending",
            )
            candidates.append(self._populate_expected_and_missing(h, metrics_data))

        # 2. Topology-based candidate
        causal_path = await self.perform_cross_layer_tracking(alert, max_depth=5)
        if len(causal_path) > 1:
            root = causal_path[-1]  # path ends at the selected root cause
            if root not in seen_roots:
                # Dynamic confidence by depth + health penalty
                confidence = min(0.6 + (len(causal_path) - 2) * 0.05, 0.85)
                last_node = self.topology_graph.get(root)
                if last_node and last_node.health_status != "healthy":
                    confidence = min(confidence + 0.1, 0.9)
                h = RootCauseHypothesis(
                    hypothesis_id=f"topology_{root}",
                    root_cause=root,
                    confidence=confidence,
                    evidence=[f"Topology causal path: {' -> '.join(causal_path)}"],
                    causal_path=causal_path,
                    verification_status="pending",
                )
                candidates.append(self._populate_expected_and_missing(h, metrics_data))

        # 3. Change-event candidate
        change_h = self._generate_change_event_candidate(alert, change_events)
        if change_h and change_h.root_cause not in seen_roots:
            candidates.append(self._populate_expected_and_missing(change_h, metrics_data))

        # 4. Common upstream dependency / cascade candidate
        if related_alerts:
            source_nodes = []
            source_attr = alert.get("host") or alert.get("source") or alert.get("service")
            if source_attr:
                source_nodes.append(source_attr)
            for a in related_alerts:
                s = a.get("host") or a.get("source") or a.get("service")
                if s:
                    source_nodes.append(s)
            source_nodes = list(set([s for s in source_nodes if s in self.topology_graph]))
            common_root = await self._find_common_upstream_dependency(source_nodes, max_depth=5)
            if common_root and common_root not in seen_roots:
                h = RootCauseHypothesis(
                    hypothesis_id=f"cascade_{common_root}",
                    root_cause=common_root,
                    confidence=0.72,
                    evidence=[
                        f"Common upstream dependency for {len(source_nodes)} correlated alerts"
                    ],
                    causal_path=[alert.get("source", "unknown"), common_root],
                    verification_status="pending",
                    is_multi_root=True,
                )
                candidates.append(self._populate_expected_and_missing(h, metrics_data))

        # 5. Scenario-specific candidates (DNS / slow SQL / OOM)
        scenario_candidates = self._generate_scenario_candidates(
            alert, metrics_data, change_events, seen_roots
        )
        for h in scenario_candidates:
            candidates.append(self._populate_expected_and_missing(h, metrics_data))

        # Filter excluded hypotheses and cap
        candidates = [h for h in candidates if h.hypothesis_id not in excluded_ids]
        candidates.sort(key=lambda h: h.confidence, reverse=True)
        return candidates[:MAX_ROOT_CAUSE_CANDIDATES]

    def _generate_change_event_candidate(
        self,
        alert: Dict[str, Any],
        change_events: List[Dict[str, Any]],
    ) -> Optional[RootCauseHypothesis]:
        """Generate a hypothesis from recent change events correlated with the alert."""
        if not change_events:
            return None

        alert_ts = self._parse_timestamp(alert.get("timestamp") or alert.get("raw_time"))
        best_event: Optional[Dict[str, Any]] = None
        best_score = 0.0

        for event in change_events:
            event_ts = self._parse_timestamp(event.get("timestamp"))
            target = str(event.get("target", "")).lower()
            source = str(alert.get("source", alert.get("service", ""))).lower()
            affected = alert.get("affected_services", []) or alert.get("affected_components", [])
            if isinstance(affected, str):
                affected = [affected]

            target_match = any(target in a.lower() for a in affected) or target in source
            if not target_match:
                continue

            score = 0.6
            if alert_ts and event_ts:
                delta_minutes = abs((alert_ts - event_ts).total_seconds()) / 60.0
                if delta_minutes <= CHANGE_CORRELATION_WINDOW_MINUTES:
                    score = 0.85
                elif delta_minutes <= 60:
                    score = 0.7
                else:
                    score = 0.55

            if score > best_score:
                best_score = score
                best_event = event

        if best_event:
            return RootCauseHypothesis(
                hypothesis_id=f"change_{best_event.get('target', 'unknown')}",
                root_cause=str(best_event.get("target", "unknown")),
                confidence=best_score,
                evidence=[
                    f"Recent {best_event.get('type', 'change')} at {best_event.get('timestamp')} "
                    f"correlated with alert"
                ],
                verification_status="pending",
            )
        return None

    def _populate_expected_and_missing(
        self,
        hypothesis: RootCauseHypothesis,
        metrics_data: Dict[str, Any],
    ) -> RootCauseHypothesis:
        """Populate expected_observations and missing_data fields based on hypothesis type."""
        if hypothesis.expected_observations and hypothesis.missing_data:
            return hypothesis

        h_type = "topology" if hypothesis.hypothesis_id.startswith("topology_") else ""
        if hypothesis.hypothesis_id.startswith("pattern_"):
            h_type = "pattern"
        elif hypothesis.hypothesis_id.startswith("change_"):
            h_type = "change"
        elif hypothesis.hypothesis_id.startswith("cascade_"):
            h_type = "cascade"
        elif hypothesis.hypothesis_id in ("multi_root", "escalate"):
            h_type = hypothesis.hypothesis_id

        root = hypothesis.root_cause

        if not hypothesis.expected_observations:
            if h_type == "topology" or h_type == "cascade":
                hypothesis.expected_observations = [
                    f"Node {root} should show abnormal metrics (CPU, memory, latency, errors)",
                    f"Downstream services dependent on {root} should report correlated failures",
                    f"Path {' -> '.join(hypothesis.causal_path)} should be observable in traces/dependencies",  # noqa: E501
                ]
            elif h_type == "pattern":
                hypothesis.expected_observations = [
                    f"Current symptoms should match historical pattern for {root}",
                    f"Preceding indicators of {root} should be present in recent metrics/logs",
                ]
            elif h_type == "change":
                hypothesis.expected_observations = [
                    f"Metrics should degrade after change to {root}",
                    f"Rollback or mitigation of {root} should relieve symptoms",
                ]
            else:
                hypothesis.expected_observations = [
                    f"Metrics or logs should directly implicate {root} as the root cause",
                ]

        if not hypothesis.missing_data:
            if h_type in ("topology", "cascade"):
                hypothesis.missing_data = [
                    "Real-time health metrics for all nodes in the causal path",
                    "Network path traces between source and root",
                    "Dependency call error rates and latency",
                ]
            elif h_type == "pattern":
                hypothesis.missing_data = [
                    "Pre/post incident metric diff",
                    "Historical resolution outcome for this pattern",
                    "Confirmation that current symptom signature matches pattern",
                ]
            elif h_type == "change":
                hypothesis.missing_data = [
                    "Pre-change baseline metrics",
                    "Post-change metric diff",
                    "Change impact scope and rollback success data",
                ]
            else:
                hypothesis.missing_data = [
                    "Additional metrics across infrastructure, service, and network layers",
                    "Topology and dependency mapping",
                    "Verification data to confirm or reject the hypothesis",
                ]

        return hypothesis

    def _parse_timestamp(self, value: Any) -> Optional[datetime]:
        """Parse a timestamp string or number into a timezone-aware datetime."""
        if isinstance(value, datetime):
            return value
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, tz=timezone.utc) if value > 0 else None
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except Exception as e:
                logging.exception("Unexpected exception: %s", e)
                try:
                    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")
                except Exception as e:
                    logging.exception("Unexpected exception: %s", e)
                    return None
        return None

    async def _causal_graph_analysis(
        self, alert: Dict[str, Any], metrics_data: Dict[str, Any]
    ) -> List[RootCauseHypothesis]:
        """基于告警与指标的因果路径分析，生成可验证的根因假设。"""
        import uuid

        hypotheses = []
        source = alert.get("source_service") or alert.get("instance", "unknown")
        metric = alert.get("metric", "unknown")
        value = alert.get("value")

        # 构建一条简单因果链：source -> metric 异常 -> 依赖服务受影响
        causal_path = [source, metric]
        downstream = set(alert.get("affected_services", []))
        if downstream:
            causal_path.extend(sorted(downstream))

        evidence = [
            f"告警指标 {metric} 当前值为 {value}",
            f"受影响服务: {', '.join(downstream) if downstream else '未指定'}",
        ]
        # 如果 metrics_data 里有相关指标，加入证据
        for key, val in metrics_data.items():
            if metric in key or key in str(metric):
                evidence.append(f"相关指标 {key} 值: {val}")

        hypotheses.append(
            RootCauseHypothesis(
                hypothesis_id=f"causal-{uuid.uuid4().hex[:8]}",
                root_cause=f"{metric} 异常可能是 {source} 上根因的传导结果",
                confidence=0.6,
                evidence=evidence,
                causal_path=causal_path,
                impact_score=alert.get("severity_score", 0.5),
                expected_observations=[
                    f"若成立，{source} 的 {metric} 指标应持续异常",
                    "下游服务错误率或延迟应同步上升",
                ],
            )
        )
        return hypotheses

    async def _ml_based_analysis(
        self, alert: Dict[str, Any], metrics_data: Dict[str, Any]
    ) -> List[RootCauseHypothesis]:
        """基于指标统计特征生成根因假设。"""
        import uuid

        hypotheses = []
        metric = alert.get("metric", "unknown")
        values = [v for v in metrics_data.values() if isinstance(v, (int, float))]
        avg = sum(values) / len(values) if values else 0.0
        threshold = alert.get("threshold", avg * 1.2 if avg else 1.0)
        current_value = alert.get("value")
        current_numeric = current_value if isinstance(current_value, (int, float)) else 1.0

        if values and current_numeric > avg:
            confidence = min(0.95, 0.5 + (current_numeric - avg) / max(avg, 1.0) * 0.3)
            root_cause = f"{metric} 明显高于历史均值 {avg:.2f}，可能为容量或资源瓶颈"
        else:
            confidence = 0.4
            root_cause = f"{metric} 异常触发，但历史数据不足，需人工确认"

        evidence = [
            f"当前值: {current_numeric}",
            f"历史均值: {avg:.2f}",
            f"阈值: {threshold}",
        ]

        hypotheses.append(
            RootCauseHypothesis(
                hypothesis_id=f"ml-{uuid.uuid4().hex[:8]}",
                root_cause=root_cause,
                confidence=round(confidence, 2),
                evidence=evidence,
                impact_score=alert.get("severity_score", 0.5),
                expected_observations=[
                    f"若成立，{metric} 应持续高于 {threshold}",
                    "相关容量指标（CPU/内存/连接数）应同步接近上限",
                ],
            )
        )
        return hypotheses

    async def predict_root_causes(
        self, current_state: Dict[str, Any], prediction_horizon: int = 60  # minutes
    ) -> Dict[str, Any]:
        """
        Predict potential root causes before they occur

        Args:
            current_state: Current system state
            prediction_horizon: Time horizon for prediction in minutes

        Returns:
            Predicted root causes with probabilities
        """
        logger.info(f"Predicting root causes for next {prediction_horizon} minutes")

        predictions: Dict[str, Any] = {
            "prediction_horizon": prediction_horizon,
            "predicted_root_causes": [],
            "confidence": 0.0,
            "model_used": "rule_based",
        }

        # Use historical patterns for prediction
        current_signature = self._create_symptom_signature(current_state)

        for pattern in self.historical_patterns.values():
            similarity = self._calculate_signature_similarity(
                current_signature, pattern.symptom_signature
            )

            if similarity > 0.3:  # Lower threshold for prediction
                predictions["predicted_root_causes"].append(
                    {
                        "root_cause": pattern.root_cause,
                        "probability": similarity * pattern.confidence,
                        "expected_time": pattern.resolution_time_avg,
                        "pattern_id": pattern.pattern_id,
                    }
                )

        # Sort by probability
        predictions["predicted_root_causes"].sort(key=lambda x: x["probability"], reverse=True)

        if predictions["predicted_root_causes"]:
            predictions["confidence"] = predictions["predicted_root_causes"][0]["probability"]

        logger.info(f"Predicted {len(predictions['predicted_root_causes'])} potential root causes")
        return predictions

    async def verify_root_cause(
        self, hypothesis: RootCauseHypothesis, verification_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Automatically verify a root cause hypothesis

        Args:
            hypothesis: Hypothesis to verify
            verification_data: Data for verification

        Returns:
            Verification result
        """
        logger.info(f"Verifying hypothesis: {hypothesis.hypothesis_id}")

        verification_result: Dict[str, Any] = {
            "hypothesis_id": hypothesis.hypothesis_id,
            "verification_status": "in_progress",
            "verification_timestamp": datetime.now().isoformat(),
            "checks": [],
        }

        # 1. Check if the proposed root cause exists in current state
        affected = verification_data.get("affected_components", []) or []
        active = verification_data.get("active_components", []) or []
        known_nodes = set(self.topology_graph.keys())
        root_cause_exists = (
            hypothesis.root_cause in affected
            or hypothesis.root_cause in active
            or hypothesis.root_cause in known_nodes
        )
        verification_result["checks"].append(
            {
                "check": "root_cause_presence",
                "passed": root_cause_exists,
                "details": (
                    f"Root cause {hypothesis.root_cause} found in current state: "
                    f"{root_cause_exists}"
                ),
            }
        )

        # 2. Check if the causal path is valid
        causal_path_valid = True
        for node in hypothesis.causal_path:
            if node not in active and node not in known_nodes:
                causal_path_valid = False
                break

        verification_result["checks"].append(
            {
                "check": "causal_path_validity",
                "passed": causal_path_valid,
                "details": f"Causal path validation: {causal_path_valid}",
            }
        )

        # 3. Check impact prediction accuracy
        if hypothesis.predicted_impact:
            actual_impact = verification_data.get("actual_impact", {})
            impact_accuracy = self._calculate_impact_accuracy(
                hypothesis.predicted_impact, actual_impact
            )
            verification_result["checks"].append(
                {
                    "check": "impact_prediction_accuracy",
                    "passed": impact_accuracy > 0.7,
                    "details": f"Impact prediction accuracy: {impact_accuracy:.2f}",
                }
            )

        # 4. Check expected observations
        observed_symptoms = set(verification_data.get("observed_symptoms", []))
        expected = hypothesis.expected_observations or []
        matched = 0
        for exp in expected:
            if any(
                str(sym).lower() in exp.lower() or exp.lower() in str(sym).lower()
                for sym in observed_symptoms
            ):
                matched += 1
        expected_match = matched / len(expected) if expected else 1.0
        verification_result["checks"].append(
            {
                "check": "expected_observations_match",
                "passed": expected_match >= 0.5,
                "details": f"Expected observations matched: {matched}/{len(expected)}",
            }
        )

        # 5. Check whether required missing data is now available
        missing_items = hypothesis.missing_data or []
        present_data = set(verification_data.keys())
        available = sum(
            1 for m in missing_items if any(m.lower() in key.lower() for key in present_data)
        )
        data_availability = available / len(missing_items) if missing_items else 1.0
        verification_result["checks"].append(
            {
                "check": "missing_data_availability",
                "passed": data_availability >= 0.5,
                "details": f"Missing data now available: {available}/{len(missing_items)}",
            }
        )

        # 6. Check against historical patterns
        pattern_match = False
        for pattern in self.historical_patterns.values():
            if pattern.root_cause == hypothesis.root_cause:
                pattern_match = True
                break

        verification_result["checks"].append(
            {
                "check": "historical_pattern_match",
                "passed": pattern_match,
                "details": f"Historical pattern match: {pattern_match}",
            }
        )

        # 7. Scenario-specific metric verification (DNS / slow SQL / OOM)
        scenario_passed = self._verify_scenario_metrics(hypothesis, verification_data)
        if scenario_passed is not None:
            verification_result["checks"].append(
                {
                    "check": "scenario_metric_match",
                    "passed": scenario_passed,
                    "details": f"Scenario-specific metric verification: {scenario_passed}",
                }
            )

        # Calculate overall verification score
        passed_checks = sum(1 for check in verification_result["checks"] if check["passed"])
        total_checks = len(verification_result["checks"])
        verification_score = passed_checks / total_checks if total_checks > 0 else 0.0

        # Determine verification status
        if verification_score >= 0.75:
            verification_result["verification_status"] = "verified"
            hypothesis.verification_status = "verified"
        elif verification_score >= 0.5:
            verification_result["verification_status"] = "partially_verified"
            hypothesis.verification_status = "partially_verified"
        else:
            verification_result["verification_status"] = "rejected"
            hypothesis.verification_status = "rejected"

        verification_result["verification_score"] = verification_score
        hypothesis.verification_timestamp = datetime.now()

        # Store verification result
        self.verification_results[hypothesis.hypothesis_id] = verification_result

        logger.info(
            f"Hypothesis verification completed: {verification_result['verification_status']}"
        )
        return verification_result

    def _verify_scenario_metrics(
        self,
        hypothesis: RootCauseHypothesis,
        verification_data: Dict[str, Any],
    ) -> Optional[bool]:
        """针对 DNS/SQL/OOM 场景的指标一致性验证。返回 None 表示非场景化假设。"""
        root = hypothesis.root_cause
        metrics = verification_data if isinstance(verification_data, dict) else {}

        def _num(key: str) -> Optional[float]:
            value = metrics.get(key)
            if isinstance(value, (int, float)):
                return float(value)
            return None

        if root.startswith("dns_resolution_failure_"):
            dns_error = _num("dns_resolution_error_rate")
            dns_latency = _num("dns_lookup_time_ms")
            if dns_error is not None and dns_error > 0:
                return True
            if dns_latency is not None and dns_latency > 500:
                return True
            return False

        if root.startswith("slow_sql_after_release_"):
            slow_rate = _num("slow_query_rate")
            avg_duration = _num("avg_query_duration_ms")
            if slow_rate is not None and slow_rate > 0:
                return True
            if avg_duration is not None and avg_duration > 500:
                return True
            return False

        if root.startswith("pod_oom_") or root.startswith("host_memory_pressure_"):
            memory_usage = _num("memory_usage_percent")
            last_state = metrics.get("last_state", {})
            if memory_usage is not None and memory_usage > 85:
                return True
            if isinstance(last_state, dict) and "OOMKilled" in str(last_state):
                return True
            return False

        return None

    def _calculate_impact_accuracy(
        self, predicted: Dict[str, float], actual: Dict[str, float]
    ) -> float:
        """Calculate accuracy of impact prediction"""
        if not predicted or not actual:
            return 0.0

        total_error = 0.0
        count = 0

        for key, pred_value in predicted.items():
            if key in actual:
                actual_value = actual[key]
                if actual_value != 0:
                    error = abs(pred_value - actual_value) / actual_value
                    total_error += error
                    count += 1

        if count == 0:
            return 0.0

        avg_error = total_error / count
        accuracy = max(0.0, 1.0 - avg_error)

        return accuracy

    def get_analysis_statistics(self) -> Dict[str, Any]:
        """Get statistics about root cause analysis performance"""
        return {
            "topology_nodes": len(self.topology_graph),
            "historical_patterns": len(self.historical_patterns),
            "active_hypotheses": len(self.active_hypotheses),
            "verification_results": len(self.verification_results),
            "pattern_match_accuracy": self._calculate_pattern_accuracy(),
            "average_verification_score": self._calculate_avg_verification_score(),
        }

    def _calculate_pattern_accuracy(self) -> float:
        """Calculate pattern matching accuracy"""
        if not self.verification_results:
            return 0.0

        verified_count = sum(
            1
            for result in self.verification_results.values()
            if result.get("verification_status") == "verified"
        )

        return verified_count / len(self.verification_results)

    def _calculate_avg_verification_score(self) -> float:
        """Calculate average verification score"""
        if not self.verification_results:
            return 0.0

        total_score = sum(
            float(result.get("verification_score", 0.0))
            for result in self.verification_results.values()
        )  # noqa: E501

        return total_score / len(self.verification_results)


# Global instance
root_cause_intelligence_engine = RootCauseIntelligenceEngine()
