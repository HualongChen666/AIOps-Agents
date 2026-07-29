#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify one Phase-5 enterprise service and append results to temp/phase5_remaining.json."""

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path("C:/AIOps_Agent_bak")
PYTHON = sys.executable

SERVICES = [
    ("fastapi_security_service", "Task70"),
    ("sqlalchemy_security_service", "Task71"),
    ("elasticsearch_audit_service", "Task72"),
    ("velero_backup_service", "Task73"),
    ("pgbackrest_backup_service", "Task74"),
    ("datacenter_visualization_service", "Task75"),
    ("chaos_mesh_service", "Task76"),
    ("incident_runbook_service", "Task77"),
    ("capacity_planning_service", "Task78"),
]

JSON_FILE = ROOT / "temp" / "phase5_remaining.json"
LOG_FILE = ROOT / "temp" / "phase5_remaining.log"


def log(msg: str) -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"{ts} {msg}"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    safe = line.encode("ascii", "replace").decode("ascii")
    print(safe, flush=True)


def load_results() -> list[dict]:
    if JSON_FILE.exists():
        try:
            return json.loads(JSON_FILE.read_text(encoding="utf-8"))
        except Exception as e:
            log(f"json load failed: {e}")
    return []


def save_results(results: list[dict]) -> None:
    JSON_FILE.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")


def run(name: str, cmd: list[str], env: dict[str, str], timeout: int = 55) -> tuple[int, str]:
    log(f"RUN {name}")
    try:
        proc = subprocess.run(
            cmd,
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or "") + "\n--- TIMEOUT STDERR ---\n" + (e.stderr or "")
        log(f"TIMEOUT {name} after {timeout}s")
        return 1, out
    out = proc.stdout
    if proc.stderr:
        out += "\n--- STDERR ---\n" + proc.stderr
    log(f"DONE {name}: rc={proc.returncode} len={len(out)}")
    return proc.returncode, out


def parse_passed(output: str) -> str:
    m = re.search(r"(\d+) passed", output)
    return m.group(0) if m else "0 passed"


def parse_total_cov(output: str) -> tuple[str, str]:
    for line in reversed(output.splitlines()):
        if line.strip().startswith("TOTAL"):
            parts = line.strip().split()
            return line.strip(), parts[-1] if parts else ""
    return "", ""


def verify_service(svc: str, task: str, base_env: dict[str, str]) -> dict:
    log(f"START {task} {svc}")
    src_dir = f"services/{svc}"
    test_dir = f"tests/services/{svc}"
    data_file = f".coverage_phase5_{svc}"

    svc_res = {"service": svc, "task": task, "commands": []}

    # tests + coverage
    cov_cmd = [
        PYTHON,
        "-m",
        "coverage",
        "run",
        f"--data-file={data_file}",
        "-m",
        "pytest",
        "-o",
        "addopts=",
        "-q",
        "--tb=short",
        test_dir,
    ]
    rc, out = run("pytest", cov_cmd, base_env, timeout=55)
    svc_res["commands"].append(
        {"name": "pytest", "returncode": rc, "output": out[:4000], "passed": parse_passed(out)}
    )

    # coverage report
    report_cmd = [PYTHON, "-m", "coverage", "report", f"--data-file={data_file}", "--show-missing"]
    rc, out = run("coverage-report", report_cmd, base_env, timeout=55)
    total_line, cov_pct = parse_total_cov(out)
    svc_res["commands"].append(
        {
            "name": "coverage-report",
            "returncode": rc,
            "output": out[:4000],
            "total_coverage": total_line,
            "coverage_pct": cov_pct,
        }
    )

    # lint / type / security
    for tool, args in [
        ("black", [PYTHON, "-m", "black", "--check", src_dir, test_dir]),
        ("isort", [PYTHON, "-m", "isort", "--check-only", src_dir, test_dir]),
        ("flake8", [PYTHON, "-m", "flake8", src_dir, test_dir]),
        ("mypy", [PYTHON, "-m", "mypy", src_dir]),
        ("bandit", [PYTHON, "-m", "bandit", "-r", src_dir]),
    ]:
        rc, out = run(tool, args, base_env, timeout=55)
        svc_res["commands"].append({"name": tool, "returncode": rc, "output": out[:3000]})

    log(f"FINISHED {task} {svc}")
    return svc_res


def main() -> int:
    idx = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    if idx < 0 or idx >= len(SERVICES):
        log(f"invalid index {idx}")
        return 1

    svc, task = SERVICES[idx]
    base_env = os.environ.copy()
    base_env["PYTHONIOENCODING"] = "utf-8"

    results = load_results()
    done = {r["service"] for r in results}
    if svc in done:
        log(f"SKIP {task} {svc} already done")
        return 0

    result = verify_service(svc, task, base_env)
    results.append(result)
    save_results(results)
    log("DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
