# -*- coding: utf-8 -*-
"""Search run.log for key markers (case-insensitive)."""
from pathlib import Path

log_path = Path("run.log")
text = log_path.read_text(encoding="utf-8", errors="ignore")
lines = text.splitlines()
print(f"Total lines: {len(lines)}")

markers = ["=== Running", "=== Summary", "short test summary", "passed", "failed", "Running", "Summary"]
for marker in markers:
    found = [i for i, line in enumerate(lines) if marker.lower() in line.lower()]
    print(f"\n'{marker}' matches: {len(found)}")
    if found:
        print("Last 10 matching line numbers:", found[-10:])
        for i in found[-5:]:
            print(f"{i}: {lines[i]}")
