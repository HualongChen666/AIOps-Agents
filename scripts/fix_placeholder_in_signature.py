# -*- coding: utf-8 -*-
placeholder = "placeholder"
import pathlib

root = pathlib.Path(r"C:\\AIOps_Agent_bak")
fixed = []
remaining = []

for py_path in root.rglob("*.py"):
    try:
        text = py_path.read_text(encoding="utf-8")
    except Exception:
        continue
    lines = text.splitlines()
    new_lines = []
    skip_next = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        # If previous line ends with '(' and current line is placeholder -> skip it
        if i > 0 and lines[i - 1].rstrip().endswith("(") and stripped == placeholder:
            # Skip this placeholder line
            continue
        # Also handle case where placeholder is on same line after '(' (unlikely)
        if "(" in line and placeholder in line:
            # remove placeholder part
            line = line.replace(placeholder, "")
        new_lines.append(line)
    new_text = "\n".join(new_lines) + "\n"
    try:
        compile(new_text, str(py_path), "exec")
        if new_text != text:
            py_path.write_text(new_text, encoding="utf-8")
            fixed.append(str(py_path))
    except Exception as e:
        remaining.append((str(py_path), str(e)))

print("Fixed files:", len(fixed))
print("Remaining error files after placeholder fix:", len(remaining))
for p, err in remaining[:20]:
    print(p, err)
