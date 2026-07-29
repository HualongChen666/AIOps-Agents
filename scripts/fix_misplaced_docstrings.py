# -*- coding: utf-8 -*-
import logging
import pathlib
import re

root = pathlib.Path(r"C:\\AIOps_Agent_bak")
placeholder = r'\s*"""TODO: Add docstring \(Google style\)\."""'
placeholder_re = re.compile(placeholder)
fixed_files = []
still_errors = []

for py_path in root.rglob("*.py"):
    try:
        text = py_path.read_text(encoding="utf-8")
    except Exception as e:
        logging.exception("Unexpected exception: %s", e)
        continue
    lines = text.splitlines()
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # Detect misplaced default_value inside function signature
        # (line ends without colon and next line is default_value)
        if (
            line.rstrip().endswith("(")
            and i + 1 < len(lines)
            and placeholder_re.fullmatch(lines[i + 1].strip())
        ):
            # Skip default_value line
            i += 2
            continue
        # Detect default_value line alone
        if placeholder_re.fullmatch(line.strip()):
            i += 1
            continue
        # Detect stray ')' line that may belong to broken signature
        if line.strip() == ")":
            # Look ahead for '->' continuation
            if i + 1 < len(lines) and lines[i + 1].lstrip().startswith("->"):
                # Merge with previous line
                if new_lines:
                    prev = new_lines.pop()
                    merged = prev.rstrip() + " " + lines[i + 1].lstrip()
                    new_lines.append(merged)
                i += 2
                continue
        new_lines.append(line)
        i += 1
    new_text = "\n".join(new_lines) + "\n"
    try:
        compile(new_text, str(py_path), "exec")
        if new_text != text:
            py_path.write_text(new_text, encoding="utf-8")
            fixed_files.append(str(py_path))
    except Exception as e:
        still_errors.append((str(py_path), str(e)))

print("Fixed files count:", len(fixed_files))
print("Remaining error files:", len(still_errors))
for p, err in still_errors[:20]:
    print(p, err)
