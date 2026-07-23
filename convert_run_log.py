# -*- coding: utf-8 -*-
"""Convert PowerShell UTF-16 log to UTF-8 and search markers."""
from pathlib import Path

log_path = Path("run.log")
out_path = Path("run_utf8.log")

text = log_path.read_text(encoding="utf-16", errors="ignore")
out_path.write_text(text, encoding="utf-8")

lines = text.splitlines()
print(f"Total lines: {len(lines)}")

markers = ["=== Running", "=== Summary", "short test summary", "FAILED", "passed", "failed", "error"]
for marker in markers:
    found = [i for i, line in enumerate(lines) if marker.lower() in line.lower()]
    print(f"\n'{marker}' matches: {len(found)}")
    if found:
        print("Last 5 matching line numbers:", found[-5:])
        for i in found[-5:]:
            print(f"{i}: {lines[i]}")
