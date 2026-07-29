# -*- coding: utf-8 -*-
# tests/conftest.py
# 测试配置和fixtures，提升测试稳定性
import os
import sys
import threading
from unittest.mock import Mock

import pytest

collect_ignore_glob = ["*_out.txt"]

# Force all threads created during tests to be daemon threads so that
# pytest-xdist worker processes can exit even when modules leave background
# threads running.
_original_thread_init = threading.Thread.__init__


def _patched_thread_init(self, *args, **kwargs):  # type: ignore[override]
    kwargs["daemon"] = True
    _original_thread_init(self, *args, **kwargs)


threading.Thread.__init__ = _patched_thread_init

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# pytest-xdist配置：确保测试在并行worker间正确运行
def pytest_configure(config):
    """配置pytest设置"""
    # 添加测试标记
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")
    config.addinivalue_line("markers", "e2e: marks tests as end-to-end tests")
    config.addinivalue_line("markers", "core: core functionality, always run")
    config.addinivalue_line("markers", "addons: requires ENABLE_ADDONS=true")

    # pytest-xdist配置
    if hasattr(config, "workerinput"):
        # 在worker进程中运行
        import logging

        logging.info(f"Running in worker process: {config.workerinput}")
    else:
        # 在主进程中运行
        import logging

        logging.info("Running in main process (controller)")


def pytest_collection_modifyitems(config, items):
    """自动给测试用例打 core / addons 标记。"""
    import pathlib
    import re

    root = pathlib.Path(__file__).parent
    ext_dir = root.parent / "extensions" / "addons"
    addon_names = set()
    if ext_dir.exists():
        for pack in ext_dir.iterdir():
            if pack.is_dir():
                addon_names.update(d.name for d in pack.iterdir() if d.is_dir())

    # 从 main.py ADDON_ROUTERS 解析 add-on api router 变量名，生成对应测试文件名
    addon_api_tests = set()
    main_py = root.parent / "main.py"
    if main_py.exists():
        text = main_py.read_text(encoding="utf-8")
        match = re.search(r"ADDON_ROUTERS\s*=\s*\[(.*?)\]", text, re.DOTALL)
        if match:
            addon_api_tests = {
                f"test_{name}.py"
                for name in re.findall(
                    r"^\s*\(\s*(\w+)\s*,\s*\w+\s*\)\s*,?$",
                    match.group(1),
                    re.MULTILINE,
                )
            }

    core_service_names = {
        "alert_service",
        "agent_orchestration_service",
        "repair_service",
        "audit_service",
    }

    for item in items:
        try:
            path = pathlib.Path(str(item.fspath))
            relpath = path.relative_to(root)
        except (ValueError, AttributeError):
            continue
        parts = relpath.parts
        mark = None
        if parts and parts[0] == "api":
            mark = "addons" if path.name in addon_api_tests else "core"
        elif parts and parts[0] in ("core", "e2e"):
            mark = "core"
        elif parts and (
            parts[0] == "addons"
            or (parts[0] == "services" and len(parts) > 1 and parts[1] in addon_names)
        ):
            mark = "addons"
        elif parts and parts[0] == "services" and len(parts) > 1 and parts[1] in core_service_names:
            mark = "core"
        if mark and mark not in item.keywords:
            item.add_marker(getattr(pytest.mark, mark))


