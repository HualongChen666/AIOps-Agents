#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Run accessibility support tests with coverage."""

import subprocess
import sys

def main():
    """Run tests with coverage."""
    # Run pytest with coverage for the specific module
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/core/test_accessibility_support.py",
        "-v",
        "--no-cov-on-fail",
        "--cov=core/accessibility_support",
        "--cov-report=term-missing",
        "--cov-report=html",
        "-n", "0"  # Disable parallel for coverage
    ]

    try:
        result = subprocess.run(cmd, check=True)
        return result.returncode
    except subprocess.CalledProcessError as e:
        print(f"Tests failed with return code {e.returncode}")
        return e.returncode

if __name__ == "__main__":
    sys.exit(main())
