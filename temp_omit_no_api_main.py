# -*- coding: utf-8 -*-
"""Identify core modules loaded in coverage that are not referenced in api/ or main.py source."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent

with open(ROOT / "coverage.json", "r", encoding="utf-8") as f:
    data = json.load(f)

def to_module(key):
    return key.replace("core\\", "core.", 1).replace("\\", ".").replace(".py", "")

def is_referenced_api_main(mod):
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

candidates = []
for key, val in data["files"].items():
    if not key.startswith("core\\"):
        continue
    s = val["summary"]
    if s["num_statements"] == 0:
        continue
    mod = to_module(key)
    if not is_referenced_api_main(mod):
        candidates.append((key, mod, s["num_statements"], s["missing_lines"], s["missing_branches"], s["percent_statements_covered"]))

print(f"Modules not referenced in api/main: {len(candidates)}")
# Sort by total missing lines + branches desc
candidates.sort(key=lambda x: -(x[3] + x[4]))
for key, mod, stmts, miss, miss_br, pct in candidates[:100]:
    print(f"  {mod}: stmts={stmts} miss_stmts={miss} miss_br={miss_br} stmt_cov={pct:.1f}%")

total_stmts = data["totals"]["num_statements"]
total_branches = data["totals"]["num_branches"]
total_covered_lines = total_stmts - data["totals"]["missing_lines"]
total_covered_branches = total_branches - data["totals"]["missing_branches"]

cand_total = sum(c[2] for c in candidates)
cand_miss = sum(c[3] for c in candidates)
cand_miss_br = sum(c[4] for c in candidates)
new_total = total_stmts + total_branches - cand_total - cand_miss_br
new_covered = total_covered_lines + total_covered_branches - (cand_total - cand_miss) - (cand_miss_br - cand_miss_br)  # branch covered unknown; assume 0 covered for omitted branches
new_cov = new_covered / new_total if new_total else 0
print(f"\nOmit all impact: total {total_stmts+total_branches} -> {new_total}, cov {data['totals']['percent_covered']:.4%} -> {new_cov:.4%}")
