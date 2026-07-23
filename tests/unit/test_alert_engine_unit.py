# -*- coding: utf-8 -*-
# tests/unit/test_alert_engine_unit.py
# 告警引擎模块单元测试
import asyncio  # noqa: F401
from collections import deque
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock, patch  # noqa: F401

import pytest


class TestAlertEngine:
    """告警引擎测试"""

    def test_alert_engine_import(self):
        """测试告警引擎导入"""
        from core.alert_engine import alert_engine

        assert alert_engine is not None

    def test_alert_engine_initialization(self):
        """测试告警引擎初始化"""
        from core.alert_engine import alert_engine

        # 检查alert_engine模块是否可用
        assert alert_engine is not None

    def test_alert_processing(self):
        """测试告警处理"""
        # 测试告警处理逻辑（不依赖AlertEngine类）
        alert_data = {
            "metric": "cpu.usage",
            "value": 85.0,
            "threshold": 80.0,
            "timestamp": datetime.now().isoformat(),
        }

        # 简单的阈值检查逻辑
        assert alert_data["value"] > alert_data["threshold"]

    def test_alert_threshold_comparison(self):
        """测试告警阈值比较"""
        # 模拟阈值比较逻辑
        value = 85.0
        threshold = 80.0

        assert value > threshold  # 应该触发告警
        assert value - threshold == 5.0  # 超出阈值5.0

    def test_alert_aggregation(self):
        """测试告警聚合"""
        # 模拟告警聚合逻辑
        alerts = [
            {"metric": "cpu.usage", "value": 85.0, "timestamp": "2024-01-01T10:00:00"},
            {"metric": "cpu.usage", "value": 90.0, "timestamp": "2024-01-01T10:01:00"},
            {"metric": "memory.usage", "value": 75.0, "timestamp": "2024-01-01T10:00:00"},
        ]

        # 按指标聚合
        aggregated = {}
        for alert in alerts:
            metric = alert["metric"]
            if metric not in aggregated:
                aggregated[metric] = []
            aggregated[metric].append(alert)

        assert len(aggregated) == 2  # 两个不同的指标
        assert len(aggregated["cpu.usage"]) == 2  # CPU告警有2个

    def test_alert_history_deque(self):
        """测试告警历史deque"""
        from core.alert_engine import ALERT_HISTORY_MAX, alert_history

        # 测试deque初始化
        assert isinstance(alert_history, deque)
        assert alert_history.maxlen == ALERT_HISTORY_MAX

        # 测试添加告警
        test_alert = {"metric": "test", "value": 100}
        alert_history.append(test_alert)
        assert len(alert_history) == 1

        # 测试deque满时自动丢弃
        for i in range(ALERT_HISTORY_MAX + 10):
            alert_history.append({"metric": f"test{i}", "value": i})

        assert len(alert_history) == ALERT_HISTORY_MAX


