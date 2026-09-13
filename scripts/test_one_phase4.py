#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Quick pytest run for a single phase-4 service."""

import os
import sys
from pathlib import Path

from core.security import subprocess_runner

sys.path.insert(0, str(Path(__file__).resolve().parent))
from service_paths import tests_relpath  # noqa: E402

ROOT = Path(os.getenv("AIOPS_ROOT", Path(__file__).resolve().parents[1]))
SERVICE = "prometheus_integration_service"


def main() -> int:
    svc_tests = tests_relpath(SERVICE)
    if svc_tests is None:
        print(f"No test directory found for {SERVICE}; nothing to run.")
        return 0
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        svc_tests,
        "-o",
        "addopts=",
        "-q",
        "--tb=short",
        "--timeout=120",
    ]
    proc = subprocess_runner.run(
        cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    out = ROOT / "verify_logs" / f"test_{SERVICE}.txt"
    out.write_text(
        f"returncode: {proc.returncode}\n\nSTDOUT:\n{proc.stdout}\n\nSTDERR:\n{proc.stderr}",
        encoding="utf-8",
    )
    print(f"returncode: {proc.returncode}")
    print(proc.stdout[-2000:] if len(proc.stdout) > 2000 else proc.stdout)
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
