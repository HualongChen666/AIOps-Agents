# -*- coding: utf-8 -*-
"""Read run.log and print all '====' lines and last 50 lines."""
from pathlib import Path

src = Path("run.log")
text = src.read_text(encoding="utf-16", errors="ignore")
lines = text.splitlines()
print(f"Total lines: {len(lines)}")
print("\n--- All '====' containing lines ---")
for i, line in enumerate(lines):
    if "====" in line and ("passed" in line.lower() or "failed" in line.lower() or "error" in line.lower()):
        print(f"{i}: {line}")
print("\n--- Last 50 lines ---")
for line in lines[-50:]:
    print(line)
