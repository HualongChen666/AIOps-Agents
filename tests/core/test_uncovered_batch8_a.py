# -*- coding: utf-8 -*-
"""Targeted functional coverage tests for core.constants, core.eager_loading,
core.service_mesh, core.service_worker_config and core.telemetry.fastapi.
"""
import sys
import types
from unittest.mock import MagicMock

import pytest

import core.constants as constants
import core.eager_loading as eager_loading
import core.service_mesh as service_mesh
import core.service_worker_config as sw_config
import core.telemetry.fastapi as telemetry_fastapi

pytestmark = [pytest.mark.core]


# -----------------------------------------------------------------------------
# core.constants
# -----------------------------------------------------------------------------
def test_constants_values():
    """Verify all default operational constants are exposed."""
    assert constants.DEFAULT_MAX_MEMORY_MB == 1024
    assert constants.DEFAULT_WARNING_THRESHOLD == 0.8
    assert constants.DEFAULT_MAX_RETRIES == 3
    assert constants.DEFAULT_BASE_DELAY == 1.0
    assert constants.DEFAULT_MAX_DELAY == 30.0
    assert constants.DEFAULT_CACHE_TTL == 300
    assert constants.DEFAULT_MAX_CACHE_SIZE == 1000
    assert constants.DEFAULT_RETENTION_DAYS == 30


# -----------------------------------------------------------------------------
# core.eager_loading
# -----------------------------------------------------------------------------
def test_eager_loading_registry_is_dict_and_mutable():
    """EAGER_LOAD_CONFIGS is a runtime registry that callers populate."""
    assert isinstance(eager_loading.EAGER_LOAD_CONFIGS, dict)
    eager_loading.EAGER_LOAD_CONFIGS["Order.items"] = "selectin"
    assert eager_loading.EAGER_LOAD_CONFIGS["Order.items"] == "selectin"
    del eager_loading.EAGER_LOAD_CONFIGS["Order.items"]
    assert "Order.items" not in eager_loading.EAGER_LOAD_CONFIGS


# -----------------------------------------------------------------------------
# core.service_mesh (alias for core.service_mesh_manager)
# -----------------------------------------------------------------------------
def test_service_mesh_alias_and_basic_manager(tmp_path, monkeypatch):
    """Use the ServiceMesh alias to build real mesh artefacts."""
    manager = service_mesh.ServiceMesh({"mesh_type": "istio"})
    assert manager.mesh_status.value == "not_configured"

    cp = manager.generate_istio_control_plane_config(
        "prod-mesh", namespace="istio-system", profile="demo"
    )
    assert cp.mesh_id == "prod-mesh"
    assert cp.control_plane_config["spec"]["profile"] == "demo"
    assert cp.control_plane_config["metadata"]["name"] == "istio-prod-mesh"

    ai = manager.generate_auto_injection_config(namespace="aiops", enabled=True)
    assert ai["metadata"]["name"] == "aiops"
    assert ai["metadata"]["labels"]["istio-injection"] == "enabled"

    vs = manager.generate_virtual_service_config(
        "api",
        routing_rules=[
            {
                "match": [{"uri": {"prefix": "/v1"}}],
                "route": [{"destination": {"host": "api", "subset": "v1"}}],
            }
        ],
        namespace="aiops",
    )
    assert vs.service_name == "api"
    assert vs.metadata["namespace"] == "aiops"

    dr = manager.generate_destination_rule_config(
        "api", subsets=[{"name": "v1", "labels": {"version": "v1"}}], namespace="aiops"
    )
    assert dr["metadata"]["name"] == "api-dr"
    assert dr["spec"]["host"] == "api"

    mtls = manager.generate_mtls_config("prod-mesh", namespace="aiops", strict_mode=False)
    assert mtls.mesh_id == "prod-mesh"
    assert mtls.authentication_policies[0]["spec"]["mtls"]["mode"] == "PERMISSIVE"

    sidecar = manager.generate_sidecar_injection_config("worker", port=8080, protocol="grpc")
    assert sidecar["kind"] == "Sidecar"
    assert sidecar["spec"]["egress"][0]["port"]["protocol"] == "GRPC"

    summary = manager.generate_service_mesh_summary()
    assert summary["mesh_type"] == "istio"
    assert summary["istio_configs_count"] == 1
    assert summary["traffic_configs_count"] == 1
    assert summary["security_configs_count"] == 1

    yaml_path = tmp_path / "cp.yaml"
    json_path = tmp_path / "cp.json"
    manager.export_config_to_yaml(cp.control_plane_config, str(yaml_path))
    manager.export_config_to_json(cp.control_plane_config, str(json_path))
    assert yaml_path.exists()
    assert json_path.exists()

    valid = {"apiVersion": "v1", "kind": "Namespace"}
    assert manager.validate_config(valid) is True
    assert manager.validate_config({}) is False
    assert manager.validate_config(None) is False

    deployment = {
        "metadata": {"name": "worker"},
        "spec": {"template": {"metadata": {}, "spec": {"containers": []}}},
    }
    injected = manager.inject_sidecar_to_deployment(deployment)
    container_names = [c["name"] for c in injected["spec"]["template"]["spec"]["containers"]]
    assert "istio-proxy" in container_names
    assert injected["spec"]["template"]["metadata"]["annotations"][
        "sidecar.istio.io/inject"
    ] == "true"


