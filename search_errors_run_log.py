# -*- coding: utf-8 -*-
"""Search run.log for Traceback and Python errors."""
from pathlib import Path
src = Path("run.log")
text = src.read_text(encoding="utf-16", errors="ignore")
lines = text.splitlines()

for i, line in enumerate(lines):
    if "Traceback" in line or "Error" in line and not line.startswith("INFO:") and not line.startswith("ERROR:core.") and not line.startswith("ERROR:api."):
        print(f"{i}: {line}")
