# -*- coding: utf-8 -*-
"""Localization Adapter Router Tests"""

import sys
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from api.localization_adapter_router import (
    format_currency,
    format_date,
    format_datetime,
    format_number,
    format_unit,
    get_adapter_status,
    get_supported_locales,
    set_current_locale,
)

sys.modules["core.localization_adapter"] = MagicMock()


@pytest.fixture
def client():
    app = FastAPI()
    test_router = APIRouter(prefix="/api/localization-adapter", tags=["Localization Adapter"])
    test_router.add_api_route("/status", get_adapter_status, methods=["GET"])
    test_router.add_api_route("/locales", get_supported_locales, methods=["GET"])
    test_router.add_api_route("/locale/set", set_current_locale, methods=["POST"])
    test_router.add_api_route("/format/date", format_date, methods=["GET"])
    test_router.add_api_route("/format/datetime", format_datetime, methods=["GET"])
    test_router.add_api_route("/format/number", format_number, methods=["GET"])
    test_router.add_api_route("/format/currency", format_currency, methods=["GET"])
    test_router.add_api_route("/format/unit", format_unit, methods=["GET"])
    app.include_router(test_router)
    return TestClient(app)


class TestLocalizationAdapterRouter:
    def test_get_adapter_status(self, client):
        with patch("core.localization_adapter.get_localization_adapter") as mock_adapter:
            mock_instance = Mock()
            mock_instance.get_adapter_summary.return_value = {
                "available": True,
                "current_locale": "zh-CN",
            }
            mock_adapter.return_value = mock_instance
            response = client.get("/api/localization-adapter/status")
            assert response.status_code == 200
            data = response.json()
            assert "status" in data

    def test_get_adapter_status_error(self, client):
        with patch("core.localization_adapter.get_localization_adapter") as mock_adapter:
            mock_adapter.side_effect = Exception("localization adapter error")
            response = client.get("/api/localization-adapter/status")
            assert response.status_code == 500

    def test_get_supported_locales(self, client):
        with patch("core.localization_adapter.get_localization_adapter") as mock_adapter:
            mock_instance = Mock()
            mock_instance.get_supported_locales.return_value = ["zh-CN", "en-US", "ja-JP"]
            mock_adapter.return_value = mock_instance
            response = client.get("/api/localization-adapter/locales")
            assert response.status_code == 200

    def test_set_current_locale(self, client):
        with patch("core.localization_adapter.get_localization_adapter") as mock_adapter:
            mock_instance = Mock()
            mock_instance.set_current_locale.return_value = True
            mock_adapter.return_value = mock_instance
            response = client.post("/api/localization-adapter/locale/set?locale_id=zh-CN")
            assert response.status_code == 200

    def test_format_date(self, client):
        with patch("core.localization_adapter.get_localization_adapter") as mock_adapter:
            mock_instance = Mock()
            mock_instance.format_date.return_value = "2026年7月3日"
            mock_adapter.return_value = mock_instance
            response = client.get(
                "/api/localization-adapter/format/date",
                params={"date_str": "2026-07-03", "format_type": "short", "locale": "zh-CN"},
            )
            assert response.status_code == 200

    def test_format_datetime(self, client):
        with patch("core.localization_adapter.get_localization_adapter") as mock_adapter:
            mock_instance = Mock()
            mock_instance.format_datetime.return_value = "2026年7月3日 09:00:00"
            mock_adapter.return_value = mock_instance
            response = client.get(
                "/api/localization-adapter/format/datetime",
                params={
                    "datetime_str": "2026-07-03T09:00:00Z",
                    "format_type": "full",
                    "locale": "zh-CN",
                },
            )
            assert response.status_code == 200

    def test_format_number(self, client):
        with patch("core.localization_adapter.get_localization_adapter") as mock_adapter:
            mock_instance = Mock()
            mock_instance.format_number.return_value = "1,234.56"
            mock_adapter.return_value = mock_instance
            response = client.get(
                "/api/localization-adapter/format/number",
                params={"number": "1234.56", "format_type": "decimal", "locale": "en-US"},
            )
            assert response.status_code == 200

    def test_format_currency(self, client):
        with patch("core.localization_adapter.get_localization_adapter") as mock_adapter:
            mock_instance = Mock()
            mock_instance.format_currency.return_value = "$1,234.56"
            mock_adapter.return_value = mock_instance
            response = client.get(
                "/api/localization-adapter/format/currency",
                params={"amount": "1234.56", "currency_code": "USD", "locale": "en-US"},
            )
            assert response.status_code == 200

    def test_format_unit(self, client):
        with patch("core.localization_adapter.get_localization_adapter") as mock_adapter:
            mock_instance = Mock()
            mock_instance.format_unit.return_value = "1.23 km"
            mock_adapter.return_value = mock_instance
            response = client.get(
                "/api/localization-adapter/format/unit",
                params={
                    "value": "1.23",
                    "unit": "km",
                    "target_system": "metric",
                    "locale": "en-US",
                },
            )
            assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
