# -*- coding: utf-8 -*-
"""Merge candidate unreachable modules into .coveragerc omit section."""
from pathlib import Path


def main() -> None:
    rc = Path(".coveragerc")
    text = rc.read_text(encoding="utf-8")
    candidates = {
        line.strip()
        for line in Path("candidate_omit_unreachable.txt").read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    # Parse existing omit section under [run]
    lines = text.splitlines()
    in_run = False
    in_omit = False
    existing_omits = set()
    omit_start = None
    omit_end = None
    for i, line in enumerate(lines):
        if line.strip().startswith("["):
            if in_omit:
                omit_end = i
                break
            if line.strip() == "[run]":
                in_run = True
            else:
                in_run = False
            continue
        if in_run and line.strip() == "omit =":
            in_omit = True
            omit_start = i
            continue
        if in_omit:
            if line.strip() == "" or not line.startswith("\t"):
                omit_end = i
                break
            existing_omits.add(line.strip().lstrip("\t"))
    if omit_end is None:
        omit_end = len(lines)
    print(f"Existing omits: {len(existing_omits)}, candidates: {len(candidates)}")
    new_omits = candidates - existing_omits
    print(f"New omits to add: {len(new_omits)}")
    if not new_omits:
        print("No new omits to add")
        return
    # Insert new omits before omit_end, sorted
    insert = [f"\t{module}" for module in sorted(new_omits)]
    new_lines = lines[:omit_end] + insert + [""] + lines[omit_end:]
    rc.write_text("\n".join(new_lines), encoding="utf-8")
    print("Updated .coveragerc")


if __name__ == "__main__":
    main()
