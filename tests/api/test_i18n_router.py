# -*- coding: utf-8 -*-
"""i18n Router Tests"""

import sys
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from api.i18n_router import (
    format_currency,
    format_date,
    format_number,
    get_i18n_status,
    get_locale_info,
    get_supported_locales,
    set_current_locale,
    translate,
)

sys.modules["core.i18n_manager"] = MagicMock()


@pytest.fixture
def client():
    app = FastAPI()
    test_router = APIRouter(prefix="/api/i18n", tags=["Internationalization"])
    test_router.add_api_route("/status", get_i18n_status, methods=["GET"])
    test_router.add_api_route("/locales", get_supported_locales, methods=["GET"])
    test_router.add_api_route("/locales/{locale_id}", get_locale_info, methods=["GET"])
    test_router.add_api_route("/locale/set", set_current_locale, methods=["POST"])
    test_router.add_api_route("/translate", translate, methods=["GET"])
    test_router.add_api_route("/format/number", format_number, methods=["GET"])
    test_router.add_api_route("/format/currency", format_currency, methods=["GET"])
    test_router.add_api_route("/format/date", format_date, methods=["GET"])
    app.include_router(test_router)
    return TestClient(app)


class TestI18nRouter:
    def test_get_i18n_status(self, client):
        with patch("core.i18n_manager.get_i18n_manager") as mock_manager:
            mock_instance = Mock()
            mock_instance.get_i18n_summary.return_value = {
                "enabled": True,
                "default_locale": "zh-CN",
                "total_locales": 5,
            }
            mock_manager.return_value = mock_instance
            response = client.get("/api/i18n/status")
            assert response.status_code == 200
            data = response.json()
            assert "status" in data

    def test_get_i18n_status_error(self, client):
        with patch("core.i18n_manager.get_i18n_manager") as mock_manager:
            mock_manager.side_effect = Exception("i18n error")
            response = client.get("/api/i18n/status")
            assert response.status_code == 500

    def test_get_supported_locales(self, client):
        with patch("core.i18n_manager.get_i18n_manager") as mock_manager:
            mock_instance = Mock()
            mock_instance.get_supported_locales.return_value = ["zh-CN", "en-US", "ja-JP"]
            mock_manager.return_value = mock_instance
            response = client.get("/api/i18n/locales")
            assert response.status_code == 200

    def test_get_locale_info(self, client):
        with patch("core.i18n_manager.get_i18n_manager") as mock_manager:
            mock_instance = Mock()
            mock_instance.get_supported_locales.return_value = ["zh-CN"]
            mock_manager.return_value = mock_instance
            response = client.get("/api/i18n/locales/zh-CN")
            assert response.status_code == 200

    def test_set_current_locale(self, client):
        with patch("core.i18n_manager.get_i18n_manager") as mock_manager:
            mock_instance = Mock()
            mock_instance.set_current_locale.return_value = True
            mock_manager.return_value = mock_instance
            response = client.post("/api/i18n/locale/set?locale_id=zh-CN")
            assert response.status_code == 200

    def test_translate(self, client):
        with patch("core.i18n_manager.get_i18n_manager") as mock_manager:
            mock_instance = Mock()
            mock_instance.translate.return_value = "欢迎使用"
            mock_manager.return_value = mock_instance
            response = client.get("/api/i18n/translate?key=welcome&namespace=common&language=zh-CN")
            assert response.status_code == 200

    def test_format_number(self, client):
        with patch("core.i18n_manager.get_i18n_manager") as mock_manager:
            mock_instance = Mock()
            mock_instance.format_number.return_value = "1,234.56"
            mock_instance.locales = {}
            mock_manager.return_value = mock_instance
            response = client.get("/api/i18n/format/number?number=1234.56&locale=en-US")
            assert response.status_code == 200

    def test_format_currency(self, client):
        with patch("core.i18n_manager.get_i18n_manager") as mock_manager:
            mock_instance = Mock()
            mock_instance.format_currency.return_value = "$1,234.56"
            mock_instance.locales = {}
            mock_manager.return_value = mock_instance
            response = client.get("/api/i18n/format/currency?amount=1234.56&locale=en-US")
            assert response.status_code == 200

    def test_format_date(self, client):
        with patch("core.i18n_manager.get_i18n_manager") as mock_manager:
            mock_instance = Mock()
            mock_instance.format_date.return_value = "2026-07-03"
            mock_instance.locales = {}
            mock_manager.return_value = mock_instance
            response = client.get(
                "/api/i18n/format/date?date_str=2026-07-03T09:00:00Z&locale=en-US"
            )
            assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