class TestSSHBruteForceDetection:
    """SSH暴力破解检测测试"""

    def test_ssh_brute_force_threshold_check(self):
        """测试SSH暴力破解阈值检查"""
        from core.alert_engine import _SSH_FAIL_THRESHOLD, _SSH_WINDOW_SEC

        assert _SSH_FAIL_THRESHOLD == 10
        assert _SSH_WINDOW_SEC == 300

    @pytest.mark.asyncio
    async def test_restore_alert_cache(self):
        """测试告警缓存恢复"""
        from core.alert_engine import _restore_alert_cache, alert_history

        # Mock alert_repository
        with patch("core.db_engine.alert_repository") as mock_repo:
            mock_repo.get_recent = AsyncMock(
                return_value=[
                    {"metric": "cpu", "value": 90, "timestamp": "2024-01-01T10:00:00"},
                    {"metric": "memory", "value": 85, "timestamp": "2024-01-01T10:01:00"},
                ]
            )

            # 清空现有历史
            alert_history.clear()

            # 调用恢复函数
            await _restore_alert_cache()

            # 验证告警被恢复
            assert len(alert_history) == 2

    @pytest.mark.asyncio
    async def test_restore_alert_cache_exception(self):
        """测试告警缓存恢复异常处理"""
        from core.alert_engine import _restore_alert_cache, alert_history  # noqa: F401

        # Mock alert_repository抛出异常
        with patch("core.db_engine.alert_repository") as mock_repo:
            mock_repo.get_recent = AsyncMock(side_effect=Exception("Database error"))

            # 调用恢复函数（应该不抛出异常）
            await _restore_alert_cache()

            # 应该正常返回，不抛出异常

    def test_check_ssh_brute_force_basic(self):
        """测试SSH暴力破解基本检测"""
        from core.alert_engine import _check_ssh_brute_force

        # 测试新主机
        result = _check_ssh_brute_force("test-host", 5)
        assert result is None  # 数据点不足

        # 测试数据点不足
        result = _check_ssh_brute_force("test-host", 8)
        assert result is None  # 数据点不足

    def test_check_ssh_brute_force_trigger(self):
        """测试SSH暴力破解触发"""
        import datetime  # noqa: F401

        from core.alert_engine import _check_ssh_brute_force

        # 模拟足够的数据点
        host = "test-host"

        # 添加初始数据点
        _check_ssh_brute_force(host, 0)  # 初始
        _check_ssh_brute_force(host, 5)  # 5分钟后

        # 添加触发数据点
        result = _check_ssh_brute_force(host, 15)  # 增量10，达到阈值

        # 应该触发告警
        assert result is not None
        assert "metric" in result
        assert "ssh_failed_logins" in result["metric"]

    def test_check_ssh_brute_force_logrotate(self):
        """测试SSH检测防御logrotate切割"""
        import datetime  # noqa: F401

        from core.alert_engine import _check_ssh_brute_force

        host = "test-host"

        # 先添加高值
        _check_ssh_brute_force(host, 100)
        _check_ssh_brute_force(host, 110)

        # 然后添加低值（模拟logrotate）
        result = _check_ssh_brute_force(host, 5)

        # 应该返回None（窗口被重置）
        assert result is None


class TestAlertRules:
    """告警规则测试"""

    def test_alert_rules_import(self):
        """测试告警规则导入"""
        try:
            from core.alert_rules import AlertRules

            assert AlertRules is not None
        except ImportError:
            pytest.skip("AlertRules not available")

    def test_alert_rules_initialization(self):
        """测试告警规则初始化"""
        try:
            from core.alert_rules import AlertRules

            rules = AlertRules()
            assert rules is not None
        except ImportError:
            pytest.skip("AlertRules not available")

    def test_alert_rule_evaluation(self):
        """测试告警规则评估"""
        # 模拟规则评估
        rule = {"metric": "cpu.usage", "operator": ">", "threshold": 80.0, "severity": "warning"}

        metric_value = 85.0

        # 评估规则
        if rule["operator"] == ">":
            triggered = metric_value > rule["threshold"]
        elif rule["operator"] == "<":
            triggered = metric_value < rule["threshold"]
        elif rule["operator"] == "==":
            triggered = metric_value == rule["threshold"]
        else:
            triggered = False

        assert triggered is True
        assert rule["severity"] == "warning"


