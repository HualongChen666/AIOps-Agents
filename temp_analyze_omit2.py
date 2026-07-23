import configparser
import ast
import os
from pathlib import Path

ROOT = Path.cwd()
UNREACHABLE_FILE = ROOT / "unreachable_modules.txt"
COVERAGERC = ROOT / ".coveragerc"


def normalize(p: str) -> str:
    p = p.strip().replace("\\\\", "/").replace("\\", "/")
    if p.endswith(".py"):
        p = p[:-3]
    return p


def test_path_for(mod: str) -> Path | None:
    # e.g. core/abac -> tests/core/test_abac.py
    # core/error_logging/alerting -> tests/core/error_logging/test_alerting.py
    # core/ai/llm_router/enhanced_router -> tests/core/ai/llm_router/test_enhanced_router.py
    parts = mod.split("/")
    if parts[0] not in ("core", "api"):
        return None
    file_part = parts[-1]
    subdir = "/".join(parts[:-1])
    candidates = [
        ROOT / subdir / f"test_{file_part}.py",
        ROOT / "tests" / subdir / f"test_{file_part}.py",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def load_imports(path: Path) -> set[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except Exception:
        return set()
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("core.") or alias.name.startswith("api."):
                    imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module and (node.module.startswith("core") or node.module.startswith("api")):
                imports.add(node.module)
    return imports


def main():
    parser = configparser.ConfigParser(allow_no_value=True)
    parser.optionxform = str
    parser.read(COVERAGERC, encoding="utf-8")

    run_omit = set()
    if parser.has_option("run", "omit"):
        raw = parser.get("run", "omit")
        run_omit = {normalize(line) for line in raw.splitlines() if line.strip() and not line.strip().startswith("#")}

    unreachable = set()
    if UNREACHABLE_FILE.exists():
        for line in UNREACHABLE_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("Unreachable"):
                unreachable.add(normalize(line))

    generic = {
        "*/.venv/*",
        "*/__init__.py",
        "*/__pycache__/*",
        "*/alembic/*",
        "*/conftest.py",
        "*/env/*",
        "*/migrations/*",
        "*/mock_manager.py",
        "*/site-packages/*",
        "*/test_*.py",
        "*/tests/*",
        "*/venv/*",
        "*/virtualenv/*",
        "setup.py",
    }
    generic_norm = {normalize(g) for g in generic}

    # Collect main/api imports
    main_imports = load_imports(ROOT / "main.py")
    api_imports = set()
    for router in (ROOT / "api").glob("*_router.py"):
        api_imports |= load_imports(router)
    all_imports = main_imports | api_imports

    to_remove = []  # currently omitted but should be measured
    to_add = []     # not omitted but unreachable and no tests

    for entry in sorted(run_omit):
        if entry in generic_norm:
            continue
        mod = entry
        has_test = test_path_for(mod) is not None
        imported = any(mod == imp or imp.startswith(mod + "/") or mod.startswith(imp + "/") for imp in all_imports)
        in_unreachable = mod in unreachable
        if has_test or imported:
            to_remove.append(entry)
        elif not in_unreachable:
            # neither imported nor has test, but also not in unreachable list
            to_add.append(entry)

    print("=== OMIT entries to REMOVE (active: tested or imported) ===")
    for e in to_remove:
        print(e)

    print("\n=== OMIT entries to KEEP (unreachable, no test, not imported) ===")
    for e in sorted(run_omit):
        if e in to_remove or e in generic_norm:
            continue
        print(e)


if __name__ == "__main__":
    main()
