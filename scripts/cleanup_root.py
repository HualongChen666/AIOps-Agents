# -*- coding: utf-8 -*-
"""Conservative productization cleanup for the repository root.

Removes generated reports, build logs, temporary scripts, .bak files and the
vendored ``external/`` directory.  Runs in dry-run mode unless ``--execute`` is
passed.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

KEEP_DIRS = {
    ".git",
    ".github",
    ".devin",
    ".windsurf",
    ".venv",
    "venv",
    "alembic",
    "alertmanager",
    "alerts",
    "api",
    "config",
    "config_env",
    "core",
    "dashboards",
    "data",
    "docs",
    "examples",
    "extensions",
    "frontend",
    "grafana",
    "helm",
    "infra",
    "infrastructure",
    "integration_docs",
    "k8s_manifests",
    "loki-config",
    "messages",
    "modules",
    "monitoring",
    "otel-config",
    "pgpool",
    "plugins",
    "postgres",
    "prometheus",
    "proto",
    "scripts",
    "sdk",
    "services",
    "static",
    "tempo",
    "tempo-config",
    "terraform",
    "test_data",
    "tests",
    "victoria-config",
    "vulnerability_data",
}

# Root files that are part of the real project.
KEEP_FILES = {
    ".bandit",
    ".coveragerc",
    ".devinignore",
    ".dockerignore",
    ".flake8",
    ".gitignore",
    ".pre-commit-config.yaml",
    "AGENTS.md",
    "CHANGELOG.md",
    "CI_CD_CONFIG_CHANGES.md",
    "CI_CD_SETUP.md",
    "CI_CD_TASK_SUMMARY.md",
    "CODE_OF_CONDUCT.md",
    "CONTRIBUTING.md",
    "CONTEXT.md",
    "Dockerfile",
    "LICENSE",
    "Makefile",
    "README.md",
    "SECURITY.md",
    "alembic.ini",
    "config.py",
    "conftest.py",
    "docker-compose.database.yml",
    "docker-compose.e2e.yml",
    "docker-compose.monitoring.yml",
    "docker-compose.prod.yml",
    "docker-compose.yml",
    "env.example",
    "env.production.template",
    "main.py",
    "mypy.ini",
    "mypy_simple.ini",
    "openapi.json",
    "openapi.yaml",
    "otel-collector-config.yaml",
    "playwright.config.ts",
    "poetry.lock",
    "prometheus.yml",
    "pyproject.toml",
    "pytest.ini",
    "pytest.e2e.ini",
    "pytest_coverage.ini",
    "requirements.txt",
    "sitecustomize.py",
    "start.py",
    "task_list.md",
    "机柜展示示意图1.png",
    "机柜展示示意图2.png",
}


def remove_path(path: Path, execute: bool) -> None:
    action = "delete" if execute else "would delete"
    print(f"  {action}: {path.relative_to(ROOT)}")
    if execute:
        if path.is_dir():
            import shutil

            shutil.rmtree(path, ignore_errors=True)
        else:
            path.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean repository root")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually delete files (default is dry-run)",
    )
    args = parser.parse_args()

    deleted = 0

    # 1. Root level cleanup
    for entry in ROOT.iterdir():
        if entry.is_dir():
            if entry.name in KEEP_DIRS:
                continue
            remove_path(entry, args.execute)
            deleted += 1
            continue

        if entry.is_file() or entry.is_symlink():
            if entry.name in KEEP_FILES:
                continue
            remove_path(entry, args.execute)
            deleted += 1

    # 2. .bak files anywhere in the repo
    for bak in ROOT.rglob("*.bak"):
        remove_path(bak, args.execute)
        deleted += 1

    print(f"\nTotal items: {deleted}")
    if not args.execute:
        print("This was a dry-run. Pass --execute to delete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
