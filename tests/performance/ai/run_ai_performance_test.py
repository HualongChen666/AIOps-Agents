#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import datetime

"""
AI Performance Test Runner
AI性能测试运行脚本
"""

import argparse
import os
import subprocess
import sys


def run_llm_tests(output_dir: str = "reports"):
    """运行LLM性能测试"""
    cmd = [
        "pytest",
        "tests/performance/ai/test_llm_performance.py",
        "-v",
        "--benchmark-only",
        f"--benchmark-json={output_dir}/llm_benchmark.json",
        f"--benchmark-html={output_dir}/llm_benchmark.html",
    ]

    print("Running LLM performance tests...")
    result = subprocess.run(cmd)
    return result.returncode


def run_rag_tests(output_dir: str = "reports"):
    """运行RAG性能测试"""
    cmd = [
        "pytest",
        "tests/performance/ai/test_rag_performance.py",
        "-v",
        "--benchmark-only",
        f"--benchmark-json={output_dir}/rag_benchmark.json",
        f"--benchmark-html={output_dir}/rag_benchmark.html",
    ]

    print("Running RAG performance tests...")
    result = subprocess.run(cmd)
    return result.returncode


def run_agent_tests(output_dir: str = "reports"):
    """运行代理性能测试"""
    cmd = [
        "pytest",
        "tests/performance/ai/test_agent_performance.py",
        "-v",
        "--benchmark-only",
        f"--benchmark-json={output_dir}/agent_benchmark.json",
        f"--benchmark-html={output_dir}/agent_benchmark.html",
    ]

    print("Running agent performance tests...")
    result = subprocess.run(cmd)
    return result.returncode


def run_all_tests(output_dir: str = "reports"):
    """运行所有AI性能测试"""
    os.makedirs(output_dir, exist_ok=True)

    results = {
        "llm": run_llm_tests(output_dir),
        "rag": run_rag_tests(output_dir),
        "agent": run_agent_tests(output_dir),
    }

    return results


def generate_cost_report(output_dir: str = "reports"):
    """生成成本报告"""
    from ai_cost_monitor import AICostMonitor

    print("Generating cost report...")

    # 创建模拟成本数据
    monitor = AICostMonitor()

    # 添加一些模拟数据
    monitor.record_usage("gpt-3.5-turbo", 1000, 2000)
    monitor.record_usage("gpt-4", 500, 1000)
    monitor.record_usage("claude-3-sonnet", 800, 1500)

    # 生成报告
    report = monitor.generate_cost_report()

    # 保存报告
    import json

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = os.path.join(output_dir, f"cost_report_{timestamp}.json")

    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)

    print(f"Cost report saved to {report_file}")

    # 生成优化建议
    suggestions = monitor.generate_optimization_suggestions()
    print("\n=== Optimization Suggestions ===")
    for suggestion in suggestions:
        print(f"[{suggestion['priority'].upper()}] {suggestion['suggestion']}")
        print(f"  Potential savings: ${suggestion.get('potential_savings', 0):.2f}")

    return report


