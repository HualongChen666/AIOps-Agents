# -*- coding: utf-8 -*-
"""Generate a UTF-8 text coverage report from the combined .coverage data."""
import io
from pathlib import Path
from coverage import Coverage

cov = Coverage(config_file=".coveragerc")
cov.load()
buf = io.StringIO()
cov.report(file=buf, show_missing=True)
text = buf.getvalue()
Path("coverage_report.txt").write_text(text, encoding="utf-8")
print(text.splitlines()[-5:])
