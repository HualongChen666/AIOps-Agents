# -*- coding: utf-8 -*-
"""Secure wrapper around the stdlib ``subprocess`` module.

All ``subprocess`` usage in the codebase should import from this module so
that Bandit only has to ignore the centralized ``B404`` / ``B603`` findings
in this single file. The wrapper validates the command argument, rejects
``shell=True``, and resolves the executable to an absolute path before
invoking the real ``subprocess`` functions.
"""

import shutil
import subprocess  # nosec B404
from typing import Any

__all__ = [
    "run",
    "Popen",
    "check_output",
    "check_call",
    "call",
    "PIPE",
    "STDOUT",
    "DEVNULL",
    "CompletedProcess",
    "CalledProcessError",
    "TimeoutExpired",
    "SubprocessError",
    "CREATE_NEW_CONSOLE",
]


def _resolve_cmd(args: tuple[Any, ...]) -> list[str]:
    """Validate and resolve the command to an absolute path."""
    if len(args) != 1:
        raise ValueError("subprocess_runner expects a single command argument (string or sequence)")

    raw = args[0]
    if isinstance(raw, str):
        cmd = [raw]
    elif isinstance(raw, (list, tuple)):
        cmd = [str(item) for item in raw]
    else:
        cmd = [str(raw)]

    if not cmd or not cmd[0]:
        raise ValueError("command argument cannot be empty")

    executable = cmd[0]
    resolved = shutil.which(executable)
    if resolved is None:
        raise FileNotFoundError(f"command not found or not executable: {executable}")

    cmd[0] = resolved
    return cmd


def run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[Any]:
    """Secure replacement for ``subprocess.run``."""
    if kwargs.get("shell"):
        raise ValueError("shell=True is not allowed in subprocess_runner")
    cmd = _resolve_cmd(args)
    return subprocess.run(cmd, **kwargs)  # nosec B603


class Popen(subprocess.Popen[Any]):
    """Secure subclass of ``subprocess.Popen``."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        if kwargs.get("shell"):
            raise ValueError("shell=True is not allowed in subprocess_runner")
        cmd = _resolve_cmd(args)
        super().__init__(cmd, **kwargs)  # nosec B603


def check_output(*args: Any, **kwargs: Any) -> Any:
    """Secure replacement for ``subprocess.check_output``."""
    if kwargs.get("shell"):
        raise ValueError("shell=True is not allowed in subprocess_runner")
    cmd = _resolve_cmd(args)
    return subprocess.check_output(cmd, **kwargs)  # nosec B603


def check_call(*args: Any, **kwargs: Any) -> Any:
    """Secure replacement for ``subprocess.check_call``."""
    if kwargs.get("shell"):
        raise ValueError("shell=True is not allowed in subprocess_runner")
    cmd = _resolve_cmd(args)
    return subprocess.check_call(cmd, **kwargs)  # nosec B603


def call(*args: Any, **kwargs: Any) -> Any:
    """Secure replacement for ``subprocess.call``."""
    if kwargs.get("shell"):
        raise ValueError("shell=True is not allowed in subprocess_runner")
    cmd = _resolve_cmd(args)
    return subprocess.call(cmd, **kwargs)  # nosec B603


# Re-export frequently-used constants and exceptions.
PIPE = subprocess.PIPE
STDOUT = subprocess.STDOUT
DEVNULL = subprocess.DEVNULL
CompletedProcess = subprocess.CompletedProcess
CalledProcessError = subprocess.CalledProcessError
TimeoutExpired = subprocess.TimeoutExpired
SubprocessError = subprocess.SubprocessError
CREATE_NEW_CONSOLE = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
