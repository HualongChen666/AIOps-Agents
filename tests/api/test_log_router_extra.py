# -*- coding: utf-8 -*-
"""补充测试：覆盖 api/log_router.py 遗漏的校验、异常和缓存分支。"""

import re
import sys
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

sys.modules["core.authentication"] = Mock()
sys.modules["core.authentication"].get_current_active_user = lambda: {"role": "admin"}
sys.modules["core.authentication"].role_required = Mock(return_value=lambda: {"role": "admin"})

sample_log = [{"time": "2026-07-02T10:30:00Z", "level": "Error", "message": "test"}]
sys.modules["core.log_collector"] = Mock()
sys.modules["core.log_collector"].get_system_errors = AsyncMock(return_value=sample_log)
sys.modules["core.log_collector"].get_application_errors = AsyncMock(return_value=sample_log)
sys.modules["core.log_collector"].get_event_logs = AsyncMock(return_value=sample_log)
sys.modules["core.log_collector"].search_logs = AsyncMock(return_value=sample_log)
sys.modules["core.log_collector"].get_linux_errors = AsyncMock(return_value=sample_log)
sys.modules["core.log_collector"].get_linux_logs = AsyncMock(return_value=sample_log)
sys.modules["core.log_collector"].search_linux_logs = AsyncMock(return_value=sample_log)

sys.modules["core.es_logger"] = Mock()
sys.modules["core.es_logger"].es_search_logs = AsyncMock(
    return_value=[{"@timestamp": "2026-07-02T10:30:00Z", "message": "test"}]
)

sys.modules["config"] = Mock()
sys.modules["config"].LINUX_HOSTS = []

from api.log_router import router  # noqa: E402

VALID_HOST_RE = re.compile(r"^[a-zA-Z0-9._:-]+$")
HOST_CONFIG = {"host": "test", "ip": "1.2.3.4"}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr("api.log_router.VALID_HOSTNAME_PATTERN", VALID_HOST_RE)
    monkeypatch.setattr("api.log_router._log_cache", {})
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


class TestLogRouterExtra:
    """覆盖 _get_linux_host 校验、各端点异常及 Linux 缓存分支。"""

    def test_linux_errors_invalid_hostname(self, client, monkeypatch):
        monkeypatch.setattr("api.log_router.LINUX_HOSTS", [HOST_CONFIG])
        response = client.get("/api/v1/logs/linux/errors?host_name=bad host&newest=10")
        assert response.status_code == 422

    def test_linux_errors_host_not_found(self, client, monkeypatch):
        monkeypatch.setattr("api.log_router.LINUX_HOSTS", [HOST_CONFIG])
        monkeypatch.setattr("api.linux_router.find_linux_host_config", lambda _: None)
        response = client.get("/api/v1/logs/linux/errors?host_name=missing&newest=10")
        assert response.status_code == 404

    def test_linux_errors_success_and_cache(self, client, monkeypatch):
        monkeypatch.setattr("api.log_router.LINUX_HOSTS", [HOST_CONFIG])
        monkeypatch.setattr(
            "api.linux_router.find_linux_host_config", lambda _: HOST_CONFIG
        )
        response1 = client.get("/api/v1/logs/linux/errors?host_name=test&newest=10")
        assert response1.status_code == 200
        assert response1.json()["cached"] is False

        response2 = client.get("/api/v1/logs/linux/errors?host_name=test&newest=10")
        assert response2.status_code == 200
        assert response2.json()["cached"] is True

    def test_linux_errors_http_exception_reraise(self, client, monkeypatch):
        monkeypatch.setattr("api.log_router.LINUX_HOSTS", [HOST_CONFIG])
        monkeypatch.setattr(
            "api.linux_router.find_linux_host_config", lambda _: HOST_CONFIG
        )
        monkeypatch.setattr(
            "api.log_router.get_linux_errors",
            AsyncMock(side_effect=HTTPException(status_code=502, detail="ssh fail")),
        )
        response = client.get("/api/v1/logs/linux/errors?host_name=test&newest=10")
        assert response.status_code == 502

    def test_linux_errors_runtime_error_500(self, client, monkeypatch):
        monkeypatch.setattr("api.log_router.LINUX_HOSTS", [HOST_CONFIG])
        monkeypatch.setattr(
            "api.linux_router.find_linux_host_config", lambda _: HOST_CONFIG
        )
        monkeypatch.setattr(
            "api.log_router.get_linux_errors",
            AsyncMock(side_effect=RuntimeError("boom")),
        )
        response = client.get("/api/v1/logs/linux/errors?host_name=test&newest=10")
        assert response.status_code == 500

    def test_linux_query_success_and_500(self, client, monkeypatch):
        monkeypatch.setattr("api.log_router.LINUX_HOSTS", [HOST_CONFIG])
        monkeypatch.setattr(
            "api.linux_router.find_linux_host_config", lambda _: HOST_CONFIG
        )
        response = client.get(
            "/api/v1/logs/linux/query?host_name=test&source=syslog&newest=20"
        )
        assert response.status_code == 200

        monkeypatch.setattr(
            "api.log_router.get_linux_logs",
            AsyncMock(side_effect=RuntimeError("boom")),
        )
        response = client.get(
            "/api/v1/logs/linux/query?host_name=test&source=syslog&newest=20"
        )
        assert response.status_code == 500

    def test_linux_search_success_and_500(self, client, monkeypatch):
        monkeypatch.setattr("api.log_router.LINUX_HOSTS", [HOST_CONFIG])
        monkeypatch.setattr(
            "api.linux_router.find_linux_host_config", lambda _: HOST_CONFIG
        )
        response = client.get(
            "/api/v1/logs/linux/search?host_name=test&keyword=err&newest=100"
        )
        assert response.status_code == 200

        monkeypatch.setattr(
            "api.log_router.search_linux_logs",
            AsyncMock(side_effect=RuntimeError("boom")),
        )
        response = client.get(
            "/api/v1/logs/linux/search?host_name=test&keyword=err&newest=100"
        )
        assert response.status_code == 500

    def test_system_errors_failure_500(self, client, monkeypatch):
        monkeypatch.setattr(
            "api.log_router.get_system_errors",
            AsyncMock(side_effect=Exception("boom")),
        )
        response = client.get("/api/v1/logs/system/errors?newest=10")
        assert response.status_code == 500

    def test_app_errors_failure_500(self, client, monkeypatch):
        monkeypatch.setattr(
            "api.log_router.get_application_errors",
            AsyncMock(side_effect=Exception("boom")),
        )
        response = client.get("/api/v1/logs/application/errors?newest=10")
        assert response.status_code == 500

    def test_query_logs_failure_500(self, client, monkeypatch):
        monkeypatch.setattr(
            "api.log_router.get_event_logs",
            AsyncMock(side_effect=Exception("boom")),
        )
        response = client.get("/api/v1/logs/query?log_name=System&level=Error&newest=20")
        assert response.status_code == 500

    def test_search_failure_500(self, client, monkeypatch):
        monkeypatch.setattr(
            "api.log_router.search_logs",
            AsyncMock(side_effect=Exception("boom")),
        )
        response = client.get("/api/v1/logs/search?keyword=err&newest=10")
        assert response.status_code == 500
