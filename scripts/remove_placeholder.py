import logging
"""Remove default_value TODO docstrings from Python files."""

import pathlib

root = pathlib.Path(r"C:\AIOps_Agent_bak")
placeholders = []
modified = []
for py in root.rglob("*.py"):
    try:
        text = py.read_text(encoding="utf-8")
    except Exception as e:
        logging.exception("Unexpected exception: %s", e)
        continue
    if any(ph in text for ph in placeholders):
        lines = text.splitlines()
        new_lines = [line for line in lines if not any(ph in line for ph in placeholders)]
        if len(new_lines) != len(lines):
            py.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
            modified.append(str(py))
print("Modified files:", len(modified))
for p in modified[:20]:
    print(p)