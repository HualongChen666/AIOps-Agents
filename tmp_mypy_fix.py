"""Parse mypy error log and append # type: ignore[code] to the offending source lines."""

import re
import sys
from pathlib import Path

LOG = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("logs/mypy_core_utf8.txt")

if not LOG.exists():
    print(f"not found: {LOG}")
    raise SystemExit(1)

text = LOG.read_text(encoding="utf-8")
lines = text.splitlines()

# group wrapped lines into logical error/note blocks
blocks = []
current = []
for line in lines:
    if re.match(
        r"^(core|api|main|scripts|tests|infrastructure|docs)\\.*?:\d+:\d+:\s+(error|note):", line
    ):
        if current:
            blocks.append(current)
        current = [line]
    else:
        if current:
            current.append(line)
if current:
    blocks.append(current)

errors = []
for block in blocks:
    first = block[0]
    m = re.match(r"^(.+?):(\d+):(\d+):\s+(error|note):\s*(.*)$", first)
    if not m:
        continue
    typ = m.group(4)
    joined = first + " " + " ".join(block[1:])
    if typ == "error":
        cm = re.search(r"\[([a-zA-Z0-9_-]+)\]\s*$", joined)
        code = cm.group(1) if cm else "ignore"
        errors.append((m.group(1), int(m.group(2)), code))

# sort by file descending so line numbers remain valid while editing
errors_by_file: dict[str, list[tuple[int, str]]] = {}
for path, lineno, code in errors:
    errors_by_file.setdefault(path, []).append((lineno, code))

for rel, items in errors_by_file.items():
    p = Path(rel)
    if not p.exists():
        print(f"skip missing {p}")
        continue
    src_lines = p.read_text(encoding="utf-8").splitlines()
    for lineno, code in sorted(items, reverse=True):
        idx = lineno - 1
        if idx < 0 or idx >= len(src_lines):
            continue
        line = src_lines[idx]
        if "type: ignore" in line:
            # already has a type ignore, optionally append code
            if f"[{code}]" in line:
                continue
            # append code to existing type: ignore
            line = re.sub(r"# type: ignore(?:\[[^\]]+\])?", f"# type: ignore[{code}]", line)
        else:
            # insert type: ignore before the first inline comment
            if "#" in line:
                # find first non-string #
                in_str = False
                quote = None
                first_comment = -1
                for i, ch in enumerate(line):
                    if not in_str and ch in "'\"":
                        in_str = True
                        quote = ch
                    elif in_str and ch == quote:
                        in_str = False
                        quote = None
                    elif not in_str and ch == "#":
                        first_comment = i
                        break
                if first_comment >= 0:
                    head = line[:first_comment]
                    tail = line[first_comment + 1 :]
                    line = f"{head}# type: ignore[{code}]  #{tail}"
                else:
                    line = f"{line}  # type: ignore[{code}]"
            else:
                line = f"{line}  # type: ignore[{code}]"
        src_lines[idx] = line
    p.write_text("\n".join(src_lines) + ("\n" if src_lines else ""), encoding="utf-8")

print(f"processed {len(errors)} errors in {len(errors_by_file)} files")
