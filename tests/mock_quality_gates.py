# -*- coding: utf-8 -*-
"""
Mock质量门禁管理器
加载和应用质量门禁配置
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional


class MockQualityGateManager:
    """Mock质量门禁管理器"""

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化质量门禁管理器

        Args:
            config_path: 配置文件路径，默认为.github/mock_quality_gates.json
        """
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), ".github", "mock_quality_gates.json"
            )

        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.violations: List[str] = []
        self.warnings: List[str] = []

    def _load_config(self) -> Dict[str, Any]:
        """加载质量门禁配置"""
        if not self.config_path.exists():
            return self._get_default_config()

        try:
            with open(self.config_path, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load config from {self.config_path}: {e}")
            return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "version": "1.0",
            "gates": {
                "coverage": {
                    "enabled": True,
                    "service_coverage_threshold": 60.0,
                    "method_coverage_threshold": 50.0,
                    "fail_on_threshold_violation": True,
                },
                "configuration": {"enabled": True, "require_all_valid": True},
                "performance": {
                    "enabled": True,
                    "max_avg_creation_time_ms": 1.0,
                    "max_avg_usage_time_ms": 0.1,
                },
            },
        }

    def check_coverage_gate(self, coverage_data: Dict[str, Any]) -> bool:
        """
        检查覆盖率门禁

        Args:
            coverage_data: 覆盖率数据

        Returns:
            是否通过门禁
        """
        gate_config = self.config["gates"]["coverage"]

        if not gate_config["enabled"]:
            return True

        summary = coverage_data.get("summary", {})
        service_coverage = summary.get("service_coverage_percentage", 0)
        method_coverage = summary.get("method_coverage_percentage", 0)

        service_threshold = gate_config["service_coverage_threshold"]
        method_threshold = gate_config["method_coverage_threshold"]

        passed = True

        if service_coverage < service_threshold:
            violation = f"Service coverage {service_coverage}% below threshold {service_threshold}%"
            self.violations.append(violation)
            passed = False
        elif service_coverage < gate_config.get("warning_threshold", 75.0):
            warning = (
                f"Service coverage {service_coverage}% below warning threshold "
                f"{gate_config.get('warning_threshold', 75.0)}%"
            )
            self.warnings.append(warning)

        if method_coverage < method_threshold:
            violation = f"Method coverage {method_coverage}% below threshold {method_threshold}%"
            self.violations.append(violation)
            passed = False

        return passed

    def check_configuration_gate(self, validation_results: Dict[str, Any]) -> bool:
        """
        检查配置门禁

        Args:
            validation_results: 验证结果

        Returns:
            是否通过门禁
        """
        gate_config = self.config["gates"]["configuration"]

        if not gate_config["enabled"]:
            return True

        if gate_config["require_all_valid"]:
            if not validation_results.get("all_valid", True):
                self.violations.append("Some mock configurations failed validation")
                return False

        return True

    def check_performance_gate(self, performance_data: Dict[str, Any]) -> bool:
        """
        检查性能门禁

        Args:
            performance_data: 性能数据

        Returns:
            是否通过门禁
        """
        gate_config = self.config["gates"]["performance"]

        if not gate_config["enabled"]:
            return True

        passed = True

        # 检查创建时间
        avg_creation_time = performance_data.get("avg_creation_time_ms", 0)
        if avg_creation_time > gate_config["max_avg_creation_time_ms"]:
            violation = (
                f"Mock creation time {avg_creation_time}ms above threshold "
                f"{gate_config['max_avg_creation_time_ms']}ms"
            )
            self.violations.append(violation)
            passed = False

        # 检查使用时间
        avg_usage_time = performance_data.get("avg_usage_time_ms", 0)
        if avg_usage_time > gate_config["max_avg_usage_time_ms"]:
            violation = f"Mock usage time {avg_usage_time}ms above threshold {  # noqa: E501
                gate_config['max_avg_usage_time_ms']}ms"
            self.violations.append(violation)
            passed = False

        return passed

    def check_usage_gate(self, usage_data: Dict[str, Any]) -> bool:
        """
        检查使用门禁

        Args:
            usage_data: 使用数据

        Returns:
            是否通过门禁
        """
        gate_config = self.config["gates"]["usage"]

        if not gate_config["enabled"]:
            return True

        passed = True

        # 检查过度使用
        if gate_config["identify_overused_mocks"]:
            overused = usage_data.get("overused_mocks", [])
            max_threshold = gate_config.get("max_overuse_threshold", 100)

            for mock_info in overused:
                if mock_info.get("calls", 0) > max_threshold:
                    violation = f"Mock {mock_info['name']} overused with {mock_info['calls']} calls"
                    self.violations.append(violation)
                    passed = False

        # 检查未使用
        if gate_config["identify_unused_mocks"]:
            unused = usage_data.get("unused_mocks", [])

            for mock_name in unused:
                # 未使用的mock通常不作为门禁，但可以产生警告
                warning = f"Mock {mock_name} is unused"
                self.warnings.append(warning)

        return passed

    def check_all_gates(self, results: Dict[str, Any]) -> bool:
        """
        检查所有门禁

        Args:
            results: 测试和报告结果

        Returns:
            是否通过所有门禁
        """
        self.violations.clear()
        self.warnings.clear()

        all_passed = True

        # 检查覆盖率门禁
        if "coverage_data" in results:
            if not self.check_coverage_gate(results["coverage_data"]):
                all_passed = False

        # 检查配置门禁
        if "validation_results" in results:
            if not self.check_configuration_gate(results["validation_results"]):
                all_passed = False

        # 检查性能门禁
        if "performance_data" in results:
            if not self.check_performance_gate(results["performance_data"]):
                all_passed = False

        # 检查使用门禁
        if "usage_data" in results:
            if not self.check_usage_gate(results["usage_data"]):
                all_passed = False

        return all_passed

    def get_gate_status(self) -> Dict[str, Any]:
        """获取门禁状态"""
        return {
            "passed": len(self.violations) == 0,
            "violations": self.violations,
            "warnings": self.warnings,
            "config_file": str(self.config_path),
        }

    def should_block_merge(self) -> bool:
        """是否应该阻止合并"""
        if len(self.violations) == 0:
            return False

        # 检查配置中的失败操作
        actions = self.config.get("actions", {}).get("on_failure", {})
        return actions.get("block_merge", True)

    def generate_gate_report(self) -> str:
        """生成门禁报告"""
        report_lines = [
            "=" * 60,
            "MOCK QUALITY GATE REPORT",
            "=" * 60,
            "",
            f"Config: {self.config_path}",
            f"Passed: {len(self.violations) == 0}",
            f"Violations: {len(self.violations)}",
            f"Warnings: {len(self.warnings)}",
            "",
        ]

        if self.violations:
            report_lines.append("VIOLATIONS:")
            for violation in self.violations:
                report_lines.append(f"  FAIL: {violation}")
            report_lines.append("")

        if self.warnings:
            report_lines.append("WARNINGS:")
            for warning in self.warnings:
                report_lines.append(f"  WARNING: {warning}")
            report_lines.append("")

        if len(self.violations) == 0:
            report_lines.append("RESULT: PASS - All quality gates met")
        else:
            report_lines.append("RESULT: FAIL - Some quality gates not met")
            if self.should_block_merge():
                report_lines.append("ACTION: Merge blocked")
            else:
                report_lines.append("ACTION: Merge not blocked but review required")

        report_lines.append("=" * 60)
        return "\n".join(report_lines)

    def is_exempt(
        self, branch: str = None, paths: List[str] = None, labels: List[str] = None
    ) -> bool:
        """
        检查是否豁免质量门禁

        Args:
            branch: 分支名称
            paths: 文件路径列表
            labels: PR标签列表

        Returns:
            是否豁免
        """
        exemptions = self.config.get("exemptions", {})

        # 分支豁免
        if branch and branch in exemptions.get("branches", []):
            return True

        # 路径豁免
        if paths:
            exempt_paths = exemptions.get("paths", [])
            for path in paths:
                for exempt_path in exempt_paths:
                    if path.startswith(exempt_path.replace("*", "")):
                        return True

        # 标签豁免
        if labels:
            exempt_labels = exemptions.get("labels", [])
            if any(label in exempt_labels for label in labels):
                return True

        return False


def load_quality_gates(config_path: Optional[str] = None) -> MockQualityGateManager:
    """
    加载质量门禁管理器

    Args:
        config_path: 配置文件路径

    Returns:
        质量门禁管理器实例
    """
    return MockQualityGateManager(config_path)
