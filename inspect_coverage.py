import json
from pathlib import Path

data = json.loads(Path("coverage.json").read_text(encoding="utf-8"))
t = data["totals"]
lines = ["TOTALS: " + json.dumps(t)]
# sample first few files
for i, (k, v) in enumerate(data["files"].items()):
    lines.append(f"FILE {k}: " + json.dumps(v["summary"]))
    if i >= 2:
        break
Path("inspect_coverage_log.txt").write_text("\n".join(lines), encoding="utf-8")
