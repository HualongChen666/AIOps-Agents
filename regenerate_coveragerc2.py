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
    # core_backup has core_backup. prefix; ignore
    if p.startswith("core_backup") or p.startswith("external"):
        return ""
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
                name = alias.name
                if name.startswith("core.") or name.startswith("api."):
                    imports.add(name)
        elif isinstance(node, ast.ImportFrom):
            mod = node.module
            if mod and (mod.startswith("core") or mod.startswith("api")):
                imports.add(mod)
                # also record dotted submodules from relative? not needed
    return imports


def test_file_for_module(mod: str) -> bool:
    """Check if a dedicated test file exists for this module under tests."""
    parts = mod.split(".")
    if parts[0] not in ("core", "api"):
        return False
    name = parts[-1]
    # tests/core/test_<name>.py or tests/core/<subdir>/test_<name>.py
    candidates = [
        ROOT / "tests" / parts[0] / f"test_{name}.py",
        ROOT / "tests" / Path(*parts) / f"test_{name}.py",
        ROOT / "tests" / Path(*parts[:-1]) / f"test_{name}.py",
        ROOT / "tests" / "infrastructure" / Path(*parts[1:]) / f"test_{name}.py",
    ]
    if parts[0] == "core":
        candidates.append(ROOT / "tests" / "infrastructure" / Path(*parts[1:]) / f"test_{name}.py")
    for c in candidates:
        if c.exists():
            return True
    return False


def main():
    active = set()

    # main and routers
    if (ROOT / "main.py").exists():
        active |= ast_imports(ROOT / "main.py")
    for router in (ROOT / "api").glob("*.py"):
        active |= ast_imports(router)

    # smoke test module lists
    smoke_a = ROOT / "tests" / "core" / "test_active_method_smoke.py"
    smoke_b = ROOT / "tests" / "core" / "test_low_coverage_method_smoke.py"
    if smoke_a.exists():
        active |= extract_active_modules(smoke_a)
    if smoke_b.exists():
        active |= extract_active_modules(smoke_b)

    # Scan all test files for core/api imports
    for test_file in (ROOT / "tests").rglob("*.py"):
        active |= ast_imports(test_file)

    # Normalize active set to module names
    active_norm = set()
    for a in active:
        if not a:
            continue
        # strip trailing submodule names if file path? We keep as-is and normalize
        m = normalize_mod(a)
        if m:
            active_norm.add(m)
        # Add parent modules too (if core.a.b imported, core.a is also active)
        parts = a.split(".")
        for i in range(1, len(parts)):
            parent = ".".join(parts[:i + 1])
            if not (parent.startswith("core") or parent.startswith("api")):
                continue
            active_norm.add(parent)

    # Include modules that have test files even if not imported
    for test_file in (ROOT / "tests").rglob("test_*.py"):
        rel = test_file.relative_to(ROOT / "tests")
        parts = list(rel.parts)
        if len(parts) < 2:
            continue
        # e.g. tests/core/test_foo.py -> core.foo
        if len(parts) == 2:
            name = parts[1][5:-3]
            active_norm.add(f"{parts[0]}.{name}")
        else:
            # tests/core/sub/test_foo.py -> core.sub.foo
            test_name = parts[-1]
            if test_name.startswith("test_") and test_name.endswith(".py"):
                name = test_name[5:-3]
                mod = ".".join([parts[0]] + parts[1:-1] + [name])
                active_norm.add(mod)

    # Read unreachable modules
    unreachable = set()
    if UNREACHABLE_FILE.exists():
        for line in UNREACHABLE_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("Unreachable"):
                continue
            m = normalize_mod(line)
            if m:
                unreachable.add(m)

    # Determine omit candidates: unreachable and not active, and no test file
    omit_modules = []
    for m in sorted(unreachable):
        if m in active_norm:
            continue
        if test_file_for_module(m):
            continue
        if m.endswith(".__init__"):
            continue
        omit_modules.append(m)

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
    print(f"Active modules found: {len(active_norm)}")


if __name__ == "__main__":
    main()
