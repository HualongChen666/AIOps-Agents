# -*- coding: utf-8 -*-
"""Combine per-phase coverage data files and emit JSON/text reports."""
import glob
import io
from pathlib import Path

try:
    from coverage import Coverage
except Exception as exc:  # pragma: no cover
    raise SystemExit(f"coverage not installed: {exc}") from exc

phase_files = sorted(glob.glob(".coverage_phase_*"))
if not phase_files:
    raise SystemExit("No .coverage_phase_* files found")

cov = Coverage(config_file=".coveragerc")
cov.load()
cov.combine(phase_files, keep=False)
cov.save()

print(f"Combined {len(phase_files)} phase files into .coverage")

# Generate JSON report
try:
    cov.json_report(outfile="coverage.json")
    print("Wrote coverage.json")
except Exception as exc:
    print(f"JSON report failed: {exc}")

# Generate text report and save to coverage_report.txt
buf = io.StringIO()
try:
    cov.report(file=buf, show_missing=True)
    text = buf.getvalue()
    Path("coverage_report.txt").write_text(text, encoding="utf-8")
    print("Wrote coverage_report.txt")
except Exception as exc:
    print(f"Text report failed: {exc}")

# Print tail of text report to console
if text:
    for line in text.splitlines()[-40:]:
        print(line)
