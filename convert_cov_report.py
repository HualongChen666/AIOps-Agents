# -*- coding: utf-8 -*-
"""Convert PowerShell-redirected UTF-16 coverage report to UTF-8."""
from pathlib import Path

src = Path("coverage_report.txt")
dst = Path("coverage_report_utf8.txt")

text = src.read_text(encoding="utf-16", errors="ignore")
dst.write_text(text, encoding="utf-8")
print("converted")
print(text.splitlines()[-10:])
