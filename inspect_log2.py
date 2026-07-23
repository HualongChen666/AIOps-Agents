# -*- coding: utf-8 -*-
"""Inspect end of run.log for phase markers and summary."""
from pathlib import Path

log_path = Path("run.log")
text = log_path.read_text(encoding="utf-16", errors="ignore")
lines = text.splitlines()
print(f"Total lines: {len(lines)}")
print("\n--- Last 100 lines ---\n")
for line in lines[-100:]:
    print(line)
