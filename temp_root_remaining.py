from pathlib import Path

ROOT = Path.cwd()
files = sorted(
    p for p in (ROOT / "tests").glob("test_*.py")
    if "_integration" not in p.name
)
for f in files:
    print(f)
