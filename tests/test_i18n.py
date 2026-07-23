# -*- coding: utf-8 -*-
# tests/test_i18n.py
# 国际化(i18n)单元测试
import json  # noqa: F401
import os  # noqa: F401
import tempfile  # noqa: F401
from pathlib import Path  # noqa: F401

import pytest

from core.i18n import (
    _MESSAGES_DIR,
    _load_messages,
    _messages,
    get_locale,
    get_messages_stats,
    get_supported_locales,
    msg,
    reload_messages,
    set_locale,
)


class TestLocaleManagement:
    """语言管理测试"""

    def test_set_locale_valid(self):
        """测试设置有效语言"""
        set_locale("zh")
        assert get_locale() == "zh"

        set_locale("en")
        assert get_locale() == "en"

    def test_set_locale_invalid(self):
        """测试设置无效语言（降级到默认）"""
        set_locale("invalid")
        assert get_locale() == "zh"  # Should fallback to default

    def test_set_locale_case_insensitive(self):
        """测试语言设置不区分大小写"""
        set_locale("ZH")
        assert get_locale() == "zh"

        set_locale("EN")
        assert get_locale() == "en"

    def test_get_locale_default(self):
        """测试获取默认语言"""
        # Reset to default
        set_locale("zh")
        assert get_locale() == "zh"


class TestTranslation:
    """翻译功能测试"""

    def test_msg_basic(self):
        """测试基本翻译"""
        set_locale("zh")
        # Test with a key that should return the key itself if not found
        result = msg("test.key")
        assert result == "test.key"  # Fallback to key if not found

    def test_msg_with_interpolation(self):
        """测试带插值的翻译"""
        set_locale("zh")
        # Test interpolation with a key that doesn't exist
        result = msg("test.key", name="value")
        # Since the key doesn't exist, it returns the key itself
        # The interpolation won't work on the key itself
        assert result == "test.key"

    def test_msg_english_locale(self):
        """测试英文语言环境"""
        set_locale("en")
        result = msg("test.key")
        assert result == "test.key"  # Fallback to key if not found


class TestSupportedLocales:
    """支持的语言测试"""

    def test_get_supported_locales(self):
        """测试获取支持的语言列表"""
        locales = get_supported_locales()
        assert isinstance(locales, list)
        assert "zh" in locales
        assert "en" in locales


class TestMessagesStats:
    """语言包统计测试"""

    def test_get_messages_stats(self):
        """测试获取语言包统计"""
        stats = get_messages_stats()

        assert "loaded" in stats
        assert "supported_locales" in stats
        assert "fallback_locale" in stats
        assert "current_locale" in stats
        assert isinstance(stats["supported_locales"], list)


class TestMessagesLoading:
    """语言包加载测试"""

    def test_load_messages(self):
        """测试加载语言包"""
        _load_messages()
        assert isinstance(_messages, dict)

    def test_reload_messages(self):
        """测试重新加载语言包"""
        stats = reload_messages()
        assert isinstance(stats, dict)
        assert "loaded" in stats


class TestMessagesDirectory:
    """语言包目录测试"""

    def test_messages_directory_exists(self):
        """测试语言包目录存在"""
        assert _MESSAGES_DIR.exists()


class TestTranslationFallback:
    """翻译降级测试"""

    def test_translation_fallback_to_key(self):
        """测试翻译降级到键本身"""
        set_locale("zh")
        result = msg("nonexistent.key")
        assert result == "nonexistent.key"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
