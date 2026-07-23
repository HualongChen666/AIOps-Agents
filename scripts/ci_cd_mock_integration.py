#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import json
import os
import sys
from pathlib import Path

from scripts.generate_mock_reports import MockReportGenerator
from tests.mock_quality_gates import load_quality_gates

"""
CI/CD集成脚本
用于在CI/CD管道中集成mock监控和质量门禁
"""


# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class CICDMockIntegration:
    """CI/CD Mock集成"""

    def __init__(self, config_path: str = None):
        """
        初始化CI/CD集成

        Args:
            config_path: 质量门禁配置路径
        """
        self.report_generator = MockReportGenerator()
        self.quality_gate_manager = load_quality_gates(config_path)

    def run_ci_pipeline(self, branch: str = None, paths: list = None, labels: list = None) -> dict:
        """
        运行CI/CD管道

        Args:
            branch: 分支名称
            paths: 修改的文件路径
            labels: PR标签

        Returns:
            管道执行结果
        """
        print("=" * 60)
        print("CI/CD MOCK MONITORING PIPELINE")
        print("=" * 60)

        results = {
            "branch": branch,
            "paths": paths,
            "labels": labels,
            "exempt": False,
            "stages": {},
        }

        # 检查豁免
        if self.quality_gate_manager.is_exempt(branch, paths, labels):
            print("\nEXEMPTION: Quality gates exempted for this pipeline")
            results["exempt"] = True
            results["stages"]["exemption_check"] = {
                "status": "exempt",
                "reason": "Matches exemption criteria",
            }
            return results

        print("\nStage 1: Report Generation")
        print("-" * 40)

        try:
            report_results = self.report_generator.generate_all_reports()
            results["stages"]["report_generation"] = {
                "status": "success",
                "reports": report_results,
            }
            print("Report generation: SUCCESS")
        except Exception as e:
            results["stages"]["report_generation"] = {"status": "failed", "error": str(e)}
            print(f"Report generation: FAILED - {e}")
            return results

        print("\nStage 2: Quality Gate Check")
        print("-" * 40)

        # 准备门禁检查数据
        gate_data = self._prepare_gate_data(report_results)

        # 检查门禁
        gates_passed = self.quality_gate_manager.check_all_gates(gate_data)
        gate_status = self.quality_gate_manager.get_gate_status()

        results["stages"]["quality_gate"] = {
            "status": "passed" if gates_passed else "failed",
            "gate_status": gate_status,
        }

        print(self.quality_gate_manager.generate_gate_report())

        print("\nStage 3: CI/CD Actions")
        print("-" * 40)

        # 根据结果执行操作
        if gates_passed:
            self._handle_success(results)
        else:
            self._handle_failure(results)

        results["pipeline_passed"] = gates_passed
        results["should_block_merge"] = self.quality_gate_manager.should_block_merge()

        print("\n" + "=" * 60)
        print("PIPELINE COMPLETED")
        print("=" * 60)

        return results

    def _prepare_gate_data(self, report_results: dict) -> dict:
        """准备门禁检查数据"""
        gate_data = {}

        # 覆盖率数据
        if "coverage" in report_results["reports"]:
            if (
                "json" in report_results["reports"]["coverage"]
                and report_results["reports"]["coverage"]["json"]["status"] == "success"
            ):
                try:
                    with open(report_results["reports"]["coverage"]["json"]["file"], "r") as f:
                        gate_data["coverage_data"] = json.load(f)
                except Exception as e:
                    print(f"Warning: Could not load coverage data: {e}")

        # 验证数据
        if (
            "validation" in report_results["reports"]
            and report_results["reports"]["validation"]["status"] == "success"
        ):
            gate_data["validation_results"] = report_results["reports"]["validation"]

        return gate_data

    def _handle_success(self, results: dict):
        """处理成功情况"""
        print("Quality gates: PASSED")

        # 检查是否需要生成徽章
        config = self.quality_gate_manager.config
        actions = config.get("actions", {}).get("on_success", {})

        if actions.get("generate_badge", False):
            self._generate_badge(results)

        if actions.get("notify_team", False):
            print("Team notification would be sent")

    def _handle_failure(self, results: dict):
        """处理失败情况"""
        print("Quality gates: FAILED")

        config = self.quality_gate_manager.config
        actions = config.get("actions", {}).get("on_failure", {})

        if actions.get("block_merge", True):
            print("Merge will be BLOCKED")

        if actions.get("comment_on_pr", True):
            self._generate_pr_comment(results)

        if actions.get("create_issue", False):
            print("Issue would be created")

        if actions.get("notify_team", True):
            print("Team notification would be sent")

    def _generate_badge(self, results: dict):
        """生成状态徽章"""
        try:
            # 这里可以集成到徽章服务
            print("Mock coverage badge would be generated")
        except Exception as e:
            print(f"Warning: Could not generate badge: {e}")

    def _generate_pr_comment(self, results: dict):
        """生成PR评论"""
        try:
            gate_report = self.quality_gate_manager.generate_gate_report()

            # 在实际CI/CD环境中，这里会调用GitHub API
            print("PR comment would be posted:")
            print(gate_report)

        except Exception as e:
            print(f"Warning: Could not generate PR comment: {e}")

    def export_results(self, results: dict, output_file: str = "ci_cd_results.json"):
        """导出CI/CD结果"""
        try:
            output_path = Path(self.report_generator.output_dir) / output_file
            with open(output_path, "w") as f:
                json.dump(results, f, indent=2)
            print(f"CI/CD results exported to: {output_path}")
        except Exception as e:
            print(f"Warning: Could not export results: {e}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="CI/CD Mock Monitoring Integration")
    parser.add_argument("--branch", help="Git branch name")
    parser.add_argument("--paths", nargs="+", help="Modified file paths")
    parser.add_argument("--labels", nargs="+", help="PR labels")
    parser.add_argument("--config", help="Quality gate config file path")
    parser.add_argument("--output-dir", default="reports", help="Reports output directory")
    parser.add_argument("--export-results", action="store_true", help="Export CI/CD results")

    args = parser.parse_args()

    # 设置输出目录
    os.environ["MOCK_REPORTS_DIR"] = args.output_dir

    # 运行CI/CD管道
    integration = CICDMockIntegration(args.config)
    results = integration.run_ci_pipeline(args.branch, args.paths, args.labels)

    # 导出结果
    if args.export_results:
        integration.export_results(results)

    # 根据结果设置退出码
    if results.get("exempt", False):
        sys.exit(0)
    elif not results.get("pipeline_passed", False):
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
