# -*- coding: utf-8 -*-
"""Select top reachable low-coverage modules for smoke testing."""
from pathlib import Path


def main() -> None:
    rows = []
    for line in Path("reachable_low_coverage.txt").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        parts = line.strip().split(",")
        name, stmts, branches, missing_lines, denom, covered, percent = parts
        missing = int(denom) - int(covered)
        rows.append((name, missing, float(percent)))
    rows.sort(key=lambda x: x[1], reverse=True)
    for name, missing, percent in rows[:30]:
        print(f"{name}: missing={missing}, percent={percent:.2f}")


if __name__ == "__main__":
    main()
