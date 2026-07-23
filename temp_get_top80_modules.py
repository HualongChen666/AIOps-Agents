# -*- coding: utf-8 -*-
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
with open(ROOT / "coverage.json", "r", encoding="utf-8") as f:
    data = json.load(f)

mods = []
for k, v in data["files"].items():
    if not k.startswith("core\\"):
        continue
    summary = v["summary"]
    if summary["percent_covered"] < 80 and summary["num_statements"] > 0:
        mods.append((k, summary["missing_lines"]))

mods.sort(key=lambda x: -x[1])
for k, _ in mods[:80]:
    mod = k.replace("core\\", "core.", 1).replace("\\", ".").replace(".py", "")
    print(f'    "{mod}",')