def generate_report(output_dir: str = "reports"):
    """生成综合性能报告"""
    import json

    from ai_report_generator import AIReportGenerator

    print("Generating comprehensive AI performance report...")

    # 收集所有测试结果
    data = {
        "total_tests": 0,
        "passed_tests": 0,
        "total_cost": 0.0,
        "total_tokens": 0,
        "llm_metrics": [],
        "rag_metrics": [],
        "vector_metrics": [],
        "agent_metrics": [],
        "cost_by_model": [],
        "optimization_suggestions": [],
    }

    # 读取各个测试的JSON报告
    for test_type in ["llm", "rag", "agent"]:
        json_file = f"{output_dir}/{test_type}_benchmark.json"
        if os.path.exists(json_file):
            with open(json_file, "r") as f:
                benchmark_data = json.load(f)
                data["total_tests"] += len(benchmark_data.get("benchmarks", []))
                data["total_duration"] = benchmark_data.get("duration", 0)

    # 添加模拟的性能指标
    data["llm_metrics"] = [
        {
            "operation": "short_prompt_inference",
            "model": "gpt-3.5-turbo",
            "mean_time_ms": 150.0,
            "p95_ms": 200.0,
            "p99_ms": 250.0,
            "token_usage": 30,
            "cost_usd": 0.00006,
        },
        {
            "operation": "medium_prompt_inference",
            "model": "gpt-3.5-turbo",
            "mean_time_ms": 300.0,
            "p95_ms": 400.0,
            "p99_ms": 500.0,
            "token_usage": 100,
            "cost_usd": 0.0002,
        },
    ]

    data["rag_metrics"] = [
        {
            "operation": "end_to_end",
            "retrieval_time_ms": 100.0,
            "generation_time_ms": 400.0,
            "total_latency_ms": 500.0,
            "num_docs": 3,
        }
    ]

    data["vector_metrics"] = [
        {
            "operation": "vector_search",
            "vector_dim": 1000,
            "search_time_ms": 50.0,
            "collection_size": 10000,
            "top_k": 5,
        }
    ]

    data["agent_metrics"] = [
        {
            "operation": "parallel_agents",
            "num_agents": 5,
            "execution_mode": "parallel",
            "total_time_ms": 300.0,
            "communication_overhead_ms": 50.0,
        }
    ]

    data["cost_by_model"] = [
        {
            "model": "gpt-3.5-turbo",
            "total_tokens": 3000,
            "input_tokens": 1000,
            "output_tokens": 2000,
            "total_cost": 0.006,
        },
        {
            "model": "gpt-4",
            "total_tokens": 1500,
            "input_tokens": 500,
            "output_tokens": 1000,
            "total_cost": 0.075,
        },
    ]

    data["optimization_suggestions"] = [
        {
            "type": "model_downgrade",
            "priority": "high",
            "suggestion": "Consider downgrading some gpt-4 requests to gpt-3.5-turbo",
            "potential_savings": 0.06,
        },
        {
            "type": "caching",
            "priority": "high",
            "suggestion": "Implement response caching to reduce redundant inference",
            "potential_savings": 0.025,
        },
    ]

    # 生成报告
    generator = AIReportGenerator(output_dir)
    html_file = generator.generate_html_report(data, {"environment": "Local"})
    json_file = generator.generate_json_report(data, {"environment": "Local"})

    print(f"HTML report generated: {html_file}")
    print(f"JSON report generated: {json_file}")


def main():
    """主函数"""

    parser = argparse.ArgumentParser(description="AIOps Agent AI Performance Test Runner")

    parser.add_argument("--all", action="store_true", help="Run all AI performance tests")

    parser.add_argument("--llm", action="store_true", help="Run LLM performance tests")

    parser.add_argument("--rag", action="store_true", help="Run RAG performance tests")

    parser.add_argument("--agent", action="store_true", help="Run agent performance tests")

    parser.add_argument("--cost-report", action="store_true", help="Generate cost report")

    parser.add_argument(
        "--generate-report", action="store_true", help="Generate comprehensive performance report"
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default="tests/performance/ai/reports",
        help="Output directory for reports (default: tests/performance/ai/reports)",
    )

    args = parser.parse_args()

    # 如果没有指定任何测试，默认运行所有测试
    if not any([args.all, args.llm, args.rag, args.agent, args.cost_report, args.generate_report]):
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

    if args.llm:
        returncode = run_llm_tests(args.output_dir)
        sys.exit(returncode)

    if args.rag:
        returncode = run_rag_tests(args.output_dir)
        sys.exit(returncode)

    if args.agent:
        returncode = run_agent_tests(args.output_dir)
        sys.exit(returncode)

    if args.cost_report:
        generate_cost_report(args.output_dir)

    if args.generate_report:
        generate_report(args.output_dir)


if __name__ == "__main__":
    main()
