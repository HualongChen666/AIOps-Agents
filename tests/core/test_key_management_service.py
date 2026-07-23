# -*- coding: utf-8 -*-
"""测试密钥管理服务模块"""

import pytest

import core.key_management_service as kms
from core.key_management_service import (
    EnvironmentKeyBackend,
    FileKeyBackend,
    KeyManagementService,
    get_key_service,
    initialize_key_management,
)


@pytest.fixture(autouse=True)
def reset_global():
    kms._global_key_service = None
    yield
    kms._global_key_service = None


class TestEnvironmentBackend:
    def test_get_set_delete_key(self, monkeypatch):
        backend = EnvironmentKeyBackend()
        monkeypatch.setenv("AIOPS_MYKEY", "secret")
        assert backend.get_key("mykey") == "secret"
        assert backend.set_key("mykey2", "value2") is True
        assert backend.key_exists("mykey2") is True
        assert backend.get_key("mykey2") == "value2"
        assert backend.delete_key("mykey2") is True
        assert backend.key_exists("mykey2") is False

    def test_get_key_without_prefix(self, monkeypatch):
        backend = EnvironmentKeyBackend()
        monkeypatch.setenv("plain_key", "plain_value")
        assert backend.get_key("plain_key") == "plain_value"

    def test_delete_missing_key(self):
        backend = EnvironmentKeyBackend()
        assert backend.delete_key("nonexistent") is False


class TestFileBackend:
    def test_load_missing_file(self, tmp_path):
        backend = FileKeyBackend(str(tmp_path / "missing.json"))
        assert backend.key_exists("x") is False

    def test_save_load_delete(self, tmp_path):
        path = tmp_path / "secrets.json"
        backend = FileKeyBackend(str(path))
        assert backend.set_key("a", "1") is True
        assert backend.get_key("a") == "1"

        backend2 = FileKeyBackend(str(path))
        assert backend2.get_key("a") == "1"
        assert backend2.delete_key("a") is True
        assert backend2.get_key("a") is None

    def test_load_invalid_json(self, tmp_path):
        path = tmp_path / "secrets.json"
        path.write_text("not-json", encoding="utf-8")
        backend = FileKeyBackend(str(path))
        assert backend.get_key("a") is None

    def test_delete_missing_key(self, tmp_path):
        backend = FileKeyBackend(str(tmp_path / "secrets.json"))
        assert backend.delete_key("missing") is False


class TestKeyManagementService:
    def test_create_invalid_backend(self):
        with pytest.raises(ValueError, match="Unsupported backend"):
            KeyManagementService("unknown")

    def test_get_required_missing(self):
        service = KeyManagementService("environment")
        with pytest.raises(ValueError, match="not found"):
            service.get_key("nonexistent", required=True)

    def test_get_default(self):
        service = KeyManagementService("environment")
        assert service.get_key("nonexistent", default="fallback") == "fallback"

    def test_set_delete_exists(self, monkeypatch, tmp_path):
        path = tmp_path / "secrets.json"
        service = KeyManagementService("file", file_path=str(path))
        assert service.set_key("k", "v") is True
        assert service.key_exists("k") is True
        assert service.get_key("k") == "v"
        assert service.delete_key("k") is True
        assert service.key_exists("k") is False

    def test_convenience_methods(self, monkeypatch):
        monkeypatch.setenv("AIOPS_JWT_SECRET_KEY", "jwt")
        monkeypatch.setenv("AIOPS_DATABASE_PASSWORD", "db")
        monkeypatch.setenv("AIOPS_OPENAI_API_KEY", "openai")

        service = KeyManagementService("environment")
        assert service.get_jwt_secret_key() == "jwt"
        assert service.get_database_password() == "db"
        assert service.get_api_key("openai") == "openai"

    def test_required_jwt_missing(self):
        service = KeyManagementService("environment")
        with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
            service.get_jwt_secret_key(required=True)

    def test_cache_hit_and_expiry(self, monkeypatch):
        service = KeyManagementService("environment", cache_ttl=0)
        monkeypatch.setenv("AIOPS_TEST_KEY", "test")
        assert service.get_key_with_cache("test_key", use_cache=True) == "test"
        assert service.get_key_with_cache("test_key", use_cache=True) == "test"
        # expired cache
        monkeypatch.setenv("AIOPS_TEST_KEY", "new")
        assert service.get_key_with_cache("test_key", use_cache=True) == "new"

    def test_rotate_and_cleanup(self, tmp_path):
        path = tmp_path / "secrets.json"
        service = KeyManagementService("file", file_path=str(path))
        service.set_key("rotate", "old")

        # retention=0 should schedule immediate expiry
        assert service.rotate_key("rotate", "new", old_value_retention=0) is True
        assert service.get_key("rotate") == "new"

        # cleanup_old_keys should remove old key
        assert service.cleanup_old_keys() >= 1

    def test_clear_cache_and_stats(self):
        service = KeyManagementService("environment")
        service._cache_key("x", "y")
        stats = service.get_cache_stats()
        assert stats["cached_keys"] == 1

        service.clear_cache()
        assert service.get_cache_stats()["cached_keys"] == 0


class TestFactory:
    def test_get_key_service_singleton(self):
        s1 = get_key_service("environment")
        s2 = get_key_service("environment")
        assert s1 is s2

    def test_initialize_key_management(self):
        initialize_key_management("environment")
        assert kms._global_key_service is not None
