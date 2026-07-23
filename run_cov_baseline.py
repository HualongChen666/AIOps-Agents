import subprocess
import sys
from pathlib import Path

log = Path("cov_baseline.log")
with log.open("w", encoding="utf-8") as f:
    rc = subprocess.call(
        [sys.executable, "scripts/run_core_api_infrastructure_tests.py"],
        stdout=f,
        stderr=subprocess.STDOUT,
    )
    f.write(f"\nEXIT_CODE: {rc}\n")
print("COVERAGE_BASELINE_EXIT:", rc)
