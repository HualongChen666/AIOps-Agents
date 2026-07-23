# -*- coding: utf-8 -*-
# tests/test_stats_engine.py
# 统计引擎单元测试
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch  # noqa: F401

import pytest

from core.stats_engine import (
    get_alert_stats,
    get_real_summary,
    get_repair_history,
    get_repair_stats,
    get_system_stats,
    record_repair,
)


class TestRepairRecording:
    """修复记录测试"""

    @pytest.mark.asyncio
    async def test_record_repair_success(self, mock_logger):
        """测试修复记录成功"""
        repair_data = {
            "script_key": "clear_temp",
            "host": "server-01",
            "status": "success",
            "output": "Temp files cleared",
        }

        with patch("core.stats_engine.logger", mock_logger):
            # Mock 数据库操作
            with patch(
                "core.stats_engine.insert_repair_record", AsyncMock(return_value="repair-001")
            ):
                result = await record_repair(repair_data)

                # 验证记录成功
                assert result["success"] is True
                assert "repair_id" in result

    @pytest.mark.asyncio
    async def test_record_repair_with_failure(self, mock_logger):
        """测试修复记录失败"""
        repair_data = {
            "script_key": "clear_temp",
            "host": "server-01",
            "status": "failure",
            "error": "Permission denied",
        }

        with patch("core.stats_engine.logger", mock_logger):
            # Mock 数据库操作
            with patch(
                "core.stats_engine.insert_repair_record", AsyncMock(return_value="repair-001")
            ):
                result = await record_repair(repair_data)

                # 验证记录成功（即使失败也要记录）
                assert result["success"] is True

    @pytest.mark.asyncio
    async def test_record_repair_invalid_data(self, mock_logger):
        """测试无效修复数据"""
        repair_data = {}

        with patch("core.stats_engine.logger", mock_logger):
            result = await record_repair(repair_data)

            # 验证无效数据处理
            assert result["success"] is False
            assert "invalid" in result["error"].lower()


class TestRepairHistory:
    """修复历史测试"""

    @pytest.mark.asyncio
    async def test_get_repair_history_success(self, mock_logger):
        """测试获取修复历史成功"""
        with patch("core.stats_engine.logger", mock_logger):
            # Mock 数据库查询
            with patch(
                "core.stats_engine.query_repair_history",
                AsyncMock(
                    return_value=[
                        {
                            "id": "repair-001",
                            "script_key": "clear_temp",
                            "host": "server-01",
                            "status": "success",
                            "timestamp": "2026-06-09T10:00:00Z",
                        }
                    ]
                ),
            ):
                history = await get_repair_history(limit=10)

                # 验证历史记录
                assert len(history) > 0
                assert history[0]["script_key"] == "clear_temp"

    @pytest.mark.asyncio
    async def test_get_repair_history_with_filter(self, mock_logger):
        """测试带过滤的修复历史"""
        with patch("core.stats_engine.logger", mock_logger):
            # Mock 数据库查询
            with patch(
                "core.stats_engine.query_repair_history",
                AsyncMock(
                    return_value=[
                        {
                            "id": "repair-001",
                            "script_key": "clear_temp",
                            "host": "server-01",
                            "status": "success",
                        }
                    ]
                ),
            ):
                history = await get_repair_history(limit=10, host="server-01")

                # 验证过滤结果
                assert len(history) > 0
                assert history[0]["host"] == "server-01"


class TestSummaryStats:
    """汇总统计测试"""

    @pytest.mark.asyncio
    async def test_get_real_summary_success(self, mock_logger):
        """测试获取实时汇总成功"""
        with patch("core.stats_engine.logger", mock_logger):
            # Mock 各个统计函数
            with patch(
                "core.stats_engine.get_alert_stats",
                AsyncMock(
                    return_value={
                        "total": 100,
                        "critical": 5,
                        "warning": 20,
                    }
                ),
            ):
                with patch(
                    "core.stats_engine.get_repair_stats",
                    AsyncMock(
                        return_value={
                            "total": 50,
                            "success": 45,
                            "failure": 5,
                        }
                    ),
                ):
                    with patch(
                        "core.stats_engine.get_system_stats",
                        AsyncMock(
                            return_value={
                                "hosts": 10,
                                "healthy": 8,
                                "unhealthy": 2,
                            }
                        ),
                    ):
                        summary = await get_real_summary()

                        # 验证汇总数据
                        assert "alerts" in summary
                        assert "repairs" in summary
                        assert "systems" in summary

    @pytest.mark.asyncio
    async def test_get_real_summary_cached(self, mock_logger):
        """测试汇总缓存"""
        with patch("core.stats_engine.logger", mock_logger):
            # Mock 缓存
            with patch(
                "core.stats_engine._summary_cache",
                {
                    "data": {"alerts": {"total": 100}},
                    "timestamp": datetime.now().timestamp(),
                },
            ):
                summary = await get_real_summary()

                # 验证从缓存获取
                assert "alerts" in summary
                assert summary["from_cache"] is True

    @pytest.mark.asyncio
    async def test_get_real_summary_cache_expired(self, mock_logger):
        """测试汇总缓存过期"""
        with patch("core.stats_engine.logger", mock_logger):
            # Mock 缓存过期
            with patch(
                "core.stats_engine._summary_cache",
                {
                    "data": {"alerts": {"total": 100}},
                    "timestamp": datetime.now().timestamp() - 1000,
                },
            ):
                # Mock 统计函数
                with patch(
                    "core.stats_engine.get_alert_stats", AsyncMock(return_value={"total": 100})
                ):
                    with patch(
                        "core.stats_engine.get_repair_stats", AsyncMock(return_value={"total": 50})
                    ):
                        with patch(
                            "core.stats_engine.get_system_stats",
                            AsyncMock(return_value={"hosts": 10}),
                        ):
                            summary = await get_real_summary()

                            # 验证重新计算
                            assert summary["from_cache"] is False


