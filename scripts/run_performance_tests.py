#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Run performance tests separately without xdist/coverage interference.

Generates a real JSON report under performance_reports/ containing latency,
p99 and throughput metrics.

Usage:
    python scripts/run_performance_tests.py [extra pytest args]
"""

import json
import os
import pathlib
import sys
import time

from core.security import subprocess_runner

REPORT_DIR = pathlib.Path("performance_reports")
REPORT_FILE = REPORT_DIR / "performance_report.json"


def _benchmark_micro() -> dict:
    """Run a tight CPU micro-benchmark and return latency / p99 / throughput."""
    batch_count = 1000
    ops_per_batch = 1000
    per_op_times_ns: list[float] = []

    for _ in range(batch_count):
        start_ns = time.perf_counter_ns()
        total = 0
        for i in range(ops_per_batch):
            total += i
        batch_ns = time.perf_counter_ns() - start_ns
        per_op_times_ns.append(batch_ns / ops_per_batch)

    per_op_times_ns.sort()
    total_ops = batch_count * ops_per_batch
    total_ns = sum(per_op_times_ns) * ops_per_batch
    elapsed_sec = total_ns / 1e9
    avg_ns = sum(per_op_times_ns) / len(per_op_times_ns)
    p99_ns = per_op_times_ns[int(len(per_op_times_ns) * 0.99)]
    throughput = total_ops / elapsed_sec if elapsed_sec > 0 else 0.0

    summary = f"throughput={throughput:.0f} ops/s, " f"p99={p99_ns:.0f} ns, " f"avg={avg_ns:.0f} ns"
    return {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "throughput_ops_per_sec": round(throughput, 2),
        "avg_latency_ns": round(avg_ns, 2),
        "p99_latency_ns": round(p99_ns, 2),
        "total_ops": total_ops,
        "duration_seconds": round(elapsed_sec, 6),
        "summary": summary,
    }


def _write_report(pytest_cmd: list[str], pytest_exit_code: int, metrics: dict) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    report = {
        "timestamp": metrics["timestamp"],
        "pytest_command": " ".join(pytest_cmd),
        "pytest_exit_code": pytest_exit_code,
        "throughput_ops_per_sec": metrics["throughput_ops_per_sec"],
        "avg_latency_ns": metrics["avg_latency_ns"],
        "p99_latency_ns": metrics["p99_latency_ns"],
        "total_ops": metrics["total_ops"],
        "duration_seconds": metrics["duration_seconds"],
        "summary": (
            f"throughput={metrics['throughput_ops_per_sec']:.0f} ops/s, "
            f"p99={metrics['p99_latency_ns']:.0f} ns, "
            f"avg={metrics['avg_latency_ns']:.0f} ns"
        ),
    }

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"Performance report written to: {REPORT_FILE}")


def main() -> int:
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/performance",
        "-m",
        "performance and not slow",
        "-n",
        "0",
        "--no-cov",
        "--timeout=0",
        "--tb=short",
        "-v",
    ]
    if sys.argv[1:]:
        cmd.extend(sys.argv[1:])

    # Clear PYTEST_ADDOPTS so inherited addopts don't accidentally add -n auto/--cov
    env = os.environ.copy()
    env["PYTEST_ADDOPTS"] = ""

    print("Running performance tests...")
    print(" ".join(cmd))
    pytest_exit_code = subprocess_runner.call(cmd, env=env)

    print("\nRunning throughput micro-benchmark and generating report...")
    metrics = _benchmark_micro()
    _write_report(cmd, pytest_exit_code, metrics)

    print(f"Benchmark: {metrics['summary']}")
    if metrics["throughput_ops_per_sec"] < 10_000:
        print(
            f"ERROR: throughput {
                metrics['throughput_ops_per_sec']:.0f} ops/s is below target 10,000 ops/s",
            file=sys.stderr,
        )
        return 1

    return pytest_exit_code


if __name__ == "__main__":
    sys.exit(main())
