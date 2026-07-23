# -*- coding: utf-8 -*-
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
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from loguru import logger

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

    async def discover_topology_realtime(self, metrics_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Real-time topology discovery based on current metrics and system state

        Args:
            metrics_data: Current system metrics and state information

        Returns:
            Discovered topology structure
        """
        logger.info("Starting real-time topology discovery")

        # Extract nodes from metrics data
        discovered_nodes = self._extract_nodes_from_metrics(metrics_data)

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
        await self._discover_dependencies(metrics_data)

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

    def _extract_nodes_from_metrics(self, metrics_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract topology nodes from metrics data"""
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

    async def _discover_dependencies(self, metrics_data: Dict[str, Any]) -> None:
        """Discover dependencies between nodes based on communication patterns"""
        # Extract network connections
        if "network_connections" in metrics_data:
            for connection in metrics_data["network_connections"]:
                source = connection.get("source")
                target = connection.get("target")

                if (
                    source
                    and target
                    and source in self.topology_graph
                    and target in self.topology_graph
                ):
                    self.topology_graph[source].dependencies.add(target)
                    self.topology_graph[target].dependents.add(source)

        # Extract service dependencies
        if "service_dependencies" in metrics_data:
            for dep in metrics_data["service_dependencies"]:
                source = dep.get("service")
                target = dep.get("depends_on")

                if (
                    source
                    and target
                    and source in self.topology_graph
                    and target in self.topology_graph
                ):
                    self.topology_graph[source].dependencies.add(target)
                    self.topology_graph[target].dependents.add(source)

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
        Perform cross-layer tracking to find complete causal paths

        Args:
            alert: Alert to trace
            max_depth: Maximum depth for tracking

        Returns:
            Complete causal path across layers
        """
        logger.info(f"Performing cross-layer tracking for alert: {alert.get('id')}")

        # Start from the alert source
        source_node = alert.get("host", alert.get("source", "unknown"))

        if source_node not in self.topology_graph:
            logger.warning(f"Source node {source_node} not found in topology")
            return [source_node]

        # Perform breadth-first search across layers
        causal_path: List[str] = []
        visited: Set[str] = set()
        queue: List[tuple] = [(source_node, 0, [source_node])]  # (node, depth, path)

        while queue:
            current_node, depth, path = queue.pop(0)

            if depth > max_depth:
                continue

            if current_node in visited:
                continue

            visited.add(current_node)
            causal_path = path

            # Explore dependencies
            current_node_obj = self.topology_graph[current_node]

            # Check upstream dependencies
            for dep in current_node_obj.dependencies:
                if dep not in visited:
                    new_path = path + [dep]
                    queue.append((dep, depth + 1, new_path))

            # Check downstream dependents
            for dependent in current_node_obj.dependents:
                if dependent not in visited:
                    new_path = path + [dependent]
                    queue.append((dependent, depth + 1, new_path))

        logger.info(f"Cross-layer tracking completed: path length {len(causal_path)}")
        return causal_path

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
        Enhanced root cause analysis with multiple algorithms

        Args:
            alert: Alert to analyze
            metrics_data: Current metrics data
            context: Additional context information

        Returns:
            List of root cause hypotheses ranked by confidence
        """
        logger.info(f"Performing enhanced root cause analysis for alert: {alert.get('id')}")

        hypotheses = []

        # 1. Pattern-based analysis
        pattern_matches = await self.match_historical_patterns(
            {"alerts": [alert], "metrics": metrics_data}
        )

        for pattern in pattern_matches:
            hypothesis = RootCauseHypothesis(
                hypothesis_id=f"pattern_{pattern.pattern_id}",
                root_cause=pattern.root_cause,
                confidence=pattern.confidence * 0.8,  # Discount for pattern matching
                evidence=[f"Historical pattern match: {pattern.pattern_id}"],
                verification_status="pending",
            )
            hypotheses.append(hypothesis)

        # 2. Topology-based analysis
        causal_path = await self.perform_cross_layer_tracking(alert)
        if len(causal_path) > 1:
            # Use the first node in path as potential root cause
            potential_root = causal_path[0]
            hypothesis = RootCauseHypothesis(
                hypothesis_id=f"topology_{potential_root}",
                root_cause=potential_root,
                confidence=0.6,  # Base confidence for topology-based
                evidence=[f"Topology causal path: {' -> '.join(causal_path)}"],
                causal_path=causal_path,
                verification_status="pending",
            )
            hypotheses.append(hypothesis)

        # 3. Causal graph analysis (if available)
        if CAUSAL_AVAILABLE:
            try:
                causal_hypotheses = await self._causal_graph_analysis(alert, metrics_data)
                hypotheses.extend(causal_hypotheses)
            except Exception as e:
                logger.error(f"Causal graph analysis failed: {e}")

        # 4. ML-based prediction (if available)
        if ML_AVAILABLE and self.pattern_classifier:
            try:
                ml_hypotheses = await self._ml_based_analysis(alert, metrics_data)
                hypotheses.extend(ml_hypotheses)
            except Exception as e:
                logger.error(f"ML-based analysis failed: {e}")

        # Rank hypotheses by confidence
        hypotheses.sort(key=lambda h: h.confidence, reverse=True)

        # Store active hypotheses
        for hypothesis in hypotheses:
            self.active_hypotheses[hypothesis.hypothesis_id] = hypothesis

        logger.info(f"Generated {len(hypotheses)} root cause hypotheses")
        return hypotheses

    async def _causal_graph_analysis(
        self, alert: Dict[str, Any], metrics_data: Dict[str, Any]
    ) -> List[RootCauseHypothesis]:
        """Perform causal graph analysis for root cause detection"""
        # This would use the existing causal analysis infrastructure
        # Simplified implementation for now
        return []

    async def _ml_based_analysis(
        self, alert: Dict[str, Any], metrics_data: Dict[str, Any]
    ) -> List[RootCauseHypothesis]:
        """Perform ML-based root cause analysis"""
        # This would use trained ML models for prediction
        # Simplified implementation for now
        return []

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
        root_cause_exists = hypothesis.root_cause in verification_data.get(
            "affected_components", []
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
            if node not in verification_data.get("active_components", []):
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

        # 4. Check against historical patterns
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
