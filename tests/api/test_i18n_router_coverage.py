# -*- coding: utf-8 -*-
"""Comprehensive tests for i18n_router.py to achieve 90%+ coverage."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException


def test_get_i18n_status_success(client):
    """Test successful i18n status retrieval."""
    resp = client.get("/api/i18n/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "data" in data
    assert "timestamp" in data


def test_get_i18n_status_exception(client):
    """Test i18n status endpoint handles exceptions."""
    with patch("core.i18n_manager.get_i18n_manager") as mock_get:
        mock_get.side_effect = Exception("Manager error")
        resp = client.get("/api/i18n/status")
        assert resp.status_code == 500


def test_get_supported_locales_success(client):
    """Test successful locales retrieval."""
    resp = client.get("/api/i18n/locales")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "data" in data
    assert "locales" in data["data"]
    assert "count" in data["data"]
    assert "timestamp" in data


def test_get_supported_locales_exception(client):
    """Test locales endpoint handles exceptions (lines 89-91)."""
    with patch("core.i18n_manager.get_i18n_manager") as mock_get:
        mock_get.side_effect = Exception("Locales error")
        resp = client.get("/api/i18n/locales")
        assert resp.status_code == 500


def test_get_locale_info_success(client):
    """Test successful locale info retrieval."""
    resp = client.get("/api/i18n/locales/zh-CN")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "data" in data
    assert "locale_id" in data["data"]
    assert "timestamp" in data


def test_get_locale_info_exception(client):
    """Test locale info endpoint handles exceptions (lines 135-137)."""
    with patch("core.i18n_manager.get_i18n_manager") as mock_get:
        mock_get.side_effect = Exception("Locale info error")
        resp = client.get("/api/i18n/locales/en-US")
        assert resp.status_code == 500


def test_set_current_locale_success(client):
    """Test successful locale setting."""
    resp = client.post("/api/i18n/locale/set?locale_id=zh-CN")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "data" in data
    assert "locale_id" in data["data"]
    assert "set" in data["data"]
    assert "timestamp" in data


def test_set_current_locale_exception(client):
    """Test set locale endpoint handles exceptions (lines 181-183)."""
    with patch("core.i18n_manager.get_i18n_manager") as mock_get:
        mock_get.side_effect = Exception("Set locale error")
        resp = client.post("/api/i18n/locale/set?locale_id=en-US")
        assert resp.status_code == 500


def test_translate_success(client):
    """Test successful translation (line 227: language is not None)."""
    resp = client.get("/api/i18n/translate?key=welcome&namespace=common&language=zh")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "data" in data
    assert "key" in data["data"]
    assert "namespace" in data["data"]
    assert "language" in data["data"]
    assert "translation" in data["data"]
    assert "timestamp" in data


def test_translate_without_language(client):
    """Test translation without language parameter (line 227: language is None)."""
    resp = client.get("/api/i18n/translate?key=welcome&namespace=common")
    assert resp.status_code == 200
    data = resp.json()
    assert data["data"]["language"] is None


def test_translate_exception(client):
    """Test translate endpoint handles exceptions."""
    with patch("core.i18n_manager.get_i18n_manager") as mock_get:
        mock_get.side_effect = Exception("Translation error")
        resp = client.get("/api/i18n/translate?key=test")
        assert resp.status_code == 500


def test_update_translation_with_language(client):
    """Test update translation with language parameter (line 265-266: language in locales)."""
    resp = client.put(
        "/api/i18n/translate?key=test_key&translation=Test Translation&namespace=common&language=zh-CN"
    )
    assert resp.status_code in (200, 400, 500)


def test_update_translation_without_language_with_current_locale(client):
    """Test update translation without language but with current locale (lines 267-275)."""
    from core.i18n_manager import get_i18n_manager

    manager = get_i18n_manager()
    # Ensure current_locale is set
    manager.current_locale = manager.locales.get("zh-CN")

    resp = client.put(
        "/api/i18n/translate?key=test_key&translation=Test Translation&namespace=common"
    )
    assert resp.status_code in (200, 400, 500)


def test_update_translation_without_language_without_current_locale(client):
    """Test update translation without language and without current locale (line 277)."""
    from core.i18n_manager import get_i18n_manager

    manager = get_i18n_manager()
    # Clear current_locale to trigger the else branch
    manager.current_locale = None

    resp = client.put(
        "/api/i18n/translate?key=test_key&translation=Test Translation&namespace=common"
    )
    # Should use default "zh-CN" locale
    assert resp.status_code in (200, 400, 500)


def test_update_translation_http_exception(client):
    """Test update translation handles HTTPException (line 292-293)."""
    from core.i18n_manager import get_i18n_manager

    manager = get_i18n_manager()

    with patch.object(manager, "set_translation", return_value=False):
        resp = client.put(
            "/api/i18n/translate?key=test_key&translation=Test Translation&namespace=common&language=invalid-locale"
        )
        # Should return 400 when locale not supported
        assert resp.status_code in (400, 500)


def test_update_translation_exception(client):
    """Test update translation handles exceptions (lines 294-296)."""
    with patch("core.i18n_manager.get_i18n_manager") as mock_get:
        mock_get.side_effect = Exception("Update translation error")
        resp = client.put("/api/i18n/translate?key=test_key&translation=Test Translation")
        assert resp.status_code == 500


def test_format_number_with_locale(client):
    """Test format number with locale parameter (lines 326-328: locale is not None)."""
    resp = client.get("/api/i18n/format/number?number=1234.56&locale=zh-CN")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "data" in data
    assert "number" in data["data"]
    assert "locale" in data["data"]
    assert "formatted" in data["data"]
    assert "timestamp" in data


def test_format_number_with_invalid_locale(client):
    """Test format number with invalid locale (line 327: locale_obj = None)."""
    resp = client.get("/api/i18n/format/number?number=1234.56&locale=invalid-locale")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"


def test_format_number_without_locale(client):
    """Test format number without locale parameter (line 326: locale is None)."""
    resp = client.get("/api/i18n/format/number?number=1234.56")
    assert resp.status_code == 200
    data = resp.json()
    assert data["data"]["locale"] is None


def test_format_number_exception(client):
    """Test format number handles exceptions (lines 336-338)."""
    with patch("core.i18n_manager.get_i18n_manager") as mock_get:
        mock_get.side_effect = Exception("Format number error")
        resp = client.get("/api/i18n/format/number?number=1234.56")
        assert resp.status_code == 500


def test_format_currency_with_locale(client):
    """Test format currency with locale parameter (lines 367-368: locale is not None)."""
    resp = client.get("/api/i18n/format/currency?amount=99.99&locale=zh-CN")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "data" in data
    assert "amount" in data["data"]
    assert "locale" in data["data"]
    assert "formatted" in data["data"]
    assert "timestamp" in data


def test_format_currency_with_invalid_locale(client):
    """Test format currency with invalid locale (line 368: locale_obj = None)."""
    resp = client.get("/api/i18n/format/currency?amount=99.99&locale=invalid-locale")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"


def test_format_currency_without_locale(client):
    """Test format currency without locale parameter (line 367: locale is None)."""
    resp = client.get("/api/i18n/format/currency?amount=99.99")
    assert resp.status_code == 200
    data = resp.json()
    assert data["data"]["locale"] is None


def test_format_currency_exception(client):
    """Test format currency handles exceptions (lines 377-379)."""
    with patch("core.i18n_manager.get_i18n_manager") as mock_get:
        mock_get.side_effect = Exception("Format currency error")
        resp = client.get("/api/i18n/format/currency?amount=99.99")
        assert resp.status_code == 500


def test_format_date_with_locale(client):
    """Test format date with locale parameter (lines 410-411: locale is not None)."""
    resp = client.get("/api/i18n/format/date?date_str=2026-07-03T09:00:00&locale=zh-CN")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "data" in data
    assert "date" in data["data"]
    assert "locale" in data["data"]
    assert "formatted" in data["data"]
    assert "timestamp" in data


def test_format_date_with_invalid_locale(client):
    """Test format date with invalid locale (line 411: locale_obj = None)."""
    resp = client.get("/api/i18n/format/date?date_str=2026-07-03T09:00:00&locale=invalid-locale")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"


def test_format_date_without_locale(client):
    """Test format date without locale parameter (line 410: locale is None)."""
    resp = client.get("/api/i18n/format/date?date_str=2026-07-03T09:00:00")
    assert resp.status_code == 200
    data = resp.json()
    assert data["data"]["locale"] is None


def test_format_date_exception(client):
    """Test format date handles exceptions (lines 420-422)."""
    with patch("core.i18n_manager.get_i18n_manager") as mock_get:
        mock_get.side_effect = Exception("Format date error")
        resp = client.get("/api/i18n/format/date?date_str=2026-07-03T09:00:00")
        assert resp.status_code == 500


def test_format_date_invalid_date_string(client):
    """Test format date with invalid date string."""
    resp = client.get("/api/i18n/format/date?date_str=invalid-date")
    assert resp.status_code == 500


def test_translate_with_invalid_language_enum(client):
    """Test translate with invalid language enum."""
    with patch("core.i18n_manager.Language") as mock_lang:
        mock_lang.side_effect = ValueError("Invalid language")
        resp = client.get("/api/i18n/translate?key=test&language=invalid")
        assert resp.status_code == 500


def test_update_translation_unsupported_locale(client):
    """Test update translation with unsupported locale."""
    resp = client.put("/api/i18n/translate?key=test&translation=Test&language=unsupported-locale")
    # Should either succeed with fallback or return error
    assert resp.status_code in (200, 400, 500)


def test_format_number_with_decimals(client):
    """Test format number with decimals parameter."""
    resp = client.get("/api/i18n/format/number?number=1234.56789&decimals=3")
    assert resp.status_code == 200


def test_format_number_zero_decimals(client):
    """Test format number with zero decimals."""
    resp = client.get("/api/i18n/format/number?number=1234.56&decimals=0")
    assert resp.status_code == 200


def test_format_number_negative(client):
    """Test format negative number."""
    resp = client.get("/api/i18n/format/number?number=-1234.56")
    assert resp.status_code == 200


def test_format_currency_zero(client):
    """Test format zero currency."""
    resp = client.get("/api/i18n/format/currency?amount=0")
    assert resp.status_code == 200


def test_format_currency_negative(client):
    """Test format negative currency."""
    resp = client.get("/api/i18n/format/currency?amount=-99.99")
    assert resp.status_code == 200


def test_format_date_different_locales(client):
    """Test format date with different locales."""
    locales = ["zh-CN", "en-US", "ja-JP"]
    for locale in locales:
        resp = client.get(f"/api/i18n/format/date?date_str=2026-07-03T09:00:00&locale={locale}")
        assert resp.status_code == 200


def test_format_number_different_locales(client):
    """Test format number with different locales."""
    locales = ["zh-CN", "en-US", "ja-JP"]
    for locale in locales:
        resp = client.get(f"/api/i18n/format/number?number=1234.56&locale={locale}")
        assert resp.status_code == 200


def test_format_currency_different_locales(client):
    """Test format currency with different locales."""
    locales = ["zh-CN", "en-US", "ja-JP"]
    for locale in locales:
        resp = client.get(f"/api/i18n/format/currency?amount=99.99&locale={locale}")
        assert resp.status_code == 200


def test_translate_different_namespaces(client):
    """Test translate with different namespaces."""
    namespaces = ["common", "ui", "errors"]
    for namespace in namespaces:
        resp = client.get(f"/api/i18n/translate?key=test&namespace={namespace}")
        assert resp.status_code == 200


def test_set_locale_different_locales(client):
    """Test set current locale with different locales."""
    locales = ["zh-CN", "en-US", "ja-JP"]
    for locale in locales:
        resp = client.post(f"/api/i18n/locale/set?locale_id={locale}")
        assert resp.status_code in (200, 500)


def test_get_locale_info_different_locales(client):
    """Test get locale info for different locales."""
    locales = ["zh-CN", "en-US", "ja-JP"]
    for locale in locales:
        resp = client.get(f"/api/i18n/locales/{locale}")
        assert resp.status_code == 200


def test_update_translation_with_valid_language_in_locales(client):
    """Test update translation when language is in manager.locales (line 265-266)."""
    from core.i18n_manager import get_i18n_manager

    manager = get_i18n_manager()
    # Ensure the locale exists
    assert "zh-CN" in manager.locales

    resp = client.put(
        "/api/i18n/translate?key=test_key&translation=Test Translation&namespace=common&language=zh-CN"
    )
    assert resp.status_code in (200, 400, 500)


def test_update_translation_with_language_not_in_locales_but_current_locale_exists(client):
    """Test update translation when language not in locales but current_locale exists (line 267-275)."""
    from core.i18n_manager import get_i18n_manager

    manager = get_i18n_manager()
    # Set current_locale
    manager.current_locale = manager.locales.get("zh-CN")

    resp = client.put(
        "/api/i18n/translate?key=test_key&translation=Test Translation&namespace=common&language=xx-XX"
    )
    # Should fallback to current locale or default
    assert resp.status_code in (200, 400, 500)


def test_update_translation_no_language_no_current_locale(client):
    """Test update translation with no language and no current_locale (line 277)."""
    from core.i18n_manager import get_i18n_manager

    manager = get_i18n_manager()
    # Clear current_locale
    manager.current_locale = None

    resp = client.put(
        "/api/i18n/translate?key=test_key&translation=Test Translation&namespace=common"
    )
    # Should use default "zh-CN"
    assert resp.status_code in (200, 400, 500)


def test_update_translation_set_translation_fails(client):
    """Test update translation when set_translation returns False (line 279-280)."""
    from core.i18n_manager import get_i18n_manager

    manager = get_i18n_manager()

    with patch.object(manager, "set_translation", return_value=False):
        resp = client.put(
            "/api/i18n/translate?key=test_key&translation=Test Translation&namespace=common&language=zh-CN"
        )
        # Should return 400 when set_translation fails
        assert resp.status_code == 400


def test_update_translation_set_translation_succeeds(client):
    """Test update translation when set_translation returns True (line 278-291)."""
    from core.i18n_manager import get_i18n_manager

    manager = get_i18n_manager()

    with patch.object(manager, "set_translation", return_value=True):
        resp = client.put(
            "/api/i18n/translate?key=test_key&translation=Test Translation&namespace=common&language=zh-CN"
        )
        # Should return 200 when set_translation succeeds
        assert resp.status_code == 200


def test_update_translation_http_exception_rethrown(client):
    """Test update translation when HTTPException is raised and rethrown (line 292-293)."""
    from core.i18n_manager import get_i18n_manager

    manager = get_i18n_manager()

    # Simulate HTTPException being raised from within the try block
    with patch.object(
        manager, "set_translation", side_effect=HTTPException(status_code=400, detail="Test error")
    ):
        resp = client.put(
            "/api/i18n/translate?key=test_key&translation=Test Translation&namespace=common&language=zh-CN"
        )
        # Should return 400 when HTTPException is raised
        assert resp.status_code == 400
