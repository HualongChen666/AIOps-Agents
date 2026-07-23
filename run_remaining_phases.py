import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PYTEST_INI = str(ROOT / "pytest_coverage.ini")

PHASES = [
    ("infrastructure", [str(ROOT / "tests" / "infrastructure")]),
    ("unit", [str(ROOT / "tests" / "unit")]),
    (
        "root",
        [str(p) for p in sorted((ROOT / "tests").glob("test_*.py"))],
    ),
    ("main_import", [str(ROOT / "tests" / "test_main_import.py")]),
    ("main_routes", [str(ROOT / "tests" / "test_main_app_routes.py")]),
    ("main_post_routes", [str(ROOT / "tests" / "test_main_app_post_routes.py")]),
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
    print(f"\n=== Running {name} tests ===")
    print(" ".join(cmd))
    return subprocess.call(cmd, env=env)


def main() -> int:
    results = []
    for name, targets in PHASES:
        rc = run_phase(name, targets)
        results.append((name, rc))
        if rc != 0:
            print(f"Warning: {name} phase exited with {rc}; continuing")

    print("\n=== Generating coverage reports ===")
    for report_cmd in (
        [sys.executable, "-m", "coverage", "json", "-o", "coverage.json"],
        [sys.executable, "-m", "coverage", "xml", "-o", "coverage.xml"],
        [sys.executable, "-m", "coverage", "html", "-d", "htmlcov"],
        [sys.executable, "-m", "coverage", "report", "-m"],
    ):
        subprocess.call(report_cmd)

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
