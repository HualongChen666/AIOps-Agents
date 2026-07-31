#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging

"""Ruff runner with Windows App Control fallback.

Attempts to run ``ruff``. If the compiled ruff binary is blocked by Windows
Application Control (WinError 4551), it falls back to ``flake8`` for lint and
``isort --check-only`` for import order, which are pure Python and usually
allowed by App Control policies.

Usage:
    python scripts/run_ruff.py [paths...]
    python scripts/run_ruff.py check .
"""

import sys

from core.security import subprocess_runner


def ruff_available() -> bool:
    try:
        from ruff import find_ruff_bin

        ruff_bin = find_ruff_bin()
    except Exception as e:
        logging.exception("Unexpected exception: %s", e)
        return False
    try:
        rc = subprocess_runner.run(
            [str(ruff_bin), "--version"],
            stdout=subprocess_runner.DEVNULL,
            stderr=subprocess_runner.DEVNULL,
            timeout=10,
        ).returncode
        return rc == 0
    except (OSError, subprocess_runner.TimeoutExpired):
        return False


def run_ruff(args: list[str]) -> int:
    from ruff import find_ruff_bin

    ruff_bin = find_ruff_bin()
    cmd = [str(ruff_bin)] + args
    print(f"Running ruff: {' '.join(cmd)}")
    return subprocess_runner.call(cmd)


def run_fallback(targets: list[str]) -> int:
    print("ruff binary is blocked by Windows Application Control; using flake8 + isort fallback.")
    targets = targets or ["."]
    flake8_cmd = [sys.executable, "-m", "flake8"] + targets
    isort_cmd = [sys.executable, "-m", "isort", "--check-only"] + targets

    rc1 = subprocess_runner.call(flake8_cmd)
    rc2 = subprocess_runner.call(isort_cmd)
    return rc1 or rc2


def main() -> int:
    args = sys.argv[1:]
    if not args:
        args = ["check", "."]
    if ruff_available():
        return run_ruff(args)
    return run_fallback(args[1:] if args and args[0] == "check" else args)


if __name__ == "__main__":
    sys.exit(main())
