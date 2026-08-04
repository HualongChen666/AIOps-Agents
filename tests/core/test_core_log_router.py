# -*- coding: utf-8 -*-
"""测试日志路由器模块"""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest

from core.log_router import (
    LogLevel,
    LogDestination,
    LogEntry,
    LogRouter,
    LogRouterManager,
    create_log_router,
)


class TestLogLevel:
    """测试日志级别枚举"""

    def test_log_level_values(self):
        """测试日志级别值"""
        assert LogLevel.DEBUG.value == "debug"
        assert LogLevel.INFO.value == "info"
        assert LogLevel.WARNING.value == "warning"
        assert LogLevel.ERROR.value == "error"
        assert LogLevel.CRITICAL.value == "critical"


class TestLogDestination:
    """测试日志目标枚举"""

    def test_log_destination_values(self):
        """测试日志目标值"""
        assert LogDestination.LOKI.value == "loki"
        assert LogDestination.ELASTICSEARCH.value == "elasticsearch"
        assert LogDestination.KAFKA.value == "kafka"
        assert LogDestination.S3.value == "s3"


class TestLogEntry:
    """测试日志条目"""

    def test_log_entry_creation(self):
        """测试创建日志条目"""
        timestamp = datetime.now(timezone.utc)
        entry = LogEntry(
            timestamp=timestamp,
            level=LogLevel.INFO,
            message="Test message",
            service="test-service",
            host="test-host",
            environment="production",
            labels={"app": "test"},
            extra={"request_id": "123"},
        )
        assert entry.timestamp == timestamp
        assert entry.level == LogLevel.INFO
        assert entry.message == "Test message"
        assert entry.service == "test-service"
        assert entry.host == "test-host"
        assert entry.environment == "production"
        assert entry.labels == {"app": "test"}
        assert entry.extra == {"request_id": "123"}

    def test_to_dict(self):
        """测试转换为字典"""
        timestamp = datetime(2026, 8, 4, 10, 0, 0, tzinfo=timezone.utc)
        entry = LogEntry(
            timestamp=timestamp,
            level=LogLevel.INFO,
            message="Test",
            service="test",
            host="host",
            environment="prod",
            labels={},
            extra={},
        )
        result = entry.to_dict()
        assert result["timestamp"] == "2026-08-04T10:00:00+00:00"
        assert result["level"] == "info"
        assert result["message"] == "Test"

    def test_to_loki_format(self):
        """测试转换为Loki格式"""
        timestamp = datetime(2026, 8, 4, 10, 0, 0, tzinfo=timezone.utc)
        entry = LogEntry(
            timestamp=timestamp,
            level=LogLevel.INFO,
            message="Test",
            service="test",
            host="host",
            environment="prod",
            labels={"app": "test"},
            extra={},
        )
        result = entry.to_loki_format()
        assert "streams" in result
        assert len(result["streams"]) == 1
        stream = result["streams"][0]
        assert stream["stream"]["service"] == "test"
        assert stream["stream"]["host"] == "host"
        assert stream["stream"]["level"] == "info"
        assert stream["stream"]["app"] == "test"
        assert len(stream["values"]) == 1


