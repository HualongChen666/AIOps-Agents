# -*- coding: utf-8 -*-
"""Omit loaded core modules that are not imported by main.py or api routers."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

with open(ROOT / "coverage.json", "r", encoding="utf-8") as f:
    data = json.load(f)

unreachable_text = (ROOT / "temp_unreachable_modules.txt").read_text(encoding="utf-8")
unreachable = set()
in_list = False
for line in unreachable_text.splitlines():
    line = line.strip()
    if line.startswith("Unreachable core modules"):
        in_list = True
        continue
    if in_list and line.startswith("core."):
        unreachable.add(line)

candidates = []
for key, val in data["files"].items():
    if not key.startswith("core\\"):
        continue
    summary = val["summary"]
    if summary["num_statements"] == 0:
        continue
    mod = key.replace("core\\", "core.", 1).replace("\\", ".").replace(".py", "")
    if mod in unreachable:
        candidates.append((key, mod, summary["num_statements"], summary["missing_lines"]))

print(f"Loaded but unreachable core modules in coverage: {len(candidates)}")
for key, mod, stmts, miss in candidates:
    print(f"  {key} ({mod}) stmts={stmts} miss={miss}")

total_stmts = data["totals"]["num_statements"]
total_miss = data["totals"]["missing_lines"]
cand_total = sum(c[2] for c in candidates)
cand_miss = sum(c[3] for c in candidates)
new_total = total_stmts - cand_total
new_miss = total_miss - cand_miss
new_cov = (total_stmts - total_miss) / new_total if new_total else 0
print(f"\nOmit impact: total {total_stmts} -> {new_total}, miss {total_miss} -> {new_miss}, cov {(total_stmts-total_miss)/total_stmts:.4%} -> {new_cov:.4%}")
