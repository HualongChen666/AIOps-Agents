# -*- coding: utf-8 -*-
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path("C:/AIOps_Agent_bak")

for path in sorted((ROOT / "core").rglob("*.py")):
    rel = path.relative_to(ROOT)
    parts = rel.with_suffix("").parts
    if parts[-1] == "__init__":
        parts = parts[:-1]
    mod = ".".join(parts)
    if mod == "core":
        continue
    sys.modules[mod] = MagicMock()

# Also mock config lightly if not present
if "config" not in sys.modules:
    sys.modules["config"] = MagicMock()

try:
    import main
    print("main imported ok")
    print("app routes:", len(main.app.routes))
except Exception as e:
    import traceback
    traceback.print_exc()
    sys.exit(1)
