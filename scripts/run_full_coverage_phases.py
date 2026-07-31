#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Run core/api/infrastructure tests in isolated, non-parallel pytest sessions
and produce a combined coverage report.

This avoids xdist coverage data-loss while keeping phases isolated.
"""

import os
import sys
from pathlib import Path

from core.security import subprocess_runner

_ROOT = Path(__file__).resolve().parents[1]
ROOT_TESTS = sorted(
    str(p) for p in (_ROOT / "tests").glob("test_*.py") if "_integration" not in p.name
)

SMOKE_TESTS = [
    "tests/core/test_active_smoke.py",
    "tests/core/test_active_method_smoke.py",
    "tests/core/test_low_coverage_method_smoke.py",
]

PHASES = [
    ("core", ["tests/core"]),
    ("api", ["tests/api"]),
    ("infrastructure", ["tests/infrastructure"]),
    ("unit", ["tests/unit"]),
    ("root", ROOT_TESTS),
    ("main_import", ["tests/test_main_import.py"]),
    ("main_routes", ["tests/test_main_app_routes.py"]),
    ("main_post_routes", ["tests/test_main_app_post_routes.py"]),
    # smoke temporarily disabled due to network/Redis hangs; will re-enable after omission strategy
    # ("smoke", SMOKE_TESTS),
]


def run_phase(name: str, targets: list[str]) -> int:
    data_file = f".coverage.{name}"
    cmd = [
        sys.executable,
        "-m",
        "coverage",
        "run",
        "--data-file",
        data_file,
        "-m",
        "pytest",
        "-c",
        str(_ROOT / "pytest_coverage.ini"),
        *targets,
        "-m",
        "not performance",
        "-n0",
        "--tb=short",
        "-q",
    ]
    if name == "core":
        for smoke in SMOKE_TESTS:
            cmd.extend(["--ignore", smoke])
    env = os.environ.copy()
    # Use the isolated pytest config and ignore any external pytest addopts
    env["PYTEST_ADDOPTS"] = ""
    print(f"\n=== Running {name} tests ===")
    print(" ".join(cmd))
    return subprocess_runner.call(cmd, env=env)


def main() -> int:
    # Start from a clean coverage data file
    for name in (".coverage", "coverage.json", "coverage.xml"):
        try:
            os.remove(name)
        except FileNotFoundError:
            pass
    # Remove any leftover per-phase coverage data files
    for p in _ROOT.glob(".coverage.*"):
        p.unlink()

    results = []
    for name, targets in PHASES:
        rc = run_phase(name, targets)
        results.append((name, rc))

    # Combine per-phase coverage data into the final .coverage file
    print("\n=== Combining coverage data ===")
    combine_cmd = [sys.executable, "-m", "coverage", "combine"]
    subprocess_runner.call(combine_cmd)

    # Generate combined coverage reports from accumulated data
    print("\n=== Generating coverage reports ===")
    for report_cmd in (
        [sys.executable, "-m", "coverage", "json", "-o", "coverage.json"],
        [sys.executable, "-m", "coverage", "xml", "-o", "coverage.xml"],
        [sys.executable, "-m", "coverage", "html", "-d", "htmlcov"],
        [sys.executable, "-m", "coverage", "report", "-m"],
    ):
        subprocess_runner.call(report_cmd)

    print("\n=== Summary ===")
    any_failed = False
    for name, rc in results:
        status = "PASS" if rc == 0 else "FAIL"
        print(f"{name}: {status} (exit {rc})")
        if rc != 0:
            any_failed = True

    return 1 if any_failed else 0


if __name__ == "__main__":
    sys.exit(main())
