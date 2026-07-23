# -*- coding: utf-8 -*-
"""Print first 100 lines of run.log."""
from pathlib import Path
src = Path("run.log")
text = src.read_text(encoding="utf-16", errors="ignore")
lines = text.splitlines()
print(f"Total lines: {len(lines)}")
print("\n--- First 100 lines ---\n")
for line in lines[:100]:
    print(line)
