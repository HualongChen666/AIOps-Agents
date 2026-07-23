import os
import subprocess
import sys
from pathlib import Path

ROOT = Path.cwd()
PYTEST_INI = str(ROOT / "pytest_coverage.ini")
files = [
    "tests/test_main_app_post_routes.py",
    "tests/test_main_app_routes.py",
    "tests/test_main_import.py",
    "tests/test_models.py",
    "tests/test_multi_tenant.py",
    "tests/test_notify_engine.py",
    "tests/test_p2_enhancements.py",
    "tests/test_password_policy.py",
    "tests/test_plugin_system.py",
    "tests/test_priority.py",
    "tests/test_rate_limiter.py",
    "tests/test_rbac.py",
    "tests/test_root_cause_intelligence.py",
    "tests/test_security_hardening.py",
    "tests/test_sso_auth.py",
    "tests/test_stats_engine.py",
    "tests/test_topology_engine.py",
    "tests/test_workflow_engine.py",
]
cmd = [
    sys.executable,
    "-m",
    "coverage",
    "run",
    "--append",
    "-m",
    "pytest",
    "-c",
    PYTEST_INI,
    *files,
    "-m",
    "not performance",
    "-n0",
    "--tb=short",
    "-q",
]
env = os.environ.copy()
env["PYTEST_ADDOPTS"] = ""
out = open("second_half_root.log", "w", encoding="utf-8")
err = open("second_half_root_err.log", "w", encoding="utf-8")
print(f"Running {len(files)} files")
proc = subprocess.Popen(
    cmd,
    env=env,
    stdout=out,
    stderr=err,
    text=True,
)
proc.wait()
print(f"exit: {proc.returncode}")
out.close()
err.close()
