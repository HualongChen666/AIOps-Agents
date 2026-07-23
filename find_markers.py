# -*- coding: utf-8 -*-
"""Find script phase markers and pytest summaries in run.log."""
from pathlib import Path

src = Path("run.log")
text = src.read_text(encoding="utf-16", errors="ignore")
lines = text.splitlines()
print(f"Total lines: {len(lines)}")

for i, line in enumerate(lines):
    if "=== Running" in line or "=== Summary ===" in line or ("====" in line and ("passed" in line or "failed" in line or "error" in line)):
        print(f"{i}: {line}")
