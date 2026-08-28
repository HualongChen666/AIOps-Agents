# -*- coding: utf-8 -*-
"""Tests for core modules batch 21b: oncall, audit, config, enhanced AI, platform strategies."""

import asyncio  # noqa: F401  # Imported for test setup
import datetime
import json  # noqa: F401  # Imported for test setup
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest  # noqa: F401  # Imported for test setup
import yaml

import config
import core.config_manager as cm
import core.enhanced_ai_capabilities as eac
import core.external_api_audit as audit
import core.notify_engine as ne
import core.oncall_adapter as oncall
import core.platform_strategies as ps

pytestmark = [pytest.mark.core]


# ---------------------------------------------------------------------------
# Fakes for core.enhanced_ai_capabilities
# ---------------------------------------------------------------------------
class _FakeArray:
    def __init__(self, data):
        self._data = list(data)

    def reshape(self, *args):
        return self

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        return iter(self._data)

    def __getitem__(self, idx):
        return self._data[idx]


class _FakeNP:
    @staticmethod
    def array(data):
        return _FakeArray(data)

    @staticmethod
    def mean(values):
        return sum(values) / len(values) if values else 0.0

    @staticmethod
    def unique(values):
        return sorted(set(values))


class _FakeSeries:
    def __init__(self, values):
        self.values = list(values)
        self.iloc = self

    def tail(self, n):
        return _FakeSeries(self.values[-n:])

    def tolist(self):
        return self.values

    def __getitem__(self, idx):
        return self.values[idx]


class _FakePD:
    @staticmethod
    def DataFrame(data, columns=None):
        if columns and data:
            return dict(zip(columns, zip(*data)))
        return {}

    @staticmethod
    def to_datetime(values):
        if hasattr(values, "__iter__") and not isinstance(values, str):
            return list(values)
        return [values]


class _FakeProphet:
    def __init__(self, **kwargs):
        pass

    def fit(self, df):
        pass

    def make_future_dataframe(self, periods):
        return None

    def predict(self, future):
        now = datetime.datetime.now()
        return {
            "yhat": _FakeSeries([1.0] * 24),
            "yhat_lower": _FakeSeries([0.5] * 24),
            "yhat_upper": _FakeSeries([1.5] * 24),
            "ds": _FakeSeries([now] * 24),
        }


class _FakeIsolationForest:
    def __init__(self, **kwargs):
        pass

    def fit(self, X):
        pass

    def predict(self, X):
        return [-1]

    def decision_function(self, X):
        return [0.5]


class _FakeRandomForestRegressor:
    def __init__(self, **kwargs):
        pass

    def fit(self, X, y):
        pass

    def partial_fit(self, X, y):
        pass


class _FakeStandardScaler:
    pass


# ---------------------------------------------------------------------------
# core/oncall_adapter.py
# ---------------------------------------------------------------------------
def test_oncall_schedule_env_and_file(monkeypatch, tmp_path):
    schedule = oncall.OncallSchedule()
    monkeypatch.setenv(
        "ONCALL_SCHEDULE_JSON",
        json.dumps(
            {
                "sre": [
                    {
                        "name": "Alice",
                        "email": "alice@x",
                        "services": ["api"],
                        "categories": ["db"],
                    }
                ]
            }
        ),
    )
    schedule.load_from_env()
    contacts = schedule.lookup(category="db", service="api", team="sre")
    assert len(contacts) == 1
    assert contacts[0].name == "Alice"

    bad_path = tmp_path / "missing.json"
    schedule.load_from_file(str(bad_path))
    assert schedule._schedules == {}

    good_path = tmp_path / "sched.json"
    good_path.write_text(json.dumps({"ops": [{"name": "Bob", "phone": "123", "team": "ops"}]}))
    schedule.load_from_file(str(good_path))
    assert schedule.lookup(team="ops")[0].name == "Bob"

    monkeypatch.setenv("ONCALL_SCHEDULE_JSON", "not-json")
    schedule.load_from_env()
    assert schedule._schedules == {}


