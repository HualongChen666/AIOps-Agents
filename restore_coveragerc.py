#!/usr/bin/env python
"""Restore .coveragerc by removing the auto-added omit entries."""
import re
from pathlib import Path

path = Path(".coveragerc")
lines = path.read_text(encoding="utf-8").splitlines()
out = []
in_run = False
in_run_omit = False
in_report = False
in_report_omit = False

for line in lines:
    stripped = line.strip()
    if stripped.startswith("["):
        in_run = stripped == "[run]"
        in_report = stripped == "[report]"
        in_report_omit = False
        out.append(line)
        continue

    if in_run and not in_run_omit and stripped == "omit =":
        in_run_omit = True
        out.append(line)
        continue

    if in_run_omit:
        if stripped.startswith("*/"):
            in_run_omit = False
            out.append(line)
        # skip the inserted core/api module lines before the first */
        continue

    if in_report and not in_report_omit and stripped == "omit =":
        in_report_omit = True
        # skip the omit = line itself
        continue

    if in_report_omit:
        if re.match(r"^(core|api)[/\\]", stripped):
            # skip inserted core/api module lines
            continue
        in_report_omit = False

    out.append(line)

path.write_text("\n".join(out) + "\n", encoding="utf-8")
print("Restored .coveragerc")
