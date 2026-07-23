import json

with open("coverage.json") as f:
    data = json.load(f)

result = {}
for fn, info in data["files"].items():
    if "core" in fn.lower() and "database" in fn.lower():
        s = info["summary"]
        result[fn] = {
            "percent": s["percent_covered_display"],
            "covered": s["covered_lines"],
            "total": s["num_statements"],
            "missing": info.get("missing_lines", []),
        }

with open("db_missing_lines.json", "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2, ensure_ascii=False)
print("done")
