#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试覆盖率分析脚本
分析当前测试覆盖率并识别需要改进的模块
"""

import subprocess
import sys


def run_coverage_analysis(test_path, cov_path):
    """运行覆盖率分析"""
    cmd = [
        "python",
        "-m",
        "pytest",
        test_path,
        f"--cov={cov_path}",
        "--cov-report=term-missing",
        "--cov-report=html",
        "-v",
        "--tb=short",
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return "Coverage analysis timed out"
    except Exception as e:
        return f"Error running coverage analysis: {e}"


def parse_coverage_output(output):
    """解析覆盖率输出"""
    coverage_data = {}

    # 查找覆盖率表格
    lines = output.split("\n")
    in_table = False

    for line in lines:
        if "coverage:" in line.lower():
            in_table = True
            continue

        if in_table:
            # 解析覆盖率行
            # 格式: Name Stmts Miss Cover Missing
            parts = line.split()
            if len(parts) >= 4 and parts[0] != "TOTAL":
                try:
                    name = parts[0]
                    stmts = int(parts[1])
                    miss = int(parts[2])
                    cover = parts[3].replace("%", "")

                    if cover.isdigit():
                        coverage_data[name] = {
                            "statements": stmts,
                            "missing": miss,
                            "coverage": int(cover),
                        }
                except (ValueError, IndexError):
                    pass

            if "TOTAL" in line:
                break

    return coverage_data


def analyze_low_coverage_modules(coverage_data, threshold=80):
    """分析低覆盖率模块"""
    low_coverage = []

    for module, data in coverage_data.items():
        if data["coverage"] < threshold:
            low_coverage.append(
                {
                    "module": module,
                    "coverage": data["coverage"],
                    "missing": data["missing"],
                    "statements": data["statements"],
                }
            )

    # 按覆盖率排序
    low_coverage.sort(key=lambda x: x["coverage"])

    return low_coverage


def main():
    """主函数"""
    print("Test Coverage Analysis")
    print("=" * 60)

    # 分析核心模块覆盖率
    print("\n1. Analyzing core modules coverage")
    print("-" * 60)

    core_output = run_coverage_analysis("tests/core/", "core")
    core_coverage = parse_coverage_output(core_output)

    print(f"Core modules analyzed: {len(core_coverage)}")

    low_coverage_core = analyze_low_coverage_modules(core_coverage, threshold=80)

    if low_coverage_core:
        print(f"\nLow coverage core modules (< 80%): {len(low_coverage_core)}")
        for item in low_coverage_core:
            print(
                f"  {item['module']}: {item['coverage']}% ({item['missing']}/{item['statements']} missing)"  # noqa: E501
            )
    else:
        print("\nAll core modules have >= 80% coverage!")

    # 分析API模块覆盖率
    print("\n2. Analyzing API modules coverage")
    print("-" * 60)

    api_output = run_coverage_analysis("tests/api/", "api")
    api_coverage = parse_coverage_output(api_output)

    print(f"API modules analyzed: {len(api_coverage)}")

    low_coverage_api = analyze_low_coverage_modules(api_coverage, threshold=80)

    if low_coverage_api:
        print(f"\nLow coverage API modules (< 80%): {len(low_coverage_api)}")
        for item in low_coverage_api:
            print(
                f"  {item['module']}: {item['coverage']}% ({item['missing']}/{item['statements']} missing)"  # noqa: E501
            )
    else:
        print("\nAll API modules have >= 80% coverage!")

    # 总结
    print("\n" + "=" * 60)
    print("Coverage Analysis Summary")
    print("=" * 60)

    total_low_coverage = len(low_coverage_core) + len(low_coverage_api)

    if total_low_coverage > 0:
        print(f"[INFO] Total modules with < 80% coverage: {total_low_coverage}")
        print("[ACTION] Need to improve coverage for these modules")

        # 生成改进建议
        print("\nImprovement Recommendations:")
        print("-" * 60)

        for item in low_coverage_core + low_coverage_api:
            module = item["module"]
            missing = item["missing"]
            print(f"- {module}: Add {missing} more test cases to reach 80%+")

        return 1
    else:
        print("[SUCCESS] All modules have >= 80% coverage!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
