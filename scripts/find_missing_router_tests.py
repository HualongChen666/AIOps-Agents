"""List API/core/modules routers that do not yet have a dedicated test file."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

ROUTER_SOURCES = {
    "api": ROOT / "api",
    "core": ROOT / "core",
    "modules": ROOT / "modules",
}


def find_missing(prefix: str, source: Path, test_dir: Path) -> list[Path]:
    missing = []
    if not source.exists():
        return missing
    test_dir.mkdir(parents=True, exist_ok=True)
    existing_tests = {p.name for p in test_dir.glob("test_*.py")} if test_dir.exists() else set()
    for path in source.rglob("*.py"):
        content = path.read_text(encoding="utf-8", errors="ignore")
        if "APIRouter(" not in content:
            continue
        # Accept any test filename that contains the router stem (handles prefixes like test_core_*)
        if not any(path.stem in name for name in existing_tests):
            missing.append(path)
    return missing


def main():
    all_missing = []
    for prefix, source in ROUTER_SOURCES.items():
        test_dir = ROOT / "tests" / prefix
        missing = find_missing(prefix, source, test_dir)
        all_missing.extend(missing)
        print(f"# {prefix}: {len(missing)} missing router test files")
        for p in sorted(missing):
            print(f"missing: {p.relative_to(ROOT)}")
    print(f"\nTOTAL missing: {len(all_missing)}")


if __name__ == "__main__":
    main()
