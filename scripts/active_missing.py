#!/usr/bin/env python
# -*- coding: utf-8 -*-
import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORE = ROOT / "core"
API = ROOT / "api"
MAIN = ROOT / "main.py"


def find_imports(path: Path) -> set[str]:
    imports = set()
    if not path.exists():
        return imports
    for p in path.rglob("*.py"):
        if "venv" in p.parts or "__pycache__" in p.parts:
            continue
        try:
            tree = ast.parse(p.read_text(encoding="utf-8", errors="replace"))
        except (SyntaxError, OSError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("core."):
                        imports.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.startswith("core."):
                    imports.add(node.module)
                    for alias in node.names:
                        imports.add(f"{node.module}.{alias.name}")
    return imports


def main() -> int:
    with open(ROOT / "coverage.json", encoding="utf-8") as f:
        cov = json.load(f)
    files = cov.get("files", {})

    app_imports = find_imports(API)
    if MAIN.exists():
        app_imports |= find_imports(ROOT)

    active_missing = []
    for fpath, info in files.items():
        if not fpath.startswith("core"):
            continue
        missing = info["summary"]["missing_lines"]
        stmts = info["summary"]["num_statements"]
        if stmts == 0 or missing == 0:
            continue
        mod = fpath.replace("\\", ".").replace("/", ".").removesuffix(".py")
        pkg_mod = mod.removesuffix(".__init__")
        is_active = pkg_mod in app_imports or mod in app_imports
        if is_active:
            active_missing.append((missing, stmts, fpath, info["summary"]["percent_covered"]))

    active_missing.sort(reverse=True, key=lambda x: x[0])
    print("Active core modules by missing statements:")
    for missing, stmts, fpath, pct in active_missing[:30]:
        print(f"  {fpath}: {missing}/{stmts} missing ({pct:.1f}%)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
