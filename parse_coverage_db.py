import json

with open("coverage.json") as f:
    data = json.load(f)

prefixes = ("core/database", "core\\\\database")
rows = []
for fn, info in data["files"].items():
    if fn.startswith("core/database") or fn.startswith("core\\\\database"):
        s = info["summary"]
        rows.append((fn, s["percent_covered_display"], s["covered_lines"], s["num_statements"]))

for fn, pct, covered, total in rows:
    print(f"{fn}: {pct}% ({covered}/{total})")

if rows:
    total_covered = sum(r[2] for r in rows)
    total_stmts = sum(r[3] for r in rows)
    print(f"Combined: {total_covered/total_stmts*100:.2f}% ({total_covered}/{total_stmts})")
else:
    print("No database files found in coverage.json")
