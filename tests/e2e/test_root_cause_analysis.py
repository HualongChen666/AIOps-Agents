# -*- coding: utf-8 -*-
"""
E2E Test: Root Cause Analysis Workflow
真实E2E测试：根因分析的端到端流程，不使用Mock
"""

import asyncio
import json  # noqa: F401
from datetime import datetime, timedelta
from typing import Any, Dict, List  # noqa: F401

import httpx  # noqa: F401
import pytest


@pytest.mark.e2e
@pytest.mark.slow
class TestRootCauseAnalysisWorkflow:
    """根因分析端到端流程E2E测试"""

    @pytest.mark.asyncio
    async def test_complete_root_cause_analysis_pipeline(self, http_client):
        """测试完整的根因分析管道：数据收集→关联分析→根因识别"""

        # 步骤1: 模拟系统指标异常，创建告警
        system_metrics = {
            "component": "payment_api",
            "metrics": {
                "response_time_p95": 2500,  # 超过阈值
                "error_rate": 0.12,  # 错误率上升
                "throughput": 800,  # 吞吐量下降
                "cpu_usage": 78.0,
                "memory_usage": 82.0,
                "db_connections": 45,  # 数据库连接数高
                "cache_hit_rate": 65.0,  # 缓存命中率下降
            },
            "timestamp": datetime.now().isoformat(),
        }

        # 创建性能告警
        alert_response = await http_client.post(
            "http://localhost:8000/api/v1/alerts",
            json={
                "component": "payment_api",
                "severity": "critical",
                "title": "支付API性能异常",
                "description": "响应时间和错误率超过阈值",
                "metrics": system_metrics["metrics"],
                "source": "monitoring",
                "timestamp": system_metrics["timestamp"],
            },
            timeout=10.0,
        )

        assert alert_response.status_code in [200, 201, 202]
        alert_id = alert_response.json().get("id")

        # 步骤2: 触发根因分析
        rca_response = await http_client.post(
            f"http://localhost:8000/api/v1/alerts/{alert_id}/root-cause",
            json={"analysis_depth": "deep", "include_historical": True, "time_window_hours": 24},
            timeout=30.0,
        )

        assert rca_response.status_code in [200, 202]
        rca_result = rca_response.json()

        # 验证根因分析结果
        assert "root_cause" in rca_result
        assert "confidence" in rca_result
        assert "related_events" in rca_result
        assert rca_result["confidence"] > 0.0

        # 步骤3: 获取关联的系统事件
        events_response = await http_client.get(
            f"http://localhost:8000/api/v1/events?related_to={alert_id}", timeout=15.0
        )

        assert events_response.status_code == 200
        related_events = events_response.json()
        assert len(related_events) > 0

        # 步骤4: 验证根因假设
        hypothesis_response = await http_client.post(
            f"http://localhost:8000/api/v1/alerts/{alert_id}/verify-hypothesis",
            json={
                "hypothesis": "数据库连接池耗尽导致性能下降",
                "verification_steps": ["检查数据库连接数", "分析慢查询", "检查缓存配置"],
            },
            timeout=20.0,
        )

        assert hypothesis_response.status_code in [200, 202]
        verification_result = hypothesis_response.json()
        assert "verified" in verification_result

        # 清理
        await http_client.delete(f"http://localhost:8000/api/v1/alerts/{alert_id}", timeout=10.0)

    @pytest.mark.asyncio
    async def test_multi_component_correlation_analysis(self, http_client):
        """测试多组件关联分析"""

        # 创建多个相关组件的告警
        components = ["api_gateway", "auth_service", "user_service"]
        alert_ids = []

        for component in components:
            alert_data = {
                "component": component,
                "severity": "warning",
                "title": f"{component}性能下降",
                "description": f"{component}响应时间增加",
                "metrics": {"response_time_ms": 1200, "error_rate": 0.05},
                "source": "monitoring",
                "timestamp": datetime.now().isoformat(),
            }

            response = await http_client.post(
                "http://localhost:8000/api/v1/alerts", json=alert_data, timeout=10.0
            )

            if response.status_code in [200, 201, 202]:
                alert_ids.append(response.json().get("id"))

        # 等待关联分析
        await asyncio.sleep(2)

        # 触发跨组件关联分析
        correlation_response = await http_client.post(
            "http://localhost:8000/api/v1/root-cause/correlation",
            json={
                "alert_ids": alert_ids,
                "analysis_type": "cross_component",
                "time_window_minutes": 30,
            },
            timeout=30.0,
        )

        assert correlation_response.status_code in [200, 202]
        correlation_result = correlation_response.json()

        # 验证关联分析结果
        assert "correlations" in correlation_result
        assert "common_root_cause" in correlation_result
        assert len(correlation_result["correlations"]) > 0

        # 清理
        for alert_id in alert_ids:
            await http_client.delete(
                f"http://localhost:8000/api/v1/alerts/{alert_id}", timeout=10.0
            )

    @pytest.mark.asyncio
    async def test_historical_pattern_matching(self, http_client):
        """测试历史模式匹配"""

        # 创建与历史模式相似的告警
        alert_data = {
            "component": "database_cluster",
            "severity": "critical",
            "title": "数据库集群性能下降",
            "description": "查询响应时间显著增加",
            "metrics": {
                "query_time_p95": 8000,
                "connection_timeout_rate": 0.08,
                "replication_lag_ms": 5000,
            },
            "source": "monitoring",
            "timestamp": datetime.now().isoformat(),
        }

        response = await http_client.post(
            "http://localhost:8000/api/v1/alerts", json=alert_data, timeout=10.0
        )

        assert response.status_code in [200, 201, 202]
        alert_id = response.json().get("id")

        # 触发历史模式匹配
        pattern_response = await http_client.post(
            f"http://localhost:8000/api/v1/alerts/{alert_id}/pattern-match",
            json={"lookback_days": 30, "similarity_threshold": 0.7},
            timeout=30.0,
        )

        assert pattern_response.status_code in [200, 202]
        pattern_result = pattern_response.json()

        # 验证模式匹配结果
        assert "matched_patterns" in pattern_result
        assert "similarity_score" in pattern_result

        # 如果找到匹配模式，获取历史解决方案
        if pattern_result.get("matched_patterns"):
            best_match = pattern_result["matched_patterns"][0]

            solution_response = await http_client.get(
                f"http://localhost:8000/api/v1/incidents/{best_match['incident_id']}/solution",
                timeout=10.0,
            )

            assert solution_response.status_code in [200, 404]  # 404 if no solution

        # 清理
        await http_client.delete(f"http://localhost:8000/api/v1/alerts/{alert_id}", timeout=10.0)

    @pytest.mark.asyncio
    async def test_causal_chain_analysis(self, http_client):
        """测试因果链分析"""

        # 创建复杂的系统故障场景
        failure_scenario = {
            "initial_alert": {
                "component": "load_balancer",
                "severity": "critical",
                "title": "负载均衡器故障",
                "metrics": {"health_check_failures": 150},
                "timestamp": datetime.now().isoformat(),
            },
            "cascade_events": [
                {
                    "component": "web_server_1",
                    "event_type": "high_cpu",
                    "timestamp": (datetime.now() + timedelta(seconds=5)).isoformat(),
                },
                {
                    "component": "database_primary",
                    "event_type": "connection_exhaustion",
                    "timestamp": (datetime.now() + timedelta(seconds=10)).isoformat(),
                },
                {
                    "component": "cache_server",
                    "event_type": "memory_pressure",
                    "timestamp": (datetime.now() + timedelta(seconds=15)).isoformat(),
                },
            ],
        }

        # 创建初始告警
        initial_response = await http_client.post(
            "http://localhost:8000/api/v1/alerts",
            json=failure_scenario["initial_alert"],
            timeout=10.0,
        )

        assert initial_response.status_code in [200, 201, 202]
        alert_id = initial_response.json().get("id")

        # 添加级联事件
        for event in failure_scenario["cascade_events"]:
            event_response = await http_client.post(
                "http://localhost:8000/api/v1/events",
                json={"alert_id": alert_id, **event},
                timeout=10.0,
            )
            assert event_response.status_code in [200, 201, 202]

        # 触发因果链分析
        chain_response = await http_client.post(
            f"http://localhost:8000/api/v1/alerts/{alert_id}/causal-chain",
            json={"max_chain_length": 10, "confidence_threshold": 0.6},
            timeout=30.0,
        )

        assert chain_response.status_code in [200, 202]
        chain_result = chain_response.json()

        # 验证因果链分析结果
        assert "causal_chain" in chain_result
        assert "root_event" in chain_result
        assert len(chain_result["causal_chain"]) > 0

        # 验证因果链的时间顺序
        chain = chain_result["causal_chain"]
        for i in range(len(chain) - 1):
            assert chain[i]["timestamp"] <= chain[i + 1]["timestamp"]

        # 清理
        await http_client.delete(f"http://localhost:8000/api/v1/alerts/{alert_id}", timeout=10.0)

    @pytest.mark.asyncio
    async def test_root_cause_confidence_validation(self, http_client):
        """测试根因分析置信度验证"""

        # 创建测试告警
        alert_data = {
            "component": "test_service",
            "severity": "warning",
            "title": "测试服务告警",
            "description": "用于置信度验证的测试告警",
            "metrics": {"test_metric": 150},
            "source": "test",
            "timestamp": datetime.now().isoformat(),
        }

        response = await http_client.post(
            "http://localhost:8000/api/v1/alerts", json=alert_data, timeout=10.0
        )

        assert response.status_code in [200, 201, 202]
        alert_id = response.json().get("id")

        # 执行根因分析
        rca_response = await http_client.post(
            f"http://localhost:8000/api/v1/alerts/{alert_id}/root-cause",
            json={"analysis_depth": "standard", "include_confidence": True},
            timeout=20.0,
        )

        assert rca_response.status_code in [200, 202]
        rca_result = rca_response.json()

        # 验证置信度字段
        assert "confidence" in rca_result
        assert 0.0 <= rca_result["confidence"] <= 1.0

        # 如果置信度较低，请求更多数据收集
        if rca_result["confidence"] < 0.7:
            additional_data_response = await http_client.post(
                f"http://localhost:8000/api/v1/alerts/{alert_id}/collect-data",
                json={"data_types": ["logs", "metrics", "traces"], "time_window_minutes": 60},
                timeout=30.0,
            )

            assert additional_data_response.status_code in [200, 202]

            # 重新分析
            reanalysis_response = await http_client.post(
                f"http://localhost:8000/api/v1/alerts/{alert_id}/root-cause",
                json={"analysis_depth": "deep", "use_additional_data": True},
                timeout=30.0,
            )

            assert reanalysis_response.status_code in [200, 202]
            reanalysis_result = reanalysis_response.json()
            assert reanalysis_result["confidence"] >= rca_result["confidence"]

        # 清理
        await http_client.delete(f"http://localhost:8000/api/v1/alerts/{alert_id}", timeout=10.0)


