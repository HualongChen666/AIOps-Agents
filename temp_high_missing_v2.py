# -*- coding: utf-8 -*-
"""List core modules with missing statements > threshold not in smoke tests."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
with open(ROOT / "coverage.json", "r", encoding="utf-8") as f:
    data = json.load(f)

smoke_files = [
    ROOT / "tests" / "core" / "test_active_smoke.py",
    ROOT / "tests" / "core" / "test_active_method_smoke.py",
    ROOT / "tests" / "core" / "test_low_coverage_method_smoke.py",
]
current = set()
for p in smoke_files:
    if not p.exists():
        continue
    text = p.read_text(encoding="utf-8")
    m = re.search(r"ACTIVE_MODULES = \[(.*?)\]", text, re.S)
    if m:
        for line in m.group(1).splitlines():
            line = line.strip()
            if line.startswith('"'):
                current.add(line.strip('",').split('#')[0].strip())

skip_prefixes = (
    "core.analysis.l2.rag_engine",
    "core.ai.llm_router.enhanced_router",
    "core.ai.rag.retriever",
    "core.qdrant_service",
    "core.cloud_collector",
    "core.storage.l4",
    "core.real_integration",
    "core.cache_helpers",
    "core.flink_stream_processor",
    "core.kafka_stream_processor",
    "core.kubernetes_deployment_manager",
    "core.model_fine_tuner",
    "core.analysis.l2.model_router",
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
print(f"Candidates (missing >= {missing_threshold}, not in smoke, not skipped): {len(candidates)}")
for mod, miss, pct in candidates[:50]:
    print(f'    "{mod}",  # missing {miss} ({pct:.1f}%)')
