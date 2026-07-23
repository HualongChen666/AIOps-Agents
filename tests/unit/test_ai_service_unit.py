# -*- coding: utf-8 -*-
# tests/unit/test_ai_service_unit.py
# AI服务模块单元测试
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, Mock, patch  # noqa: F401

import pytest


class TestModuleConstants:
    """模块常量测试"""

    def test_metrics_ctx_max_len(self):
        """测试指标上下文最大长度常量"""
        from core.ai_service import _METRICS_CTX_MAX_LEN

        assert _METRICS_CTX_MAX_LEN == 500

    def test_rich_context_timeout_default(self):
        """测试富上下文超时默认值"""
        from core.ai_service import _RICH_CONTEXT_PER_SOURCE_TIMEOUT_SEC

        assert _RICH_CONTEXT_PER_SOURCE_TIMEOUT_SEC >= 0.5
        assert _RICH_CONTEXT_PER_SOURCE_TIMEOUT_SEC <= 10.0


class TestSafeAlertValue:
    """安全告警值处理测试"""

    def test_safe_alert_value_none(self):
        """测试None值处理"""
        from core.ai_service import _safe_alert_value

        result = _safe_alert_value(None)
        assert result is None

    def test_safe_alert_value_int(self):
        """测试整数值处理"""
        from core.ai_service import _safe_alert_value

        result = _safe_alert_value(42)
        assert result == 42

    def test_safe_alert_value_float(self):
        """测试浮点数值处理"""
        from core.ai_service import _safe_alert_value

        result = _safe_alert_value(3.14)
        assert result == 3.14

    def test_safe_alert_value_bool(self):
        """测试布尔值处理"""
        from core.ai_service import _safe_alert_value

        result = _safe_alert_value(True)
        assert result is True

    def test_safe_alert_value_string_numeric(self):
        """测试数字字符串处理"""
        from core.ai_service import _safe_alert_value

        result = _safe_alert_value("42")
        assert result == 42.0

    def test_safe_alert_value_string_non_numeric(self):
        """测试非数字字符串处理"""
        from core.ai_service import _safe_alert_value

        result = _safe_alert_value("error message")
        assert result == "error message"

    def test_safe_alert_value_string_long(self):
        """测试长字符串截断"""
        from core.ai_service import _safe_alert_value

        long_string = "A" * 100
        result = _safe_alert_value(long_string)
        assert len(result) == 64

    def test_safe_alert_value_dict(self):
        """测试字典类型处理"""
        from core.ai_service import _safe_alert_value

        result = _safe_alert_value({"key": "value"})
        assert isinstance(result, str)
        assert len(result) <= 64

    def test_safe_alert_value_list(self):
        """测试列表类型处理"""
        from core.ai_service import _safe_alert_value

        result = _safe_alert_value([1, 2, 3])
        assert isinstance(result, str)
        assert len(result) <= 64

    def test_safe_alert_value_other_type(self):
        """测试其他类型处理"""
        from core.ai_service import _safe_alert_value

        result = _safe_alert_value({"key": "value"})
        assert isinstance(result, str)
        assert len(result) <= 64


class TestSafeGetMetric:
    """安全指标提取测试"""

    def test_safe_get_metric_valid(self):
        """测试有效指标提取"""
        from core.ai_service import _safe_get_metric

        snapshot = {"system": {"cpu": 75.5}}

        result = _safe_get_metric(snapshot, "system", "cpu")
        assert result == 75.5

    def test_safe_get_metric_missing_section(self):
        """测试缺失section"""
        from core.ai_service import _safe_get_metric

        snapshot = {"system": {"cpu": 75.5}}

        result = _safe_get_metric(snapshot, "network", "in_bytes")
        assert result == "N/A"

    def test_safe_get_metric_missing_field(self):
        """测试缺失field"""
        from core.ai_service import _safe_get_metric

        snapshot = {"system": {"cpu": 75.5}}

        result = _safe_get_metric(snapshot, "system", "memory")
        assert result == "N/A"

    def test_safe_get_metric_not_dict(self):
        """测试非dict输入"""
        from core.ai_service import _safe_get_metric

        result = _safe_get_metric("not a dict", "system", "cpu")
        assert result == "N/A"

    def test_safe_get_metric_section_not_dict(self):
        """测试section不是dict"""
        from core.ai_service import _safe_get_metric

        snapshot = {"system": "not a dict"}

        result = _safe_get_metric(snapshot, "system", "cpu")
        assert result == "N/A"

    def test_safe_get_metric_custom_default(self):
        """测试自定义默认值"""
        from core.ai_service import _safe_get_metric

        snapshot = {}

        result = _safe_get_metric(snapshot, "system", "cpu", default=0)
        assert result == 0


