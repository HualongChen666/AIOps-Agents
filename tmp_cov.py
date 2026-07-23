import json

with open("coverage.json") as f:
    data = json.load(f)

files = []
for p, v in data["files"].items():
    s = v["summary"]
    files.append((p, s["percent_covered"], s.get("missing_lines", 0), s.get("num_statements", 0)))

files.sort(key=lambda x: x[1])
print("Lowest coverage files:")
for p, pct, miss, stmt in files[:100]:
    print(f"{p}: {pct:.1f}% missing {miss} lines ({stmt} statements)")
