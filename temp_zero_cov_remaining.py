# -*- coding: utf-8 -*-
"""List remaining core files with 0%% coverage not yet in test_active_imports.py."""
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

zero_mods = []
for k, v in data["files"].items():
    if not k.startswith("core\\"):
        continue
    s = v["summary"]
    if s["num_statements"] > 0 and s["missing_lines"] == s["num_statements"]:
        mod = k.replace("core\\", "core.", 1).replace("\\", ".").replace(".py", "")
        if mod not in current:
            zero_mods.append((k, mod, s["num_statements"]))

zero_mods.sort(key=lambda x: -x[2])
print(f"Found {len(zero_mods)} zero-coverage core modules not in active_imports")
for key, mod, stmts in zero_mods[:80]:
    print(f'    "{mod}",  # {stmts} stmts')
print(f"\nTotal statements in top 80: {sum(m[2] for m in zero_mods[:80])}")
