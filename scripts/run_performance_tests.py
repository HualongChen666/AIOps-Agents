#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Run performance tests separately without xdist/coverage interference.

Usage:
    python scripts/run_performance_tests.py [extra pytest args]
"""

import os
import subprocess
import sys


def main() -> int:
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-m",
        "performance",
        "-n",
        "0",
        "--no-cov",
        "--timeout=0",
        "--tb=short",
        "-v",
    ]
    if sys.argv[1:]:
        cmd.extend(sys.argv[1:])

    # Clear PYTEST_ADDOPTS so inherited addopts don't accidentally add -n auto/--cov
    env = os.environ.copy()
    env["PYTEST_ADDOPTS"] = ""

    print("Running performance tests...")
    print(" ".join(cmd))
    return subprocess.call(cmd, env=env)


if __name__ == "__main__":
    sys.exit(main())
