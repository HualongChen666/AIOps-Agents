# -*- coding: utf-8 -*-
# tests/test_audit_service.py
# 🔧 P0-7: 审计日志服务单元测试

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.audit_service import AuditService, audit_context


class TestAuditService:
    """审计日志服务测试"""

    @pytest.mark.asyncio
    async def test_log_action_success(self):
        """测试记录审计日志 - 成功"""
        with patch("core.audit_service.AsyncSessionLocal") as mock_session_factory:
            mock_session = AsyncMock()
            mock_session.add = MagicMock()
            mock_session.commit = AsyncMock()
            mock_session.refresh = AsyncMock()
            mock_log = MagicMock()
            mock_log.id = 1
            mock_session.refresh.return_value = mock_log
            mock_session.__aenter__.return_value = mock_session
            mock_session.__aexit__.return_value = None
            mock_session_factory.return_value = mock_session

            log_id = await AuditService.log_action(
                action="test_action",
                resource_type="test_resource",
                username="testuser",
                status="success",
            )

            assert log_id is not None
            assert log_id == 1

    @pytest.mark.asyncio
    async def test_log_action_failure(self):
        """测试记录审计日志 - 失败"""
        with patch("core.audit_service.AsyncSessionLocal") as mock_session_factory:
            mock_session = AsyncMock()
            mock_session.add = MagicMock()
            mock_session.commit = AsyncMock(side_effect=Exception("DB error"))
            mock_session.__aenter__.return_value = mock_session
            mock_session.__aexit__.return_value = None
            mock_session_factory.return_value = mock_session

            log_id = await AuditService.log_action(
                action="test_action",
                resource_type="test_resource",
            )

            assert log_id is None

    @pytest.mark.asyncio
    async def test_get_audit_logs(self):
        """测试查询审计日志"""
        with patch("core.audit_service.AsyncSessionLocal") as mock_session_factory:
            mock_session = AsyncMock()
            mock_log = MagicMock()
            mock_log.id = 1
            mock_log.action = "test_action"
            mock_log.resource_type = "test_resource"
            mock_log.resource_id = "123"
            mock_log.user_id = 1
            mock_log.username = "testuser"
            mock_log.ip_address = "127.0.0.1"
            mock_log.status = "success"
            mock_log.details = "Test details"
            mock_log.metadata = {"key": "value"}
            mock_log.created_at = datetime.now()

            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = [mock_log]
            mock_session.execute = AsyncMock(return_value=mock_result)
            mock_session.__aenter__.return_value = mock_session
            mock_session.__aexit__.return_value = None
            mock_session_factory.return_value = mock_session

            logs = await AuditService.get_audit_logs(limit=10)

            assert len(logs) == 1
            assert logs[0]["action"] == "test_action"
            assert logs[0]["username"] == "testuser"

    @pytest.mark.asyncio
    async def test_get_audit_logs_with_filters(self):
        """测试查询审计日志 - 带过滤条件"""
        with patch("core.audit_service.AsyncSessionLocal") as mock_session_factory:
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = []
            mock_session.execute = AsyncMock(return_value=mock_result)
            mock_session.__aenter__.return_value = mock_session
            mock_session.__aexit__.return_value = None
            mock_session_factory.return_value = mock_session

            logs = await AuditService.get_audit_logs(
                action="login",
                resource_type="user",
                username="testuser",
            )

            assert isinstance(logs, list)

    @pytest.mark.asyncio
    async def test_count_audit_logs(self):
        """测试统计审计日志数量"""
        with patch("core.audit_service.AsyncSessionLocal") as mock_session_factory:
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalar.return_value = 100
            mock_session.execute = AsyncMock(return_value=mock_result)
            mock_session.__aenter__.return_value = mock_session
            mock_session.__aexit__.return_value = None
            mock_session_factory.return_value = mock_session

            count = await AuditService.count_audit_logs()

            assert count == 100

    @pytest.mark.asyncio
    async def test_get_user_activity_summary(self):
        """测试获取用户活动摘要"""
        with patch("core.audit_service.AsyncSessionLocal") as mock_session_factory:
            mock_session = AsyncMock()

            # Mock total count
            mock_total_result = MagicMock()
            mock_total_result.scalar.return_value = 50
            mock_session.execute.return_value = mock_total_result
            mock_session.__aenter__.return_value = mock_session
            mock_session.__aexit__.return_value = None
            mock_session_factory.return_value = mock_session

            summary = await AuditService.get_user_activity_summary("testuser", days=30)

            assert summary["username"] == "testuser"
            assert summary["period_days"] == 30
            assert "total_actions" in summary

    @pytest.mark.asyncio
    async def test_cleanup_old_logs(self):
        """测试清理旧审计日志"""
        with patch("core.audit_service.AsyncSessionLocal") as mock_session_factory:
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.rowcount = 100
            mock_session.execute = AsyncMock(return_value=mock_result)
            mock_session.commit = AsyncMock()
            mock_session.__aenter__.return_value = mock_session
            mock_session.__aexit__.return_value = None
            mock_session_factory.return_value = mock_session

            count = await AuditService.cleanup_old_logs(days_to_keep=90)

            assert count == 100


class TestAuditContext:
    """审计上下文管理器测试"""

    @pytest.mark.asyncio
    async def test_audit_context_success(self):
        """测试审计上下文 - 成功"""
        with patch("core.audit_service.audit_service") as mock_audit_service:
            mock_audit_service.log_action = AsyncMock()

            async with audit_context(
                action="test_action",
                resource_type="test_resource",
                username="testuser",
            ):
                pass

            mock_audit_service.log_action.assert_called_once()
            call_args = mock_audit_service.log_action.call_args
            assert call_args[1]["status"] == "success"

    @pytest.mark.asyncio
    async def test_audit_context_failure(self):
        """测试审计上下文 - 失败"""
        with patch("core.audit_service.audit_service") as mock_audit_service:
            mock_audit_service.log_action = AsyncMock()

            with pytest.raises(ValueError):
                async with audit_context(
                    action="test_action",
                    resource_type="test_resource",
                    username="testuser",
                ):
                    raise ValueError("Test error")

            mock_audit_service.log_action.assert_called_once()
            call_args = mock_audit_service.log_action.call_args
            assert call_args[1]["status"] == "failure"
            assert "Test error" in call_args[1]["details"]
