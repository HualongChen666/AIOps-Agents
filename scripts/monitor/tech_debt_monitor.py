# -*- coding: utf-8 -*-
"""
技术债务监控脚本

定期扫描项目中的技术债务，包括：
- 安全漏洞（bandit, safety）
- 代码质量（flake8, mypy）
- 测试覆盖率（pytest-cov）
- 依赖状态（pip outdated）

结果存储到SQLite数据库，支持趋势分析和预警。
"""

import json
import logging
import os
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class TechDebtMonitor:
    """技术债务监控器"""

    def __init__(self, project_root: Path, db_path: Path):
        """
        初始化监控器

        Args:
            project_root: 项目根目录
            db_path: 数据库路径
        """
        self.project_root = project_root
        self.db_path = db_path
        self.timestamp = datetime.now()
        self.results: Dict[str, Any] = {"timestamp": self.timestamp.isoformat(), "scans": {}}

    def init_database(self):
        """初始化数据库表结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 创建扫描结果表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scan_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                scan_type TEXT NOT NULL,
                result_json TEXT NOT NULL,
                UNIQUE(timestamp, scan_type)
            )
        """)

        # 创建预警记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                level TEXT NOT NULL,
                message TEXT NOT NULL,
                details TEXT
            )
        """)

        conn.commit()
        conn.close()
        logger.info("Database initialized")

    def run_bandit_scan(self) -> Dict[str, Any]:
        """
        运行bandit安全扫描

        Returns:
            扫描结果字典
        """
        logger.info("Running bandit scan...")
        try:
            # Use text format instead of JSON for better compatibility
            cmd = [
                sys.executable,
                "-m",
                "bandit",
                "-r",
                "api",
                "core",
                "main.py",
                "-f",
                "txt",
                "--exclude",
                "venv",
            ]
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=120,
            )

            # Parse text output
            output = result.stdout if result.stdout else result.stderr

            if output.strip():
                # Count actual severity annotations in issue details
                high_count = output.count("Severity: High")
                medium_count = output.count("Severity: Medium")
                low_count = output.count("Severity: Low")
                total_issues = output.count(">> Issue:")

                return {
                    "success": True,
                    "total_issues": total_issues,
                    "severity_breakdown": {
                        "HIGH": high_count,
                        "MEDIUM": medium_count,
                        "LOW": low_count,
                    },
                    "issues": [],  # Text format doesn't provide detailed issue list
                    "format": "text",
                }
            else:
                return {
                    "success": True,
                    "total_issues": 0,
                    "severity_breakdown": {"HIGH": 0, "MEDIUM": 0, "LOW": 0},
                    "issues": [],
                }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Bandit scan timed out"}
        except Exception as e:
            logger.error(f"Bandit scan failed: {e}")
            return {"success": False, "error": str(e)}

    def run_flake8_scan(self) -> Dict[str, Any]:
        """
        运行flake8代码检查

        Returns:
            扫描结果字典
        """
        logger.info("Running flake8 scan...")
        try:
            cmd = [
                sys.executable,
                "-m",
                "flake8",
                "api",
                "core",
                "main.py",
                "--max-line-length=100",
                "--statistics",
            ]
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=120,
            )

            error_count = len(result.stdout.strip().split("\n")) if result.stdout.strip() else 0

            return {"success": True, "error_count": error_count, "has_errors": error_count > 0}
        except Exception as e:
            logger.error(f"Flake8 scan failed: {e}")
            return {"success": False, "error": str(e)}

    def run_mypy_scan(self) -> Dict[str, Any]:
        """
        运行mypy类型检查

        Returns:
            扫描结果字典
        """
        logger.info("Running mypy scan...")
        try:
            cmd = [sys.executable, "-m", "mypy", "api", "core", "main.py"]
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=120,
            )

            error_count = result.stdout.count(": error:") if result.stdout else 0

            return {"success": True, "error_count": error_count, "has_errors": error_count > 0}
        except Exception as e:
            logger.error(f"Mypy scan failed: {e}")
            return {"success": False, "error": str(e)}

    def run_safety_scan(self) -> Dict[str, Any]:
        """
        运行safety依赖漏洞扫描

        Returns:
            扫描结果字典
        """
        logger.info("Running safety scan...")
        try:
            # Use text format instead of JSON for better compatibility
            cmd = [sys.executable, "-m", "safety", "check"]
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=300,
            )

            # Parse text output
            output = result.stdout if result.stdout else result.stderr

            if output.strip():
                # Check if there are vulnerabilities
                if (
                    "No known security vulnerabilities" in output
                    or "No vulnerabilities found" in output
                ):
                    return {
                        "success": True,
                        "vulnerability_count": 0,
                        "vulnerabilities": [],
                        "format": "text",
                    }
                else:
                    # Count actual vulnerability report lines
                    vuln_count = output.count("Vulnerability found in")
                    return {
                        "success": True,
                        "vulnerability_count": vuln_count,
                        "vulnerabilities": [],
                        "format": "text",
                    }
            else:
                return {"success": True, "vulnerability_count": 0, "vulnerabilities": []}
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Safety scan timed out"}
        except Exception as e:
            logging.exception("Unexpected exception: %s", e)
            logger.error("Safety scan failed")
            return {"success": False, "error": "Unknown error"}

    def run_all_scans(self) -> Dict[str, Any]:
        """运行所有扫描"""
        logger.info("Starting all scans...")

        self.results["scans"]["bandit"] = self.run_bandit_scan()
        self.results["scans"]["flake8"] = self.run_flake8_scan()
        self.results["scans"]["mypy"] = self.run_mypy_scan()
        self.results["scans"]["safety"] = self.run_safety_scan()

        logger.info("All scans completed")
        return self.results

    def save_results(self):
        """保存扫描结果到数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for scan_type, scan_result in self.results["scans"].items():
            cursor.execute(
                """
                INSERT OR REPLACE INTO scan_results
                (timestamp, scan_type, result_json)
                VALUES (?, ?, ?)
            """,
                (self.results["timestamp"], scan_type, json.dumps(scan_result)),
            )

        conn.commit()
        conn.close()
        logger.info("Results saved to database")

    def check_alerts(self) -> List[Dict[str, Any]]:
        """
        检查预警条件

        Returns:
            预警列表
        """
        alerts = []

        # 检查bandit高危漏洞
        bandit_result = self.results["scans"].get("bandit", {})
        if bandit_result.get("success"):
            high_count = bandit_result.get("severity_breakdown", {}).get("HIGH", 0)
            if high_count > 0:
                alerts.append(
                    {
                        "level": "P0",
                        "message": f"发现{high_count}个High严重度安全漏洞",
                        "details": json.dumps(bandit_result),
                    }
                )

        # 检查flake8错误
        flake8_result = self.results["scans"].get("flake8", {})
        if flake8_result.get("success") and flake8_result.get("has_errors"):
            alerts.append(
                {
                    "level": "P1",
                    "message": f'发现{flake8_result.get("error_count")}个flake8错误',
                    "details": json.dumps(flake8_result),
                }
            )

        # 检查safety漏洞
        safety_result = self.results["scans"].get("safety", {})
        if safety_result.get("success"):
            vuln_count = safety_result.get("vulnerability_count", 0)
            if vuln_count > 0:
                alerts.append(
                    {
                        "level": "P1",
                        "message": f"发现{vuln_count}个依赖漏洞",
                        "details": json.dumps(safety_result),
                    }
                )

        # 保存预警到数据库
        if alerts:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            for alert in alerts:
                cursor.execute(
                    """
                    INSERT INTO alerts (timestamp, level, message, details)
                    VALUES (?, ?, ?, ?)
                """,
                    (
                        self.results["timestamp"],
                        alert["level"],
                        alert["message"],
                        alert.get("details"),
                    ),
                )
            conn.commit()
            conn.close()

        return alerts

    def generate_report(self) -> str:
        """
        生成监控报告

        Returns:
            Markdown格式报告
        """
        report_lines = [
            "# 技术债务监控报告",
            f"\n**扫描时间**: {self.results['timestamp']}",
            "\n## 扫描结果概览",
        ]

        # 添加各扫描结果
        for scan_type, result in self.results["scans"].items():
            report_lines.append(f"\n### {scan_type.upper()} 扫描")
            if result.get("success"):
                if scan_type == "bandit":
                    total = result.get("total_issues", 0)
                    severity = result.get("severity_breakdown", {})
                    report_lines.append(f"- 总问题数: {total}")
                    report_lines.append(f"- HIGH: {severity.get('HIGH', 0)}")
                    report_lines.append(f"- MEDIUM: {severity.get('MEDIUM', 0)}")
                    report_lines.append(f"- LOW: {severity.get('LOW', 0)}")
                elif scan_type == "flake8":
                    report_lines.append(f"- 错误数: {result.get('error_count', 0)}")
                    report_lines.append(
                        f"- 状态: {'有错误' if result.get('has_errors') else '无错误'}"
                    )
                elif scan_type == "mypy":
                    report_lines.append(f"- 错误数: {result.get('error_count', 0)}")
                    report_lines.append(
                        f"- 状态: {'有错误' if result.get('has_errors') else '无错误'}"
                    )
                elif scan_type == "safety":
                    report_lines.append(f"- 漏洞数: {result.get('vulnerability_count', 0)}")
            else:
                report_lines.append(f"- 扫描失败: {result.get('error', 'Unknown error')}")

        # 添加预警信息
        alerts = self.check_alerts()
        if alerts:
            report_lines.append("\n## 预警信息")
            for alert in alerts:
                report_lines.append(f"\n### {alert['level']} 预警")
                report_lines.append(f"- {alert['message']}")
        else:
            report_lines.append("\n## 预警信息")
            report_lines.append("✅ 无预警")

        return "\n".join(report_lines)

    def run(self) -> Dict[str, Any]:
        """
        运行完整监控流程

        Returns:
            监控结果
        """
        logger.info("Starting technical debt monitoring...")

        # 初始化数据库
        self.init_database()

        # 运行所有扫描
        self.run_all_scans()

        # 保存结果
        self.save_results()

        # 检查预警
        alerts = self.check_alerts()
        if alerts:
            logger.warning(f"Generated {len(alerts)} alerts")

        # 生成报告
        report = self.generate_report()

        # 保存报告
        report_dir = self.project_root / "Tech_questions"
        report_dir.mkdir(exist_ok=True)
        report_path = report_dir / f'tech_debt_report_{self.timestamp.strftime("%Y%m%d_%H%M%S")}.md'
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)

        logger.info(f"Report saved to {report_path}")

        return {"results": self.results, "alerts": alerts, "report_path": str(report_path)}


def main():
    """主函数"""
    # 在 Windows cp1252 控制台输出中文前，确保 stdout 使用 UTF-8
    if sys.stdout:
        reconfigure = getattr(sys.stdout, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8")

    # 子进程 Python 默认使用 UTF-8，避免 bandit/safety 等读取含中文的文件时解码失败
    os.environ.setdefault("PYTHONUTF8", "1")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

    project_root = Path(__file__).parent.parent.parent
    db_path = project_root / "data" / "tech_debt_monitor.db"

    # 确保数据目录存在
    db_path.parent.mkdir(exist_ok=True)

    monitor = TechDebtMonitor(project_root, db_path)
    results = monitor.run()

    # 输出摘要
    print("\n" + "=" * 50)
    print("技术债务监控完成")
    print("=" * 50)
    print(f"扫描时间: {results['results']['timestamp']}")
    print(f"预警数量: {len(results['alerts'])}")
    print(f"报告路径: {results['report_path']}")
    print("=" * 50)

    if results["alerts"]:
        print("\n预警信息:")
        for alert in results["alerts"]:
            print(f"  [{alert['level']}] {alert['message']}")


if __name__ == "__main__":
    main()