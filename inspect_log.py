# -*- coding: utf-8 -*-
"""Inspect run.log around core summary."""
from pathlib import Path

log_path = Path("run.log")
text = log_path.read_text(encoding="utf-16", errors="ignore")
lines = text.splitlines()
print(f"Total lines: {len(lines)}")
# find core summary
for i, line in enumerate(lines):
    if "5087 passed" in line:
        print(f"\n--- Around core summary (line {i}) ---")
        start = max(0, i - 20)
        end = min(len(lines), i + 50)
        for j in range(start, end):
            print(lines[j])
        break