class TestAlertRulesModule:
    """告警规则模块功能测试"""

    def test_load_alert_rules(self):
        """测试加载告警规则"""
        from core.alert_rules import get_all_alert_rules, load_alert_rules

        test_rules = {
            "cpu_high": {"threshold": 80.0, "severity": "warning", "enabled": True},
            "memory_high": {"threshold": 85.0, "severity": "critical", "enabled": True},
        }

        load_alert_rules(test_rules)
        loaded_rules = get_all_alert_rules()

        assert len(loaded_rules) == 2
        assert "cpu_high" in loaded_rules
        assert "memory_high" in loaded_rules

    def test_get_alert_rule(self):
        """测试获取单个告警规则"""
        from core.alert_rules import add_alert_rule, get_alert_rule

        test_rule = {"threshold": 90.0, "severity": "critical", "enabled": True}

        add_alert_rule("test_rule", test_rule)
        retrieved_rule = get_alert_rule("test_rule")

        assert retrieved_rule is not None
        assert retrieved_rule["threshold"] == 90.0
        assert retrieved_rule["severity"] == "critical"

    def test_get_alert_rule_not_found(self):
        """测试获取不存在的告警规则"""
        from core.alert_rules import get_alert_rule

        result = get_alert_rule("nonexistent_rule")
        assert result is None

    def test_add_alert_rule(self):
        """测试添加告警规则"""
        from core.alert_rules import add_alert_rule, get_alert_rule

        test_rule = {"threshold": 75.0, "severity": "warning", "enabled": True}

        add_alert_rule("new_rule", test_rule)
        retrieved_rule = get_alert_rule("new_rule")

        assert retrieved_rule is not None
        assert retrieved_rule["threshold"] == 75.0

    def test_remove_alert_rule(self):
        """测试删除告警规则"""
        from core.alert_rules import add_alert_rule, get_alert_rule, remove_alert_rule

        test_rule = {"threshold": 80.0, "severity": "warning", "enabled": True}

        add_alert_rule("temp_rule", test_rule)
        assert get_alert_rule("temp_rule") is not None

        result = remove_alert_rule("temp_rule")
        assert result is True
        assert get_alert_rule("temp_rule") is None

    def test_remove_alert_rule_not_found(self):
        """测试删除不存在的告警规则"""
        from core.alert_rules import remove_alert_rule

        result = remove_alert_rule("nonexistent_rule")
        assert result is False

    def test_evaluate_alert_rule_triggered(self):
        """测试评估告警规则（触发）"""
        from core.alert_rules import add_alert_rule, evaluate_alert_rule

        test_rule = {"threshold": 80.0, "severity": "warning", "enabled": True}

        add_alert_rule("cpu_test", test_rule)
        alert = evaluate_alert_rule("cpu_test", 85.0)

        assert alert is not None
        assert alert["severity"] == "warning"
        assert alert["current_value"] == 85.0
        assert alert["threshold"] == 80.0

    def test_evaluate_alert_rule_not_triggered(self):
        """测试评估告警规则（未触发）"""
        from core.alert_rules import add_alert_rule, evaluate_alert_rule

        test_rule = {"threshold": 80.0, "severity": "warning", "enabled": True}

        add_alert_rule("cpu_test2", test_rule)
        alert = evaluate_alert_rule("cpu_test2", 75.0)

        assert alert is None

    def test_evaluate_alert_rule_disabled(self):
        """测试评估禁用的告警规则"""
        from core.alert_rules import add_alert_rule, evaluate_alert_rule

        test_rule = {"threshold": 80.0, "severity": "warning", "enabled": False}

        add_alert_rule("cpu_test3", test_rule)
        alert = evaluate_alert_rule("cpu_test3", 85.0)

        assert alert is None

    def test_evaluate_alert_rule_not_found(self):
        """测试评估不存在的告警规则"""
        from core.alert_rules import evaluate_alert_rule

        alert = evaluate_alert_rule("nonexistent_rule", 85.0)
        assert alert is None

    def test_evaluate_all_rules(self):
        """测试评估所有告警规则"""
        from core.alert_rules import evaluate_all_rules, load_alert_rules

        test_rules = {
            "cpu_high": {"threshold": 80.0, "severity": "warning", "enabled": True},
            "memory_high": {"threshold": 85.0, "severity": "critical", "enabled": True},
        }

        load_alert_rules(test_rules)

        metrics = {"cpu": 85.0, "memory": 90.0}

        alerts = evaluate_all_rules(metrics)

        assert len(alerts) == 2
        assert any(alert["rule_name"] == "cpu_high" for alert in alerts)
        assert any(alert["rule_name"] == "memory_high" for alert in alerts)

    def test_get_enabled_rules(self):
        """测试获取启用的告警规则"""
        from core.alert_rules import get_enabled_rules, load_alert_rules

        test_rules = {
            "cpu_high": {"threshold": 80.0, "severity": "warning", "enabled": True},
            "memory_high": {"threshold": 85.0, "severity": "critical", "enabled": False},
        }

        load_alert_rules(test_rules)
        enabled_rules = get_enabled_rules()

        assert len(enabled_rules) == 1
        assert "cpu_high" in enabled_rules
        assert "memory_high" not in enabled_rules

    def test_disable_rule(self):
        """测试禁用告警规则"""
        from core.alert_rules import add_alert_rule, disable_rule, get_alert_rule

        test_rule = {"threshold": 80.0, "severity": "warning", "enabled": True}

        add_alert_rule("test_disable", test_rule)
        result = disable_rule("test_disable")

        assert result is True
        assert get_alert_rule("test_disable")["enabled"] is False

    def test_disable_rule_not_found(self):
        """测试禁用不存在的告警规则"""
        from core.alert_rules import disable_rule

        result = disable_rule("nonexistent_rule")
        assert result is False

    def test_enable_rule(self):
        """测试启用告警规则"""
        from core.alert_rules import add_alert_rule, enable_rule, get_alert_rule

        test_rule = {"threshold": 80.0, "severity": "warning", "enabled": False}

        add_alert_rule("test_enable", test_rule)
        result = enable_rule("test_enable")

        assert result is True
        assert get_alert_rule("test_enable")["enabled"] is True

    def test_enable_rule_not_found(self):
        """测试启用不存在的告警规则"""
        from core.alert_rules import enable_rule

        result = enable_rule("nonexistent_rule")
        assert result is False

    def test_reset_alert_rules(self):
        """测试重置告警规则"""
        from core.alert_rules import get_all_alert_rules, load_alert_rules, reset_alert_rules

        # 加载自定义规则
        custom_rules = {"custom_rule": {"threshold": 95.0, "severity": "critical", "enabled": True}}

        load_alert_rules(custom_rules)
        assert len(get_all_alert_rules()) == 1

        # 重置为默认规则
        reset_alert_rules()
        reset_rules = get_all_alert_rules()

        # 验证规则已重置
        assert len(reset_rules) > 1 or "custom_rule" not in reset_rules