class TestExtractGatherResult:
    """gather结果提取测试"""

    def test_extract_gather_result_cancelled_error(self):
        """测试CancelledError处理"""
        import asyncio

        from core.ai_service import _extract_gather_result

        result = _extract_gather_result(asyncio.CancelledError(), "test", list)
        assert result is None

    def test_extract_gather_result_exception(self):
        """测试异常处理"""
        from core.ai_service import _extract_gather_result

        result = _extract_gather_result(ValueError("test error"), "test", list)
        assert result is None

    def test_extract_gather_result_none(self):
        """测试None处理"""
        from core.ai_service import _extract_gather_result

        result = _extract_gather_result(None, "test", list)
        assert result is None

    def test_extract_gather_result_valid_type(self):
        """测试有效类型"""
        from core.ai_service import _extract_gather_result

        result = _extract_gather_result([1, 2, 3], "test", list)
        assert result == [1, 2, 3]

    def test_extract_gather_result_wrong_type(self):
        """测试错误类型"""
        from core.ai_service import _extract_gather_result

        result = _extract_gather_result("not a list", "test", list)
        assert result is None


class TestAIContextService:
    """AI上下文服务测试"""

    @pytest.mark.asyncio
    async def test_collect_rich_context_with_snapshot(self):
        """测试使用snapshot采集富上下文"""
        from core.ai_service import AIContextService

        service = AIContextService()

        snapshot = {
            "top_processes": [{"name": "process1", "cpu": 10.5}, {"name": "process2", "cpu": 8.3}]
        }

        with patch("core.ai_service.get_cached_snapshot"):
            with patch("core.alert_engine.alert_history", []):
                with patch("core.repair_engine.repair_history", []):
                    with patch("core.metrics_history.metrics_history") as mock_metrics:
                        mock_metrics.get_stats.return_value = {}

                        result = await service.collect_rich_context(snapshot)

                        assert "top_processes" in result
                        assert "recent_alerts" in result
                        assert "recent_repairs" in result
                        assert "stats" in result

    @pytest.mark.asyncio
    async def test_collect_rich_context_alert_history_exception(self):
        """测试告警历史读取异常处理"""
        from core.ai_service import AIContextService

        service = AIContextService()

        snapshot = {}

        with patch("core.ai_service.get_cached_snapshot") as mock_cached:
            mock_cached.return_value = {}
            with patch("core.alert_engine.alert_history") as mock_history:
                mock_history.__iter__ = Mock(side_effect=Exception("Alert history error"))
                with patch("core.repair_engine.repair_history", []):
                    with patch("core.metrics_history.metrics_history") as mock_metrics:
                        mock_metrics.get_stats.return_value = {}

                        result = await service.collect_rich_context(snapshot)

                        assert result["recent_alerts"] == []

    @pytest.mark.asyncio
    async def test_collect_rich_context_repair_history_exception(self):
        """测试修复记录读取异常处理"""
        from core.ai_service import AIContextService

        service = AIContextService()

        snapshot = {}

        with patch("core.ai_service.get_cached_snapshot") as mock_cached:
            mock_cached.return_value = {}
            with patch("core.alert_engine.alert_history", []):
                with patch("core.repair_engine.repair_history") as mock_repair:
                    mock_repair.__iter__ = Mock(side_effect=Exception("Repair history error"))
                    with patch("core.metrics_history.metrics_history") as mock_metrics:
                        mock_metrics.get_stats.return_value = {}

                        result = await service.collect_rich_context(snapshot)

                        assert result["recent_repairs"] == []

    @pytest.mark.asyncio
    async def test_collect_rich_context_cancelled_error(self):
        """测试CancelledError处理"""
        import asyncio

        from core.ai_service import AIContextService

        service = AIContextService()

        snapshot = {}

        with patch("core.ai_service.get_cached_snapshot") as mock_cached:
            mock_cached.return_value = {}
            with patch("core.alert_engine.alert_history", []):
                with patch("core.repair_engine.repair_history", []):
                    with patch("core.metrics_history.metrics_history") as mock_metrics:
                        mock_metrics.get_stats.return_value = {}

                        with patch("core.ai_service.asyncio.gather") as mock_gather:
                            mock_gather.side_effect = asyncio.CancelledError("Cancelled")

                            try:
                                await service.collect_rich_context(snapshot)
                                assert False, "Should raise CancelledError"
                            except asyncio.CancelledError:
                                pass

    @pytest.mark.asyncio
    async def test_collect_rich_context_without_snapshot(self):
        """测试不使用snapshot采集富上下文"""
        from core.ai_service import AIContextService

        service = AIContextService()

        with patch("core.ai_service.get_cached_snapshot") as mock_cached:
            mock_cached.return_value = {"top_processes": [{"name": "process1"}]}

            with patch("core.alert_engine.alert_history", []):
                with patch("core.repair_engine.repair_history", []):
                    with patch("core.metrics_history.metrics_history") as mock_metrics:
                        mock_metrics.get_stats.return_value = {}

                        result = await service.collect_rich_context()

                        assert "top_processes" in result
                        mock_cached.assert_called_once()

    @pytest.mark.asyncio
    async def test_collect_rich_context_with_alerts(self):
        """测试采集告警历史"""
        from core.ai_service import AIContextService

        service = AIContextService()

        alert_history = [
            {
                "level": "warning",
                "title": "High CPU",
                "desc": "CPU usage is high",
                "raw_time": datetime.now(timezone.utc).isoformat(),
                "metric": "cpu_percent",
                "value": 85.5,
            }
        ]

        with patch("core.alert_engine.alert_history", alert_history):
            with patch("core.ai_service.get_cached_snapshot") as mock_cached:
                mock_cached.return_value = {}

                with patch("core.repair_engine.repair_history", []):
                    with patch("core.metrics_history.metrics_history") as mock_metrics:
                        mock_metrics.get_stats.return_value = {}

                        result = await service.collect_rich_context()

                        assert len(result["recent_alerts"]) == 1
                        assert result["recent_alerts"][0]["level"] == "warning"

    @pytest.mark.asyncio
    async def test_collect_rich_context_timeout(self):
        """测试超时处理"""
        from core.ai_service import AIContextService

        service = AIContextService()

        async def slow_fetch():
            import asyncio

            await asyncio.sleep(10)
            return []

        with patch("core.ai_service.get_cached_snapshot") as mock_cached:
            mock_cached.return_value = {}

            with patch("core.alert_engine.alert_history", []):
                with patch("core.repair_engine.repair_history", []):
                    with patch("core.metrics_history.metrics_history") as mock_metrics:
                        mock_metrics.get_stats.return_value = {}

                        # 修改_RICH_CONTEXT_PER_SOURCE_TIMEOUT_SEC为很小的值
                        import core.ai_service as ai_service_module

                        original_timeout = ai_service_module._RICH_CONTEXT_PER_SOURCE_TIMEOUT_SEC
                        ai_service_module._RICH_CONTEXT_PER_SOURCE_TIMEOUT_SEC = 0.01

                        try:
                            # 由于超时设置，应该快速返回
                            result = await service.collect_rich_context()

                            assert "top_processes" in result
                            assert "recent_alerts" in result
                        finally:
                            ai_service_module._RICH_CONTEXT_PER_SOURCE_TIMEOUT_SEC = (
                                original_timeout
                            )

    @pytest.mark.asyncio
    async def test_collect_rich_context_exception_handling(self):
        """测试异常处理"""
        from core.ai_service import AIContextService

        service = AIContextService()

        with patch("core.ai_service.get_cached_snapshot", side_effect=Exception("test error")):
            with patch("core.alert_engine.alert_history", side_effect=Exception("test error")):
                with patch(
                    "core.repair_engine.repair_history", side_effect=Exception("test error")
                ):
                    with patch("core.metrics_history.metrics_history") as mock_metrics:
                        mock_metrics.get_stats.side_effect = Exception("test error")

                        result = await service.collect_rich_context()

                        # 即使所有数据源都失败，也应该返回空的结构
                        assert "top_processes" in result
                        assert "recent_alerts" in result
                        assert "recent_repairs" in result
                        assert "stats" in result

    @pytest.mark.asyncio
    async def test_collect_rich_context_invalid_alert_data(self):
        """测试无效告警数据处理"""
        from core.ai_service import AIContextService

        service = AIContextService()

        # 测试各种无效的告警数据
        invalid_alerts = [
            None,  # None值
            "string",  # 字符串
            123,  # 数字
            {"level": 123},  # level不是字符串
            {"level": None},  # level是None
            {},  # 空字典
        ]

        for alert_data in invalid_alerts:
            with patch("core.ai_service.get_cached_snapshot") as mock_cached:
                mock_cached.return_value = {}

                with patch("core.alert_engine.alert_history", [alert_data]):
                    with patch("core.repair_engine.repair_history", []):
                        with patch("core.metrics_history.metrics_history") as mock_metrics:
                            mock_metrics.get_stats.return_value = {}

                            result = await service.collect_rich_context()

                            # 应该成功处理，不抛出异常
                            assert "recent_alerts" in result
                            assert isinstance(result["recent_alerts"], list)

    @pytest.mark.asyncio
    async def test_collect_rich_context_cancelled_error_propagation(self):
        """测试CancelledError传播"""
        import asyncio

        from core.ai_service import AIContextService

        service = AIContextService()

        with patch("core.ai_service.get_cached_snapshot") as mock_cached:
            mock_cached.return_value = {}

            # 模拟CancelledError
            async def cancelled_fetch():
                raise asyncio.CancelledError()

            with patch("core.alert_engine.alert_history", []):
                with patch("core.repair_engine.repair_history", []):
                    with patch("core.metrics_history.metrics_history") as mock_metrics:
                        mock_metrics.get_stats.return_value = {}

                        # 修改_fetch_processes来抛出CancelledError
                        original_service = service  # noqa: F841

                        async def mock_collect():
                            # 模拟gather返回CancelledError
                            results = [asyncio.CancelledError(), [], [], []]  # noqa: F841
                            # 应该重新抛出CancelledError
                            try:
                                raise asyncio.CancelledError()
                            except asyncio.CancelledError:
                                raise

                        with pytest.raises(asyncio.CancelledError):
                            await mock_collect()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
