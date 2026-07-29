#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Analyze coverage report and identify active vs P2/default_value low-coverage modules."""

import re
from pathlib import Path
from typing import Dict, List, Tuple

REPORT_PATH = Path("verify_logs/coverage_report.log")
ROOT = Path(".")


def parse_report(path: Path) -> List[Dict]:
    rows = []
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith("----") or line.startswith("Name") or not line.strip():
                continue
            if line.startswith("TOTAL"):
                continue
            # Split on 2+ spaces to keep file paths with spaces intact
            parts = re.split(r" {2,}", line)
            if len(parts) < 6:
                continue
            parts = parts[:7]
            file_path = parts[0]
            try:
                stmts = int(parts[1])
                miss = int(parts[2])
                branches = int(parts[3])
                partial = int(parts[4])
                cover = float(parts[5].rstrip("%"))
            except (ValueError, IndexError):
                continue
            rows.append(
                {
                    "file": file_path,
                    "stmts": stmts,
                    "miss": miss,
                    "branches": branches,
                    "partial": partial,
                    "cover": cover,
                    "missing": parts[6] if len(parts) > 6 else "",
                }
            )
    return rows


def find_python_imports(source: str) -> List[str]:
    """Find module names imported from core.* or api.* in source code."""
    modules: List[str] = []
    for m in re.finditer(r"(?:from|import)\s+((?:core|api)(?:\.[a-zA-Z_0-9]+)*)\b", source):
        modules.append(m.group(1))
    # also handle `from core.x import y` -> module core.x
    for m in re.finditer(r"from\s+((?:core|api)(?:\.[a-zA-Z_0-9]+)*)\s+import", source):
        modules.append(m.group(1))
    return list(set(modules))


def get_active_modules() -> Dict[str, List[str]]:
    active: Dict[str, List[str]] = {}
    main_file = ROOT / "main.py"
    if main_file.exists():
        active["main.py"] = find_python_imports(main_file.read_text(encoding="utf-8"))
    for router in (ROOT / "api").glob("*_router.py"):
        active[f"api/{router.name}"] = find_python_imports(router.read_text(encoding="utf-8"))
    return active


def module_from_file(file_path: str) -> str:
    """Convert coverage file path (backslashes) to dotted module name."""
    p = file_path.replace("\\", "/")
    if p.endswith(".py"):
        p = p[:-3]
    if p.startswith("api/") or p.startswith("core/"):
        return p.replace("/", ".")
    return p.replace("/", ".")


def main() -> None:
    if not REPORT_PATH.exists():
        print(f"Report not found: {REPORT_PATH}")
        return

    rows = parse_report(REPORT_PATH)
    if not rows:
        print("WARNING: no coverage rows parsed")
    active_modules = get_active_modules()
    # Flatten active set and normalize
    active_set: set = set()
    for mods in active_modules.values():
        active_set.update(mods)

    low = [r for r in rows if r["cover"] < 80]
    low.sort(key=lambda x: x["miss"], reverse=True)

    active_low: List[Tuple[Dict, List[str]]] = []
    inactive_low: List[Dict] = []
    for r in low:
        mod = module_from_file(r["file"])
        importers = [
            k
            for k, v in active_modules.items()
            if any(mod == m or mod.startswith(m + ".") or m.startswith(mod + ".") for m in v)
        ]
        if importers:
            active_low.append((r, importers))
        else:
            inactive_low.append(r)

    total_missing_active = sum(r["miss"] for r, _ in active_low)
    total_missing_inactive = sum(r["miss"] for r in inactive_low)

    print(f"Low-coverage (<80%) files: {len(low)}")
    print(
        f"  Active (imported by main/api): {len(active_low)}  "
        f"missing statements: {total_missing_active}"
    )
    print(
        f"  Inactive (P2/placeholder):     {len(inactive_low)}  "
        f"missing statements: {total_missing_inactive}"
    )
    print()

    print("Top 30 ACTIVE low-coverage files (by missing statements):")
    for r, imps in active_low[:30]:
        print(
            f"  {r['file']:<60} cover={r['cover']:>6.2f}%  "
            f"stmts={r['stmts']:>5}  miss={r['miss']:>5}  "
            f"importers={','.join(imps[:2])}"
        )
    print()

    print("Top 30 INACTIVE low-coverage files (candidates for omission/cleanup):")
    for r in inactive_low[:30]:
        print(
            f"  {r['file']:<60} cover={r['cover']:>6.2f}%  "
            f"stmts={r['stmts']:>5}  miss={r['miss']:>5}"
        )
    print()

    # Estimate coverage boost if inactive files were omitted
    # We don't have total here, use the report total line
    total_stmts = sum(r["stmts"] for r in rows)
    print(f"Total measured statements (core+api): {total_stmts}")
    print(
        "Omitting inactive low-coverage files would remove "
        f"{total_missing_inactive} missing stmts from denominator"
    )


if __name__ == "__main__":
    main()
