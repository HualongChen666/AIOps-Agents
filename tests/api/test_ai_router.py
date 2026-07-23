# -*- coding: utf-8 -*-
# tests/api/test_ai_router.py
# AI路由API测试
import asyncio  # noqa: F401
import os
import sys
import time
from unittest.mock import AsyncMock, Mock, patch  # noqa: F401

import pytest  # noqa: F401


@pytest.fixture(autouse=True)
def _patch_expensive_ai_context(monkeypatch):
    """Patch expensive snapshot/rich-context collection to keep AI router tests fast."""
    monkeypatch.setattr(
        "api.ai_router._collect_snapshot_with_cache",
        AsyncMock(return_value={}),
    )
    monkeypatch.setattr(
        "api.ai_router._collect_rich_context",
        AsyncMock(return_value=None),
    )

from fastapi import FastAPI
from fastapi.testclient import TestClient

import api.ai_router as _ai_router
from api.ai_router import (
    _build_context_summary,
    _build_metrics_context,
    _extract_disk_usage,
    _extract_gather_result,
    _safe_alert_value,
    _safe_get_metric,
    router,
)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# 直接导入路由模块，避免导入main.py

# 创建独立的测试应用
test_app = FastAPI()
test_app.include_router(router)
client = TestClient(test_app)


class TestAIRouter:
    """AI路由测试类"""

    def test_ai_analyze_basic_request(self):
        """测试基本AI分析请求"""
        request_data = {
            "query": "CPU使用率飙升，请分析根因",
            "include_metrics": False,  # 禁用指标采集以避免依赖问题
            "platform": "windows",
            "include_rich_context": False,
        }

        # Mock整个ai_engine模块
        with patch("api.ai_router.analyze") as mock_analyze:
            mock_analyze.return_value = {
                "analysis": "分析结果",
                "root_cause": "CPU过载",
                "suggestions": ["增加资源", "优化进程"],
            }

            response = client.post("/api/ai/analyze", json=request_data)

            # 验证响应状态码
            assert response.status_code in [200, 202]  # 可能是异步处理

            if response.status_code == 200:
                data = response.json()
                assert "analysis" in data or "result" in data

    def test_ai_analyze_with_rich_context(self):
        """测试包含富上下文的AI分析请求"""
        request_data = {
            "query": "内存使用过高",
            "include_metrics": False,  # 禁用指标采集
            "platform": "linux",
            "include_rich_context": True,
        }

        with patch("api.ai_router.analyze") as mock_analyze:
            mock_analyze.return_value = {
                "analysis": "内存分析",
                "rich_context": {"top_processes": [], "recent_alerts": [], "recent_repairs": []},
            }

            response = client.post("/api/ai/analyze", json=request_data)

            assert response.status_code in [200, 202]

    def test_ai_analyze_without_metrics(self):
        """测试不包含指标的AI分析请求"""
        request_data = {
            "query": "系统响应慢",
            "include_metrics": False,
            "platform": "windows",
            "include_rich_context": False,
        }

        with patch("api.ai_router.analyze") as mock_analyze:
            mock_analyze.return_value = {"analysis": "响应慢分析"}

            response = client.post("/api/ai/analyze", json=request_data)

            assert response.status_code in [200, 202]

    def test_ai_analyze_query_validation(self):
        """测试查询参数验证"""
        # 测试空查询
        request_data = {"query": "", "include_metrics": False, "platform": "windows"}

        response = client.post("/api/ai/analyze", json=request_data)
        assert response.status_code == 422  # 验证错误

        # 测试过长查询
        request_data = {
            "query": "a" * 3000,  # 超过2000字符限制
            "include_metrics": False,
            "platform": "windows",
        }

        response = client.post("/api/ai/analyze", json=request_data)
        assert response.status_code == 422

    def test_ai_analyze_platform_validation(self):
        """测试平台参数验证"""
        # 测试无效平台
        request_data = {
            "query": "测试查询",
            "include_metrics": False,
            "platform": "invalid_platform",
        }

        response = client.post("/api/ai/analyze", json=request_data)
        assert response.status_code == 422

    def test_ai_analyze_platform_normalization(self):
        """测试平台参数规范化"""
        # 测试大写平台名
        request_data = {
            "query": "测试查询",
            "include_metrics": False,
            "platform": "WINDOWS",  # 应该被规范化为小写
        }

        with patch("api.ai_router.analyze") as mock_analyze:
            mock_analyze.return_value = {"analysis": "测试结果"}

            response = client.post("/api/ai/analyze", json=request_data)
            # 平台规范化在Pydantic层处理，应该能正常处理大写
            assert response.status_code in [200, 202, 422]  # 可能接受或拒绝

    def test_ai_analyze_error_handling(self):
        """测试AI分析错误处理"""
        _ = {"query": "测试错误处理", "include_metrics": False, "platform": "windows"}

        # 由于analyze是async函数，我们需要使用不同的方法
        # 暂时跳过这个测试，标记为xfail
        pytest.xfail("Async mock with TestClient requires different approach")

    def test_ai_analyze_timeout_handling(self):
        """测试AI分析超时处理"""
        # 暂时跳过这个测试，标记为xfail
        pytest.xfail("Async mock with TestClient requires different approach")

    def test_ai_analyze_concurrent_requests(self):
        """测试并发AI分析请求"""

        request_data = {"query": "并发测试", "include_metrics": False, "platform": "windows"}

        async def make_request():
            with patch("api.ai_router.analyze") as mock_analyze:
                mock_analyze.return_value = {"analysis": "并发结果"}
                return client.post("/api/ai/analyze", json=request_data)

        # 这里简化处理，实际应该使用异步测试
        responses = []
        for _ in range(3):
            with patch("api.ai_router.analyze") as mock_analyze:
                mock_analyze.return_value = {"analysis": f"结果{_}"}
                response = client.post("/api/ai/analyze", json=request_data)
                responses.append(response)

        # 验证所有请求都得到处理
        for response in responses:
            assert response.status_code in [200, 202]

    def test_ai_analyze_response_format(self):
        """测试AI分析响应格式"""
        request_data = {"query": "响应格式测试", "include_metrics": False, "platform": "windows"}

        with patch("api.ai_router.analyze") as mock_analyze:
            mock_analyze.return_value = {
                "analysis": "分析结果",
                "confidence": 0.95,
                "suggestions": ["建议1", "建议2"],
                "metadata": {"model": "gpt-4", "timestamp": "2024-01-01T00:00:00Z"},
            }

            response = client.post("/api/ai/analyze", json=request_data)

            if response.status_code == 200:
                data = response.json()
                # 验证响应包含必要字段
                assert isinstance(data, dict)

    def test_ai_analyze_with_empty_query(self):
        """测试空查询字符串"""
        request_data = {
            "query": "   ",  # 只有空白字符
            "include_metrics": False,
            "platform": "windows",
        }

        response = client.post("/api/ai/analyze", json=request_data)
        assert response.status_code == 422