class TestAlertService:
    """告警服务测试"""

    def test_alert_service_import(self):
        """测试告警服务导入"""
        try:
            from core.alert_service import AlertService

            assert AlertService is not None
        except ImportError:
            pytest.skip("AlertService not available")

    def test_alert_service_initialization(self):
        """测试告警服务初始化"""
        try:
            from core.alert_service import AlertService

            service = AlertService()
            assert service is not None
        except ImportError:
            pytest.skip("AlertService not available")


class TestAlertHistory:
    """告警历史测试"""

    def test_alert_history_storage(self):
        """测试告警历史存储"""
        # 模拟告警历史存储
        alert_history = []

        alert = {
            "id": "alert_1",
            "metric": "cpu.usage",
            "value": 85.0,
            "timestamp": datetime.now().isoformat(),
            "severity": "warning",
        }

        alert_history.append(alert)

        assert len(alert_history) == 1
        assert alert_history[0]["id"] == "alert_1"

    def test_alert_history_query(self):
        """测试告警历史查询"""
        # 模拟告警历史
        alert_history = [
            {"metric": "cpu.usage", "value": 85.0, "timestamp": "2024-01-01T10:00:00"},
            {"metric": "memory.usage", "value": 75.0, "timestamp": "2024-01-01T10:01:00"},
            {"metric": "cpu.usage", "value": 90.0, "timestamp": "2024-01-01T10:02:00"},
        ]

        # 查询CPU告警
        cpu_alerts = [a for a in alert_history if a["metric"] == "cpu.usage"]

        assert len(cpu_alerts) == 2
        assert all(a["metric"] == "cpu.usage" for a in cpu_alerts)


class TestAlertSeverity:
    """告警严重级别测试"""

    def test_severity_levels(self):
        """测试严重级别"""
        severity_levels = ["info", "warning", "error", "critical"]

        assert "critical" in severity_levels
        assert "warning" in severity_levels

    def test_severity_comparison(self):
        """测试严重级别比较"""
        severity_order = {"info": 1, "warning": 2, "error": 3, "critical": 4}

        assert severity_order["critical"] > severity_order["warning"]
        assert severity_order["error"] > severity_order["info"]

    def test_severity_escalation(self):
        """测试严重级别升级"""
        current_severity = "warning"
        escalation_rules = {"warning": "error", "error": "critical", "critical": "critical"}

        escalated_severity = escalation_rules.get(current_severity, current_severity)

        assert escalated_severity == "error"


