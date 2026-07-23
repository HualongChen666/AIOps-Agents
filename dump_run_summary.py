# -*- coding: utf-8 -*-
"""Extract a compact summary from run.log (UTF-16) into run_summary.txt."""
from pathlib import Path

src = Path("run.log")
text = src.read_text(encoding="utf-16", errors="ignore")
lines = text.splitlines()

out_lines = []
out_lines.append(f"Total log lines: {len(lines)}")
out_lines.append("")

# Print the last pytest summary lines and short test summary
in_summary = False
for line in lines:
    if "short test summary" in line.lower():
        in_summary = True
    if in_summary:
        out_lines.append(line)
    if line.startswith("====") and ("passed" in line or "failed" in line):
        out_lines.append(line)
        in_summary = False

# Also collect all distinct FAILED test names
failed = [line for line in lines if line.startswith("FAILED ")]
out_lines.append("")
out_lines.append(f"Distinct FAILED lines: {len(failed)}")
for f in failed:
    out_lines.append(f)

# Phase markers from run_core_api_infrastructure_tests.py
phase_markers = [line for line in lines if "=== Running" in line or "=== Summary ===" in line]
if phase_markers:
    out_lines.append("")
    out_lines.append("Phase markers:")
    for m in phase_markers:
        out_lines.append(m)

Path("run_summary.txt").write_text("\n".join(out_lines), encoding="utf-8")
print("run_summary.txt written")
