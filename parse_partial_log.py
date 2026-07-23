# -*- coding: utf-8 -*-
"""Extract pytest summary from run_partial.log (UTF-16)."""
from pathlib import Path
import re

p = Path("run_partial.log")
text = p.read_text(encoding="utf-16", errors="ignore")
lines = text.splitlines()

print(f"Total lines: {len(lines)}")

# Print all final summary lines and FAILED/ERROR lines
print("\n--- Final summary lines ---")
for i, line in enumerate(lines):
    if "FAILED" in line or "ERROR" in line or ("====" in line and ("passed" in line or "failed" in line)):
        print(f"{i}: {line}")

print("\n--- Last 50 lines ---")
for line in lines[-50:]:
    print(line)
