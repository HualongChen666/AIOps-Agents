import subprocess
import sys
import re
import os

SERVICES = [
    "service_mesh_service",
    "tracing_service",
    "alert_rule_service",
    "message_queue_service",
    "workflow_engine_service",
    "kafka_event_service",
]
TEST_PATHS = [f"tests/services/{s}" for s in SERVICES]
SVC_PATHS = [f"services/{s}" for s in SERVICES]


def run_step(name, cmd, cwd=None):
    print(f"\n>>> {name}")
    print(f"$ {' '.join(cmd)}")
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
        env=env,
    )
    tail = (proc.stdout + proc.stderr)[-4000:]
    print(tail)
    return proc.returncode


def pytest_summary(stdout):
    combined = stdout
    m = re.findall(r"(\d+ passed(?:, \d+ failed)?(?:, \d+ error)? in [\d\.]+s)", combined)
    return m[-1] if m else "unknown"


def main():
    base = "c:/AIOps_Agent_bak"
    results = []

    # pytest
    rc = run_step(
        "pytest",
        [sys.executable, "-m", "pytest"] + TEST_PATHS + ["-q", "--tb=short", "--no-header", "--disable-warnings", "-rN"],
        cwd=base,
    )
    results.append(("pytest", rc))

    # black check
    rc = run_step("black --check", [sys.executable, "-m", "black", "--check"] + SVC_PATHS, cwd=base)
    results.append(("black", rc))

    # ruff / flake8 / isort fallback
    rc = run_step("run_ruff", [sys.executable, "scripts/run_ruff.py"] + SVC_PATHS, cwd=base)
    results.append(("run_ruff", rc))

    # isort check
    rc = run_step("isort --check-only", [sys.executable, "-m", "isort", "--check-only"] + SVC_PATHS, cwd=base)
    results.append(("isort", rc))

    # mypy
    rc = run_step("mypy", [sys.executable, "-m", "mypy"] + SVC_PATHS, cwd=base)
    results.append(("mypy", rc))

    print("\n" + "=" * 60)
    print("Phase 3 Verification Summary")
    print("=" * 60)
    for name, rc in results:
        status = "PASS" if rc == 0 else "FAIL"
        print(f"  {name:<25} {status}")
    overall = "PASS" if all(rc == 0 for _, rc in results) else "FAIL"
    print("-" * 60)
    print(f"  Overall: {overall}")
    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
