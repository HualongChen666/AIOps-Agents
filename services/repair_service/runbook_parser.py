# -*- coding: utf-8 -*-
"""Runbook YAML parser and loader."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from services.repair_service.schemas import PlatformType, RepairRunbook, RepairStep, RiskLevel

try:
    import yaml

    _YAML_AVAILABLE = True
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]
    _YAML_AVAILABLE = False


class RunbookParser:
    """Parse and validate YAML runbooks."""

    EXAMPLE_DIR: Path = Path(__file__).parent / "runbook_examples"

    @classmethod
    def from_yaml(cls, content: str) -> RepairRunbook:
        """Parse runbook from YAML string."""
        if not _YAML_AVAILABLE:
            raise RuntimeError("PyYAML is not installed")
        data = yaml.safe_load(content)
        if not isinstance(data, dict):
            raise ValueError("Runbook YAML must be a mapping")
        return cls._build_runbook(data)

    @classmethod
    def from_file(cls, path: Path | str) -> RepairRunbook:
        """Parse runbook from YAML file."""
        raw = Path(path).read_text(encoding="utf-8")
        return cls.from_yaml(raw)

    @classmethod
    def list_example_runbooks(cls) -> List[str]:
        """Return list of available example runbook ids."""
        if not cls.EXAMPLE_DIR.exists():
            return []
        return [p.stem for p in cls.EXAMPLE_DIR.glob("*.yml")]

    @classmethod
    def load_example(cls, runbook_id: str) -> Optional[RepairRunbook]:
        """Load an example runbook by id."""
        path = cls.EXAMPLE_DIR / f"{runbook_id}.yml"
        if not path.exists():
            return None
        return cls.from_file(path)

    @classmethod
    def _build_runbook(cls, data: Dict[str, Any]) -> RepairRunbook:
        steps_data = data.get("steps", [])
        if not isinstance(steps_data, list):
            raise ValueError("Runbook 'steps' must be a list")

        steps: List[RepairStep] = []
        for idx, step_data in enumerate(steps_data):
            if not isinstance(step_data, dict):
                raise ValueError(f"Step {idx} must be a mapping")
            steps.append(
                RepairStep(
                    name=step_data.get("name", f"step-{idx}"),
                    command=step_data.get("command", ""),
                    timeout_seconds=int(step_data.get("timeout_seconds", 60)),
                    rollback_command=step_data.get("rollback_command"),
                    verify_command=step_data.get("verify_command"),
                )
            )

        return RepairRunbook(
            runbook_id=data["runbook_id"],
            name=data.get("name", data["runbook_id"]),
            description=data.get("description", ""),
            platform=PlatformType(data.get("platform", "linux")),
            risk_level=RiskLevel(data.get("risk_level", "low")),
            steps=steps,
            params=data.get("params", {}),
        )

    @staticmethod
    def render_command(command: str, params: Dict[str, Any]) -> str:
        """Render command template with params, similar to repair_engine."""
        result = command
        for key, value in params.items():
            placeholder = f"{{{key}}}"
            result = result.replace(placeholder, str(value))
        # Leave unreplaced placeholders as-is
        return result

    @staticmethod
    def validate(runbook: RepairRunbook) -> List[str]:
        """Validate runbook and return list of errors."""
        errors: List[str] = []
        if not runbook.runbook_id:
            errors.append("runbook_id is required")
        if not runbook.steps:
            errors.append("runbook must contain at least one step")
        for idx, step in enumerate(runbook.steps):
            if not step.command:
                errors.append(f"Step {idx} ({step.name}) has empty command")
        return errors


def get_runbook_catalog() -> Dict[str, str]:
    """Return id -> description mapping for all example runbooks."""
    catalog: Dict[str, str] = {}
    for runbook_id in RunbookParser.list_example_runbooks():
        try:
            runbook = RunbookParser.load_example(runbook_id)
            if runbook:
                catalog[runbook_id] = runbook.description or runbook.name
        except Exception as e:
            logger.warning(f"Failed to load runbook {runbook_id}: {e}")
    return catalog