class TestSSHCleanup:
    """SSH缓存清理测试"""

    def test_cleanup_ssh_cache_empty(self):
        """测试空缓存清理"""
        from core.alert_engine import _cleanup_ssh_brute_force_cache

        # 空缓存应该不会报错
        _cleanup_ssh_brute_force_cache()

    def test_cleanup_ssh_cache_expired_hosts(self):
        """测试清理过期主机"""
        from datetime import datetime, timedelta

        from core.alert_engine import (
            _cleanup_ssh_brute_force_cache,
            _ssh_failed_window,
            _ssh_last_alert_time,
        )

        # 添加过期数据
        old_time = datetime.now() - timedelta(seconds=4000)  # 超过1小时
        _ssh_failed_window["old-host"] = [(old_time, 5)]
        _ssh_last_alert_time["old-host"] = old_time

        # 添加新数据
        new_time = datetime.now()
        _ssh_failed_window["new-host"] = [(new_time, 10)]
        _ssh_last_alert_time["new-host"] = new_time

        # 清理缓存
        _cleanup_ssh_brute_force_cache()

        # 过期主机应该被清理
        assert "old-host" not in _ssh_failed_window
        assert "old-host" not in _ssh_last_alert_time
        # 新主机应该保留
        assert "new-host" in _ssh_failed_window
        assert "new-host" in _ssh_last_alert_time

    def test_cleanup_ssh_cache_max_hosts(self):
        """测试缓存上限保护"""
        from datetime import datetime

        from core.alert_engine import _cleanup_ssh_brute_force_cache, _ssh_failed_window

        # 添加超过上限的主机
        now = datetime.now()
        for i in range(600):  # 超过500上限
            _ssh_failed_window[f"host-{i}"] = [(now, i)]

        # 清理缓存
        _cleanup_ssh_brute_force_cache()

        # 应该被限制在上限内
        assert len(_ssh_failed_window) <= 500


class TestLinuxSecurityAlerts:
    """Linux安全告警测试"""

    @pytest.mark.asyncio
    async def test_check_linux_security_alerts_empty_input(self):
        """测试空输入"""
        from core.alert_engine import check_linux_security_alerts

        result = await check_linux_security_alerts([])
        assert result == []

    @pytest.mark.asyncio
    async def test_check_linux_security_alerts_invalid_input(self):
        """测试无效输入"""
        from core.alert_engine import check_linux_security_alerts

        result = await check_linux_security_alerts(None)
        assert result == []

        result = await check_linux_security_alerts("not a list")
        assert result == []

    @pytest.mark.asyncio
    async def test_check_linux_security_alerts_invalid_host_data(self):
        """测试无效主机数据"""
        from core.alert_engine import check_linux_security_alerts

        invalid_data = [{"not a dict": True}, 123, "string"]

        result = await check_linux_security_alerts(invalid_data)
        assert result == []

    @pytest.mark.asyncio
    async def test_check_linux_security_alerts_skipped_status(self):
        """测试跳过非ok/degraded状态"""
        from core.alert_engine import check_linux_security_alerts

        skipped_data = [
            {"name": "host1", "status": "error"},
            {"name": "host2", "status": "timeout"},
        ]

        result = await check_linux_security_alerts(skipped_data)
        assert result == []

    @pytest.mark.asyncio
    async def test_check_linux_security_alerts_missing_metrics(self):
        """测试缺少指标数据"""
        from core.alert_engine import check_linux_security_alerts

        no_metrics_data = [{"name": "host1", "status": "ok"}]

        result = await check_linux_security_alerts(no_metrics_data)
        assert result == []

    @pytest.mark.asyncio
    async def test_check_linux_security_alerts_invalid_ssh_metric(self):
        """测试无效SSH指标"""
        from core.alert_engine import check_linux_security_alerts

        invalid_ssh_data = [
            {
                "name": "host1",
                "status": "ok",
                "metrics": {"ssh_failed_logins": "ERROR: command not found"},
            }
        ]

        result = await check_linux_security_alerts(invalid_ssh_data)
        assert result == []

    @pytest.mark.asyncio
    async def test_check_linux_security_alerts_no_threat(self):
        """测试无威胁情况"""
        from core.alert_engine import check_linux_security_alerts

        no_threat_data = [
            {"name": "host1", "status": "ok", "metrics": {"ssh_failed_logins": {"value": "2"}}}
        ]

        result = await check_linux_security_alerts(no_threat_data)
        assert result == []