# -----------------------------------------------------------------------------
# core.service_worker_config
# -----------------------------------------------------------------------------
def test_service_worker_config_and_scripts():
    """Service worker config and generated JS scripts match business policy."""
    config = sw_config.SERVICE_WORKER_CONFIG
    assert config["version"] == "1.0.0"
    assert config["cache_name"] == "aiops-cache-v1"
    assert "/api/v1/health" in config["cache_urls"]
    assert "/api/v1/*" in config["network_first_patterns"]
    assert "/static/*" in config["cache_first_patterns"]
    assert config["skip_waiting"] is True
    assert config["clients_claim"] is True

    script = sw_config.get_service_worker_script()
    assert "const CACHE_NAME = 'aiops-cache-v1';" in script
    assert "'/api/v1/health'" in script
    assert "self.addEventListener('install'" in script
    assert "self.addEventListener('activate'" in script
    assert "self.addEventListener('fetch'" in script
    assert "caches.open(CACHE_NAME)" in script
    assert "caches.match(event.request)" in script
    assert "self.skipWaiting()" in script
    assert "self.clients.claim()" in script

    registration = sw_config.get_service_worker_registration_script()
    assert "'serviceWorker' in navigator" in registration
    assert "navigator.serviceWorker.register('/sw.js')" in registration
    assert "window.addEventListener('load'" in registration


# -----------------------------------------------------------------------------
# core.telemetry.fastapi fixtures/helpers
# -----------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _patch_opentelemetry_instrumentors(monkeypatch):
    """Replace real OTel instrumentors with deterministic fakes."""
    # FastAPIInstrumentor.instrument_app is a classmethod-like call.
    fake_fastapi = MagicMock()
    fake_fastapi.instrument_app = MagicMock()
    monkeypatch.setattr(telemetry_fastapi, "FastAPIInstrumentor", fake_fastapi)

    fake_httpx = MagicMock()
    fake_httpx.return_value.instrument = MagicMock()
    monkeypatch.setattr(telemetry_fastapi, "HTTPXClientInstrumentor", fake_httpx)

    fake_sqlalchemy = MagicMock()
    fake_sqlalchemy.return_value.instrument = MagicMock()
    monkeypatch.setattr(telemetry_fastapi, "SQLAlchemyInstrumentor", fake_sqlalchemy)

    fake_redis_cls = MagicMock()
    fake_redis_cls.return_value.instrument = MagicMock()
    fake_redis_mod = types.SimpleNamespace(RedisInstrumentor=fake_redis_cls)
    monkeypatch.setitem(sys.modules, "opentelemetry.instrumentation.redis", fake_redis_mod)


def _init_telemetry_success(**kwargs):
    return True


def _init_telemetry_false(**kwargs):
    return False


def _init_telemetry_import_error(**kwargs):
    raise ImportError("opentelemetry missing")


# -----------------------------------------------------------------------------
# core.telemetry.fastapi
# -----------------------------------------------------------------------------
def test_instrument_fastapi_success(monkeypatch):
    app = MagicMock()
    telemetry_fastapi.instrument_fastapi(app, service_name="aiops-test", excluded_urls="/health,/metrics")
    telemetry_fastapi.FastAPIInstrumentor.instrument_app.assert_called_once_with(
        app, tracer_provider=None, excluded_urls="/health,/metrics"
    )


