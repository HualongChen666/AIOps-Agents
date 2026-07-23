import os
import subprocess
import sys
from pathlib import Path

ROOT = Path.cwd()
PYTEST_INI = str(ROOT / "pytest_coverage.ini")
log_path = ROOT / "low_cov_smoke.log"
err_path = ROOT / "low_cov_smoke_err.log"

cmd = [
    sys.executable,
    "-m",
    "pytest",
    "-c",
    PYTEST_INI,
    "tests/core/test_low_coverage_method_smoke.py",
    "-m",
    "not performance",
    "-n0",
    "--tb=short",
    "-q",
]
env = os.environ.copy()
env["PYTEST_ADDOPTS"] = ""
with open(log_path, "w", encoding="utf-8") as out, open(err_path, "w", encoding="utf-8") as err:
    proc = subprocess.Popen(cmd, env=env, stdout=out, stderr=err, text=True)
    rc = proc.wait()
print(f"exit: {rc}")
