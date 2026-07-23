# -*- coding: utf-8 -*-
"""
Call Chain Analysis Engine
Enterprise-grade call chain analysis with bottleneck detection and root cause analysis
"""

import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, TypedDict

from loguru import logger


class BaselineData(TypedDict):
    """Baseline data structure for service-operation pairs"""

    durations: List[float]
    error_count: int
    total_count: int


class AnalysisType(Enum):
    """Analysis type"""

    PERFORMANCE_BOTTLENECK = "performance_bottleneck"
    ANOMALY_DETECTION = "anomaly_detection"
    ERROR_ANALYSIS = "error_analysis"
    ROOT_CAUSE_ANALYSIS = "root_cause_analysis"
    DEPENDENCY_ANALYSIS = "dependency_analysis"


class Severity(Enum):
    """Severity level"""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class CallChainNode:
    """Call chain node"""

    span_id: str
    parent_span_id: Optional[str]
    operation_name: str
    service_name: str
    start_time: datetime
    end_time: datetime
    duration_ms: float
    self_duration_ms: float
    status: str
    error_message: Optional[str] = None
    children: List["CallChainNode"] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceBottleneck:
    """Performance bottleneck"""

    bottleneck_id: str
    service_name: str
    operation_name: str
    severity: Severity
    avg_duration_ms: float
    baseline_duration_ms: float
    degradation_percentage: float
    frequency: int
    impact_score: float
    recommendations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Anomaly:
    """Detected anomaly"""

    anomaly_id: str
    anomaly_type: str
    service_name: str
    metric_name: str
    severity: Severity
    detected_at: datetime
    value: float
    expected_value: float
    deviation_percentage: float
    description: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RootCause:
    """Root cause analysis result"""

    root_cause_id: str
    issue_type: str
    severity: Severity
    confidence: float
    root_cause_service: str
    root_cause_operation: str
    contributing_factors: List[str] = field(default_factory=list)
    evidence: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class CallChainAnalysisEngine:
    """Enterprise-grade call chain analysis engine"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize call chain analysis engine

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # Call chain data storage
        self.call_chains: Dict[str, List[CallChainNode]] = {}

        # Analysis results storage
        self.bottlenecks: List[PerformanceBottleneck] = []
        self.anomalies: List[Anomaly] = []
        self.root_causes: List[RootCause] = []

        # Baseline data for comparison
        self.baseline_data: Dict[str, BaselineData] = {}

        # Statistics
        self.total_analyses = 0
        self.bottlenecks_detected = 0
        self.anomalies_detected = 0
        self.root_causes_identified = 0

        logger.info("Call chain analysis engine initialized")

    def add_call_chain(self, trace_id: str, call_chain: List[CallChainNode]) -> None:
        """
        Add call chain for analysis

        Args:
            trace_id: Trace ID
            call_chain: Call chain nodes
        """
        self.call_chains[trace_id] = call_chain

        # Update baseline data
        self._update_baseline_data(call_chain)

        logger.debug(f"Added call chain: {trace_id}")

    def _update_baseline_data(self, call_chain: List[CallChainNode]) -> None:
        """
        Update baseline data with call chain

        Args:
            call_chain: Call chain nodes
        """
        for node in call_chain:
            key = f"{node.service_name}.{node.operation_name}"

            if key not in self.baseline_data:
                self.baseline_data[key] = {"durations": [], "error_count": 0, "total_count": 0}

            self.baseline_data[key]["durations"].append(node.duration_ms)
            self.baseline_data[key]["total_count"] += 1

            if node.status != "OK":
                self.baseline_data[key]["error_count"] += 1

    def analyze_performance_bottlenecks(self) -> List[PerformanceBottleneck]:
        """
        Analyze performance bottlenecks

        Returns:
            List of detected bottlenecks
        """
        bottlenecks = []

        # Analyze each service-operation pair
        for key, data in self.baseline_data.items():
            service_name, operation_name = key.split(".", 1)

            durations = data["durations"]
            if not durations:
                continue

            avg_duration = statistics.mean(durations)

            # Calculate baseline (median of historical data)
            baseline_duration = statistics.median(durations)

            # Detect degradation
            degradation = (
                (avg_duration - baseline_duration) / baseline_duration
                if baseline_duration > 0
                else 0
            )

            if degradation > 0.5:  # 50% degradation threshold
                severity = self._calculate_bottleneck_severity(degradation, avg_duration)

                bottleneck = PerformanceBottleneck(
                    bottleneck_id=(
                        f"bottleneck_{key}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
                    ),
                    service_name=service_name,
                    operation_name=operation_name,
                    severity=severity,
                    avg_duration_ms=avg_duration,
                    baseline_duration_ms=baseline_duration,
                    degradation_percentage=degradation * 100,
                    frequency=data["total_count"],
                    impact_score=self._calculate_impact_score(degradation, data["total_count"]),
                    recommendations=self._generate_bottleneck_recommendations(
                        service_name, operation_name, degradation
                    ),
                )

                bottlenecks.append(bottleneck)
                self.bottlenecks_detected += 1

        self.bottlenecks.extend(bottlenecks)
        self.total_analyses += 1

        logger.info(f"Detected {len(bottlenecks)} performance bottlenecks")

        return bottlenecks

    def _calculate_bottleneck_severity(self, degradation: float, duration: float) -> Severity:
        """
        Calculate bottleneck severity

        Args:
            degradation: Performance degradation percentage
            duration: Average duration in milliseconds

        Returns:
            Severity level
        """
        if degradation > 2.0 or duration > 5000:  # >200% degradation or >5s
            return Severity.CRITICAL
        elif degradation > 1.0 or duration > 1000:  # >100% degradation or >1s
            return Severity.HIGH
        elif degradation > 0.5 or duration > 500:  # >50% degradation or >500ms
            return Severity.MEDIUM
        else:
            return Severity.LOW

    def _calculate_impact_score(self, degradation: float, frequency: int) -> float:
        """
        Calculate impact score for bottleneck

        Args:
            degradation: Performance degradation
            frequency: Frequency of occurrence

        Returns:
            Impact score (0-100)
        """
        # Normalize degradation to 0-1 range (assuming max 200% degradation)
        normalized_degradation = min(degradation / 2.0, 1.0)

        # Normalize frequency to 0-1 range (assuming max 1000 occurrences)
        normalized_frequency = min(frequency / 1000.0, 1.0)

        # Calculate weighted impact score
        impact_score = (normalized_degradation * 0.7 + normalized_frequency * 0.3) * 100

        return round(impact_score, 2)

    def _generate_bottleneck_recommendations(
        self, service_name: str, operation_name: str, degradation: float
    ) -> List[str]:
        """
        Generate recommendations for bottleneck

        Args:
            service_name: Service name
            operation_name: Operation name
            degradation: Performance degradation

        Returns:
            List of recommendations
        """
        recommendations = []

        if degradation > 1.0:
            recommendations.append(
                f"Review {service_name}.{operation_name} for performance optimization"
            )
            recommendations.append("Consider implementing caching for this operation")
            recommendations.append("Optimize database queries if applicable")

        if degradation > 0.5:
            recommendations.append("Monitor resource utilization for this service")
            recommendations.append("Consider horizontal scaling if load is high")

        recommendations.append("Review recent code changes for potential regressions")
        recommendations.append("Check for external service dependencies that may be causing delays")

        return recommendations

    def analyze_anomalies(self, threshold: float = 2.0) -> List[Anomaly]:
        """
        Detect anomalies in call chains

        Args:
            threshold: Standard deviation threshold for anomaly detection

        Returns:
            List of detected anomalies
        """
        anomalies = []

        for key, data in self.baseline_data.items():
            service_name, operation_name = key.split(".", 1)

            durations = data["durations"]
            if len(durations) < 10:  # Need minimum data points
                continue

            # Calculate statistics
            mean_duration = statistics.mean(durations)
            std_duration = statistics.stdev(durations) if len(durations) > 1 else 0

            if std_duration == 0:
                continue

            # Detect anomalies using z-score
            for duration in durations[-10:]:  # Check recent 10 data points
                z_score = (duration - mean_duration) / std_duration if std_duration > 0 else 0

                if abs(z_score) > threshold:
                    severity = (
                        Severity.CRITICAL
                        if abs(z_score) > 4
                        else Severity.HIGH if abs(z_score) > 3 else Severity.MEDIUM
                    )

                    anomaly = Anomaly(
                        anomaly_id=(
                            f"anomaly_{key}_"
                            f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')}"
                        ),
                        anomaly_type="duration_anomaly",
                        service_name=service_name,
                        metric_name="duration_ms",
                        severity=severity,
                        detected_at=datetime.now(timezone.utc),
                        value=duration,
                        expected_value=mean_duration,
                        deviation_percentage=(
                            ((duration - mean_duration) / mean_duration) * 100
                            if mean_duration > 0
                            else 0
                        ),
                        description=(
                            f"Duration anomaly detected for {service_name}."
                            f"{operation_name}: {duration:.2f}ms "
                            f"(expected: {mean_duration:.2f}ms, z-score: {z_score:.2f})"
                        ),
                    )

                    anomalies.append(anomaly)
                    self.anomalies_detected += 1

        self.anomalies.extend(anomalies)
        self.total_analyses += 1

        logger.info(f"Detected {len(anomalies)} anomalies")

        return anomalies

    def analyze_root_causes(self, trace_id: str) -> List[RootCause]:
        """
        Analyze root causes for issues in a trace

        Args:
            trace_id: Trace ID

        Returns:
            List of identified root causes
        """
        if trace_id not in self.call_chains:
            return []

        call_chain = self.call_chains[trace_id]
        root_causes = []

        # Find error nodes in the call chain
        error_nodes = self._find_error_nodes(call_chain)

        for error_node in error_nodes:
            root_cause = self._analyze_error_root_cause(error_node, call_chain)
            if root_cause:
                root_causes.append(root_cause)
                self.root_causes_identified += 1

        self.total_analyses += 1

        logger.info(f"Identified {len(root_causes)} root causes for trace {trace_id}")

        return root_causes

    def _find_error_nodes(self, call_chain: List[CallChainNode]) -> List[CallChainNode]:
        """
        Find error nodes in call chain

        Args:
            call_chain: Call chain nodes

        Returns:
            List of error nodes
        """
        error_nodes = []

        for node in call_chain:
            if node.status != "OK":
                error_nodes.append(node)

            # Recursively check children
            if node.children:
                error_nodes.extend(self._find_error_nodes(node.children))

        return error_nodes

    def _analyze_error_root_cause(
        self, error_node: CallChainNode, call_chain: List[CallChainNode]
    ) -> Optional[RootCause]:
        """
        Analyze root cause for an error node

        Args:
            error_node: Error node
            call_chain: Full call chain

        Returns:
            Root cause analysis result
        """
        # Determine error type
        error_type = self._classify_error(error_node)

        # Find contributing factors
        contributing_factors = self._identify_contributing_factors(error_node, call_chain)

        # Calculate confidence
        confidence = self._calculate_root_cause_confidence(error_node, contributing_factors)

        # Generate recommendations
        recommendations = self._generate_root_cause_recommendations(
            error_type, error_node.service_name, error_node.operation_name
        )

        root_cause = RootCause(
            root_cause_id=(
                f"root_cause_{error_node.span_id}_"
                f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
            ),
            issue_type=error_type,
            severity=self._calculate_error_severity(error_node),
            confidence=confidence,
            root_cause_service=error_node.service_name,
            root_cause_operation=error_node.operation_name,
            contributing_factors=contributing_factors,
            evidence={
                "error_message": error_node.error_message,
                "duration_ms": error_node.duration_ms,
                "attributes": error_node.attributes,
            },
            recommendations=recommendations,
        )

        return root_cause

    def _classify_error(self, error_node: CallChainNode) -> str:
        """
        Classify error type

        Args:
            error_node: Error node

        Returns:
            Error type
        """
        error_message = error_node.error_message or ""

        if "timeout" in error_message.lower():
            return "timeout_error"
        elif "connection" in error_message.lower():
            return "connection_error"
        elif "database" in error_message.lower() or "sql" in error_message.lower():
            return "database_error"
        elif "network" in error_message.lower():
            return "network_error"
        elif "permission" in error_message.lower() or "unauthorized" in error_message.lower():
            return "authorization_error"
        else:
            return "application_error"

    def _identify_contributing_factors(
        self, error_node: CallChainNode, call_chain: List[CallChainNode]
    ) -> List[str]:
        """
        Identify contributing factors for error

        Args:
            error_node: Error node
            call_chain: Full call chain

        Returns:
            List of contributing factors
        """
        factors = []

        # Check duration
        if error_node.duration_ms > 1000:
            factors.append("high_duration")

        # Check if parent had errors
        if error_node.parent_span_id:
            parent = self._find_node_by_id(error_node.parent_span_id, call_chain)
            if parent and parent.status != "OK":
                factors.append("parent_error")

        # Check service-specific factors
        if error_node.service_name in self.baseline_data:
            baseline = self.baseline_data[error_node.service_name]
            if baseline["error_count"] / baseline["total_count"] > 0.1:
                factors.append("high_service_error_rate")

        return factors

    def _find_node_by_id(
        self, span_id: str, call_chain: List[CallChainNode]
    ) -> Optional[CallChainNode]:
        """
        Find node by span ID

        Args:
            span_id: Span ID
            call_chain: Call chain nodes

        Returns:
            Node or None
        """
        for node in call_chain:
            if node.span_id == span_id:
                return node
            if node.children:
                found = self._find_node_by_id(span_id, node.children)
                if found:
                    return found
        return None

    def _calculate_root_cause_confidence(
        self, error_node: CallChainNode, factors: List[str]
    ) -> float:
        """
        Calculate confidence in root cause analysis

        Args:
            error_node: Error node
            factors: Contributing factors

        Returns:
            Confidence score (0-1)
        """
        confidence = 0.5  # Base confidence

        # Increase confidence with more factors
        confidence += len(factors) * 0.1

        # Increase confidence if error message is specific
        if error_node.error_message and len(error_node.error_message) > 10:
            confidence += 0.1

        # Cap confidence at 1.0
        confidence = min(confidence, 1.0)

        return round(confidence, 2)

    def _calculate_error_severity(self, error_node: CallChainNode) -> Severity:
        """
        Calculate error severity

        Args:
            error_node: Error node

        Returns:
            Severity level
        """
        if error_node.duration_ms > 5000:
            return Severity.CRITICAL
        elif error_node.duration_ms > 1000:
            return Severity.HIGH
        elif error_node.duration_ms > 500:
            return Severity.MEDIUM
        else:
            return Severity.LOW

    def _generate_root_cause_recommendations(
        self, error_type: str, service_name: str, operation_name: str
    ) -> List[str]:
        """
        Generate recommendations for root cause

        Args:
            error_type: Error type
            service_name: Service name
            operation_name: Operation name

        Returns:
            List of recommendations
        """
        recommendations = []

        if error_type == "timeout_error":
            recommendations.append("Increase timeout configuration for this operation")
            recommendations.append("Optimize the operation to reduce execution time")
            recommendations.append("Check for network latency issues")

        elif error_type == "connection_error":
            recommendations.append("Verify service connectivity and availability")
            recommendations.append("Check firewall and network configuration")
            recommendations.append("Implement retry logic with exponential backoff")

        elif error_type == "database_error":
            recommendations.append("Review database query performance")
            recommendations.append("Check database connection pool configuration")
            recommendations.append("Verify database schema and indexes")

        elif error_type == "authorization_error":
            recommendations.append("Review user permissions and access controls")
            recommendations.append("Check authentication token validity")
            recommendations.append("Verify service account credentials")

        else:
            recommendations.append(f"Review {service_name}.{operation_name} implementation")
            recommendations.append("Check application logs for detailed error information")
            recommendations.append("Implement proper error handling and logging")

        return recommendations

    def get_statistics(self) -> Dict[str, Any]:
        """Get analysis statistics"""
        return {
            "total_analyses": self.total_analyses,
            "bottlenecks_detected": self.bottlenecks_detected,
            "anomalies_detected": self.anomalies_detected,
            "root_causes_identified": self.root_causes_identified,
            "total_call_chains": len(self.call_chains),
            "total_services_analyzed": len(self.baseline_data),
        }


def get_call_chain_analysis_engine(
    config: Optional[Dict[str, Any]] = None,
) -> CallChainAnalysisEngine:
    """
    Factory function to get call chain analysis engine instance

    Args:
        config: Optional configuration dictionary

    Returns:
        CallChainAnalysisEngine: Analysis engine instance
    """
    return CallChainAnalysisEngine(config)
