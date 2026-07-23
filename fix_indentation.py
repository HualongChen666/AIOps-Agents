import re
from pathlib import Path

api_dir = Path("C:/AIOps_Agent_bak/api")
pattern = re.compile(r'^(\s+)"""TODO: Add docstring \(Google style\)\."""$', re.MULTILINE)

for py_file in api_dir.glob("*.py"):
    content = py_file.read_text(encoding="utf-8")
    lines = content.split("\n")
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]

        match = pattern.match(line)
        if match:
            indent = match.group(1)
            # Check if next line is a function/class definition
            if i + 1 < len(lines):
                next_line = lines[i + 1].lstrip()
                if next_line.startswith("def ") or next_line.startswith("class "):

                    i += 1
                    continue
        new_lines.append(line)
        i += 1

    new_content = "\n".join(new_lines)
    if new_content != content:
        py_file.write_text(new_content, encoding="utf-8")
        print(f"Fixed: {py_file.name}")
