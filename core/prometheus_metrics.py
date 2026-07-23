# -*- coding: utf-8 -*-
"""
Prometheus Metrics Exporter
Prometheus指标导出器
"""

import logging
from typing import Any, Dict

from prometheus_client import Counter, Gauge, Histogram, Info, start_http_server

logger = logging.getLogger(__name__)


class PrometheusMetricsExporter:
    """Prometheus指标导出器"""

    def __init__(self):
        """初始化Prometheus指标"""

        # API性能指标
        self.api_response_time = Histogram(
            "aiops_api_response_time_seconds",
            "API response time in seconds",
            ["endpoint", "method"],
        )

        self.api_throughput = Counter(
            "aiops_api_requests_total", "Total API requests", ["endpoint", "method", "status"]
        )

        self.api_errors = Counter(
            "aiops_api_errors_total", "Total API errors", ["endpoint", "method", "error_type"]
        )

        # 数据库性能指标
        self.db_query_time = Histogram(
            "aiops_db_query_time_seconds", "Database query time in seconds", ["table", "operation"]
        )

        self.db_pool_connections = Gauge(
            "aiops_db_pool_connections", "Database pool connections", ["state"]  # active, idle
        )

        self.db_query_errors = Counter(
            "aiops_db_query_errors_total",
            "Total database query errors",
            ["table", "operation", "error_type"],
        )

        # AI性能指标
        self.llm_inference_time = Histogram(
            "aiops_llm_inference_time_seconds",
            "LLM inference time in seconds",
            ["model", "provider"],
        )

        self.llm_token_usage = Counter(
            "aiops_llm_token_usage_total",
            "Total LLM token usage",
            ["model", "token_type"],  # prompt, completion
        )

        self.llm_cost = Counter("aiops_llm_cost_usd_total", "Total LLM cost in USD", ["model"])

        # RAG性能指标
        self.rag_retrieval_time = Histogram(
            "aiops_rag_retrieval_time_seconds", "RAG retrieval time in seconds", ["collection"]
        )

        self.rag_generation_time = Histogram(
            "aiops_rag_generation_time_seconds", "RAG generation time in seconds", ["model"]
        )

        self.rag_e2e_latency = Histogram(
            "aiops_rag_e2e_latency_seconds",
            "RAG end-to-end latency in seconds",
            ["collection", "model"],
        )

        # 向量检索性能指标
        self.vector_search_time = Histogram(
            "aiops_vector_search_time_seconds",
            "Vector search time in seconds",
            ["collection", "vector_dim"],
        )

        # 代理编排性能指标
        self.agent_execution_time = Histogram(
            "aiops_agent_execution_time_seconds",
            "Agent execution time in seconds",
            ["agent_type", "execution_mode"],
        )

        # 性能回归指标
        self.performance_regressions = Gauge(
            "aiops_performance_regressions_total",
            "Total performance regressions",
            ["severity", "status"],
        )

        # 系统资源指标
        self.system_cpu_usage = Gauge(
            "aiops_system_cpu_usage_percent", "System CPU usage percentage", ["host"]
        )

        self.system_memory_usage = Gauge(
            "aiops_system_memory_usage_percent", "System memory usage percentage", ["host"]
        )

        # 应用信息
        self.app_info = Info("aiops_app_info", "AIOps Agent application information")

    def record_api_request(
        self,
        endpoint: str,
        method: str,
        duration: float,
        status: int,
    ):
        """记录API请求"""
        self.api_response_time.labels(endpoint=endpoint, method=method).observe(duration)

        self.api_throughput.labels(endpoint=endpoint, method=method, status=status).inc()

        if status >= 400:
            self.api_errors.labels(endpoint=endpoint, method=method, error_type=str(status)).inc()

    def record_db_query(
        self,
        table: str,
        operation: str,
        duration: float,
        success: bool = True,
    ):
        """记录数据库查询"""
        self.db_query_time.labels(table=table, operation=operation).observe(duration)

        if not success:
            self.db_query_errors.labels(
                table=table, operation=operation, error_type="query_failed"
            ).inc()

    def record_db_pool_stats(
        self,
        active: int,
        idle: int,
    ):
        """记录数据库连接池统计"""
        self.db_pool_connections.labels(state="active").set(active)
        self.db_pool_connections.labels(state="idle").set(idle)

    def record_llm_inference(
        self,
        model: str,
        provider: str,
        duration: float,
        prompt_tokens: int,
        completion_tokens: int,
        cost: float,
    ):
        """记录LLM推理"""
        self.llm_inference_time.labels(model=model, provider=provider).observe(duration)

        prompt_label = "prompt"
        self.llm_token_usage.labels(model=model, token_type=prompt_label).inc(prompt_tokens)

        completion_label = "completion"
        self.llm_token_usage.labels(model=model, token_type=completion_label).inc(completion_tokens)

        self.llm_cost.labels(model=model).inc(cost)

    def record_rag_retrieval(
        self,
        collection: str,
        duration: float,
    ):
        """记录RAG检索"""
        self.rag_retrieval_time.labels(collection=collection).observe(duration)

    def record_rag_generation(
        self,
        model: str,
        duration: float,
    ):
        """记录RAG生成"""
        self.rag_generation_time.labels(model=model).observe(duration)

    def record_rag_e2e(
        self,
        collection: str,
        model: str,
        duration: float,
    ):
        """记录RAG端到端延迟"""
        self.rag_e2e_latency.labels(collection=collection, model=model).observe(duration)

    def record_vector_search(
        self,
        collection: str,
        vector_dim: int,
        duration: float,
    ):
        """记录向量检索"""
        self.vector_search_time.labels(collection=collection, vector_dim=str(vector_dim)).observe(
            duration
        )

    def record_agent_execution(
        self,
        agent_type: str,
        execution_mode: str,
        duration: float,
    ):
        """记录代理执行"""
        self.agent_execution_time.labels(
            agent_type=agent_type, execution_mode=execution_mode
        ).observe(duration)

    def update_performance_regressions(
        self,
        severity: str,
        status: str,
        count: int,
    ):
        """更新性能回归统计"""
        self.performance_regressions.labels(severity=severity, status=status).set(count)

    def record_system_resources(
        self,
        host: str,
        cpu_usage: float,
        memory_usage: float,
    ):
        """记录系统资源"""
        self.system_cpu_usage.labels(host=host).set(cpu_usage)
        self.system_memory_usage.labels(host=host).set(memory_usage)

    def set_app_info(self, info: Dict[str, Any]):
        """设置应用信息"""
        self.app_info.info(info)

    def start_metrics_server(self, port: int = 9090):
        """启动Prometheus指标服务器"""
        try:
            start_http_server(port)
            logger.info(f"Prometheus metrics server started on port {port}")
        except Exception as e:
            logger.error(f"Failed to start Prometheus metrics server: {e}")


# 全局实例
metrics_exporter = PrometheusMetricsExporter()


def get_metrics_exporter() -> PrometheusMetricsExporter:
    """获取指标导出器实例"""
    return metrics_exporter
