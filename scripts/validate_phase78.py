#!/usr/bin/env python
# -*- coding: utf-8 -*"
"""Validate Phase 7/8 open-source, documentation, SDK and CI/CD artifacts.

Checks:
- Required open-source files (LICENSE, CHANGELOG, SECURITY, etc.) are present.
- tests/open_source passes.
- docs/sphinx can build (best-effort; skipped if sphinx not installed).
- sdk/python, sdk/go, sdk/java demo files exist and are non-empty.
- api/schemas/examples.py contains at least 23 example models.
- main.py calls enhance_app_routes.
- .github/workflows/ci.yml enforces coverage>=85 and bandit/ruff/mypy.
- .github/workflows/release.yml exists and references v0.1.0 + Helm + Docker.
- helm/aiops-agent/Chart.yaml version is 0.1.0.
"""

import json
import os
import pathlib
import sys
import time

import yaml

from core.security import subprocess_runner

PROJECT_ROOT = pathlib.Path(__file__).parent.parent

REQUIRED_OPEN_FILES = [
    "LICENSE",
    "CODE_OF_CONDUCT.md",
    "SECURITY.md",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
]

REQUIRED_WORKFLOWS = [
    ".github/workflows/ci.yml",
    ".github/workflows/release.yml",
]

SDK_DEMOS = [
    "sdk/python/demo.py",
    "sdk/go/main.go",
    "sdk/java/src/main/java/AIOpsAgentDemo.java",
]


def _check_open_source() -> list[str]:
    issues = []
    for rel in REQUIRED_OPEN_FILES:
        path = PROJECT_ROOT / rel
        if not path.exists() or not path.read_text(encoding="utf-8").strip():
            issues.append(f"Missing or empty open-source file: {rel}")
    return issues


def _check_sphinx_build() -> dict:
    result = {"available": False, "ok": False, "message": ""}
    try:
        proc = subprocess_runner.run(
            [sys.executable, "-m", "sphinx", "--version"],
            capture_output=True,
            text=True,
            timeout=20,
        )
        result["available"] = proc.returncode == 0
    except Exception as exc:
        result["message"] = f"sphinx not available: {exc}"
        return result

    if not result["available"]:
        result["message"] = "sphinx not installed"
        return result

    try:
        proc = subprocess_runner.run(
            [
                sys.executable,
                "-m",
                "sphinx.cmd.build",
                str(PROJECT_ROOT / "docs" / "sphinx"),
                str(PROJECT_ROOT / "docs" / "_build"),
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=120,
        )
        result["ok"] = proc.returncode == 0
        result["message"] = proc.stderr[-500:] if not result["ok"] else "sphinx-build succeeded"
    except Exception as exc:
        result["message"] = f"sphinx-build error: {exc}"
    return result


def _check_sdk_demos() -> list[str]:
    issues = []
    for rel in SDK_DEMOS:
        path = PROJECT_ROOT / rel
        if not path.exists() or not path.read_text(encoding="utf-8").strip():
            issues.append(f"Missing or empty SDK demo: {rel}")
    return issues


def _check_pydantic_examples() -> list[str]:
    issues = []
    examples = PROJECT_ROOT / "api" / "schemas" / "examples.py"
    if not examples.exists():
        issues.append("api/schemas/examples.py missing")
        return issues
    text = examples.read_text(encoding="utf-8")
    count = text.count("class ") - text.count("class CodeSample")  # rough count
    if "EXAMPLE_MODELS" not in text:
        issues.append("EXAMPLE_MODELS list missing in api/schemas/examples.py")
    if count < 23:
        issues.append(f"Expected at least 23 example classes, found ~{count}")
    if "enhance_app_routes" not in (PROJECT_ROOT / "main.py").read_text(encoding="utf-8"):
        issues.append("main.py does not call enhance_app_routes")
    return issues


def _check_ci_workflow() -> list[str]:
    issues = []
    ci = PROJECT_ROOT / ".github" / "workflows" / "ci.yml"
    if not ci.exists():
        issues.append(".github/workflows/ci.yml missing")
        return issues
    try:
        with open(ci, "r", encoding="utf-8") as f:
            yaml.safe_load(f)
    except Exception as exc:
        issues.append(f"ci.yml parse error: {exc}")
        return issues

    text = ci.read_text(encoding="utf-8")
    if "COVERAGE_THRESHOLD: 85" not in text:
        issues.append("ci.yml does not set COVERAGE_THRESHOLD to 85")
    for token in ["ruff", "bandit", "mypy", "pytest"]:
        if token not in text:
            issues.append(f"ci.yml missing {token}")
    return issues


def _check_release_workflow() -> list[str]:
    issues = []
    rel = PROJECT_ROOT / ".github" / "workflows" / "release.yml"
    if not rel.exists():
        issues.append(".github/workflows/release.yml missing")
        return issues
    text = rel.read_text(encoding="utf-8")
    for token in ["v0.1.0", "helm", "Dockerfile", "aiops-agent-0.1.0"]:
        if token not in text:
            issues.append(f"release.yml missing reference to {token}")
    chart = PROJECT_ROOT / "helm" / "aiops-agent" / "Chart.yaml"
    if chart.exists() and "version: 0.1.0" not in chart.read_text(encoding="utf-8"):
        issues.append("Helm chart version is not 0.1.0")
    return issues


def _run_open_source_tests() -> dict:
    result = {"returncode": None, "stderr": ""}
    env = os.environ.copy()
    env["PYTEST_ADDOPTS"] = "--no-cov"
    try:
        proc = subprocess_runner.run(
            [sys.executable, "-m", "pytest", "tests/open_source", "-q"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=120,
            env=env,
        )
        result["returncode"] = proc.returncode
        result["stderr"] = proc.stderr[-500:]
    except Exception as exc:
        result["stderr"] = str(exc)
    return result


def main() -> int:
    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "phase": "Phase 7/8 - Open Source, Docs and CI/CD",
        "issues": [],
        "valid": True,
        "checks": {},
    }

    report["issues"].extend(_check_open_source())
    report["checks"]["sphinx_build"] = _check_sphinx_build()
    report["issues"].extend(_check_sdk_demos())
    report["issues"].extend(_check_pydantic_examples())
    report["issues"].extend(_check_ci_workflow())
    report["issues"].extend(_check_release_workflow())

    open_source_test = _run_open_source_tests()
    report["checks"]["open_source_tests"] = open_source_test
    if open_source_test["returncode"] != 0:
        report["issues"].append(f"tests/open_source failed (rc={
            open_source_test['returncode']}): {
            open_source_test['stderr']}")

    if report["issues"]:
        report["valid"] = False

    report_dir = PROJECT_ROOT / "validation_reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_file = report_dir / "phase78_opensource_cicd_readiness.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    status = "valid" if report["valid"] else "invalid"
    print(f"Phase 7/8 validation report ({status}) written to {report_file}")
    for issue in report["issues"]:
        print(f"  - {issue}")

    return 0 if report["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
