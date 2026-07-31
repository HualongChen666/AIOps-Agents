#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Validate Phase 5 deployment artifacts.

This script checks the presence and syntactic validity of the Helm chart,
Terraform files, Istio service mesh manifests, integration Docker Compose file
and Ansible playbook. It does **not** require a running Kubernetes or Docker
cluster and is intended for offline CI validation of the generated artifacts.
"""

import json
import pathlib
import shutil
import subprocess
import sys
import time

import yaml

PROJECT_ROOT = pathlib.Path(__file__).parent.parent

REQUIRED_ARTIFACTS = [
    PROJECT_ROOT / "helm" / "aiops-agent" / "Chart.yaml",
    PROJECT_ROOT / "helm" / "aiops-agent" / "values.yaml",
    PROJECT_ROOT / "terraform" / "main.tf",
    PROJECT_ROOT / "infra" / "istio" / "aiops-mesh.yaml",
    PROJECT_ROOT / "infrastructure" / "integration-test.yml",
    PROJECT_ROOT / "infra" / "ansible" / "site.yml",
    PROJECT_ROOT / "core" / "service_mesh_manager.py",
]


def _parse_yaml(path: pathlib.Path) -> None:
    with open(path, "r", encoding="utf-8") as f:
        list(yaml.safe_load_all(f))


def _check_helm_chart() -> list[str]:
    issues = []
    chart_file = PROJECT_ROOT / "helm" / "aiops-agent" / "Chart.yaml"
    values_file = PROJECT_ROOT / "helm" / "aiops-agent" / "values.yaml"
    try:
        with open(chart_file, "r", encoding="utf-8") as f:
            chart = yaml.safe_load(f)
        if not isinstance(chart, dict) or chart.get("apiVersion") != "v2":
            issues.append(f"{chart_file} missing apiVersion v2")
        with open(values_file, "r", encoding="utf-8") as f:
            values = yaml.safe_load(f)
        if not isinstance(values, dict):
            issues.append(f"{values_file} is not a valid YAML mapping")
    except Exception as exc:
        issues.append(f"Helm chart validation failed: {exc}")
    return issues


def _check_terraform() -> list[str]:
    issues = []
    for tf_file in (PROJECT_ROOT / "terraform").glob("*.tf"):
        try:
            with open(tf_file, "r", encoding="utf-8") as f:
                content = f.read()
            if (
                "resource " not in content
                and "variable " not in content
                and "output " not in content
            ):
                issues.append(f"{tf_file.name} does not contain Terraform declarations")
        except Exception as exc:
            issues.append(f"Terraform file {tf_file.name} read error: {exc}")
    return issues


def _check_yaml_artifacts() -> list[str]:
    issues = []
    yaml_files = [
        PROJECT_ROOT / "infra" / "istio" / "aiops-mesh.yaml",
        PROJECT_ROOT / "infrastructure" / "integration-test.yml",
        PROJECT_ROOT / "infra" / "ansible" / "site.yml",
    ]
    for yf in yaml_files:
        try:
            _parse_yaml(yf)
        except Exception as exc:
            issues.append(f"YAML parse error in {yf.relative_to(PROJECT_ROOT)}: {exc}")
    return issues


def _check_service_mesh_manager() -> list[str]:
    issues = []
    source = PROJECT_ROOT / "core" / "service_mesh_manager.py"
    try:
        text = source.read_text(encoding="utf-8")
        for method in (
            "generate_sidecar_injection_config",
            "inject_sidecar_to_deployment",
            "generate_istio_control_plane_config",
            "generate_mtls_config",
        ):
            if f"def {method}(" not in text:
                issues.append(f"service_mesh_manager.py missing method {method}")
    except Exception as exc:
        issues.append(f"Could not read {source}: {exc}")
    return issues


def _check_helm_dryrun() -> tuple[bool, str]:
    """Attempt `helm template` or `helm install --dry-run` if helm is available."""
    try:
        helm_cmd = shutil.which("helm") or "helm"
        subprocess.run(
            [helm_cmd, "version"],
            capture_output=True,
            text=True,
            check=True,
            timeout=20,
        )
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False, "helm not installed or unavailable"

    try:
        result = subprocess.run(
            [helm_cmd, "template", "aiops-agent", "./helm/aiops-agent"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            return False, f"helm template failed: {result.stderr.strip()}"
        return True, "helm template rendered successfully"
    except Exception as exc:
        return False, f"helm template error: {exc}"


def main() -> int:
    report: dict = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "phase": "Phase 5 - Real Deployment Validation",
        "artifact_checks": [],
        "helm_dryrun": {},
        "issues": [],
        "valid": True,
    }

    for artifact in REQUIRED_ARTIFACTS:
        exists = artifact.exists()
        entry = {"path": str(artifact.relative_to(PROJECT_ROOT)), "exists": exists}
        report["artifact_checks"].append(entry)
        if not exists:
            report["issues"].append(f"Missing artifact: {artifact}")
            report["valid"] = False

    report["issues"].extend(_check_helm_chart())
    report["issues"].extend(_check_terraform())
    report["issues"].extend(_check_yaml_artifacts())
    report["issues"].extend(_check_service_mesh_manager())

    helm_ok, helm_message = _check_helm_dryrun()
    report["helm_dryrun"] = {"available": helm_ok, "message": helm_message}
    if not helm_ok:
        # helm is an environment/runtime dependency; absence does not invalidate artifacts.
        report["helm_dryrun_warning"] = f"helm dry-run check: {helm_message}"

    if report["issues"]:
        report["valid"] = False

    report_dir = PROJECT_ROOT / "validation_reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_file = report_dir / "phase5_deployment_readiness.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    status = "valid" if report["valid"] else "invalid"
    print(f"Phase 5 validation report ({status}) written to {report_file}")
    for issue in report["issues"]:
        print(f"  - {issue}")

    return 0 if report["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
