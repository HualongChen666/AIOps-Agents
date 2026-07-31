#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Final per-service verification for tasks 62-69 after enhancements."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

from core.security import subprocess_runner

ROOT = Path("C:/AIOps_Agent_bak")
PYTHON = sys.executable
ENVS = os.environ.copy()
ENVS["PYTHONIOENCODING"] = "utf-8"

SERVICES = [
    ("62", "prometheus_integration_service", "Prometheus集成（任务62）"),
    ("63", "grafana_integration_service", "Grafana集成（任务63）"),
    ("64", "elk_stack_service", "ELK Stack集成（任务64）"),
    ("65", "datadog_integration_service", "Datadog集成（任务65）"),
    ("66", "cloud_monitoring_service", "云监控集成（任务66）"),
    ("67", "ansible_automation_service", "Ansible自动化（任务67）"),
    ("68", "terraform_iac_service", "Terraform基础设施即代码（任务68）"),
    ("69", "kubernetes_orchestration_service", "Kubernetes容器编排（任务69）"),
]


def run(cmd: list[str]) -> tuple[int, str, str]:
    proc = subprocess_runner.run(
        cmd,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=ENVS,
    )
    return proc.returncode, proc.stdout, proc.stderr


def file_metrics(service_dir: Path) -> dict[str, int]:
    pass_lines = 0
    notimplemented_lines = 0
    todo_lines = 0
    for f in service_dir.rglob("*.py"):
        if "__pycache__" in f.parts or "test_" in f.name:
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        pass_lines += text.count("pass")
        notimplemented_lines += text.count("NotImplementedError")
        todo_lines += len(re.findall(r"TODO|FIXME|XXX", text, re.IGNORECASE))
    return {
        "noop_lines": pass_lines,
        "notimplemented_lines": notimplemented_lines,
        "todo_lines": todo_lines,
    }


def list_files(service_dir: Path) -> dict[str, bool]:
    return {
        "has_readme": (service_dir / "README.md").is_file(),
        "has_dockerfile": (service_dir / "Dockerfile").is_file(),
        "has_k8s": (service_dir / "k8s").is_dir(),
        "has_prometheus": (service_dir / "prometheus.yml").is_file(),
        "has_docker_compose": (service_dir / "docker-compose.yml").is_file(),
        "has_architecture": (service_dir / "architecture.md").is_file(),
    }


def count_python_files(service_dir: Path) -> int:
    return len([f for f in service_dir.rglob("*.py") if "__pycache__" not in f.parts])


def extract_coverage_percent(report: str) -> str:
    m = re.search(r"TOTAL\s+\d+\s+\d+\s+\d+\s+\d+\s+(\d+%)", report)
    if m:
        return m.group(1)
    return "unknown"


def main() -> int:
    json_path = ROOT / "verify_logs" / "tasks_62_69_final_verification.json"
    txt_path = ROOT / "verify_logs" / "phase4_enhanced_verify.txt"
    results = []

    cov_dir = ROOT / "verify_logs" / "cov_configs"
    cov_dir.mkdir(parents=True, exist_ok=True)

    with open(txt_path, "w", encoding="utf-8") as log:
        for task, service, title in SERVICES:
            sdir = ROOT / "services" / service
            tdir = ROOT / "tests" / "services" / service
            log.write(f"\n=== Task {task} {title} ({service}) ===\n")
            print(f"[Task {task}] {service}")

            files_info = list_files(sdir)
            metrics = file_metrics(sdir)
            metrics["python_files"] = count_python_files(sdir)
            log.write(f"files: {json.dumps(files_info, ensure_ascii=False)}\n")
            log.write(f"metrics: {json.dumps(metrics, ensure_ascii=False)}\n")

            black_rc, black_out, black_err = run(
                [PYTHON, "-m", "black", "--check", str(sdir), str(tdir)]
            )
            log.write(f"black rc={black_rc}\n{black_err}{black_out}\n")

            isort_rc, isort_out, isort_err = run(
                [PYTHON, "-m", "isort", "--check-only", str(sdir), str(tdir)]
            )
            log.write(f"isort rc={isort_rc}\n{isort_err}{isort_out}\n")

            flake8_rc, flake8_out, flake8_err = run([PYTHON, "-m", "flake8", str(sdir), str(tdir)])
            log.write(f"flake8 rc={flake8_rc}\n{flake8_out}{flake8_err}\n")

            mypy_rc, mypy_out, mypy_err = run(
                [PYTHON, "-m", "mypy", "--ignore-missing-imports", str(sdir)]
            )
            log.write(f"mypy rc={mypy_rc}\n{mypy_out}{mypy_err}\n")

            bandit_rc, bandit_out, bandit_err = run([PYTHON, "-m", "bandit", "-r", str(sdir)])
            log.write(f"bandit rc={bandit_rc}\n{bandit_out}{bandit_err}\n")

            rc_file = cov_dir / f"coverage_{service}_enhanced.ini"
            rc_file.write_text(
                f"[run]\nsource = services/{service}\nbranch = True\n[report]\nshow_missing = False\n",  # noqa: E501
                encoding="utf-8",
            )
            cov_data = cov_dir / f".coverage_{service}_enhanced"
            cov_data.unlink(missing_ok=True)

            pytest_cmd = [
                PYTHON,
                "-m",
                "coverage",
                "run",
                "--data-file",
                str(cov_data),
                "--rcfile",
                str(rc_file),
                "-m",
                "pytest",
                str(tdir),
                "-o",
                "addopts=",
                "-q",
                "--tb=short",
                "--timeout=120",
            ]
            prc, pout, perr = run(pytest_cmd)
            log.write(f"pytest rc={prc}\n{pout}\n{perr}\n")

            report_cmd = [
                PYTHON,
                "-m",
                "coverage",
                "report",
                "--data-file",
                str(cov_data),
                "--rcfile",
                str(rc_file),
            ]
            rprc, rout, rerr = run(report_cmd)
            log.write(f"coverage rc={rprc}\n{rout}\n{rerr}\n")

            results.append(
                {
                    "task": task,
                    "service": service,
                    "title": title,
                    "files": files_info,
                    "metrics": metrics,
                    "black": {"rc": black_rc, "stdout": black_out, "stderr": black_err},
                    "isort": {"rc": isort_rc, "stdout": isort_out, "stderr": isort_err},
                    "flake8": {"rc": flake8_rc, "stdout": flake8_out, "stderr": flake8_err},
                    "mypy": {"rc": mypy_rc, "stdout": mypy_out, "stderr": mypy_err},
                    "bandit": {"rc": bandit_rc, "stdout": bandit_out, "stderr": bandit_err},
                    "pytest": {"rc": prc, "stdout": pout, "stderr": perr},
                    "coverage": {"rc": rprc, "report": rout, "stderr": rerr},
                    "coverage_total": extract_coverage_percent(rout),
                }
            )

    json_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote {json_path} and {txt_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
