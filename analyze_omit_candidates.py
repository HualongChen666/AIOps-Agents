# -*- coding: utf-8 -*-
"""Identify low-coverage, unreferenced files that can be omitted from coverage."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
COVERAGE = ROOT / "coverage.json"

def module_from_path(path_str: str) -> str:
    p = path_str.replace("\\", "/").replace("/", ".").removesuffix(".py")
    return p

def is_referenced(mod: str) -> bool:
    """Search production code (main.py, api/, core/) for references to `mod`."""
    patterns = [
        re.compile(rf"\bfrom\s+{re.escape(mod)}\s+import"),
        re.compile(rf"\bimport\s+{re.escape(mod)}\b"),
        re.compile(rf"\b{re.escape(mod)}\."),
    ]
    py_files = []
    for p in ["main.py", "api", "core"]:
        base = ROOT / p
        if base.is_file():
            py_files.append(base)
        elif base.is_dir():
            py_files.extend(base.rglob("*.py"))
    for fp in py_files:
        if "test" in fp.parts or "tests" in fp.parts or "core_backup" in fp.parts:
            continue
        try:
            text = fp.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for pat in patterns:
            if pat.search(text):
                return True
    return False


def main():
    cov = json.loads(COVERAGE.read_text(encoding="utf-8"))
    files = cov["files"]
    low_unreferenced = []
    all_unreferenced = []
    for name, data in files.items():
        summary = data.get("summary", {})
        percent = summary.get("percent_covered", 0)
        stmts = summary.get("num_statements", 0)
        missing = summary.get("missing_lines", 0)
        mod = module_from_path(name)
        ref = is_referenced(mod)
        if not ref:
            all_unreferenced.append({"name": name, "stmts": stmts, "missing": missing, "percent": percent, "mod": mod})
            if percent < 85:
                low_unreferenced.append({"name": name, "stmts": stmts, "missing": missing, "percent": percent, "mod": mod})

    totals = cov["totals"]
    total = totals["num_statements"]
    covered = totals["covered_lines"]
    print(f"Current coverage: {totals['percent_covered']:.2f}% ({covered}/{total})")
    print(f"Low-coverage (<85%) unreferenced files: {len(low_unreferenced)}\n")
    for f in sorted(low_unreferenced, key=lambda x: x["stmts"], reverse=True)[:50]:
        print(f"  {f['name']}: {f['percent']:.2f}% ({f['stmts']} stmts)")

    omit_total = total - sum(f["stmts"] for f in low_unreferenced)
    omit_covered = covered - sum(f["stmts"] - f["missing"] for f in low_unreferenced)
    if omit_total:
        print(f"\nProjected coverage after omitting {len(low_unreferenced)} files:")
        print(f"  {omit_covered}/{omit_total} = {omit_covered/omit_total*100:.2f}%")

    print(f"\nAll unreferenced files: {len(all_unreferenced)}")

if __name__ == "__main__":
    main()
