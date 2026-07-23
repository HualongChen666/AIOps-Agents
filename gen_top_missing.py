# -*- coding: utf-8 -*-
"""Generate TOP_MISSING_MODULES for test_top_missing_smoke.py."""
import ast
from pathlib import Path


def main() -> None:
    # Load ACTIVE_MODULES and SKIP_MODULE_PREFIXES from test_low_coverage_method_smoke.py
    text = Path("tests/core/test_low_coverage_method_smoke.py").read_text(encoding="utf-8")
    tree = ast.parse(text)
    active_modules = []
    skip_prefixes = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    if target.id == "ACTIVE_MODULES":
                        active_modules = [elt.s for elt in node.value.elts]
                    elif target.id == "SKIP_MODULE_PREFIXES":
                        skip_prefixes = [elt.s for elt in node.value.elts]

    # Modules already tested by top_missing_smoke that we want to keep (non-omitted)
    current = [
        "core.database_connection_optimizer",
        "core.database_cache_optimizer",
        "core.database_query_optimizer",
        "core.config_manager",
        "core.stats_engine",
        "core.alert_intelligence",
        "core.metrics_history",
        "core.ai_service",
        "core.alert_service",
        "core.agent.tools",
        "core.agent.subagent",
        "core.agent.executor",
        "core.security_monitoring",
    ]

    # Omitted unreachable modules to drop
    omitted = {
        line.strip().replace("/", "\\").replace("\\", ".").replace(".py", "")
        for line in Path("candidate_omit_unreachable.txt").read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    current = [m for m in current if m not in omitted]

    # Add reachable high-missing modules not in ACTIVE or SKIP_PREFIX
    reachable = []
    for line in Path("reachable_low_coverage.txt").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        parts = line.strip().split(",")
        name, stmts, branches, missing_lines, denom, covered, percent = parts
        mod = name.replace("\\", ".").replace(".py", "")
        if not mod.startswith("core."):
            continue
        if mod in active_modules or mod in current:
            continue
        if any(mod.startswith(p) for p in skip_prefixes):
            continue
        if mod in omitted:
            continue
        missing = int(denom) - int(covered)
        reachable.append((mod, missing))
    reachable.sort(key=lambda x: x[1], reverse=True)

    # Include top 20 reachable high-missing
    selected = current + [m for m, _ in reachable[:20]]
    print(f"Selected {len(selected)} modules")
    for m, _ in reachable[:20]:
        print(f"  {m}")

    # Update test_top_missing_smoke.py
    target = Path("tests/core/test_top_missing_smoke.py")
    content = target.read_text(encoding="utf-8")
    start_marker = "TOP_MISSING_MODULES = ["
    end_marker = "]"
    start = content.find(start_marker)
    end = content.find(end_marker, start) + len(end_marker)
    new_list = "TOP_MISSING_MODULES = [\n" + "".join(f'    "{m}",\n' for m in selected) + "]\n"
    target.write_text(content[:start] + new_list + content[end:], encoding="utf-8")
    print("Updated tests/core/test_top_missing_smoke.py")


if __name__ == "__main__":
    main()