def test_oncall_schedule_lookup_filters():
    schedule = oncall.OncallSchedule()
    schedule._schedules = {
        "sre": [
            {"name": "A", "team": "sre", "services": ["svc1"]},
            {"name": "B", "team": "ops", "categories": ["db"]},
        ]
    }
    assert len(schedule.lookup(service="svc1")) == 2
    assert any(c.name == "B" for c in schedule.lookup(category="db"))
    assert any(c.name == "A" for c in schedule.lookup(team="sre"))
    assert len(schedule.lookup()) == 2


def test_oncall_adapter_sync_and_singleton():
    adapter = oncall.OncallAdapter(provider="json")
    adapter.add_local_schedule("sre", [{"name": "Local", "email": "local@x", "team": "sre"}])
    contacts = adapter.lookup(team="sre")
    assert contacts[0].name == "Local"
    assert oncall.get_oncall_adapter() is oncall.get_oncall_adapter()


@pytest.mark.asyncio
async def test_oncall_adapter_external_success(monkeypatch):
    monkeypatch.setattr(ne, "_get_http_client", None)

    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json = MagicMock(return_value=[{"name": "Ext"}, "skip", {"name": "Ext2"}])
    client = AsyncMock()
    client.get = AsyncMock(return_value=resp)
    monkeypatch.setattr(oncall.httpx, "AsyncClient", lambda **kw: client)

    adapter = oncall.OncallAdapter(provider="pagerduty")
    adapter.api_base = "https://pd.example.com"  # noqa: F841  # Variable for test verification
    adapter.api_token = "tok"
    adapter.add_local_schedule("sre", [{"name": "Local", "email": "local@x", "team": "sre"}])

    contacts = await adapter.lookup_async(category="c", service="s", team="t")
    assert len(contacts) == 2
    assert contacts[0].name == "Ext"
    client.get.assert_awaited_once()


@pytest.mark.asyncio
async def test_oncall_adapter_external_failure_fallback(monkeypatch):
    monkeypatch.setattr(ne, "_get_http_client", None)

    resp = MagicMock()
    resp.raise_for_status = MagicMock(side_effect=Exception("boom"))
    client = AsyncMock()
    client.get = AsyncMock(return_value=resp)
    monkeypatch.setattr(oncall.httpx, "AsyncClient", lambda **kw: client)

    adapter = oncall.OncallAdapter(provider="pagerduty")
    adapter.api_base = "https://pd.example.com"  # noqa: F841  # Variable for test verification
    adapter.api_token = "tok"
    adapter.add_local_schedule("sre", [{"name": "Fallback", "email": "fb@x", "team": "sre"}])

    contacts = await adapter.lookup_async()
    assert contacts[0].name == "Fallback"


# ---------------------------------------------------------------------------
# core/external_api_audit.py
# ---------------------------------------------------------------------------
def test_audit_log_levels_and_sanitization():
    logger = audit.ExternalAPIAuditLogger()
    logger.log_api_call(
        method="GET",
        url="http://api.example.com/data?token=secret",
        headers={"authorization": "Bearer x", "x-trace": "1"},
        body="payload",
        response_status=200,
        response_time_ms=50.0,
    )
    record = logger._audit_logs[-1]
    assert "?***" in record["url"]
    assert record["headers"]["authorization"] == "***REDACTED***"
    assert record["headers"]["x-trace"] == "1"

    logger.log_api_call(
        method="POST",
        url="http://api.example.com/data",
        response_status=500,
    )
    assert logger._audit_logs[-1]["response_status"] == 500

    logger.log_api_call(
        method="DELETE",
        url="http://api.example.com/item",
        error="timeout",
    )
    assert logger._audit_logs[-1]["error"] == "timeout"

    logger.disable_audit()
    before = len(logger._audit_logs)
    logger.log_api_call(method="PATCH", url="http://x")
    assert len(logger._audit_logs) == before
    logger.enable_audit()


