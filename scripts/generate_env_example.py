# -*- coding: utf-8 -*-
# Generate .env.example from core/config_models.py aliases.
from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
src = (ROOT / "core/config_models.py").read_text(encoding="utf-8")
aliases = sorted(set(re.findall(r'alias="([A-Z_0-9]+)"', src)))
lines = ["# AIOps Agent environment variables", "# Generated from core/config_models.py", ""]
lines += [f"{alias}=" for alias in aliases]
lines += ["", "# General", "ENVIRONMENT=development", "DEBUG=true", "LOG_LEVEL=INFO", ""]
(ROOT / ".env.example").write_text("\n".join(lines), encoding="utf-8")
print(f"generated {len(aliases)} variables")
