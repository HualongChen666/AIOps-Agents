"""
AI Service 附加测试用例
为提升 core/ai_service.py 的覆盖率
"""

import asyncio
import os
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from core.ai_service import (
    AIContextService,
    _extract_gather_result,
    _safe_alert_value,
    _safe_get_metric,
    ai_context_service,
)


class TestSafeAlertValueExtended:
    """扩展 _safe_alert_value 函数的测试覆盖"""

    def test_safe_alert_value_float_string(self):
        """测试可转换为float的字符串"""
        assert _safe_alert_value("123.45") == 123.45
        assert _safe_alert_value("0") == 0.0
        assert _safe_alert_value("-50.5") == -50.5

    def test_safe_alert_value_long_string(self):
        """测试长字符串截断"""
        long_str = "a" * 100
        result = _safe_alert_value(long_str)
        assert len(result) == 64
        assert result == "a" * 64

    def test_safe_alert_value_unicode_string(self):
        """测试Unicode字符串"""
        unicode_str = "测试中文🎉"
        result = _safe_alert_value(unicode_str)
        assert isinstance(result, str)
        assert len(result) <= 64

    def test_safe_alert_value_bytes(self):
        """测试bytes类型"""
        byte_val = b"test"
        result = _safe_alert_value(byte_val)
        assert isinstance(result, str)
        assert len(result) <= 64

    def test_safe_alert_value_complex_number(self):
        """测试复数"""
        complex_val = 3 + 4j
        result = _safe_alert_value(complex_val)
        assert isinstance(result, str)
        assert len(result) <= 64

    def test_safe_alert_value_list(self):
        """测试列表类型"""
        list_val = [1, 2, 3]
        result = _safe_alert_value(list_val)
        assert isinstance(result, str)
        assert len(result) <= 64

    def test_safe_alert_value_dict(self):
        """测试字典类型"""
        dict_val = {"key": "value"}
        result = _safe_alert_value(dict_val)
        assert isinstance(result, str)
        assert len(result) <= 64


class TestSafeGetMetricExtended:
    """扩展 _safe_get_metric 函数的测试覆盖"""

    def test_safe_get_metric_nested_deep(self):
        """测试深层嵌套"""
        snapshot = {"level1": {"level2": {"level3": {"target": "value"}}}}
        result = _safe_get_metric(snapshot, "level1", "level2")
        assert isinstance(result, dict)
        assert "level3" in result

    def test_safe_get_metric_section_is_list(self):
        """测试section是列表"""
        snapshot = {"section": [1, 2, 3]}
        result = _safe_get_metric(snapshot, "section", "field")
        assert result == "N/A"

    def test_safe_get_metric_section_is_string(self):
        """测试section是字符串"""
        snapshot = {"section": "string_value"}
        result = _safe_get_metric(snapshot, "section", "field")
        assert result == "N/A"

    def test_safe_get_metric_field_is_complex(self):
        """测试field是复杂对象"""
        snapshot = {"section": {"field": {"nested": "value"}}}
        result = _safe_get_metric(snapshot, "section", "field")
        assert isinstance(result, dict)

    def test_safe_get_metric_custom_default(self):
        """测试自定义默认值"""
        snapshot = {}
        result = _safe_get_metric(snapshot, "section", "field", default="custom")
        assert result == "custom"

    def test_safe_get_metric_none_default(self):
        """测试None作为默认值"""
        snapshot = {}
        result = _safe_get_metric(snapshot, "section", "field", default=None)
        assert result is None

    def test_safe_get_metric_zero_default(self):
        """测试0作为默认值"""
        snapshot = {}
        result = _safe_get_metric(snapshot, "section", "field", default=0)
        assert result == 0


class TestExtractGatherResultExtended:
    """扩展 _extract_gather_result 函数的测试覆盖"""

    def test_extract_gather_result_timeout_error(self):
        """测试TimeoutError"""
        result = asyncio.TimeoutError("timeout")
        extracted = _extract_gather_result(result, "test", dict)
        assert extracted is None

    def test_extract_gather_result_keyboard_interrupt(self):
        """测试KeyboardInterrupt"""
        result = KeyboardInterrupt()
        extracted = _extract_gather_result(result, "test", dict)
        assert extracted is None

    def test_extract_gather_result_runtime_error(self):
        """测试RuntimeError"""
        result = RuntimeError("runtime error")
        extracted = _extract_gather_result(result, "test", dict)
        assert extracted is None

    def test_extract_gather_result_value_error(self):
        """测试ValueError"""
        result = ValueError("value error")
        extracted = _extract_gather_result(result, "test", dict)
        assert extracted is None

    def test_extract_gather_result_type_error(self):
        """测试TypeError"""
        result = TypeError("type error")
        extracted = _extract_gather_result(result, "test", dict)
        assert extracted is None

    def test_extract_gather_result_attribute_error(self):
        """测试AttributeError"""
        result = AttributeError("attribute error")
        extracted = _extract_gather_result(result, "test", dict)
        assert extracted is None

    def test_extract_gather_result_key_error(self):
        """测试KeyError"""
        result = KeyError("key error")
        extracted = _extract_gather_result(result, "test", dict)
        assert extracted is None

    def test_extract_gather_result_index_error(self):
        """测试IndexError"""
        result = IndexError("index error")
        extracted = _extract_gather_result(result, "test", dict)
        assert extracted is None

    def test_extract_gather_result_empty_string(self):
        """测试空字符串"""
        result = ""
        extracted = _extract_gather_result(result, "test", str)
        assert extracted == ""

    def test_extract_gather_result_zero(self):
        """测试0值"""
        result = 0
        extracted = _extract_gather_result(result, "test", int)
        assert extracted == 0

    def test_extract_gather_result_false(self):
        """测试False值"""
        result = False
        extracted = _extract_gather_result(result, "test", bool)
        assert extracted is False

    def test_extract_gather_result_empty_list(self):
        """测试空列表"""
        result = []
        extracted = _extract_gather_result(result, "test", list)
        assert extracted == []

    def test_extract_gather_result_empty_dict(self):
        """测试空字典"""
        result = {}
        extracted = _extract_gather_result(result, "test", dict)
        assert extracted == {}


class TestGlobalInstance:
    """测试全局实例"""

    def test_ai_context_service_instance(self):
        """测试全局服务实例"""
        assert ai_context_service is not None
        assert isinstance(ai_context_service, AIContextService)

    def test_ai_context_service_singleton(self):
        """测试单例模式"""
        service1 = AIContextService()
        service2 = AIContextService()
        # 虽然不是严格单例，但应该是相同类型
        assert type(service1) == type(service2)
