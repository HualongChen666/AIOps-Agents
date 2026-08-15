# -*- coding: utf-8 -*-
"""Integration tests for AIOps Agent main.py startup and lifecycle.

Each test starts ``main.py`` in a real subprocess under ``coverage run`` with a
different environment configuration, then uses a real ``FastAPI TestClient`` to
exercise the application.  This proves:

* normal startup
* startup with a missing/invalid environment variable (graceful degradation)
* router mount switches (add-on packs enabled/disabled)
* add-on loading failure degradation
* TLS enforcement and CORS preflight handling
* optional security scan skip

No mocks or stubs are used for the application itself; only environment
variables and Python path manipulation are applied to the real process.
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNNER = Path(__file__).with_name("main_integration_runner.py")
BROKEN_ADDON_FIXTURE = REPO_ROOT / "tests" / "integration" / "fixtures" / "broken_hardware_remediation"

# (scenario, env_overrides)
SCENARIOS = [
    (
        "normal",
        {
            "ALLOWED_LOCAL_IPS": "127.0.0.1,::1,localhost,testclient",
        },
    ),
    (
        "missing_env",
        {
            "DATABASE_URL": "sqlite:///C:/_aiops_missing_env_test/no_such_dir/db.sqlite",
            "ALLOWED_LOCAL_IPS": "testclient",
        },
    ),
    (
        "router_disabled",
        {
            "ENABLE_ADDONS": "false",
            "RAG_ENABLED": "false",
            "LLM_ROUTER_ENABLED": "false",
            "TOPOLOGY_ENABLED": "false",
            "TRACING_ENABLED": "false",
            "LOG_AGGREGATION_ENABLED": "false",
            "INCIDENT_RESPONSE_ENABLED": "false",
            "WORKFLOW_ENABLED": "false",
            "INTEGRATIONS_ENABLED": "false",
            "SECURITY_SCANNING_ENABLED": "false",
            "PLUGINS_ENABLED": "false",
            "GRAPHQL_ENABLED": "false",
            "MCP_ENABLED": "false",
            "I18N_ENABLED": "false",
            "DOC_GENERATION_ENABLED": "false",
            "ALLOWED_LOCAL_IPS": "testclient",
        },
    ),
    (
        "addon_failure",
        {
            "BROKEN_ADDON_PATH": str(BROKEN_ADDON_FIXTURE),
            "ALLOWED_LOCAL_IPS": "testclient",
        },
    ),
    (
        "tls_enforced",
        {
            "AIOPS_ENFORCE_TLS": "true",
            "ALLOWED_LOCAL_IPS": "testclient",
        },
    ),
    (
        "disable_security_scan",
        {
            "AIOPS_DISABLE_SECURITY_SCAN": "1",
            "ALLOWED_LOCAL_IPS": "testclient",
        },
    ),
]


@pytest.mark.parametrize("scenario,overrides", SCENARIOS, ids=[s for s, _ in SCENARIOS])
def test_main_startup_scenario(scenario, overrides):
    env = os.environ.copy()
    env.update(overrides)
    env.setdefault("AIOPS_GRPC_PORT", "0")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        result_file = f.name

    try:
        cmd = [
            sys.executable,
            "-m",
            "coverage",
            "run",
            "--parallel-mode",
            str(RUNNER),
            scenario,
            result_file,
        ]
        completed = subprocess.run(
            cmd,
            env=env,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=240,
        )

        if completed.returncode != 0 or not Path(result_file).exists():
            print("STDOUT:\n", completed.stdout, file=sys.stderr)
            print("STDERR:\n", completed.stderr, file=sys.stderr)
            pytest.fail(f"integration runner for scenario '{scenario}' exited with {completed.returncode}")

        result = json.loads(Path(result_file).read_text(encoding="utf-8"))
        assert result.get("status") == "ok", (
            f"scenario '{scenario}' did not succeed: "
            f"{result.get('error', '')}\n{result.get('traceback', '')}"
        )
        assert result.get("detail") is not None, "result detail missing"
    finally:
        try:
            Path(result_file).unlink(missing_ok=True)
        except OSError:
            pass
