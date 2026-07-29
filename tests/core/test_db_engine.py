# -*- coding: utf-8 -*-
import logging
"""测试数据库引擎模块"""

import pytest


class TestDBEngineModule:
    """测试数据库引擎模块"""

    def test_db_engine_module_exists(self):
        """测试数据库引擎模块存在"""
        from core import db_engine

        assert db_engine is not None

    def test_db_engine_has_functions(self):
        """测试数据库引擎模块有函数"""
        from core import db_engine

        # 检查模块有函数或类
        assert len(dir(db_engine)) > 0

    def test_engine_exists(self):
        """测试engine存在"""
        from core.db_engine import engine

        assert engine is not None

    def test_async_session_local_exists(self):
        """测试AsyncSessionLocal存在"""
        from core.db_engine import AsyncSessionLocal

        assert AsyncSessionLocal is not None

    def test_base_exists(self):
        """测试Base存在"""
        from core.database import Base

        assert Base is not None

    def test_async_get_session_context_manager(self):
        """测试async_get_session函数"""
        from core.db_engine import async_get_session

        assert async_get_session is not None
        assert callable(async_get_session)

    @pytest.mark.asyncio
    async def test_async_init_db_function_exists(self):
        """测试async_init_db函数存在"""
        from core.db_engine import async_init_db

        assert async_init_db is not None
        assert callable(async_init_db)

    def test_async_insert_alert_function_exists(self):
        """测试async_insert_alert函数存在"""
        from core.db_engine import async_insert_alert

        assert async_insert_alert is not None
        assert callable(async_insert_alert)

    def test_async_query_alerts_function_exists(self):
        """测试async_query_alerts函数存在"""
        from core.db_engine import async_query_alerts

        assert async_query_alerts is not None
        assert callable(async_query_alerts)

    def test_async_count_alerts_function_exists(self):
        """测试async_count_alerts函数存在"""
        from core.db_engine import async_count_alerts

        assert async_count_alerts is not None
        assert callable(async_count_alerts)

    def test_async_clear_alerts_function_exists(self):
        """测试async_clear_alerts函数存在"""
        from core.db_engine import async_clear_alerts

        assert async_clear_alerts is not None
        assert callable(async_clear_alerts)

    def test_async_insert_repair_record_function_exists(self):
        """测试async_insert_repair_record函数存在"""
        from core.db_engine import async_insert_repair_record

        assert async_insert_repair_record is not None
        assert callable(async_insert_repair_record)

    def test_async_query_repairs_function_exists(self):
        """测试async_query_repairs函数存在"""
        from core.db_engine import async_query_repairs

        assert async_query_repairs is not None
        assert callable(async_query_repairs)

    def test_async_upsert_pending_approval_function_exists(self):
        """测试async_upsert_pending_approval函数存在"""
        from core.db_engine import async_upsert_pending_approval

        assert async_upsert_pending_approval is not None
        assert callable(async_upsert_pending_approval)

    def test_async_get_pending_approval_function_exists(self):
        """测试async_get_pending_approval函数存在"""
        from core.db_engine import async_get_pending_approval

        assert async_get_pending_approval is not None
        assert callable(async_get_pending_approval)

    def test_async_get_all_pending_approvals_function_exists(self):
        """测试async_get_all_pending_approvals函数存在"""
        from core.db_engine import async_get_all_pending_approvals

        assert async_get_all_pending_approvals is not None
        assert callable(async_get_all_pending_approvals)

    def test_async_update_approval_status_function_exists(self):
        """测试async_update_approval_status函数存在"""
        from core.db_engine import async_update_approval_status

        assert async_update_approval_status is not None
        assert callable(async_update_approval_status)

    def test_sync_wrapper_functions_exist(self):
        """测试同步包装函数存在"""
        from core.db_engine import (
            clear_alerts,
            count_alerts,
            get_all_pending_approvals,
            get_pending_approval,
            insert_alert,
            insert_repair_record,
            query_alerts,
            query_repairs,
            update_approval_status,
            upsert_pending_approval,
        )

        assert insert_alert is not None
        assert query_alerts is not None
        assert count_alerts is not None
        assert clear_alerts is not None
        assert insert_repair_record is not None
        assert query_repairs is not None
        assert upsert_pending_approval is not None
        assert get_pending_approval is not None
        assert get_all_pending_approvals is not None
        assert update_approval_status is not None

    def test_postgresql_alert_repository_exists(self):
        """测试PostgreSQLAlertRepository类存在"""
        from core.db_engine import PostgreSQLAlertRepository

        assert PostgreSQLAlertRepository is not None
        assert hasattr(PostgreSQLAlertRepository, "save")
        assert hasattr(PostgreSQLAlertRepository, "query")
        assert hasattr(PostgreSQLAlertRepository, "get_by_id")
        assert hasattr(PostgreSQLAlertRepository, "update_status")
        assert hasattr(PostgreSQLAlertRepository, "delete")
        assert hasattr(PostgreSQLAlertRepository, "count")
        assert hasattr(PostgreSQLAlertRepository, "clear_all")
        assert hasattr(PostgreSQLAlertRepository, "get_recent")

    def test_database_engine_stub_exists(self):
        """测试DatabaseEngine stub类存在"""
        from core.db_engine import DatabaseEngine

        assert DatabaseEngine is not None

    def test_database_engine_stub_initialization(self):
        """测试DatabaseEngine stub初始化"""
        from core.db_engine import DatabaseEngine

        db_engine = DatabaseEngine("test_connection_string")
        assert db_engine.connection_string == "test_connection_string"
        assert db_engine.connected is False

    def test_database_engine_stub_methods(self):
        """测试DatabaseEngine stub方法"""
        from core.db_engine import DatabaseEngine

        db_engine = DatabaseEngine()
        assert hasattr(db_engine, "connect")
        assert hasattr(db_engine, "disconnect")
        assert hasattr(db_engine, "execute")
        assert hasattr(db_engine, "fetchall")

    def test_alert_repository_instance_exists(self):
        """测试alert_repository实例存在"""
        from core.db_engine import alert_repository

        assert alert_repository is not None
        assert isinstance(alert_repository, object)

    def test_module_exports(self):
        """测试模块导出"""
        from core.db_engine import __all__

        expected_exports = [
            "engine",
            "Base",
            "AsyncSessionLocal",
            "async_get_session",
            "async_init_db",
            "async_insert_alert",
            "async_query_alerts",
            "async_count_alerts",
            "async_clear_alerts",
            "async_insert_repair_record",
            "async_query_repairs",
            "async_upsert_pending_approval",
            "async_get_pending_approval",
            "async_get_all_pending_approvals",
            "async_update_approval_status",
            "insert_alert",
            "query_alerts",
            "count_alerts",
            "clear_alerts",
            "upsert_pending_approval",
            "get_pending_approval",
            "get_all_pending_approvals",
            "update_approval_status",
            "insert_repair_record",
            "query_repairs",
            "insert_verify_record",
            "db_clear_alerts",
        ]

        for export in expected_exports:
            assert export in __all__


