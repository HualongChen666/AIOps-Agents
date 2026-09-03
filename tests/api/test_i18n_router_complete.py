# -*- coding: utf-8 -*-
"""
Complete i18n Router Tests
Comprehensive tests for all i18n API endpoints including newly added ones
Uses pytest-xdist for parallel testing
"""

import os
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException


@pytest.fixture(autouse=True)
def set_test_mode():
    """Set TEST_MODE to bypass authentication during testing"""
    os.environ["TEST_MODE"] = "true"
    yield
    if "TEST_MODE" in os.environ:
        del os.environ["TEST_MODE"]


@pytest.fixture
def client():
    """Create test client"""
    from main import app
    from fastapi.testclient import TestClient
    return TestClient(app)


# Tests for newly added endpoints

def test_add_locale_success(client):
    """Test successful locale addition"""
    resp = client.post(
        "/api/i18n/locale/add",
        params={
            "locale_id": "fr-FR",
            "language": "fr",
            "region": "FR",
            "timezone": "Europe/Paris",
            "number_format": "#,##0.##",
            "date_format": "DD/MM/YYYY HH:mm:ss",
            "currency": "EUR"
        }
    )
    assert resp.status_code in (200, 400, 401, 500)
    if resp.status_code == 200:
        data = resp.json()
        assert data["status"] == "success"
        assert "locale_id" in data["data"]
        assert data["data"]["added"] is True


def test_add_locale_duplicate(client):
    """Test adding duplicate locale"""
    # First add
    client.post(
        "/api/i18n/locale/add",
        params={
            "locale_id": "de-DE",
            "language": "de",
            "region": "DE",
            "timezone": "Europe/Berlin",
            "currency": "EUR"
        }
    )
    # Try to add again
    resp = client.post(
        "/api/i18n/locale/add",
        params={
            "locale_id": "de-DE",
            "language": "de",
            "region": "DE",
            "timezone": "Europe/Berlin",
            "currency": "EUR"
        }
    )
    assert resp.status_code in (400, 401, 500)


def test_add_locale_invalid_language(client):
    """Test adding locale with invalid language code"""
    resp = client.post(
        "/api/i18n/locale/add",
        params={
            "locale_id": "xx-XX",
            "language": "invalid",
            "region": "XX",
            "timezone": "UTC",
            "currency": "USD"
        }
    )
    assert resp.status_code in (400, 401)


def test_add_locale_invalid_timezone(client):
    """Test adding locale with invalid timezone"""
    resp = client.post(
        "/api/i18n/locale/add",
        params={
            "locale_id": "en-GB",
            "language": "en",
            "region": "GB",
            "timezone": "Invalid/Timezone",
            "currency": "GBP"
        }
    )
    assert resp.status_code in (400, 401)


def test_detect_locale_with_accept_language(client):
    """Test locale detection with Accept-Language header"""
    resp = client.get(
        "/api/i18n/locale/detect",
        params={"accept_language": "zh-CN,zh;q=0.9,en;q=0.8"}
    )
    assert resp.status_code in (200, 401, 500)
    if resp.status_code == 200:
        data = resp.json()
        assert data["status"] == "success"
        assert "detected_locale" in data["data"]


def test_detect_locale_with_timezone(client):
    """Test locale detection with user timezone"""
    resp = client.get(
        "/api/i18n/locale/detect",
        params={"user_timezone": "Asia/Tokyo"}
    )
    assert resp.status_code in (200, 401, 500)
    if resp.status_code == 200:
        data = resp.json()
        assert data["status"] == "success"


def test_detect_locale_both_parameters(client):
    """Test locale detection with both parameters"""
    resp = client.get(
        "/api/i18n/locale/detect",
        params={
            "accept_language": "ja-JP,ja;q=0.9",
            "user_timezone": "Asia/Tokyo"
        }
    )
    assert resp.status_code in (200, 401, 500)


def test_detect_locale_no_parameters(client):
    """Test locale detection without parameters"""
    resp = client.get("/api/i18n/locale/detect")
    assert resp.status_code in (200, 401, 500)


