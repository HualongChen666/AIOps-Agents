#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Quick pytest run for a single phase-4 service."""

import subprocess
import sys
from pathlib import Path

ROOT = Path("C:/AIOps_Agent_bak")
SERVICE = "prometheus_integration_service"


def main() -> int:
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        f"tests/services/{SERVICE}",
        "-o",
        "addopts=",
        "-q",
        "--tb=short",
        "--timeout=120",
    ]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = ROOT / "verify_logs" / f"test_{SERVICE}.txt"
    out.write_text(f"returncode: {proc.returncode}\n\nSTDOUT:\n{proc.stdout}\n\nSTDERR:\n{proc.stderr}", encoding="utf-8")
    print(f"returncode: {proc.returncode}")
    print(proc.stdout[-2000:] if len(proc.stdout) > 2000 else proc.stdout)
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
