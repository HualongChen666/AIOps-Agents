#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据库操作覆盖率监控脚本

定期检查数据库相关模块的测试覆盖率，并生成报告。
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def run_coverage_check():
    """运行数据库覆盖率检查并解析 coverage.json"""
    test_files = [
        "tests/core/test_database.py",
        "tests/core/test_database_cache_optimizer.py",
        "tests/core/test_database_connection_optimizer.py",
        "tests/core/test_database_optimization_manager.py",
        "tests/core/test_database_query_optimizer.py",
        "tests/unit/test_database_unit.py",
        "tests/unit/test_database_cache_optimizer_unit.py",
        "tests/unit/test_database_connection_optimizer_unit.py",
        "tests/unit/test_database_optimization_manager_unit.py",
        "tests/unit/test_database_query_optimizer_unit.py",
        "tests/unit/test_database_10_3_unit.py",
    ]

    existing_test_files = [f for f in test_files if Path(f).exists()]

    if not existing_test_files:
        print("错误：没有找到任何测试文件")
        return None

    cmd = [
        "python",
        "-m",
        "pytest",
        *existing_test_files,
        "-q",
        "--timeout=120",
    ]

    print("运行覆盖率检查...")
    print(f"命令: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            cwd="C:\\AIOps_Agent_bak",
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode != 0:
            print(result.stdout)
            print(result.stderr)
            return None

        return parse_coverage_json()

    except subprocess.TimeoutExpired:
        print("错误：覆盖率检查超时")
        return None
    except Exception as e:
        print(f"错误：运行覆盖率检查失败 - {e}")
        return None


def parse_coverage_json():
    """解析 coverage.json 中的数据库模块覆盖率"""
    database_modules = [
        "database.py",
        "database_cache_optimizer.py",
        "database_connection_optimizer.py",
        "database_optimization_manager.py",
        "database_query_optimizer.py",
    ]

    coverage_path = Path("C:\\AIOps_Agent_bak\\coverage.json")
    if not coverage_path.exists():
        print("错误：未生成 coverage.json")
        return None

    data = json.loads(coverage_path.read_text(encoding="utf-8"))
    results = {}
    total_lines = 0
    total_covered = 0

    for module in database_modules:
        file_key = f"core\\{module}"
        info = data["files"].get(file_key)
        if not info:
            continue

        summary = info["summary"]
        total = summary["num_statements"]
        covered = summary["covered_lines"]
        percent = summary["percent_covered"]

        results[f"core/{module}"] = {
            "lines": total,
            "covered": covered,
            "percent": percent,
            "status": "PASS" if percent >= 50 else "FAIL",
        }

        total_lines += total
        total_covered += covered

    overall_percent = (total_covered / total_lines * 100) if total_lines > 0 else 0.0
    results["overall"] = {
        "total_lines": total_lines,
        "total_covered": total_covered,
        "percent": overall_percent,
        "status": "PASS" if overall_percent >= 50 else "FAIL",
    }

    return results


def generate_report(results):
    """生成覆盖率报告"""
    if not results:
        return None

    report = []
    report.append("=" * 80)
    report.append("数据库操作覆盖率报告")
    report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("=" * 80)
    report.append("")

    # 整体覆盖率
    overall = results.get("overall", {})
    report.append(
        f"整体覆盖率: {overall['percent']:.2f}%"
        f" ({overall['total_covered']}/{overall['total_lines']} 行)"
    )
    report.append(f"状态: {overall['status']}")
    report.append("")

    # 各模块覆盖率
    report.append("-" * 80)
    report.append("各模块覆盖率详情:")
    report.append("-" * 80)
    report.append("")

    for module, data in results.items():
        if module == "overall":
            continue

        status_icon = "✓" if data["status"] == "PASS" else "✗"
        report.append(f"{status_icon} {module}")
        report.append(f"  覆盖率: {data['percent']:.2f}% ({data['covered']}/{data['lines']} 行)")
        report.append(f"  状态: {data['status']}")
        report.append("")

    # 低覆盖率模块
    report.append("-" * 80)
    report.append("低覆盖率模块 (< 50%):")
    report.append("-" * 80)
    report.append("")

    low_coverage_modules = []
    for module, data in results.items():
        if module == "overall":
            continue
        if data["percent"] < 50:
            low_coverage_modules.append((module, data))

    if low_coverage_modules:
        for module, data in low_coverage_modules:
            report.append(f"✗ {module}: {data['percent']:.2f}%")
    else:
        report.append("无低覆盖率模块")

    report.append("")
    report.append("=" * 80)

    return "\n".join(report)


def save_report(report):
    """保存报告到文件"""
    if not report:
        return

    report_dir = Path("C:\\AIOps_Agent_bak\\reports")
    report_dir.mkdir(exist_ok=True)

    report_file = report_dir / f"database_coverage_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"报告已保存到: {report_file}")


def main():
    """主函数"""
    print("开始数据库操作覆盖率检查...")
    print()

    # 运行覆盖率检查
    coverage_data = run_coverage_check()

    if not coverage_data:
        print("覆盖率检查失败")
        sys.exit(1)

    # 分析覆盖率
    results = coverage_data

    if not results:
        print("覆盖率分析失败")
        sys.exit(1)

    # 生成报告
    report = generate_report(results)

    if report:
        print(report)
        print()
        save_report(report)

    # 检查整体覆盖率是否达标
    overall = results.get("overall", {})
    if overall["percent"] < 50:
        print(f"错误：整体覆盖率 {overall['percent']:.2f}% 未达到目标 50%")
        sys.exit(1)
    else:
        print(f"成功：整体覆盖率 {overall['percent']:.2f}% 达到目标 50%")
        sys.exit(0)


if __name__ == "__main__":
    main()
