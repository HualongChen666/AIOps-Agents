#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Format all phase-4 service directories with black and isort."""

import sys
from pathlib import Path

from core.security import subprocess_runner

ROOT = Path("C:/AIOps_Agent_bak")
PYTHON = sys.executable
SERVICES = [
    "prometheus_integration_service",
    "grafana_integration_service",
    "elk_stack_service",
    "datadog_integration_service",
    "cloud_monitoring_service",
    "ansible_automation_service",
    "terraform_iac_service",
    "kubernetes_orchestration_service",
]


def run(args):
    return subprocess_runner.run(
        [PYTHON, "-m"] + args,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def main():
    for svc in SERVICES:
        print(f"Formatting {svc} ...")
        r1 = run(["black", f"services/{svc}", f"tests/services/{svc}"])
        if r1.returncode != 0:
            print(f"  black rc={r1.returncode}")
            print(r1.stderr[:500])
        r2 = run(["isort", f"services/{svc}", f"tests/services/{svc}"])
        if r2.returncode != 0:
            print(f"  isort rc={r2.returncode}")
            print(r2.stderr[:500])
    print("Done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
