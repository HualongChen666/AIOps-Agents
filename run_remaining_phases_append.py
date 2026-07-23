#!/usr/bin/env python
"""Run the remaining test phases for coverage sequentially using --append."""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PYTEST_INI = str(ROOT / "pytest_coverage.ini")

ROOT_TESTS = sorted(
    str(p) for p in (ROOT / "tests").glob("test_*.py") if "_integration" not in p.name
)

SMOKE_TESTS = [
    str(ROOT / "tests/core/test_active_smoke.py"),
    str(ROOT / "tests/core/test_active_method_smoke.py"),
    str(ROOT / "tests/core/test_low_coverage_method_smoke.py"),
]

PHASES = [
    ("root", ROOT_TESTS),
    ("main_import", [str(ROOT / "tests/test_main_import.py")]),
    ("main_routes", [str(ROOT / "tests/test_main_app_routes.py")]),
    ("main_post_routes", [str(ROOT / "tests/test_main_app_post_routes.py")]),
    ("smoke", SMOKE_TESTS),
]


def run_phase(name: str, targets: list[str]) -> int:
    cmd = [
        sys.executable,
        "-m",
        "coverage",
        "run",
        "--append",
        "-m",
        "pytest",
        "-c",
        PYTEST_INI,
        *targets,
        "-m",
        "not performance",
        "-n0",
        "--tb=short",
        "-q",
    ]
    env = os.environ.copy()
    env["PYTEST_ADDOPTS"] = ""
    print(f"\n=== Running {name} phase ===")
    print(" ".join(cmd))
    rc = subprocess.call(cmd, env=env)
    print(f"{name} phase exit: {rc}")
    return rc


def main() -> int:
    results = []
    for name, targets in PHASES:
        rc = run_phase(name, targets)
        results.append((name, rc))
        if rc != 0 and name != "smoke":
            print(f"Stopping after {name} failure (exit {rc})")
            return 1

    print("\n=== Generating coverage reports ===")
    reports = (
        [sys.executable, "-m", "coverage", "json", "-o", "coverage.json"],
        [sys.executable, "-m", "coverage", "xml", "-o", "coverage.xml"],
        [sys.executable, "-m", "coverage", "html", "-d", "htmlcov"],
        [sys.executable, "-m", "coverage", "report", "-m"],
    )
    for report_cmd in reports:
        subprocess.call(report_cmd)

    print("\n=== Summary ===")
    for name, rc in results:
        print(f"{name}: {'PASS' if rc == 0 else 'FAIL'} (exit {rc})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
