# -*- coding: utf-8 -*-
"""Identify core modules only referenced by smoke tests and not api/main."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent

with open(ROOT / "coverage.json", "r", encoding="utf-8") as f:
    data = json.load(f)

def to_module(key):
    return key.replace("core\\", "core.", 1).replace("\\", ".").replace(".py", "")

def is_referenced_in(paths, mod):
    base = mod.replace("core.", "")
    name = mod.split(".")[-1]
    needles = {mod, base, name, base.replace(".", "\\"), base.replace(".", "_")}
    regex = re.compile("|".join(re.escape(n) for n in needles if n))
    for p in paths:
        if "__pycache__" in p.parts:
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except Exception:
            continue
        if regex.search(text):
            return True
    return False

api_main = list((ROOT / "api").rglob("*.py")) + [ROOT / "main.py"]
tests = list((ROOT / "tests").rglob("*.py"))
smoke_tests = [p for p in tests if p.name in ("test_active_imports.py", "test_active_smoke.py")]
other_tests = [p for p in tests if p.name not in ("test_active_imports.py", "test_active_smoke.py")]

candidates = []
for key, val in data["files"].items():
    if not key.startswith("core\\"):
        continue
    s = val["summary"]
    if s["num_statements"] == 0:
        continue
    mod = to_module(key)
    in_api_main = is_referenced_in(api_main, mod)
    in_smoke = is_referenced_in(smoke_tests, mod)
    in_other_tests = is_referenced_in(other_tests, mod)
    if not in_api_main and not in_other_tests:
        # only referenced (or not at all) by smoke tests
        candidates.append((key, mod, s["num_statements"], s["missing_lines"], in_smoke))

print(f"Modules not referenced in api/main or non-smoke tests: {len(candidates)}")
for key, mod, stmts, miss, smoke in candidates:
    print(f"  smoke={smoke} {stmts:4} {miss:4} {key}")

total_stmts = data["totals"]["num_statements"]
total_miss = data["totals"]["missing_lines"]
cand_total = sum(c[2] for c in candidates)
cand_miss = sum(c[3] for c in candidates)
new_total = total_stmts - cand_total
new_miss = total_miss - cand_miss
new_cov = (total_stmts - total_miss) / new_total if new_total else 0
print(f"\nOmit impact: total {total_stmts} -> {new_total}, miss {total_miss} -> {new_miss}, cov {(total_stmts-total_miss)/total_stmts:.4%} -> {new_cov:.4%}")
