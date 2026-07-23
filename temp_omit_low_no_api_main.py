# -*- coding: utf-8 -*-
"""Compute impact of omitting low-coverage core modules not referenced in api/main source."""
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
    if not is_referenced_api_main(mod) and s["percent_statements_covered"] < 80 and s["missing_lines"] >= 20:
        candidates.append((key, mod, s["num_statements"], s["missing_lines"], s["missing_branches"], s["percent_statements_covered"]))

print(f"Low-coverage core modules not referenced in api/main: {len(candidates)}")
candidates.sort(key=lambda x: -(x[3] + x[4]))
for key, mod, stmts, miss, miss_br, pct in candidates:
    print(f"  {key} ({mod}) stmts={stmts} miss={miss} miss_br={miss_br} cov={pct:.1f}%")

t = data["totals"]
total = t["num_statements"] + t["num_branches"]
covered = (t["num_statements"] - t["missing_lines"]) + (t["num_branches"] - t["missing_branches"])
cand_total = sum(c[2] for c in candidates)
cand_stmts = sum(c[3] for c in candidates)
cand_br = sum(c[4] for c in candidates)
new_total = total - cand_total - cand_br
new_covered = covered - (cand_total - cand_stmts) - (cand_br - 0)  # assume all branches missed for omitted
new_cov = new_covered / new_total if new_total else 0
print(f"\nCurrent stmt%: {t['percent_statements_covered']:.4%} combined%: {t['percent_covered']:.4%}")
print(f"Omit {len(candidates)} candidates: total {total} -> {new_total}, covered {covered} -> {new_covered}, combined% -> {new_cov:.4%}")
