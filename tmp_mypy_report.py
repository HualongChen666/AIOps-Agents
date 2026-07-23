"""Parse mypy output and print grouped errors per file."""

from collections import defaultdict
from pathlib import Path

LOG = Path("logs/mypy_core_utf8.txt")
if not LOG.exists():
    print(f"not found: {LOG}")
    raise SystemExit(1)

text = LOG.read_text(encoding="utf-8")
lines = text.splitlines()

by_file = defaultdict(list)
for line in lines:
    if ": error:" not in line:
        continue
    # line format: core\error_logging\handler.py:185:9: error: ...
    head, _, msg = line.partition(": error: ")
    path = head.split(":", 1)[0]
    by_file[path].append(msg)

print(f"total lines: {len(lines)}")
print(f"total error lines: {sum(len(v) for v in by_file.values())}")
print(f"files with errors: {len(by_file)}")
for path, msgs in sorted(by_file.items()):
    print(f"{path}: {len(msgs)}")
