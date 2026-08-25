# -*- coding: utf-8 -*-
"""
Prometheus Metrics Exporter for AIOps Agent
============================================

This module provides Prometheus metrics export functionality for the AIOps Agent,
integrating with the existing performance framework and exposing metrics in Prometheus format.
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

from core.performance_data_collector import PerformanceDataCollector
from core.performance_optimizer import PerformanceOptimizer

logger = logging.getLogger(__name__)


class MetricsExporter:
    """
    Prometheus Metrics Exporter for AIOps Agent

    Exports metrics in Prometheus format, integrating with the existing
    performance framework and providing comprehensive monitoring capabilities.
    """

    def __init__(
        self,
        performance_collector: Optional[PerformanceDataCollector] = None,
        performance_optimizer: Optional[PerformanceOptimizer] = None,
    ):
        """
        Initialize the metrics exporter

        Args:
            performance_collector: Performance data collector instance
            performance_optimizer: Performance optimizer instance
        """
        self.performance_collector = performance_collector or PerformanceDataCollector()
        self.performance_optimizer = performance_optimizer or PerformanceOptimizer()

        # Create a custom registry for AIOps metrics
        self.registry = CollectorRegistry()

        # Initialize API metrics
        self._init_api_metrics()

        # Initialize AI/LLM metrics
        self._init_ai_metrics()

        # Initialize Knowledge Graph metrics
        self._init_knowledge_graph_metrics()

        # Initialize Workflow metrics
        self._init_workflow_metrics()

        # Initialize Resource metrics
        self._init_resource_metrics()

        # Initialize KPI/SLO metrics
        self._init_kpi_slo_metrics()

        # Initialize Cache metrics
        self._init_cache_metrics()

        # Initialize Database metrics
        self._init_database_metrics()

        logger.info("Metrics Exporter initialized")

    def _init_api_metrics(self):
        """Initialize API-related metrics"""
        # API request counter
        self.api_requests_total = Counter(
            "aiops_api_requests_total",
            "Total number of API requests",
            ["method", "endpoint", "status"],
            registry=self.registry,
        )

        # API request duration histogram
        self.api_request_duration_seconds = Histogram(
            "aiops_api_request_duration_seconds",
            "API request duration in seconds",
            ["method", "endpoint"],
            buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
            registry=self.registry,
        )

        # API connection pool gauge
        self.api_connections_active = Gauge(
            "aiops_api_connections_active",
            "Number of active API connections",
            registry=self.registry,
        )

        self.api_connections_idle = Gauge(
            "aiops_api_connections_idle", "Number of idle API connections", registry=self.registry
        )

        # API error counter
        self.api_errors_total = Counter(
            "aiops_api_errors_total",
            "Total number of API errors",
            ["error_type"],
            registry=self.registry,
        )

    def _init_ai_metrics(self):
        """Initialize AI/LLM-related metrics"""
        # AI request counter
        self.ai_requests_total = Counter(
            "aiops_ai_requests_total",
            "Total number of AI requests",
            ["model", "operation"],
            registry=self.registry,
        )

        # AI request duration histogram
        self.ai_request_duration_seconds = Histogram(
            "aiops_ai_request_duration_seconds",
            "AI request duration in seconds",
            ["model", "operation"],
            buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
            registry=self.registry,
        )

        # AI token counter
        self.ai_tokens_total = Counter(
            "aiops_ai_tokens_total",
            "Total number of AI tokens used",
            ["model", "token_type"],
            registry=self.registry,
        )

        # AI cost gauge
        self.ai_cost_usd = Gauge(
            "aiops_ai_cost_usd", "Total AI cost in USD", ["model"], registry=self.registry
        )

        # AI failure counter
        self.ai_requests_failed_total = Counter(
            "aiops_ai_requests_failed_total",
            "Total number of failed AI requests",
            ["model", "error_type"],
            registry=self.registry,
        )

        # AI cache metrics
        self.ai_cache_hits_total = Counter(
            "aiops_ai_cache_hits_total", "Total number of AI cache hits", registry=self.registry
        )

        self.ai_cache_misses_total = Counter(
            "aiops_ai_cache_misses_total", "Total number of AI cache misses", registry=self.registry
        )

    def _init_knowledge_graph_metrics(self):
        """Initialize Knowledge Graph-related metrics"""
        # Knowledge graph query counter
        self.kg_queries_total = Counter(
            "aiops_knowledge_graph_queries_total",
            "Total number of knowledge graph queries",
            ["query_type"],
            registry=self.registry,
        )

        # Knowledge graph query duration histogram
        self.kg_query_duration_seconds = Histogram(
            "aiops_knowledge_graph_query_duration_seconds",
            "Knowledge graph query duration in seconds",
            ["query_type"],
            buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
            registry=self.registry,
        )

        # Knowledge graph size gauges
        self.kg_nodes_total = Gauge(
            "aiops_knowledge_graph_nodes_total",
            "Total number of nodes in knowledge graph",
            registry=self.registry,
        )

        self.kg_edges_total = Gauge(
            "aiops_knowledge_graph_edges_total",
            "Total number of edges in knowledge graph",
            registry=self.registry,
        )

        # Knowledge graph cache metrics
        self.kg_cache_hits_total = Counter(
            "aiops_knowledge_graph_cache_hits_total",
            "Total number of knowledge graph cache hits",
            registry=self.registry,
        )

        self.kg_cache_misses_total = Counter(
            "aiops_knowledge_graph_cache_misses_total",
            "Total number of knowledge graph cache misses",
            registry=self.registry,
        )

    def _init_workflow_metrics(self):
        """Initialize Workflow-related metrics"""
        # Workflow execution counter
        self.workflow_executions_total = Counter(
            "aiops_workflow_executions_total",
            "Total number of workflow executions",
            ["workflow_type", "status"],
            registry=self.registry,
        )

        # Workflow execution duration histogram
        self.workflow_execution_duration_seconds = Histogram(
            "aiops_workflow_execution_duration_seconds",
            "Workflow execution duration in seconds",
            ["workflow_type"],
            buckets=(1.0, 5.0, 10.0, 30.0, 60.0, 300.0, 600.0),
            registry=self.registry,
        )

        # Workflow queue size gauge
        self.workflow_queue_size = Gauge(
            "aiops_workflow_queue_size", "Current workflow queue size", registry=self.registry
        )

        # Workflow failure counter
        self.workflow_executions_failed_total = Counter(
            "aiops_workflow_executions_failed_total",
            "Total number of failed workflow executions",
            ["workflow_type", "error_type"],
            registry=self.registry,
        )

    def _init_resource_metrics(self):
        """Initialize Resource-related metrics"""
        # CPU usage gauge
        self.cpu_usage_percent = Gauge(
            "aiops_cpu_usage_percent", "CPU usage percentage", ["instance"], registry=self.registry
        )

        # Memory usage gauge
        self.memory_usage_bytes = Gauge(
            "aiops_memory_usage_bytes",
            "Memory usage in bytes",
            ["instance"],
            registry=self.registry,
        )

        # Disk I/O gauge
        self.disk_io_bytes = Gauge(
            "aiops_disk_io_bytes",
            "Disk I/O in bytes",
            ["instance", "operation"],
            registry=self.registry,
        )

        # Network I/O gauge
        self.network_io_bytes = Gauge(
            "aiops_network_io_bytes",
            "Network I/O in bytes",
            ["instance", "direction"],
            registry=self.registry,
        )

    def _init_kpi_slo_metrics(self):
        """Initialize KPI/SLO-related metrics"""
        # SLO availability gauge
        self.slo_availability = Gauge(
            "aiops_slo_availability",
            "SLO availability percentage",
            ["slo_name"],
            registry=self.registry,
        )

        # SLO latency gauge
        self.slo_latency = Gauge(
            "aiops_slo_latency",
            "SLO latency in seconds",
            ["slo_name", "percentile"],
            registry=self.registry,
        )

        # Error budget gauge
        self.error_budget_remaining = Gauge(
            "aiops_error_budget_remaining",
            "Error budget remaining percentage",
            ["slo_name"],
            registry=self.registry,
        )

        # KPI gauges
        self.kpi_throughput = Gauge(
            "aiops_kpi_throughput",
            "KPI throughput (requests per second)",
            ["kpi_name"],
            registry=self.registry,
        )

        self.kpi_success_rate = Gauge(
            "aiops_kpi_success_rate", "KPI success rate", ["kpi_name"], registry=self.registry
        )

    def _init_cache_metrics(self):
        """Initialize Cache-related metrics"""
        # Cache hit/miss counters
        self.cache_hits_total = Counter(
            "aiops_cache_hits_total",
            "Total number of cache hits",
            ["cache_name"],
            registry=self.registry,
        )

        self.cache_misses_total = Counter(
            "aiops_cache_misses_total",
            "Total number of cache misses",
            ["cache_name"],
            registry=self.registry,
        )

        # Cache size gauge
        self.cache_size = Gauge(
            "aiops_cache_size", "Current cache size", ["cache_name"], registry=self.registry
        )

        # Cache hit rate gauge
        self.cache_hit_rate = Gauge(
            "aiops_cache_hit_rate", "Cache hit rate", ["cache_name"], registry=self.registry
        )

    def _init_database_metrics(self):
        """Initialize Database-related metrics"""
        # Database connection pool gauge
        self.postgres_connections_active = Gauge(
            "aiops_postgres_connections_active",
            "Number of active PostgreSQL connections",
            registry=self.registry,
        )

        self.postgres_connections_idle = Gauge(
            "aiops_postgres_connections_idle",
            "Number of idle PostgreSQL connections",
            registry=self.registry,
        )

        self.postgres_connections_max = Gauge(
            "aiops_postgres_connections_max",
            "Maximum number of PostgreSQL connections",
            registry=self.registry,
        )

        # Database query duration histogram
        self.postgres_query_duration_seconds = Histogram(
            "aiops_postgres_query_duration_seconds",
            "PostgreSQL query duration in seconds",
            ["query_type"],
            buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0),
            registry=self.registry,
        )

        # Database replication lag gauge
        self.postgres_replication_lag_seconds = Gauge(
            "aiops_postgres_replication_lag_seconds",
            "PostgreSQL replication lag in seconds",
            registry=self.registry,
        )

    # API Metrics Methods
    def record_api_request(self, method: str, endpoint: str, status: int, duration: float):
        """
        Record an API request

        Args:
            method: HTTP method
            endpoint: API endpoint
            status: HTTP status code
            duration: Request duration in seconds
        """
        self.api_requests_total.labels(method=method, endpoint=endpoint, status=status).inc()
        self.api_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)

        if status >= 400:
            self.api_errors_total.labels(error_type=f"http_{status}").inc()

    def update_api_connections(self, active: int, idle: int):
        """
        Update API connection pool metrics

        Args:
            active: Number of active connections
            idle: Number of idle connections
        """
        self.api_connections_active.set(active)
        self.api_connections_idle.set(idle)

    # AI Metrics Methods
    def record_ai_request(
        self, model: str, operation: str, duration: float, tokens: int = 0, cost: float = 0.0
    ):
        """
        Record an AI request

        Args:
            model: AI model name
            operation: Operation type
            duration: Request duration in seconds
            tokens: Number of tokens used
            cost: Cost in USD
        """
        self.ai_requests_total.labels(model=model, operation=operation).inc()
        self.ai_request_duration_seconds.labels(model=model, operation=operation).observe(duration)

        if tokens > 0:
            self.ai_tokens_total.labels(model=model, token_type="input").inc(tokens)

        if cost > 0:
            self.ai_cost_usd.labels(model=model).inc(cost)

    def record_ai_failure(self, model: str, error_type: str):
        """
        Record an AI request failure

        Args:
            model: AI model name
            error_type: Type of error
        """
        self.ai_requests_failed_total.labels(model=model, error_type=error_type).inc()

    def record_ai_cache_hit(self):
        """Record an AI cache hit"""
        self.ai_cache_hits_total.inc()

    def record_ai_cache_miss(self):
        """Record an AI cache miss"""
        self.ai_cache_misses_total.inc()

    # Knowledge Graph Metrics Methods
    def record_kg_query(self, query_type: str, duration: float):
        """
        Record a knowledge graph query

        Args:
            query_type: Type of query
            duration: Query duration in seconds
        """
        self.kg_queries_total.labels(query_type=query_type).inc()
        self.kg_query_duration_seconds.labels(query_type=query_type).observe(duration)

    def update_kg_size(self, nodes: int, edges: int):
        """
        Update knowledge graph size metrics

        Args:
            nodes: Number of nodes
            edges: Number of edges
        """
        self.kg_nodes_total.set(nodes)
        self.kg_edges_total.set(edges)

    def record_kg_cache_hit(self):
        """Record a knowledge graph cache hit"""
        self.kg_cache_hits_total.inc()

    def record_kg_cache_miss(self):
        """Record a knowledge graph cache miss"""
        self.kg_cache_misses_total.inc()

    # Workflow Metrics Methods
    def record_workflow_execution(self, workflow_type: str, status: str, duration: float):
        """
        Record a workflow execution

        Args:
            workflow_type: Type of workflow
            status: Execution status
            duration: Execution duration in seconds
        """
        self.workflow_executions_total.labels(workflow_type=workflow_type, status=status).inc()
        self.workflow_execution_duration_seconds.labels(workflow_type=workflow_type).observe(
            duration
        )

    def update_workflow_queue_size(self, size: int):
        """
        Update workflow queue size

        Args:
            size: Current queue size
        """
        self.workflow_queue_size.set(size)

    def record_workflow_failure(self, workflow_type: str, error_type: str):
        """
        Record a workflow execution failure

        Args:
            workflow_type: Type of workflow
            error_type: Type of error
        """
        self.workflow_executions_failed_total.labels(
            workflow_type=workflow_type, error_type=error_type
        ).inc()

    # Resource Metrics Methods
    def update_cpu_usage(self, instance: str, usage_percent: float):
        """
        Update CPU usage metric

        Args:
            instance: Instance name
            usage_percent: CPU usage percentage
        """
        self.cpu_usage_percent.labels(instance=instance).set(usage_percent)

    def update_memory_usage(self, instance: str, usage_bytes: int):
        """
        Update memory usage metric

        Args:
            instance: Instance name
            usage_bytes: Memory usage in bytes
        """
        self.memory_usage_bytes.labels(instance=instance).set(usage_bytes)

    def update_disk_io(self, instance: str, operation: str, io_bytes: int):
        """
        Update disk I/O metric

        Args:
            instance: Instance name
            operation: Operation type (read/write)
            io_bytes: I/O bytes
        """
        self.disk_io_bytes.labels(instance=instance, operation=operation).set(io_bytes)

    def update_network_io(self, instance: str, direction: str, io_bytes: int):
        """
        Update network I/O metric

        Args:
            instance: Instance name
            direction: Direction (rx/tx)
            io_bytes: I/O bytes
        """
        self.network_io_bytes.labels(instance=instance, direction=direction).set(io_bytes)

    # KPI/SLO Metrics Methods
    def update_slo_availability(self, slo_name: str, availability: float):
        """
        Update SLO availability metric

        Args:
            slo_name: SLO name
            availability: Availability percentage (0-1)
        """
        self.slo_availability.labels(slo_name=slo_name).set(availability)

    def update_slo_latency(self, slo_name: str, percentile: str, latency: float):
        """
        Update SLO latency metric

        Args:
            slo_name: SLO name
            percentile: Percentile (p50, p95, p99)
            latency: Latency in seconds
        """
        self.slo_latency.labels(slo_name=slo_name, percentile=percentile).set(latency)

    def update_error_budget(self, slo_name: str, remaining: float):
        """
        Update error budget remaining metric

        Args:
            slo_name: SLO name
            remaining: Error budget remaining percentage (0-1)
        """
        self.error_budget_remaining.labels(slo_name=slo_name).set(remaining)

    def update_kpi_throughput(self, kpi_name: str, throughput: float):
        """
        Update KPI throughput metric

        Args:
            kpi_name: KPI name
            throughput: Throughput (requests per second)
        """
        self.kpi_throughput.labels(kpi_name=kpi_name).set(throughput)

    def update_kpi_success_rate(self, kpi_name: str, success_rate: float):
        """
        Update KPI success rate metric

        Args:
            kpi_name: KPI name
            success_rate: Success rate (0-1)
        """
        self.kpi_success_rate.labels(kpi_name=kpi_name).set(success_rate)

    # Cache Metrics Methods
    def record_cache_hit(self, cache_name: str):
        """
        Record a cache hit

        Args:
            cache_name: Name of the cache
        """
        self.cache_hits_total.labels(cache_name=cache_name).inc()

    def record_cache_miss(self, cache_name: str):
        """
        Record a cache miss

        Args:
            cache_name: Name of the cache
        """
        self.cache_misses_total.labels(cache_name=cache_name).inc()

    def update_cache_size(self, cache_name: str, size: int):
        """
        Update cache size metric

        Args:
            cache_name: Name of the cache
            size: Current cache size
        """
        self.cache_size.labels(cache_name=cache_name).set(size)

    def update_cache_hit_rate(self, cache_name: str, hit_rate: float):
        """
        Update cache hit rate metric

        Args:
            cache_name: Name of the cache
            hit_rate: Hit rate (0-1)
        """
        self.cache_hit_rate.labels(cache_name=cache_name).set(hit_rate)

    # Database Metrics Methods
    def update_postgres_connections(self, active: int, idle: int, max_conn: int):
        """
        Update PostgreSQL connection metrics

        Args:
            active: Number of active connections
            idle: Number of idle connections
            max_conn: Maximum number of connections
        """
        self.postgres_connections_active.set(active)
        self.postgres_connections_idle.set(idle)
        self.postgres_connections_max.set(max_conn)

    def record_postgres_query(self, query_type: str, duration: float):
        """
        Record a PostgreSQL query

        Args:
            query_type: Type of query
            duration: Query duration in seconds
        """
        self.postgres_query_duration_seconds.labels(query_type=query_type).observe(duration)

    def update_replication_lag(self, lag_seconds: float):
        """
        Update replication lag metric

        Args:
            lag_seconds: Replication lag in seconds
        """
        self.postgres_replication_lag_seconds.set(lag_seconds)

    # Export Methods
    def export_metrics(self) -> str:
        """
        Export metrics in Prometheus format

        Returns:
            Metrics in Prometheus text format
        """
        return generate_latest(self.registry).decode("utf-8")

    def get_metrics_response(self) -> Response:
        """
        Get metrics as FastAPI response

        Returns:
            FastAPI Response with metrics
        """
        return Response(content=self.export_metrics(), media_type=CONTENT_TYPE_LATEST)

    async def collect_from_performance_data(self):
        """
        Collect metrics from performance data collector

        This method integrates with the existing performance framework
        to populate Prometheus metrics from collected performance data.
        """
        try:
            # Query recent performance metrics
            metrics = await self.performance_collector.query_metrics(
                start_time=datetime.now().replace(hour=0, minute=0, second=0, microsecond=0),
                limit=100,
            )

            # Update metrics based on collected data
            for metric in metrics:
                component = metric.get("component", "unknown")

                # Update component-specific metrics
                if component == "api":
                    self.update_api_connections(
                        active=metric.get("connection_count", 0),
                        idle=metric.get("total_requests", 0) - metric.get("connection_count", 0),
                    )
                elif component == "ai":
                    if metric.get("throughput_ops"):
                        self.update_kpi_throughput("ai_requests", metric.get("throughput_ops"))
                    if metric.get("error_rate"):
                        self.update_kpi_success_rate("ai_requests", 1 - metric.get("error_rate"))
                elif component == "knowledge_graph":
                    self.update_kg_size(
                        nodes=metric.get("data_volume", 0), edges=metric.get("data_volume", 0) // 2
                    )
                elif component == "workflow":
                    self.update_workflow_queue_size(metric.get("total_requests", 0))

            logger.info(f"Collected {len(metrics)} performance metrics")

        except Exception as e:
            logger.error(f"Failed to collect performance metrics: {e}", exc_info=True)

    async def collect_from_performance_optimizer(self):
        """
        Collect metrics from performance optimizer

        This method integrates with the performance optimizer to
        populate Prometheus metrics from optimizer data.
        """
        try:
            # Collect resource metrics from optimizer
            if hasattr(self.performance_optimizer, "metrics_history"):
                # CPU usage
                if "cpu_usage" in self.performance_optimizer.metrics_history:
                    recent_cpu = [
                        v for _, v in self.performance_optimizer.metrics_history["cpu_usage"][-5:]
                    ]
                    if recent_cpu:
                        avg_cpu = sum(recent_cpu) / len(recent_cpu)
                        self.update_cpu_usage("main", avg_cpu)

                # Memory usage
                if "memory_usage" in self.performance_optimizer.metrics_history:
                    recent_memory = [
                        v
                        for _, v in self.performance_optimizer.metrics_history["memory_usage"][-5:]
                    ]
                    if recent_memory:
                        avg_memory = sum(recent_memory) / len(recent_memory)
                        self.update_memory_usage(
                            "main", avg_memory * 1024 * 1024
                        )  # Convert to bytes

                # Cache hit rates
                for cache_name, stats in self.performance_optimizer.cache_stats.items():
                    if stats.hits + stats.misses > 0:
                        hit_rate = stats.hits / (stats.hits + stats.misses)
                        self.update_cache_hit_rate(cache_name, hit_rate)
                        self.update_cache_size(cache_name, stats.size)

            logger.info("Collected metrics from performance optimizer")

        except Exception as e:
            logger.error(f"Failed to collect optimizer metrics: {e}", exc_info=True)


# Global metrics exporter instance
_metrics_exporter: Optional[MetricsExporter] = None


def get_metrics_exporter() -> MetricsExporter:
    """
    Get the global metrics exporter instance

    Returns:
        MetricsExporter instance
    """
    global _metrics_exporter
    if _metrics_exporter is None:
        _metrics_exporter = MetricsExporter()
    return _metrics_exporter


def record_api_request(method: str, endpoint: str, status: int, duration: float) -> None:
    """
    Convenience function to record an API request

    Args:
        method: HTTP method
        endpoint: API endpoint
        status: HTTP status code
        duration: Request duration in seconds
    """
    exporter = get_metrics_exporter()
    exporter.record_api_request(method, endpoint, status, duration)


def record_ai_request(
    model: str, operation: str, duration: float, tokens: int = 0, cost: float = 0.0
) -> None:
    """
    Convenience function to record an AI request

    Args:
        model: AI model name
        operation: Operation type
        duration: Request duration in seconds
        tokens: Number of tokens used
        cost: Cost in USD
    """
    exporter = get_metrics_exporter()
    exporter.record_ai_request(model, operation, duration, tokens, cost)