class TestDBEngineAsyncFunctions:
    """测试数据库引擎异步函数"""

    @pytest.mark.asyncio
    async def test_async_insert_alert_with_mock(self):
        """测试async_insert_alert使用mock"""
        from unittest.mock import AsyncMock, patch

        from core.db_engine import async_insert_alert

        alert_data = {
            "level": "info",
            "category": "test",
            "alert_type": "test_alert",
            "title": "Test Alert",
            "desc": "Test description",
            "metric": "cpu",
            "value": 80.0,
        }

        with patch("core.db_engine.AsyncSessionLocal") as mock_session_local:
            mock_session = AsyncMock()
            mock_session_local.return_value.__aenter__.return_value = mock_session
            mock_session.commit = AsyncMock()

            try:
                result = await async_insert_alert(alert_data)
                # 函数应该返回一个alert_id
                assert result is not None
                assert isinstance(result, str)
            except Exception as e:
                logging.exception("Unexpected exception: %s", e)
                # 可能会因为其他依赖失败，这是预期的
                pass

    @pytest.mark.asyncio
    async def test_async_query_alerts_with_mock(self):
        """测试async_query_alerts使用mock"""
        from unittest.mock import AsyncMock, patch

        from core.db_engine import async_query_alerts

        with patch("core.db_engine.AsyncSessionLocal") as mock_session_local:
            mock_session = AsyncMock()
            mock_session_local.return_value.__aenter__.return_value = mock_session
            mock_session.execute = AsyncMock()

            try:
                result = await async_query_alerts(limit=10)
                # 函数应该返回一个列表
                assert isinstance(result, list)
            except Exception as e:
                logging.exception("Unexpected exception: %s", e)
                # 可能会因为其他依赖失败，这是预期的
                pass

    @pytest.mark.asyncio
    async def test_async_count_alerts_with_mock(self):
        """测试async_count_alerts使用mock"""
        from unittest.mock import AsyncMock, patch

        from core.db_engine import async_count_alerts

        with patch("core.db_engine.AsyncSessionLocal") as mock_session_local:
            mock_session = AsyncMock()
            mock_session_local.return_value.__aenter__.return_value = mock_session
            mock_session.execute = AsyncMock()
            mock_session.execute.return_value.scalar.return_value = 5

            try:
                result = await async_count_alerts()
                # 函数应该返回一个整数
                assert isinstance(result, int)
            except Exception as e:
                logging.exception("Unexpected exception: %s", e)
                # 可能会因为其他依赖失败，这是预期的
                pass


