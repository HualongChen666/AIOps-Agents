import re
from pathlib import Path

log_path = Path("full_coverage_log.txt")
out_path = Path("report_extract.txt")

raw = log_path.read_bytes()
if raw.startswith(b"\xff\xfe"):
    text = raw[2:].decode("utf-16-le", errors="ignore")
elif raw.startswith(b"\xfe\xff"):
    text = raw[2:].decode("utf-16-be", errors="ignore")
else:
    text = raw.decode("utf-16", errors="ignore")

lines = text.splitlines()

# Find the last TOTAL line and the header before it.
last_total_idx = -1
header_idx = -1
for i in range(len(lines) - 1, -1, -1):
    if lines[i].strip().startswith("TOTAL"):
        last_total_idx = i
        break

# find the Name header before last TOTAL
for i in range(last_total_idx, -1, -1):
    if re.match(r"^Name\s+Stmts\s+Miss\s+Branch\s+BrPart\s+Cover", lines[i]):
        header_idx = i
        break

out = []
out.append(f"last_total_idx={last_total_idx}, header_idx={header_idx}")
report_lines = lines[header_idx + 2 : last_total_idx]  # skip header and dashes
# Also include TOTAL line
out.append(f"TOTAL line: {lines[last_total_idx]}")
out.append(f"Number of report lines: {len(report_lines)}")
out.append("")
out.append("Last 100 report lines:")
for line in report_lines[-100:]:
    out.append(repr(line))

out_path.write_text("\n".join(out), encoding="utf-8")
print("done")
