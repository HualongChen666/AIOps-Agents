import json

with open("coverage.json") as f:
    data = json.load(f)

rows = []
for fn, info in data["files"].items():
    if "database" in fn.lower() and "core" in fn.lower():
        s = info["summary"]
        rows.append((fn, s["percent_covered_display"], s["covered_lines"], s["num_statements"]))

lines = []
for fn, pct, covered, total in rows:
    lines.append(f"{fn}: {pct}% ({covered}/{total})")

if rows:
    total_covered = sum(r[2] for r in rows)
    total_stmts = sum(r[3] for r in rows)
    lines.append(f"Combined: {total_covered/total_stmts*100:.2f}% ({total_covered}/{total_stmts})")
else:
    lines.append("No database files found in coverage.json")

with open("db_coverage_summary.txt", "w") as f:
    f.write("\n".join(lines))
print("done")
