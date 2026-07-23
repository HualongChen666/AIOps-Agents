# -*- coding: utf-8 -*-
"""分析 coverage.json，找出覆盖低且可达的核心/ API 模块，并给出覆盖率提升潜力。"""

import json
from pathlib import Path


def main():
    base = Path(__file__).parent.parent
    cov = json.loads((base / "coverage.json").read_text(encoding="utf-8"))

    total_stmts = sum(d["summary"]["num_statements"] for d in cov["files"].values())
    total_miss = sum(d["summary"]["missing_lines"] for d in cov["files"].values())
    overall = (total_stmts - total_miss) / total_stmts * 100
    print(f"当前总覆盖率: {overall:.2f}%  (stmts={total_stmts} miss={total_miss})")

    low_files = []
    for key, data in cov["files"].items():
        if not (key.startswith("core") or key.startswith("api")):
            continue
        s = data["summary"]
        if s["num_statements"] == 0:
            continue
        covered = s["num_statements"] - s["missing_lines"]
        pct = covered / s["num_statements"] * 100
        if pct < 80:
            low_files.append((key, s["num_statements"], s["missing_lines"], pct))

    low_files.sort(key=lambda x: x[2], reverse=True)

    print(f"\n低于 80% 的 core/api 文件数: {len(low_files)}")
    print("\n按缺失语句数排序前 30 (覆盖这些可最大程度提升覆盖率):\n")
    cumulative = 0
    for key, stmts, miss, pct in low_files[:30]:
        cumulative += miss
        print(f"  {key}: stmts={stmts} miss={miss} cov={pct:.1f}%")

    potential = (total_stmts - total_miss + cumulative) / total_stmts * 100
    print(f"\n若完全覆盖前 30 文件缺失行，总覆盖率可升至: {potential:.2f}%")


if __name__ == "__main__":
    main()