@pytest.mark.e2e
@pytest.mark.slow
class TestRootCauseReporting:
    """根因分析报告E2E测试"""

    @pytest.mark.asyncio
    async def test_generate_rca_report(self, http_client):
        """测试生成根因分析报告"""

        # 创建告警
        alert_data = {
            "component": "reporting_service",
            "severity": "critical",
            "title": "报告服务故障",
            "description": "报告生成失败",
            "metrics": {"error_count": 25},
            "source": "monitoring",
            "timestamp": datetime.now().isoformat(),
        }

        response = await http_client.post(
            "http://localhost:8000/api/v1/alerts", json=alert_data, timeout=10.0
        )

        assert response.status_code in [200, 201, 202]
        alert_id = response.json().get("id")

        # 执行根因分析
        await http_client.post(
            f"http://localhost:8000/api/v1/alerts/{alert_id}/root-cause",
            json={"analysis_depth": "deep"},
            timeout=20.0,
        )

        # 生成RCA报告
        report_response = await http_client.post(
            f"http://localhost:8000/api/v1/alerts/{alert_id}/rca-report",
            json={"format": "detailed", "include_recommendations": True, "language": "zh-CN"},
            timeout=15.0,
        )

        assert report_response.status_code in [200, 202]
        report = report_response.json()

        # 验证报告结构
        assert "summary" in report
        assert "root_cause" in report
        assert "timeline" in report
        assert "recommendations" in report
        assert "metadata" in report

        # 清理
        await http_client.delete(f"http://localhost:8000/api/v1/alerts/{alert_id}", timeout=10.0)

    @pytest.mark.asyncio
    async def test_rca_report_export_formats(self, http_client):
        """测试RCA报告不同导出格式"""

        alert_data = {
            "component": "export_test_service",
            "severity": "warning",
            "title": "导出测试告警",
            "description": "用于测试报告导出",
            "metrics": {"test": 100},
            "source": "test",
            "timestamp": datetime.now().isoformat(),
        }

        response = await http_client.post(
            "http://localhost:8000/api/v1/alerts", json=alert_data, timeout=10.0
        )

        alert_id = response.json().get("id")

        # 测试不同格式导出
        formats = ["json", "html", "pdf", "markdown"]

        for format_type in formats:
            export_response = await http_client.post(
                f"http://localhost:8000/api/v1/alerts/{alert_id}/rca-report",
                json={"format": format_type},
                timeout=15.0,
            )

            assert export_response.status_code in [200, 202]

        # 清理
        await http_client.delete(f"http://localhost:8000/api/v1/alerts/{alert_id}", timeout=10.0)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "e2e"])
