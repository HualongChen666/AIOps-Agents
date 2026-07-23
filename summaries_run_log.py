# -*- coding: utf-8 -*-
"""Extract all pytest summary lines from run.log."""
from pathlib import Path
import re

src = Path("run.log")
text = src.read_text(encoding="utf-16", errors="ignore")
lines = text.splitlines()

print(f"Total lines: {len(lines)}")
print("\n--- All pytest summary lines ('====' containing passed/failed/error) ---\n")
pattern = re.compile(r"==== .* (passed|failed|error|errors).*(?:====|=====)")
for i, line in enumerate(lines):
    if "passed" in line and (line.startswith("====") or "====" in line):
        print(f"{i}: {line}")
    if "failed" in line and "====" in line:
        print(f"{i}: {line}")
    if line.startswith("FAILED"):
        print(f"{i}: {line}")
