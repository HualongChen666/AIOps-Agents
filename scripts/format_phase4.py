#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Format all phase-4 service directories with black and isort."""

import os
import sys
from pathlib import Path

from core.security import subprocess_runner

sys.path.insert(0, str(Path(__file__).resolve().parent))
from service_paths import service_relpath, tests_relpath  # noqa: E402

ROOT = Path(os.getenv("AIOPS_ROOT", Path(__file__).resolve().parents[1]))
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
        targets = [service_relpath(svc)]
        svc_tests = tests_relpath(svc)
        if svc_tests:
            targets.append(svc_tests)
        r1 = run(["black", *targets])
        if r1.returncode != 0:
            print(f"  black rc={r1.returncode}")
            print(r1.stderr[:500])
        r2 = run(["isort", *targets])
        if r2.returncode != 0:
            print(f"  isort rc={r2.returncode}")
            print(r2.stderr[:500])
    print("Done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
