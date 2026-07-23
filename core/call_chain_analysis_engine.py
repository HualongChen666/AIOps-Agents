# -*- coding: utf-8 -*-
"""
Call Chain Analysis Engine
Analyzes distributed tracing data to identify performance bottlenecks and root causes
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger


class SpanKind(Enum):
    """Span kind types"""

    SERVER = "server"
    CLIENT = "client"
    PRODUCER = "producer"
    CONSUMER = "consumer"
    INTERNAL = "internal"


class SpanStatus(Enum):
    """Span status"""

    OK = "ok"
    ERROR = "error"
    TIMEOUT = "timeout"


@dataclass
class Span:
    """Represents a span in a trace"""

    span_id: str
    trace_id: str
    parent_span_id: Optional[str] = None
    operation_name: str = ""
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = None
    duration_ms: float = 0.0
    kind: SpanKind = SpanKind.INTERNAL
    status: SpanStatus = SpanStatus.OK
    status_message: str = ""
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)
    tags: Dict[str, str] = field(default_factory=dict)

    @property
    def is_error(self) -> bool:
        """Check if span has error status"""
        return self.status != SpanStatus.OK

    @property
    def is_completed(self) -> bool:
        """Check if span is completed"""
        return self.end_time is not None


@dataclass
class Trace:
    """Represents a complete trace with multiple spans"""

    trace_id: str
    root_span_id: str
    spans: List[Span] = field(default_factory=list)
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = None
    duration_ms: float = 0.0
    service_names: List[str] = field(default_factory=list)

    def add_span(self, span: Span) -> None:
        """Add a span to the trace"""
        self.spans.append(span)
        if span.start_time < self.start_time:
            self.start_time = span.start_time
        if span.end_time and (self.end_time is None or span.end_time > self.end_time):
            self.end_time = span.end_time
        self.duration_ms = (
            (self.end_time - self.start_time).total_seconds() * 1000 if self.end_time else 0.0
        )

        # Extract service name from attributes
        service_name = span.attributes.get("service.name") or span.tags.get("service.name")
        if service_name and service_name not in self.service_names:
            self.service_names.append(service_name)

    def get_span_tree(self) -> Dict[str, List[Span]]:
        """Build span tree structure"""
        span_map = {span.span_id: span for span in self.spans}
        tree = defaultdict(list)

        for span in self.spans:
            if span.parent_span_id and span.parent_span_id in span_map:
                tree[span.parent_span_id].append(span)
            else:
                tree[self.root_span_id].append(span)

        return dict(tree)

    def get_error_spans(self) -> List[Span]:
        """Get all error spans in the trace"""
        return [span for span in self.spans if span.is_error]

    def get_slowest_spans(self, limit: int = 10) -> List[Span]:
        """Get slowest spans in the trace"""
        return sorted(self.spans, key=lambda s: s.duration_ms, reverse=True)[:limit]


@dataclass
class PerformanceIssue:
    """Represents a performance issue identified in analysis"""

    issue_type: str  # "slow_operation", "high_latency", "resource_bottleneck"
    severity: str  # "low", "medium", "high", "critical"
    description: str
    affected_spans: List[str] = field(default_factory=list)
    affected_services: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    recommendations: List[str] = field(default_factory=list)


@dataclass
class RootCauseAnalysis:
    """Root cause analysis result"""

    trace_id: str
    root_cause: str
    confidence: float  # 0.0 to 1.0
    contributing_factors: List[str] = field(default_factory=list)
    error_chain: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class CallChainAnalysisEngine:
    """
    Engine for analyzing call chains and identifying issues
    """

    def __init__(self):
        """Initialize the analysis engine"""
        self.traces: Dict[str, Trace] = {}
        self.performance_issues: List[PerformanceIssue] = []
        self.root_cause_analyses: Dict[str, RootCauseAnalysis] = {}
        logger.info("Call chain analysis engine initialized")

    def add_trace(self, trace: Trace) -> None:
        """
        Add a trace for analysis

        Args:
            trace: Trace to analyze
        """
        self.traces[trace.trace_id] = trace
        logger.debug(f"Added trace {trace.trace_id} with {len(trace.spans)} spans")

    def analyze_trace(self, trace_id: str) -> Dict[str, Any]:
        """
        Analyze a specific trace

        Args:
            trace_id: Trace ID to analyze

        Returns:
            Analysis results
        """
        if trace_id not in self.traces:
            logger.warning(f"Trace {trace_id} not found")
            return {"error": "Trace not found"}

        trace = self.traces[trace_id]

        analysis = {
            "trace_id": trace_id,
            "total_duration_ms": trace.duration_ms,
            "total_spans": len(trace.spans),
            "service_count": len(trace.service_names),
            "error_count": len(trace.get_error_spans()),
            "slowest_operations": [
                {
                    "operation": span.operation_name,
                    "duration_ms": span.duration_ms,
                    "service": span.attributes.get("service.name", "unknown"),
                }
                for span in trace.get_slowest_spans(5)
            ],
            "span_tree": self._build_span_tree_summary(trace),
            "performance_issues": self._identify_performance_issues(trace),
            "root_cause": self._analyze_root_cause(trace),
        }

        return analysis

    def _build_span_tree_summary(self, trace: Trace) -> Dict[str, Any]:
        """Build summary of span tree structure"""
        tree = trace.get_span_tree()
        return {
            "root_span_id": trace.root_span_id,
            "total_levels": self._calculate_tree_depth(tree, trace.root_span_id),
            "branching_factor": self._calculate_branching_factor(tree),
            "critical_path": self._identify_critical_path(trace),
        }

    def _calculate_tree_depth(
        self, tree: Dict[str, List[Span]], node_id: str, depth: int = 0
    ) -> int:
        """Calculate maximum depth of span tree"""
        if node_id not in tree or not tree[node_id]:
            return depth

        max_child_depth = depth
        for child_span in tree[node_id]:
            child_depth = self._calculate_tree_depth(tree, child_span.span_id, depth + 1)
            max_child_depth = max(max_child_depth, child_depth)

        return max_child_depth

    def _calculate_branching_factor(self, tree: Dict[str, List[Span]]) -> float:
        """Calculate average branching factor"""
        if not tree:
            return 0.0

        total_children = sum(len(children) for children in tree.values())
        return total_children / len(tree) if tree else 0.0

    def _identify_critical_path(self, trace: Trace) -> List[str]:
        """Identify critical path in trace (longest path)"""
        # Simplified critical path identification
        # In real implementation, would use proper graph algorithms
        sorted_spans = sorted(trace.spans, key=lambda s: s.duration_ms, reverse=True)
        return [span.span_id for span in sorted_spans[:3]]

    def _identify_performance_issues(self, trace: Trace) -> List[Dict[str, Any]]:
        """Identify performance issues in trace"""
        issues = []

        # Identify slow operations
        slow_threshold = 1000  # 1 second
        slow_spans = [span for span in trace.spans if span.duration_ms > slow_threshold]

        if slow_spans:
            issues.append(
                {
                    "type": "slow_operation",
                    "count": len(slow_spans),
                    "slowest_spans": [
                        {
                            "operation": span.operation_name,
                            "duration_ms": span.duration_ms,
                            "service": span.attributes.get("service.name", "unknown"),
                        }
                        for span in slow_spans[:3]
                    ],
                }
            )

        # Identify error patterns
        error_spans = trace.get_error_spans()
        if error_spans:
            issues.append(
                {
                    "type": "error_pattern",
                    "count": len(error_spans),
                    "error_types": list(
                        set(span.status_message for span in error_spans if span.status_message)
                    ),
                }
            )

        return issues

    def _analyze_root_cause(self, trace: Trace) -> Dict[str, Any]:
        """Analyze root cause of issues in trace"""
        error_spans = trace.get_error_spans()

        if not error_spans:
            return {
                "root_cause": "No errors detected",
                "confidence": 1.0,
                "contributing_factors": [],
            }

        # Simplified root cause analysis
        # In real implementation, would use more sophisticated algorithms
        error_types: defaultdict[str, int] = defaultdict(int)
        for span in error_spans:
            error_types[span.status_message or "unknown"] += 1

        most_common_error = max(error_types.items(), key=lambda x: x[1])

        return {
            "root_cause": most_common_error[0],
            "confidence": min(most_common_error[1] / len(error_spans) + 0.5, 1.0),
            "contributing_factors": list(error_types.keys()),
            "error_chain": [span.span_id for span in error_spans],
        }

    def aggregate_traces(self, trace_ids: List[str]) -> Dict[str, Any]:
        """
        Aggregate analysis across multiple traces

        Args:
            trace_ids: List of trace IDs to aggregate

        Returns:
            Aggregated analysis results
        """
        available_traces = [self.traces[tid] for tid in trace_ids if tid in self.traces]

        if not available_traces:
            return {"error": "No valid traces found"}

        total_spans = sum(len(trace.spans) for trace in available_traces)
        total_errors = sum(len(trace.get_error_spans()) for trace in available_traces)
        avg_duration = sum(trace.duration_ms for trace in available_traces) / len(available_traces)

        # Collect all service names
        all_services = set()
        for trace in available_traces:
            all_services.update(trace.service_names)

        return {
            "trace_count": len(available_traces),
            "total_spans": total_spans,
            "total_errors": total_errors,
            "error_rate": total_errors / total_spans if total_spans > 0 else 0.0,
            "average_duration_ms": avg_duration,
            "unique_services": list(all_services),
            "service_count": len(all_services),
        }

    def identify_performance_bottlenecks(
        self, service_name: Optional[str] = None
    ) -> List[PerformanceIssue]:
        """
        Identify performance bottlenecks across all traces

        Args:
            service_name: Optional filter by service name

        Returns:
            List of performance issues
        """
        bottlenecks = []

        for trace in self.traces.values():
            if service_name and service_name not in trace.service_names:
                continue

            # Check for slow operations
            slow_spans = [span for span in trace.spans if span.duration_ms > 2000]  # 2 seconds
            for span in slow_spans:
                issue = PerformanceIssue(
                    issue_type="slow_operation",
                    severity="high" if span.duration_ms > 5000 else "medium",
                    description=f"Slow operation detected: {span.operation_name}",
                    affected_spans=[span.span_id],
                    affected_services=[span.attributes.get("service.name", "unknown")],
                    metrics={"duration_ms": span.duration_ms},
                    recommendations=[
                        "Optimize database queries",
                        "Add caching",
                        "Review algorithm complexity",
                    ],
                )
                bottlenecks.append(issue)

        # Sort by severity and duration
        bottlenecks.sort(key=lambda x: (x.severity, x.metrics.get("duration_ms", 0)), reverse=True)

        return bottlenecks[:20]  # Return top 20 bottlenecks

    def get_engine_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the analysis engine

        Returns:
            Engine statistics
        """
        return {
            "total_traces": len(self.traces),
            "total_spans": sum(len(trace.spans) for trace in self.traces.values()),
            "total_performance_issues": len(self.performance_issues),
            "total_root_cause_analyses": len(self.root_cause_analyses),
            "memory_usage": "N/A",  # Could add actual memory tracking
        }

    def search_by_trace_id(self, trace_id: str) -> Optional[Trace]:
        """
        Search for a trace by ID

        Args:
            trace_id: Trace ID to search for

        Returns:
            Trace if found, None otherwise
        """
        return self.traces.get(trace_id)

    def filter_by_service_name(self, service_name: str) -> List[Trace]:
        """
        Filter traces by service name

        Args:
            service_name: Service name to filter by

        Returns:
            List of traces that involve the specified service
        """
        return [trace for trace in self.traces.values() if service_name in trace.service_names]

    def filter_by_time_range(self, start_time: datetime, end_time: datetime) -> List[Trace]:
        """
        Filter traces by time range

        Args:
            start_time: Start of time range
            end_time: End of time range

        Returns:
            List of traces within the time range
        """
        return [
            trace for trace in self.traces.values() if start_time <= trace.start_time <= end_time
        ]

    def filter_by_duration(
        self, min_duration_ms: Optional[float] = None, max_duration_ms: Optional[float] = None
    ) -> List[Trace]:
        """
        Filter traces by duration

        Args:
            min_duration_ms: Minimum duration in milliseconds
            max_duration_ms: Maximum duration in milliseconds

        Returns:
            List of traces matching duration criteria
        """
        filtered = []
        for trace in self.traces.values():
            if min_duration_ms is not None and trace.duration_ms < min_duration_ms:
                continue
            if max_duration_ms is not None and trace.duration_ms > max_duration_ms:
                continue
            filtered.append(trace)
        return filtered

    def filter_by_tags(self, tags: Dict[str, str]) -> List[Trace]:
        """
        Filter traces by tags

        Args:
            tags: Dictionary of tag key-value pairs to match

        Returns:
            List of traces with matching tags
        """
        filtered = []
        for trace in self.traces.values():
            # Check if any span in the trace has all the specified tags
            for span in trace.spans:
                if all(span.tags.get(key) == value for key, value in tags.items()):
                    filtered.append(trace)
                    break
        return filtered

    def filter_by_error_status(self, has_errors: bool = True) -> List[Trace]:
        """
        Filter traces by error status

        Args:
            has_errors: If True, return traces with errors; if False, return traces without errors

        Returns:
            List of traces matching error status criteria
        """
        if has_errors:
            return [trace for trace in self.traces.values() if trace.get_error_spans()]
        else:
            return [trace for trace in self.traces.values() if not trace.get_error_spans()]

    def search_spans_by_operation(self, operation_name: str) -> List[Span]:
        """
        Search for spans by operation name

        Args:
            operation_name: Operation name to search for

        Returns:
            List of spans matching the operation name
        """
        matching_spans = []
        for trace in self.traces.values():
            matching_spans.extend(
                [
                    span
                    for span in trace.spans
                    if operation_name.lower() in span.operation_name.lower()
                ]
            )
        return matching_spans

    def advanced_search(
        self,
        trace_id: Optional[str] = None,
        service_name: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        min_duration_ms: Optional[float] = None,
        max_duration_ms: Optional[float] = None,
        tags: Optional[Dict[str, str]] = None,
        has_errors: Optional[bool] = None,
        operation_name: Optional[str] = None,
    ) -> List[Trace]:
        """
        Advanced search with multiple filters

        Args:
            trace_id: Filter by trace ID
            service_name: Filter by service name
            start_time: Filter by start time
            end_time: Filter by end time
            min_duration_ms: Filter by minimum duration
            max_duration_ms: Filter by maximum duration
            tags: Filter by tags
            has_errors: Filter by error status
            operation_name: Filter by operation name in spans

        Returns:
            List of traces matching all specified criteria
        """
        filtered = list(self.traces.values())

        # Filter by trace ID
        if trace_id:
            filtered = [trace for trace in filtered if trace.trace_id == trace_id]

        # Filter by service name
        if service_name:
            filtered = [trace for trace in filtered if service_name in trace.service_names]

        # Filter by time range
        if start_time:
            filtered = [trace for trace in filtered if trace.start_time >= start_time]
        if end_time:
            filtered = [trace for trace in filtered if trace.start_time <= end_time]

        # Filter by duration
        if min_duration_ms:
            filtered = [trace for trace in filtered if trace.duration_ms >= min_duration_ms]
        if max_duration_ms:
            filtered = [trace for trace in filtered if trace.duration_ms <= max_duration_ms]

        # Filter by tags
        if tags:
            filtered = [
                trace
                for trace in filtered
                if any(
                    all(span.tags.get(key) == value for key, value in tags.items())
                    for span in trace.spans
                )
            ]

        # Filter by error status
        if has_errors is not None:
            if has_errors:
                filtered = [trace for trace in filtered if trace.get_error_spans()]
            else:
                filtered = [trace for trace in filtered if not trace.get_error_spans()]

        # Filter by operation name in spans
        if operation_name:
            filtered = [
                trace
                for trace in filtered
                if any(
                    operation_name.lower() in span.operation_name.lower() for span in trace.spans
                )
            ]

        return filtered


# Global instance
_analysis_engine: Optional[CallChainAnalysisEngine] = None


def get_call_chain_analysis_engine() -> CallChainAnalysisEngine:
    """
    Get the global call chain analysis engine instance

    Returns:
        CallChainAnalysisEngine instance
    """
    global _analysis_engine
    if _analysis_engine is None:
        _analysis_engine = CallChainAnalysisEngine()
    return _analysis_engine
