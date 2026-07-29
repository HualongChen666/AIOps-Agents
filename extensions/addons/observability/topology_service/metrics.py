# -*- coding: utf-8 -*-
"""Prometheus metrics for the topology microservice."""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

TOPOLOGY_DISCOVERED_NODES = Counter(
    "topology_discovered_nodes_total",
    "Total number of discovered topology nodes",
    ["source"],
)
TOPOLOGY_DISCOVERED_EDGES = Counter(
    "topology_discovered_edges_total",
    "Total number of discovered topology edges",
    ["source"],
)
TOPOLOGY_DISCOVERY_DURATION = Histogram(
    "topology_discovery_duration_seconds",
    "Time spent discovering topology",
    ["source"],
)
TOPOLOGY_IMPACT_ANALYSIS_DURATION = Histogram(
    "topology_impact_analysis_duration_seconds",
    "Time spent analyzing topology impact",
    ["direction"],
)
TOPOLOGY_VISUALIZATION_REQUESTS = Counter(
    "topology_visualization_requests_total",
    "Total number of visualization requests",
    ["layout"],
)
TOPOLOGY_REALTIME_MESSAGES = Counter(
    "topology_realtime_messages_total",
    "Total number of real-time topology messages",
    ["event_type"],
)
TOPOLOGY_VERSION_COMMITS = Counter(
    "topology_version_commits_total",
    "Total number of topology version commits",
    ["topology_id"],
)
TOPOLOGY_AUDIT_EVENTS = Counter(
    "topology_audit_events_total",
    "Total number of topology audit events",
    ["event_type"],
)
TOPOLOGY_SAGA_STATUS = Gauge(
    "topology_saga_status",
    "Current saga transaction status (0=pending,1=success,2=failed,3=compensating)",
    ["saga_id"],
)
TOPOLOGY_ACTIVE_DISCOVERIES = Gauge(
    "topology_active_discoveries",
    "Number of active topology discoveries",
)
