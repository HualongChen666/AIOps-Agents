# -*- coding: utf-8 -*-
"""Print tail and some context of run.log."""
from pathlib import Path

log_path = Path("run.log")
text = log_path.read_text(encoding="utf-8", errors="ignore")
lines = text.splitlines()
print(f"Total lines: {len(lines)}")
print("\n--- Last 200 lines ---\n")
for line in lines[-200:]:
    print(line)
