# -*- coding: utf-8 -*-
"""Run the core/api/infrastructure test suite and stream stdout to a UTF-8 log."""
import subprocess
import sys
from pathlib import Path

log_path = Path("run_full.log")
cmd = [sys.executable, "-u", "scripts/run_core_api_infrastructure_tests.py"]

with log_path.open("wb") as f:
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:
        for line in proc.stdout:
            f.write(line)
            f.flush()
    finally:
        proc.wait()

print(f"Done. Log written to {log_path}. Exit code: {proc.returncode}")
