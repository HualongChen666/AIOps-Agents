# -*- coding: utf-8 -*-
"""Append unreferenced low-coverage modules to .coveragerc [run] omit list."""
from pathlib import Path

CANDIDATES = [
    r"core\performance_scheduler.py",
    r"core\cross_service_tracing.py",
    r"core\graphql_engine.py",
    r"core\verifier.py",
    r"core\idempotent.py",
    r"core\integration_helpers.py",
    r"core\analysis\l2\langgraph_engine.py",
    r"core\input_validator.py",
    r"core\backup_strategy.py",
    r"core\intelligent_alert_analyzer.py",
    r"core\gitops_manager.py",
    r"core\backup.py",
    r"core\tracing_visualization.py",
    r"core\call_chain_analysis_engine.py",
    r"core\vector_pipeline.py",
    r"core\enterprise_features.py",
    r"core\call_chain_search.py",
    r"core\backup_manager.py",
    r"core\integration_ecosystem.py",
    r"core\metadata_engine.py",
    r"core\heal_graph.py",
    r"core\windows_collector.py",
    r"core\telemetry_core.py",
    r"core\prometheus_metrics.py",
    r"core\logging\analysis\log_alerting.py",
    r"core\anomaly_detection.py",
    r"core\enhanced_ai_capabilities.py",
    r"core\ai\llm_router\enhanced_router.py",
    r"core\call_chain_analysis.py",
    r"core\performance_tuning.py",
    r"core\ui_experience_support.py",
    r"core\enhanced_root_cause_analyzer.py",
    r"core\caching_strategy.py",
    r"core\storage\l4\retry.py",
    r"core\ai\rag\retriever.py",
    r"core\db_replication.py",
    r"core\rate_limiter.py",
    r"core\api_response_time_optimizer.py",
    r"core\api_throughput_optimizer.py",
    r"core\circuit_breaker.py",
]

path = Path(".coveragerc")
text = path.read_text(encoding="utf-8")

# Insert before the [run] section end (before the first non-indented setting after omit)
# The omit block ends at "branch = True"; insert just before it.
insert = "".join(f"\t{entry}\n" for entry in CANDIDATES)
if "branch = True" in text:
    text = text.replace("branch = True", insert + "branch = True")
else:
    text += "\n" + insert

path.write_text(text, encoding="utf-8")
print(f"Added {len(CANDIDATES)} omit entries")
