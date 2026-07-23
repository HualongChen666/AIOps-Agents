# -*- coding: utf-8 -*-
"""Find core modules referenced by main.py and api/ routers."""
import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def find_imports(text: str) -> set:
    found = set()
    # from core.foo import ...
    found.update(re.findall(r"from\s+([\w.]+)\s+import", text))
    # import core.foo, core.bar
    found.update(re.findall(r"import\s+([\w.]+(?:\s*,\s*[\w.]+)*)", text))
    return found


def active_modules() -> set:
    modules = set()
    # main.py
    main_text = (ROOT / "main.py").read_text(encoding="utf-8", errors="ignore")
    modules.update(find_imports(main_text))

    # api routers
    for p in (ROOT / "api").rglob("*.py"):
        if p.name.startswith("__"):
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        modules.update(find_imports(text))

    # Filter to core.* and api.* modules that correspond to files
    active = set()
    for mod in modules:
        if mod.startswith("core."):
            path = ROOT / (mod.replace(".", "/") + ".py")
            if path.exists():
                active.add(mod)
    return active


if __name__ == "__main__":
    active = sorted(active_modules())
    for m in active:
        print(m)
    print(f"\nTotal: {len(active)}")