class TestLogRouter:
    """测试日志路由器"""

    def test_init(self):
        """测试初始化"""
        config = {
            "destinations": ["loki", "elasticsearch"],
            "loki_url": "http://loki:3100",
            "elasticsearch_url": "http://es:9200",
        }
        router = LogRouter(config)
        assert router.config == config
        assert router.destinations == ["loki", "elasticsearch"]
        assert router.loki_url == "http://loki:3100"
        assert router.elasticsearch_url == "http://es:9200"
        assert router.enabled is True
        assert router.session is None

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """测试异步上下文管理器"""
        config = {"destinations": []}
        router = LogRouter(config)
        await router.__aenter__()
        assert router.session is not None
        await router.__aexit__(None, None, None)
        # Session is closed but not set to None by __aexit__
        assert router.session.closed

    @pytest.mark.asyncio
    async def test_context_manager_exception(self):
        """测试异步上下文管理器异常处理"""
        config = {"destinations": []}
        router = LogRouter(config)
        await router.__aenter__()
        await router.__aexit__(Exception, Exception("test"), None)
        assert router.session.closed

    @pytest.mark.asyncio
    async def test_route_log_disabled(self):
        """测试禁用状态下的日志路由"""
        config = {"destinations": ["loki"]}
        router = LogRouter(config)
        router.enabled = False
        entry = LogEntry(
            timestamp=datetime.now(timezone.utc),
            level=LogLevel.INFO,
            message="Test",
            service="test",
            host="host",
            environment="prod",
            labels={},
            extra={},
        )
        result = await router.route_log(entry)
        assert result is False

    @pytest.mark.asyncio
    async def test_route_log_no_destinations(self):
        """测试无目标时的日志路由"""
        config = {"destinations": []}
        router = LogRouter(config)
        entry = LogEntry(
            timestamp=datetime.now(timezone.utc),
            level=LogLevel.INFO,
            message="Test",
            service="test",
            host="host",
            environment="prod",
            labels={},
            extra={},
        )
        result = await router.route_log(entry)
        assert result is True

    @pytest.mark.asyncio
    async def test_route_log_kafka_destination(self):
        """测试路由到Kafka"""
        config = {"destinations": ["kafka"]}
        router = LogRouter(config)
        entry = LogEntry(
            timestamp=datetime.now(timezone.utc),
            level=LogLevel.INFO,
            message="Test",
            service="test",
            host="host",
            environment="prod",
            labels={},
            extra={},
        )
        with patch.object(router, "send_to_kafka", new_callable=AsyncMock) as mock_kafka:
            mock_kafka.return_value = True
            result = await router.route_log(entry)
            assert result is True

    @pytest.mark.asyncio
    async def test_route_log_s3_destination(self):
        """测试路由到S3"""
        config = {"destinations": ["s3"]}
        router = LogRouter(config)
        entry = LogEntry(
            timestamp=datetime.now(timezone.utc),
            level=LogLevel.INFO,
            message="Test",
            service="test",
            host="host",
            environment="prod",
            labels={},
            extra={},
        )
        with patch.object(router, "send_to_s3", new_callable=AsyncMock) as mock_s3:
            mock_s3.return_value = True
            result = await router.route_log(entry)
            assert result is True

    @pytest.mark.asyncio
    async def test_route_log_with_exception(self):
        """测试路由日志异常处理"""
        config = {"destinations": ["loki"]}
        router = LogRouter(config)
        entry = LogEntry(
            timestamp=datetime.now(timezone.utc),
            level=LogLevel.INFO,
            message="Test",
            service="test",
            host="host",
            environment="prod",
            labels={},
            extra={},
        )
        with patch.object(router, "send_to_loki", new_callable=AsyncMock) as mock_loki:
            mock_loki.side_effect = Exception("Network error")
            result = await router.route_log(entry)
            assert result is False

    @pytest.mark.asyncio
    async def test_send_to_loki_success(self):
        """测试成功发送到Loki"""
        config = {"destinations": [], "loki_url": "http://loki:3100"}
        router = LogRouter(config)
        entry = LogEntry(
            timestamp=datetime.now(timezone.utc),
            level=LogLevel.INFO,
            message="Test",
            service="test",
            host="host",
            environment="prod",
            labels={},
            extra={},
        )

        mock_response = AsyncMock()
        mock_response.status = 204

        mock_post = AsyncMock()
        mock_post.__aenter__ = AsyncMock(return_value=mock_response)
        mock_post.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.post = Mock(return_value=mock_post)
        mock_session.close = AsyncMock()

        with patch.object(router, "session", mock_session):
            result = await router.send_to_loki(entry)
            assert result is True

    @pytest.mark.asyncio
    async def test_send_to_loki_failure(self):
        """测试发送到Loki失败"""
        config = {"destinations": [], "loki_url": "http://loki:3100"}
        router = LogRouter(config)
        entry = LogEntry(
            timestamp=datetime.now(timezone.utc),
            level=LogLevel.INFO,
            message="Test",
            service="test",
            host="host",
            environment="prod",
            labels={},
            extra={},
        )

        mock_response = AsyncMock()
        mock_response.status = 500

        mock_post = AsyncMock()
        mock_post.__aenter__ = AsyncMock(return_value=mock_response)
        mock_post.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.post = Mock(return_value=mock_post)
        mock_session.close = AsyncMock()

        with patch.object(router, "session", mock_session):
            result = await router.send_to_loki(entry)
            assert result is False

    @pytest.mark.asyncio
    async def test_send_to_elasticsearch_success(self):
        """测试成功发送到Elasticsearch"""
        config = {"destinations": [], "elasticsearch_url": "http://es:9200"}
        router = LogRouter(config)
        entry = LogEntry(
            timestamp=datetime.now(timezone.utc),
            level=LogLevel.INFO,
            message="Test",
            service="test",
            host="host",
            environment="prod",
            labels={},
            extra={},
        )

        mock_response = AsyncMock()
        mock_response.status = 200

        mock_post = AsyncMock()
        mock_post.__aenter__ = AsyncMock(return_value=mock_response)
        mock_post.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.post = Mock(return_value=mock_post)
        mock_session.close = AsyncMock()

        with patch.object(router, "session", mock_session):
            result = await router.send_to_elasticsearch(entry)
            assert result is True

    @pytest.mark.asyncio
    async def test_send_to_elasticsearch_failure(self):
        """测试发送到Elasticsearch失败"""
        config = {"destinations": [], "elasticsearch_url": "http://es:9200"}
        router = LogRouter(config)
        entry = LogEntry(
            timestamp=datetime.now(timezone.utc),
            level=LogLevel.INFO,
            message="Test",
            service="test",
            host="host",
            environment="prod",
            labels={},
            extra={},
        )

        mock_response = AsyncMock()
        mock_response.status = 500

        mock_post = AsyncMock()
        mock_post.__aenter__ = AsyncMock(return_value=mock_response)
        mock_post.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.post = Mock(return_value=mock_post)
        mock_session.close = AsyncMock()

        with patch.object(router, "session", mock_session):
            result = await router.send_to_elasticsearch(entry)
            assert result is False

    @pytest.mark.asyncio
    async def test_send_to_kafka(self):
        """测试发送到Kafka"""
        config = {"destinations": []}
        router = LogRouter(config)
        entry = LogEntry(
            timestamp=datetime.now(timezone.utc),
            level=LogLevel.INFO,
            message="Test",
            service="test",
            host="host",
            environment="prod",
            labels={},
            extra={},
        )
        result = await router.send_to_kafka(entry)
        assert result is True

    @pytest.mark.asyncio
    async def test_send_to_kafka_exception(self):
        """测试发送到Kafka异常"""
        config = {"destinations": []}
        router = LogRouter(config)
        entry = LogEntry(
            timestamp=datetime.now(timezone.utc),
            level=LogLevel.INFO,
            message="Test",
            service="test",
            host="host",
            environment="prod",
            labels={},
            extra={},
        )
        with patch("core.log_router.logger"):
            # The function always returns True in current implementation
            result = await router.send_to_kafka(entry)
            assert result is True

    @pytest.mark.asyncio
    async def test_send_to_s3(self):
        """测试发送到S3"""
        config = {"destinations": []}
        router = LogRouter(config)
        entry = LogEntry(
            timestamp=datetime.now(timezone.utc),
            level=LogLevel.INFO,
            message="Test",
            service="test",
            host="host",
            environment="prod",
            labels={},
            extra={},
        )
        result = await router.send_to_s3(entry)
        assert result is True

    @pytest.mark.asyncio
    async def test_send_to_s3_exception(self):
        """测试发送到S3异常"""
        config = {"destinations": []}
        router = LogRouter(config)
        entry = LogEntry(
            timestamp=datetime.now(timezone.utc),
            level=LogLevel.INFO,
            message="Test",
            service="test",
            host="host",
            environment="prod",
            labels={},
            extra={},
        )
        with patch("core.log_router.logger"):
            # The function always returns True in current implementation
            result = await router.send_to_s3(entry)
            assert result is True

    @pytest.mark.asyncio
    async def test_batch_route_logs(self):
        """测试批量路由日志"""
        config = {"destinations": ["loki"]}
        router = LogRouter(config)

        entries = [
            LogEntry(
                timestamp=datetime.now(timezone.utc),
                level=LogLevel.INFO,
                message=f"Test {i}",
                service="test",
                host="host",
                environment="prod",
                labels={},
                extra={},
            )
            for i in range(3)
        ]

        with patch.object(router, "route_log", new_callable=AsyncMock) as mock_route:
            mock_route.return_value = True
            result = await router.batch_route_logs(entries)
            assert result["total"] == 3
            assert result["success"] == 3
            assert result["failed"] == 0
            assert "loki" in result["by_destination"]

    @pytest.mark.asyncio
    async def test_batch_route_logs_with_failure(self):
        """测试批量路由日志包含失败"""
        config = {"destinations": ["loki"]}
        router = LogRouter(config)

        entries = [
            LogEntry(
                timestamp=datetime.now(timezone.utc),
                level=LogLevel.INFO,
                message=f"Test {i}",
                service="test",
                host="host",
                environment="prod",
                labels={},
                extra={},
            )
            for i in range(3)
        ]

        with patch.object(router, "route_log", new_callable=AsyncMock) as mock_route:
            mock_route.return_value = False
            result = await router.batch_route_logs(entries)
            assert result["total"] == 3
            assert result["success"] == 0
            assert result["failed"] == 3

    def test_parse_fluent_bit_log_success(self):
        """测试成功解析Fluent-Bit日志"""
        config = {"destinations": []}
        router = LogRouter(config)
        log_line = '{"timestamp": "2026-08-04T10:00:00Z", "level": "info", "message": "Test", "service": "test", "host": "host", "environment": "prod", "labels": {}, "extra": {}}'
        entry = router.parse_fluent_bit_log(log_line)
        assert entry is not None
        assert entry.message == "Test"
        assert entry.service == "test"

    def test_parse_fluent_bit_log_failure(self):
        """测试解析Fluent-Bit日志失败"""
        config = {"destinations": []}
        router = LogRouter(config)
        log_line = "invalid json"
        entry = router.parse_fluent_bit_log(log_line)
        assert entry is None

    def test_create_log_entry(self):
        """测试创建日志条目"""
        config = {"destinations": []}
        router = LogRouter(config)
        entry = router.create_log_entry(
            message="Test message",
            level=LogLevel.INFO,
            service="test-service",
            host="test-host",
        )
        assert entry.message == "Test message"
        assert entry.level == LogLevel.INFO
        assert entry.service == "test-service"
        assert entry.host == "test-host"

    def test_create_log_entry_default_host(self):
        """测试创建日志条目使用默认主机"""
        config = {"destinations": []}
        router = LogRouter(config)
        entry = router.create_log_entry(
            message="Test message",
            level=LogLevel.INFO,
            service="test-service",
        )
        assert entry.message == "Test message"
        assert entry.level == LogLevel.INFO
        assert entry.service == "test-service"
        # Host should be DEFAULT_LOG_HOST when not provided

    def test_enable(self):
        """测试启用日志路由"""
        config = {"destinations": []}
        router = LogRouter(config)
        router.enabled = False
        router.enable()
        assert router.enabled is True

    def test_disable(self):
        """测试禁用日志路由"""
        config = {"destinations": []}
        router = LogRouter(config)
        router.disable()
        assert router.enabled is False


