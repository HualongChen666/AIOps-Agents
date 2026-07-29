# -*- coding: utf-8 -*-
"""
E2E Test Configuration
E2E测试配置和fixtures，提供真实环境集成测试的基础设施
"""

import asyncio
import os
import shutil
import sys
import tempfile
from typing import AsyncGenerator

import httpx
import pytest
from playwright.async_api import Browser, BrowserContext, Page, async_playwright

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# E2E 默认使用本地 SQLite,避免依赖 PostgreSQL
os.environ.setdefault("USE_SQLITE", "true")
os.environ.setdefault("SQLITE_PATH", os.path.join(tempfile.gettempdir(), "aiops_e2e.db"))

# E2E测试标记
pytestmark = pytest.mark.e2e


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环用于异步测试"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def http_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """创建真实的HTTP客户端用于E2E测试"""
    os.getenv("E2E_BASE_URL", "http://localhost:8000")

    async with httpx.AsyncClient(timeout=30.0) as client:
        yield client


@pytest.fixture(scope="session")
def test_database_url():
    """获取测试数据库URL"""
    return os.getenv("E2E_DATABASE_URL", "postgresql://testuser:testpass@localhost:5432/test_db")


@pytest.fixture(scope="session")
def test_redis_url():
    """获取测试Redis URL"""
    return os.getenv("E2E_REDIS_URL", "redis://localhost:6379/1")


@pytest.fixture(scope="session")
def test_qdrant_url():
    """获取测试Qdrant URL"""
    return os.getenv("E2E_QDRANT_URL", "http://localhost:6333")


@pytest.fixture(scope="function")
async def cleanup_database():
    """清理测试数据库的fixture"""
    # 在每个测试前后清理数据库状态
    yield
    # 清理逻辑
    await cleanup_test_data()


@pytest.fixture(scope="function")
async def cleanup_redis():
    """清理测试Redis的fixture"""
    yield
    # 清理Redis缓存
    await cleanup_test_cache()


@pytest.fixture(scope="function")
def test_data_dir():
    """创建临时测试数据目录"""
    temp_dir = tempfile.mkdtemp(prefix="e2e_test_")
    yield temp_dir
    # 清理临时目录
    shutil.rmtree(temp_dir, ignore_errors=True)


async def cleanup_test_data():
    """清理测试数据"""
    # 实现测试数据清理逻辑


async def cleanup_test_cache():
    """清理测试缓存"""
    # 实现缓存清理逻辑


@pytest.fixture(scope="session")
def app_port():
    """获取应用端口"""
    return int(os.getenv("E2E_APP_PORT", "8000"))


@pytest.fixture(scope="session", autouse=True)
def init_e2e_sqlite():
    """初始化 e2e SQLite 数据库(只运行一次)。"""
    db_path = os.environ.get("SQLITE_PATH")
    if db_path and os.path.exists(db_path):
        os.remove(db_path)
    from core.db_engine import async_init_db

    asyncio.run(async_init_db())
    yield
    if db_path and os.path.exists(db_path):
        try:
            os.remove(db_path)
        except OSError:
            pass


# 跳过E2E测试的配置
def pytest_configure(config):
    """配置pytest"""
    config.addinivalue_line("markers", "e2e: marks tests as end-to-end tests")
    config.addinivalue_line("markers", "slow: marks tests as slow running")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")


# 并行测试配置
def pytest_addoption(parser):
    """添加pytest选项"""
    parser.addoption(
        "--e2e-parallel", action="store_true", default=False, help="run E2E tests in parallel"
    )


# Playwright fixtures for browser-based E2E tests
@pytest.fixture(scope="session")
async def browser() -> AsyncGenerator[Browser, None]:
    """浏览器fixture"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        yield browser
        await browser.close()


@pytest.fixture(scope="session")
async def context(browser: Browser) -> AsyncGenerator[BrowserContext, None]:
    """浏览器上下文fixture"""
    context = await browser.new_context(
        viewport={"width": 1920, "height": 1080}, ignore_https_errors=True
    )
    yield context
    await context.close()


@pytest.fixture
async def page(context: BrowserContext) -> AsyncGenerator[Page, None]:
    """页面fixture"""
    page = await context.new_page()
    yield page
    await page.close()


@pytest.fixture
def base_url():
    """基础URL"""
    return "http://localhost:8000"


@pytest.fixture
def api_base_url():
    """API基础URL"""
    return "http://localhost:8000/api/v1"
