# -*- coding: utf-8 -*-
"""Tests for core/ai_service.py."""

import pytest  # noqa: F401  # Imported for test setup

from core.ai_service import (
    AIContextService,
    _extract_gather_result,
    _safe_alert_value,
    _safe_get_metric,
)


def test_safe_alert_value():
    assert _safe_alert_value(None) is None
    assert _safe_alert_value(42) == 42
    assert len(_safe_alert_value("too long string " * 20)) == 64


def test_safe_get_metric():
    assert _safe_get_metric({}, "cpu", "usage") == "N/A"
    assert _safe_get_metric({"cpu": {"usage": 80}}, "cpu", "usage") == 80
    assert _safe_get_metric({"cpu": None}, "cpu", "usage", default=0) == 0


def test_extract_gather_result():
    assert _extract_gather_result({"a": 1}, "test", dict) == {"a": 1}
    assert _extract_gather_result("not a dict", "test", dict) is None
    assert _extract_gather_result(RuntimeError("boom"), "test", dict) is None
    assert _extract_gather_result(None, "test", dict) is None


def test_safe_alert_value_edge_cases():
    """测试 _safe_alert_value 的边界条件"""
    # 测试 float 类型
    assert _safe_alert_value(3.14) == 3.14
    assert _safe_alert_value(-0.5) == -0.5

    # 测试 bool 类型
    assert _safe_alert_value(True) is True
    assert _safe_alert_value(False) is False

    # 测试空字符串
    assert _safe_alert_value("") == ""

    # 测试可转换为数字的字符串
    assert _safe_alert_value("123") == 123.0
    assert _safe_alert_value("-45.67") == -45.67
    assert _safe_alert_value("0") == 0.0

    # 测试不可转换为数字的字符串
    assert _safe_alert_value("abc") == "abc"
    assert _safe_alert_value("not a number") == "not a number"

    # 测试字符串截断边界（正好64字符）
    str_64 = "a" * 64
    assert _safe_alert_value(str_64) == str_64
    assert len(_safe_alert_value(str_64)) == 64

    # 测试字符串截断边界（超过64字符）
    str_65 = "a" * 65
    assert len(_safe_alert_value(str_65)) == 64

    # 测试其他类型（列表、字典等转换为字符串）
    assert _safe_alert_value([1, 2, 3]) == "[1, 2, 3]"
    assert _safe_alert_value({"key": "value"}) == "{'key': 'value'}"
    assert len(_safe_alert_value({"a": "b" * 100})) == 64


def test_safe_get_metric_edge_cases():
    """测试 _safe_get_metric 的边界条件"""
    # 测试 snapshot 为 None
    assert _safe_get_metric(None, "cpu", "usage") == "N/A"

    # 测试 snapshot 为非 dict 类型
    assert _safe_get_metric("not a dict", "cpu", "usage") == "N/A"
    assert _safe_get_metric([1, 2, 3], "cpu", "usage") == "N/A"
    assert _safe_get_metric(123, "cpu", "usage") == "N/A"

    # 测试 section 不存在
    assert _safe_get_metric({}, "cpu", "usage") == "N/A"
    assert _safe_get_metric({"memory": {"usage": 50}}, "cpu", "usage") == "N/A"

    # 测试 section 为非 dict 类型
    assert _safe_get_metric({"cpu": "not a dict"}, "cpu", "usage") == "N/A"
    assert _safe_get_metric({"cpu": [1, 2, 3]}, "cpu", "usage") == "N/A"
    assert _safe_get_metric({"cpu": 123}, "cpu", "usage") == "N/A"

    # 测试 field 不存在
    assert _safe_get_metric({"cpu": {}}, "cpu", "usage") == "N/A"
    assert _safe_get_metric({"cpu": {"temp": 60}}, "cpu", "usage") == "N/A"

    # 测试自定义默认值
    assert _safe_get_metric({}, "cpu", "usage", default=0) == 0
    assert _safe_get_metric({}, "cpu", "usage", default=None) is None
    assert _safe_get_metric({}, "cpu", "usage", default="unknown") == "unknown"

    # 测试嵌套层级错误
    assert _safe_get_metric({"cpu": None}, "cpu", "usage", default=0) == 0

    # 测试正常获取各种类型
    assert _safe_get_metric({"cpu": {"usage": 80}}, "cpu", "usage") == 80
    assert _safe_get_metric({"cpu": {"usage": "high"}}, "cpu", "usage") == "high"
    assert _safe_get_metric({"cpu": {"usage": None}}, "cpu", "usage") is None