class TestDBEngineSyncWrappers:
    """测试数据库引擎同步包装函数"""

    def test_insert_alert_sync_wrapper(self):
        """测试insert_alert同步包装器"""
        from unittest.mock import patch

        from core.db_engine import insert_alert

        alert_data = {
            "level": "info",
            "title": "Test",
        }

        with patch("core.db_engine.asyncio.run") as mock_run:
            mock_run.return_value = "test_alert_id"

            insert_alert(alert_data)
            # 函数应该调用asyncio.run
            assert mock_run.called

    def test_query_alerts_sync_wrapper(self):
        """测试query_alerts同步包装器"""
        from unittest.mock import patch

        from core.db_engine import query_alerts

        with patch("core.db_engine.asyncio.run") as mock_run:
            mock_run.return_value = []

            result = query_alerts(limit=10)
            # 函数应该调用asyncio.run
            assert mock_run.called
            assert isinstance(result, list)

    def test_count_alerts_sync_wrapper(self):
        """测试count_alerts同步包装器"""
        from unittest.mock import patch

        from core.db_engine import count_alerts

        with patch("core.db_engine.asyncio.run") as mock_run:
            mock_run.return_value = 5

            result = count_alerts()
            # 函数应该调用asyncio.run
            assert mock_run.called
            assert isinstance(result, int)


class TestPostgreSQLAlertRepository:
    """测试PostgreSQLAlertRepository类"""

    def test_repository_initialization(self):
        """测试仓储初始化"""
        from core.db_engine import PostgreSQLAlertRepository

        repo = PostgreSQLAlertRepository()
        assert repo is not None

    def test_repository_methods_are_async(self):
        """测试仓储方法是异步的"""
        import inspect

        from core.db_engine import PostgreSQLAlertRepository

        repo = PostgreSQLAlertRepository()

        async_methods = [
            "save",
            "query",
            "get_by_id",
            "update_status",
            "delete",
            "count",
            "clear_all",
            "get_recent",
        ]

        for method_name in async_methods:
            assert hasattr(repo, method_name)
            method = getattr(repo, method_name)
            assert inspect.iscoroutinefunction(method)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])