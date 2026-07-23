import json
from pathlib import Path

repo = Path.cwd()
cov_json = repo / "coverage.json"
unreach_txt = repo / "unreachable_modules.txt"

with open(cov_json, "r", encoding="utf-8") as f:
    cov = json.load(f)

unreachable = set()
with open(unreach_txt, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line.startswith("core\\") or line.startswith("api\\"):
            # normalize to / and then to coverage keys use forward slashes? Actually coverage.json keys use backslashes? check
            unreachable.add(line.replace("\\", "/"))

low_unreachable = []
for fname, data in cov["files"].items():
    summary = data.get("summary") or data
    percent = summary.get("percent_covered", 0)
    missing = summary.get("missing_lines", 0)
    # coverage.json keys use forward slashes? It may use path sep of OS (backslash on Windows). Normalize.
    key_norm = fname.replace("\\", "/")
    if percent < 80 and key_norm in unreachable:
        low_unreachable.append((fname, missing, percent))

low_unreachable.sort(key=lambda x: x[1], reverse=True)

total_missing = sum(x[1] for x in low_unreachable)
print(f"Low-coverage (<80%) unreachable files: {len(low_unreachable)}")
print(f"Total missing lines in them: {total_missing}")
print("Top candidates:")
for fname, missing, percent in low_unreachable[:60]:
    print(f"{missing:4d} missing ({percent:5.2f}%) {fname}")