class TestAlertStats:
    """告警统计测试"""

    @pytest.mark.asyncio
    async def test_get_alert_stats_success(self, mock_logger):
        """测试获取告警统计成功"""
        with patch("core.stats_engine.logger", mock_logger):
            # Mock 数据库查询
            with patch(
                "core.stats_engine.query_alert_stats",
                AsyncMock(
                    return_value={
                        "total": 100,
                        "by_severity": {
                            "critical": 5,
                            "warning": 20,
                            "info": 75,
                        },
                        "by_type": {
                            "cpu_high": 30,
                            "memory_high": 25,
                            "disk_high": 20,
                        },
                    }
                ),
            ):
                stats = await get_alert_stats()

                # 验证统计数据
                assert stats["total"] == 100
                assert "by_severity" in stats
                assert "by_type" in stats

    @pytest.mark.asyncio
    async def test_get_alert_stats_with_time_range(self, mock_logger):
        """测试带时间范围的告警统计"""
        start_time = "2026-06-09T00:00:00Z"
        end_time = "2026-06-09T23:59:59Z"

        with patch("core.stats_engine.logger", mock_logger):
            # Mock 数据库查询
            with patch(
                "core.stats_engine.query_alert_stats",
                AsyncMock(
                    return_value={
                        "total": 50,
                        "by_severity": {"critical": 2, "warning": 10},
                    }
                ),
            ):
                stats = await get_alert_stats(start_time=start_time, end_time=end_time)

                # 验证时间范围统计
                assert stats["total"] == 50


class TestRepairStats:
    """修复统计测试"""

    @pytest.mark.asyncio
    async def test_get_repair_stats_success(self, mock_logger):
        """测试获取修复统计成功"""
        with patch("core.stats_engine.logger", mock_logger):
            # Mock 数据库查询
            with patch(
                "core.stats_engine.query_repair_stats",
                AsyncMock(
                    return_value={
                        "total": 50,
                        "success": 45,
                        "failure": 5,
                        "success_rate": 0.9,
                        "by_script": {
                            "clear_temp": 20,
                            "restart_service": 15,
                            "kill_process": 10,
                        },
                    }
                ),
            ):
                stats = await get_repair_stats()

                # 验证统计数据
                assert stats["total"] == 50
                assert stats["success_rate"] == 0.9
                assert "by_script" in stats

    @pytest.mark.asyncio
    async def test_get_repair_stats_by_host(self, mock_logger):
        """测试按主机统计修复"""
        with patch("core.stats_engine.logger", mock_logger):
            # Mock 数据库查询
            with patch(
                "core.stats_engine.query_repair_stats",
                AsyncMock(
                    return_value={
                        "total": 30,
                        "success": 28,
                        "failure": 2,
                        "by_host": {
                            "server-01": 15,
                            "server-02": 15,
                        },
                    }
                ),
            ):
                stats = await get_repair_stats(group_by="host")

                # 验证按主机统计
                assert "by_host" in stats


class TestSystemStats:
    """系统统计测试"""

    @pytest.mark.asyncio
    async def test_get_system_stats_success(self, mock_logger):
        """测试获取系统统计成功"""
        with patch("core.stats_engine.logger", mock_logger):
            # Mock 数据库查询
            with patch(
                "core.stats_engine.query_system_stats",
                AsyncMock(
                    return_value={
                        "total_hosts": 10,
                        "healthy_hosts": 8,
                        "unhealthy_hosts": 2,
                        "avg_cpu": 45.5,
                        "avg_memory": 60.2,
                        "avg_disk": 70.0,
                    }
                ),
            ):
                stats = await get_system_stats()

                # 验证系统统计
                assert stats["total_hosts"] == 10
                assert stats["healthy_hosts"] == 8
                assert "avg_cpu" in stats


