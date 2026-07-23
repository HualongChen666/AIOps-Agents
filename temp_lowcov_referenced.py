# -*- coding: utf-8 -*-
"""List low-coverage core modules with reference status and missing stmts."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
with open(ROOT / "coverage.json", "r", encoding="utf-8") as f:
    data = json.load(f)

def to_module(key):
    return key.replace("core\\", "core.", 1).replace("\\", ".").replace(".py", "")

def is_referenced(mod):
    base = mod.replace("core.", "")
    name = mod.split(".")[-1]
    needles = {mod, base, name, base.replace(".", "\\"), base.replace(".", "_")}
    regex = re.compile("|".join(re.escape(n) for n in needles if n))
    targets = list((ROOT / "api").rglob("*.py")) + [ROOT / "main.py"]
    for p in targets:
        if "__pycache__" in p.parts:
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except Exception:
            continue
        if regex.search(text):
            return True
    return False

mods = []
for k, v in data["files"].items():
    if not k.startswith("core\\"):
        continue
    s = v["summary"]
    if s["percent_covered"] < 80 and s["num_statements"] > 0:
        mod = to_module(k)
        mods.append((k, mod, s["num_statements"], s["missing_lines"], is_referenced(mod)))

mods.sort(key=lambda x: -x[3])
print(f"Low-coverage core modules: {len(mods)}")
for key, mod, stmts, miss, ref in mods:
    print(f"{ref!s:5} {stmts:4} {miss:4} {key} ({mod})")
