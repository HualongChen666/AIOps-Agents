#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
"""Run core/api/infrastructure tests in isolated pytest sessions.

This avoids cross-module ``sys.modules`` pollution between ``tests/api``
(which mocks core modules at import time) and ``tests/core``.

Usage:
    python scripts/run_core_api_infrastructure_tests.py [extra pytest args]
"""

import glob
import os
import shutil
import subprocess
import sys
from pathlib import Path

try:
    from coverage import Coverage
except Exception as e:
    logging.exception("Unexpected exception: %s", e)
    Coverage = None

_ROOT = Path(__file__).resolve().parents[1]
ROOT_TESTS = sorted(
    str(p) for p in (_ROOT / "tests").glob("test_*.py") if "_integration" not in p.name
)

PHASES = [
    ("core", ["tests/core"]),
    ("api", ["tests/api"]),
    ("infrastructure", ["tests/infrastructure"]),
    ("unit", ["tests/unit"]),
    # ("root", ROOT_TESTS),
    # ("main_import", ["tests/test_main_import.py"]),
    ("main_routes", ["tests/test_main_app_routes.py"]),
    ("main_post_routes", ["tests/test_main_app_post_routes.py"]),
]


def _clean_coverage() -> None:
    for pattern in (".coverage", ".coverage.*", ".coverage_*", "coverage.json", "coverage.xml"):
        for path in Path(".").glob(pattern):
            try:
                if path.is_dir():
                    shutil.rmtree(path, ignore_errors=True)
                else:
                    path.unlink()
            except FileNotFoundError:
                pass
    if Path("htmlcov").exists():
        shutil.rmtree("htmlcov", ignore_errors=True)


def run_phase(name: str, targets: list[str], extra: list[str]) -> int:
    # Use a unique coverage data file basename per phase so xdist worker data
    # from different phases does not overwrite each other.  ``parallel=True`` in
    # .coveragerc will cause pytest-cov to write .coverage_phase_<name>.* files.
    # Per-phase coverage reports are disabled here; reports are generated after
    # all phases are combined.
    n_workers = "auto"
    dist = ""
    if name == "api":
        # API tests mock sys.modules at import time; keep each test file in its
        # own worker to avoid cross-file mock contamination.
        n_workers = str(len(list(_ROOT.joinpath("tests/api").glob("test_*.py"))))
        dist = " --dist=loadfile"
    addopts = (
        "--strict-markers --disable-warnings --tb=short --verbose --showlocals "
        f"-n {n_workers} --cov=core --cov=api --cov-append -m 'not performance'{dist}"
    )
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        *targets,
        "-o",
        f"addopts={addopts}",
        "--timeout=120",
        *extra,
    ]
    env = os.environ.copy()
    env["PYTEST_ADDOPTS"] = ""
    env["COVERAGE_FILE"] = f".coverage_phase_{name}"

    print(f"\n=== Running {name} tests ===")
    print(" ".join(cmd))
    return subprocess.call(cmd, env=env)


def _combine_and_report() -> None:
    print("\n=== Combining phase coverage data ===")
    phase_files = sorted(glob.glob(".coverage_phase_*"))
    if not phase_files:
        print("No phase coverage data files found")
        return

    if Coverage is not None:
        cov = Coverage(config_file=".coveragerc")
        cov.load()
        cov.combine(phase_files, keep=False)
        cov.save()
        try:
            cov.json_report(outfile="coverage.json")
        except Exception as exc:
            print(f"JSON report failed: {exc}")
        try:
            cov.html_report(directory="htmlcov")
        except Exception as exc:
            print(f"HTML report failed: {exc}")
        try:
            cov.xml_report(outfile="coverage.xml")
        except Exception as exc:
            print(f"XML report failed: {exc}")
    else:
        subprocess.run(
            [sys.executable, "-m", "coverage", "combine", "-q", *phase_files], check=False
        )
        subprocess.run(
            [sys.executable, "-m", "coverage", "json", "-o", "coverage.json"], check=False
        )
        subprocess.run([sys.executable, "-m", "coverage", "html", "-d", "htmlcov"], check=False)
        subprocess.run([sys.executable, "-m", "coverage", "xml", "-o", "coverage.xml"], check=False)

    if Path("cov_summary.py").exists():
        subprocess.run([sys.executable, "cov_summary.py"], check=False)

    print(f"Combined {len(phase_files)} phase coverage data files")


def main() -> int:
    _clean_coverage()
    extra = sys.argv[1:]
    results = []
    for name, targets in PHASES:
        rc = run_phase(name, targets, extra)
        results.append((name, rc))

    _combine_and_report()

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