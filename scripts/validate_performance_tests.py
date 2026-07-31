#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging

"""
Validate Performance Tests
性能测试验证脚本
"""

import shutil
import sys
from pathlib import Path

from core.security import subprocess_runner


def check_dependencies():
    """检查依赖项是否已安装"""
    print("=" * 60)
    print("检查性能测试依赖项")
    print("=" * 60)

    dependencies = [
        ("pytest", "pytest --version"),
        ("pytest-benchmark", "pytest --version"),
        ("locust", "locust --version"),
    ]

    missing = []
    for name, check_cmd in dependencies:
        try:
            result = subprocess_runner.run(check_cmd.split(), capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print(f"✅ {name}: 已安装")
            else:
                print(f"❌ {name}: 未安装")
                missing.append(name)
        except Exception as e:
            logging.exception("Unexpected exception: %s", e)
            print(f"❌ {name}: 未安装")
            missing.append(name)

    if missing:
        print(f"\n缺少依赖项: {', '.join(missing)}")
        print("请运行: pip install -r requirements.txt")
        return False

    print("\n✅ 所有依赖项已安装")
    return True


def validate_api_performance_tests():
    """验证API性能测试"""
    print("\n" + "=" * 60)
    print("验证API性能测试")
    print("=" * 60)

    try:
        # 检查locustfile是否存在
        locustfile = Path("tests/performance/locustfile.py")
        if not locustfile.exists():
            print(f"❌ Locust文件不存在: {locustfile}")
            return False

        print(f"✅ Locust文件存在: {locustfile}")

        # 验证locustfile语法
        locust_cmd = shutil.which("locust") or "locust"
        result = subprocess_runner.run(
            [locust_cmd, "-f", str(locustfile), "--check"], capture_output=True, text=True, timeout=30
        )

        if result.returncode == 0:
            print("✅ Locust文件语法验证通过")
            return True
        else:
            print("❌ Locust文件语法验证失败")
            print(result.stderr)
            return False

    except Exception as e:
        print(f"❌ 验证失败: {e}")
        return False


def validate_database_performance_tests():
    """验证数据库性能测试"""
    print("\n" + "=" * 60)
    print("验证数据库性能测试")
    print("=" * 60)

    try:
        # 检查测试文件是否存在
        test_files = [
            "tests/performance/database/test_crud_performance.py",
            "tests/performance/database/test_connection_pool_performance.py",
            "tests/performance/database/test_transaction_performance.py",
            "tests/performance/database/test_index_performance.py",
        ]

        for test_file in test_files:
            test_path = Path(test_file)
            if not test_path.exists():
                print(f"❌ 测试文件不存在: {test_file}")
                return False
            print(f"✅ 测试文件存在: {test_file}")

        # 收集测试（不运行）
        pytest_cmd = shutil.which("pytest") or "pytest"
        result = subprocess_runner.run(
            [pytest_cmd, "tests/performance/database/", "--collect-only"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            print("✅ 数据库性能测试收集成功")
            return True
        else:
            print("❌ 数据库性能测试收集失败")
            print(result.stderr)
            return False

    except Exception as e:
        print(f"❌ 验证失败: {e}")
        return False


def validate_ai_performance_tests():
    """验证AI性能测试"""
    print("\n" + "=" * 60)
    print("验证AI性能测试")
    print("=" * 60)

    try:
        # 检查测试文件是否存在
        test_files = [
            "tests/performance/ai/test_llm_performance.py",
            "tests/performance/ai/test_rag_performance.py",
            "tests/performance/ai/test_agent_performance.py",
        ]

        for test_file in test_files:
            test_path = Path(test_file)
            if not test_path.exists():
                print(f"❌ 测试文件不存在: {test_file}")
                return False
            print(f"✅ 测试文件存在: {test_file}")

        # 收集测试（不运行）
        pytest_cmd = shutil.which("pytest") or "pytest"
        result = subprocess_runner.run(
            [pytest_cmd, "tests/performance/ai/", "--collect-only"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            print("✅ AI性能测试收集成功")
            return True
        else:
            print("❌ AI性能测试收集失败")
            print(result.stderr)
            return False

    except Exception as e:
        print(f"❌ 验证失败: {e}")
        return False


def validate_database_migration():
    """验证数据库迁移"""
    print("\n" + "=" * 60)
    print("验证数据库迁移")
    print("=" * 60)

    try:
        # 检查迁移文件是否存在
        migration_file = Path("alembic/versions/20240102_000000_add_performance_tables.py")
        if not migration_file.exists():
            print(f"❌ 迁移文件不存在: {migration_file}")
            return False

        print(f"✅ 迁移文件存在: {migration_file}")

        # 检查迁移语法
        result = subprocess_runner.run(
            [sys.executable, "-m", "py_compile", str(migration_file)],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            print("✅ 迁移文件语法验证通过")
            return True
        else:
            print("❌ 迁移文件语法验证失败")
            print(result.stderr)
            return False

    except Exception as e:
        print(f"❌ 验证失败: {e}")
        return False


def validate_performance_services():
    """验证性能服务"""
    print("\n" + "=" * 60)
    print("验证性能服务")
    print("=" * 60)

    try:
        # 检查服务文件是否存在
        service_files = [
            "core/performance_data_collector.py",
            "core/performance_regression_detector.py",
            "core/performance_report_generator.py",
        ]

        for service_file in service_files:
            service_path = Path(service_file)
            if not service_path.exists():
                print(f"❌ 服务文件不存在: {service_file}")
                return False
            print(f"✅ 服务文件存在: {service_file}")

        # 检查语法
        for service_file in service_files:
            result = subprocess_runner.run(
                [sys.executable, "-m", "py_compile", service_file],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                print(f"❌ 服务文件语法验证失败: {service_file}")
                print(result.stderr)
                return False

        print("✅ 所有服务文件语法验证通过")
        return True

    except Exception as e:
        print(f"❌ 验证失败: {e}")
        return False


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("性能测试验证")
    print("=" * 60)

    results = {
        "依赖项检查": check_dependencies(),
        "API性能测试": validate_api_performance_tests(),
        "数据库性能测试": validate_database_performance_tests(),
        "AI性能测试": validate_ai_performance_tests(),
        "数据库迁移": validate_database_migration(),
        "性能服务": validate_performance_services(),
    }

    print("\n" + "=" * 60)
    print("验证结果汇总")
    print("=" * 60)

    for name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name}: {status}")

    all_passed = all(results.values())

    print("\n" + "=" * 60)
    if all_passed:
        print("✅ 所有验证通过")
        print("=" * 60)
        return 0
    else:
        print("❌ 部分验证失败")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
