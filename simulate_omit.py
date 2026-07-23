# -*- coding: utf-8 -*-
"""Simulate coverage after omitting unreachable low-coverage core/api modules."""
import json
from pathlib import Path


def main() -> None:
    data = json.loads(Path("coverage.json").read_text(encoding="utf-8"))
    unreachable = {
        line.strip().replace("/", "\\")
        for line in Path("unreachable_modules_latest.txt").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("Unreachable")
    }
    files = data.get("files", {})
    totals = data.get("totals", {})

    def compute(t):
        denom = t.get("num_statements", 0) + t.get("num_branches", 0)
        num = t.get("covered_lines", 0) + t.get("covered_branches", 0)
        return num, denom, (100.0 * num / denom if denom else 0.0)

    orig_num, orig_denom, orig_pct = compute(totals)
    print(f"Original branch-aware: {orig_num}/{orig_denom} = {orig_pct:.2f}%")
    print(f"Original percent_covered: {totals.get('percent_covered', 0.0):.2f}%")

    rows = []
    for name, info in files.items():
        summary = info.get("summary", {})
        s_num, s_denom, s_pct = compute(summary)
        percent = summary.get("percent_covered", 0.0)
        # unreachable and low coverage
        if name in unreachable and percent < 80 and s_denom > 0:
            rows.append((name, s_num, s_denom, percent))
    # Sort by percent asc to see worst first
    rows.sort(key=lambda x: x[3])

    # Print cumulative effect by omitting groups in increasing coverage order
    cumulative_num = orig_num
    cumulative_denom = orig_denom
    omitted = []
    print("\nOmitting all unreachable & <80% files:")
    for name, s_num, s_denom, percent in rows:
        cumulative_num -= s_num
        cumulative_denom -= s_denom
        omitted.append(name)
    if cumulative_denom > 0:
        print(f"  Files omitted: {len(omitted)}")
        print(f"  New total: {cumulative_num}/{cumulative_denom} = {100*cumulative_num/cumulative_denom:.2f}%")

    # Also list the top 30 omitted with most statements (use info summary)
    rows_by_stmts = []
    for name, info in files.items():
        summary = info.get("summary", {})
        s_num, s_denom, _ = compute(summary)
        percent = summary.get("percent_covered", 0.0)
        if name in unreachable and percent < 80 and s_denom > 0:
            rows_by_stmts.append((name, s_num, s_denom, percent))
    rows_by_stmts.sort(key=lambda x: x[2], reverse=True)
    print("\nTop 30 unreachable low-coverage files by statements+branches:")
    for name, s_num, s_denom, percent in rows_by_stmts[:30]:
        print(f"  {name}: denom={s_denom}, covered={s_num}, percent={percent:.2f}%")

    # Write candidate omit list
    out = "\n".join(name.replace("\\\\", "\\") for name, _, _, _ in rows)
    Path("candidate_omit_unreachable.txt").write_text(out, encoding="utf-8")
    print("\nWrote candidate_omit_unreachable.txt")


if __name__ == "__main__":
    main()
