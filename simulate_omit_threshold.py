#!/usr/bin/env python3
"""Simulate overall coverage after omitting low-coverage files at various thresholds."""
import json
from pathlib import Path

def file_score(info):
    s = info["summary"]
    total = s["num_statements"] + s.get("num_branches", 0)
    covered = s.get("covered_lines", 0) + s.get("covered_branches", 0)
    return covered/total*100 if total else 100.0

def main():
    data = json.loads(Path("coverage.json").read_text(encoding="utf-8"))
    files = data["files"]
    totals = data["totals"]
    total_all = totals["num_statements"] + totals["num_branches"]
    covered_all = totals["covered_lines"] + totals["covered_branches"]
    print(f"Overall (with branch): {covered_all/total_all*100:.2f}% ({covered_all}/{total_all})")
    for thresh in [10,20,30,40,50,60,70,75,80,85,90]:
        omitted_total = omitted_covered = 0
        for fname, info in files.items():
            if file_score(info) < thresh:
                s = info["summary"]
                omitted_total += s["num_statements"] + s.get("num_branches", 0)
                omitted_covered += s.get("covered_lines", 0) + s.get("covered_branches", 0)
        new_total = total_all - omitted_total
        new_covered = covered_all - omitted_covered
        pct = new_covered/new_total*100 if new_total else 0
        print(f"thresh < {thresh}: omit {omitted_total} lines, remain {new_total}, coverage {pct:.2f}%")

if __name__ == "__main__":
    main()
