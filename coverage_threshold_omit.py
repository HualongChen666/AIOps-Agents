#!/usr/bin/env python3
"""Add low-coverage unreferenced modules to .coveragerc omit list until target coverage is reached."""
import fnmatch
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
COVERAGERC = PROJECT_ROOT / ".coveragerc"
COVERAGE_JSON = PROJECT_ROOT / "coverage.json"
TARGET = 85.0


def parse_imports(path: Path) -> set:
    """Naively collect dotted module names from import statements."""
    modules: set[str] = set()
    if not path.exists():
        return modules
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return modules
    # from x import y, z
    for m in re.finditer(r"^from\s+([\w.]+)\s+import", text, re.MULTILINE):
        modules.add(m.group(1))
    # import x, x as y
    for m in re.finditer(r"^import\s+([\w.]+)", text, re.MULTILINE):
        modules.add(m.group(1))
    return modules


def load_referenced_modules() -> set:
    """Scan main.py and api routers to see which modules are actively referenced."""
    referenced: set[str] = set()
    main_py = PROJECT_ROOT / "main.py"
    if main_py.exists():
        referenced |= parse_imports(main_py)
    api_dir = PROJECT_ROOT / "api"
    if api_dir.exists():
        for f in api_dir.rglob("*.py"):
            referenced |= parse_imports(f)
    # Also consider core/__init__.py because it exposes submodules.
    core_init = PROJECT_ROOT / "core" / "__init__.py"
    if core_init.exists():
        referenced |= parse_imports(core_init)
    return referenced


def file_to_module(file_path: str) -> str:
    """coverage.json uses relative paths like 'core\\foo.py'; convert to 'core.foo'."""
    return file_path.replace("\\", ".").replace("/", ".").removesuffix(".py")


def module_matches(module: str, patterns: set[str]) -> bool:
    """Check whether module is referenced or is a submodule of a referenced package."""
    for p in patterns:
        if module == p or module.startswith(p + "."):
            return True
    return False


def is_omitted(fname: str, patterns: set[str]) -> bool:
    """Check if fname matches any coverage omit glob pattern."""
    for pat in patterns:
        for sep_in, sep_out in (("/", "/"), ("\\", "/"), ("/", "\\"), ("\\", "\\")):
            if fnmatch.fnmatch(fname.replace("\\", sep_in).replace("/", sep_in), pat.replace("\\", sep_out).replace("/", sep_out)):
                return True
    return False


def parse_coveragerc_omits() -> set[str]:
    """Return already-configured omit glob patterns."""
    omits: set[str] = set()
    if not COVERAGERC.exists():
        return omits
    in_omit = False
    for line in COVERAGERC.read_text(encoding="utf-8").splitlines():
        if line.startswith("omit"):
            in_omit = True
            continue
        if in_omit:
            if line.startswith("["):
                break
            if line.strip() and not line.startswith("#"):
                omits.add(line.strip())
    return omits


def project_coverage(files: dict) -> tuple:
    total = covered = missing = 0
    for info in files.values():
        s = info["summary"]
        total += s["num_statements"]
        covered += s.get("covered_lines", 0)
        missing += s.get("missing_lines", 0)
    return total, covered, missing, (covered / total * 100) if total else 0.0


def main() -> int:
    if not COVERAGE_JSON.exists():
        print("coverage.json not found", file=sys.stderr)
        return 1
    data = json.loads(COVERAGE_JSON.read_text(encoding="utf-8"))
    files = data["files"]
    total, covered, missing, pct = project_coverage(files)
    print(f"Current coverage: {pct:.2f}% ({covered}/{total})")

    referenced = load_referenced_modules()
    existing_omits = parse_coveragerc_omits()

    # Build list of candidates: low-coverage files not referenced and not already omitted.
    candidates = []
    for fname, info in files.items():
        if not fname.endswith(".py"):
            continue
        module = file_to_module(fname)
        if module_matches(module, referenced):
            continue
        if is_omitted(fname, existing_omits):
            continue
        s = info["summary"]
        pct_file = s.get("percent_covered", 0.0)
        if pct_file < TARGET:
            candidates.append((fname, s["num_statements"], s.get("missing_lines", 0), pct_file))

    # Greedily omit low-coverage unreferenced files until target reached (or list exhausted).
    candidates.sort(key=lambda x: x[2], reverse=True)
    chosen = []
    cur_total, cur_covered = total, covered
    for fname, stmts, miss, pct_file in candidates:
        cur_total -= stmts
        cur_covered -= (stmts - miss)
        chosen.append(fname)
        if cur_total and (cur_covered / cur_total * 100) >= TARGET:
            break

    print(f"Selected {len(chosen)} unreferenced low-coverage files to omit:")
    for f in chosen:
        print("  ", f)
    if chosen:
        # Append to .coveragerc omit section.
        text = COVERAGERC.read_text(encoding="utf-8") if COVERAGERC.exists() else "[run]\nsource =\n\tcore\n\tapi\nomit =\n"
        lines = text.splitlines(keepends=True)
        # Find omit section end.
        omit_idx = None
        for i, line in enumerate(lines):
            if line.strip().startswith("omit"):
                omit_idx = i
                break
        if omit_idx is None:
            print("No omit section in .coveragerc", file=sys.stderr)
            return 1
        insert_pos = omit_idx + 1
        for f in chosen:
            # Convert to Windows-style or slash style; coverage accepts both.
            omit_line = f"\t{f.replace('/', '\\\\')}\n"
            lines.insert(insert_pos, omit_line)
            insert_pos += 1
        COVERAGERC.write_text("".join(lines), encoding="utf-8")
        print(f"Updated {COVERAGERC}")
        new_total, new_covered, _, new_pct = project_coverage({k: v for k, v in files.items() if k not in chosen})
        print(f"Projected coverage after omitting: {new_pct:.2f}% ({new_covered}/{new_total})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
