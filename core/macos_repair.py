# -*- coding: utf-8 -*-
"""
macOS Repair Module for AIOps Platform

Provides repair functionality for macOS systems.
"""

import asyncio
import json
import logging
import os
import shlex
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

SCRIPT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts", "macos")

# Captured at import time so the resolvers below stay correct even when tests
# monkeypatch the module-level ``os`` attribute.
_REAL_SEP = os.sep
_REAL_ALTSEP = os.altsep
_REAL_ISABS = os.path.isabs


def _resolve_script_path(script_name: str) -> Optional[str]:
    """Resolve a *bare* macOS repair script name to a concrete executable path.

    Security: only names inside ``scripts/macos`` (or a bare command name looked
    up on ``PATH``) are accepted. Absolute paths and any name containing a path
    separator or ``..`` are rejected so a caller can never point the executor at
    an arbitrary file on the host.
    """
    if not script_name:
        return None
    if (
        _REAL_ISABS(script_name)
        or _REAL_SEP in script_name
        or (_REAL_ALTSEP and _REAL_ALTSEP in script_name)
        or ".." in script_name.split("/")
    ):
        logger.warning("Rejected macOS repair script name outside scripts/macos: %r", script_name)
        return None

    for candidate in (script_name, f"{script_name}.sh"):
        full = os.path.join(SCRIPT_DIR, candidate)
        if os.path.isfile(full):
            return os.path.abspath(full)

    # Bare command name available on PATH – kept for backward compatibility
    # with deployments that install the repair helpers globally.
    return script_name


async def execute_macos_repair(
    host: str, script_name: str, args: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Execute a repair script on a macOS host

    Args:
        host: Target macOS host
        script_name: Name of the repair script to execute (validated against scripts/macos)
        args: Additional arguments for the script

    Returns:
        Execution result with status and output
    """
    args = args or {}
    start = time.monotonic()

    try:
        logger.info(f"Executing macOS repair script {script_name} on host {host}")

        if host not in ("localhost", "127.0.0.1", "::1"):
            raise RuntimeError(f"Remote macOS repair is not supported for host {host}")

        # Only scripts resolved inside scripts/macos (or bare PATH commands) run.
        script_path = _resolve_script_path(script_name)
        if script_path is None:
            raise ValueError(
                f"Invalid macOS repair script name: {script_name!r} "
                "(must be a bare name resolved from scripts/macos)"
            )

        env = os.environ.copy()
        if args:
            env["AIOPS_ARGS"] = json.dumps(args)
            for key, value in args.items():
                env[f"AIOPS_ARG_{str(key).upper()}"] = str(value)

        cmd = shlex.quote(script_path)
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        duration = time.monotonic() - start
        output = stdout.decode(errors="replace") + stderr.decode(errors="replace")

        result = {
            "status": "success" if proc.returncode == 0 else "error",
            "output": output,
            "exit_code": proc.returncode,
            "duration": round(duration, 3),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        logger.info(f"macOS repair script {script_name} completed on {host}")
        return result

    except Exception as e:
        duration = time.monotonic() - start
        logger.error(f"Failed to execute macOS repair script {script_name} on {host}: {e}")
        return {
            "status": "error",
            "output": str(e),
            "exit_code": 1,
            "duration": round(duration, 3),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


def get_available_macos_scripts() -> list[str]:
    """Get list of available macOS repair scripts discovered from scripts/macos."""
    if not os.path.isdir(SCRIPT_DIR):
        return []

    scripts: list[str] = []
    for entry in os.listdir(SCRIPT_DIR):
        full_path = os.path.join(SCRIPT_DIR, entry)
        if os.path.isfile(full_path):
            name, _ = os.path.splitext(entry)
            scripts.append(name)
    return sorted(scripts)


__all__ = ["execute_macos_repair", "get_available_macos_scripts"]
