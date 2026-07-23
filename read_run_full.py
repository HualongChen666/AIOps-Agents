# -*- coding: utf-8 -*-
from pathlib import Path
p = Path("run_full.log")
print(p.read_text(encoding="utf-8", errors="ignore"))