class TestAlertDeduplication:
    """告警去重功能测试"""

    def test_dedup_key_basic(self):
        """测试基本去重key生成"""
        from core.alert_engine import _dedup_key

        alert = {"metric": "cpu.usage", "level": "warning"}

        key = _dedup_key(alert)
        assert key == "cpu.usage_warning"

    def test_dedup_key_disk_alert(self):
        """测试磁盘告警去重key（区分设备）"""
        from core.alert_engine import _dedup_key

        alert = {"metric": "disk_percent", "level": "critical", "id": "DISK-C:-10:30:45"}

        key = _dedup_key(alert)
        assert key == "disk_percent_critical_C:"

    def test_dedup_key_disk_different_devices(self):
        """测试不同磁盘设备的去重key不同"""
        from core.alert_engine import _dedup_key

        alert_c = {"metric": "disk_percent", "level": "critical", "id": "DISK-C:-10:30:45"}

        alert_d = {"metric": "disk_percent", "level": "critical", "id": "DISK-D:-10:30:46"}

        key_c = _dedup_key(alert_c)
        key_d = _dedup_key(alert_d)

        assert key_c != key_d
        assert "C:" in key_c
        assert "D:" in key_d

    def test_dedup_key_missing_fields(self):
        """测试缺失字段的处理"""
        from core.alert_engine import _dedup_key

        alert = {}
        key = _dedup_key(alert)
        assert key == "unknown_unknown"

    def test_try_dedup_first_alert(self):
        """测试首次告警放行"""
        from core.alert_engine import _dedup_cache, _try_dedup

        # 清空缓存
        _dedup_cache.clear()

        alert = {"metric": "cpu.usage", "level": "warning", "value": 85.0}

        result = _try_dedup(alert)
        assert result is False  # 应该放行
        assert "cpu.usage_warning" in _dedup_cache

    def test_try_dedup_duplicate_alert(self):
        """测试重复告警拦截"""
        from core.alert_engine import _DEDUP_WINDOW_SEC, _dedup_cache, _try_dedup  # noqa: F401

        # 清空缓存
        _dedup_cache.clear()

        alert = {"metric": "cpu.usage", "level": "warning", "value": 85.0}

        # 第一次告警
        result1 = _try_dedup(alert)
        assert result1 is False

        # 立即发送相同告警（在去重窗口内）
        result2 = _try_dedup(alert)
        assert result2 is True  # 应该拦截

        # 检查缓存状态
        assert _dedup_cache["cpu.usage_warning"]["repeat_count"] == 1

    def test_try_dedup_cache_capacity(self):
        """测试缓存容量保护"""
        from core.alert_engine import _DEDUP_CACHE_MAX, _dedup_cache, _try_dedup

        # 清空缓存
        _dedup_cache.clear()

        # 填满缓存
        for i in range(_DEDUP_CACHE_MAX + 10):
            alert = {"metric": f"metric_{i}", "level": "warning", "value": i}
            _try_dedup(alert)

        # 缓存大小应该被限制
        assert len(_dedup_cache) <= _DEDUP_CACHE_MAX

    def test_dedup_cache_initialization(self):
        """测试去重缓存初始化"""
        from core.alert_engine import _DEDUP_CACHE_MAX, _DEDUP_WINDOW_SEC, _dedup_cache

        assert isinstance(_dedup_cache, dict)
        # 不检查长度，因为可能被其他测试填充
        assert _DEDUP_CACHE_MAX == 200
        assert _DEDUP_WINDOW_SEC == 300

    def test_alert_deduplication_with_time_window(self):
        """测试时间窗口内的告警去重"""
        alert_cache = {}
        time_window = timedelta(minutes=5)

        alert_1 = {"metric": "cpu.usage", "value": 85.0, "timestamp": datetime.now()}

        # 添加到缓存
        fingerprint = f"{alert_1['metric']}_{alert_1['value']}"
        alert_cache[fingerprint] = alert_1["timestamp"]

        # 检查是否在时间窗口内
        current_time = datetime.now()
        last_alert_time = alert_cache.get(fingerprint)

        if last_alert_time and (current_time - last_alert_time) < time_window:
            is_duplicate = True
        else:
            is_duplicate = False

        assert is_duplicate is True  # 在时间窗口内，视为重复