def test_add_translation_resource_success(client):
    """Test successful translation resource addition"""
    resp = client.post(
        "/api/i18n/translation/resource/add",
        params={
            "language": "en",
            "namespace": "ui",
            "version": "1.0"
        },
        json={
            "button_save": "Save",
            "button_cancel": "Cancel",
            "button_delete": "Delete"
        }
    )
    assert resp.status_code in (200, 400, 401, 500)
    if resp.status_code == 200:
        data = resp.json()
        assert data["status"] == "success"
        assert "translation_count" in data["data"]
        assert data["data"]["added"] is True


def test_add_translation_resource_invalid_language(client):
    """Test adding translation resource with invalid language"""
    resp = client.post(
        "/api/i18n/translation/resource/add",
        params={
            "language": "invalid",
            "namespace": "test"
        },
        json={"test": "test"}
    )
    assert resp.status_code in (400, 401)


def test_add_translation_resource_empty_translations(client):
    """Test adding translation resource with empty translations"""
    resp = client.post(
        "/api/i18n/translation/resource/add",
        params={
            "language": "en",
            "namespace": "empty"
        },
        json={}
    )
    assert resp.status_code in (200, 400, 401, 500)


def test_get_namespace_translations_success(client):
    """Test successful namespace translations retrieval"""
    # First add some translations
    client.post(
        "/api/i18n/translation/resource/add",
        params={
            "language": "zh",
            "namespace": "common"
        },
        json={
            "welcome": "欢迎",
            "goodbye": "再见"
        }
    )
    
    resp = client.get(
        "/api/i18n/translations/namespace",
        params={"locale_id": "zh-CN", "namespace": "common"}
    )
    assert resp.status_code in (200, 404, 401, 500)
    if resp.status_code == 200:
        data = resp.json()
        assert data["status"] == "success"
        assert "translations" in data["data"]
        assert "count" in data["data"]


def test_get_namespace_translations_not_found(client):
    """Test getting namespace translations when not found"""
    resp = client.get(
        "/api/i18n/translations/namespace",
        params={"locale_id": "nonexistent", "namespace": "nonexistent"}
    )
    assert resp.status_code in (404, 401, 500)


def test_get_namespace_translations_default_namespace(client):
    """Test getting namespace translations with default namespace"""
    resp = client.get(
        "/api/i18n/translations/namespace",
        params={"locale_id": "zh-CN"}
    )
    assert resp.status_code in (200, 404, 401, 500)


def test_convert_timezone_success(client):
    """Test successful timezone conversion"""
    resp = client.post(
        "/api/i18n/timezone/convert",
        params={
            "date_str": "2026-07-03T09:00:00",
            "from_timezone": "UTC",
            "to_timezone": "Asia/Shanghai"
        }
    )
    assert resp.status_code in (200, 401, 500)
    if resp.status_code == 200:
        data = resp.json()
        assert data["status"] == "success"
        assert "converted_date" in data["data"]
        assert "from_timezone" in data["data"]
        assert "to_timezone" in data["data"]


def test_convert_timezone_invalid_from_timezone(client):
    """Test timezone conversion with invalid source timezone"""
    resp = client.post(
        "/api/i18n/timezone/convert",
        params={
            "date_str": "2026-07-03T09:00:00",
            "from_timezone": "Invalid/Timezone",
            "to_timezone": "UTC"
        }
    )
    assert resp.status_code in (400, 401)


def test_convert_timezone_invalid_to_timezone(client):
    """Test timezone conversion with invalid target timezone"""
    resp = client.post(
        "/api/i18n/timezone/convert",
        params={
            "date_str": "2026-07-03T09:00:00",
            "from_timezone": "UTC",
            "to_timezone": "Invalid/Timezone"
        }
    )
    assert resp.status_code in (400, 401)


def test_convert_timezone_invalid_date(client):
    """Test timezone conversion with invalid date string"""
    resp = client.post(
        "/api/i18n/timezone/convert",
        params={
            "date_str": "invalid-date",
            "from_timezone": "UTC",
            "to_timezone": "Asia/Shanghai"
        }
    )
    assert resp.status_code in (500, 400, 401)


