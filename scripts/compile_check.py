import json
import pathlib
import traceback

root = pathlib.Path(r"C:\AIOps_Agent_bak")
errors = []
for py in root.rglob("*.py"):
    try:
        source = py.read_text(encoding="utf-8")
        compile(source, str(py), "exec")
    except Exception as e:
        tb = traceback.format_exc()
        errors.append({"file": str(py), "error": str(e), "trace": tb})
print("Total errors:", len(errors))
with open("compile_errors.json", "w", encoding="utf-8") as f:
    json.dump(errors, f, ensure_ascii=False, indent=2)
