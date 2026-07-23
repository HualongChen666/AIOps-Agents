import re
from pathlib import Path


def main() -> None:
    log = Path("cov_with_config.log").read_text(encoding="utf-8", errors="ignore")
    # Find the core phase coverage report between "Running core tests" and "Running api tests"
    m = re.search(
        r"=== Running core tests ===.*?(=== Running api tests ===|==================.*= FAILURES =)",
        log,
        re.DOTALL,
    )
    if not m:
        print("Could not find core phase report")
        return
    section = m.group(0)
    # Find coverage table rows: "path   stmts   miss  cover   missing"
    rows = []
    for line in section.splitlines():
        parts = re.split(r"\s+", line.rstrip())
        if len(parts) >= 4 and parts[0].startswith("core") and parts[0].endswith(".py"):
            try:
                stmts = int(parts[1])
                miss = int(parts[2])
                cover = float(parts[3].rstrip("%"))
                rows.append((parts[0], stmts, miss, cover))
            except ValueError:
                continue
    rows.sort(key=lambda x: x[2], reverse=True)
    print(f"CORE phase rows found: {len(rows)}")
    print("TOP20 missing:")
    for r in rows[:20]:
        print(f"{r[0]},{r[1]},{r[2]},{r[3]}")
    low = [r for r in rows if r[3] < 80 and r[1] > 0]
    print(f"\nLOW_COVERAGE (<80%): {len(low)}")
    for r in low[:20]:
        print(f"{r[0]},{r[1]},{r[2]},{r[3]}")


if __name__ == "__main__":
    main()
