# -*- coding: utf-8 -*-
"""
Tracing Data Visualization
Enterprise-grade tracing data visualization with dashboards and analytics
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger


class VisualizationType(Enum):
    """Visualization type"""

    TRACE_VIEW = "trace_view"
    SERVICE_MAP = "service_map"
    DEPENDENCY_GRAPH = "dependency_graph"
    FLAME_GRAPH = "flame_graph"
    GANTT_CHART = "gantt_chart"
    TIMELINE = "timeline"
    METRICS_DASHBOARD = "metrics_dashboard"


class TimeRange(Enum):
    """Time range for visualization"""

    LAST_15_MINUTES = "15m"
    LAST_30_MINUTES = "30m"
    LAST_1_HOUR = "1h"
    LAST_6_HOURS = "6h"
    LAST_24_HOURS = "24h"
    LAST_7_DAYS = "7d"
    CUSTOM = "custom"


@dataclass
class TraceData:
    """Trace data structure"""

    trace_id: str
    root_span_id: str
    service_name: str
    operation_name: str
    start_time: datetime
    end_time: datetime
    duration_ms: float
    status: str
    spans: List[Dict[str, Any]] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ServiceNode:
    """Service node for service map"""

    service_name: str
    request_count: int = 0
    error_count: int = 0
    avg_duration_ms: float = 0.0
    p95_duration_ms: float = 0.0
    p99_duration_ms: float = 0.0
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SpanNode:
    """Span node for flame graph"""

    span_id: str
    parent_span_id: Optional[str]
    operation_name: str
    service_name: str
    start_time: datetime
    duration_ms: float
    self_duration_ms: float
    children: List["SpanNode"] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)


class TracingVisualizationManager:
    """Enterprise-grade tracing visualization manager"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize tracing visualization manager

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # Trace data storage
        self.trace_data: Dict[str, TraceData] = {}

        # Service map data
        self.service_map: Dict[str, ServiceNode] = {}

        # Visualization cache
        self.visualization_cache: Dict[str, Any] = {}

        # Statistics
        self.total_traces = 0
        self.visualizations_generated = 0

        logger.info("Tracing visualization manager initialized")

    def add_trace_data(self, trace_data: TraceData) -> None:
        """
        Add trace data to storage

        Args:
            trace_data: Trace data
        """
        self.trace_data[trace_data.trace_id] = trace_data
        self.total_traces += 1

        # Update service map
        self._update_service_map(trace_data)

        logger.debug(f"Added trace data: {trace_data.trace_id}")

    def _update_service_map(self, trace_data: TraceData) -> None:
        """
        Update service map with trace data

        Args:
            trace_data: Trace data
        """
        # Extract service names from spans
        services = set()
        for span in trace_data.spans:
            service_name = span.get("service_name", "unknown")
            services.add(service_name)

        # Update service nodes
        for service_name in services:
            if service_name not in self.service_map:
                self.service_map[service_name] = ServiceNode(service_name=service_name)

            node = self.service_map[service_name]
            node.request_count += 1

            if trace_data.status != "OK":
                node.error_count += 1

            # Update duration statistics
            durations = [
                span.get("duration_ms", 0)
                for span in trace_data.spans
                if span.get("service_name") == service_name
            ]

            if durations:
                node.avg_duration_ms = sum(durations) / len(durations)
                sorted_durations = sorted(durations)
                node.p95_duration_ms = sorted_durations[int(len(sorted_durations) * 0.95)]
                node.p99_duration_ms = sorted_durations[int(len(sorted_durations) * 0.99)]

    def generate_trace_view(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """
        Generate trace view visualization

        Args:
            trace_id: Trace ID

        Returns:
            Trace view data
        """
        if trace_id not in self.trace_data:
            return None

        trace = self.trace_data[trace_id]

        # Build span tree
        span_tree = self._build_span_tree(trace.spans)

        # Calculate span statistics
        span_stats = self._calculate_span_statistics(trace.spans)

        visualization = {
            "visualization_type": VisualizationType.TRACE_VIEW.value,
            "trace_id": trace.trace_id,
            "service_name": trace.service_name,
            "operation_name": trace.operation_name,
            "start_time": trace.start_time.isoformat(),
            "end_time": trace.end_time.isoformat(),
            "duration_ms": trace.duration_ms,
            "status": trace.status,
            "span_tree": span_tree,
            "span_statistics": span_stats,
            "attributes": trace.attributes,
        }

        self.visualizations_generated += 1

        return visualization

    def _build_span_tree(self, spans: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Build span tree from flat span list

        Args:
            spans: Flat span list

        Returns:
            Span tree structure
        """
        span_map = {}
        root_spans = []

        # Create span nodes
        for span in spans:
            span_id = span.get("span_id")
            parent_span_id = span.get("parent_span_id")

            span_node = {
                "span_id": span_id,
                "parent_span_id": parent_span_id,
                "operation_name": span.get("operation_name", ""),
                "service_name": span.get("service_name", ""),
                "start_time": span.get("start_time"),
                "duration_ms": span.get("duration_ms", 0),
                "status": span.get("status", "OK"),
                "children": [],
                "attributes": span.get("attributes", {}),
            }

            span_map[span_id] = span_node

            if not parent_span_id:
                root_spans.append(span_node)

        # Build tree structure
        for span_node in span_map.values():
            parent_span_id = span_node["parent_span_id"]
            if parent_span_id and parent_span_id in span_map:
                span_map[parent_span_id]["children"].append(span_node)

        return {"roots": root_spans, "total_spans": len(spans)}

    def _calculate_span_statistics(self, spans: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate span statistics

        Args:
            spans: Span list

        Returns:
            Span statistics
        """
        total_spans = len(spans)
        if total_spans == 0:
            return {}

        durations = [span.get("duration_ms", 0) for span in spans]
        error_count = sum(1 for span in spans if span.get("status") != "OK")

        sorted_durations = sorted(durations)

        return {
            "total_spans": total_spans,
            "error_count": error_count,
            "error_rate": error_count / total_spans,
            "min_duration_ms": min(durations),
            "max_duration_ms": max(durations),
            "avg_duration_ms": sum(durations) / total_spans,
            "median_duration_ms": sorted_durations[total_spans // 2],
            "p95_duration_ms": sorted_durations[int(total_spans * 0.95)],
            "p99_duration_ms": sorted_durations[int(total_spans * 0.99)],
        }

    def generate_service_map(self) -> Dict[str, Any]:
        """
        Generate service map visualization

        Returns:
            Service map data
        """
        nodes = []
        edges = []

        for service_name, node in self.service_map.items():
            nodes.append(
                {
                    "service_name": service_name,
                    "request_count": node.request_count,
                    "error_count": node.error_count,
                    "error_rate": (
                        node.error_count / node.request_count if node.request_count > 0 else 0
                    ),
                    "avg_duration_ms": node.avg_duration_ms,
                    "p95_duration_ms": node.p95_duration_ms,
                    "p99_duration_ms": node.p99_duration_ms,
                }
            )

            # Create edges for dependencies
            for dependency in node.dependencies:
                edges.append({"source": service_name, "target": dependency})

        visualization = {
            "visualization_type": VisualizationType.SERVICE_MAP.value,
            "nodes": nodes,
            "edges": edges,
            "total_services": len(nodes),
            "total_edges": len(edges),
        }

        self.visualizations_generated += 1

        return visualization

    def generate_flame_graph(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """
        Generate flame graph visualization

        Args:
            trace_id: Trace ID

        Returns:
            Flame graph data
        """
        if trace_id not in self.trace_data:
            return None

        trace = self.trace_data[trace_id]

        # Build flame graph tree
        flame_tree = self._build_flame_tree(trace.spans)

        visualization = {
            "visualization_type": VisualizationType.FLAME_GRAPH.value,
            "trace_id": trace_id,
            "flame_tree": flame_tree,
            "total_spans": len(trace.spans),
        }

        self.visualizations_generated += 1

        return visualization

    def _build_flame_tree(self, spans: List[Dict[str, Any]]) -> List[SpanNode]:
        """
        Build flame graph tree

        Args:
            spans: Span list

        Returns:
            Flame graph tree
        """
        span_map = {}
        root_nodes = []

        # Create span nodes
        for span in spans:
            span_id = span.get("span_id")
            parent_span_id = span.get("parent_span_id")

            if span_id is None:
                continue

            span_node = SpanNode(
                span_id=span_id,
                parent_span_id=parent_span_id,
                operation_name=span.get("operation_name", ""),
                service_name=span.get("service_name", ""),
                start_time=datetime.fromisoformat(span.get("start_time", "")),
                duration_ms=span.get("duration_ms", 0),
                self_duration_ms=span.get("duration_ms", 0),
                attributes=span.get("attributes", {}),
            )

            span_map[span_id] = span_node

            if not parent_span_id:
                root_nodes.append(span_node)

        # Build tree structure and calculate self duration
        for span_node in span_map.values():
            parent_span_id = span_node.parent_span_id
            if parent_span_id and parent_span_id in span_map:
                span_map[parent_span_id].children.append(span_node)

        # Calculate self duration (excluding children)
        for span_node in span_map.values():
            children_duration = sum(child.duration_ms for child in span_node.children)
            span_node.self_duration_ms = max(0, span_node.duration_ms - children_duration)

        return root_nodes

    def generate_gantt_chart(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """
        Generate Gantt chart visualization

        Args:
            trace_id: Trace ID

        Returns:
            Gantt chart data
        """
        if trace_id not in self.trace_data:
            return None

        trace = self.trace_data[trace_id]

        # Build Gantt chart data
        gantt_data = []
        for span in trace.spans:
            gantt_data.append(
                {
                    "span_id": span.get("span_id"),
                    "parent_span_id": span.get("parent_span_id"),
                    "operation_name": span.get("operation_name", ""),
                    "service_name": span.get("service_name", ""),
                    "start_time": span.get("start_time"),
                    "duration_ms": span.get("duration_ms", 0),
                    "status": span.get("status", "OK"),
                }
            )

        visualization = {
            "visualization_type": VisualizationType.GANTT_CHART.value,
            "trace_id": trace_id,
            "gantt_data": gantt_data,
            "total_spans": len(gantt_data),
        }

        self.visualizations_generated += 1

        return visualization

    def generate_metrics_dashboard(
        self, time_range: TimeRange = TimeRange.LAST_24_HOURS
    ) -> Dict[str, Any]:
        """
        Generate metrics dashboard visualization

        Args:
            time_range: Time range for metrics

        Returns:
            Metrics dashboard data
        """
        # Filter traces by time range
        cutoff_time = self._get_cutoff_time(time_range)
        filtered_traces = [
            trace for trace in self.trace_data.values() if trace.start_time >= cutoff_time
        ]

        # Calculate metrics
        total_traces = len(filtered_traces)
        error_traces = sum(1 for trace in filtered_traces if trace.status != "OK")

        durations = [trace.duration_ms for trace in filtered_traces]

        # Service-level metrics
        service_metrics = {}
        for service_name, node in self.service_map.items():
            service_metrics[service_name] = {
                "request_count": node.request_count,
                "error_count": node.error_count,
                "error_rate": (
                    node.error_count / node.request_count if node.request_count > 0 else 0
                ),
                "avg_duration_ms": node.avg_duration_ms,
                "p95_duration_ms": node.p95_duration_ms,
            }

        visualization = {
            "visualization_type": VisualizationType.METRICS_DASHBOARD.value,
            "time_range": time_range.value,
            "total_traces": total_traces,
            "error_traces": error_traces,
            "error_rate": error_traces / total_traces if total_traces > 0 else 0,
            "avg_duration_ms": sum(durations) / len(durations) if durations else 0,
            "p95_duration_ms": (
                sorted(durations)[int(len(durations) * 0.95)] if len(durations) > 0 else 0
            ),
            "service_metrics": service_metrics,
            "total_services": len(service_metrics),
        }

        self.visualizations_generated += 1

        return visualization

    def _get_cutoff_time(self, time_range: TimeRange) -> datetime:
        """
        Get cutoff time for time range

        Args:
            time_range: Time range

        Returns:
            Cutoff datetime
        """
        now = datetime.now(timezone.utc)

        if time_range == TimeRange.LAST_15_MINUTES:
            return now - timedelta(minutes=15)
        elif time_range == TimeRange.LAST_30_MINUTES:
            return now - timedelta(minutes=30)
        elif time_range == TimeRange.LAST_1_HOUR:
            return now - timedelta(hours=1)
        elif time_range == TimeRange.LAST_6_HOURS:
            return now - timedelta(hours=6)
        elif time_range == TimeRange.LAST_24_HOURS:
            return now - timedelta(hours=24)
        elif time_range == TimeRange.LAST_7_DAYS:
            return now - timedelta(days=7)
        else:
            return now - timedelta(hours=1)

    def get_statistics(self) -> Dict[str, Any]:
        """Get visualization statistics"""
        return {
            "total_traces": self.total_traces,
            "total_services": len(self.service_map),
            "visualizations_generated": self.visualizations_generated,
            "cache_size": len(self.visualization_cache),
        }


def get_tracing_visualization_manager(
    config: Optional[Dict[str, Any]] = None,
) -> TracingVisualizationManager:
    """
    Factory function to get tracing visualization manager instance

    Args:
        config: Optional configuration dictionary

    Returns:
        TracingVisualizationManager: Visualization manager instance
    """
    return TracingVisualizationManager(config)