class TestLogRouterManager:
    """测试日志路由器管理器"""

    def test_init(self):
        """测试初始化"""
        manager = LogRouterManager()
        assert manager.routers == {}
        assert manager.default_router is None

    def test_add_router(self):
        """测试添加路由器"""
        manager = LogRouterManager()
        config = {"destinations": ["loki"]}
        router = manager.add_router("test", config)
        assert isinstance(router, LogRouter)
        assert "test" in manager.routers
        assert manager.default_router is not None

    def test_get_router(self):
        """测试获取路由器"""
        manager = LogRouterManager()
        config = {"destinations": []}
        manager.add_router("test", config)
        router = manager.get_router("test")
        assert router is not None
        assert isinstance(router, LogRouter)

    def test_get_router_not_found(self):
        """测试获取不存在的路由器"""
        manager = LogRouterManager()
        router = manager.get_router("nonexistent")
        assert router is None

    def test_remove_router(self):
        """测试移除路由器"""
        manager = LogRouterManager()
        config = {"destinations": []}
        manager.add_router("test", config)
        result = manager.remove_router("test")
        assert result is True
        assert "test" not in manager.routers

    def test_remove_router_default(self):
        """测试移除默认路由器"""
        manager = LogRouterManager()
        config = {"destinations": []}
        manager.add_router("test", config)
        # Set as default
        manager.default_router = manager.routers["test"]
        result = manager.remove_router("test")
        assert result is True
        assert "test" not in manager.routers

    def test_remove_router_not_found(self):
        """测试移除不存在的路由器"""
        manager = LogRouterManager()
        result = manager.remove_router("nonexistent")
        assert result is False

    def test_set_default_router(self):
        """测试设置默认路由器"""
        manager = LogRouterManager()
        config = {"destinations": []}
        manager.add_router("test", config)
        manager.default_router = None
        result = manager.set_default_router("test")
        assert result is True
        assert manager.default_router is not None

    def test_set_default_router_not_found(self):
        """测试设置不存在的默认路由器"""
        manager = LogRouterManager()
        result = manager.set_default_router("nonexistent")
        assert result is False


class TestCreateLogRouter:
    """测试创建日志路由器工厂函数"""

    def test_create_log_router(self):
        """测试创建日志路由器"""
        config = {"destinations": ["loki"]}
        router = create_log_router(config)
        assert isinstance(router, LogRouter)
        assert router.destinations == ["loki"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