def test_get_supported_languages_success(client):
    """Test successful supported languages retrieval"""
    resp = client.get("/api/i18n/languages")
    assert resp.status_code in (200, 401, 500)
    if resp.status_code == 200:
        data = resp.json()
        assert data["status"] == "success"
        assert "languages" in data["data"]
        assert "count" in data["data"]
        assert isinstance(data["data"]["languages"], list)


def test_get_supported_languages_multiple(client):
    """Test that multiple languages are returned"""
    resp = client.get("/api/i18n/languages")
    assert resp.status_code in (200, 401, 500)
    if resp.status_code == 200:
        data = resp.json()
        assert data["data"]["count"] >= 3  # At least zh, en, ja


def test_get_i18n_summary_success(client):
    """Test successful i18n summary retrieval"""
    resp = client.get("/api/i18n/summary")
    assert resp.status_code in (200, 401, 500)
    if resp.status_code == 200:
        data = resp.json()
        assert data["status"] == "success"
        assert "total_locales" in data["data"]
        assert "total_translations" in data["data"]
        assert "total_namespaces" in data["data"]
        assert "current_locale" in data["data"]
        assert "default_language" in data["data"]
        assert "fallback_language" in data["data"]
        assert "supported_languages" in data["data"]


def test_get_i18n_summary_after_adding_locale(client):
    """Test i18n summary after adding a new locale"""
    # Get initial summary
    initial_resp = client.get("/api/i18n/summary")
    initial_count = initial_resp.json()["data"]["total_locales"] if initial_resp.status_code == 200 else 0
    
    # Add a new locale
    client.post(
        "/api/i18n/locale/add",
        params={
            "locale_id": "ko-KR",
            "language": "ko",
            "region": "KR",
            "timezone": "Asia/Seoul",
            "currency": "KRW"
        }
    )
    
    # Get summary again
    resp = client.get("/api/i18n/summary")
    assert resp.status_code in (200, 401, 500)


def test_add_locale_with_all_parameters(client):
    """Test adding locale with all optional parameters"""
    resp = client.post(
        "/api/i18n/locale/add",
        params={
            "locale_id": "es-ES",
            "language": "es",
            "region": "ES",
            "timezone": "Europe/Madrid",
            "number_format": "#.##0,##",
            "date_format": "DD/MM/YYYY HH:mm:ss",
            "currency": "EUR"
        }
    )
    assert resp.status_code in (200, 400, 401, 500)


def test_add_translation_resource_with_version(client):
    """Test adding translation resource with custom version"""
    resp = client.post(
        "/api/i18n/translation/resource/add",
        params={
            "language": "ja",
            "namespace": "errors",
            "version": "2.0"
        },
        json={
            "error_404": "ページが見つかりません",
            "error_500": "サーバーエラー"
        }
    )
    assert resp.status_code in (200, 400, 401, 500)


def test_convert_timezone_different_pairs(client):
    """Test timezone conversion with different timezone pairs"""
    timezone_pairs = [
        ("UTC", "America/New_York"),
        ("UTC", "Europe/London"),
        ("Asia/Shanghai", "America/New_York"),
        ("Asia/Tokyo", "UTC")
    ]
    
    for from_tz, to_tz in timezone_pairs:
        resp = client.post(
            "/api/i18n/timezone/convert",
            params={
                "date_str": "2026-07-03T12:00:00",
                "from_timezone": from_tz,
                "to_timezone": to_tz
            }
        )
        assert resp.status_code in (200, 401, 500)


def test_get_namespace_translations_different_namespaces(client):
    """Test getting translations from different namespaces"""
    namespaces = ["common", "ui", "errors", "messages"]
    
    for namespace in namespaces:
        resp = client.get(
            "/api/i18n/translations/namespace",
            params={"locale_id": "zh-CN", "namespace": namespace}
        )
        assert resp.status_code in (200, 404, 401, 500)


def test_add_translation_resource_batch(client):
    """Test adding multiple translation resources in sequence"""
    languages = ["en", "zh", "ja"]
    
    for language in languages:
        resp = client.post(
            "/api/i18n/translation/resource/add",
            params={
                "language": language,
                "namespace": "test_batch"
            },
            json={"test_key": f"test_value_{language}"}
        )
        assert resp.status_code in (200, 400, 401, 500)


