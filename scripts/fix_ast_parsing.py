# -*- coding: utf-8 -*-
import ast
import pathlib

root = pathlib.Path(r"C:\\AIOps_Agent_bak")

fixed = []
still_error = []

for p in root.rglob("*.py"):
    try:
        source = p.read_text(encoding="utf-8")
        ast.parse(source)
        continue
    except Exception:
        # Try to add utf-8 coding comment if missing
        lines = source.splitlines()
        has_coding = any("coding" in line for line in lines[:2])
        if not has_coding:
            new_source = "# -*- coding: utf-8 -*-\n" + source
        else:
            new_source = source
        # Ensure file ends with a newline
        if not new_source.endswith("\n"):
            new_source += "\n"
        try:
            ast.parse(new_source)
            # Write back fixed content
            p.write_text(new_source, encoding="utf-8")
            fixed.append(str(p))
        except Exception as e2:
            still_error.append((str(p), str(e2)))

print("Fixed files:", len(fixed))
print("Still error files:", len(still_error))
for path, err in still_error[:20]:
    print(path, err)
