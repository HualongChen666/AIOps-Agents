# -*- coding: utf-8 -*-
# tests/unit/test_ai_service.py
# AI服务层单元测试
import asyncio
from unittest.mock import AsyncMock, Mock, patch  # noqa: F401

import pytest

from core.ai_service import (
    AIContextService,
    _extract_gather_result,
    _safe_alert_value,
    _safe_get_metric,
    ai_context_service,
)


class TestSafeAlertValue:
    """_safe_alert_value辅助函数测试"""

    def test_none_value(self):
        """测试None值处理"""
        result = _safe_alert_value(None)  # noqa: F841
        assert result is None

    def test_numeric_values(self):
        """测试数值类型处理"""
        assert _safe_alert_value(42) == 42
        assert _safe_alert_value(3.14) == 3.14
        assert _safe_alert_value(True) is True
        assert _safe_alert_value(False) is False

    def test_string_numeric_conversion(self):
        """测试字符串数值转换"""
        assert _safe_alert_value("42") == 42.0
        assert _safe_alert_value("3.14") == 3.14
        assert _safe_alert_value("-10") == -10.0

    def test_string_non_numeric(self):
        """测试非数字字符串处理"""
        assert _safe_alert_value("error") == "error"
        assert _safe_alert_value("invalid") == "invalid"

    def test_string_truncation(self):
        """测试长字符串截断"""
        long_string = "a" * 100
        result = _safe_alert_value(long_string)  # noqa: F841
        assert len(result) == 64
        assert result == "a" * 64  # noqa: F841

    def test_other_types(self):
        """测试其他类型转换"""
        assert _safe_alert_value([1, 2, 3]) == "[1, 2, 3]"
        assert _safe_alert_value({"key": "value"}) == "{'key': 'value'}"
        assert _safe_alert_value(123) == 123  # int直接返回


class TestSafeGetMetric:
    """_safe_get_metric辅助函数测试"""

    def test_valid_nested_dict(self):
        """测试有效的嵌套字典"""
        snapshot = {"cpu": {"usage": 80.5, "load": 1.2}, "memory": {"usage": 60.0}}
        assert _safe_get_metric(snapshot, "cpu", "usage") == 80.5
        assert _safe_get_metric(snapshot, "cpu", "load") == 1.2
        assert _safe_get_metric(snapshot, "memory", "usage") == 60.0

    def test_missing_section(self):
        """测试缺失的section"""
        snapshot = {"cpu": {"usage": 80.5}}
        assert _safe_get_metric(snapshot, "memory", "usage") == "N/A"

    def test_missing_field(self):
        """测试缺失的field"""
        snapshot = {"cpu": {"usage": 80.5}}
        assert _safe_get_metric(snapshot, "cpu", "load") == "N/A"

    def test_non_dict_snapshot(self):
        """测试非字典snapshot"""
        assert _safe_get_metric(None, "cpu", "usage") == "N/A"
        assert _safe_get_metric("invalid", "cpu", "usage") == "N/A"
        assert _safe_get_metric(123, "cpu", "usage") == "N/A"

    def test_non_dict_section(self):
        """测试非字典section"""
        snapshot = {"cpu": "invalid"}
        assert _safe_get_metric(snapshot, "cpu", "usage") == "N/A"

    def test_custom_default(self):
        """测试自定义默认值"""
        snapshot = {}
        assert _safe_get_metric(snapshot, "cpu", "usage", "unknown") == "unknown"
        assert _safe_get_metric(snapshot, "cpu", "usage", 0) == 0


class TestExtractGatherResult:
    """_extract_gather_result辅助函数测试"""

    def test_cancelled_error(self):
        """测试CancelledError处理"""
        result = _extract_gather_result(asyncio.CancelledError(), "test", str)  # noqa: F841
        assert result is None

    def test_exception_handling(self):
        """测试异常处理"""
        result = _extract_gather_result(ValueError("test error"), "test", str)  # noqa: F841
        assert result is None

    def test_none_value(self):
        """测试None值处理"""
        result = _extract_gather_result(None, "test", str)  # noqa: F841
        assert result is None

    def test_correct_type(self):
        """测试正确类型返回"""
        result = _extract_gather_result("test string", "test", str)  # noqa: F841
        assert result == "test string"  # noqa: F841

    def test_list_type(self):
        """测试列表类型返回"""
        result = _extract_gather_result([1, 2, 3], "test", list)  # noqa: F841
        assert result == [1, 2, 3]  # noqa: F841

    def test_dict_type(self):
        """测试字典类型返回"""
        result = _extract_gather_result({"key": "value"}, "test", dict)  # noqa: F841
        assert result == {"key": "value"}  # noqa: F841

    def test_wrong_type(self):
        """测试错误类型处理"""
        result = _extract_gather_result("string", "test", int)  # noqa: F841
        assert result is None

    def test_wrong_type_list(self):
        """测试错误类型列表处理"""
        result = _extract_gather_result([1, 2, 3], "test", dict)  # noqa: F841
        assert result is None