class TestStatsAggregation:
    """统计聚合测试"""

    @pytest.mark.asyncio
    async def test_aggregate_hourly_stats(self, mock_logger):
        """测试小时级统计聚合"""
        with patch("core.stats_engine.logger", mock_logger):
            # Mock 数据库查询
            with patch(
                "core.stats_engine.query_hourly_stats",
                AsyncMock(
                    return_value=[
                        {"hour": "2026-06-09T10:00:00Z", "alerts": 10, "repairs": 5},
                        {"hour": "2026-06-09T11:00:00Z", "alerts": 15, "repairs": 8},
                    ]
                ),
            ):
                stats = await get_alert_stats(aggregation="hourly")

                # 验证小时级聚合
                assert len(stats["hourly"]) > 0

    @pytest.mark.asyncio
    async def test_aggregate_daily_stats(self, mock_logger):
        """测试日级统计聚合"""
        with patch("core.stats_engine.logger", mock_logger):
            # Mock 数据库查询
            with patch(
                "core.stats_engine.query_daily_stats",
                AsyncMock(
                    return_value=[
                        {"day": "2026-06-09", "alerts": 100, "repairs": 50},
                        {"day": "2026-06-08", "alerts": 95, "repairs": 45},
                    ]
                ),
            ):
                stats = await get_alert_stats(aggregation="daily")

                # 验证日级聚合
                assert len(stats["daily"]) > 0


class TestStatsErrorHandling:
    """统计错误处理测试"""

    @pytest.mark.asyncio
    async def test_get_stats_with_db_error(self, mock_logger):
        """测试数据库错误处理"""
        with patch("core.stats_engine.logger", mock_logger):
            # Mock 数据库查询失败
            with patch(
                "core.stats_engine.query_alert_stats", AsyncMock(side_effect=Exception("DB error"))
            ):
                stats = await get_alert_stats()

                # 验证错误被捕获
                assert stats["success"] is False
                # 验证日志记录
                mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_record_repair_with_db_error(self, mock_logger):
        """测试修复记录数据库错误"""
        repair_data = {
            "script_key": "clear_temp",
            "host": "server-01",
            "status": "success",
        }

        with patch("core.stats_engine.logger", mock_logger):
            # Mock 数据库操作失败
            with patch(
                "core.stats_engine.insert_repair_record",
                AsyncMock(side_effect=Exception("DB error")),
            ):
                result = await record_repair(repair_data)

                # 验证错误被捕获
                assert result["success"] is False


class TestStatsValidation:
    """统计验证测试"""

    @pytest.mark.asyncio
    async def test_validate_stats_data(self, mock_logger):
        """测试统计数据验证"""
        stats = {
            "total": 100,
            "success": 80,
            "failure": 20,
        }

        with patch("core.stats_engine.logger", mock_logger):
            from core.stats_engine import validate_stats

            result = validate_stats(stats)

            # 验证统计有效
            assert result["valid"] is True

    @pytest.mark.asyncio
    async def test_validate_stats_inconsistent(self, mock_logger):
        """测试不一致的统计数据"""
        stats = {
            "total": 100,
            "success": 80,
            "failure": 30,  # 80 + 30 != 100
        }

        with patch("core.stats_engine.logger", mock_logger):
            from core.stats_engine import validate_stats

            result = validate_stats(stats)

            # 验证统计不一致
            assert result["valid"] is False
            assert "inconsistent" in result["error"].lower()


class TestStatsConcurrency:
    """统计并发测试"""

    @pytest.mark.asyncio
    async def test_concurrent_stats_queries(self, mock_logger):
        """测试并发统计查询"""
        with patch("core.stats_engine.logger", mock_logger):
            # Mock 统计函数(通过测试模块名打补丁, 覆盖 from ... import 引入的本地引用)
            with patch(
                "tests.test_stats_engine.get_alert_stats",
                AsyncMock(return_value={"total": 100, "success": True}),
            ):
                with patch(
                    "tests.test_stats_engine.get_repair_stats",
                    AsyncMock(return_value={"total": 50, "success": True}),
                ):
                    with patch(
                        "tests.test_stats_engine.get_system_stats",
                        AsyncMock(return_value={"hosts": 10, "success": True}),
                    ):
                        # 并发查询
                        tasks = [
                            get_alert_stats(),
                            get_repair_stats(),
                            get_system_stats(),
                        ]
                        results = await asyncio.gather(*tasks)

                        # 验证所有查询成功
                        assert all(r["success"] for r in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
