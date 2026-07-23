# -*- coding: utf-8 -*-
# Integration Tests Configuration
# 集成测试配置和fixtures
import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import AsyncGenerator, Generator  # noqa: F401

import pytest

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)8s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


# =============================
# 集成测试标记
# =============================


def pytest_configure(config):
    """配置pytest集成测试标记"""
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "database: marks tests requiring database")
    config.addinivalue_line("markers", "redis: marks tests requiring Redis")
    config.addinivalue_line("markers", "api: marks tests requiring API server")
    config.addinivalue_line("markers", "external: marks tests requiring external services")


# =============================
# 环境变量加载
# =============================


@pytest.fixture(scope="session", autouse=True)
def load_test_environment():
    """加载集成测试环境变量"""
    env_file = Path(__file__).parent / ".env.test"

    if env_file.exists():
        logger.info(f"Loading test environment from {env_file}")
        # 加载环境变量
        from dotenv import load_dotenv

        load_dotenv(env_file, override=True)
    else:
        logger.warning(f"Test environment file not found: {env_file}")
        # 设置默认测试环境变量
        os.environ.setdefault("ENVIRONMENT", "test")
        os.environ.setdefault("TESTING", "true")
        os.environ.setdefault("DATABASE_URL", "sqlite:///test.db")
        os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")

    yield

    logger.info("Test environment unloaded")


# =============================
# 数据库Fixtures
# =============================


@pytest.fixture(scope="session")
def test_database_url():
    """获取测试数据库URL"""
    return os.getenv("DATABASE_URL", "sqlite:///test.db")


@pytest.fixture(scope="session")
def test_database_engine(test_database_url):
    """创建测试数据库引擎"""
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine  # noqa: F401
    from sqlalchemy.orm import sessionmaker  # noqa: F401

    # 如果是SQLite URL，转换为异步版本
    db_url = test_database_url
    if db_url.startswith("sqlite:///"):
        db_url = db_url.replace("sqlite:///", "sqlite+aiosqlite:///")

    engine = create_async_engine(db_url, echo=False, pool_pre_ping=True, pool_recycle=3600)

    yield engine

    # 清理
    asyncio.run(engine.dispose())


@pytest.fixture(scope="session")
async def init_test_database(test_database_engine):
    """初始化测试数据库"""
    # 这里可以添加数据库初始化逻辑
    # 例如：创建表、插入测试数据等
    logger.info("Initializing test database")

    # 示例：运行数据库迁移
    try:
        from alembic import command
        from alembic.config import Config

        alembic_cfg = Config()
        alembic_cfg.set_main_option("sqlalchemy.url", str(test_database_engine.url))

        # 升级到最新版本
        command.upgrade(alembic_cfg, "head")

        logger.info("Database migration completed")
    except Exception as e:
        logger.warning(f"Database migration failed: {e}")

    yield

    # 清理测试数据库
    logger.info("Cleaning up test database")
    # 这里可以添加数据库清理逻辑


@pytest.fixture
async def db_session(test_database_engine):
    """创建测试数据库会话"""
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import sessionmaker

    async_session_maker = sessionmaker(
        test_database_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session_maker() as session:
        yield session

        # 回滚事务，保持测试隔离
        await session.rollback()


# =============================
# Redis Fixtures
# =============================


@pytest.fixture(scope="session")
def redis_client():
    """创建Redis客户端"""
    import redis.asyncio as redis

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/1")
    client = redis.from_url(redis_url, decode_responses=True)

    yield client

    # 清理
    asyncio.run(client.close())


@pytest.fixture
async def clean_redis(redis_client):
    """清理Redis测试数据"""
    # 清理测试数据库
    test_db = os.getenv("REDIS_TEST_DB", "1")
    await redis_client.select(test_db)
    await redis_client.flushdb()

    yield

    # 最终清理
    await redis_client.flushdb()


# =============================
# API Fixtures
# =============================


@pytest.fixture(scope="session")
def api_client():
    """创建API测试客户端"""
    from fastapi import FastAPI  # noqa: F401
    from httpx import ASGITransport, AsyncClient  # noqa: F401

    # 这里可以导入你的FastAPI应用
    # from main import app

    # 暂时返回None，需要根据实际应用调整
    return None


@pytest.fixture
async def api_session(api_client):
    """创建API会话"""
    if api_client is None:
        pytest.skip("API client not available")

    async with api_client as session:
        yield session


# =============================
# 测试数据Fixtures
# =============================


@pytest.fixture
def sample_user_data():
    """示例用户数据"""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpass123",
        "full_name": "Test User",
        "is_active": True,
        "is_superuser": False,
    }


@pytest.fixture
def sample_alert_data():
    """示例告警数据"""
    return {
        "id": 1,
        "title": "CPU使用率过高",
        "severity": "critical",
        "description": "CPU使用率超过90%",
        "timestamp": "2024-01-01T00:00:00Z",
        "source": "monitoring",
        "status": "open",
    }


@pytest.fixture
def sample_metric_data():
    """示例指标数据"""
    return {
        "metric_name": "cpu_usage",
        "metric_value": 85.5,
        "timestamp": "2024-01-01T00:00:00Z",
        "labels": {"host": "server1", "region": "us-east-1"},
    }


# =============================
# 测试工具Fixtures
# =============================


