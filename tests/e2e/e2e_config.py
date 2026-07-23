# -*- coding: utf-8 -*-
"""
E2E Test Configuration
E2E测试配置和环境管理
"""

import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional  # noqa: F401

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)8s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


class E2ETestEnvironment:
    """E2E测试环境管理器"""

    def __init__(self, project_root: Optional[Path] = None):
        if project_root is None:
            project_root = Path(__file__).parent.parent.parent

        self.project_root = project_root
        self.e2e_dir = project_root / "tests" / "e2e"
        self.required_services = ["api", "database", "redis"]

    def check_environment(self) -> bool:
        """检查E2E测试环境"""
        logger.info("Checking E2E test environment...")

        # 检查API服务
        api_available = self._check_api_service()
        logger.info(f"API service: {'Available' if api_available else 'Not available'}")

        # 检查数据库服务
        db_available = self._check_database_service()
        logger.info(f"Database service: {'Available' if db_available else 'Not available'}")

        # 检查Redis服务
        redis_available = self._check_redis_service()
        logger.info(f"Redis service: {'Available' if redis_available else 'Not available'}")

        # 检查环境变量
        env_configured = self._check_environment_variables()
        logger.info(
            f"Environment variables: {'Configured' if env_configured else 'Not configured'}"
        )

        return api_available and env_configured

    def _check_api_service(self) -> bool:
        """检查API服务"""
        try:
            import httpx

            base_url = os.getenv("E2E_BASE_URL", "http://localhost:8000")

            response = httpx.get(f"{base_url}/api/v1/health", timeout=5.0)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"API service check failed: {e}")
            return False

    def _check_database_service(self) -> bool:
        """检查数据库服务"""
        try:
            import psycopg2

            db_url = os.getenv(
                "E2E_DATABASE_URL", "postgresql://testuser:testpass@localhost:5432/test_db"
            )

            conn = psycopg2.connect(db_url, connect_timeout=5)
            conn.close()
            return True
        except Exception as e:
            logger.warning(f"Database service check failed: {e}")
            return False

    def _check_redis_service(self) -> bool:
        """检查Redis服务"""
        try:
            import redis

            redis_url = os.getenv("E2E_REDIS_URL", "redis://localhost:6379/1")

            client = redis.from_url(redis_url, decode_responses=True)
            client.ping()
            client.close()
            return True
        except Exception as e:
            logger.warning(f"Redis service check failed: {e}")
            return False

    def _check_environment_variables(self) -> bool:
        """检查环境变量"""
        required_vars = ["E2E_BASE_URL"]
        optional_vars = ["E2E_DATABASE_URL", "E2E_REDIS_URL"]

        all_required = all(os.getenv(var) for var in required_vars)
        some_optional = any(os.getenv(var) for var in optional_vars)

        return all_required or some_optional

    def setup_environment(self):
        """设置E2E测试环境"""
        logger.info("Setting up E2E test environment...")

        # 创建必要的目录
        directories = ["logs", "reports", "test_data"]
        for directory in directories:
            dir_path = self.project_root / directory
            dir_path.mkdir(exist_ok=True)
            logger.info(f"Created directory: {directory}")

        # 检查环境
        env_ok = self.check_environment()

        if not env_ok:
            logger.warning("E2E environment check failed. Some tests may be skipped.")

        logger.info("E2E test environment setup complete")
        return env_ok

    def run_e2e_tests(self, test_filter: Optional[str] = None):
        """运行E2E测试"""
        logger.info("Running E2E tests...")

        # 构建pytest命令
        pytest_cmd = ["python", "-m", "pytest", "tests/e2e/"]

        if test_filter:
            pytest_cmd.extend(["-k", test_filter])

        # 添加标记
        pytest_cmd.extend(["-m", "e2e"])

        # 添加详细输出
        pytest_cmd.extend(["-v", "--tb=short"])

        # 添加超时
        pytest_cmd.extend(["--timeout=300"])

        logger.info(f"Running: {' '.join(pytest_cmd)}")

        try:
            result = subprocess.run(pytest_cmd, cwd=self.project_root, check=False)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Failed to run E2E tests: {e}")
            return False


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="E2E test environment management")
    parser.add_argument("--check", action="store_true", help="Check E2E environment")
    parser.add_argument("--setup", action="store_true", help="Setup E2E environment")
    parser.add_argument("--run", action="store_true", help="Run E2E tests")
    parser.add_argument("--filter", type=str, help="Filter tests by name")

    args = parser.parse_args()

    env = E2ETestEnvironment()

    if args.check:
        # 只检查环境
        success = env.check_environment()
        sys.exit(0 if success else 1)

    if args.setup:
        # 设置环境
        success = env.setup_environment()
        sys.exit(0 if success else 1)

    if args.run:
        # 运行测试
        success = env.run_e2e_tests(args.filter)
        sys.exit(0 if success else 1)

    # 默认：检查环境
    success = env.check_environment()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
