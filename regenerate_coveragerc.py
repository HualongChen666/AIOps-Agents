import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
UNREACHABLE_FILE = ROOT / "unreachable_modules.txt"
COVERAGERC = ROOT / ".coveragerc"

GENERIC_PATTERNS = [
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
]


def normalize_mod(p: str) -> str:
    p = p.strip().replace("\\\\", "/").replace("\\", "/").replace("/", ".")
    if p.endswith(".py"):
        p = p[:-3]
    return p


def file_omit(mod: str) -> str:
    return mod.replace(".", "\\") + ".py"


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
    candidates = [
        ROOT / "tests" / Path(*parts) / f"test_{parts[-1]}.py",
        ROOT / "tests" / Path(*parts[:-1]) / f"test_{parts[-1]}.py",
        ROOT / "tests" / parts[0] / f"test_{parts[-1]}.py",
    ]
    for c in candidates:
        if c.exists():
            return True
    return False


def main():
    active = set()
    active |= extract_active_modules(ROOT / "tests" / "core" / "test_active_method_smoke.py")
    active |= extract_active_modules(ROOT / "tests" / "core" / "test_low_coverage_method_smoke.py")
    if (ROOT / "main.py").exists():
        active |= ast_imports(ROOT / "main.py")
    for router in (ROOT / "api").glob("*_router.py"):
        active |= ast_imports(router)

    active_norm = {normalize_mod(a) for a in active}

    unreachable = set()
    if UNREACHABLE_FILE.exists():
        for line in UNREACHABLE_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("Unreachable"):
                mod = normalize_mod(line)
                if mod.startswith("core.") or mod.startswith("api."):
                    unreachable.add(mod)

    # Omit only unreachable modules that are not actively tested/imported
    omit_modules = sorted(unreachable - active_norm)
    # Drop __init__ modules (covered by generic pattern)
    omit_modules = [m for m in omit_modules if not m.endswith(".__init__") and m not in active_norm and not has_test_file(m)]

    lines = ["[run]", "source = ", "\tcore", "\tapi", "omit = "]
    for p in GENERIC_PATTERNS:
        lines.append(f"\t{p}")
    for m in omit_modules:
        lines.append(f"\t{file_omit(m)}")

    lines.extend([
        "branch = True",
        "parallel = True",
        "data_file = .coverage",
        "",
        "[report]",
        "precision = 2",
        "show_missing = True",
        "skip_empty = True",
        "sort = Cover",
        "exclude_lines = ",
        "\tpragma: no cover",
        "\t",
        "\tdef __repr__",
        "\tdef __str__",
        "\traise AssertionError",
        "\traise NotImplementedError",
        "\tif __name__ == .__main__.:",
        "\tif TYPE_CHECKING:",
        "\tif MYPY:",
        "\t",
        "\t@abstractmethod",
        "\t@abc.abstractmethod",
        "\t",
        "\t: typing.",
        "\tfrom typing import",
        "\t",
        "\tassert False",
        "\tassert debug",
        "\t",
        "\texcept ImportError:",
        "\texcept Exception:",
        "\t",
        "\tclass Test",
        "\tdef test_",
        "",
        "[html]",
        "directory = htmlcov",
        "title = AIOps Agent Coverage Report",
        "",
        "[xml]",
        "output = coverage.xml",
        "",
        "[json]",
        "output = coverage.json",
        "",
        "[paths]",
        "source = ",
        "\tcore/",
        "\t*/core/",
    ])

    COVERAGERC.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {COVERAGERC} with {len(omit_modules)} module omits")


if __name__ == "__main__":
    main()
