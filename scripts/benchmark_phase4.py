#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Throughput benchmark for phase-4 services."""

import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, "C:/AIOps_Agent_bak")

SERVICES = [
    "prometheus_integration_service",
    "grafana_integration_service",
    "elk_stack_service",
    "datadog_integration_service",
    "cloud_monitoring_service",
    "ansible_automation_service",
    "terraform_iac_service",
    "kubernetes_orchestration_service",
]


def benchmark(service_name: str) -> dict:
    metrics_mod = __import__(f"services.{service_name}.metrics", fromlist=["MetricsCollector"])
    service_mod = __import__(f"services.{service_name}.service", fromlist=["OPERATIONS", "Service"])
    MetricsCollector = metrics_mod.MetricsCollector
    Service = service_mod.Service
    OPERATIONS = service_mod.OPERATIONS

    op = OPERATIONS[0]
    n = 1000
    metrics = MetricsCollector(f"{service_name.replace('_', '-')}-bench")
    service = Service(redis_url="", metrics=metrics)
    async def _run() -> None:
        coros = [
            getattr(service, op)({
                "config": {"i": i},
                "idempotency_key": f"bench-{i}",
            })
            for i in range(n)
        ]
        await asyncio.gather(*coros)

    start = time.perf_counter()
    asyncio.run(_run())
    elapsed = time.perf_counter() - start
    ops_per_sec = n / elapsed
    return {
        "service": service_name,
        "operation": op,
        "requests": n,
        "elapsed_seconds": round(elapsed, 3),
        "ops_per_second": round(ops_per_sec, 0),
        "target_ops_per_second": 10000,
        "passed": ops_per_sec >= 10000,
    }


def main() -> int:
    results = []
    for svc in SERVICES:
        print(f"Benchmarking {svc} ...")
        results.append(benchmark(svc))
    out = Path("C:/AIOps_Agent_bak/verify_logs/phase4_performance_report.json")
    out.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
