# -*- coding: utf-8 -*-
"""Localization Resource Router Tests"""

import sys
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from api.localization_resource_router import (
    add_translation,
    export_translations,
    get_missing_translations,
    get_resource_status,
    get_translations,
    import_translations,
)

sys.modules["core.localization_resource_manager"] = MagicMock()


@pytest.fixture
def client():
    app = FastAPI()
    test_router = APIRouter(prefix="/api/localization", tags=["Localization"])
    test_router.add_api_route("/status", get_resource_status, methods=["GET"])
    test_router.add_api_route("/translations", get_translations, methods=["GET"])
    test_router.add_api_route("/translation/add", add_translation, methods=["POST"])
    test_router.add_api_route("/translation/export", export_translations, methods=["POST"])
    test_router.add_api_route("/translation/import", import_translations, methods=["POST"])
    test_router.add_api_route("/translations/missing", get_missing_translations, methods=["GET"])
    app.include_router(test_router)
    return TestClient(app)


class TestLocalizationResourceRouter:
    def test_get_resource_status(self, client):
        with patch("core.localization_resource_manager.get_resource_manager") as mock_manager:
            mock_instance = Mock()
            mock_instance.get_resource_summary.return_value = {
                "total_languages": 3,
                "total_translations": 1000,
            }
            mock_manager.return_value = mock_instance
            response = client.get("/api/localization/status")
            assert response.status_code == 200
            data = response.json()
            assert "status" in data

    def test_get_resource_status_error(self, client):
        with patch("core.localization_resource_manager.get_resource_manager") as mock_manager:
            mock_manager.side_effect = Exception("localization resource error")
            response = client.get("/api/localization/status")
            assert response.status_code == 500

    def test_get_translations(self, client):
        with patch("core.localization_resource_manager.get_resource_manager") as mock_manager:
            mock_instance = Mock()
            mock_instance.get_translations.return_value = {"hello": "你好", "world": "世界"}
            mock_manager.return_value = mock_instance
            response = client.get("/api/localization/translations?language=zh-CN&namespace=common")
            assert response.status_code == 200

    def test_get_translations_not_found(self, client):
        with patch("core.localization_resource_manager.get_resource_manager") as mock_manager:
            mock_instance = Mock()
            mock_instance.get_translations.return_value = None
            mock_manager.return_value = mock_instance
            response = client.get("/api/localization/translations?language=fr&namespace=common")
            assert response.status_code == 404

    def test_add_translation(self, client):
        with patch("core.localization_resource_manager.get_resource_manager") as mock_manager:
            mock_instance = Mock()
            mock_instance.add_translation.return_value = True
            mock_manager.return_value = mock_instance
            response = client.post(
                "/api/localization/translation/add",
                params={"language": "zh-CN", "namespace": "common", "key": "test", "value": "测试"},
            )
            assert response.status_code == 200

    def test_export_translations(self, client):
        with patch("core.localization_resource_manager.get_resource_manager") as mock_manager:
            mock_instance = Mock()
            mock_instance.export_translations.return_value = True
            mock_manager.return_value = mock_instance
            response = client.post(
                "/api/localization/translation/export",
                params={
                    "language": "zh-CN",
                    "namespace": "common",
                    "output_path": "/tmp/translations.json",
                },
            )
            assert response.status_code == 200

    def test_import_translations(self, client):
        with patch("core.localization_resource_manager.get_resource_manager") as mock_manager:
            mock_instance = Mock()
            mock_instance.import_translations.return_value = True
            mock_manager.return_value = mock_instance
            response = client.post(
                "/api/localization/translation/import",
                params={
                    "language": "zh-CN",
                    "namespace": "common",
                    "input_path": "/tmp/translations.json",
                },
            )
            assert response.status_code == 200

    def test_get_missing_translations(self, client):
        with patch("core.localization_resource_manager.get_resource_manager") as mock_manager:
            mock_instance = Mock()
            mock_instance.get_missing_translations.return_value = ["key1", "key2"]
            mock_manager.return_value = mock_instance
            response = client.get(
                "/api/localization/translations/missing",
                params={"source_language": "en", "target_language": "zh-CN", "namespace": "common"},
            )
            assert response.status_code == 200

    def test_get_translations_empty(self, client):
        """测试空翻译列表"""
        with patch("core.localization_resource_manager.get_resource_manager") as mock_manager:
            mock_instance = Mock()
            mock_instance.get_translations.return_value = {}
            mock_manager.return_value = mock_instance
            response = client.get("/api/localization/translations?language=zh-CN&namespace=empty")
            assert response.status_code == 404

    def test_add_translation_duplicate(self, client):
        """测试添加重复翻译"""
        with patch("core.localization_resource_manager.get_resource_manager") as mock_manager:
            mock_instance = Mock()
            mock_instance.add_translation.side_effect = ValueError("Translation already exists")
            mock_manager.return_value = mock_instance
            response = client.post(
                "/api/localization/translation/add",
                params={"language": "zh-CN", "namespace": "common", "key": "test", "value": "测试"},
            )
            assert response.status_code == 500

    def test_export_translations_error(self, client):
        """测试导出翻译失败"""
        with patch("core.localization_resource_manager.get_resource_manager") as mock_manager:
            mock_instance = Mock()
            mock_instance.export_translations.side_effect = Exception("Export failed")
            mock_manager.return_value = mock_instance
            response = client.post(
                "/api/localization/translation/export",
                params={
                    "language": "zh-CN",
                    "namespace": "common",
                    "output_path": "/tmp/translations.json",
                },
            )
            assert response.status_code == 500

    def test_import_translations_error(self, client):
        """测试导入翻译失败"""
        with patch("core.localization_resource_manager.get_resource_manager") as mock_manager:
            mock_instance = Mock()
            mock_instance.import_translations.side_effect = Exception("Import failed")
            mock_manager.return_value = mock_instance
            response = client.post(
                "/api/localization/translation/import",
                params={
                    "language": "zh-CN",
                    "namespace": "common",
                    "input_path": "/tmp/translations.json",
                },
            )
            assert response.status_code == 500

    def test_get_missing_translations_none(self, client):
        """测试无缺失翻译"""
        with patch("core.localization_resource_manager.get_resource_manager") as mock_manager:
            mock_instance = Mock()
            mock_instance.get_missing_translations.return_value = []
            mock_manager.return_value = mock_instance
            response = client.get(
                "/api/localization/translations/missing",
                params={"source_language": "en", "target_language": "zh-CN", "namespace": "common"},
            )
            assert response.status_code == 200

    def test_get_translations_with_filter(self, client):
        """测试带过滤条件的翻译查询"""
        with patch("core.localization_resource_manager.get_resource_manager") as mock_manager:
            mock_instance = Mock()
            mock_instance.get_translations.return_value = {"hello": "你好"}
            mock_manager.return_value = mock_instance
            response = client.get(
                "/api/localization/translations?language=zh-CN&namespace=common&key_prefix=hello"
            )
            assert response.status_code == 200

    def test_add_translation_invalid_language(self, client):
        """测试无效语言代码"""
        with patch("core.localization_resource_manager.get_resource_manager") as mock_manager:
            mock_instance = Mock()
            mock_instance.add_translation.side_effect = ValueError("Invalid language code")
            mock_manager.return_value = mock_instance
            response = client.post(
                "/api/localization/translation/add",
                params={
                    "language": "invalid",
                    "namespace": "common",
                    "key": "test",
                    "value": "test",
                },
            )
            assert response.status_code == 500

    def test_export_translations_format(self, client):
        """测试不同格式的导出"""
        with patch("core.localization_resource_manager.get_resource_manager") as mock_manager:
            mock_instance = Mock()
            mock_instance.export_translations.return_value = True
            mock_manager.return_value = mock_instance
            response = client.post(
                "/api/localization/translation/export",
                params={
                    "language": "zh-CN",
                    "namespace": "common",
                    "output_path": "/tmp/translations.json",
                    "format": "json",
                },
            )
            assert response.status_code == 200

    def test_import_translations_format(self, client):
        """测试不同格式的导入"""
        with patch("core.localization_resource_manager.get_resource_manager") as mock_manager:
            mock_instance = Mock()
            mock_instance.import_translations.return_value = True
            mock_manager.return_value = mock_instance
            response = client.post(
                "/api/localization/translation/import",
                params={
                    "language": "zh-CN",
                    "namespace": "common",
                    "input_path": "/tmp/translations.json",
                    "format": "json",
                },
            )
            assert response.status_code == 200

    def test_get_translations_multiple_namespaces(self, client):
        """测试多命名空间翻译"""
        with patch("core.localization_resource_manager.get_resource_manager") as mock_manager:
            mock_instance = Mock()
            mock_instance.get_translations.return_value = {"key1": "value1"}
            mock_manager.return_value = mock_instance
            response = client.get("/api/localization/translations?language=zh-CN&namespace=admin")
            assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
