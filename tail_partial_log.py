# -*- coding: utf-8 -*-
from pathlib import Path

p = Path("run_partial.log")
if not p.exists():
    print("log not found")
else:
    text = p.read_text(encoding="utf-16", errors="ignore")
    lines = text.splitlines()
    print(f"Log lines: {len(lines)}")
    print("\n--- Last 40 lines ---\n")
    for line in lines[-40:]:
        print(line)
