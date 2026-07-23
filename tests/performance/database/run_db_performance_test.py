#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database Performance Test Runner
数据库性能测试运行脚本
"""

import argparse
import os
import subprocess
import sys


def run_crud_tests(output_dir: str = "reports"):
    """运行CRUD性能测试"""
    cmd = [
        "pytest",
        "tests/performance/database/test_crud_performance.py",
        "-v",
        "--benchmark-only",
        f"--benchmark-json={output_dir}/crud_benchmark.json",
        f"--benchmark-html={output_dir}/crud_benchmark.html",
    ]

    print("Running CRUD performance tests...")
    result = subprocess.run(cmd)
    return result.returncode


def run_pool_tests(output_dir: str = "reports"):
    """运行连接池性能测试"""
    cmd = [
        "pytest",
        "tests/performance/database/test_connection_pool_performance.py",
        "-v",
        "--benchmark-only",
        f"--benchmark-json={output_dir}/pool_benchmark.json",
        f"--benchmark-html={output_dir}/pool_benchmark.html",
    ]

    print("Running connection pool performance tests...")
    result = subprocess.run(cmd)
    return result.returncode


def run_transaction_tests(output_dir: str = "reports"):
    """运行事务性能测试"""
    cmd = [
        "pytest",
        "tests/performance/database/test_transaction_performance.py",
        "-v",
        "--benchmark-only",
        f"--benchmark-json={output_dir}/transaction_benchmark.json",
        f"--benchmark-html={output_dir}/transaction_benchmark.html",
    ]

    print("Running transaction performance tests...")
    result = subprocess.run(cmd)
    return result.returncode


def run_index_tests(output_dir: str = "reports"):
    """运行索引性能测试"""
    cmd = [
        "pytest",
        "tests/performance/database/test_index_performance.py",
        "-v",
        "--benchmark-only",
        f"--benchmark-json={output_dir}/index_benchmark.json",
        f"--benchmark-html={output_dir}/index_benchmark.html",
    ]

    print("Running index performance tests...")
    result = subprocess.run(cmd)
    return result.returncode


def run_all_tests(output_dir: str = "reports"):
    """运行所有数据库性能测试"""
    os.makedirs(output_dir, exist_ok=True)

    results = {
        "crud": run_crud_tests(output_dir),
        "pool": run_pool_tests(output_dir),
        "transaction": run_transaction_tests(output_dir),
        "index": run_index_tests(output_dir),
    }

    return results


def analyze_slow_queries(threshold_ms: float = 100.0):
    """分析慢查询"""
    import asyncio

    from slow_query_analyzer import analyze_slow_queries, check_table_health

    async def run_analysis():
        print(f"Analyzing slow queries (threshold: {threshold_ms}ms)...")
        report = await analyze_slow_queries(threshold_ms=threshold_ms)

        print("\n=== Slow Query Analysis Report ===")
        print(f"Total slow queries: {report['slow_query_count']}")
        print(f"Total calls: {report['summary']['total_calls']}")
        print(f"Total time: {report['summary']['total_time_ms']:.2f}ms")
        print(f"Average time: {report['summary']['avg_time_ms']:.2f}ms")

        print("\n=== Optimization Suggestions ===")
        for opt in report.get("optimizations", []):
            print(f"[{opt['priority'].upper()}] {opt['suggestion']}")
            print(f"  Estimated improvement: {opt['estimated_improvement']:.1f}%")

        print("\n=== Table Health Check ===")
        health_report = await check_table_health()
        for table in health_report["tables"]:
            if table["health"] == "unhealthy":
                print(f"Table {table['table_name']}: UNHEALTHY")
                for issue in table["issues"]:
                    print(f"  - {issue}")

        return report

    return asyncio.run(run_analysis())


def generate_report(output_dir: str = "reports"):
    """生成综合性能报告"""
    import json

    from db_report_generator import DatabaseReportGenerator

    print("Generating comprehensive performance report...")

    # 收集所有测试结果
    data = {
        "total_tests": 0,
        "passed_tests": 0,
        "failed_tests": 0,
        "total_duration": 0,
        "crud_metrics": [],
        "pool_metrics": [],
        "transaction_metrics": [],
        "index_metrics": [],
        "slow_queries": [],
        "optimization_suggestions": [],
    }

    # 读取各个测试的JSON报告
    for test_type in ["crud", "pool", "transaction", "index"]:
        json_file = f"{output_dir}/{test_type}_benchmark.json"
        if os.path.exists(json_file):
            with open(json_file, "r") as f:
                benchmark_data = json.load(f)
                data["total_tests"] += len(benchmark_data.get("benchmarks", []))
                data["total_duration"] += benchmark_data.get("duration", 0)

    # 生成报告
    generator = DatabaseReportGenerator(output_dir)
    html_file = generator.generate_html_report(
        data, {"database": "PostgreSQL", "environment": "Local"}
    )
    json_file = generator.generate_json_report(
        data, {"database": "PostgreSQL", "environment": "Local"}
    )

    print(f"HTML report generated: {html_file}")
    print(f"JSON report generated: {json_file}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="AIOps Agent Database Performance Test Runner")

    parser.add_argument("--all", action="store_true", help="Run all database performance tests")

    parser.add_argument("--crud", action="store_true", help="Run CRUD performance tests")

    parser.add_argument("--pool", action="store_true", help="Run connection pool performance tests")

    parser.add_argument(
        "--transaction", action="store_true", help="Run transaction performance tests"
    )

    parser.add_argument("--index", action="store_true", help="Run index performance tests")

    parser.add_argument("--analyze-slow-queries", action="store_true", help="Analyze slow queries")

    parser.add_argument(
        "--threshold",
        type=float,
        default=100.0,
        help="Slow query threshold in milliseconds (default: 100)",
    )

    parser.add_argument(
        "--generate-report", action="store_true", help="Generate comprehensive performance report"
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default="tests/performance/database/reports",
        help="Output directory for reports (default: tests/performance/database/reports)",
    )

    args = parser.parse_args()

    # 如果没有指定任何测试，默认运行所有测试
    if not any(
        [
            args.all,
            args.crud,
            args.pool,
            args.transaction,
            args.index,
            args.analyze_slow_queries,
            args.generate_report,
        ]
    ):
        args.all = True

    if args.all:
        results = run_all_tests(args.output_dir)
        print("\n=== Test Results ===")
        for test_type, returncode in results.items():
            status = "PASSED" if returncode == 0 else "FAILED"
            print(f"{test_type}: {status}")

        # 如果所有测试都通过，生成报告
        if all(r == 0 for r in results.values()):
            generate_report(args.output_dir)

    if args.crud:
        returncode = run_crud_tests(args.output_dir)
        sys.exit(returncode)

    if args.pool:
        returncode = run_pool_tests(args.output_dir)
        sys.exit(returncode)

    if args.transaction:
        returncode = run_transaction_tests(args.output_dir)
        sys.exit(returncode)

    if args.index:
        returncode = run_index_tests(args.output_dir)
        sys.exit(returncode)

    if args.analyze_slow_queries:
        analyze_slow_queries(args.threshold)

    if args.generate_report:
        generate_report(args.output_dir)


if __name__ == "__main__":
    main()