def pytest_runtest_setup(item):
    """未启用 ENABLE_ADDONS 时跳过 addons 测试。"""
    if "addons" in item.keywords and os.getenv("ENABLE_ADDONS", "").lower() != "true":
        pytest.skip("ENABLE_ADDONS is not true")


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """设置测试环境"""
    # 清理之前的缓存数据
    if "core.cache_helpers_mock" in sys.modules:
        from core.cache_helpers_mock import _cache_metadata, _cache_store

        _cache_store.clear()
        _cache_metadata.clear()

    # 初始化全局mock管理器和监控器
    from tests.mock_manager import get_mock_manager, get_mock_monitor

    mock_manager = get_mock_manager()
    mock_monitor = get_mock_monitor()

    yield

    # 测试结束后清理
    if "core.cache_helpers_mock" in sys.modules:
        from core.cache_helpers_mock import _cache_metadata, _cache_store

        _cache_store.clear()
        _cache_metadata.clear()

    # 生成最终监控报告
    try:
        import os

        from tests.mock_manager import MockConfigs, MockCoverageReporter

        # 获取所有预定义配置
        registered_mocks = {}
        config_methods = [
            "get_ai_analyze_config",
            "get_alert_service_config",
            "get_health_check_config",
            "get_database_config",
            "get_cache_config",
            "get_auth_config",
            "get_workflow_service_config",
            "get_topology_service_config",
            "get_audit_service_config",
            "get_user_service_config",
            "get_config_service_config",
            "get_notification_service_config",
            "get_storage_service_config",
            "get_monitoring_service_config",
            "get_security_service_config",
            "get_plugin_service_config",
        ]

        for method_name in config_methods:
            method = getattr(MockConfigs, method_name)
            config = method()
            service_name = method_name.replace("get_", "").replace("_config", "")
            registered_mocks[service_name] = config

        # 生成报告
        reporter = MockCoverageReporter(mock_monitor)
        report = reporter.generate_coverage_report(registered_mocks, output_format="text")

        # 保存报告
        report_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "reports")
        os.makedirs(report_dir, exist_ok=True)

        report_file = os.path.join(report_dir, "mock_coverage_report.txt")
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"\nMock coverage report saved to: {report_file}")

    except Exception as e:
        import logging

        logging.warning(f"Failed to generate mock coverage report: {e}")

    # 清理mock管理器和监控器
    mock_manager.cleanup()
    from tests.mock_manager import reset_global_mock_manager, reset_global_mock_monitor

    reset_global_mock_manager()
    reset_global_mock_monitor()


# pytest-xdist worker_id fixture
@pytest.fixture(scope="session")
def worker_id(request):
    """获取当前worker的ID（用于pytest-xdist并行测试）"""
    if hasattr(request.config, "workerinput"):
        return request.config.workerinput["workerid"]
    else:
        return "master"


# pytest-xdist worker_count fixture
@pytest.fixture(scope="session")
def worker_count(request):
    """获取worker总数（用于pytest-xdist并行测试）"""
    if hasattr(request.config, "workerinput"):
        return request.config.workerinput["workercount"]
    else:
        return 1


@pytest.fixture
def mock_ai_analyze():
    """AI分析的统一mock - 使用新的mock管理器"""
    from unittest.mock import AsyncMock

    from tests.mock_manager import MockConfigs, create_stable_mock  # noqa: F401

    config = MockConfigs.get_ai_analyze_config()
    mock = AsyncMock(return_value=config["return_value"])
    return mock


@pytest.fixture
def mock_alert_service():
    """告警服务的统一mock - 使用新的mock管理器"""
    from tests.mock_manager import MockConfigs, create_service_mock

    config = MockConfigs.get_alert_service_config()
    mock = create_service_mock("alert_service", config, is_async=False)
    return mock


@pytest.fixture
def mock_health_check():
    """健康检查的统一mock - 使用新的mock管理器"""
    from unittest.mock import AsyncMock

    from tests.mock_manager import MockConfigs, create_service_mock

    config = MockConfigs.get_health_check_config()
    mock = create_service_mock("health_check", config, is_async=False)
    # 特别处理异步方法
    mock.perform_health_checks = AsyncMock(return_value=config["perform_health_checks"])
    return mock


@pytest.fixture
def sample_alert_data():
    """示例告警数据"""
    return {
        "id": 1,
        "title": "CPU使用率过高",
        "severity": "critical",
        "description": "CPU使用率超过90%",
        "timestamp": "2024-01-01T00:00:00Z",
    }


@pytest.fixture
def sample_ai_request():
    """示例AI请求"""
    return {
        "query": "CPU使用率飙升，请分析根因",
        "include_metrics": False,
        "platform": "windows",
        "include_rich_context": False,
    }


# 添加测试超时 - Windows兼容版本
@pytest.fixture(autouse=True)
def timeout_protection():
    """测试超时保护（Windows兼容版本）"""
    # Windows不支持SIGALRM，使用pytest-timeout插件
    yield


