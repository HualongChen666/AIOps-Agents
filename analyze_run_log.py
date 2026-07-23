# -*- coding: utf-8 -*-
"""Parse run.log and emit a compact failure summary."""
import re
from collections import Counter
from pathlib import Path

log_path = Path("run.log")
out_path = Path("run_summary.txt")

lines = log_path.read_text(encoding="utf-8", errors="ignore").splitlines()

# Find pytest summary lines and failed test names
failed = []
summary_lines = []
patterns = [
    re.compile(r"FAILED\s+([\w/_.-]+::[\w<>\[\]_-]+)"),
    re.compile(r"ERROR\s+([\w/_.-]+::[\w<>\[\]_-]+)"),
]
summary_pattern = re.compile(r"={5,}\s+(\d+ passed, \d+ failed, \d+ skipped|.*short test summary.*)={5,}")

for line in lines:
    if summary_pattern.search(line) or "short test summary" in line:
        summary_lines.append(line)
    for pat in patterns:
        m = pat.search(line)
        if m:
            failed.append(m.group(1))

counts = Counter(failed)

out = []
out.append(f"Total lines in log: {len(lines)}")
out.append("")
if summary_lines:
    out.append("Pytest summary snippets:")
    for s in summary_lines[-20:]:
        out.append(s)
else:
    out.append("No pytest summary snippets found.")
out.append("")
if counts:
    out.append(f"Unique failed/errored tests: {len(counts)}")
    for test, c in counts.most_common():
        out.append(f"{c}\t{test}")
else:
    out.append("No FAILED/ERROR test names found.")

out_text = "\n".join(out)
print(out_text)
out_path.write_text(out_text, encoding="utf-8")
