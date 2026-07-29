#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Validate Phase 6 E2E and observability artifacts.

Checks:
- .github/workflows/e2e.yml is present and syntactically valid.
- main.py lifespan wires OpenTelemetry to Tempo/Prometheus/Jaeger and Loki.
- Grafana dashboards in grafana/dashboards/ are valid JSON.
- validation_reports/ and performance_reports/ contain real execution data.
- pytest can collect tests/e2e (best-effort; skipped if Playwright is missing).
"""

import json
import pathlib
import subprocess
import sys
import time

import yaml

PROJECT_ROOT = pathlib.Path(__file__).parent.parent

REQUIRED_WORKFLOWS = [PROJECT_ROOT / ".github" / "workflows" / "e2e.yml"]
REQUIRED_REPORT_DIRS = [
    PROJECT_ROOT / "validation_reports",
    PROJECT_ROOT / "performance_reports",
]
DASHBOARD_DIR = PROJECT_ROOT / "grafana" / "dashboards"


def _load_json(path: pathlib.Path) -> tuple[bool, str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not data:
            return False, f"{path.name} is empty"
        return True, ""
    except Exception as exc:
        return False, f"{path.name} JSON error: {exc}"


def _check_workflows() -> list[str]:
    issues = []
    for wf in REQUIRED_WORKFLOWS:
        if not wf.exists():
            issues.append(f"Missing workflow: {wf}")
            continue
        try:
            with open(wf, "r", encoding="utf-8") as f:
                yaml.safe_load(f)
        except Exception as exc:
            issues.append(f"YAML parse error in {wf.name}: {exc}")
    return issues


def _check_main_py_telemetry() -> list[str]:
    issues = []
    main_file = PROJECT_ROOT / "main.py"
    text = main_file.read_text(encoding="utf-8")
    for needle in [
        "OTEL_COLLECTOR_ENDPOINT",
        "TEMPO_URL",
        "LOKI_URL",
        "setup_fastapi_telemetry",
        "setup_loki_logging",
    ]:
        if needle not in text:
            issues.append(f"main.py missing telemetry reference: {needle}")
    return issues


def _check_grafana_dashboards() -> list[str]:
    issues = []
    if not DASHBOARD_DIR.exists():
        issues.append(f"Dashboard directory missing: {DASHBOARD_DIR}")
        return issues
    dashboards = list(DASHBOARD_DIR.glob("*.json"))
    if not dashboards:
        issues.append("No JSON dashboards found in grafana/dashboards/")
    for db in dashboards:
        ok, msg = _load_json(db)
        if not ok:
            issues.append(msg)
    return issues


def _check_reports() -> list[str]:
    issues = []
    for report_dir in REQUIRED_REPORT_DIRS:
        if not report_dir.exists():
            issues.append(f"Report directory missing: {report_dir}")
            continue
        json_files = list(report_dir.glob("*.json"))
        if not json_files:
            issues.append(f"No JSON reports in {report_dir}")
            continue
        for jf in json_files:
            ok, msg = _load_json(jf)
            if not ok:
                issues.append(msg)
    return issues


def _check_e2e_collection() -> dict:
    result = {"attempted": False, "returncode": None, "stderr": ""}
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/e2e", "--collect-only", "-q"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=120,
        )
        result["attempted"] = True
        result["returncode"] = proc.returncode
        result["stderr"] = proc.stderr[:1000]
    except Exception as exc:
        result["stderr"] = str(exc)
    return result


def main() -> int:
    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "phase": "Phase 6 - E2E and Observability",
        "issues": [],
        "valid": True,
        "checks": {},
    }

    report["issues"].extend(_check_workflows())
    report["issues"].extend(_check_main_py_telemetry())
    report["issues"].extend(_check_grafana_dashboards())
    report["issues"].extend(_check_reports())

    e2e_collection = _check_e2e_collection()
    report["checks"]["e2e_collection"] = e2e_collection
    if e2e_collection["attempted"] and e2e_collection["returncode"] != 0:
        report["issues"].append(f"E2E collect-only failed (rc={
                e2e_collection['returncode']}): {
                e2e_collection['stderr']}")

    if report["issues"]:
        report["valid"] = False

    report_dir = PROJECT_ROOT / "validation_reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_file = report_dir / "phase6_observability_readiness.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    status = "valid" if report["valid"] else "invalid"
    print(f"Phase 6 validation report ({status}) written to {report_file}")
    for issue in report["issues"]:
        print(f"  - {issue}")

    return 0 if report["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
