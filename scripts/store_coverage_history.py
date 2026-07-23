#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
覆盖率历史存储脚本
用于存储和跟踪覆盖率历史数据，支持趋势分析
"""

import json
import os
from datetime import datetime
from typing import Any, Dict


def load_coverage_history(history_file: str = "coverage_history.json") -> Dict[str, Any]:
    """加载覆盖率历史数据"""
    if not os.path.exists(history_file):
        return {"history": []}

    with open(history_file, "r", encoding="utf-8") as f:
        return json.load(f)


def save_coverage_history(history: Dict[str, Any], history_file: str = "coverage_history.json"):
    """保存覆盖率历史数据"""
    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def parse_coverage_json(coverage_file: str = "coverage.json") -> Dict[str, float]:
    """解析coverage.json文件，提取覆盖率数据"""
    if not os.path.exists(coverage_file):
        return {}

    with open(coverage_file, "r", encoding="utf-8") as f:
        coverage_data = json.load(f)

    # 提取总体覆盖率
    totals = coverage_data.get("totals", {})
    return {
        "line_coverage": totals.get("percent_covered", 0.0),
        "branch_coverage": totals.get("percent_covered_display", 0.0),
        "num_statements": totals.get("num_statements", 0),
        "num_missing": totals.get("num_missing", 0),
        "num_branches": totals.get("num_branches", 0),
        "num_partial_branches": totals.get("num_partial_branches", 0),
    }


def add_coverage_entry(
    history: Dict[str, Any],
    coverage_data: Dict[str, float],
    commit_hash: str = None,
    branch: str = "main",
) -> Dict[str, Any]:
    """添加新的覆盖率条目到历史记录"""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "commit": commit_hash,
        "branch": branch,
        "coverage": coverage_data,
    }

    history["history"].append(entry)

    # 保持历史记录不超过100条
    if len(history["history"]) > 100:
        history["history"] = history["history"][-100:]

    return history


def calculate_coverage_trend(history: Dict[str, Any]) -> Dict[str, Any]:
    """计算覆盖率趋势"""
    if len(history["history"]) < 2:
        return {"trend": "insufficient_data"}

    recent = history["history"][-5:]  # 最近5次记录
    line_coverages = [entry["coverage"].get("line_coverage", 0) for entry in recent]

    if line_coverages[-1] > line_coverages[0]:
        trend = "increasing"
    elif line_coverages[-1] < line_coverages[0]:
        trend = "decreasing"
    else:
        trend = "stable"

    return {
        "trend": trend,
        "current": line_coverages[-1],
        "previous": line_coverages[0],
        "change": line_coverages[-1] - line_coverages[0],
        "average": sum(line_coverages) / len(line_coverages),
    }


def generate_coverage_report(history: Dict[str, Any]) -> str:
    """生成覆盖率报告"""
    if not history["history"]:
        return "No coverage history available."

    latest = history["history"][-1]
    trend = calculate_coverage_trend(history)

    report = f"""
Coverage Report
{'=' * 50}
Latest Coverage: {latest['coverage'].get('line_coverage', 0):.2f}%
Branch Coverage: {latest['coverage'].get('branch_coverage', 0):.2f}%
Timestamp: {latest['timestamp']}
Commit: {latest.get('commit', 'N/A')}
Branch: {latest.get('branch', 'N/A')}

Trend Analysis
{'=' * 50}
Trend: {trend['trend']}
Current: {trend.get('current', 0):.2f}%
Previous: {trend.get('previous', 0):.2f}%
Change: {trend.get('change', 0):+.2f}%
Average (last 5): {trend.get('average', 0):.2f}%

History (last 10 entries)
{'=' * 50}
"""

    for entry in history["history"][-10:]:
        report += (
            f"{entry['timestamp'][:19]} - {entry['coverage'].get('line_coverage', 0):.2f}%"
            f" ({entry.get('commit', 'N/A')[:8]})\n"
        )

    return report


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="Store and analyze coverage history")
    parser.add_argument("--coverage-file", default="coverage.json", help="Coverage JSON file path")
    parser.add_argument(
        "--history-file", default="coverage_history.json", help="History JSON file path"
    )
    parser.add_argument("--commit", help="Git commit hash")
    parser.add_argument("--branch", default="main", help="Git branch name")
    parser.add_argument("--report", action="store_true", help="Generate coverage report")

    args = parser.parse_args()

    # 加载历史数据
    history = load_coverage_history(args.history_file)

    # 解析覆盖率数据
    coverage_data = parse_coverage_json(args.coverage_file)

    if coverage_data:
        # 添加新的覆盖率条目
        history = add_coverage_entry(history, coverage_data, args.commit, args.branch)
        save_coverage_history(history, args.history_file)
        print(f"Coverage data saved to {args.history_file}")

    # 生成报告
    if args.report:
        report = generate_coverage_report(history)
        print(report)

        # 保存报告到文件
        report_file = "coverage_report.txt"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"Report saved to {report_file}")


if __name__ == "__main__":
    main()
