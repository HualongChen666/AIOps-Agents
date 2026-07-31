#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
"""
AIOps Agent 测试维护脚本
用于定期检查和更新测试以跟上代码变更
"""

import json
import os  # noqa: F401
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Windows控制台编码处理
if sys.platform == "win32":
    import codecs

    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())


class TestMaintenance:
    """测试维护工具"""

    def __init__(self, project_root=None):
        """初始化测试维护工具"""
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.test_dir = self.project_root / "tests"
        self.unit_test_dir = self.test_dir / "unit"
        self.integration_test_dir = self.test_dir / "integration"
        self.e2e_test_dir = self.test_dir / "e2e"
        self.core_dir = self.project_root / "core"
        self.api_dir = self.project_root / "api"

        self.results = {
            "timestamp": datetime.now().isoformat(),
            "checks": [],
            "recommendations": [],
        }

    def check_test_coverage_for_new_files(self):
        """检查新代码文件是否有对应的测试"""
        print("检查新代码文件的测试覆盖...")

        # 获取所有Python文件
        core_files = list(self.core_dir.glob("**/*.py"))
        api_files = list(self.api_dir.glob("**/*.py"))

        # 检查是否有对应的测试文件
        missing_tests = []

        for code_file in core_files + api_files:
            # 跳过__init__.py文件
            if code_file.name == "__init__.py":
                continue

            # 构造预期的测试文件名
            module_name = code_file.stem
            expected_test_name = f"test_{module_name}.py"

            # 检查测试文件是否存在
            test_exists = (self.unit_test_dir / expected_test_name).exists() or (
                self.test_dir / expected_test_name
            ).exists()

            if not test_exists:
                missing_tests.append(
                    {
                        "code_file": str(code_file.relative_to(self.project_root)),
                        "expected_test": expected_test_name,
                        "priority": (
                            "high"
                            if "engine" in module_name or "router" in module_name
                            else "medium"
                        ),
                    }
                )

        self.results["checks"].append(
            {
                "name": "test_coverage_for_new_files",
                "status": "completed",
                "missing_tests_count": len(missing_tests),
                "missing_tests": missing_tests[:10],  # 只显示前10个
            }
        )

        if missing_tests:
            self.results["recommendations"].append(
                {
                    "type": "new_tests_needed",
                    "message": f"发现 {len(missing_tests)} 个代码文件缺少测试",
                    "details": missing_tests,
                }
            )

        print(f"   发现 {len(missing_tests)} 个文件缺少测试")
        return missing_tests

    def check_test_file_age(self):
        """检查测试文件是否需要更新"""
        print("检查测试文件更新状态...")

        outdated_tests = []
        current_time = datetime.now()

        # 检查单元测试
        if self.unit_test_dir.exists():
            for test_file in self.unit_test_dir.glob("test_*.py"):
                # 获取对应的代码文件
                module_name = test_file.stem.replace("test_", "")
                code_file = self.core_dir / f"{module_name}.py"

                if code_file.exists():
                    # 比较修改时间
                    test_mtime = datetime.fromtimestamp(test_file.stat().st_mtime)
                    code_mtime = datetime.fromtimestamp(code_file.stat().st_mtime)

                    # 如果代码文件比测试文件新，可能需要更新测试
                    if code_mtime > test_mtime:
                        days_old = (current_time - test_mtime).days
                        outdated_tests.append(
                            {
                                "test_file": str(test_file.relative_to(self.project_root)),
                                "code_file": str(code_file.relative_to(self.project_root)),
                                "days_since_test_update": days_old,
                                "priority": "high" if days_old > 30 else "medium",
                            }
                        )

        self.results["checks"].append(
            {
                "name": "test_file_age",
                "status": "completed",
                "outdated_tests_count": len(outdated_tests),
                "outdated_tests": outdated_tests[:10],
            }
        )

        if outdated_tests:
            self.results["recommendations"].append(
                {
                    "type": "outdated_tests",
                    "message": f"发现 {len(outdated_tests)} 个测试文件可能需要更新",
                    "details": outdated_tests,
                }
            )

        print(f"   发现 {len(outdated_tests)} 个测试文件可能需要更新")
        return outdated_tests

    def check_import_coverage(self):
        """检查测试中的导入是否与代码匹配"""
        print("检查导入覆盖...")

        # 这里可以添加逻辑来检查测试文件是否导入了被测试的模块
        # 简化版本：检查测试文件是否至少导入了对应的模块

        import_issues = []

        if self.unit_test_dir.exists():
            for test_file in self.unit_test_dir.glob("test_*.py"):
                try:
                    with open(test_file, "r", encoding="utf-8") as f:
                        content = f.read()

                    # 检查是否导入了core模块
                    if "from core." not in content and "import core." not in content:
                        import_issues.append(
                            {
                                "test_file": str(test_file.relative_to(self.project_root)),
                                "issue": "可能缺少core模块导入",
                            }
                        )
                except Exception as e:
                    import_issues.append(
                        {
                            "test_file": str(test_file.relative_to(self.project_root)),
                            "issue": f"读取文件失败: {str(e)}",
                        }
                    )

        self.results["checks"].append(
            {
                "name": "import_coverage",
                "status": "completed",
                "import_issues_count": len(import_issues),
                "import_issues": import_issues[:5],
            }
        )

        print(f"   发现 {len(import_issues)} 个导入问题")
        return import_issues

    def run_quick_test_check(self):
        """运行快速测试检查"""
        print("运行快速测试检查...")

        try:
            # 运行单元测试收集
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "tests/unit/", "--collect-only"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=30,
            )

            collected_tests = result.stdout.count("test_")

            self.results["checks"].append(
                {
                    "name": "quick_test_check",
                    "status": "completed",
                    "collected_tests": collected_tests,
                    "success": result.returncode == 0,
                }
            )

            print(f"   收集到 {collected_tests} 个测试用例")

            if result.returncode != 0:
                self.results["recommendations"].append(
                    {
                        "type": "test_collection_error",
                        "message": "测试收集失败，可能存在导入错误",
                        "details": result.stderr,
                    }
                )

            return collected_tests

        except subprocess.TimeoutExpired:
            print("   ⚠️  测试收集超时")
            self.results["checks"].append(
                {"name": "quick_test_check", "status": "timeout", "error": "测试收集超时"}
            )
            return 0
        except Exception as e:
            print(f"   ❌ 测试收集失败: {str(e)}")
            self.results["checks"].append(
                {"name": "quick_test_check", "status": "error", "error": str(e)}
            )
            return 0

    def generate_maintenance_report(self):
        """生成维护报告"""
        print("生成维护报告...")

        report = {
            "summary": {
                "total_checks": len(self.results["checks"]),
                "total_recommendations": len(self.results["recommendations"]),
                "timestamp": self.results["timestamp"],
            },
            "details": self.results,
        }

        # 保存报告
        report_file = self.project_root / "docs" / "reports" / "test_maintenance_report.json"
        report_file.parent.mkdir(parents=True, exist_ok=True)

        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"   报告已保存到: {report_file}")
        return report

    def print_summary(self):
        """打印维护摘要"""
        print("\n" + "=" * 50)
        print("测试维护摘要")
        print("=" * 50)

        print(f"检查时间: {self.results['timestamp']}")
        print(f"执行检查: {len(self.results['checks'])}")
        print(f"发现问题: {len(self.results['recommendations'])}")

        if self.results["recommendations"]:
            print("\n建议行动:")
            for i, rec in enumerate(self.results["recommendations"], 1):
                print(f"{i}. {rec['message']}")
        else:
            print("\n未发现需要立即处理的问题")

        print("=" * 50)


def main():
    """主函数"""
    print("AIOps Agent 测试维护工具")
    print("=" * 50)

    # 创建维护工具实例
    maintainer = TestMaintenance()

    # 执行各项检查
    maintainer.check_test_coverage_for_new_files()
    maintainer.check_test_file_age()
    maintainer.check_import_coverage()
    maintainer.run_quick_test_check()

    # 生成报告
    maintainer.generate_maintenance_report()

    # 打印摘要
    maintainer.print_summary()

    return 0


if __name__ == "__main__":
    sys.exit(main())