# 重试装饰器
def retry_on_failure(max_retries=3, delay=1):
    """测试重试装饰器"""

    def decorator(test_func):
        def wrapper(*args, **kwargs):
            import time

            last_exception = None

            for attempt in range(max_retries):
                try:
                    return test_func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        time.sleep(delay)
                    else:
                        raise last_exception

        return wrapper

    return decorator


# 测试数据清理工具
class TestDataCleaner:
    """测试数据清理工具"""

    @staticmethod
    def clear_all_caches():
        """清理所有缓存"""
        if "core.cache_helpers_mock" in sys.modules:
            from core.cache_helpers_mock import _cache_metadata, _cache_store

            _cache_store.clear()
            _cache_metadata.clear()

    @staticmethod
    def clear_message_queues():
        """清理所有消息队列"""
        if "core.message_queue_mock" in sys.modules:
            # 消息队列mock会自动清理
            pass

    @staticmethod
    def clear_all():
        """清理所有测试数据"""
        TestDataCleaner.clear_all_caches()
        TestDataCleaner.clear_message_queues()


@pytest.fixture(autouse=True)
def clean_test_data():
    """每个测试后自动清理数据"""
    yield
    TestDataCleaner.clear_all()


@pytest.fixture(autouse=True)
def reset_mocks_between_tests():
    """每个测试后自动重置mock状态"""
    from tests.mock_manager import get_mock_manager

    yield
    # 重置所有mock状态，避免测试间相互影响
    try:
        mock_manager = get_mock_manager()
        mock_manager.reset_all_mocks()
    except Exception as e:
        # 如果重置失败，记录警告但不中断测试
        import logging

        logging.warning(f"Failed to reset mocks between tests: {e}")


# 测试性能监控
class PerformanceMonitor:
    """测试性能监控"""

    def __init__(self):
        self.test_times = {}

    def record_test_time(self, test_name, duration):
        """记录测试执行时间"""
        if test_name not in self.test_times:
            self.test_times[test_name] = []
        self.test_times[test_name].append(duration)

    def get_average_time(self, test_name):
        """获取测试平均执行时间"""
        if test_name in self.test_times and self.test_times[test_name]:
            return sum(self.test_times[test_name]) / len(self.test_times[test_name])
        return 0


@pytest.fixture(scope="session")
def performance_monitor():
    """性能监控fixture"""
    return PerformanceMonitor()


@pytest.fixture
def mock_logger():
    """Mock logger fixture - 使用新的mock管理器"""
    from tests.mock_manager import create_service_mock

    config = {
        "info": Mock(),
        "error": Mock(),
        "warning": Mock(),
        "debug": Mock(),
        "critical": Mock(),
    }
    mock = create_service_mock("logger", config, is_async=False)
    return mock


@pytest.fixture
def mock_config():
    """Mock配置fixture - 使用新的mock管理器"""
    from tests.mock_manager import create_service_mock

    config = {
        "get": Mock(return_value="test_value"),
        "set": Mock(return_value=True),
        "get_int": Mock(return_value=42),
        "get_bool": Mock(return_value=True),
        "get_list": Mock(return_value=["item1", "item2"]),
    }
    mock = create_service_mock("config", config, is_async=False)
    return mock


@pytest.fixture
def mock_database():
    """Mock数据库fixture - 使用新的mock管理器"""
    from tests.mock_manager import MockConfigs, create_service_mock

    config = MockConfigs.get_database_config()
    mock = create_service_mock("database", config, is_async=False)
    return mock


@pytest.fixture
def mock_cache():
    """Mock缓存fixture - 使用新的mock管理器"""
    from tests.mock_manager import MockConfigs, create_service_mock

    config = MockConfigs.get_cache_config()
    mock = create_service_mock("cache", config, is_async=False)
    return mock


@pytest.fixture
def mock_auth():
    """Mock认证fixture - 使用新的mock管理器"""
    from tests.mock_manager import MockConfigs, create_service_mock

    config = MockConfigs.get_auth_config()
    mock = create_service_mock("auth", config, is_async=False)
    return mock


# 异步mock专用fixtures
@pytest.fixture
def async_mock_ai_analyze():
    """异步AI分析的统一mock"""
    from unittest.mock import AsyncMock

    from tests.mock_manager import MockConfigs

    config = MockConfigs.get_ai_analyze_config()
    mock = AsyncMock(return_value=config["return_value"])
    return mock


