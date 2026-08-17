import importlib
import os
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest

import config


@pytest.fixture(autouse=True)
def _reload_default_config():
    yield
    for key in (
        "ENVIRONMENT",
        "POSTGRES_PASSWORD",
        "JWT_SECRET_KEY",
        "AI_ENABLED",
        "LANGFUSE_ENABLED",
        "CONFIG_HOT_RELOAD_ENABLED",
        "CONFIG_VALIDATION_ENABLED",
    ):
        os.environ.pop(key, None)
    importlib.reload(config)


def test_core_config_raises_when_spec_missing(monkeypatch):
    import core.config as core_config

    monkeypatch.setattr(core_config.importlib.util, "spec_from_file_location", lambda *a, **k: None)
    with pytest.raises(ImportError):
        importlib.reload(core_config)


def test_load_env_file_on_import(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("LOAD_DOTENV_TEST=value\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    importlib.reload(config)


def test_import_in_production(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("POSTGRES_PASSWORD", "prod-password")
    monkeypatch.setenv("JWT_SECRET_KEY", "prod-secret")
    monkeypatch.setenv("AI_ENABLED", "true")
    monkeypatch.setenv("LANGFUSE_ENABLED", "true")
    importlib.reload(config)
    assert config.ENVIRONMENT == "production"
    assert config.POSTGRES_PASSWORD == "prod-password"
    assert config.JWT_SECRET_KEY == "prod-secret"


def test_watchdog_available(monkeypatch):
    fake_events_mod = types.ModuleType("watchdog.events")
    fake_events_mod.FileSystemEventHandler = object

    class FakeObserver:
        def __init__(self):
            self.started = False

        def schedule(self, *args, **kwargs):
            return self

        def start(self):
            self.started = True

        def stop(self):
            self.started = False

        def join(self):
            pass

    fake_observers_mod = types.ModuleType("watchdog.observers")
    fake_observers_mod.Observer = FakeObserver

    monkeypatch.setitem(sys.modules, "watchdog", types.ModuleType("watchdog"))
    monkeypatch.setitem(sys.modules, "watchdog.events", fake_events_mod)
    monkeypatch.setitem(sys.modules, "watchdog.observers", fake_observers_mod)
    monkeypatch.setenv("CONFIG_HOT_RELOAD_ENABLED", "true")

    importlib.reload(config)

    assert config.WATCHDOG_AVAILABLE is True
    assert config.is_config_hot_reload_enabled() is True
    assert isinstance(config._config_reload_handler, config.ConfigReloadHandler)

    handler = config.ConfigReloadHandler("os")
    calls = []
    handler.set_reload_callback(lambda: calls.append(1))
    handler.on_modified(SimpleNamespace(src_path="config.py"))
    assert calls == [1]

    config.disable_config_hot_reload()
    assert config.is_config_hot_reload_enabled() is False


def test_watchdog_unavailable_handler(monkeypatch):
    monkeypatch.setitem(sys.modules, "watchdog.events", None)
    monkeypatch.setitem(sys.modules, "watchdog.observers", None)
    importlib.reload(config)
    assert config.WATCHDOG_AVAILABLE is False
    handler = config.ConfigReloadHandler()
    handler.set_reload_callback(lambda: None)
    handler.set_reload_callback("not callable")


def test_validate_config_branches(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("POSTGRES_PASSWORD", "not-default")
    monkeypatch.setenv("JWT_SECRET_KEY", "not-default")
    importlib.reload(config)

    config.JWT_SECRET_KEY = "dev-secret-key-change-me-in-production"
    config.POSTGRES_PASSWORD = "postgres"
    config.POSTGRES_URL = "mysql://bad"
    config.REDIS_PASSWORD = "secret"
    config.REDIS_MODE = "standalone"
    config.REDIS_CLUSTER_ENABLED = True
    config.REDIS_NODES = ""
    config.AI_CONFIG = {"is_enabled": True, "api_key": ""}
    config.LLM_ROUTER_MODELS = []
    config.VICTORIAMETRICS_ENABLED = True
    config.LANGGRAPH_ENABLED = True
    config.RAG_ENABLED = False
    config.L7_INTEGRATION_CONFIG["itsm"]["servicenow"]["enabled"] = True
    config.SERVICENOW_INSTANCE = ""
    config.SERVICENOW_USERNAME = ""
    config.SERVICENOW_PASSWORD = ""
    config.L7_INTEGRATION_CONFIG["itsm"]["jira"]["enabled"] = True
    config.JIRA_URL = ""
    config.JIRA_USERNAME = ""
    config.JIRA_API_TOKEN = ""
    config.SLACK_ENABLED = True
    config.SLACK_BOT_TOKEN = ""
    config.TEAMS_ENABLED = True
    config.TEAMS_WEBHOOK = ""
    config.KAFKA_BROKERS = []
    config.FLINK_CONFIG["enable_state_backend"] = True
    config.FLINK_CONFIG["state_backend"] = ""
    config.LANGFUSE_CONFIG["is_enabled"] = True
    config.LANGFUSE_CONFIG["public_key"] = ""
    config.LANGFUSE_CONFIG["secret_key"] = ""
    config.DB_REPLICATION_ENABLED = True
    config.DB_REPLICA_HOSTS = ""
    config.BACKUP_ENABLED = True
    config.BACKUP_LOCATION = ""
    config.REDIS_PORT = 999999

    result = config.validate_config()
    assert result["is_valid"] is False
    assert result["errors"]
    assert result["warnings"]


def test_config_validation_disabled_on_import(monkeypatch):
    monkeypatch.setenv("CONFIG_VALIDATION_ENABLED", "false")
    importlib.reload(config)
    result = config.validate_config()
    assert "is_valid" in result
