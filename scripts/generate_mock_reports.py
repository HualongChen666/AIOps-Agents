#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
自动化Mock报告生成脚本
用于CI/CD集成和本地开发
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.mock_manager import (  # noqa: E402
    MockConfigs,
    MockConfigValidator,
    MockCoverageReporter,
    get_mock_manager,
    get_mock_monitor,
    get_smart_manager,
)


class MockReportGenerator:
    """Mock报告生成器"""

    def __init__(self, output_dir: str = "reports"):
        """
        初始化报告生成器

        Args:
            output_dir: 报告输出目录
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 初始化组件
        self.monitor = get_mock_monitor()
        self.manager = get_mock_manager()
        self.smart_manager = get_smart_manager()
        self.validator = MockConfigValidator()

    def generate_all_reports(self) -> dict:
        """生成所有报告"""
        print("Generating mock reports...")

        results = {"timestamp": datetime.now().isoformat(), "reports": {}}

        # 1. 覆盖率报告
        try:
            coverage_results = self.generate_coverage_reports()
            results["reports"]["coverage"] = coverage_results
            print("Coverage reports generated successfully")
        except Exception as e:
            print(f"Failed to generate coverage reports: {e}")
            results["reports"]["coverage"] = {"error": str(e)}

        # 2. 智能分析报告
        try:
            smart_results = self.generate_smart_analysis_report()
            results["reports"]["smart_analysis"] = smart_results
            print("Smart analysis report generated successfully")
        except Exception as e:
            print(f"Failed to generate smart analysis report: {e}")
            results["reports"]["smart_analysis"] = {"error": str(e)}

        # 3. 配置验证报告
        try:
            validation_results = self.generate_validation_report()
            results["reports"]["validation"] = validation_results
            print("Validation report generated successfully")
        except Exception as e:
            print(f"Failed to generate validation report: {e}")
            results["reports"]["validation"] = {"error": str(e)}

        # 4. 使用统计报告
        try:
            usage_results = self.generate_usage_report()
            results["reports"]["usage"] = usage_results
            print("Usage report generated successfully")
        except Exception as e:
            print(f"Failed to generate usage report: {e}")
            results["reports"]["usage"] = {"error": str(e)}

        # 5. 保存综合报告
        self.save_comprehensive_report(results)

        print(f"\nAll reports generated successfully in: {self.output_dir}")
        return results

    def generate_coverage_reports(self) -> dict:
        """生成覆盖率报告"""
        reporter = MockCoverageReporter(self.monitor)

        # 获取所有预定义配置
        registered_mocks = self._get_all_registered_mocks()

        # 生成不同格式的报告
        formats = ["text", "json", "html"]
        results = {}

        for format_type in formats:
            try:
                report = reporter.generate_coverage_report(registered_mocks, format_type)

                # 保存报告
                filename = (
                    f"mock_coverage_{format_type}.{format_type if format_type != 'text' else 'txt'}"
                )
                filepath = self.output_dir / filename

                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(report)

                results[format_type] = {"file": str(filepath), "status": "success"}

            except Exception as e:
                results[format_type] = {"file": None, "status": "error", "error": str(e)}

        return results

    def generate_smart_analysis_report(self) -> dict:
        """生成智能分析报告"""
        try:
            report = self.smart_manager.generate_smart_report()

            filepath = self.output_dir / "smart_mock_analysis.txt"
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(report)

            # 生成JSON格式的分析数据
            analysis_data = {
                "usage_patterns": self.smart_manager.analyze_usage_patterns(),
                "anomalies": self.smart_manager.detect_anomalies(),
                "optimization_suggestions": self.smart_manager.generate_optimization_suggestions(),
                "performance_metrics": self.smart_manager.performance_monitoring(),
                "auto_optimization": self.smart_manager.auto_optimize_config(),
            }

            json_filepath = self.output_dir / "smart_mock_analysis.json"
            with open(json_filepath, "w", encoding="utf-8") as f:
                json.dump(analysis_data, f, indent=2)

            return {
                "text_report": str(filepath),
                "json_data": str(json_filepath),
                "status": "success",
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}

    def generate_validation_report(self) -> dict:
        """生成配置验证报告"""
        try:
            # 验证所有预定义配置
            config_methods = self._get_config_method_names()

            validation_results = {}
            all_valid = True

            for method_name in config_methods:
                method = getattr(MockConfigs, method_name)
                config = method()
                service_name = method_name.replace("get_", "").replace("_config", "")

                is_valid = self.validator.validate_config(service_name, config)
                validation_results[service_name] = {
                    "valid": is_valid,
                    "errors": self.validator.validation_errors.copy(),
                    "warnings": self.validator.validation_warnings.copy(),
                }

                if not is_valid:
                    all_valid = False

            # 生成报告
            report_lines = [
                "Mock Configuration Validation Report",
                "=" * 50,
                f"Total configs: {len(config_methods)}",
                f"Valid configs: {sum(1 for r in validation_results.values() if r['valid'])}",
                f"Invalid configs: {sum(1 for r in validation_results.values() if not r['valid'])}",
                "",
                "Detailed Results:",
            ]

            for service_name, result in validation_results.items():
                status = "PASS" if result["valid"] else "FAIL"
                report_lines.append(f"  {status} {service_name}")

                if result["errors"]:
                    for error in result["errors"]:
                        report_lines.append(f"    ERROR: {error}")

                if result["warnings"]:
                    for warning in result["warnings"]:
                        report_lines.append(f"    WARNING: {warning}")

            report_text = "\n".join(report_lines)

            filepath = self.output_dir / "mock_validation_report.txt"
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(report_text)

            # 保存JSON格式的验证结果
            json_filepath = self.output_dir / "mock_validation_report.json"
            with open(json_filepath, "w", encoding="utf-8") as f:
                json.dump(validation_results, f, indent=2)

            return {
                "text_report": str(filepath),
                "json_data": str(json_filepath),
                "all_valid": all_valid,
                "status": "success",
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}

    def generate_usage_report(self) -> dict:
        """生成使用统计报告"""
        try:
            stats = self.monitor.get_mock_stats()
            history = self.monitor.get_test_history()

            report_lines = [
                "Mock Usage Statistics Report",
                "=" * 50,
                f"Session Duration: {
                    stats['session_duration']:.2f}s",
                f"Total Mocks Used: {
                    stats['total_mocks_used']}",
                f"Total Calls: {
                    stats['total_calls']}",
                f"Most Used Mock: {
                    stats['most_used_mock'] or 'None'} ({
                        stats['most_used_mock_calls']} calls)",
                "",
                "Mock Details:",
            ]

            for mock_name, mock_data in stats["mock_details"].items():
                report_lines.append(f"  {mock_name}:")
                report_lines.append(f"    Total Calls: {mock_data['total_calls']}")
                report_lines.append(f"    Methods: {len(mock_data['methods'])}")

                for method_name, method_data in mock_data["methods"].items():
                    report_lines.append(f"      {method_name}: {method_data['call_count']} calls")

            if history:
                report_lines.append("")
                report_lines.append("Test History:")
                for i, test in enumerate(history, 1):
                    report_lines.append(f"  {i}. {test['test_name']}: {test['mocks_used']} mocks")

            report_text = "\n".join(report_lines)

            filepath = self.output_dir / "mock_usage_report.txt"
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(report_text)

            # 保存JSON格式的统计数据
            json_data = {
                "statistics": stats,
                "test_history": history,
                "timestamp": datetime.now().isoformat(),
            }

            json_filepath = self.output_dir / "mock_usage_report.json"
            with open(json_filepath, "w", encoding="utf-8") as f:
                json.dump(json_data, f, indent=2)

            return {
                "text_report": str(filepath),
                "json_data": str(json_filepath),
                "status": "success",
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}

    def save_comprehensive_report(self, results: dict):
        """保存综合报告"""
        filepath = self.output_dir / "comprehensive_mock_report.json"

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)

        print(f"Comprehensive report saved to: {filepath}")

    def _get_all_registered_mocks(self) -> dict:
        """获取所有注册的mock配置"""
        registered_mocks = {}
        config_methods = self._get_config_method_names()

        for method_name in config_methods:
            method = getattr(MockConfigs, method_name)
            config = method()
            service_name = method_name.replace("get_", "").replace("_config", "")
            registered_mocks[service_name] = config

        return registered_mocks

    def _get_config_method_names(self) -> list:
        """获取配置方法名称列表"""
        return [
            "get_ai_analyze_config",
            "get_alert_service_config",
            "get_health_check_config",
            "get_database_config",
            "get_cache_config",
            "get_auth_config",
            "get_workflow_service_config",
            "get_topology_service_config",
            "get_audit_service_config",
            "get_user_service_config",
            "get_config_service_config",
            "get_notification_service_config",
            "get_storage_service_config",
            "get_monitoring_service_config",
            "get_security_service_config",
            "get_plugin_service_config",
        ]


def check_quality_gates(results: dict, thresholds: dict = None) -> bool:
    """
    检查质量门禁

    Args:
        results: 报告生成结果
        thresholds: 质量门禁阈值

    Returns:
        是否通过质量门禁
    """
    if thresholds is None:
        thresholds = {
            "min_service_coverage": 60.0,
            "min_method_coverage": 50.0,
            "require_all_valid_configs": True,
        }

    all_passed = True

    # 检查覆盖率门禁
    if "coverage" in results["reports"] and "json" in results["reports"]["coverage"]:
        try:
            with open(results["reports"]["coverage"]["json"]["file"], "r") as f:
                coverage_data = json.load(f)

            summary = coverage_data["summary"]
            service_coverage = summary["service_coverage_percentage"]
            method_coverage = summary["method_coverage_percentage"]

            if service_coverage < thresholds["min_service_coverage"]:
                print(f"FAIL: Service coverage {service_coverage}% below threshold {
                    thresholds['min_service_coverage']}%")
                all_passed = False

            if method_coverage < thresholds["min_method_coverage"]:
                print(f"FAIL: Method coverage {method_coverage}% below threshold {
                    thresholds['min_method_coverage']}%")
                all_passed = False

        except Exception as e:
            print(f"ERROR: Could not check coverage gates: {e}")
            all_passed = False

    # 检查配置验证门禁
    if thresholds.get("require_all_valid_configs", True):
        if (
            "validation" in results["reports"]
            and results["reports"]["validation"].get("status") == "success"
        ):
            if not results["reports"]["validation"].get("all_valid", True):
                print("FAIL: Some mock configurations failed validation")
                all_passed = False

    return all_passed


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Generate mock monitoring reports")
    parser.add_argument("--output-dir", default="reports", help="Output directory for reports")
    parser.add_argument("--check-gates", action="store_true", help="Check quality gates")
    parser.add_argument(
        "--service-coverage", type=float, default=60.0, help="Minimum service coverage threshold"
    )
    parser.add_argument(
        "--method-coverage", type=float, default=50.0, help="Minimum method coverage threshold"
    )

    args = parser.parse_args()

    # 生成报告
    generator = MockReportGenerator(args.output_dir)
    generator.generate_all_reports()

    # 检查覆盖率门禁
    if args.check_gates:
        thresholds = {
            "min_service_coverage": args.service_coverage,
            "min_method_coverage": args.method_coverage,
            "require_all_valid_configs": True,
        }

        print("\n" + "=" * 50)
        print("QUALITY GATE CHECK")
        print("=" * 50)

        # 准备门禁检查数据
        gate_data = {}

        # 加载覆盖率数据
        try:
            coverage_file = args.output_dir / "mock_coverage_report.json"
            if coverage_file.exists():
                with open(coverage_file, "r") as f:
                    gate_data["coverage_data"] = json.load(f)
        except Exception as e:
            print(f"Warning: Could not load coverage data: {e}")

        # 加载验证数据
        try:
            validation_file = args.output_dir / "mock_validation_report.json"
            if validation_file.exists():
                with open(validation_file, "r") as f:
                    validation_data = json.load(f)
                    gate_data["validation_results"] = validation_data
        except Exception as e:
            print(f"Warning: Could not load validation data: {e}")

        # 检查门禁
        passed = check_quality_gates({"reports": gate_data}, thresholds)

        if passed:
            print("PASS: All quality gates met")
            sys.exit(0)
        else:
            print("FAIL: Some quality gates not met")
            sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