@pytest.fixture
def async_mock_database():
    """异步数据库mock"""
    from unittest.mock import AsyncMock

    mock = AsyncMock()
    mock.fetchone = AsyncMock(return_value=None)
    mock.fetchall = AsyncMock(return_value=[])
    mock.execute = AsyncMock(return_value=AsyncMock(rowcount=1))
    mock.commit = AsyncMock()
    mock.rollback = AsyncMock()
    return mock


@pytest.fixture
def async_mock_cache():
    """异步缓存mock"""
    from unittest.mock import AsyncMock

    mock = AsyncMock()
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=True)
    mock.exists = AsyncMock(return_value=False)
    mock.clear = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def async_mock_message_queue():
    """异步消息队列mock"""
    from unittest.mock import AsyncMock

    mock = AsyncMock()
    mock.publish = AsyncMock(return_value=True)
    mock.consume = AsyncMock()
    mock.ack_message = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def app():
    """FastAPI应用实例fixture"""
    try:
        from main import app

        return app
    except ImportError:
        # 如果main.py无法导入，创建一个测试用的FastAPI应用
        from fastapi import FastAPI

        test_app = FastAPI()
        return test_app


@pytest.fixture
async def client(app):
    """TestClient fixture用于测试FastAPI应用"""
    from httpx import ASGITransport, AsyncClient

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def authenticated_client(app):
    """带认证的TestClient fixture"""
    from httpx import ASGITransport, AsyncClient

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "Bearer test_token"},
    ) as ac:
        yield ac


class HTTPClientUtils:
    """HTTP客户端工具类"""

    @staticmethod
    def assert_response_status(response, expected_status):
        """断言响应状态码"""
        assert response.status_code == expected_status, (
            f"Expected status {expected_status}, got {response.status_code}. "
            f"Response: {response.text}"
        )

    @staticmethod
    def assert_response_contains(response, text):
        """断言响应包含指定文本"""
        assert text in response.text, f"Expected response to contain '{text}', got: {response.text}"

    @staticmethod
    def assert_response_json(response, expected_json):
        """断言响应JSON匹配"""
        assert (
            response.json() == expected_json
        ), f"Expected JSON {expected_json}, got {response.json()}"


@pytest.fixture
def http_client_utils():
    """HTTP客户端工具fixture"""
    return HTTPClientUtils()


@pytest.fixture(scope="function")
async def test_db_engine():
    """测试数据库引擎fixture（使用SQLite内存数据库）"""
    from sqlalchemy.ext.asyncio import create_async_engine

    # 使用SQLite内存数据库进行测试
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False, future=True)

    yield engine

    # 清理
    await engine.dispose()


@pytest.fixture(scope="function")
async def test_db_session(test_db_engine):
    """测试数据库会话fixture"""
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import sessionmaker

    async_session = sessionmaker(test_db_engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        yield session


@pytest.fixture(scope="function")
async def test_redis_client():
    """测试Redis客户端fixture（使用fakeredis模拟）"""
    try:
        import fakeredis.aio

        # 使用fakeredis模拟Redis
        redis_client = fakeredis.aio.FakeRedis(decode_responses=True)
        yield redis_client
        # 清理
        await redis_client.flushall()
        await redis_client.close()
    except ImportError:
        # 如果fakeredis不可用，使用轻量级内存异步Redis fake
        import asyncio

        class AsyncFakeRedis:
            """轻量级异步内存Redis fake，支持get/set/delete/exists/flushall/close。"""

            def __init__(self):
                self._data: dict[str, str] = {}
                self._lock = asyncio.Lock()

            async def get(self, key: str):
                async with self._lock:
                    return self._data.get(key)

            async def set(self, key: str, value: str, *args, **kwargs):
                async with self._lock:
                    self._data[key] = str(value)
                return True

            async def delete(self, key: str):
                async with self._lock:
                    return 1 if self._data.pop(key, None) is not None else 0

            async def exists(self, key: str):
                async with self._lock:
                    return 1 if key in self._data else 0

            async def flushall(self):
                async with self._lock:
                    self._data.clear()
                return True

            async def close(self):
                pass

        redis_client = AsyncFakeRedis()
        yield redis_client
        await redis_client.flushall()
        await redis_client.close()
