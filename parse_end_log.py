# -*- coding: utf-8 -*-
"""Read end of run_partial.log and search for pytest-cov/coverage errors."""
from pathlib import Path
p = Path("run_partial.log")
text = p.read_text(encoding="utf-16", errors="ignore")
lines = text.splitlines()
print(f"Total lines: {len(lines)}")
print("\n--- Last 100 lines ---\n")
for line in lines[-100:]:
    print(line)
print("\n--- Lines containing 'coverage' or 'cov' in last 500 ---\n")
for line in lines[-500:]:
    if "coverage" in line.lower() or "cov-" in line.lower() or "cov=" in line.lower():
        print(line)