@pytest.mark.asyncio
async def test_collect_rich_context_error_handling():
    """测试 collect_rich_context 的错误处理"""
    service = AIContextService()

    # 测试 snapshot 为 None（应使用缓存快照）
    ctx = await service.collect_rich_context(snapshot=None)
    assert isinstance(ctx, dict)
    assert "top_processes" in ctx
    assert "recent_alerts" in ctx
    assert "stats" in ctx

    # 测试 snapshot 为空字典
    ctx = await service.collect_rich_context(snapshot={})
    assert isinstance(ctx, dict)
    assert "top_processes" in ctx
    assert "recent_alerts" in ctx

    # 测试 snapshot 为非 dict 类型
    ctx = await service.collect_rich_context(snapshot="invalid")
    assert isinstance(ctx, dict)
    assert "top_processes" in ctx

    # 测试 snapshot 包含无效数据结构
    ctx = await service.collect_rich_context(
        snapshot={
            "top_processes": "not a list",
            "cpu": "not a dict",
            "memory": None,
        }
    )
    assert isinstance(ctx, dict)
    # 应该有默认值而不崩溃
    assert "top_processes" in ctx
    assert "infrastructure_metrics" in ctx

    # 测试 service_name 参数
    ctx = await service.collect_rich_context(
        snapshot={"top_processes": [{"name": "test"}]},
        service_name="test_service"
    )
    assert isinstance(ctx, dict)
    assert "service_metrics" in ctx
    assert "topology" in ctx


@pytest.mark.asyncio
async def test_collect_rich_context_with_complex_data():
    """测试 collect_rich_context 的复杂数据处理"""
    service = AIContextService()

    # 测试包含特殊字符的复杂数据
    complex_snapshot = {
        "top_processes": [
            {"name": "process-with-special-chars-<>\"&'", "cpu": 10.5, "memory": 2048},
            {"name": "中文进程", "cpu": 20.3, "memory": 4096},
            {"name": "🚀 emoji process", "cpu": 5.0, "memory": 1024},
        ],
        "cpu": {
            "usage": 85.5,
            "temperature": 72.3,
            "cores": [10, 20, 30, 40],
        },
        "memory": {
            "total": 16384,
            "used": 8192,
            "free": 8192,
        },
        "disk": [
            {"device": "/dev/sda1", "mount": "/", "usage": 75.5},
            {"device": "/dev/sda2", "mount": "/data", "usage": 45.2},
        ],
        "network": {
            "in": 1024000,
            "out": 512000,
            "errors": 0,
        },
        "system": {
            "uptime": 86400,
            "load": [1.5, 1.8, 2.1],
        },
    }

    ctx = await service.collect_rich_context(snapshot=complex_snapshot)
    assert isinstance(ctx, dict)

    # 验证 top_processes 被正确处理（限制为5个）
    assert "top_processes" in ctx
    assert isinstance(ctx["top_processes"], list)
    assert len(ctx["top_processes"]) <= 5

    # 验证基础设施指标被正确提取
    assert "infrastructure_metrics" in ctx
    infra = ctx["infrastructure_metrics"]
    assert "cpu" in infra
    assert "memory" in infra
    assert "disk" in infra
    assert "network" in infra
    assert "system" in infra

    # 测试大数据量场景（超过限制）
    large_snapshot = {
        "top_processes": [{"name": f"process_{i}", "cpu": i} for i in range(100)],
        "cpu": {"usage": 50},
    }

    ctx = await service.collect_rich_context(snapshot=large_snapshot)
    assert len(ctx["top_processes"]) <= 5  # 应该被限制为5个

    # 测试包含 None 值的数据
    null_snapshot = {
        "top_processes": None,
        "cpu": None,
        "memory": None,
    }

    ctx = await service.collect_rich_context(snapshot=null_snapshot)
    assert isinstance(ctx, dict)
    assert "top_processes" in ctx
    assert "infrastructure_metrics" in ctx

    # 测试嵌套的复杂数据结构
    nested_snapshot = {
        "top_processes": [
            {
                "name": "complex",
                "details": {
                    "user": "root",
                    "command": "/usr/bin/python",
                    "args": ["--verbose", "--config", "/etc/config.json"],
                },
            }
        ],
        "cpu": {"usage": 60},
    }

    ctx = await service.collect_rich_context(snapshot=nested_snapshot)
    assert isinstance(ctx, dict)
    assert "top_processes" in ctx