def test_audit_query_clear_and_export():
    logger = audit.ExternalAPIAuditLogger()
    for i in range(5):
        logger.log_api_call(
            method="GET",
            url=f"http://api.example.com/{i}",
            response_status=200 + i,
            response_time_ms=100.0 * (i + 1),
            caller="service",
        )

    results = logger.query_audit_logs(
        method="GET",
        url_pattern="1",
        min_status=200,
        max_status=299,
        caller="service",
        limit=2,
    )
    assert isinstance(results, list)
    assert len(results) <= 2

    old_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=2)
    logger._audit_logs.appendleft(
        {
            "timestamp": old_time.isoformat(),
            "method": "POST",
            "url": "http://old",
            "response_status": 200,
        }
    )
    logger.clear_audit_logs(older_than_hours=1)
    assert all(
        datetime.datetime.fromisoformat(r["timestamp"]) >= old_time + datetime.timedelta(hours=1)
        for r in logger._audit_logs
    )

    assert "GET" in logger.export_audit_logs(format="json")
    assert logger.export_audit_logs(format="csv").startswith("timestamp")
    with pytest.raises(ValueError):
        logger.export_audit_logs(format="xml")

    logger.clear_audit_logs()
    assert logger.export_audit_logs(format="csv") == ""


def test_audit_summary():
    logger = audit.ExternalAPIAuditLogger()
    logger.log_api_call(
        method="GET",
        url="http://api.example.com/a",
        response_status=200,
        response_time_ms=1500.0,
        caller="a",
    )
    logger.log_api_call(
        method="POST",
        url="http://api.example.com/b",
        response_status=500,
        caller="b",
    )
    old_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=25)
    logger._audit_logs.append(
        {
            "timestamp": old_time.isoformat(),
            "method": "GET",
            "url": "http://old",
            "response_status": 200,
            "response_time_ms": 100.0,
            "caller": "a",
        }
    )
    summary = logger.get_audit_summary(hours=24)
    assert summary["total_calls"] == 2
    assert summary["failed_calls"] == 1
    assert summary["slow_calls"] == 1
    assert "GET" in summary["method_distribution"]


@pytest.mark.asyncio
async def test_audit_httpx_and_aiohttp_decorators(monkeypatch):
    local_logger = audit.ExternalAPIAuditLogger()
    monkeypatch.setattr(audit, "get_audit_logger", lambda: local_logger)

    async def fake_httpx_ok(**kwargs):
        class Resp:
            status_code = 200

        return Resp()

    wrapped_ok = audit.audit_httpx_call(fake_httpx_ok)
    resp = await wrapped_ok(
        method="GET", url="http://api.example.com/x", headers={"h": "v"}, content="b"
    )
    assert resp.status_code == 200
    assert len(local_logger._audit_logs) == 1

    async def fake_httpx_fail(**kwargs):
        raise Exception("boom")

    wrapped_fail = audit.audit_httpx_call(fake_httpx_fail)
    with pytest.raises(Exception):
        await wrapped_fail(method="POST", url="http://api.example.com/y")
    assert any(r.get("error") for r in local_logger._audit_logs)

    async def fake_aiohttp_ok(*args, **kwargs):
        return "ok"

    wrapped_aio = audit.audit_aiohttp_call(fake_aiohttp_ok)
    assert await wrapped_aio() == "ok"

    async def fake_aiohttp_fail(*args, **kwargs):
        raise Exception("bad")

    wrapped_aio_fail = audit.audit_aiohttp_call(fake_aiohttp_fail)
    with pytest.raises(Exception):
        await wrapped_aio_fail()


def test_initialize_external_api_audit(monkeypatch):
    monkeypatch.setenv("EXTERNAL_API_AUDIT_ENABLED", "false")
    audit.initialize_external_api_audit()
    assert not audit.get_audit_logger()._audit_enabled
    monkeypatch.setenv("EXTERNAL_API_AUDIT_ENABLED", "true")
    audit.initialize_external_api_audit()
    assert audit.get_audit_logger()._audit_enabled


