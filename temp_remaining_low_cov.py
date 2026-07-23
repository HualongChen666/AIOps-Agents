# -*- coding: utf-8 -*-
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
with open(ROOT / "coverage.json", "r", encoding="utf-8") as f:
    data = json.load(f)

current = set()
for line in (ROOT / "tests" / "core" / "test_active_imports.py").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if line.startswith('"core.'):
        current.add(line.strip('",'))

mods = []
for k, v in data["files"].items():
    if not k.startswith("core\\"):
        continue
    summary = v["summary"]
    if summary["percent_covered"] < 80 and summary["num_statements"] > 0:
        mod = k.replace("core\\", "core.", 1).replace("\\", ".").replace(".py", "")
        if mod not in current:
            mods.append((mod, summary["missing_lines"]))

mods.sort(key=lambda x: -x[1])
for m, miss in mods:
    print(f'    "{m}",  # missing {miss}')
