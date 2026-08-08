# -*- coding: utf-8 -*-
"""Docker repair functionality with safe command execution and persistent history."""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from config import BASE_DIR

logger = logging.getLogger(__name__)

_DOCKER_SCRIPTS: Dict[str, Dict[str, Any]] = {
    "restart_container": {
        "description": "Restart a Docker container by name",
        "requires": ["container"],
        "command_factory": lambda host, params: ["docker", "restart", params["container"]],
        "read_only": False,
    },
    "inspect_container": {
        "description": "Inspect a Docker container",
        "requires": ["container"],
        "command_factory": lambda host, params: ["docker", "inspect", params["container"]],
        "read_only": True,
    },
    "container_stats": {
        "description": "Show stats for all containers (no-stream)",
        "requires": [],
        "command_factory": lambda host, params: ["docker", "stats", "--no-stream"],
        "read_only": True,
    },
    "prune_images": {
        "description": "Remove unused Docker images",
        "requires": [],
        "command_factory": lambda host, params: ["docker", "image", "prune", "-f"],
        "read_only": False,
    },
    "ps": {
        "description": "List running containers",
        "requires": [],
        "command_factory": lambda host, params: ["docker", "ps"],
        "read_only": True,
    },
}

_HISTORY_FILE: Path = BASE_DIR / "data" / "docker_repair_history.json"


def _load_history() -> List[Dict[str, Any]]:
    try:
        if _HISTORY_FILE.is_file():
            return json.loads(_HISTORY_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning(f"Failed to load docker repair history: {e}")
    return []


def _save_history(history: List[Dict[str, Any]]) -> None:
    try:
        _HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        _HISTORY_FILE.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        logger.warning(f"Failed to save docker repair history: {e}")


def get_docker_repair_scripts() -> Dict[str, Any]:
    """Return available Docker repair scripts metadata."""
    return {
        key: {"description": meta["description"], "requires": meta["requires"], "read_only": meta["read_only"]}
        for key, meta in _DOCKER_SCRIPTS.items()
    }


def get_docker_repair_history(limit: int = 100) -> List[Dict[str, Any]]:
    """Return recent Docker repair history."""
    history = _load_history()
    return history[-limit:] if limit else history


async def execute_repair_sync(
    host_name: str, script_key: str, params: Dict[str, str]
) -> Dict[str, Any]:
    """Execute a Docker repair script and record the result.

    Safety: destructive commands require ``params["force"] == "true"`` and
    will still only run if the ``docker`` CLI is available. By default the
    command is simulated (dry-run) to avoid accidental changes.
    """
    meta = _DOCKER_SCRIPTS.get(script_key)
    if not meta:
        return {
            "success": False,
            "error": f"Unknown docker repair script: {script_key}",
            "host": host_name,
        }

    missing = [r for r in meta["requires"] if r not in params]
    if missing:
        return {
            "success": False,
            "error": f"Missing required params: {missing}",
            "host": host_name,
            "script": script_key,
        }

    dry_run = str(params.get("force", "")).lower() not in ("true", "1", "yes")
    command = meta["command_factory"](host_name, params)
    timestamp = datetime.now(timezone.utc).isoformat()
    docker_available = shutil.which("docker") is not None

    result: Dict[str, Any] = {
        "host": host_name,
        "script": script_key,
        "command": command,
        "params": params,
        "timestamp": timestamp,
        "dry_run": dry_run,
        "docker_available": docker_available,
    }

    if not docker_available:
        result["success"] = True
        result["output"] = "docker CLI not available; command simulated"
        _record(result)
        return result

    if dry_run:
        result["success"] = True
        result["output"] = f"Dry-run would execute: {' '.join(command)}"
        _record(result)
        return result

    try:
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        result["success"] = proc.returncode == 0
        result["returncode"] = proc.returncode
        result["stdout"] = proc.stdout[:2000]
        result["stderr"] = proc.stderr[:2000]
    except Exception as e:
        result["success"] = False
        result["error"] = str(e)

    _record(result)
    return result


def _record(record: Dict[str, Any]) -> None:
    history = _load_history()
    history.append(record)
    _save_history(history[-500:])
