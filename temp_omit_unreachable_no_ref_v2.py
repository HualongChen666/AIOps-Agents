# -*- coding: utf-8 -*-
"""Omit loaded core modules that are not imported/referenced by main.py, api, or tests."""
import json
import re
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

def to_module(key):
    return key.replace("core\\", "core.", 1).replace("\\", ".").replace(".py", "")

def has_test(mod):
    parts = mod.split(".")
    if len(parts) >= 2:
        test_path = ROOT / "tests" / "core" / Path(*parts[1:]).with_name(f"test_{parts[-1]}.py")
        if test_path.exists():
            return True
    return False

def is_referenced(mod):
    base = mod.replace("core.", "")
    name = mod.split(".")[-1]
    needles = {mod, base, name, base.replace(".", "\\"), base.replace(".", "_")}
    regex = re.compile("|".join(re.escape(n) for n in needles if n))
    targets = (
        list((ROOT / "api").rglob("*.py"))
        + [ROOT / "main.py"]
        + list((ROOT / "tests").rglob("*.py"))
    )
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
    summary = val["summary"]
    if summary["num_statements"] == 0:
        continue
    mod = to_module(key)
    if mod in unreachable and not has_test(mod) and not is_referenced(mod):
        candidates.append((key, mod, summary["num_statements"], summary["missing_lines"]))

print(f"Unreachable, unreferenced, and no dedicated tests loaded core modules: {len(candidates)}")
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
