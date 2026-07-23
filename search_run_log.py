# -*- coding: utf-8 -*-
"""Search run.log for key markers."""
from pathlib import Path

log_path = Path("run.log")
text = log_path.read_text(encoding="utf-8", errors="ignore")
lines = text.splitlines()
print(f"Total lines: {len(lines)}")

markers = ["=== Running", "=== Summary ===", "short test summary", "passed", "failed"]
for marker in markers:
    print(f"\n--- '{marker}' occurrences ---")
    found = [line for line in lines if marker in line]
    for line in found[-20:]:
        print(line)
