# -*- coding: utf-8 -*-
"""List core modules with missing statements > threshold not in test_active_method_smoke.py."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
with open(ROOT / "coverage.json", "r", encoding="utf-8") as f:
    data = json.load(f)

current_text = (ROOT / "tests" / "core" / "test_active_method_smoke.py").read_text(encoding="utf-8")
# Extract current ACTIVE_MODULES entries between brackets
import re
m = re.search(r"ACTIVE_MODULES = \[(.*?)\]", current_text, re.S)
current = set()
if m:
    for line in m.group(1).splitlines():
        line = line.strip()
        if line.startswith('"'):
            current.add(line.strip('",'))

skip_prefixes = (
    "core.analysis.l2.rag_engine",
    "core.ai.llm_router.enhanced_router",
    "core.ai.rag.retriever",
    "core.qdrant_service",
    "core.cloud_collector",
    "core.storage.l4",
    "core.real_integration",
    "core.cache_helpers",
)

missing_threshold = 20
candidates = []
for k, v in data["files"].items():
    if not k.startswith("core\\"):
        continue
    s = v["summary"]
    if s["percent_statements_covered"] < 80 and s["missing_lines"] >= missing_threshold:
        mod = k.replace("core\\", "core.", 1).replace("\\", ".").replace(".py", "")
        if mod in current:
            continue
        if any(mod.startswith(p) for p in skip_prefixes):
            continue
        candidates.append((mod, s["missing_lines"], s["percent_statements_covered"]))

candidates.sort(key=lambda x: -x[1])
print(f"Candidates (missing >= {missing_threshold}, not in current): {len(candidates)}")
for mod, miss, pct in candidates:
    print(f'    "{mod}",  # missing {miss} ({pct:.1f}%)')
