import re
from pathlib import Path

log_path = Path("full_coverage_log.txt")
raw = log_path.read_bytes()
if raw.startswith(b"\xff\xfe"):
    text = raw[2:].decode("utf-16-le", errors="ignore")
elif raw.startswith(b"\xfe\xff"):
    text = raw[2:].decode("utf-16-be", errors="ignore")
else:
    text = raw.decode("utf-16", errors="ignore")
lines = text.splitlines()

# Find last report block
last_total_idx = -1
header_idx = -1
for i in range(len(lines) - 1, -1, -1):
    if lines[i].strip().startswith("TOTAL"):
        last_total_idx = i
        break
for i in range(last_total_idx, -1, -1):
    if re.match(r"^Name\s+Stmts\s+Miss\s+Branch\s+BrPart\s+Cover", lines[i]):
        header_idx = i
        break

report_lines = lines[header_idx + 2 : last_total_idx]
total_line = lines[last_total_idx]

pattern = re.compile(r"^(.+?)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+([\d.]+)%")
files = {}
for line in report_lines:
    m = pattern.match(line)
    if m:
        fname = m.group(1).strip()
        files[fname] = {
            "stmts": int(m.group(2)),
            "miss": int(m.group(3)),
            "branch": int(m.group(4)),
            "brpart": int(m.group(5)),
            "cover": float(m.group(6)),
        }

# Output top low coverage files sorted by missing lines
out = []
out.append(f"Parsed {len(files)} files. {total_line}")
out.append("")
low = sorted(files.items(), key=lambda kv: kv[1]["miss"], reverse=True)[:80]
out.append("Top 80 files by missing lines:")
out.append(f"{'cover':>8} {'miss':>5} {'stmts':>6} {'branch':>6} {'brpart':>6} file")
for fname, d in low:
    out.append(
        f"{d['cover']:>7.2f}% {d['miss']:>5} {d['stmts']:>6} {d['branch']:>6} {d['brpart']:>6} {fname}"
    )

Path("report_top_missing.txt").write_text("\n".join(out), encoding="utf-8")
print("done")
