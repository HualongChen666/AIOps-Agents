# -*- coding: utf-8 -*-
"""Inspect start of run.log."""
from pathlib import Path

log_path = Path("run.log")
text = log_path.read_text(encoding="utf-16", errors="ignore")
lines = text.splitlines()
print(f"Total lines: {len(lines)}")
print("\n--- First 50 lines ---\n")
for line in lines[:50]:
    print(line)
