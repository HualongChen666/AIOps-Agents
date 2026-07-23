#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run mypy on Phase 6 generated services."""

import subprocess
import sys
from pathlib import Path

ROOT = Path("C:/AIOps_Agent_bak")
NAMES = [
    "sphinx_documentation",
    "security_audit",
    "backup_recovery_drill",
    "incident_response",
    "github_repository",
    "open_source_license",
    "plugin_system",
    "plugin_market",
    "api_standards",
    "data_standards",
    "performance_monitoring",
    "cache_optimization",
    "database_optimization",
    "security_scanning",
    "penetration_testing",
    "automated_deployment",
    "automated_ops",
    "log_aggregation",
    "metrics_monitoring",
    "distributed_tracing",
]

paths = [str(ROOT / "services" / f"{name}_service") for name in NAMES]
cmd = [
    sys.executable,
    "-m",
    "mypy",
    *paths,
    "--ignore-missing-imports",
    "--no-error-summary",
]
result = subprocess.run(cmd, cwd=str(ROOT))
sys.exit(result.returncode)
