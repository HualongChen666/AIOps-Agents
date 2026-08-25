# -*- coding: utf-8 -*-
"""
运行安全管理、修复管理和监控高级路由测试的脚本
"""
import subprocess
import sys
from pathlib import Path


def run_tests(test_file=None, coverage=False, verbose=False):
    """
    运行测试
    
    Args:
        test_file: 特定的测试文件路径
        coverage: 是否生成覆盖率报告
        verbose: 是否显示详细输出
    """
    cmd = ["pytest"]
    
    if test_file:
        cmd.append(test_file)
    else:
        # 运行所有三个advanced router测试
        cmd.extend([
            "tests/api/test_security_advanced_router.py",
            "tests/api/test_repair_advanced_router.py",
            "tests/api/test_monitoring_advanced_router.py"
        ])
    
    if coverage:
        cmd.extend([
            "--cov=api/security_advanced_router",
            "--cov=api/repair_advanced_router",
            "--cov=api/monitoring_advanced_router",
            "--cov-report=html",
            "--cov-report=term-missing",
            "--cov-fail-under=90"
        ])
    
    if verbose:
        cmd.append("-v")
    else:
        cmd.append("-q")
    
    cmd.extend([
        "--tb=short",
        "--disable-warnings"
    ])
    
    print(f"运行命令: {' '.join(cmd)}")
    print("=" * 80)
    
    result = subprocess.run(cmd, cwd=Path(__file__).parent, shell=False)
    
    if result.returncode == 0:
        print("\n" + "=" * 80)
        print("✅ 所有测试通过！")
        if coverage:
            print("📊 覆盖率报告已生成在 htmlcov/ 目录中")
    else:
        print("\n" + "=" * 80)
        print("❌ 测试失败")
        sys.exit(1)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="运行高级路由测试")
    parser.add_argument(
        "--security",
        action="store_true",
        help="只运行安全管理测试"
    )
    parser.add_argument(
        "--repair",
        action="store_true",
        help="只运行修复管理测试"
    )
    parser.add_argument(
        "--monitoring",
        action="store_true",
        help="只运行监控测试"
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="生成覆盖率报告"
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="详细输出"
    )
    
    args = parser.parse_args()
    
    test_file = None
    if args.security:
        test_file = "tests/api/test_security_advanced_router.py"
    elif args.repair:
        test_file = "tests/api/test_repair_advanced_router.py"
    elif args.monitoring:
        test_file = "tests/api/test_monitoring_advanced_router.py"
    
    run_tests(test_file=test_file, coverage=args.coverage, verbose=args.verbose)


if __name__ == "__main__":
    main()
