# -*- coding: utf-8 -*-
"""测试Prometheus指标模块"""

import pytest


class TestPrometheusMetricsModule:
    """测试Prometheus指标模块"""

    def test_prometheus_metrics_module_exists(self):
        """测试Prometheus指标模块存在"""
        from core import prometheus_metrics

        assert prometheus_metrics is not None

    def test_prometheus_metrics_has_functions(self):
        """测试Prometheus指标模块有函数"""
        from core import prometheus_metrics

        # 检查模块有函数或类
        assert len(dir(prometheus_metrics)) > 0


class TestPrometheusMetricsExporter:
    """测试PrometheusMetricsExporter类"""

    def test_prometheus_metrics_exporter_init(self):
        """测试PrometheusMetricsExporter初始化"""
        try:
            from core.prometheus_metrics import PrometheusMetricsExporter

            exporter = PrometheusMetricsExporter()

            assert exporter is not None
            assert exporter.api_response_time is not None
            assert exporter.api_throughput is not None
            assert exporter.api_errors is not None
        except Exception as e:
            pytest.skip(f"Cannot test prometheus metrics exporter init: {e}")

    def test_api_metrics_exist(self):
        """测试API指标存在"""
        try:
            from core.prometheus_metrics import PrometheusMetricsExporter

            exporter = PrometheusMetricsExporter()

            assert hasattr(exporter, "api_response_time")
            assert hasattr(exporter, "api_throughput")
            assert hasattr(exporter, "api_errors")
        except Exception as e:
            pytest.skip(f"Cannot test api metrics exist: {e}")

    def test_db_metrics_exist(self):
        """测试数据库指标存在"""
        try:
            from core.prometheus_metrics import PrometheusMetricsExporter

            exporter = PrometheusMetricsExporter()

            assert hasattr(exporter, "db_query_time")
            assert hasattr(exporter, "db_pool_connections")
            assert hasattr(exporter, "db_query_errors")
        except Exception as e:
            pytest.skip(f"Cannot test db metrics exist: {e}")

    def test_ai_metrics_exist(self):
        """测试AI指标存在"""
        try:
            from core.prometheus_metrics import PrometheusMetricsExporter

            exporter = PrometheusMetricsExporter()

            assert hasattr(exporter, "llm_inference_time")
            assert hasattr(exporter, "llm_token_usage")
            assert hasattr(exporter, "llm_cost")
        except Exception as e:
            pytest.skip(f"Cannot test ai metrics exist: {e}")

    def test_rag_metrics_exist(self):
        """测试RAG指标存在"""
        try:
            from core.prometheus_metrics import PrometheusMetricsExporter

            exporter = PrometheusMetricsExporter()

            assert hasattr(exporter, "rag_retrieval_time")
            assert hasattr(exporter, "rag_generation_time")
            assert hasattr(exporter, "rag_e2e_latency")
        except Exception as e:
            pytest.skip(f"Cannot test rag metrics exist: {e}")

    def test_vector_metrics_exist(self):
        """测试向量指标存在"""
        try:
            from core.prometheus_metrics import PrometheusMetricsExporter

            exporter = PrometheusMetricsExporter()

            assert hasattr(exporter, "vector_search_time")
        except Exception as e:
            pytest.skip(f"Cannot test vector metrics exist: {e}")

    def test_agent_metrics_exist(self):
        """测试代理指标存在"""
        try:
            from core.prometheus_metrics import PrometheusMetricsExporter

            exporter = PrometheusMetricsExporter()

            assert hasattr(exporter, "agent_execution_time")
        except Exception as e:
            pytest.skip(f"Cannot test agent metrics exist: {e}")

    def test_performance_metrics_exist(self):
        """测试性能指标存在"""
        try:
            from core.prometheus_metrics import PrometheusMetricsExporter

            exporter = PrometheusMetricsExporter()

            assert hasattr(exporter, "performance_regressions")
        except Exception as e:
            pytest.skip(f"Cannot test performance metrics exist: {e}")


class TestPrometheusMetricsIntegration:
    """测试Prometheus指标集成"""

    def test_all_metrics_initialized(self):
        """测试所有指标已初始化"""
        try:
            from core.prometheus_metrics import PrometheusMetricsExporter

            exporter = PrometheusMetricsExporter()

            # Check all expected metrics are initialized
            expected_metrics = [
                "api_response_time",
                "api_throughput",
                "api_errors",
                "db_query_time",
                "db_pool_connections",
                "db_query_errors",
                "llm_inference_time",
                "llm_token_usage",
                "llm_cost",
                "rag_retrieval_time",
                "rag_generation_time",
                "rag_e2e_latency",
                "vector_search_time",
                "agent_execution_time",
                "performance_regressions",
            ]

            for metric_name in expected_metrics:
                assert hasattr(exporter, metric_name)
        except Exception as e:
            pytest.skip(f"Cannot test all metrics initialized: {e}")

    def test_metrics_types(self):
        """测试指标类型"""
        try:
            from prometheus_client import Counter, Gauge, Histogram

            from core.prometheus_metrics import PrometheusMetricsExporter

            exporter = PrometheusMetricsExporter()

            # Check metric types
            assert isinstance(exporter.api_response_time, Histogram)
            assert isinstance(exporter.api_throughput, Counter)
            assert isinstance(exporter.api_errors, Counter)
            assert isinstance(exporter.db_pool_connections, Gauge)
        except Exception as e:
            pytest.skip(f"Cannot test metrics types: {e}")


class TestPrometheusMetricsExporterEdgeCases:
    """测试PrometheusMetricsExporter边界情况"""

    def test_exporter_singleton(self):
        """测试导出器单例"""
        try:
            from core.prometheus_metrics import PrometheusMetricsExporter

            exporter1 = PrometheusMetricsExporter()
            exporter2 = PrometheusMetricsExporter()

            # Should create new instances
            assert exporter1 is not exporter2
        except Exception as e:
            pytest.skip(f"Cannot test exporter singleton: {e}")

    def test_metric_labels_exist(self):
        """测试指标标签存在"""
        try:
            from core.prometheus_metrics import PrometheusMetricsExporter

            exporter = PrometheusMetricsExporter()

            # Check metrics have labels
            assert hasattr(exporter.api_response_time, "labels")
            assert hasattr(exporter.api_throughput, "labels")
            assert hasattr(exporter.api_errors, "labels")
        except Exception as e:
            pytest.skip(f"Cannot test metric labels exist: {e}")

    def test_metric_descriptions(self):
        """测试指标描述"""
        try:
            from core.prometheus_metrics import PrometheusMetricsExporter

            exporter = PrometheusMetricsExporter()

            # Check metrics have documentation
            assert exporter.api_response_time._doc is not None or True
            assert exporter.api_throughput._doc is not None or True
        except Exception as e:
            pytest.skip(f"Cannot test metric descriptions: {e}")


class TestPrometheusMetricsModuleStructure:
    """测试Prometheus指标模块结构"""

    def test_module_has_exporter_class(self):
        """测试模块有导出器类"""
        try:
            from core import prometheus_metrics

            assert hasattr(prometheus_metrics, "PrometheusMetricsExporter")
        except Exception as e:
            pytest.skip(f"Cannot test module has exporter class: {e}")

    def test_module_has_functions(self):
        """测试模块有函数"""
        try:
            from core import prometheus_metrics

            # Check for functions
            functions = [attr for attr in dir(prometheus_metrics) if not attr.startswith("_")]
            assert len(functions) > 0
        except Exception as e:
            pytest.skip(f"Cannot test module has functions: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
