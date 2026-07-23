import ast
import configparser
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
COVERAGERC = ROOT / ".coveragerc"

# Generic omit patterns we always keep
GENERIC_PATTERNS = {
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
    "*.bak",
    "*.backup",
}


def normalize(p: str) -> str:
    p = p.strip()
    if p.endswith(".py"):
        p = p[:-3]
    # Convert path separators and dotted module names to dotted form
    p = p.replace("\\\\", ".").replace("\\", ".").replace("/", ".")
    return p


def extract_active_modules(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8")
    match = re.search(r"ACTIVE_MODULES\s*=\s*\[(.*?)\]", text, re.DOTALL)
    if not match:
        return set()
    entries = re.findall(r'"([^"]+)"', match.group(1))
    return set(entries)


def ast_imports(path: Path) -> set[str]:
    imports = set()
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except Exception:
        return imports
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("core.") or alias.name.startswith("api."):
                    imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module and (node.module.startswith("core") or node.module.startswith("api")):
                imports.add(node.module)
    return imports


def has_test_file(mod: str) -> bool:
    parts = mod.split(".")
    if parts[0] not in ("core", "api"):
        return False
    # tests/core/<subdir>/test_<file>.py or tests/core/test_<file>.py
    test_dir = ROOT / "tests" / Path(*parts)
    candidates = [
        test_dir.with_name(f"test_{test_dir.name}.py"),
        ROOT / "tests" / parts[0] / f"test_{parts[-1]}.py",
    ]
    if len(parts) > 2:
        candidates.append(ROOT / "tests" / Path(*parts[:-1]) / f"test_{parts[-1]}.py")
    for c in candidates:
        if c.exists():
            return True
    return False


def main():
    active = set()
    active |= extract_active_modules(ROOT / "tests" / "core" / "test_active_method_smoke.py")
    active |= extract_active_modules(ROOT / "tests" / "core" / "test_low_coverage_method_smoke.py")

    main_path = ROOT / "main.py"
    if main_path.exists():
        active |= ast_imports(main_path)

    for router in (ROOT / "api").glob("*_router.py"):
        active |= ast_imports(router)

    # Normalize active set
    active_norm = {normalize(a) for a in active}

    parser = configparser.ConfigParser(allow_no_value=True)
    parser.optionxform = str
    parser.read(COVERAGERC, encoding="utf-8")

    def clean_omit(raw: str) -> str:
        if not raw:
            return ""
        lines = []
        for line in raw.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                lines.append(line)
                continue
            # Keep generic glob patterns and setup.py
            if stripped in GENERIC_PATTERNS or any(c in stripped for c in "*?["):
                lines.append(line)
                continue
            mod = normalize(stripped)
            if mod in active_norm or has_test_file(mod):
                # remove: over-omit for active module
                continue
            # keep pattern
            lines.append(line)
        return "\n".join(lines)

    for section in ("run", "report"):
        if parser.has_option(section, "omit"):
            raw = parser.get(section, "omit")
            new = clean_omit(raw)
            parser.set(section, "omit", new)

    with open(COVERAGERC, "w", encoding="utf-8") as f:
        parser.write(f)

    print("Cleaned .coveragerc omit sections")


if __name__ == "__main__":
    main()
