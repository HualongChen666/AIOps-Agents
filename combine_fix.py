# -*- coding: utf-8 -*-
"""Recombine per-phase coverage data and write a UTF-8 text report."""
import glob
import io
from pathlib import Path

from coverage import Coverage

phase_files = sorted(glob.glob(".coverage_phase_*"))
if not phase_files:
    raise SystemExit("No phase coverage files found")

cov = Coverage(config_file=".coveragerc")
cov.load()
cov.combine(phase_files, keep=False)
cov.save()
print(f"Combined {len(phase_files)} phase files")

buf = io.StringIO()
cov.report(file=buf, show_missing=True)
text = buf.getvalue()
Path("coverage_report.txt").write_text(text, encoding="utf-8")
for line in text.splitlines()[-5:]:
    print(line)