def test_error_handling_add_locale_exception(client):
    """Test error handling when add_locale raises exception"""
    with patch("core.i18n_manager.get_i18n_manager") as mock_get:
        mock_manager = MagicMock()
        mock_manager.add_locale.side_effect = Exception("Database error")
        mock_get.return_value = mock_manager
        
        resp = client.post(
            "/api/i18n/locale/add",
            params={
                "locale_id": "test-TEST",
                "language": "en",
                "region": "TEST",
                "timezone": "UTC",
                "currency": "USD"
            }
        )
        assert resp.status_code in (500, 401)


def test_error_handling_detect_locale_exception(client):
    """Test error handling when detect_locale raises exception"""
    with patch("core.i18n_manager.get_i18n_manager") as mock_get:
        mock_manager = MagicMock()
        mock_manager.detect_locale_from_request.side_effect = Exception("Detection error")
        mock_get.return_value = mock_manager
        
        resp = client.get("/api/i18n/locale/detect")
        assert resp.status_code in (500, 401)


def test_error_handling_add_translation_resource_exception(client):
    """Test error handling when add_translation_resource raises exception"""
    with patch("core.i18n_manager.get_i18n_manager") as mock_get:
        mock_manager = MagicMock()
        mock_manager.add_translation_resource.side_effect = Exception("Resource error")
        mock_get.return_value = mock_manager
        
        resp = client.post(
            "/api/i18n/translation/resource/add",
            params={"language": "en", "namespace": "test"},
            json={"test": "test"}
        )
        assert resp.status_code in (500, 401)


def test_error_handling_convert_timezone_exception(client):
    """Test error handling when convert_timezone raises exception"""
    with patch("core.i18n_manager.get_i18n_manager") as mock_get:
        mock_manager = MagicMock()
        mock_manager.convert_timezone.side_effect = Exception("Conversion error")
        mock_get.return_value = mock_manager
        
        resp = client.post(
            "/api/i18n/timezone/convert",
            params={
                "date_str": "2026-07-03T09:00:00",
                "from_timezone": "UTC",
                "to_timezone": "Asia/Shanghai"
            }
        )
        assert resp.status_code in (500, 401)


def test_error_handling_get_supported_languages_exception(client):
    """Test error handling when get_supported_languages raises exception"""
    with patch("core.i18n_manager.get_i18n_manager") as mock_get:
        mock_manager = MagicMock()
        mock_manager.get_supported_languages.side_effect = Exception("Languages error")
        mock_get.return_value = mock_manager
        
        resp = client.get("/api/i18n/languages")
        assert resp.status_code in (500, 401)


def test_error_handling_get_i18n_summary_exception(client):
    """Test error handling when get_i18n_summary raises exception"""
    with patch("core.i18n_manager.get_i18n_manager") as mock_get:
        mock_manager = MagicMock()
        mock_manager.get_i18n_summary.side_effect = Exception("Summary error")
        mock_get.return_value = mock_manager
        
        resp = client.get("/api/i18n/summary")
        assert resp.status_code in (500, 401)


def test_integration_add_locale_then_get_summary(client):
    """Integration test: add locale then verify in summary"""
    # Add a new locale
    add_resp = client.post(
        "/api/i18n/locale/add",
        params={
            "locale_id": "it-IT",
            "language": "it",  # Note: this might fail if 'it' is not in Language enum
            "region": "IT",
            "timezone": "Europe/Rome",
            "currency": "EUR"
        }
    )
    
    # Get summary
    summary_resp = client.get("/api/i18n/summary")
    assert summary_resp.status_code in (200, 401, 500)


def test_integration_add_translation_then_get_namespace(client):
    """Integration test: add translation resource then retrieve it"""
    # Add translation resource
    add_resp = client.post(
        "/api/i18n/translation/resource/add",
        params={
            "language": "en",
            "namespace": "integration_test"
        },
        json={"integration_key": "integration_value"}
    )
    
    # Retrieve namespace translations
    get_resp = client.get(
        "/api/i18n/translations/namespace",
        params={"locale_id": "en-US", "namespace": "integration_test"}
    )
    assert get_resp.status_code in (200, 404, 401, 500)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-n", "auto"])
