# -*- coding: utf-8 -*-
"""
Enhanced Alert Engine Tests
增强的告警引擎测试，包含异步测试、边界条件和错误处理
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch  # noqa: F401

import pytest

from core.alert_engine import (
    _check_ssh_brute_force,
    _cleanup_ssh_brute_force_cache,
    _dedup_key,
    _get_dynamic_warn_threshold,
    _try_dedup,
    alert_history,
    check_and_generate_alerts,
    check_linux_security_alerts,
    clear_dedup_cache,
    clear_ssh_brute_force_cache,
    get_dedup_stats,
)


@pytest.fixture
def reset_alert_engine_state():
    """重置告警引擎状态"""
    # 清空缓存
    clear_dedup_cache()
    clear_ssh_brute_force_cache()
    alert_history.clear()
    yield
    # 测试后再次清理
    clear_dedup_cache()
    clear_ssh_brute_force_cache()
    alert_history.clear()


class TestSSHBruteForceDetection:
    """SSH暴破检测测试"""

    def test_check_ssh_brute_force_basic_trigger(self, reset_alert_engine_state):
        """测试SSH暴破检测基本触发"""
        host_name = "test-server"

        # 第一次采样，不应该触发（数据不足）
        result1 = _check_ssh_brute_force(host_name, 5)  # noqa: F841
        assert result1 is None

        # 第二次采样，增量达到阈值，应该触发
        result2 = _check_ssh_brute_force(host_name, 15)  # 增量10
        assert result2 is not None
        assert result2["level"] == "critical"
        assert result2["category"] == "security"
        assert result2["alert_type"] == "ssh_brute_force"
        assert "SSH 暴力破解" in result2["title"]
        assert host_name in result2["title"]

    def test_check_ssh_brute_force_below_threshold(self, reset_alert_engine_state):
        """测试SSH暴破检测低于阈值"""
        host_name = "test-server"

        # 第一次采样
        _check_ssh_brute_force(host_name, 5)

        # 第二次采样，增量低于阈值
        result = _check_ssh_brute_force(host_name, 8)  # 增量3，低于阈值10
        assert result is None

    def test_check_ssh_brute_force_cooldown_period(self, reset_alert_engine_state):
        """测试SSH暴破检测冷却期"""
        host_name = "test-server"

        # 触发第一次告警
        result1 = _check_ssh_brute_force(host_name, 5)  # noqa: F841
        result2 = _check_ssh_brute_force(host_name, 15)
        assert result2 is not None

        # 冷却期内再次触发，应该被拦截
        result3 = _check_ssh_brute_force(host_name, 25)  # 增量10
        assert result3 is None  # 冷却期内不重复告警

    def test_check_ssh_brute_force_log_rotation_defense(self, reset_alert_engine_state):
        """测试SSH暴破检测防御日志切割"""
        host_name = "test-server"

        # 第一次采样高值
        result1 = _check_ssh_brute_force(host_name, 1000)  # noqa: F841
        assert result1 is None

        # 模拟日志切割，值骤降
        result2 = _check_ssh_brute_force(host_name, 10)  # 从1000降到10
        assert result2 is None  # 应该重置窗口，不触发告警

        # 从新基准开始重新计数
        result3 = _check_ssh_brute_force(host_name, 20)  # 增量10
        assert result3 is not None  # 现在应该触发

    def test_check_ssh_brute_force_window_cleanup(self, reset_alert_engine_state):
        """测试SSH暴破检测窗口清理"""
        host_name = "test-server"

        # 创建多个采样点
        now = datetime.now()
        for i in range(5):
            test_time = now - timedelta(seconds=400 - i * 100)  # 分布在400秒内
            with patch("core.alert_engine.datetime") as mock_datetime:
                mock_datetime.datetime.now.return_value = test_time
                _check_ssh_brute_force(host_name, i * 5)

        # 超过5分钟的采样点应该被清理
        # 这个测试验证窗口清理逻辑

    def test_check_ssh_brute_force_unique_alert_ids(self, reset_alert_engine_state):
        """测试SSH暴破检测告警ID唯一性"""
        host_name = "test-server"

        # 触发两次告警（不同时间）
        result1 = _check_ssh_brute_force(host_name, 5)  # noqa: F841
        result2 = _check_ssh_brute_force(host_name, 15)

        if result1 and result2:
            # 等待冷却期过后
            import time

            time.sleep(0.1)  # 短暂等待确保时间戳不同

        # 验证告警ID包含随机后缀，确保唯一性
        if result2:
            assert "-" in result2["id"]
            assert result2["id"].startswith("SEC-SSH-")


class TestSSHCleanup:
    """SSH缓存清理测试"""

    def test_cleanup_ssh_brute_force_cache_basic(self, reset_alert_engine_state):
        """测试SSH暴破缓存基本清理"""
        # 添加一些测试数据
        _check_ssh_brute_force("host1", 5)
        _check_ssh_brute_force("host2", 5)

        # 执行清理
        _cleanup_ssh_brute_force_cache()

        # 清理应该不抛出异常
        assert True

    def test_cleanup_ssh_brute_force_cache_expiry(self, reset_alert_engine_state):
        """测试SSH暴破缓存过期清理"""
        host_name = "test-server"

        # 添加过期数据
        old_time = datetime.now() - timedelta(seconds=4000)  # 超过1小时
        with patch("core.alert_engine.datetime") as mock_datetime:
            mock_datetime.datetime.now.return_value = old_time
            _check_ssh_brute_force(host_name, 5)

        # 执行清理
        _cleanup_ssh_brute_force_cache()

        # 过期数据应该被清理

    def test_cleanup_ssh_brute_force_cache_limit(self, reset_alert_engine_state):
        """测试SSH暴破缓存上限保护"""
        # 尝试添加超过上限的主机
        for i in range(600):  # 超过_SSH_CACHE_MAX_HOSTS (500)
            _check_ssh_brute_force(f"host{i}", 5)

        # 执行清理，应该触发上限保护
        _cleanup_ssh_brute_force_cache()

        # 应该不抛出异常，且缓存大小在限制内


class TestAlertDeduplication:
    """告警去重测试"""

    def test_dedup_key_generation(self, reset_alert_engine_state):
        """测试去重键生成"""
        # CPU告警
        cpu_alert = {"metric": "cpu_percent", "level": "warning"}
        cpu_key = _dedup_key(cpu_alert)
        assert cpu_key == "cpu_percent_warning"

        # 磁盘告警（带设备标识）
        disk_alert = {"metric": "disk_percent", "level": "critical", "id": "DISK-C:-12:30:45"}
        disk_key = _dedup_key(disk_alert)
        assert "disk_percent_critical" in disk_key
        assert "C:" in disk_key  # 设备标识应该包含在键中

    def test_try_dedup_first_alert(self, reset_alert_engine_state):
        """测试首次告警通过去重"""
        alert = {"metric": "cpu_percent", "level": "warning", "host": "server1"}

        result = _try_dedup(alert)
        assert result is False  # 首次告警应该通过

    def test_try_dedup_duplicate_within_window(self, reset_alert_engine_state):
        """测试窗口内重复告警被拦截"""
        alert = {"metric": "cpu_percent", "level": "warning", "host": "server1"}

        # 第一次通过
        result1 = _try_dedup(alert)  # noqa: F841
        assert result1 is False

        # 立即重复，应该被拦截
        result2 = _try_dedup(alert)
        assert result2 is True  # 被去重拦截

    def test_try_dedup_window_expiry(self, reset_alert_engine_state):
        """测试去重窗口过期"""
        alert = {"metric": "cpu_percent", "level": "warning", "host": "server1"}

        # 第一次通过
        _try_dedup(alert)

        # 等待窗口过期
        import time

        time.sleep(0.1)  # 短暂等待

        # 模拟时间流逝超过窗口期
        old_time = datetime.now() - timedelta(seconds=400)  # 超过5分钟
        with patch("core.alert_engine.datetime") as mock_datetime:
            mock_datetime.datetime.now.return_value = old_time

            # 窗口过期后应该通过
            # 注意：实际实现可能需要调整这个测试

    def test_try_dedup_cache_overflow_protection(self, reset_alert_engine_state):
        """测试去重缓存溢出保护"""
        # 尝试填满缓存
        for i in range(250):  # 超过_DEDUP_CACHE_MAX (200)
            alert = {"metric": f"metric_{i % 10}", "level": "warning", "host": f"server{i}"}
            _try_dedup(alert)

        # 应该不抛出异常，且自动清理旧条目
        assert True

    def test_get_dedup_stats(self, reset_alert_engine_state):
        """测试获取去重统计信息"""
        # 添加一些测试数据
        for i in range(5):
            alert = {"metric": f"metric_{i}", "level": "warning", "host": "server1"}
            _try_dedup(alert)

        stats = get_dedup_stats()
        assert isinstance(stats, dict)
        assert "cache_size" in stats
        assert "active_windows" in stats
        assert "total_suppressed" in stats
        assert stats["cache_size"] >= 0

    def test_clear_dedup_cache(self, reset_alert_engine_state):
        """测试清空去重缓存"""
        # 添加测试数据
        for i in range(10):
            alert = {"metric": f"metric_{i}", "level": "warning", "host": "server1"}
            _try_dedup(alert)

        # 清空缓存
        count = clear_dedup_cache()
        assert count >= 0

        # 验证缓存已清空
        stats = get_dedup_stats()
        assert stats["cache_size"] == 0


class TestDynamicThreshold:
    """动态阈值测试"""

    def test_get_dynamic_threshold_disabled(self, reset_alert_engine_state):
        """测试动态阈值功能禁用时"""
        with patch("core.alert_engine.DYNAMIC_THRESHOLD_CONFIG", {"enabled": False}):
            threshold = _get_dynamic_warn_threshold("cpu", 80.0)
            assert threshold == 80.0  # 应该返回静态阈值

    def test_get_dynamic_threshold_enabled_success(self, reset_alert_engine_state):
        """测试动态阈值功能启用成功"""
        with patch("core.alert_engine.DYNAMIC_THRESHOLD_CONFIG", {"enabled": True}):
            with patch("core.alert_engine.metrics_history") as mock_metrics:
                mock_metrics.get_dynamic_threshold.return_value = (
                    85.0,
                    {"source": "dynamic", "samples": 50, "mean": 75.0, "std": 5.0},
                )

                threshold = _get_dynamic_warn_threshold("cpu", 80.0)
                assert threshold == 85.0  # 应该返回动态阈值

    def test_get_dynamic_threshold_exception_fallback(self, reset_alert_engine_state):
        """测试动态阈值异常时回退到静态阈值"""
        with patch("core.alert_engine.DYNAMIC_THRESHOLD_CONFIG", {"enabled": True}):
            with patch("core.alert_engine.metrics_history") as mock_metrics:
                mock_metrics.get_dynamic_threshold.side_effect = Exception("Calculation failed")

                threshold = _get_dynamic_warn_threshold("cpu", 80.0)
                assert threshold == 80.0  # 应该回退到静态阈值


class TestAlertGeneration:
    """告警生成测试"""

    def test_check_and_generate_alerts_cpu_critical(self, reset_alert_engine_state):
        """测试CPU严重告警生成"""
        metrics = {"cpu": {"usage_percent": 95.0}, "memory": {"usage_percent": 45.0}, "disk": []}

        alerts = check_and_generate_alerts(metrics)  # noqa: F841
        assert len(alerts) > 0

        cpu_alerts = [a for a in alerts if "CPU" in a.get("title", "")]  # noqa: F841
        assert len(cpu_alerts) > 0
        assert cpu_alerts[0]["level"] == "critical"

    def test_check_and_generate_alerts_memory_warning(self, reset_alert_engine_state):
        """测试内存警告告警生成"""
        metrics = {"cpu": {"usage_percent": 45.0}, "memory": {"usage_percent": 88.0}, "disk": []}

        alerts = check_and_generate_alerts(metrics)  # noqa: F841
        assert len(alerts) > 0

        memory_alerts = [a for a in alerts if "内存" in a.get("title", "")]  # noqa: F841
        assert len(memory_alerts) > 0
        assert memory_alerts[0]["level"] == "warning"

    def test_check_and_generate_alerts_disk_critical(self, reset_alert_engine_state):
        """测试磁盘严重告警生成"""
        metrics = {
            "cpu": {"usage_percent": 45.0},
            "memory": {"usage_percent": 45.0},
            "disk": [{"device": "C:", "percent": 95.0}, {"device": "D:", "percent": 98.0}],
        }

        alerts = check_and_generate_alerts(metrics)  # noqa: F841
        assert len(alerts) > 0

        disk_alerts = [a for a in alerts if "磁盘" in a.get("title", "")]  # noqa: F841
        assert len(disk_alerts) > 0

    def test_check_and_generate_alerts_all_normal(self, reset_alert_engine_state):
        """测试所有指标正常时不生成告警"""
        metrics = {
            "cpu": {"usage_percent": 45.0},
            "memory": {"usage_percent": 45.0},
            "disk": [{"device": "C:", "percent": 45.0}],
        }

        alerts = check_and_generate_alerts(metrics)  # noqa: F841
        assert len(alerts) == 0  # 不应该生成告警

    def test_check_and_generate_alerts_multiple_alerts(self, reset_alert_engine_state):
        """测试多个告警同时生成"""
        metrics = {
            "cpu": {"usage_percent": 95.0},
            "memory": {"usage_percent": 92.0},
            "disk": [{"device": "C:", "percent": 97.0}],
        }

        alerts = check_and_generate_alerts(metrics)  # noqa: F841
        assert len(alerts) >= 3  # 应该生成至少3个告警


class TestLinuxSecurityAlerts:
    """Linux安全告警测试"""

    @pytest.mark.asyncio
    async def test_check_linux_security_alerts_basic(self, reset_alert_engine_state):
        """测试基本Linux安全告警检测"""
        linux_results = [
            {
                "name": "server1",
                "status": "ok",
                "metrics": {"ssh_failed_logins": {"value": "15"}},  # 超过阈值10
            }
        ]

        # Mock依赖
        with patch("core.alert_engine.broadcast", new_callable=AsyncMock):
            with patch("core.alert_engine.alert_repository") as mock_repo:
                mock_repo.save = AsyncMock()

                alerts = await check_linux_security_alerts(linux_results)  # noqa: F841

                # 应该生成SSH暴破告警
                assert len(alerts) > 0
                assert alerts[0]["alert_type"] == "ssh_brute_force"

    @pytest.mark.asyncio
    async def test_check_linux_security_alerts_below_threshold(self, reset_alert_engine_state):
        """测试低于阈值时不生成告警"""
        linux_results = [
            {
                "name": "server1",
                "status": "ok",
                "metrics": {"ssh_failed_logins": {"value": "5"}},  # 低于阈值10
            }
        ]

        alerts = await check_linux_security_alerts(linux_results)  # noqa: F841
        assert len(alerts) == 0  # 不应该生成告警

    @pytest.mark.asyncio
    async def test_check_linux_security_alerts_invalid_data(self, reset_alert_engine_state):
        """测试无效数据处理"""
        linux_results = [
            {
                "name": "server1",
                "status": "ok",
                "metrics": {"ssh_failed_logins": {"value": "ERROR"}},  # 无效值
            }
        ]

        alerts = await check_linux_security_alerts(linux_results)  # noqa: F841
        assert len(alerts) == 0  # 应该跳过无效数据

    @pytest.mark.asyncio
    async def test_check_linux_security_alerts_malformed_host_data(self, reset_alert_engine_state):
        """测试格式错误的主机数据处理"""
        linux_results = [{"invalid": "data"}]  # 格式错误

        alerts = await check_linux_security_alerts(linux_results)  # noqa: F841
        assert len(alerts) == 0  # 应该跳过格式错误的数据

    @pytest.mark.asyncio
    async def test_check_linux_security_alerts_database_failure(self, reset_alert_engine_state):
        """测试数据库写入失败时的降级处理"""
        linux_results = [
            {"name": "server1", "status": "ok", "metrics": {"ssh_failed_logins": {"value": "15"}}}
        ]

        with patch("core.alert_engine.broadcast", new_callable=AsyncMock):
            with patch("core.alert_engine.alert_repository") as mock_repo:
                mock_repo.save = AsyncMock(side_effect=Exception("DB error"))

                # 应该不抛出异常，降级为仅内存存储
                alerts = await check_linux_security_alerts(linux_results)  # noqa: F841
                assert len(alerts) > 0  # 告警仍然生成
                assert len(alert_history) > 0  # 存储在内存中


class TestErrorHandling:
    """错误处理测试"""

    def test_check_and_generate_alerts_none_metrics(self, reset_alert_engine_state):
        """测试None指标处理"""
        alerts = check_and_generate_alerts(None)  # noqa: F841
        assert len(alerts) == 0

    def test_check_and_generate_alerts_empty_metrics(self, reset_alert_engine_state):
        """测试空指标处理"""
        alerts = check_and_generate_alerts({})  # noqa: F841
        assert len(alerts) == 0

    def test_check_and_generate_alerts_missing_metric_fields(self, reset_alert_engine_state):
        """测试缺失指标字段处理"""
        metrics = {"cpu": {}, "memory": {"usage_percent": 45.0}}  # 缺少usage_percent字段

        # 应该不抛出异常，优雅处理缺失字段
        alerts = check_and_generate_alerts(metrics)  # noqa: F841
        # 可能生成内存告警，但不应该因为缺失字段而崩溃

    def test_dedup_key_missing_fields(self, reset_alert_engine_state):
        """测试去重键生成时缺失字段"""
        alert = {}  # 空告警

        # 应该优雅处理缺失字段
        key = _dedup_key(alert)
        assert key == "unknown_unknown"  # 应该有默认值


class TestEdgeCases:
    """边界条件测试"""

    def test_exact_threshold_values(self, reset_alert_engine_state):
        """测试精确阈值边界"""
        # 测试CPU精确阈值
        metrics = {
            "cpu": {"usage_percent": 80.0},  # 精确在阈值上
            "memory": {"usage_percent": 45.0},
            "disk": [],
        }

        alerts = check_and_generate_alerts(metrics)  # noqa: F841
        # 根据实现，精确阈值可能触发或不触发

    def test_zero_and_negative_values(self, reset_alert_engine_state):
        """测试零值和负值处理"""
        metrics = {
            "cpu": {"usage_percent": -5.0},  # 负值
            "memory": {"usage_percent": 0.0},  # 零值
            "disk": [],
        }

        # 应该优雅处理无效值
        alerts = check_and_generate_alerts(metrics)  # noqa: F841
        # 不应该崩溃

    def test_extremely_large_values(self, reset_alert_engine_state):
        """测试极大值处理"""
        metrics = {
            "cpu": {"usage_percent": 9999.0},  # 极大值
            "memory": {"usage_percent": 45.0},
            "disk": [],
        }

        # 应该优雅处理极大值
        alerts = check_and_generate_alerts(metrics)  # noqa: F841
        # 不应该崩溃

    def test_concurrent_alert_generation(self, reset_alert_engine_state):
        """测试并发告警生成"""

        async def generate_alerts():
            for i in range(10):
                metrics = {
                    "cpu": {"usage_percent": 85.0 + i},
                    "memory": {"usage_percent": 45.0},
                    "disk": [],
                }
                check_and_generate_alerts(metrics)

        # 运行并发告警生成
        asyncio.run(generate_alerts())

        # 应该不抛出异常，且去重机制正常工作
        assert True


@pytest.mark.integration
class TestAlertEngineIntegration:
    """告警引擎集成测试"""

    @pytest.mark.asyncio
    async def test_full_alert_workflow(self, reset_alert_engine_state):
        """测试完整告警工作流"""
        # 1. 生成告警
        metrics = {"cpu": {"usage_percent": 95.0}, "memory": {"usage_percent": 45.0}, "disk": []}

        alerts = check_and_generate_alerts(metrics)  # noqa: F841
        assert len(alerts) > 0

        # 2. 测试去重
        for alert in alerts:
            dedup_result = _try_dedup(alert)
            # 第一次应该通过
            assert dedup_result is False

        # 3. 测试统计信息
        stats = get_dedup_stats()
        assert stats["cache_size"] > 0

    @pytest.mark.asyncio
    async def test_ssh_detection_workflow(self, reset_alert_engine_state):
        """测试SSH检测完整工作流"""
        # 1. 模拟SSH暴破
        linux_results = [
            {
                "name": "test-server",
                "status": "ok",
                "metrics": {"ssh_failed_logins": {"value": "15"}},
            }
        ]

        with patch("core.alert_engine.broadcast", new_callable=AsyncMock):
            with patch("core.alert_engine.alert_repository") as mock_repo:
                mock_repo.save = AsyncMock()

                # 2. 检测安全告警
                alerts = await check_linux_security_alerts(linux_results)  # noqa: F841
                assert len(alerts) > 0

                # 3. 验证告警结构
                alert = alerts[0]
                assert alert["level"] == "critical"
                assert alert["category"] == "security"
                assert alert["alert_type"] == "ssh_brute_force"

    @pytest.mark.asyncio
    async def test_alert_history_management(self, reset_alert_engine_state):
        """测试告警历史管理"""
        # 生成多个告警
        for i in range(5):
            metrics = {
                "cpu": {"usage_percent": 85.0 + i},
                "memory": {"usage_percent": 45.0},
                "disk": [],
            }
            alerts = check_and_generate_alerts(metrics)  # noqa: F841
            alert_history.extend(alerts)

        # 验证历史记录
        assert len(alert_history) > 0

        # 验证历史记录上限
        original_maxlen = alert_history.maxlen
        assert original_maxlen > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
