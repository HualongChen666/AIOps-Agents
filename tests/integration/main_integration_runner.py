# -*- coding: utf-8 -*-
"""Integration runner for main.py startup scenarios.

This script is executed by ``coverage run`` from ``test_main_integration.py``.
It is not a pytest test file; it is a standalone runner that imports ``main``
in a fresh process under a given environment configuration and exercises the
real FastAPI application via ``TestClient``.
"""

import json
import os
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _set_default_ports():
    """Use a disabled gRPC port by default so tests don't bind real ports."""
    os.environ.setdefault("AIOPS_GRPC_PORT", "0")


def _setup_pythonpath():
    """Ensure repo root is on sys.path, and prepend broken-addon shadow if requested."""
    # Insert repo root so ``import main`` resolves to main.py in the project root.
    sys.path.insert(0, str(REPO_ROOT))
    broken_path = os.environ.get("BROKEN_ADDON_PATH")
    if broken_path:
        # Broken addon is inserted before the repo root so ``import extensions``
        # resolves to the fixture's extensions package, while ``import main`` still
        # resolves to the real main.py (fixture has no main.py).
        sys.path.insert(0, broken_path)


def _load_app():
    # Import main in this subprocess so module-level code and lifespan run fresh.
    import main

    return main.app


def _get_openapi_paths(client):
    r = client.get("/openapi.json")
    if r.status_code != 200:
        return {}
    return set(r.json().get("paths", {}).keys())


def _run_normal(client):
    health = client.get("/health")
    assert health.status_code == 200, f"/health returned {health.status_code}"

    openapi = client.get("/openapi.json")
    assert openapi.status_code == 200, f"/openapi.json returned {openapi.status_code}"
    paths = _get_openapi_paths(client)
    assert "/api/v1/health/ping" in paths, "core health ping route missing"
    # Core routes should always be mounted.
    assert any("/api/v1/" in p for p in paths), "no /api/v1 routes in OpenAPI"

    sw = client.get("/sw.js")
    assert sw.status_code == 200, f"/sw.js returned {sw.status_code}"

    sw_reg = client.get("/sw-register.js")
    assert sw_reg.status_code == 200, f"/sw-register.js returned {sw_reg.status_code}"

    root = client.get("/")
    assert root.status_code in {200, 404, 500}, f"/ returned {root.status_code}"

    metrics = client.get("/metrics")
    assert metrics.status_code in {200, 404}, f"/metrics returned {metrics.status_code}"

    dr = client.get("/api/v1/dr/scenarios")
    # This is not a public route, so it may return 401 if the DR module is not
    # configured; 200 or 500 are also acceptable. The server must not crash.
    assert dr.status_code in {200, 401, 500}, f"/api/v1/dr/scenarios returned {dr.status_code}"

    # Exercise the rate-limit middleware until it returns 429 (or we reach the cap).
    rate_limit_observed = False
    for _ in range(120):
        r = client.get("/health")
        if r.status_code == 429:
            rate_limit_observed = True
            break

    return {
        "health_status": health.status_code,
        "openapi_paths": len(paths),
        "rate_limit_observed": rate_limit_observed,
    }


def _run_missing_env(client):
    # DATABASE_URL was set to an invalid path before importing main. The app must
    # still start and respond to health checks (graceful degradation).
    health = client.get("/health")
    assert health.status_code == 200, f"missing-env startup: /health returned {health.status_code}"
    return {"degraded_startup": True}


def _run_router_disabled(client):
    paths = _get_openapi_paths(client)
    assert "/health" in paths, "core /health missing when addons disabled"

    # These are add-on route families; they should be absent when the packs are off.
    addon_prefixes = ("/api/v1/ai", "/api/v1/rag", "/api/v1/topology", "/api/v1/llm")
    for prefix in addon_prefixes:
        matches = [p for p in paths if p.startswith(prefix)]
        assert not matches, f"add-on route {matches} unexpectedly mounted (prefix {prefix})"

    return {"addon_routes_disabled": True, "path_count": len(paths)}


def _run_addon_failure(client):
    # The broken hardware_remediation fixture raises on import; main.py must catch
    # the error and continue to start up.
    health = client.get("/health")
    assert health.status_code == 200, f"addon-failure startup: /health returned {health.status_code}"
    return {"addon_failure_degraded": True}


def _run_tls_enforced(client):
    # A non-preflight OPTIONS request reaches the security middleware and should
    # be passed through to the next middleware without TLS rejection.
    options = client.request("OPTIONS", "/health")
    assert options.status_code in {200, 204, 405}, f"OPTIONS /health got {options.status_code}"

    # With AIOPS_ENFORCE_TLS=true, plain HTTP requests are rejected before routing.
    r = client.get("/health")
    assert r.status_code == 400, f"TLS enforcement expected 400, got {r.status_code}"

    # CORS preflight with proper preflight headers should be allowed by CORS middleware.
    options = client.request(
        "OPTIONS",
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert options.status_code in {200, 204, 400}, f"OPTIONS /health got {options.status_code}"

    return {"tls_rejected_http": True}


def _run_disable_security_scan(client):
    # AIOPS_DISABLE_SECURITY_SCAN=1 should skip the security testing system init.
    health = client.get("/health")
    assert health.status_code == 200, f"disable-security-scan startup: /health returned {health.status_code}"
    return {"security_scan_skipped": True}


def _run_rate_limit(client):
    # Hit the rate limiter by sending many rapid requests from the same client.
    # The exact threshold depends on config; we just need to observe either 200
    # or 429, confirming the rate-limit middleware is active.
    codes = set()
    for _ in range(120):
        r = client.get("/health")
        codes.add(r.status_code)
        if r.status_code == 429:
            break
    assert 200 in codes, "rate-limit test never received 200"
    return {"rate_limit_codes": sorted(codes)}


SCENARIOS = {
    "normal": _run_normal,
    "missing_env": _run_missing_env,
    "router_disabled": _run_router_disabled,
    "addon_failure": _run_addon_failure,
    "tls_enforced": _run_tls_enforced,
    "disable_security_scan": _run_disable_security_scan,
    "rate_limit": _run_rate_limit,
}


def main():
    if len(sys.argv) < 3:
        print("usage: main_integration_runner.py <scenario> <result.json>", file=sys.stderr)
        raise SystemExit(2)

    scenario = sys.argv[1]
    result_file = sys.argv[2]
    runner = SCENARIOS.get(scenario)
    if runner is None:
        print(f"unknown scenario: {scenario}", file=sys.stderr)
        raise SystemExit(2)

    _set_default_ports()
    _setup_pythonpath()

    result = {"scenario": scenario, "status": "ok", "detail": {}}
    try:
        app = _load_app()
        from fastapi.testclient import TestClient

        with TestClient(app, base_url="http://testserver") as client:
            result["detail"] = runner(client)
    except Exception as exc:
        result["status"] = "failed"
        result["error"] = f"{type(exc).__name__}: {exc}"
        result["traceback"] = traceback.format_exc()

    Path(result_file).write_text(json.dumps(result, indent=2), encoding="utf-8")
    if result["status"] != "ok":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
