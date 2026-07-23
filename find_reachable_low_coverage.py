# -*- coding: utf-8 -*-
"""List low-coverage core/api modules that are reachable (not in unreachable list)."""
import json
from pathlib import Path


def main() -> None:
    data = json.loads(Path("coverage.json").read_text(encoding="utf-8"))
    unreachable = {
        line.strip().replace("/", "\\")
        for line in Path("unreachable_modules_latest.txt").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("Unreachable")
    }

    rows = []
    for name, file_info in data.get("files", {}).items():
        summary = file_info.get("summary", {})
        stmts = summary.get("num_statements", 0)
        missing = summary.get("missing_lines", 0)
        percent = summary.get("percent_covered", 0.0)
        branches = summary.get("num_branches", 0)
        covered_branches = summary.get("covered_branches", 0)
        if stmts == 0:
            continue
        if name not in unreachable and percent < 80 and missing > 0:
            denom = stmts + branches
            covered = stmts - missing + covered_branches
            rows.append((name, stmts, branches, missing, denom, covered, percent))
    rows.sort(key=lambda x: x[4] - x[5])  # missing by branch+stmt
    out_lines = []
    for r in rows:
        out_lines.append(f"{r[0]},{r[1]},{r[2]},{r[3]},{r[4]},{r[5]},{r[6]}")
    Path("reachable_low_coverage.txt").write_text("\n".join(out_lines), encoding="utf-8")
    print("Reachable low-coverage modules:", len(rows))
    for line in out_lines[:30]:
        print(line)
    total_missing = sum(r[4] - r[5] for r in rows)
    print(f"\nTotal statements+branches missing: {total_missing}")


if __name__ == "__main__":
    main()
