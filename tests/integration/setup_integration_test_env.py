# -*- coding: utf-8 -*-
# Integration Test Environment Setup Script
# 集成测试环境设置脚本
import asyncio
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


class IntegrationTestEnvironmentSetup:
    """集成测试环境设置器"""

    def __init__(self, project_root: Optional[Path] = None):
        if project_root is None:
            project_root = Path(__file__).parent.parent.parent

        self.project_root = project_root
        self.test_dir = project_root / "tests" / "integration"
        self.required_directories = ["logs", "reports", "test_data"]
        self.required_files = [".env.test", "conftest.py"]

    def check_environment(self) -> bool:
        """检查测试环境"""
        logger.info("Checking integration test environment...")

        # 检查目录
        for directory in self.required_directories:
            dir_path = self.project_root / directory
            if not dir_path.exists():
                logger.warning(f"Required directory missing: {directory}")
                return False
            else:
                logger.info(f"✓ Directory exists: {directory}")

        # 检查文件
        for file in self.required_files:
            file_path = self.test_dir / file
            if not file_path.exists():
                logger.warning(f"Required file missing: {file}")
                return False
            else:
                logger.info(f"✓ File exists: {file}")

        return True

    def create_directories(self):
        """创建必要的目录"""
        logger.info("Creating required directories...")

        for directory in self.required_directories:
            dir_path = self.project_root / directory
            dir_path.mkdir(exist_ok=True)
            logger.info(f"✓ Created directory: {directory}")

    def check_dependencies(self) -> bool:
        """检查依赖项"""
        logger.info("Checking dependencies...")

        required_packages = {
            "pytest": "pytest",
            "pytest_asyncio": "pytest_asyncio",
            "pytest_timeout": "pytest_timeout",
            "httpx": "httpx",
            "sqlalchemy": "sqlalchemy",
            "alembic": "alembic",
            "redis": "redis",
        }

        missing_packages = []

        for package_name, import_name in required_packages.items():
            try:
                __import__(import_name)
                logger.info(f"✓ {package_name} is installed")
            except ImportError:
                logger.warning(f"✗ {package_name} is not installed")
                missing_packages.append(package_name)

        if missing_packages:
            logger.error(f"Missing packages: {', '.join(missing_packages)}")
            logger.info("Install with: pip install " + " ".join(missing_packages))
            return False

        return True

    def check_database_connection(self) -> bool:
        """检查数据库连接"""
        logger.info("Checking database connection...")

        database_url = os.getenv("DATABASE_URL", "sqlite:///test.db")

        try:
            if database_url.startswith("sqlite"):
                # SQLite不需要网络连接
                logger.info("✓ SQLite database (no network connection needed)")
                return True
            else:
                # 检查PostgreSQL或其他数据库连接
                import sqlalchemy  # noqa: F401
                from sqlalchemy.ext.asyncio import create_async_engine

                # 转换URL为异步版本
                async_url = database_url
                if async_url.startswith("postgresql://"):
                    async_url = async_url.replace("postgresql://", "postgresql+asyncpg://")
                elif async_url.startswith("mysql://"):
                    async_url = async_url.replace("mysql://", "mysql+aiomysql://")

                engine = create_async_engine(async_url)

                async def test_connection():
                    async with engine.connect() as conn:
                        await conn.execute("SELECT 1")

                asyncio.run(test_connection())

                # 同步方式清理
                def sync_dispose():
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            # 如果循环正在运行，创建新任务
                            loop.create_task(engine.dispose())
                        else:
                            loop.run_until_complete(engine.dispose())
                    except BaseException:
                        pass

                sync_dispose()

                logger.info("✓ Database connection successful")
                return True

        except Exception as e:
            logger.warning(f"✗ Database connection failed: {e}")
            logger.info("Database tests will be skipped")
            return False

    def check_redis_connection(self) -> bool:
        """检查Redis连接"""
        logger.info("Checking Redis connection...")

        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/1")

        try:
            import redis.asyncio as redis

            client = redis.from_url(redis_url, decode_responses=True)

            async def test_connection():
                await client.ping()
                await client.close()

            asyncio.run(test_connection())

            logger.info("✓ Redis connection successful")
            return True

        except Exception as e:
            logger.warning(f"✗ Redis connection failed: {e}")
            logger.info("Redis tests will be skipped")
            return False

    def check_api_server(self) -> bool:
        """检查API服务器"""
        logger.info("Checking API server...")

        api_url = os.getenv("API_BASE_URL", "http://localhost:8000")

        try:
            import httpx

            response = httpx.get(f"{api_url}/health", timeout=5)
            if response.status_code == 200:
                logger.info("✓ API server is running")
                return True
            else:
                logger.warning(f"✗ API server returned status {response.status_code}")
                return False

        except Exception as e:
            logger.warning(f"✗ API server check failed: {e}")
            logger.info("API tests will be skipped")
            return False

    def run_database_migrations(self):
        """运行数据库迁移"""
        logger.info("Running database migrations...")

        try:
            from alembic import command
            from alembic.config import Config

            alembic_cfg = Config()
            alembic_ini_path = self.project_root / "alembic.ini"

            if alembic_ini_path.exists():
                alembic_cfg.set_main_option("script_location", "alembic")

                database_url = os.getenv("DATABASE_URL", "sqlite:///test.db")
                alembic_cfg.set_main_option("sqlalchemy.url", database_url)

                # 升级到最新版本
                command.upgrade(alembic_cfg, "head")

                logger.info("✓ Database migrations completed")
            else:
                logger.warning("✗ alembic.ini not found")

        except Exception as e:
            logger.warning(f"✗ Database migrations failed: {e}")
            logger.info("Database migrations will be skipped")

    def setup_environment(self):
        """设置集成测试环境"""
        logger.info("=" * 60)
        logger.info("Setting up Integration Test Environment")
        logger.info("=" * 60)

        # 加载环境变量
        env_file = self.test_dir / ".env.test"
        if env_file.exists():
            logger.info(f"Loading environment from {env_file}")
            from dotenv import load_dotenv

            load_dotenv(env_file, override=True)
        else:
            logger.warning(f"Environment file not found: {env_file}")

        # 创建目录
        self.create_directories()

        # 检查依赖
        if not self.check_dependencies():
            logger.error("Dependency check failed. Please install required packages.")
            return False

        # 检查服务连接
        services_status = {
            "database": self.check_database_connection(),
            "redis": self.check_redis_connection(),
            "api": self.check_api_server(),
        }

        logger.info("Services Status:")
        for service, status in services_status.items():
            status_str = "✓ Available" if status else "✗ Unavailable"
            logger.info(f"  {service}: {status_str}")

        # 运行数据库迁移（如果数据库可用）
        if services_status["database"]:
            self.run_database_migrations()

        logger.info("=" * 60)
        logger.info("Integration Test Environment Setup Complete")
        logger.info("=" * 60)

        return True

    def run_integration_tests(self, test_filter: Optional[str] = None):
        """运行集成测试"""
        logger.info("Running integration tests...")

        # 构建pytest命令
        pytest_cmd = ["python", "-m", "pytest", "tests/integration/"]

        if test_filter:
            pytest_cmd.extend(["-k", test_filter])

        # 添加标记
        pytest_cmd.extend(["-m", "integration"])

        # 添加详细输出
        pytest_cmd.extend(["-v", "--tb=short"])

        logger.info(f"Running: {' '.join(pytest_cmd)}")

        try:
            result = subprocess.run(pytest_cmd, cwd=self.project_root, check=False)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Failed to run tests: {e}")
            return False


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="Setup and run integration tests")
    parser.add_argument("--check", action="store_true", help="Check environment only")
    parser.add_argument("--setup", action="store_true", help="Setup environment")
    parser.add_argument("--run", action="store_true", help="Run integration tests")
    parser.add_argument("--filter", type=str, help="Filter tests by name")

    args = parser.parse_args()

    setup = IntegrationTestEnvironmentSetup()

    if args.check:
        # 只检查环境
        success = setup.check_environment()
        sys.exit(0 if success else 1)

    if args.setup:
        # 设置环境
        success = setup.setup_environment()
        sys.exit(0 if success else 1)

    if args.run:
        # 运行测试
        success = setup.run_integration_tests(args.filter)
        sys.exit(0 if success else 1)

    # 默认：设置环境
    success = setup.setup_environment()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