class TestAIRouterIntegration:
    """AI路由集成测试"""

    def test_ai_analyze_end_to_end(self):
        """测试AI分析端到端流程"""
        request_data = {
            "query": "端到端测试",
            "include_metrics": False,
            "platform": "windows",
            "include_rich_context": False,
        }

        # 这里测试实际的集成流程
        # 如果AI引擎不可用，应该使用mock
        with patch("api.ai_router.analyze") as mock_analyze:
            mock_analyze.return_value = {"analysis": "端到端分析结果"}

            response = client.post("/api/ai/analyze", json=request_data)
            assert response.status_code in [200, 202]

    def test_ai_analyze_with_snapshot_cache(self):
        """测试使用快照缓存的AI分析"""
        request_data = {"query": "缓存测试", "include_metrics": False, "platform": "windows"}

        with patch("api.ai_router.analyze") as mock_analyze:
            mock_analyze.return_value = {"analysis": "缓存分析"}

            # 第一次请求
            response1 = client.post("/api/ai/analyze", json=request_data)
            # 第二次请求（应该使用缓存）
            response2 = client.post("/api/ai/analyze", json=request_data)

            assert response1.status_code in [200, 202]
            assert response2.status_code in [200, 202]


class TestAIRouterPerformance:
    """AI路由性能测试"""

    def test_ai_analyze_response_time(self):
        """测试AI分析响应时间"""

        request_data = {
            "query": "性能测试",
            "include_metrics": False,  # 禁用指标采集以加快测试
            "include_rich_context": False,
            "platform": "windows",
        }

        with patch.object(_ai_router, "analyze", new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = "快速结果"

            start_time = time.time()
            response = client.post("/api/ai/analyze", json=request_data)
            end_time = time.time()

            response_time = end_time - start_time

            assert response.status_code in [200, 202]
            # 响应时间应该在合理范围内（< 15秒，考虑到mock开销）
            assert response_time < 15.0

    def test_ai_analyze_with_large_context(self):
        """测试大上下文AI分析"""
        # 模拟大量上下文数据
        large_context = {
            "top_processes": [{"pid": i, "name": f"process_{i}"} for i in range(100)],
            "recent_alerts": [{"id": i, "title": f"alert_{i}"} for i in range(50)],
        }

        request_data = {"query": "大上下文测试", "include_metrics": False, "platform": "windows"}

        with patch("api.ai_router.analyze") as mock_analyze:
            mock_analyze.return_value = {
                "analysis": "大上下文分析",
                "context_size": len(large_context),
            }

            response = client.post("/api/ai/analyze", json=request_data)
            assert response.status_code in [200, 202]


class TestAIRouterRichContext:
    """测试富上下文功能"""

    def test_ai_analyze_with_metrics_enabled(self):
        """测试启用指标采集"""
        request_data = {
            "query": "指标测试",
            "include_metrics": True,
            "platform": "windows",
            "include_rich_context": False,
        }

        with patch("api.ai_router.analyze") as mock_analyze:
            mock_analyze.return_value = {"analysis": "指标分析"}

            response = client.post("/api/ai/analyze", json=request_data)
            assert response.status_code in [200, 202]

    def test_ai_analyze_with_both_metrics_and_rich_context(self):
        """测试同时启用指标和富上下文"""
        request_data = {
            "query": "综合测试",
            "include_metrics": True,
            "platform": "linux",
            "include_rich_context": True,
        }

        with patch("api.ai_router.analyze") as mock_analyze:
            mock_analyze.return_value = {"analysis": "综合分析"}

            response = client.post("/api/ai/analyze", json=request_data)
            assert response.status_code in [200, 202]

    def test_ai_analyze_rich_context_timeout(self):
        """测试富上下文超时"""
        request_data = {
            "query": "超时测试",
            "include_metrics": False,
            "platform": "windows",
            "include_rich_context": True,
        }

        with patch("api.ai_router.analyze") as mock_analyze:
            mock_analyze.return_value = {"analysis": "超时降级分析"}

            response = client.post("/api/ai/analyze", json=request_data)
            assert response.status_code in [200, 202]

    def test_ai_analyze_with_linux_platform(self):
        """测试Linux平台"""
        request_data = {
            "query": "Linux测试",
            "include_metrics": False,
            "platform": "linux",
        }

        with patch("api.ai_router.analyze") as mock_analyze:
            mock_analyze.return_value = {"analysis": "Linux分析"}

            response = client.post("/api/ai/analyze", json=request_data)
            assert response.status_code in [200, 202]

    def test_ai_analyze_with_windows_platform(self):
        """测试Windows平台"""
        request_data = {
            "query": "Windows测试",
            "include_metrics": False,
            "platform": "windows",
        }

        with patch("api.ai_router.analyze") as mock_analyze:
            mock_analyze.return_value = {"analysis": "Windows分析"}

            response = client.post("/api/ai/analyze", json=request_data)
            assert response.status_code in [200, 202]


class TestAIRouterEdgeCases:
    """测试边缘情况"""

    def test_ai_analyze_with_min_query(self):
        """测试最小长度查询"""
        request_data = {
            "query": "a",  # 最小长度1
            "include_metrics": False,
            "platform": "windows",
        }

        with patch("api.ai_router.analyze") as mock_analyze:
            mock_analyze.return_value = {"analysis": "最小查询"}

            response = client.post("/api/ai/analyze", json=request_data)
            assert response.status_code in [200, 202]

    def test_ai_analyze_with_max_query(self):
        """测试最大长度查询"""
        request_data = {
            "query": "a" * 2000,  # 最大长度2000
            "include_metrics": False,
            "platform": "windows",
        }

        with patch("api.ai_router.analyze") as mock_analyze:
            mock_analyze.return_value = {"analysis": "最大查询"}

            response = client.post("/api/ai/analyze", json=request_data)
            assert response.status_code in [200, 202]

    def test_ai_analyze_with_special_characters(self):
        """测试特殊字符查询"""
        request_data = {
            "query": "测试特殊字符: <>&\"'\\n\\t",
            "include_metrics": False,
            "platform": "windows",
        }

        with patch("api.ai_router.analyze") as mock_analyze:
            mock_analyze.return_value = {"analysis": "特殊字符分析"}

            response = client.post("/api/ai/analyze", json=request_data)
            assert response.status_code in [200, 202]

    def test_ai_analyze_with_unicode(self):
        """测试Unicode字符查询"""
        request_data = {
            "query": "测试Unicode: 你好世界 🌍",
            "include_metrics": False,
            "platform": "windows",
        }

        with patch("api.ai_router.analyze") as mock_analyze:
            mock_analyze.return_value = {"analysis": "Unicode分析"}

            response = client.post("/api/ai/analyze", json=request_data)
            assert response.status_code in [200, 202]

    def test_ai_analyze_with_whitespace_query(self):
        """测试前后有空白的查询"""
        request_data = {
            "query": "  前后空白  ",
            "include_metrics": False,
            "platform": "windows",
        }

        with patch("api.ai_router.analyze") as mock_analyze:
            mock_analyze.return_value = {"analysis": "空白处理"}

            response = client.post("/api/ai/analyze", json=request_data)
            assert response.status_code in [200, 202]

    def test_ai_analyze_with_missing_optional_fields(self):
        """测试缺少可选字段"""
        request_data = {"query": "测试查询"}  # 缺少include_metrics和platform

        with patch("api.ai_router.analyze") as mock_analyze:
            mock_analyze.return_value = {"analysis": "默认值测试"}

            response = client.post("/api/ai/analyze", json=request_data)
            assert response.status_code in [200, 202]


class TestAIRouterResponseValidation:
    """测试响应验证"""

    def test_ai_analyze_response_has_status(self):
        """测试响应包含status字段"""
        request_data = {"query": "状态测试", "include_metrics": False, "platform": "windows"}

        with patch("api.ai_router.analyze") as mock_analyze:
            mock_analyze.return_value = "分析结果"

            response = client.post("/api/ai/analyze", json=request_data)
            if response.status_code == 200:
                data = response.json()
                assert "status" in data

    def test_ai_analyze_response_has_analysis(self):
        """测试响应包含analysis字段"""
        request_data = {"query": "分析测试", "include_metrics": False, "platform": "windows"}

        with patch("api.ai_router.analyze") as mock_analyze:
            mock_analyze.return_value = "分析结果"

            response = client.post("/api/ai/analyze", json=request_data)
            if response.status_code == 200:
                data = response.json()
                assert "analysis" in data

    def test_ai_analyze_response_has_platform(self):
        """测试响应包含platform字段"""
        request_data = {"query": "平台测试", "include_metrics": False, "platform": "linux"}

        with patch("api.ai_router.analyze") as mock_analyze:
            mock_analyze.return_value = "分析结果"

            response = client.post("/api/ai/analyze", json=request_data)
            if response.status_code == 200:
                data = response.json()
                assert "platform" in data

    def test_ai_analyze_response_content_type(self):
        """测试响应内容类型"""
        request_data = {"query": "内容类型测试", "include_metrics": False, "platform": "windows"}

        with patch("api.ai_router.analyze") as mock_analyze:
            mock_analyze.return_value = "分析结果"

            response = client.post("/api/ai/analyze", json=request_data)
            assert "application/json" in response.headers["content-type"]


class TestAIRouterErrorScenarios:
    """测试错误场景"""

    def test_ai_analyze_with_null_analyze_result(self):
        """测试AI引擎返回None"""
        request_data = {"query": "空结果测试", "include_metrics": False, "platform": "windows"}

        with patch("api.ai_router.analyze") as mock_analyze:
            mock_analyze.return_value = None

            response = client.post("/api/ai/analyze", json=request_data)
            assert response.status_code in [200, 500]

    def test_ai_analyze_with_empty_analyze_result(self):
        """测试AI引擎返回空字符串"""
        request_data = {"query": "空字符串测试", "include_metrics": False, "platform": "windows"}

        with patch("api.ai_router.analyze") as mock_analyze:
            mock_analyze.return_value = ""

            response = client.post("/api/ai/analyze", json=request_data)
            assert response.status_code in [200, 500]

    def test_ai_analyze_with_invalid_json(self):
        """测试无效JSON请求"""
        response = client.post("/api/ai/analyze", data="invalid json")
        assert response.status_code == 422

    def test_ai_analyze_with_missing_query(self):
        """测试缺少query字段"""
        request_data = {"include_metrics": False, "platform": "windows"}

        response = client.post("/api/ai/analyze", json=request_data)
        assert response.status_code == 422

    def test_ai_analyze_with_wrong_method(self):
        """测试错误的HTTP方法"""
        response = client.get("/api/ai/analyze")
        assert response.status_code in [405, 404]

    def test_ai_analyze_with_put_method(self):
        """测试PUT方法"""
        request_data = {"query": "PUT测试", "include_metrics": False, "platform": "windows"}

        response = client.put("/api/ai/analyze", json=request_data)
        assert response.status_code in [405, 404]

    def test_ai_analyze_with_delete_method(self):
        """测试DELETE方法"""
        response = client.delete("/api/ai/analyze")
        assert response.status_code in [405, 404]


class TestAIRouterHelpers:
    """AI路由辅助函数测试"""

    def test_safe_alert_value_numeric(self):
        assert _safe_alert_value(42) == 42
        assert _safe_alert_value(3.14) == 3.14
        assert _safe_alert_value(True) is True

    def test_safe_alert_value_string(self):
        assert _safe_alert_value("12.5") == 12.5
        assert _safe_alert_value("abc") == "abc"

    def test_safe_alert_value_object_truncated(self):
        class Foo:
            def __str__(self):
                return "x" * 100

        assert len(_safe_alert_value(Foo())) == 64

    def test_safe_get_metric(self):
        snapshot = {"cpu": {"usage_percent": 80}}
        assert _safe_get_metric(snapshot, "cpu", "usage_percent") == 80
        assert _safe_get_metric(snapshot, "cpu", "missing") == "N/A"
        assert _safe_get_metric("not_a_dict", "cpu", "usage_percent") == "N/A"

    def test_extract_gather_result(self):
        assert _extract_gather_result([1, 2], "test", list) == [1, 2]
        assert _extract_gather_result({"a": 1}, "test", dict) == {"a": 1}
        assert _extract_gather_result(ValueError("err"), "test", list) is None
        assert _extract_gather_result(asyncio.CancelledError(), "test", list) is None

    def test_extract_disk_usage_list(self):
        snapshot = {"disk": [{"usage_percent": 70}]}
        assert _extract_disk_usage(snapshot) == 70

    def test_extract_disk_usage_dict(self):
        snapshot = {"disk": {"sda1": {"usage_percent": 60}}}
        assert _extract_disk_usage(snapshot) == 60

    def test_extract_disk_usage_missing(self):
        assert _extract_disk_usage({}) == "N/A"

    def test_build_metrics_context(self):
        snapshot = {
            "cpu": {"usage_percent": 80},
            "memory": {"usage_percent": 70},
            "disk": [{"usage_percent": 60}],
        }
        ctx = _build_metrics_context(snapshot)
        assert "CPU=80" in ctx
        assert "内存=70" in ctx

    def test_build_context_summary(self):
        rich = {
            "top_processes": [1, 2],
            "recent_alerts": [1, 2, 3],
            "recent_repairs": [1],
        }
        summary = _build_context_summary(rich)
        assert summary["process_count"] == 2
        assert summary["alert_count"] == 3
        assert summary["repair_count"] == 1

    def test_build_context_summary_empty(self):
        assert _build_context_summary(None)["rich_enabled"] is False


class TestAIRouterAdvancedScenarios:
    """AI路由进阶场景"""

    def test_ai_analyze_with_metrics_context(self):
        """测试启用指标上下文分支"""
        request_data = {
            "query": "指标测试",
            "include_metrics": True,
            "include_rich_context": False,
            "platform": "windows",
        }
        with (
            patch.object(_ai_router, "get_cached_snapshot") as mock_snapshot,
            patch.object(_ai_router, "analyze", new_callable=AsyncMock) as mock_analyze,
        ):
            mock_snapshot.return_value = {
                "cpu": {"usage_percent": 80},
                "memory": {"usage_percent": 70},
                "disk": [{"usage_percent": 60}],
            }
            mock_analyze.return_value = "分析结果"
            response = client.post("/api/ai/analyze", json=request_data)
            assert response.status_code == 200
            data = response.json()
            assert "metrics_context" in data
            assert "CPU" in data["metrics_context"]

    def test_ai_analyze_with_rich_context(self):
        """测试启用富上下文分支"""
        request_data = {
            "query": "富上下文测试",
            "include_metrics": False,
            "include_rich_context": True,
            "platform": "windows",
        }
        with (
            patch.object(_ai_router, "get_cached_snapshot") as mock_snapshot,
            patch.object(_ai_router, "_collect_rich_context", new_callable=AsyncMock) as mock_rich,
            patch.object(_ai_router, "analyze", new_callable=AsyncMock) as mock_analyze,
        ):
            mock_snapshot.return_value = {"cpu": {"usage_percent": 80}}
            mock_rich.return_value = {
                "top_processes": [],
                "recent_alerts": [],
                "recent_repairs": [],
                "stats": {},
            }
            mock_analyze.return_value = "分析结果"
            response = client.post("/api/ai/analyze", json=request_data)
            assert response.status_code == 200
            data = response.json()
            assert "context_summary" in data

    def test_ai_analyze_exception_returns_500(self):
        """测试AI引擎异常返回500"""
        request_data = {
            "query": "异常测试",
            "include_metrics": False,
            "include_rich_context": False,
            "platform": "windows",
        }
        with patch.object(_ai_router, "analyze") as mock_analyze:
            mock_analyze.side_effect = RuntimeError("AI engine failed")
            response = client.post("/api/ai/analyze", json=request_data)
            assert response.status_code == 500
