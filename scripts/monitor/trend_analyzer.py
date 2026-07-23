# -*- coding: utf-8 -*-
"""
技术债务趋势分析模块

从数据库中读取历史扫描结果，分析债务变化趋势。
"""

import json
import logging
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TrendAnalyzer:
    """债务趋势分析器"""

    def __init__(self, db_path: Path):
        """
        初始化分析器

        Args:
            db_path: 数据库路径
        """
        self.db_path = db_path

    def get_scan_history(self, scan_type: str, days: int = 30) -> List[Dict[str, Any]]:
        """
        获取指定类型的扫描历史

        Args:
            scan_type: 扫描类型（bandit, flake8, mypy, safety）
            days: 获取最近多少天的数据

        Returns:
            扫描历史列表
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

        cursor.execute(
            """
            SELECT timestamp, result_json
            FROM scan_results
            WHERE scan_type = ? AND timestamp >= ?
            ORDER BY timestamp DESC
        """,
            (scan_type, cutoff_date),
        )

        results = []
        for row in cursor.fetchall():
            timestamp, result_json = row
            results.append({"timestamp": timestamp, "data": json.loads(result_json)})

        conn.close()
        return results

    def analyze_bandit_trend(self, days: int = 30) -> Dict[str, Any]:
        """
        分析bandit扫描趋势

        Args:
            days: 分析最近多少天

        Returns:
            趋势分析结果
        """
        history = self.get_scan_history("bandit", days)

        if not history:
            return {"error": "No data available"}

        trend = {
            "scan_type": "bandit",
            "period_days": days,
            "data_points": len(history),
            "latest": history[0]["data"],
            "oldest": history[-1]["data"],
            "trend": {},
        }

        # 计算趋势
        latest_high = trend["latest"].get("severity_breakdown", {}).get("HIGH", 0)
        oldest_high = trend["oldest"].get("severity_breakdown", {}).get("HIGH", 0)

        latest_total = trend["latest"].get("total_issues", 0)
        oldest_total = trend["oldest"].get("total_issues", 0)

        trend["trend"]["high_severity_change"] = latest_high - oldest_high
        trend["trend"]["total_issues_change"] = latest_total - oldest_total
        trend["trend"]["trend_direction"] = (
            "improving"
            if latest_total < oldest_total
            else "worsening" if latest_total > oldest_total else "stable"
        )

        return trend

    def analyze_flake8_trend(self, days: int = 30) -> Dict[str, Any]:
        """
        分析flake8扫描趋势

        Args:
            days: 分析最近多少天

        Returns:
            趋势分析结果
        """
        history = self.get_scan_history("flake8", days)

        if not history:
            return {"error": "No data available"}

        trend = {
            "scan_type": "flake8",
            "period_days": days,
            "data_points": len(history),
            "latest": history[0]["data"],
            "oldest": history[-1]["data"],
            "trend": {},
        }

        latest_errors = trend["latest"].get("error_count", 0)
        oldest_errors = trend["oldest"].get("error_count", 0)

        trend["trend"]["error_count_change"] = latest_errors - oldest_errors
        trend["trend"]["trend_direction"] = (
            "improving"
            if latest_errors < oldest_errors
            else "worsening" if latest_errors > oldest_errors else "stable"
        )

        return trend

    def analyze_safety_trend(self, days: int = 30) -> Dict[str, Any]:
        """
        分析safety扫描趋势

        Args:
            days: 分析最近多少天

        Returns:
            趋势分析结果
        """
        history = self.get_scan_history("safety", days)

        if not history:
            return {"error": "No data available"}

        trend = {
            "scan_type": "safety",
            "period_days": days,
            "data_points": len(history),
            "latest": history[0]["data"],
            "oldest": history[-1]["data"],
            "trend": {},
        }

        latest_vulns = trend["latest"].get("vulnerability_count", 0)
        oldest_vulns = trend["oldest"].get("vulnerability_count", 0)

        trend["trend"]["vulnerability_change"] = latest_vulns - oldest_vulns
        trend["trend"]["trend_direction"] = (
            "improving"
            if latest_vulns < oldest_vulns
            else "worsening" if latest_vulns > oldest_vulns else "stable"
        )

        return trend

    def get_alert_history(self, days: int = 30) -> List[Dict[str, Any]]:
        """
        获取预警历史

        Args:
            days: 获取最近多少天的预警

        Returns:
            预警历史列表
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

        cursor.execute(
            """
            SELECT timestamp, level, message, details
            FROM alerts
            WHERE timestamp >= ?
            ORDER BY timestamp DESC
        """,
            (cutoff_date,),
        )

        results = []
        for row in cursor.fetchall():
            timestamp, level, message, details = row
            results.append(
                {"timestamp": timestamp, "level": level, "message": message, "details": details}
            )

        conn.close()
        return results

    def generate_trend_report(self, days: int = 30) -> str:
        """
        生成趋势分析报告

        Args:
            days: 分析最近多少天

        Returns:
            Markdown格式报告
        """
        report_lines = [
            "# 技术债务趋势分析报告",
            f"\n**分析周期**: 最近{days}天",
            f"**生成时间**: {datetime.now().isoformat()}",
            "\n## 各类扫描趋势",
        ]

        # Bandit趋势
        bandit_trend = self.analyze_bandit_trend(days)
        if "error" not in bandit_trend:
            report_lines.append("\n### Bandit安全扫描")
            report_lines.append(f"- 数据点数: {bandit_trend['data_points']}")
            report_lines.append(
                "- 最新High严重度: "
                f"{bandit_trend['latest'].get('severity_breakdown', {}).get('HIGH', 0)}"
            )
            report_lines.append(
                f"- High严重度变化: {bandit_trend['trend']['high_severity_change']:+d}"
            )
            report_lines.append(
                f"- 总问题数变化: {bandit_trend['trend']['total_issues_change']:+d}"
            )
            report_lines.append(f"- 趋势方向: {bandit_trend['trend']['trend_direction']}")

        # Flake8趋势
        flake8_trend = self.analyze_flake8_trend(days)
        if "error" not in flake8_trend:
            report_lines.append("\n### Flake8代码检查")
            report_lines.append(f"- 数据点数: {flake8_trend['data_points']}")
            report_lines.append(f"- 最新错误数: {flake8_trend['latest'].get('error_count', 0)}")
            report_lines.append(f"- 错误数变化: {flake8_trend['trend']['error_count_change']:+d}")
            report_lines.append(f"- 趋势方向: {flake8_trend['trend']['trend_direction']}")

        # Safety趋势
        safety_trend = self.analyze_safety_trend(days)
        if "error" not in safety_trend:
            report_lines.append("\n### Safety依赖扫描")
            report_lines.append(f"- 数据点数: {safety_trend['data_points']}")
            report_lines.append(
                f"- 最新漏洞数: {safety_trend['latest'].get('vulnerability_count', 0)}"
            )
            report_lines.append(f"- 漏洞数变化: {safety_trend['trend']['vulnerability_change']:+d}")
            report_lines.append(f"- 趋势方向: {safety_trend['trend']['trend_direction']}")

        # 预警历史
        alerts = self.get_alert_history(days)
        report_lines.append("\n## 预警历史")
        if alerts:
            report_lines.append(f"\n最近{days}天共{len(alerts)}个预警")
            for alert in alerts[:10]:  # 只显示前10个
                report_lines.append(f"\n### {alert['timestamp']}")
                report_lines.append(f"- 级别: {alert['level']}")
                report_lines.append(f"- 消息: {alert['message']}")
        else:
            report_lines.append("\n✅ 无预警记录")

        return "\n".join(report_lines)


def main():
    """主函数"""
    # 在 Windows cp1252 控制台输出中文前，确保 stdout 使用 UTF-8
    if sys.stdout:
        reconfigure = getattr(sys.stdout, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8")

    project_root = Path(__file__).parent.parent.parent
    db_path = project_root / "data" / "tech_debt_monitor.db"

    analyzer = TrendAnalyzer(db_path)
    report = analyzer.generate_trend_report(days=30)

    # 保存报告
    report_dir = project_root / "Tech_questions"
    report_dir.mkdir(exist_ok=True)
    report_path = (
        report_dir / f'tech_debt_trend_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.md'
    )

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"Trend report saved to {report_path}")
    print(report)


if __name__ == "__main__":
    main()