class TestAIContextService:
    """AI上下文服务测试"""

    def test_service_initialization(self):
        """测试服务初始化"""
        service = AIContextService()
        assert service is not None
        assert isinstance(service, AIContextService)

    def test_default_service_instance(self):
        """测试默认服务实例"""
        assert ai_context_service is not None
        assert isinstance(ai_context_service, AIContextService)

    @pytest.mark.asyncio
    async def test_collect_rich_context_basic(self):
        """测试基本富上下文采集"""
        service = AIContextService()

        # 模拟snapshot
        mock_snapshot = {
            "top_processes": [
                {"pid": 1, "name": "process1", "cpu": 10.5},
                {"pid": 2, "name": "process2", "cpu": 5.2},
            ]
        }

        with patch("core.ai_service.get_cached_snapshot", return_value=mock_snapshot):
            with patch("core.alert_engine.alert_history", []):
                with patch("core.repair_engine.repair_history", []):
                    with patch("core.metrics_history.metrics_history") as mock_metrics:
                        mock_metrics.get_stats.return_value = {}

                        result = await service.collect_rich_context(mock_snapshot)  # noqa: F841

                        assert isinstance(result, dict)
                        assert "top_processes" in result
                        assert "recent_alerts" in result
                        assert "recent_repairs" in result
                        assert "stats" in result

    @pytest.mark.asyncio
    async def test_collect_rich_context_with_empty_snapshot(self):
        """测试空snapshot处理"""
        service = AIContextService()

        with patch("core.ai_service.get_cached_snapshot", return_value=None):
            with patch("core.alert_engine.alert_history", []):
                with patch("core.repair_engine.repair_history", []):
                    with patch("core.metrics_history.metrics_history") as mock_metrics:
                        mock_metrics.get_stats.return_value = {}

                        result = await service.collect_rich_context(None)  # noqa: F841

                        assert result["top_processes"] == []
                        assert result["recent_alerts"] == []
                        assert result["recent_repairs"] == []
                        assert result["stats"] == {}

    @pytest.mark.asyncio
    async def test_collect_rich_context_with_alerts(self):
        """测试告警数据处理"""
        service = AIContextService()

        mock_alerts = [
            {
                "level": "error",
                "title": "CPU High",
                "desc": "CPU usage is high",
                "raw_time": "2024-01-01 10:00",
                "metric": "cpu.usage",
                "value": 90.5,
            },
            {
                "level": "warning",
                "title": "Memory Warning",
                "desc": "Memory usage warning",
                "raw_time": "2024-01-01 11:00",
                "metric": "memory.usage",
                "value": 80.0,
            },
            {
                "level": "info",
                "title": "System Info",
                "desc": "System information",
                "raw_time": "2024-01-01 12:00",
                "metric": "system.status",
                "value": "ok",
            },
        ]

        with patch("core.ai_service.get_cached_snapshot", return_value=None):
            with patch("core.alert_engine.alert_history", mock_alerts):
                with patch("core.repair_engine.repair_history", []):
                    with patch("core.metrics_history.metrics_history") as mock_metrics:
                        mock_metrics.get_stats.return_value = {}

                        result = await service.collect_rich_context(None)  # noqa: F841

                        assert len(result["recent_alerts"]) == 3
                        assert result["recent_alerts"][0]["level"] == "error"
                        assert result["recent_alerts"][0]["title"] == "CPU High"
                        assert result["recent_alerts"][0]["value"] == 90.5

    @pytest.mark.asyncio
    async def test_collect_rich_context_with_repairs(self):
        """测试修复数据处理"""
        service = AIContextService()

        mock_repairs = [
            {"id": 1, "type": "restart", "status": "success"},
            {"id": 2, "type": "config", "status": "success"},
        ]

        with patch("core.ai_service.get_cached_snapshot", return_value=None):
            with patch("core.alert_engine.alert_history", []):
                with patch("core.repair_engine.repair_history", mock_repairs):
                    with patch("core.metrics_history.metrics_history") as mock_metrics:
                        mock_metrics.get_stats.return_value = {}

                        result = await service.collect_rich_context(None)  # noqa: F841

                        assert len(result["recent_repairs"]) == 2
                        assert result["recent_repairs"][0]["id"] == 1

    @pytest.mark.asyncio
    async def test_collect_rich_context_with_stats(self):
        """测试统计数据处理"""
        service = AIContextService()

        mock_stats = {"total_alerts": 100, "total_repairs": 50, "success_rate": 0.95}

        with patch("core.ai_service.get_cached_snapshot", return_value=None):
            with patch("core.alert_engine.alert_history", []):
                with patch("core.repair_engine.repair_history", []):
                    with patch("core.metrics_history.metrics_history") as mock_metrics:
                        mock_metrics.get_stats.return_value = mock_stats

                        result = await service.collect_rich_context(None)  # noqa: F841

                        assert result["stats"] == mock_stats

    @pytest.mark.asyncio
    async def test_collect_rich_context_error_handling(self):
        """测试错误处理"""
        service = AIContextService()

        with patch("core.ai_service.get_cached_snapshot", side_effect=Exception("Snapshot error")):
            with patch("core.alert_engine.alert_history", side_effect=Exception("Alert error")):
                with patch(
                    "core.repair_engine.repair_history", side_effect=Exception("Repair error")
                ):
                    with patch(
                        "core.metrics_history.metrics_history", side_effect=Exception("Stats error")
                    ):

                        result = await service.collect_rich_context(None)  # noqa: F841

                        # 即使所有数据源都出错，也应该返回默认结构
                        assert result["top_processes"] == []
                        assert result["recent_alerts"] == []
                        assert result["recent_repairs"] == []
                        assert result["stats"] == {}

    @pytest.mark.asyncio
    async def test_collect_rich_context_truncation(self):
        """测试数据截断"""
        service = AIContextService()

        long_alert = {
            "level": "error",
            "title": "a" * 300,
            "desc": "b" * 600,
            "raw_time": "c" * 50,
            "metric": "d" * 100,
            "value": "e" * 100,
        }

        with patch("core.ai_service.get_cached_snapshot", return_value=None):
            with patch("core.alert_engine.alert_history", [long_alert]):
                with patch("core.repair_engine.repair_history", []):
                    with patch("core.metrics_history.metrics_history") as mock_metrics:
                        mock_metrics.get_stats.return_value = {}

                        result = await service.collect_rich_context(None)  # noqa: F841

                        alert = result["recent_alerts"][0]
                        assert len(alert["title"]) <= 200
                        assert len(alert["desc"]) <= 500
                        assert len(alert["raw_time"]) <= 32
                        assert len(alert["metric"]) <= 64

    @pytest.mark.asyncio
    async def test_collect_rich_context_timeout_handling(self):
        """测试超时处理"""
        service = AIContextService()

        # 使用AsyncMock来处理异步函数
        async def slow_fetch():
            await asyncio.sleep(10)
            return "data"

        # 使用AsyncMock包装异步函数
        mock_slow_fetch = AsyncMock(side_effect=slow_fetch)

        with patch("core.ai_service.get_cached_snapshot", mock_slow_fetch):
            with patch("core.alert_engine.alert_history", []):
                with patch("core.repair_engine.repair_history", []):
                    with patch("core.metrics_history.metrics_history") as mock_metrics:
                        mock_metrics.get_stats.return_value = {}

                        # 应该在超时时间内完成
                        result = await service.collect_rich_context(None)  # noqa: F841

                        # 由于超时，应该返回默认值
                        assert result["top_processes"] == []

    @pytest.mark.asyncio
    async def test_collect_rich_context_parallel_execution(self):
        """测试并行执行"""
        service = AIContextService()

        call_count = {"count": 0}

        async def tracked_fetch():
            call_count["count"] += 1
            await asyncio.sleep(0.1)
            return "data"

        # 使用AsyncMock包装异步函数
        mock_tracked_fetch = AsyncMock(side_effect=tracked_fetch)

        with patch("core.ai_service.get_cached_snapshot", mock_tracked_fetch):
            with patch("core.alert_engine.alert_history", []):
                with patch("core.repair_engine.repair_history", []):
                    with patch("core.metrics_history.metrics_history") as mock_metrics:
                        mock_metrics.get_stats.return_value = {}

                        import time

                        start = time.time()
                        result = await service.collect_rich_context(None)  # noqa: F841
                        elapsed = time.time() - start

                        # 并行执行应该比串行快
                        assert elapsed < 0.5  # 4个任务并行，每个0.1秒，应该远小于0.4秒


class TestDataCleaning:
    """数据清洗测试"""

    def test_alert_level_normalization(self):
        """测试告警级别标准化"""
        from core.ai_service import AIContextService

        # 测试不同类型的level字段
        mock_alerts = [
            {"level": "error", "title": "Test"},
            {"level": 1, "title": "Test"},
            {"level": None, "title": "Test"},
            {"level": True, "title": "Test"},
        ]

        service = AIContextService()

        # 这个测试主要通过collect_rich_context间接验证
        # 我们可以验证level字段被正确转换为字符串
        with patch("core.ai_service.get_cached_snapshot", return_value=None):
            with patch("core.alert_engine.alert_history", mock_alerts):
                with patch("core.repair_engine.repair_history", []):
                    with patch("core.metrics_history.metrics_history") as mock_metrics:
                        mock_metrics.get_stats.return_value = {}

                        import asyncio

                        result = asyncio.run(service.collect_rich_context(None))  # noqa: F841

                        # 所有level应该都是字符串
                        for alert in result["recent_alerts"]:
                            assert isinstance(alert["level"], str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
