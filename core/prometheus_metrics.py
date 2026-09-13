# -*- coding: utf-8 -*-
"""
Prometheus Metrics Exporter (unified)
=====================================

Single source of truth for every ``aiops_*`` application metric.

Historically the repository shipped **two** exporters:

* ``core/prometheus_metrics.py`` (``PrometheusMetricsExporter``) registered its
  metrics on the process **default** registry, and was the one the running
  application actually wrote to (HTTP middleware, websocket manager, message
  queue, rate limiter) — but it had **no HTTP outlet**.
* ``core/metrics_exporter.py`` (``MetricsExporter``) used a **separate custom**
  ``CollectorRegistry`` that was exposed at ``/api/v1/metrics/prometheus`` but
  was written to by **nobody**.

The result was the worst of both worlds: the registry with data had no endpoint
and the endpoint had no data, so every dashboard panel and alert rule stayed
permanently empty.

This module now owns **all** metric families on the default registry, which is
what the application exposes at ``/metrics`` (and via the compatibility endpoint
``/api/v1/metrics/prometheus``). ``core/metrics_exporter.py`` is kept only as a
thin re-export shim for backwards compatibility.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    REGISTRY,
    Counter,
    Gauge,
    Histogram,
    Info,
    generate_latest,
    start_http_server,
)
from starlette.responses import Response

logger = logging.getLogger(__name__)

#: Guards against a second instantiation re-registering the same time series on
#: the default registry (prometheus_client raises ``ValueError`` in that case).
_INITIALIZED = False
_SINGLETON: "PrometheusMetricsExporter | None" = None


class PrometheusMetricsExporter:
    """Prometheus metrics exporter bound to the process default registry."""

    def __new__(cls, *args: Any, **kwargs: Any) -> "PrometheusMetricsExporter":
        global _SINGLETON
        if _SINGLETON is not None:
            return _SINGLETON
        return super().__new__(cls)

    def __init__(self) -> None:
        global _INITIALIZED, _SINGLETON
        if _INITIALIZED:
            return

        # ------------------------------------------------------------------
        # API metrics
        # ------------------------------------------------------------------
        self.api_requests_total = Counter(
            "aiops_api_requests_total",
            "Total API requests",
            ["endpoint", "method", "status"],
        )
        self.api_request_duration_seconds = Histogram(
            "aiops_api_request_duration_seconds",
            "API request duration in seconds",
            ["endpoint", "method"],
            buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
        )
        self.api_errors_total = Counter(
            "aiops_api_errors_total",
            "Total API errors",
            ["endpoint", "method", "error_type"],
        )
        self.api_connections_active = Gauge(
            "aiops_api_connections_active", "Number of active API connections"
        )
        self.api_connections_idle = Gauge(
            "aiops_api_connections_idle", "Number of idle API connections"
        )

        # ------------------------------------------------------------------
        # Database metrics
        # ------------------------------------------------------------------
        self.db_query_time_seconds = Histogram(
            "aiops_db_query_time_seconds",
            "Database query time in seconds",
            ["table", "operation"],
        )
        self.db_pool_connections = Gauge(
            "aiops_db_pool_connections",
            "Database connection pool size",
            ["state"],  # active, idle, max
        )
        self.db_query_errors_total = Counter(
            "aiops_db_query_errors_total",
            "Total database query errors",
            ["table", "operation", "error_type"],
        )
        self.postgres_replication_lag_seconds = Gauge(
            "aiops_postgres_replication_lag_seconds",
            "PostgreSQL replication lag in seconds",
        )

        # ------------------------------------------------------------------
        # AI / LLM metrics
        # ------------------------------------------------------------------
        self.ai_requests_total = Counter(
            "aiops_ai_requests_total",
            "Total number of AI requests",
            ["model", "operation"],
        )
        self.ai_request_duration_seconds = Histogram(
            "aiops_ai_request_duration_seconds",
            "AI request duration in seconds",
            ["model", "operation"],
            buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
        )
        self.ai_analysis_duration_seconds = Histogram(
            "aiops_ai_analysis_duration_seconds",
            "AI root-cause analysis duration in seconds",
            ["analysis_type"],
            buckets=(0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0),
        )
        self.ai_tokens_total = Counter(
            "aiops_ai_tokens_total",
            "Total number of AI tokens used",
            ["model", "token_type"],
        )
        self.ai_cost_usd_total = Counter(
            "aiops_ai_cost_usd_total",
            "Total AI cost in USD",
            ["model"],
        )
        self.ai_requests_failed_total = Counter(
            "aiops_ai_requests_failed_total",
            "Total number of failed AI requests",
            ["model", "error_type"],
        )
        self.ai_cache_hits_total = Counter(
            "aiops_ai_cache_hits_total", "Total number of AI cache hits"
        )
        self.ai_cache_misses_total = Counter(
            "aiops_ai_cache_misses_total", "Total number of AI cache misses"
        )

        # ------------------------------------------------------------------
        # Knowledge graph metrics
        # ------------------------------------------------------------------
        self.kg_queries_total = Counter(
            "aiops_knowledge_graph_queries_total",
            "Total number of knowledge graph queries",
            ["query_type"],
        )
        self.kg_query_duration_seconds = Histogram(
            "aiops_knowledge_graph_query_duration_seconds",
            "Knowledge graph query duration in seconds",
            ["query_type"],
            buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
        )
        self.kg_nodes_total = Gauge(
            "aiops_knowledge_graph_nodes_total", "Total number of knowledge graph nodes"
        )
        self.kg_edges_total = Gauge(
            "aiops_knowledge_graph_edges_total", "Total number of knowledge graph edges"
        )
        self.kg_cache_hits_total = Counter(
            "aiops_knowledge_graph_cache_hits_total", "Knowledge graph cache hits"
        )
        self.kg_cache_misses_total = Counter(
            "aiops_knowledge_graph_cache_misses_total", "Knowledge graph cache misses"
        )

        # ------------------------------------------------------------------
        # Workflow metrics
        # ------------------------------------------------------------------
        self.workflow_executions_total = Counter(
            "aiops_workflow_executions_total",
            "Total number of workflow executions",
            ["workflow_type", "status"],
        )
        self.workflow_execution_duration_seconds = Histogram(
            "aiops_workflow_execution_duration_seconds",
            "Workflow execution duration in seconds",
            ["workflow_type"],
            buckets=(1.0, 5.0, 10.0, 30.0, 60.0, 300.0, 600.0),
        )
        self.workflow_queue_size = Gauge(
            "aiops_workflow_queue_size", "Current workflow queue size"
        )
        self.workflow_executions_failed_total = Counter(
            "aiops_workflow_executions_failed_total",
            "Total number of failed workflow executions",
            ["workflow_type", "error_type"],
        )

        # ------------------------------------------------------------------
        # RAG / vector / agent metrics
        # ------------------------------------------------------------------
        self.rag_retrieval_time = Histogram(
            "aiops_rag_retrieval_time_seconds",
            "RAG retrieval time in seconds",
            ["collection"],
        )
        self.rag_generation_time = Histogram(
            "aiops_rag_generation_time_seconds", "RAG generation time in seconds", ["model"]
        )
        self.rag_e2e_latency = Histogram(
            "aiops_rag_e2e_latency_seconds",
            "RAG end-to-end latency in seconds",
            ["collection", "model"],
        )
        self.vector_search_time = Histogram(
            "aiops_vector_search_time_seconds",
            "Vector search time in seconds",
            ["collection", "vector_dim"],
        )
        self.agent_execution_time = Histogram(
            "aiops_agent_execution_time_seconds",
            "Agent execution time in seconds",
            ["agent_type", "execution_mode"],
        )

        # ------------------------------------------------------------------
        # Performance regression metrics
        # ------------------------------------------------------------------
        self.performance_regressions = Gauge(
            "aiops_performance_regressions_total",
            "Total performance regressions",
            ["severity", "status"],
        )

        # ------------------------------------------------------------------
        # System resource metrics
        # ------------------------------------------------------------------
        self.system_cpu_usage = Gauge(
            "aiops_system_cpu_usage_percent", "System CPU usage percentage", ["host"]
        )
        self.system_memory_usage = Gauge(
            "aiops_system_memory_usage_percent", "System memory usage percentage", ["host"]
        )
        self.system_disk_usage = Gauge(
            "aiops_system_disk_usage_percent", "System disk usage percentage", ["host"]
        )
        self.system_network_rx = Gauge(
            "aiops_system_network_rx_bytes", "System network received bytes", ["host"]
        )
        self.system_network_tx = Gauge(
            "aiops_system_network_tx_bytes", "System network transmitted bytes", ["host"]
        )
        self.system_resource_usage = Gauge(
            "aiops_system_resource_usage",
            "Aggregate system resource utilisation (max of cpu/memory/disk, 0-1)",
        )
        self.memory_usage_bytes = Gauge(
            "aiops_memory_usage_bytes", "Memory usage in bytes", ["instance"]
        )
        self.disk_io_bytes = Gauge(
            "aiops_disk_io_bytes", "Disk I/O in bytes", ["instance", "operation"]
        )
        self.network_io_bytes = Gauge(
            "aiops_network_io_bytes", "Network I/O in bytes", ["instance", "direction"]
        )

        # ------------------------------------------------------------------
        # Queue / session / websocket metrics
        # ------------------------------------------------------------------
        self.queue_depth = Gauge(
            "aiops_queue_depth", "Current number of messages in a queue", ["queue_name"]
        )
        self.active_sessions = Gauge(
            "aiops_active_sessions_total",
            "Total number of active user sessions",
            ["session_type"],
        )
        self.websocket_connections = Gauge(
            "aiops_websocket_connections_total",
            "Total number of active WebSocket connections",
            ["channel"],
        )

        # ------------------------------------------------------------------
        # Cache metrics
        # ------------------------------------------------------------------
        self.cache_hits_total = Counter(
            "aiops_cache_hits_total", "Total number of cache hits", ["cache_name"]
        )
        self.cache_misses_total = Counter(
            "aiops_cache_misses_total", "Total number of cache misses", ["cache_name"]
        )
        self.cache_size = Gauge(
            "aiops_cache_size", "Current cache size", ["cache_name"]
        )
        self.cache_hit_rate = Gauge(
            "aiops_cache_hit_rate", "Cache hit rate", ["cache_name"]
        )

        # ------------------------------------------------------------------
        # SLO / KPI metrics
        # ------------------------------------------------------------------
        self.slo_availability = Gauge(
            "aiops_slo_availability", "SLO availability percentage", ["slo_name"]
        )
        self.slo_latency = Gauge(
            "aiops_slo_latency", "SLO latency in seconds", ["slo_name", "percentile"]
        )
        self.error_budget_remaining = Gauge(
            "aiops_error_budget_remaining", "Error budget remaining percentage", ["slo_name"]
        )
        self.kpi_throughput = Gauge(
            "aiops_kpi_throughput", "KPI throughput (requests per second)", ["kpi_name"]
        )
        self.kpi_success_rate = Gauge(
            "aiops_kpi_success_rate", "KPI success rate", ["kpi_name"]
        )

        # ------------------------------------------------------------------
        # Domain / observability metrics (sampled from real stores)
        # ------------------------------------------------------------------
        self.alerts_pending = Gauge(
            "aiops_alerts_pending", "Number of unacknowledged/unresolved alerts"
        )
        self.alerts_total = Gauge("aiops_alerts_total", "Number of alerts on record")
        self.alert_backlog_count = Gauge(
            "aiops_alert_backlog_count", "Alerts waiting to be processed"
        )
        self.repairs_total = Counter(
            "aiops_repairs_total", "Total number of repair executions"
        )
        self.repairs_successful_total = Counter(
            "aiops_repairs_successful_total", "Total successful repairs"
        )
        self.repairs_failed_total = Counter(
            "aiops_repairs_failed_total", "Total failed repairs"
        )
        self.repair_active_count = Gauge(
            "aiops_repair_active_count", "Repairs currently in progress"
        )
        self.backup_last_status = Gauge(
            "aiops_backup_last_status", "Status of the most recent backup (1=success, 0=failure)"
        )
        self.backup_last_timestamp = Gauge(
            "aiops_backup_last_timestamp", "Unix timestamp of the most recent backup"
        )
        self.backup_storage_total = Gauge(
            "aiops_backup_storage_total", "Total bytes used by stored backups"
        )
        self.backup_storage_available = Gauge(
            "aiops_backup_storage_available", "Free bytes on the backup volume"
        )
        self.anomalies_detected_total = Counter(
            "aiops_anomalies_detected_total", "Total anomalies detected"
        )
        self.recent_anomalies = Gauge(
            "aiops_recent_anomalies", "Anomalies detected in the last 24h"
        )
        self.audit_logs_total = Counter(
            "aiops_audit_logs_total", "Total audit log entries"
        )
        self.health_status = Gauge(
            "aiops_health_status", "Overall platform health (1=healthy, 0=unhealthy)"
        )
        self.mttr_minutes = Gauge(
            "aiops_mttr_minutes", "Mean time to repair across recorded repairs"
        )
        self.apm_error_rate = Gauge(
            "aiops_apm_error_rate", "Share of API requests returning 4xx/5xx"
        )
        self.apm_slow_request_rate = Gauge(
            "aiops_apm_slow_request_rate", "Share of API requests slower than the SLA"
        )
        self.model_accuracy = Gauge(
            "aiops_model_accuracy", "Mean accuracy of deployed models"
        )
        self.root_cause_success_rate = Gauge(
            "aiops_root_cause_success_rate", "Share of RCA runs that produced a conclusion"
        )
        self.auth_failures_total = Counter(
            "aiops_auth_failures_total", "Total authentication failures"
        )
        self.rate_limit_exceeded_total = Counter(
            "aiops_rate_limit_exceeded_total", "Total rate limit rejections"
        )

        # ------------------------------------------------------------------
        # Application info
        # ------------------------------------------------------------------
        self.app_info = Info("aiops_app_info", "AIOps Agent application information")

        _INITIALIZED = True
        _SINGLETON = self
        logger.info("Unified Prometheus metrics exporter initialised (default registry)")

    # ======================================================================
    # API
    # ======================================================================
    def record_api_request(
        self, endpoint: str, method: str, duration: float, status: int
    ) -> None:
        """Record an API request (count, latency histogram and error counter)."""
        self.api_request_duration_seconds.labels(endpoint=endpoint, method=method).observe(
            duration
        )
        self.api_requests_total.labels(
            endpoint=endpoint, method=method, status=status
        ).inc()
        if status >= 400:
            self.api_errors_total.labels(
                endpoint=endpoint, method=method, error_type=str(status)
            ).inc()

    def update_api_connections(self, active: int, idle: int) -> None:
        """Update the API connection pool gauge."""
        self.api_connections_active.set(active)
        self.api_connections_idle.set(idle)

    # ======================================================================
    # Database
    # ======================================================================
    def record_db_query(
        self, table: str, operation: str, duration: float, success: bool = True
    ) -> None:
        """Record a database query."""
        self.db_query_time_seconds.labels(table=table, operation=operation).observe(duration)
        if not success:
            self.db_query_errors_total.labels(
                table=table, operation=operation, error_type="query_failed"
            ).inc()

    def record_db_pool_stats(self, active: int, idle: int, max_conn: int = 0) -> None:
        """Record database connection pool statistics."""
        self.db_pool_connections.labels(state="active").set(active)
        self.db_pool_connections.labels(state="idle").set(idle)
        if max_conn:
            self.db_pool_connections.labels(state="max").set(max_conn)

    def update_replication_lag(self, lag_seconds: float) -> None:
        """Record PostgreSQL replication lag."""
        self.postgres_replication_lag_seconds.set(lag_seconds)

    # ======================================================================
    # AI / LLM
    # ======================================================================
    def record_ai_request(
        self, model: str, operation: str, duration: float, tokens: int = 0, cost: float = 0.0
    ) -> None:
        """Record an AI request (count, latency, tokens and cost)."""
        self.ai_requests_total.labels(model=model, operation=operation).inc()
        self.ai_request_duration_seconds.labels(model=model, operation=operation).observe(
            duration
        )
        if tokens:
            self.ai_tokens_total.labels(model=model, token_type="input").inc(tokens)
        if cost:
            self.ai_cost_usd_total.labels(model=model).inc(cost)

    def record_llm_inference(
        self,
        model: str,
        provider: str,
        duration: float,
        prompt_tokens: int,
        completion_tokens: int,
        cost: float,
    ) -> None:
        """Record an LLM inference (kept for backwards compatibility)."""
        self.ai_requests_total.labels(model=model, operation=provider).inc()
        self.ai_request_duration_seconds.labels(model=model, operation=provider).observe(
            duration
        )
        if prompt_tokens:
            self.ai_tokens_total.labels(model=model, token_type="prompt").inc(prompt_tokens)
        if completion_tokens:
            self.ai_tokens_total.labels(model=model, token_type="completion").inc(
                completion_tokens
            )
        if cost:
            self.ai_cost_usd_total.labels(model=model).inc(cost)

    def record_ai_failure(self, model: str, error_type: str) -> None:
        """Record a failed AI request."""
        self.ai_requests_failed_total.labels(model=model, error_type=error_type).inc()

    def record_ai_cache_hit(self) -> None:
        self.ai_cache_hits_total.inc()

    def record_ai_cache_miss(self) -> None:
        self.ai_cache_misses_total.inc()

    def record_ai_analysis(self, analysis_type: str, duration: float) -> None:
        """Record the duration of an AI root-cause analysis run."""
        self.ai_analysis_duration_seconds.labels(analysis_type=analysis_type).observe(duration)

    # ======================================================================
    # Knowledge graph
    # ======================================================================
    def record_kg_query(self, query_type: str, duration: float) -> None:
        """Record a knowledge graph query."""
        self.kg_queries_total.labels(query_type=query_type).inc()
        self.kg_query_duration_seconds.labels(query_type=query_type).observe(duration)

    def update_kg_size(self, nodes: int, edges: int) -> None:
        self.kg_nodes_total.set(nodes)
        self.kg_edges_total.set(edges)

    def record_kg_cache_hit(self) -> None:
        self.kg_cache_hits_total.inc()

    def record_kg_cache_miss(self) -> None:
        self.kg_cache_misses_total.inc()

    # ======================================================================
    # Workflow
    # ======================================================================
    def record_workflow_execution(self, workflow_type: str, status: str, duration: float) -> None:
        self.workflow_executions_total.labels(
            workflow_type=workflow_type, status=status
        ).inc()
        self.workflow_execution_duration_seconds.labels(workflow_type=workflow_type).observe(
            duration
        )

    def update_workflow_queue_size(self, size: int) -> None:
        self.workflow_queue_size.set(size)

    def record_workflow_failure(self, workflow_type: str, error_type: str) -> None:
        self.workflow_executions_failed_total.labels(
            workflow_type=workflow_type, error_type=error_type
        ).inc()

    # ======================================================================
    # RAG / vector / agent
    # ======================================================================
    def record_rag_retrieval(self, collection: str, duration: float) -> None:
        self.rag_retrieval_time.labels(collection=collection).observe(duration)

    def record_rag_generation(self, model: str, duration: float) -> None:
        self.rag_generation_time.labels(model=model).observe(duration)

    def record_rag_e2e(self, collection: str, model: str, duration: float) -> None:
        self.rag_e2e_latency.labels(collection=collection, model=model).observe(duration)

    def record_vector_search(self, collection: str, vector_dim: int, duration: float) -> None:
        self.vector_search_time.labels(
            collection=collection, vector_dim=str(vector_dim)
        ).observe(duration)

    def record_agent_execution(
        self, agent_type: str, execution_mode: str, duration: float
    ) -> None:
        self.agent_execution_time.labels(
            agent_type=agent_type, execution_mode=execution_mode
        ).observe(duration)

    # ======================================================================
    # Performance regressions
    # ======================================================================
    def update_performance_regressions(self, severity: str, status: str, count: int) -> None:
        self.performance_regressions.labels(severity=severity, status=status).set(count)

    # ======================================================================
    # System resources
    # ======================================================================
    def record_system_resources(self, host: str, cpu_usage: float, memory_usage: float) -> None:
        self.system_cpu_usage.labels(host=host).set(cpu_usage)
        self.system_memory_usage.labels(host=host).set(memory_usage)

    def update_cpu_usage(self, instance: str, usage_percent: float) -> None:
        self.system_cpu_usage.labels(host=instance).set(usage_percent)

    def update_memory_usage(self, instance: str, usage_bytes: int) -> None:
        self.memory_usage_bytes.labels(instance=instance).set(usage_bytes)

    def update_disk_io(self, instance: str, operation: str, io_bytes: int) -> None:
        self.disk_io_bytes.labels(instance=instance, operation=operation).set(io_bytes)

    def update_network_io(self, instance: str, direction: str, io_bytes: int) -> None:
        self.network_io_bytes.labels(instance=instance, direction=direction).set(io_bytes)

    # ======================================================================
    # Queue / sessions / websockets
    # ======================================================================
    def record_queue_depth(self, queue_name: str, depth: int) -> None:
        self.queue_depth.labels(queue_name=queue_name).set(depth)

    def record_active_sessions(self, session_type: str, count: int) -> None:
        self.active_sessions.labels(session_type=session_type).set(count)

    def record_websocket_connections(self, channel: str, count: int) -> None:
        self.websocket_connections.labels(channel=channel).set(count)

    # ======================================================================
    # Cache
    # ======================================================================
    def record_cache_hit(self, cache_name: str = "default") -> None:
        self.cache_hits_total.labels(cache_name=cache_name).inc()

    def record_cache_miss(self, cache_name: str = "default") -> None:
        self.cache_misses_total.labels(cache_name=cache_name).inc()

    def update_cache_size(self, cache_name: str, size: int) -> None:
        self.cache_size.labels(cache_name=cache_name).set(size)

    def update_cache_hit_rate(self, cache_name: str, hit_rate: float) -> None:
        self.cache_hit_rate.labels(cache_name=cache_name).set(hit_rate)

    # ======================================================================
    # SLO / KPI
    # ======================================================================
    def update_slo_availability(self, slo_name: str, availability: float) -> None:
        self.slo_availability.labels(slo_name=slo_name).set(availability)

    def update_slo_latency(self, slo_name: str, percentile: str, latency: float) -> None:
        self.slo_latency.labels(slo_name=slo_name, percentile=percentile).set(latency)

    def update_error_budget(self, slo_name: str, remaining: float) -> None:
        self.error_budget_remaining.labels(slo_name=slo_name).set(remaining)

    def update_kpi_throughput(self, kpi_name: str, throughput: float) -> None:
        self.kpi_throughput.labels(kpi_name=kpi_name).set(throughput)

    def update_kpi_success_rate(self, kpi_name: str, success_rate: float) -> None:
        self.kpi_success_rate.labels(kpi_name=kpi_name).set(success_rate)

    # ======================================================================
    # Application info / export
    # ======================================================================
    def set_app_info(self, info: Dict[str, Any]) -> None:
        self.app_info.info(info)

    def export_metrics(self) -> bytes:
        """Return the default-registry metrics in Prometheus text format."""
        return generate_latest(REGISTRY)

    def get_metrics_response(self) -> Response:
        """Return the default-registry metrics as a FastAPI/Starlette response."""
        return Response(content=self.export_metrics(), media_type=CONTENT_TYPE_LATEST)

    def start_metrics_server(self, port: int = 9090) -> None:
        """Expose the default registry on a standalone HTTP port.

        The application normally serves metrics from its ASGI ``/metrics`` route;
        this helper is for deployments that prefer a dedicated metrics port.
        """
        try:
            start_http_server(port)
            logger.info("Prometheus metrics server started on port %s", port)
        except Exception as e:  # pragma: no cover - port conflicts are environment specific
            logger.error("Failed to start Prometheus metrics server: %s", e)


#: Module-level singleton.
metrics_exporter = PrometheusMetricsExporter()


def get_metrics_exporter() -> PrometheusMetricsExporter:
    """Return the process-wide metrics exporter singleton."""
    return metrics_exporter


def record_auth_failure() -> None:
    """Increment the authentication-failure counter (best effort)."""
    try:
        get_metrics_exporter().auth_failures_total.inc()
    except Exception:  # pragma: no cover - metrics must never break auth
        pass


def record_rate_limit_exceeded() -> None:
    """Increment the rate-limit-rejection counter (best effort)."""
    try:
        get_metrics_exporter().rate_limit_exceeded_total.inc()
    except Exception:  # pragma: no cover - metrics must never break limiting
        pass
