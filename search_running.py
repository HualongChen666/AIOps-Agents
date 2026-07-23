# -*- coding: utf-8 -*-
"""Search run.log for 'Running' markers."""
from pathlib import Path
src = Path("run.log")
text = src.read_text(encoding="utf-16", errors="ignore")
lines = text.splitlines()
for i, line in enumerate(lines):
    if "running" in line.lower() and ("Running api" in line or "Running core" in line or "Running infrastructure" in line or "tests" in line):
        if "Running api" in line or "Running core" in line or "Running infrastructure" in line or "Running unit" in line or "Running root" in line or "=== Running" in line:
            print(f"{i}: {line}")
