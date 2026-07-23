import configparser
import os
from pathlib import Path

ROOT = Path.cwd()
UNREACHABLE_FILE = ROOT / "unreachable_modules.txt"
COVERAGERC = ROOT / ".coveragerc"


def normalize(p: str) -> str:
    # convert both backslash styles to forward slashes, drop .py if present
    p = p.strip().replace("\\\\", "/").replace("\\", "/")
    if p.endswith(".py"):
        p = p[:-3]
    return p


def main():
    parser = configparser.ConfigParser(allow_no_value=True)
    # Preserve case sensitivity
    parser.optionxform = str
    parser.read(COVERAGERC, encoding="utf-8")

    run_omit = set()
    report_omit = set()
    if parser.has_option("run", "omit"):
        raw = parser.get("run", "omit")
        run_omit = {normalize(line) for line in raw.splitlines() if line.strip() and not line.strip().startswith("#")}
    if parser.has_option("report", "omit"):
        raw = parser.get("report", "omit")
        report_omit = {normalize(line) for line in raw.splitlines() if line.strip() and not line.strip().startswith("#")}

    unreachable = set()
    if UNREACHABLE_FILE.exists():
        for line in UNREACHABLE_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("Unreachable"):
                unreachable.add(normalize(line))

    # Patterns that are generic, not file-level
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

    def classify(entry: str):
        if entry in generic_norm:
            return "generic"
        if entry in unreachable:
            return "unreachable"
        return "reachable"

    print("=== RUN omit classification ===")
    for entry in sorted(run_omit):
        label = classify(entry)
        print(label, entry)

    print("\n=== REPORT-only omit entries ===")
    report_only = report_omit - run_omit
    for entry in sorted(report_only):
        print(classify(entry), entry)

    print("\n=== Potentially reachable RUN omits (candidate for removal) ===")
    for entry in sorted(run_omit):
        if classify(entry) == "reachable":
            print(entry)

    print("\n=== Unreachable modules NOT in RUN omit (candidates for omit) ===")
    for entry in sorted(unreachable - run_omit):
        if entry not in generic_norm:
            print(entry)


if __name__ == "__main__":
    main()
