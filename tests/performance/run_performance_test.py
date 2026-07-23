#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能测试运行脚本
支持命令行参数配置测试场景
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def run_locust_test(
    scenario: str,
    users: int,
    spawn_rate: int,
    duration: int,
    host: str,
    output_dir: str = "reports",
):
    """
    运行Locust性能测试

    Args:
        scenario: 测试场景 (staircase, spike, wave, constant, custom)
        users: 并发用户数
        spawn_rate: 用户生成速率
        duration: 测试时长(秒)
        host: 目标主机
        output_dir: 输出目录
    """
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)

    # 构建Locust命令
    cmd = [
        "locust",
        "-f",
        "locustfile.py",
        "--headless",
        "--host",
        host,
        "--html",
        f"{output_dir}/{scenario}_report.html",
        "--json",
        f"{output_dir}/{scenario}_report.json",
        "--logfile",
        f"{output_dir}/{scenario}.log",
        "--loglevel",
        "INFO",
    ]

    # 根据场景选择负载形状
    shape_classes = {
        "staircase": "locust_config.py::StaircaseLoadShape",
        "spike": "locust_config.py::SpikeLoadShape",
        "wave": "locust_config.py::WaveLoadShape",
        "constant": "locust_config.py::ConstantLoadShape",
        "custom": "locust_config.py::CustomLoadShape",
    }

    if scenario in shape_classes:
        cmd.extend(["--shape", shape_classes[scenario]])
    else:
        # 如果不是预定义场景，使用用户指定的参数
        cmd.extend(
            ["--users", str(users), "--spawn-rate", str(spawn_rate), "--run-time", str(duration)]
        )

    print(f"Running performance test with scenario: {scenario}")
    print(f"Command: {' '.join(cmd)}")

    # 运行测试
    result = subprocess.run(cmd, cwd="tests/performance")

    if result.returncode != 0:
        print(f"Performance test failed with return code: {result.returncode}")
        sys.exit(1)

    print("Performance test completed successfully")
    print(f"Reports saved to: {output_dir}")


def generate_reports(output_dir: str = "reports"):
    """
    生成性能测试报告

    Args:
        output_dir: 输出目录
    """
    import json

    from report_generator import (
        HTMLReportGenerator,
        PerformanceRegressionDetector,
    )

    # 查找最新的JSON报告
    json_files = list(Path(output_dir).glob("*_report.json"))
    if not json_files:
        print("No JSON report found")
        return

    latest_json = max(json_files, key=lambda p: p.stat().st_mtime)

    with open(latest_json, "r") as f:
        data = json.load(f)

    # 生成HTML报告
    html_gen = HTMLReportGenerator(output_dir)
    html_file = html_gen.generate(
        data,
        {
            "environment": "Local",
            "scenario": latest_json.stem.replace("_report", ""),
            "users": "N/A",
        },
    )

    print(f"HTML report generated: {html_file}")

    # 性能回归检测
    detector = PerformanceRegressionDetector()
    regressions = detector.detect_regression(data)
    alert = detector.generate_alert(regressions)

    print("\n" + "=" * 50)
    print("Performance Regression Detection")
    print("=" * 50)
    print(alert)

    if regressions:
        print("\n⚠️  Performance regression detected!")
        sys.exit(1)
    else:
        print("\n✅ No performance regression detected")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="AIOps Agent Performance Test Runner")

    parser.add_argument(
        "--scenario",
        type=str,
        choices=["staircase", "spike", "wave", "constant", "custom"],
        default="staircase",
        help="Test scenario (default: staircase)",
    )

    parser.add_argument(
        "--users", type=int, default=1000, help="Number of concurrent users (default: 1000)"
    )

    parser.add_argument(
        "--spawn-rate", type=int, default=100, help="User spawn rate (default: 100)"
    )

    parser.add_argument(
        "--duration", type=int, default=300, help="Test duration in seconds (default: 300)"
    )

    parser.add_argument(
        "--host",
        type=str,
        default="http://localhost:8000",
        help="Target host (default: http://localhost:8000)",
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default="tests/performance/reports",
        help="Output directory (default: tests/performance/reports)",
    )

    parser.add_argument(
        "--generate-reports-only",
        action="store_true",
        help="Only generate reports from existing test results",
    )

    args = parser.parse_args()

    if args.generate_reports_only:
        generate_reports(args.output_dir)
    else:
        run_locust_test(
            scenario=args.scenario,
            users=args.users,
            spawn_rate=args.spawn_rate,
            duration=args.duration,
            host=args.host,
            output_dir=args.output_dir,
        )
        generate_reports(args.output_dir)


if __name__ == "__main__":
    main()
