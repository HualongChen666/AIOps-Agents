# -*- coding: utf-8 -*-
"""Phase 3 Prometheus metrics for the AIOps SRE Agent."""

from __future__ import annotations

from prometheus_client import Counter, Gauge

HEAL_TOTAL = Counter(
    "heal_total",
    "Total number of heal workflows started",
    ["script_key"],
)

HEAL_SUCCESS = Counter(
    "heal_success",
    "Total number of heal workflows that succeeded",
    ["script_key"],
)

HEAL_FAILED = Counter(
    "heal_failed",
    "Total number of heal workflows that failed",
    ["script_key"],
)

HEAL_PENDING_APPROVAL = Gauge(
    "heal_pending_approval",
    "Number of alerts currently awaiting approval",
    ["alert_id"],
)

VERIFY_PASSED = Counter(
    "verify_passed",
    "Total number of verifications that passed",
    ["strategy"],
)

VERIFY_FAILED = Counter(
    "verify_failed",
    "Total number of verifications that failed",
    ["strategy"],
)

LLM_COST_PER_INCIDENT = Counter(
    "llm_cost_per_incident_usd",
    "Estimated LLM cost per incident in USD",
    ["model"],
)
