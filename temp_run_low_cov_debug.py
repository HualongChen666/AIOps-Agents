import os
import subprocess
import sys
from pathlib import Path

ROOT = Path.cwd()
PYTEST_INI = str(ROOT / "pytest_coverage.ini")
log_file = ROOT / "low_cov_debug.log"
err_file = ROOT / "low_cov_debug_err.log"

cmd = [
    sys.executable,
    "-m",
    "pytest",
    "-c",
    PYTEST_INI,
    "-p",
    "no:cov",
    "tests/core/test_low_coverage_method_smoke.py",
    "-m",
    "not performance",
    "-n0",
    "-v",
    "--tb=line",
    "-x",
    "-o",
    "timeout=15",
]
env = os.environ.copy()
env["PYTEST_ADDOPTS"] = ""

with open(log_file, "w", encoding="utf-8") as out, open(err_file, "w", encoding="utf-8") as err:
    proc = subprocess.Popen(cmd, env=env, stdout=out, stderr=err, text=True)
    rc = proc.wait()
print(f"exit: {rc}")