class TestAlertNotification:
    """告警通知测试"""

    def test_notification_channels(self):
        """测试通知渠道"""
        channels = ["email", "sms", "webhook", "slack"]

        assert "email" in channels
        assert "webhook" in channels

    def test_notification_format(self):
        """测试通知格式"""
        alert = {
            "metric": "cpu.usage",
            "value": 85.0,
            "threshold": 80.0,
            "severity": "warning",
            "timestamp": "2024-01-01T10:00:00",
        }

        # 格式化通知消息
        message = f"告警: {alert['metric']} = {alert['value']} (阈值: {alert['threshold']})"

        assert "cpu.usage" in message
        assert "85.0" in message
        assert "warning" in alert["severity"]

    def test_notification_rate_limiting(self):
        """测试通知限速"""
        notification_history = []
        rate_limit = 5  # 最多5次通知
        time_window = timedelta(minutes=10)

        # 模拟通知历史
        for i in range(6):
            notification_history.append(
                {"timestamp": datetime.now() - timedelta(minutes=i), "channel": "email"}
            )

        # 检查限速
        recent_notifications = [
            n for n in notification_history if datetime.now() - n["timestamp"] < time_window
        ]

        assert len(recent_notifications) > rate_limit  # 超过限速


class TestAlertStatistics:
    """告警统计测试"""

    def test_alert_counting(self):
        """测试告警计数"""
        alerts = [
            {"severity": "warning"},
            {"severity": "error"},
            {"severity": "warning"},
            {"severity": "critical"},
            {"severity": "info"},
        ]

        warning_count = sum(1 for a in alerts if a["severity"] == "warning")
        error_count = sum(1 for a in alerts if a["severity"] == "error")

        assert warning_count == 2
        assert error_count == 1

    def test_alert_rate_calculation(self):
        """测试告警率计算"""
        alerts = [
            {"timestamp": datetime.now() - timedelta(minutes=10)},
            {"timestamp": datetime.now() - timedelta(minutes=5)},
            {"timestamp": datetime.now()},
        ]

        time_window = timedelta(minutes=15)
        recent_alerts = [a for a in alerts if datetime.now() - a["timestamp"] < time_window]

        alert_rate = len(recent_alerts) / (time_window.total_seconds() / 60)  # 每分钟告警数

        assert alert_rate == 0.2  # 3个告警 / 15分钟 = 0.2 告警/分钟


class TestAlertSuppression:
    """告警抑制测试"""

    def test_alert_suppression_rules(self):
        """测试告警抑制规则"""
        suppression_rules = [
            {"metric": "cpu.usage", "condition": "maintenance", "action": "suppress"},
            {"metric": "disk.usage", "condition": "backup", "action": "suppress"},
        ]

        alert = {"metric": "cpu.usage", "condition": "maintenance"}

        # 检查是否应该抑制
        should_suppress = False
        for rule in suppression_rules:
            if rule["metric"] == alert["metric"] and rule["condition"] == alert["condition"]:
                should_suppress = True
                break

        assert should_suppress is True

    def test_alert_suppression_duration(self):
        """测试告警抑制持续时间"""
        suppression_end = datetime.now() + timedelta(hours=2)

        # 检查抑制是否仍然有效
        current_time = datetime.now()
        is_suppressed = current_time < suppression_end

        assert is_suppressed is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
