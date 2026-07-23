import json
import sys

path = sys.argv[1] if len(sys.argv) > 1 else "coverage.json"
with open(path, "r", encoding="utf-8") as f:
    d = json.load(f)
t = d["totals"]
print("TOTAL", t["percent_covered"])
print("FILES", len(d["files"]))
print("STMTS", t["num_statements"], "COVERED", t["covered_lines"])