def test_instrument_fastapi_failure(monkeypatch):
    telemetry_fastapi.FastAPIInstrumentor.instrument_app.side_effect = RuntimeError(
        "no tracer provider"
    )
    # Should swallow exception and warn; no exception raised.
    telemetry_fastapi.instrument_fastapi(MagicMock(), service_name="aiops-test")


def test_instrument_httpx_success():
    telemetry_fastapi.instrument_httpx()
    assert telemetry_fastapi.HTTPXClientInstrumentor().instrument.called


def test_instrument_httpx_failure(monkeypatch):
    telemetry_fastapi.HTTPXClientInstrumentor.return_value.instrument.side_effect = RuntimeError(
        "httpx not installed"
    )
    telemetry_fastapi.instrument_httpx()


def test_instrument_sqlalchemy_success():
    engine = MagicMock()
    telemetry_fastapi.instrument_sqlalchemy(engine)
    telemetry_fastapi.SQLAlchemyInstrumentor().instrument.assert_called_once_with(engine=engine)


def test_instrument_sqlalchemy_failure(monkeypatch):
    telemetry_fastapi.SQLAlchemyInstrumentor.return_value.instrument.side_effect = RuntimeError(
        "sqlalchemy not installed"
    )
    telemetry_fastapi.instrument_sqlalchemy(MagicMock())


def test_instrument_redis_success():
    telemetry_fastapi.instrument_redis()
    fake_redis = sys.modules["opentelemetry.instrumentation.redis"].RedisInstrumentor
    assert fake_redis().instrument.called


def test_instrument_redis_failure(monkeypatch):
    fake_redis = sys.modules["opentelemetry.instrumentation.redis"].RedisInstrumentor
    fake_redis.return_value.instrument.side_effect = RuntimeError("redis not installed")
    telemetry_fastapi.instrument_redis()


def test_setup_fastapi_telemetry_all_enabled(monkeypatch):
    monkeypatch.setattr("core.telemetry.initialize_telemetry", _init_telemetry_success)
    app = MagicMock()
    engine = MagicMock()
    result = telemetry_fastapi.setup_fastapi_telemetry(
        app,
        service_name="aiops-test",
        instrument_http=True,
        instrument_db=True,
        enable_redis_instrumentation=True,
        db_engine=engine,
        otlp_endpoint="localhost:4317",
        environment="testing",
    )
    assert result is True
    telemetry_fastapi.FastAPIInstrumentor.instrument_app.assert_called()
    assert telemetry_fastapi.HTTPXClientInstrumentor().instrument.called
    assert telemetry_fastapi.SQLAlchemyInstrumentor().instrument.called


def test_setup_fastapi_telemetry_init_false(monkeypatch):
    monkeypatch.setattr("core.telemetry.initialize_telemetry", _init_telemetry_false)
    result = telemetry_fastapi.setup_fastapi_telemetry(MagicMock())
    assert result is False


def test_setup_fastapi_telemetry_import_error(monkeypatch):
    monkeypatch.setattr("core.telemetry.initialize_telemetry", _init_telemetry_import_error)
    result = telemetry_fastapi.setup_fastapi_telemetry(MagicMock())
    assert result is False


def test_setup_fastapi_telemetry_optional_instruments_off(monkeypatch):
    monkeypatch.setattr("core.telemetry.initialize_telemetry", _init_telemetry_success)
    app = MagicMock()
    result = telemetry_fastapi.setup_fastapi_telemetry(
        app,
        instrument_http=False,
        instrument_db=False,
        enable_redis_instrumentation=False,
    )
    assert result is True
    # HTTPX / SQLAlchemy / Redis instrumentors should not have been invoked.
    assert not telemetry_fastapi.HTTPXClientInstrumentor().instrument.called
    assert not telemetry_fastapi.SQLAlchemyInstrumentor().instrument.called
    redis_cls = sys.modules["opentelemetry.instrumentation.redis"].RedisInstrumentor
    assert not redis_cls().instrument.called


def test_setup_fastapi_telemetry_db_enabled_without_engine(monkeypatch):
    monkeypatch.setattr("core.telemetry.initialize_telemetry", _init_telemetry_success)
    app = MagicMock()
    result = telemetry_fastapi.setup_fastapi_telemetry(
        app,
        instrument_http=False,
        instrument_db=True,
        enable_redis_instrumentation=False,
    )
    assert result is True
    assert not telemetry_fastapi.SQLAlchemyInstrumentor().instrument.called