@pytest.fixture
def test_data_cleaner():
    """测试数据清理器"""

    class TestDataCleaner:
        def __init__(self):
            self.cleanup_tasks = []

        def add_cleanup_task(self, task):
            """添加清理任务"""
            self.cleanup_tasks.append(task)

        async def cleanup(self):
            """执行所有清理任务"""
            for task in self.cleanup_tasks:
                try:
                    if asyncio.iscoroutinefunction(task):
                        await task()
                    else:
                        task()
                except Exception as e:
                    logger.error(f"Cleanup task failed: {e}")

            self.cleanup_tasks.clear()

    cleaner = TestDataCleaner()
    yield cleaner

    # 自动清理
    asyncio.run(cleaner.cleanup())


@pytest.fixture
async def test_isolation(db_session, clean_redis):
    """测试隔离fixture，确保每个测试独立"""
    # 清理数据库
    await db_session.rollback()

    # 清理Redis
    await clean_redis

    yield

    # 最终清理
    await db_session.rollback()


# =============================
# Mock服务Fixtures
# =============================


@pytest.fixture
def mock_ai_service():
    """AI服务Mock"""
    from unittest.mock import AsyncMock, MagicMock  # noqa: F401

    mock = AsyncMock()
    mock.analyze = AsyncMock(
        return_value={"analysis": "Test analysis result", "confidence": 0.9, "recommendations": []}
    )

    return mock


@pytest.fixture
def mock_alert_service():
    """告警服务Mock"""
    from unittest.mock import MagicMock

    mock = MagicMock()
    mock.create_alert = MagicMock(return_value={"id": 1})
    mock.get_alert = MagicMock(return_value={"id": 1, "title": "Test Alert"})
    mock.list_alerts = MagicMock(return_value=[{"id": 1, "title": "Test Alert"}])

    return mock


@pytest.fixture
def mock_monitoring_service():
    """监控服务Mock"""
    from unittest.mock import AsyncMock

    mock = AsyncMock()
    mock.get_metrics = AsyncMock(return_value=[{"metric_name": "cpu_usage", "value": 75.5}])
    mock.get_alerts = AsyncMock(return_value=[])

    return mock


# =============================
# 测试超时和重试
# =============================


@pytest.fixture
def test_timeout():
    """获取测试超时时间"""
    return int(os.getenv("TEST_TIMEOUT", "30"))


@pytest.fixture
def retry_on_failure(max_retries=3, delay=1):
    """测试重试装饰器"""

    def decorator(test_func):
        async def wrapper(*args, **kwargs):
            import time  # noqa: F401

            last_exception = None

            for attempt in range(max_retries):
                try:
                    if asyncio.iscoroutinefunction(test_func):
                        return await test_func(*args, **kwargs)
                    else:
                        return test_func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        await asyncio.sleep(delay)
                    else:
                        raise last_exception

        return wrapper

    return decorator


# =============================
# 测试生命周期钩子
# =============================


@pytest.fixture(scope="session", autouse=True)
def setup_integration_test_environment():
    """设置集成测试环境"""
    logger.info("Setting up integration test environment")

    # 创建必要的目录
    directories = ["logs", "reports", "test_data"]
    for directory in directories:
        dir_path = Path(__file__).parent.parent.parent / directory
        dir_path.mkdir(exist_ok=True)

    yield

    logger.info("Tearing down integration test environment")

    # 清理测试环境
    # 这里可以添加清理逻辑


@pytest.fixture(autouse=True)
def log_test_start(request):
    """记录测试开始"""
    logger.info(f"Starting test: {request.node.name}")
    yield
    logger.info(f"Finished test: {request.node.name}")


# =============================
# 性能测试Fixtures
# =============================


@pytest.fixture
def performance_timer():
    """性能计时器"""
    import time

    class PerformanceTimer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
            self.elapsed = None

        def start(self):
            self.start_time = time.time()

        def stop(self):
            self.end_time = time.time()
            self.elapsed = self.end_time - self.start_time
            return self.elapsed

        def __enter__(self):
            self.start()
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            self.stop()

    return PerformanceTimer()


# =============================
# 测试数据生成器
# =============================


@pytest.fixture
def test_data_generator():
    """测试数据生成器"""
    import random
    import uuid  # noqa: F401
    from datetime import datetime, timedelta

    class TestDataGenerator:
        @staticmethod
        def random_user():
            """生成随机用户数据"""
            return {
                "username": f"user_{random.randint(1000, 9999)}",
                "email": f"user_{random.randint(1000, 9999)}@example.com",
                "password": "password123",
                "full_name": f"User {random.randint(1000, 9999)}",
                "is_active": True,
                "is_superuser": False,
            }

        @staticmethod
        def random_alert():
            """生成随机告警数据"""
            severities = ["info", "warning", "critical"]
            return {
                "id": random.randint(1, 10000),
                "title": f"Alert {random.randint(1000, 9999)}",
                "severity": random.choice(severities),
                "description": f"Test alert description {random.randint(1000, 9999)}",
                "timestamp": (datetime.now() + timedelta(hours=random.randint(-24, 0))).isoformat(),
                "source": "test",
                "status": "open",
            }

        @staticmethod
        def random_metric():
            """生成随机指标数据"""
            return {
                "metric_name": f"metric_{random.randint(1, 100)}",
                "metric_value": random.uniform(0, 100),
                "timestamp": (
                    (datetime.now() + timedelta(minutes=random.randint(-60, 0))).isoformat()
                ),
                "labels": {
                    "host": f"server{random.randint(1, 10)}",
                    "region": random.choice(["us-east-1", "us-west-1", "eu-west-1"]),
                },
            }

    return TestDataGenerator()
