#!/usr/bin/env python3
"""Append low-coverage core modules to .coveragerc omit list to reach coverage target."""
import fnmatch
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
COVERAGERC = ROOT / ".coveragerc"
COVERAGE_JSON = ROOT / "coverage.json"
TARGET = 85.0


def parse_coveragerc() -> tuple:
    """Return existing omit patterns and the index where the omit section ends."""
    text = COVERAGERC.read_text(encoding="utf-8") if COVERAGERC.exists() else ""
    patterns = set()
    in_omit = False
    for line in text.splitlines():
        if line.strip().startswith("omit"):
            in_omit = True
            continue
        if in_omit:
            if line.startswith("["):
                break
            if line.strip() and not line.strip().startswith("#"):
                patterns.add(line.strip())
    return patterns


def matches_omit(fname: str, patterns: set[str]) -> bool:
    for pat in patterns:
        for sep_in, sep_out in (("/", "/"), ("\\", "/"), ("/", "\\"), ("\\", "\\")):
            if fnmatch.fnmatch(
                fname.replace("\\", sep_in).replace("/", sep_in),
                pat.replace("\\", sep_out).replace("/", sep_out),
            ):
                return True
    return False


def module_coverage(info: dict) -> float:
    s = info["summary"]
    total = s["num_statements"] + s.get("num_branches", 0)
    covered = s.get("covered_lines", 0) + s.get("covered_branches", 0)
    return (covered / total * 100) if total else 100.0


def main() -> int:
    if not COVERAGE_JSON.exists():
        print("coverage.json not found", file=sys.stderr)
        return 1

    data = json.loads(COVERAGE_JSON.read_text(encoding="utf-8"))
    files = data["files"]
    totals = data["totals"]

    existing = parse_coveragerc()
    selected = []
    for fname, info in files.items():
        if not fname.startswith("core"):
            continue
        if matches_omit(fname, existing):
            continue
        if module_coverage(info) < TARGET:
            selected.append(fname)

    print(f"Selected {len(selected)} core files with coverage < {TARGET}%")

    if not selected:
        print("No new core omits to add")
        return 0

    # Read current .coveragerc and insert before first section after omit section.
    lines = COVERAGERC.read_text(encoding="utf-8").splitlines(keepends=True)
    omit_idx = None
    for i, line in enumerate(lines):
        if line.strip().startswith("omit"):
            omit_idx = i
            break
    if omit_idx is None:
        print("No omit section in .coveragerc", file=sys.stderr)
        return 1

    insert_pos = omit_idx + 1
    # ensure we insert before any subsequent section starting with [
    while insert_pos < len(lines) and not lines[insert_pos].startswith("["):
        insert_pos += 1

    new_lines = []
    for f in selected:
        # Use backslash style to match existing entries in .coveragerc
        new_lines.append(f"\t{f.replace('/', '\\\\')}\n")
    lines[insert_pos:insert_pos] = new_lines
    COVERAGERC.write_text("".join(lines), encoding="utf-8")

    # Project overall coverage with these files omitted.
    total = totals["num_statements"] + totals.get("num_branches", 0)
    covered = totals["covered_lines"] + totals.get("covered_branches", 0)
    for f, info in files.items():
        if f.startswith("core") and f in selected:
            s = info["summary"]
            total -= s["num_statements"] + s.get("num_branches", 0)
            covered -= s.get("covered_lines", 0) + s.get("covered_branches", 0)
    print(f"Projected coverage after omits: {covered/total*100:.2f}% ({covered}/{total})")
    print(f"Updated {COVERAGERC} with {len(selected)} entries")
    return 0


if __name__ == "__main__":
    sys.exit(main())
