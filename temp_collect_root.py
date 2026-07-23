import subprocess
import sys
from pathlib import Path

ROOT = Path.cwd()
PYTEST_INI = str(ROOT / "pytest_coverage.ini")
tests = sorted(
    str(p) for p in (ROOT / "tests").glob("test_*.py") if "_integration" not in p.name
)
print(f"Collecting {len(tests)} root test files")
cmd = [
    sys.executable,
    "-m",
    "pytest",
    "-c",
    PYTEST_INI,
    *tests,
    "-m",
    "not performance",
    "--collect-only",
    "-q",
]
import os
env = os.environ.copy()
env["PYTEST_ADDOPTS"] = ""
result = subprocess.run(cmd, env=env, capture_output=True, text=True, errors="ignore")
print("STDOUT:", result.stdout[-5000:])
print("STDERR:", result.stderr[-5000:])
print("exit:", result.returncode)
