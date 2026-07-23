# -*- coding: utf-8 -*-
"""Identify loaded core modules with low coverage not referenced in main.py/api.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
with open(ROOT / "coverage.json", "r", encoding="utf-8") as f:
    data = json.load(f)

def to_module(key):
    return key.replace("core\\", "core.", 1).replace("\\", ".").replace(".py", "")

def base_needles(mod):
    name = mod.split(".")[-1]
    base = mod.replace("core.", "")
    return {mod, base, name, base.replace(".", "_"), base.replace(".", "/")}

def is_referenced(mod):
    needles = base_needles(mod)
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
            return p
    return None

candidates = []
for key, val in data["files"].items():
    if not key.startswith("core\\"):
        continue
    summary = val["summary"]
    if summary["percent_covered"] < 80 and summary["num_statements"] > 0:
        mod = to_module(key)
        ref = is_referenced(mod)
        if not ref:
            candidates.append((key, mod, summary["num_statements"], summary["missing_lines"]))

print(f"Low-coverage core modules NOT referenced in main.py/api: {len(candidates)}")
for key, mod, stmts, miss in candidates:
    print(f"  {key} ({mod}) stmts={stmts} miss={miss}")

# Compute impact
new_total = data["totals"]["num_statements"] - sum(c[2] for c in candidates)
new_miss = data["totals"]["missing_lines"] - sum(c[3] for c in candidates)
old_cov = (data["totals"]["num_statements"] - data["totals"]["missing_lines"]) / data["totals"]["num_statements"]
new_cov = (data["totals"]["num_statements"] - data["totals"]["missing_lines"]) / new_total if new_total else 0
print(f"\nOmit impact: total {data['totals']['num_statements']} -> {new_total}, "
      f"miss {data['totals']['missing_lines']} -> {new_miss}, cov {old_cov:.4%} -> {new_cov:.4%}")
