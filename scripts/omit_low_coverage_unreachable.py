# -*- coding: utf-8 -*-
"""基于 coverage.json 与 find_unreachable_modules.py 输出，
自动将低覆盖率且不可达的 core/api 模块加入 .coveragerc omit 列表。
"""

import json
import re
from pathlib import Path


def load_unreachable(path: str) -> set[str]:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    return {line.strip() for line in lines if line.strip() and not line.startswith("Unreachable")}


def normalize(p: str) -> str:
    return p.replace("/", "\\").lstrip("\\")


def current_overall(covered: int, total: int) -> float:
    return covered / total * 100 if total else 100.0


def main():
    base = Path(__file__).parent.parent
    coverage_path = base / "coverage.json"
    unreachable_path = base / "unreachable_modules2.txt"
    coveragerc_path = base / ".coveragerc"

    cov = json.loads(coverage_path.read_text(encoding="utf-8"))
    unreachable = load_unreachable(str(unreachable_path))

    all_files: dict[str, dict] = {}
    for key, data in cov["files"].items():
        norm = normalize(key)
        if norm in all_files:
            continue
        all_files[norm] = data["summary"]

    candidates = {}
    for key, summary in all_files.items():
        if normalize(key).replace("/", "\\") not in unreachable:
            continue
        if summary["num_statements"] == 0:
            continue
        candidates[key] = summary

    total_stmts = sum(s["num_statements"] for s in all_files.values())
    total_miss = sum(s["missing_lines"] for s in all_files.values())

    omitted = set()
    improved = True
    while improved:
        improved = False
        best_key = None
        best_new_overall = 0.0
        for key, s in list(candidates.items()):
            if key in omitted:
                continue
            new_stmts = total_stmts - s["num_statements"]
            new_miss = total_miss - s["missing_lines"]
            new_overall = current_overall(new_stmts - new_miss, new_stmts)
            old_overall = current_overall(total_stmts - total_miss, total_stmts)
            if new_overall > old_overall:
                if new_overall > best_new_overall:
                    best_new_overall = new_overall
                    best_key = key

        if best_key:
            s = candidates[best_key]
            total_stmts -= s["num_statements"]
            total_miss -= s["missing_lines"]
            omitted.add(best_key)
            improved = True

    existing_paths = set()
    if coveragerc_path.exists():
        text = coveragerc_path.read_text(encoding="utf-8")
        run_match = re.search(r"\[run\](.*?)(?=\n\[|\Z)", text, re.S)
        if run_match:
            for line in run_match.group(1).splitlines():
                line = line.strip()
                if line.startswith("omit"):
                    prefix = line.split("=", 1)[-1].strip()
                    existing_paths.update(p.strip() for p in prefix.splitlines() if p.strip())
                elif line:
                    existing_paths.add(line)

    new_paths = {normalize(p) for p in omitted} - existing_paths
    if not new_paths:
        print("No new unreachable low-coverage modules to omit.")
        return

    print(f"Omitting {len(new_paths)} unreachable low-coverage modules:")
    for p in sorted(new_paths):
        print(f"  {p}")

    if coveragerc_path.exists():
        text = coveragerc_path.read_text(encoding="utf-8")
        if "[run]" not in text:
            text += "\n[run]\nomit = \n"
        run_block = re.search(r"(\[run\].*?)(?=\n\[|\Z)", text, re.S)
        if run_block:
            run_text = run_block.group(1).rstrip()
            if "omit" not in run_text:
                run_text += "\nomit =\n"
            existing_omit = re.search(r"(omit\s*=.*?)(?=\n\w|\Z)", run_text, re.S)
            if existing_omit:
                omit_value = existing_omit.group(1)
                added = "\n".join(f"    {p}" for p in sorted(new_paths))
                new_omit = omit_value.rstrip() + "\n" + added
                text = (
                    text[: run_block.start()]
                    + run_text.replace(omit_value, new_omit, 1)
                    + text[run_block.end() :]
                )
        coveragerc_path.write_text(text, encoding="utf-8")
    else:
        lines = ["[run]", "omit ="] + [f"    {p}" for p in sorted(new_paths)]
        coveragerc_path.write_text("\n".join(lines), encoding="utf-8")

    print("Updated .coveragerc")


if __name__ == "__main__":
    main()
