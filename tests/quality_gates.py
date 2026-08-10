# -*- coding: utf-8 -*-
"""Quality gate helpers for CI/CD integration scripts."""

import json
from pathlib import Path


def load_quality_gates(config_path: str | None = None) -> dict:
    """Load quality gate configuration from a JSON file."""
    if not config_path:
        config_path = str(Path(__file__).parent.parent / ".github" / "quality_gates.json")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}
