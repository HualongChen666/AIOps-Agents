from pathlib import Path
import re

log_path = Path("full_coverage_log.txt")
raw = log_path.read_bytes()
# Remove BOM if present, then decode UTF-16 (PowerShell default for > redirect)
if raw.startswith(b"\xff\xfe"):
    text = raw[2:].decode("utf-16-le", errors="ignore")
elif raw.startswith(b"\xfe\xff"):
    text = raw[2:].decode("utf-16-be", errors="ignore")
else:
    text = raw.decode("utf-16", errors="ignore")
lines = text.splitlines()
print("total lines:", len(lines))
# find the last TOTAL
last_total = -1
for i in range(len(lines)-1, -1, -1):
    if lines[i].strip().startswith("TOTAL"):
        last_total = i
        break
print("last TOTAL line:", last_total)
start = max(0, last_total - 100)
end = min(len(lines), last_total + 5)
for i in range(start, end):
    print(f"{i}: {lines[i]!r}")
