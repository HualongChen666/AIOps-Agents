# -*- coding: utf-8 -*-
"""测试国际化管理器模块"""

from datetime import datetime

import pytest

from core.i18n_manager import (
    I18nManager,
    Language,
    Locale,
    TimeZone,
    TranslationResource,
    get_i18n_manager,
)


class TestI18nEnumsAndDataClasses:
    """测试枚举和数据类"""

    def test_language_values(self):
        assert Language.CHINESE.value == "zh"
        assert Language.ENGLISH.value == "en"

    def test_timezone_values(self):
        assert TimeZone.UTC.value == "UTC"
        assert TimeZone.BEIJING.value == "Asia/Shanghai"

    def test_locale_defaults(self):
        locale = Locale(
            language=Language.ENGLISH,
            region="US",
            timezone=TimeZone.NEW_YORK,
            number_format="#",
            date_format="MM",
            currency="USD",
        )
        assert locale.metadata == {}


class TestI18nManager:
    """测试 I18nManager 核心方法"""

    def test_init_default_locales(self):
        mgr = I18nManager()
        assert "zh-CN" in mgr.locales
        assert "en-US" in mgr.locales
        assert mgr.current_locale is not None

    def test_add_locale(self):
        mgr = I18nManager()
        new_locale = Locale(
            language=Language.FRENCH,
            region="FR",
            timezone=TimeZone.PARIS,
            number_format="#",
            date_format="DD",
            currency="EUR",
        )
        assert mgr.add_locale("fr-FR", new_locale) is True
        assert mgr.add_locale("fr-FR", new_locale) is False

    def test_set_current_locale(self):
        mgr = I18nManager()
        assert mgr.set_current_locale("en-US") is True
        assert mgr.get_current_locale() == mgr.locales["en-US"]
        assert mgr.set_current_locale("missing") is False

    def test_detect_locale_from_request(self):
        mgr = I18nManager()
        assert mgr.detect_locale_from_request("en;q=0.9") == "en-US"
        assert mgr.detect_locale_from_request("zh") == "zh-CN"
        assert mgr.detect_locale_from_request(None, "UTC") is None
        assert mgr.detect_locale_from_request("en", "Invalid/Zone") == "en-US"

    def test_detect_locale_auto_detect_disabled(self):
        mgr = I18nManager(config={"auto_detect_language": False, "auto_detect_timezone": False})
        assert mgr.detect_locale_from_request("en") is None

    def test_add_translation_resource(self):
        mgr = I18nManager()
        resource = TranslationResource(
            language=Language.ENGLISH,
            namespace="common",
            translations={"hello": "Hello", "world": "World"},
        )
        assert mgr.add_translation_resource(resource) is True
        assert mgr.total_translations == 2

    def test_translate(self):
        mgr = I18nManager()
        resource = TranslationResource(
            language=Language.CHINESE,
            namespace="common",
            translations={"hello": "你好, {name}"},
        )
        mgr.add_translation_resource(resource)
        assert mgr.translate("hello", name="AI") == "你好, AI"

    def test_translate_fallback(self):
        mgr = I18nManager()
        en_resource = TranslationResource(
            language=Language.ENGLISH,
            namespace="common",
            translations={"key": "English"},
        )
        mgr.add_translation_resource(en_resource)
        mgr.fallback_language = Language.ENGLISH
        # No Chinese translation, fallback to English
        assert mgr.translate("key", language=Language.CHINESE) == "English"

    def test_translate_missing_namespace_uses_common(self):
        mgr = I18nManager()
        common = TranslationResource(
            language=Language.CHINESE,
            namespace="common",
            translations={"shared": "common-value"},
        )
        mgr.add_translation_resource(common)
        assert mgr.translate("shared", namespace="missing") == "common-value"

    def test_translate_returns_key_when_missing(self):
        mgr = I18nManager()
        assert mgr.translate("missing_key") == "missing_key"

    def test_format_translation_invalid_kwargs(self):
        mgr = I18nManager()
        assert mgr._format_translation("{missing}", extra="x") == "{missing}"

    def test_format_number_and_currency(self):
        mgr = I18nManager()
        locale = mgr.locales["en-US"]
        formatted = mgr.format_number(1234.5, locale)
        assert formatted == locale.number_format
        assert mgr.format_currency(100, locale) == f"{locale.currency} {formatted}"

    def test_format_number_invalid_locale(self):
        mgr = I18nManager()
        assert mgr.format_number(42, None) == mgr.current_locale.number_format

    def test_format_date(self):
        mgr = I18nManager()
        date = datetime(2026, 7, 20, 10, 0, 0)
        assert "2026-07-20" in mgr.format_date(date)

    def test_convert_timezone(self):
        mgr = I18nManager()
        date = datetime.utcnow()
        assert mgr.convert_timezone(date, TimeZone.UTC, TimeZone.BEIJING) == date

    def test_get_supported_languages_and_locales(self):
        mgr = I18nManager()
        languages = mgr.get_supported_languages()
        assert any(lang["code"] == "zh" for lang in languages)
        locales = mgr.get_supported_locales()
        assert any(loc["locale_id"] == "zh-CN" for loc in locales)

    def test_get_i18n_summary(self):
        mgr = I18nManager()
        summary = mgr.get_i18n_summary()
        assert "total_locales" in summary
        assert summary["default_language"] == "zh"

    def test_get_i18n_manager_singleton(self):
        mgr1 = get_i18n_manager()
        mgr2 = get_i18n_manager()
        assert mgr1 is mgr2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
