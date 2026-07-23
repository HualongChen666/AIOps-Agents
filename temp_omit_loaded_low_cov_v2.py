# -*- coding: utf-8 -*-
"""Compute omit impact for low-coverage loaded core modules not in main.py/api."""
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
    needles = {mod, base, mod.split(".")[-1], base.replace(".", "\\"), base.replace(".", "_")}
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

core_files = [(k, v) for k, v in data["files"].items() if k.startswith("core\\")]
candidates = []
for key, val in core_files:
    summary = val["summary"]
    if summary["percent_covered"] < 80 and summary["num_statements"] > 0:
        mod = to_module(key)
        if not is_referenced(mod):
            candidates.append((key, mod, summary["num_statements"], summary["missing_lines"]))

total = sum(c[2] for c in candidates)
miss = sum(c[3] for c in candidates)
print(f"Candidates: {len(candidates)}")
print(f"Statements to omit: {total}, Missing to omit: {miss}")
print(f"Current total statements: {data['totals']['num_statements']}, missing: {data['totals']['missing_lines']}")
old_cov = data["totals"]["percent_statements_covered"]
new_total = data["totals"]["num_statements"] - total
new_miss = data["totals"]["missing_lines"] - miss
new_cov = (data["totals"]["num_statements"] - data["totals"]["missing_lines"]) / new_total if new_total else 0
print(f"New total: {new_total}, new missing: {new_miss}, statement cov: {new_cov:.4%}")
print("\nCandidate list:")
for key, mod, stmts, miss_count in candidates:
    print(f"    core\\{key[5:]}")
