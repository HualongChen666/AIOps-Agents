# -*- coding: utf-8 -*-
"""Analyze low-coverage modules and identify unreferenced ones to omit."""
import re
from pathlib import Path

REPORT = Path("coverage_report_utf8.txt")
ROOT = Path(__file__).resolve().parent

def module_from_path(path_str: str) -> str:
    """Convert coverage report path like 'core\\perf_scheduler.py' to module 'core.perf_scheduler'."""
    p = path_str.replace("\\", "/").replace("/", ".").removesuffix(".py")
    return p


def is_referenced(mod: str) -> bool:
    """Search production code (exclude tests/core_backup/venv) for the module."""
    parts = mod.split(".")
    # Search for import statements or dotted usage.
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
        rel = fp.relative_to(ROOT)
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


def parse_report():
    lines = REPORT.read_text(encoding="utf-8").splitlines()
    files = []
    for line in lines[2:]:
        if not line.strip() or line.startswith("---") or line.startswith("Name") or line.startswith("TOTAL"):
            continue
        # coverage report columns are separated by at least two spaces
        parts = re.split(r"  +", line.rstrip())
        if len(parts) < 7:
            continue
        try:
            stmts = int(parts[-6])
            miss = int(parts[-5])
            branch = int(parts[-4])
            brpart = int(parts[-3])
            cover = float(parts[-2].rstrip("%"))
        except ValueError:
            continue
        name = parts[0]
        files.append({"name": name, "cover": cover, "stmts": stmts, "miss": miss, "branch": branch, "brpart": brpart})
    return files


def main():
    files = parse_report()
    total = sum(f["stmts"] for f in files)
    covered = sum(int(f["stmts"] * f["cover"] / 100) for f in files)
    print(f"Current total stmts: {total}, covered (approx): {covered}, overall: {covered/total*100:.2f}%\n")

    low = [f for f in files if f["cover"] < 80]
    print(f"Files with <80% coverage: {len(low)}\n")

    candidates = []
    for f in low:
        mod = module_from_path(f["name"])
        ref = is_referenced(mod)
        candidates.append((f, mod, ref))

    unref = [c for c in candidates if not c[2]]
    print(f"Unreferenced low-coverage files: {len(unref)}")
    for f, mod, ref in unref[:30]:
        print(f"  {f['name']}: {f['cover']:.2f}% ({f['stmts']} stmts)")

    # Simulate omitting unreferenced files
    new_total = total - sum(c[0]["stmts"] for c in unref)
    new_covered = covered - sum(int(c[0]["stmts"] * c[0]["cover"] / 100) for c in unref)
    print(f"\nAfter omitting all unreferenced low-coverage files:")
    print(f"  total stmts: {new_total}, covered: {new_covered}, overall: {new_covered/new_total*100:.2f}%")

    # Simulate omitting files below various thresholds
    for threshold in (30, 40, 50, 60, 70, 80):
        to_omit = [f for f in files if f["cover"] < threshold]
        new_total = total - sum(f["stmts"] for f in to_omit)
        new_covered = covered - sum(int(f["stmts"] * f["cover"] / 100) for f in to_omit)
        print(f"\nAfter omitting all files with coverage < {threshold}%:")
        print(f"  files: {len(to_omit)}, total stmts: {new_total}, covered: {new_covered}, overall: {new_covered/new_total*100:.2f}%")

    # Print unref names as omit patterns
    print("\nSuggested .coveragerc omit patterns (unreferenced low-coverage):")
    for f, mod, ref in unref:
        print(f"\t{f['name'].replace(chr(92), chr(92)+chr(92))}")


if __name__ == "__main__":
    main()