# ---------------------------------------------------------------------------
# core/config_manager.py
# ---------------------------------------------------------------------------
@pytest.fixture
def cfg_manager(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setattr(cm, "DOTENV_AVAILABLE", False)
    return cm.ConfigManager()


def _write_json_config(tmp_path, data):
    path = tmp_path / "cfg.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return str(path)


def test_config_load_defaults_and_getters(cfg_manager):
    cfg_manager.load_config()
    cfg = cfg_manager.get_config()
    assert cfg.environment == cm.Environment.TEST
    assert cfg_manager.get_config_value("app_name") == cfg.app_name
    assert cfg_manager.get_config_value("missing", "def") == "def"

    empty = cm.ConfigManager()
    with pytest.raises(RuntimeError):
        empty.get_config()


def test_config_load_from_json_and_yaml(cfg_manager, tmp_path):
    json_path = _write_json_config(tmp_path, {"app_name": "JsonApp"})
    cfg_manager.load_config(json_path)
    assert cfg_manager.get_config_value("app_name") == "JsonApp"

    yaml_path = tmp_path / "cfg.yaml"
    yaml_path.write_text(yaml.safe_dump({"app_name": "YamlApp"}), encoding="utf-8")
    cfg_manager.load_config(str(yaml_path))
    assert cfg_manager.get_config_value("app_name") == "YamlApp"

    out_path = tmp_path / "out.json"
    cfg_manager.save_config(str(out_path))
    assert out_path.exists()
    out_yaml = tmp_path / "out.yaml"
    cfg_manager.save_config(str(out_yaml))
    assert out_yaml.exists()


def test_config_env_overrides(cfg_manager, monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "jwt-123")
    monkeypatch.setenv("CORS_ORIGINS", "http://a,http://b")
    monkeypatch.setenv("CORS_ALLOW_METHODS", "GET,POST")
    monkeypatch.setenv("CORS_ALLOW_HEADERS", "X-Custom")
    monkeypatch.setenv("AI_API_KEY", "sk-abc")
    cfg_manager.load_config()
    assert cfg_manager.get_config_value("security.jwt_secret_key") == "jwt-123"
    assert cfg_manager.get_config_value("cors_origins") == ["http://a", "http://b"]
    assert cfg_manager.get_config_value("cors_allow_methods") == ["GET", "POST"]
    assert cfg_manager.get_config_value("cors_allow_headers") == ["X-Custom"]
    assert cfg_manager.get_config_value("ai.api_key") == "sk-abc"


def test_config_production_tls_validation(cfg_manager, monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "prod-secret")
    cfg_manager._environment = cm.Environment.PRODUCTION
    cfg_manager.load_config()
    config = cfg_manager.get_config()
    assert config.environment == cm.Environment.PRODUCTION
    config.security.tls_enabled = True
    config.security.tls_cert_path = ""
    config.security.tls_key_path = ""
    with pytest.raises(ValueError):
        cfg_manager._validate_config(config)


def test_config_missing_file_and_unsupported(cfg_manager, tmp_path):
    cfg_manager.load_config(str(tmp_path / "missing.json"))
    assert cfg_manager.get_config() is not None

    txt_path = tmp_path / "cfg.txt"
    txt_path.write_text("hello")
    cfg_manager.load_config(str(txt_path))
    assert cfg_manager.get_config() is not None

    cfg_manager.load_config()
    with pytest.raises(ValueError):
        cfg_manager.save_config(str(tmp_path / "out.bin"))


def test_config_update_set_rollback_and_audit(cfg_manager, tmp_path):
    cfg_manager.load_config(_write_json_config(tmp_path, {"app_name": "Orig"}))
    cfg_manager.set_config_value("app_name", "Changed")
    assert cfg_manager.get_config_value("app_name") == "Changed"

    config_obj = cfg_manager.get_config()
    cfg_manager._update_config_from_dict(
        config_obj, {"app_name": "Updated", "security": {"tls_enabled": False}, "nope": 1}
    )
    assert config_obj.app_name == "Updated"
    assert config_obj.security.tls_enabled is False

    result = cfg_manager.rollback_config(1)  # noqa: F841  # Variable for test verification
    assert result["status"] == "success"

    cfg_manager.audit_config_change("user", "app_name", {"old": "Changed", "new": "Updated"})
    assert len(cfg_manager._audit_log) >= 1


def test_config_reload_and_hot_reload(cfg_manager, tmp_path):
    json_path = _write_json_config(tmp_path, {"app_name": "Reload"})
    cfg_manager.load_config(json_path)

    reloaded = cfg_manager.reload_config()
    assert reloaded is not None

    empty = cm.ConfigManager()
    empty.load_config()
    result = empty.reload_config()  # noqa: F841  # Variable for test verification
    assert result is not None

    fresh = cm.ConfigManager()
    fresh._config_file = Path(json_path)
    handler = cm.ConfigManager._ConfigReloadHandler(fresh)
    event = type("E", (), {"src_path": json_path})()
    handler.on_modified(event)
    assert fresh.get_config().app_name == "Reload"

    event_bad = type("E", (), {"src_path": str(tmp_path / "other.json")})()
    handler.on_modified(event_bad)

    watcher = cm.ConfigManager()
    watcher._config_file = Path(json_path)
    start = watcher.start_hot_reload(json_path)
    assert start["status"] == "started"
    assert watcher.start_hot_reload(json_path)["status"] == "already_running"
    stop = watcher.stop_hot_reload()
    assert stop["status"] == "stopped"
    assert watcher.stop_hot_reload()["status"] == "not_running"


def test_config_setup_unified_and_helpers(cfg_manager, tmp_path, monkeypatch):
    cfg_manager.load_config(_write_json_config(tmp_path, {"app_name": "Unified"}))
    result = (
        cfg_manager.setup_unified_configuration()
    )  # noqa: F841  # Variable for test verification
    assert result["status"] == "success"
    assert "config_summary" in result

    cfg_manager.load_config = MagicMock(side_effect=Exception("fail"))
    error = cfg_manager.setup_unified_configuration()
    assert error["status"] == "error"


def test_config_loader_validator_and_top_level(tmp_path):
    json_path = _write_json_config(tmp_path, {"app_name": "Loader"})

    loader = cm.ConfigLoader()
    cfg = loader.load(json_path)
    assert cfg is not None

    validator = cm.ConfigValidator()
    assert validator.validate(cfg) == []
    assert isinstance(validator.validate("invalid"), list)

    assert cm.load_config(json_path) is not None
    out_path = tmp_path / "saved.json"
    assert isinstance(cm.save_config(str(out_path)), dict)
    assert cm.get_config_value("app_name") is not None
    assert isinstance(cm.setup_unified_configuration(), dict)


def test_config_get_config_dict_excludes_secrets(cfg_manager, tmp_path):
    cfg_manager.load_config(_write_json_config(tmp_path, {"security": {"jwt_secret_key": "x"}}))
    d = cfg_manager.get_config_dict()
    assert d["security"].get("jwt_secret_key") is None or d["security"].get("jwt_secret_key") == ""
    assert "database" in d


# ---------------------------------------------------------------------------
# core/enhanced_ai_capabilities.py
# ---------------------------------------------------------------------------
@pytest.fixture
def ai_cap(monkeypatch):
    monkeypatch.setattr(eac, "ML_AVAILABLE", False)
    monkeypatch.setattr(eac, "PROPHET_AVAILABLE", False)
    return eac.EnhancedAICapabilities()


@pytest.mark.asyncio
async def test_ai_initialize_and_stats(ai_cap, monkeypatch):
    monkeypatch.setattr(eac, "ML_AVAILABLE", True)
    monkeypatch.setattr(eac, "IsolationForest", _FakeIsolationForest, raising=False)
    monkeypatch.setattr(eac, "RandomForestRegressor", _FakeRandomForestRegressor, raising=False)
    monkeypatch.setattr(eac, "Prophet", _FakeProphet, raising=False)
    monkeypatch.setattr(eac, "StandardScaler", _FakeStandardScaler, raising=False)
    cap = eac.EnhancedAICapabilities()
    await cap.initialize()
    assert len(cap.anomaly_detectors) > 0
    stats = await cap.get_ai_statistics()
    assert stats["prediction_models"] >= 0


@pytest.mark.asyncio
async def test_ai_predict_timeseries(monkeypatch):
    monkeypatch.setattr(eac, "PROPHET_AVAILABLE", True)
    monkeypatch.setattr(eac, "Prophet", _FakeProphet, raising=False)
    monkeypatch.setattr(eac, "np", _FakeNP(), raising=False)
    monkeypatch.setattr(eac, "pd", _FakePD(), raising=False)
    cap = eac.EnhancedAICapabilities()
    historical = [(datetime.datetime.now(), float(i)) for i in range(30)]
    result = await cap.predict_timeseries(
        "cpu_usage", historical
    )  # noqa: F841  # Variable for test verification
    assert isinstance(result, eac.PredictionResult)
    assert len(result.predicted_values) == 24
    cached = await cap.predict_timeseries("cpu_usage", historical)
    assert cached is result


@pytest.mark.asyncio
async def test_ai_predict_timeseries_unavailable(ai_cap):
    result = await ai_cap.predict_timeseries(
        "cpu_usage", []
    )  # noqa: F841  # Variable for test verification
    assert result is None


@pytest.mark.asyncio
async def test_ai_predict_anomalies(monkeypatch):
    monkeypatch.setattr(eac, "ML_AVAILABLE", True)
    monkeypatch.setattr(eac, "IsolationForest", _FakeIsolationForest, raising=False)
    monkeypatch.setattr(eac, "np", _FakeNP(), raising=False)
    cap = eac.EnhancedAICapabilities()
    cap.min_samples_for_training = 3
    historical = [(datetime.datetime.now(), float(i)) for i in range(50)]
    result = await cap.predict_anomalies(
        "cpu_usage", 95.0, historical
    )  # noqa: F841  # Variable for test verification
    assert isinstance(result, eac.AnomalyPrediction)
    assert result.is_anomalous is True


@pytest.mark.asyncio
async def test_ai_predict_anomalies_unavailable(ai_cap):
    result = await ai_cap.predict_anomalies(
        "cpu_usage", 1.0, []
    )  # noqa: F841  # Variable for test verification
    assert result is None


@pytest.mark.asyncio
async def test_ai_adaptive_learn(ai_cap, monkeypatch):
    assert await ai_cap.adaptive_learn("rf_test", [], eac.LearningMode.ONLINE) is None

    monkeypatch.setattr(eac, "ML_AVAILABLE", True)
    monkeypatch.setattr(eac, "_fit_model", AsyncMock())
    cap = eac.EnhancedAICapabilities()
    cap.prediction_models["rf_test"] = _FakeRandomForestRegressor()
    samples = [({"f": 1}, 1.0), ({"f": 2}, 2.0)]
    for mode in [eac.LearningMode.ONLINE, eac.LearningMode.BATCH, eac.LearningMode.TRANSFER]:
        update = await cap.adaptive_learn("rf_test", samples, mode)
        assert isinstance(update, eac.LearningUpdate)
        assert update.learning_mode == mode

    assert await cap.adaptive_learn("missing", samples) is None


@pytest.mark.asyncio
async def test_ai_fit_model(monkeypatch):
    class FakeClassifier:
        def __init__(self):
            self.calls = []

        def partial_fit(self, X, y, classes=None):
            self.calls.append(("partial", classes))

    class FakeRegressor:
        def __init__(self):
            self.calls = []

        def fit(self, X, y):
            self.calls.append("fit")

    await eac._fit_model(FakeClassifier(), [({"a": 1}, "x"), ({"a": 2}, "y")], incremental=True)
    await eac._fit_model(FakeRegressor(), [({"a": 1}, 1.0), ({"a": 2}, 2.0)], incremental=False)
    await eac._fit_model(None, [], incremental=False)

    monkeypatch.setattr(eac, "ML_AVAILABLE", False)
    acc = eac.defaultdict(list)
    model = object()
    await eac._fit_model(model, [({"a": 1}, 1)], incremental=False, knowledge_accumulator=acc)
    assert str(id(model)) in acc
    assert len(acc[str(id(model))]) == 1


@pytest.mark.asyncio
async def test_ai_parse_natural_language(ai_cap):
    result = await ai_cap.parse_natural_language(
        "check cpu usage above 90 in last hour"
    )  # noqa: F841  # Variable for test verification
    assert isinstance(result, eac.NLParseResult)
    assert result.intent == "monitor"
    assert "cpu_usage" in result.entities.values()
    assert isinstance(result.suggested_actions, list)


@pytest.mark.asyncio
async def test_ai_explain_decision(ai_cap):
    result = await ai_cap.explain_decision(  # noqa: F841  # Variable for test verification
        "scale_up",
        {
            "metrics": {},
            "historical_data": {},
            "ml_model": "m",
            "confidence": 0.85,
        },
    )
    assert isinstance(result, eac.DecisionExplanation)
    assert result.decision == "scale_up"
    assert result.alternative_options

    restart = await ai_cap.explain_decision("restart_service", {})
    assert isinstance(restart, eac.DecisionExplanation)


@pytest.mark.asyncio
async def test_ai_knowledge_and_relearn(ai_cap):
    await ai_cap.accumulate_knowledge(
        {
            "symptoms": ["cpu high"],
            "root_causes": ["overload"],
            "resolution": "scale out",
            "id": "inc-1",
        }
    )
    pattern = ai_cap._generate_knowledge_pattern(["cpu high"], ["overload"])
    insights = await ai_cap.get_knowledge_insights(pattern)
    assert insights["incident_count"] == 1
    assert insights["success_rate"] == 1.0

    ai_cap.performance_metrics["m"] = [0.9, 0.9, 0.8]
    assert await ai_cap._should_relearn("m") is True
    ai_cap.performance_metrics["m2"] = [0.9]
    assert await ai_cap._should_relearn("m2") is False


# ---------------------------------------------------------------------------
# core/platform_strategies.py
# ---------------------------------------------------------------------------
def test_get_platform_strategy_and_registry():
    windows = ps.get_platform_strategy("windows")
    assert windows.requires_host_name() is False
    all_strategies = ps.get_all_platform_strategies()
    assert set(all_strategies.keys()) == {"windows", "linux", "docker", "kubernetes"}
    with pytest.raises(ValueError):
        ps.get_platform_strategy("unknown")


@pytest.mark.asyncio
async def test_platform_strategies_execute(monkeypatch):
    for name, strategy in ps.PLATFORM_STRATEGIES.items():
        strategy._execute_repair = AsyncMock(return_value={"success": True})
        strategy._get_history = MagicMock(return_value=[{"id": "h1"}])
        if hasattr(strategy, "_get_scripts"):
            strategy._get_scripts = MagicMock(return_value={"fix": {}})

    win = ps.get_platform_strategy("windows")
    assert isinstance(win.get_scripts(), dict)
    result = await win.execute_repair(
        "fix", "host", {}
    )  # noqa: F841  # Variable for test verification
    assert result["success"]
    assert win.get_history(5)
    win._execute_repair.assert_awaited_with("fix", {})

    linux = ps.get_platform_strategy("linux")
    linux._get_scripts = MagicMock(return_value=[{"key": "restart"}, {"key": "fix"}])
    scripts = linux.get_scripts()
    assert "restart" in scripts
    assert "fix" in scripts
    await linux.execute_repair("fix", "host1", {"p": "v"})
    linux._execute_repair.assert_awaited_with("host1", "fix", {"p": "v"})

    docker = ps.get_platform_strategy("docker")
    await docker.execute_repair("fix", "host2", {})
    docker._execute_repair.assert_awaited_with("host2", "fix", {})

    k8s = ps.get_platform_strategy("kubernetes")
    monkeypatch.setattr(config, "K8S_HOSTS", [{"host": "k8s-node"}])
    await k8s.execute_repair("fix", "k8s-node", {})
    k8s._execute_repair.assert_awaited_with({"host": "k8s-node"}, "fix", {})

    monkeypatch.setattr(config, "K8S_HOSTS", [])
    result = await k8s.execute_repair(
        "fix", "missing", {}
    )  # noqa: F841  # Variable for test verification
    assert result["success"] is False
    assert k8s.get_scripts() == {}
