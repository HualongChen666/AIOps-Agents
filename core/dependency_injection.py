# -*- coding: utf-8 -*-
"""
Dependency Injection Container
依赖注入容器

提供轻量级的依赖注入功能，解决循环依赖问题，不修改现有架构。
"""

import asyncio
import inspect
import logging
from contextvars import ContextVar
from functools import wraps
from typing import Any, Callable, Dict, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ServiceLifecycle:
    """服务生命周期管理"""

    async def initialize(self) -> None:
        """初始化服务"""
        import logging

        logging.getLogger(__name__).info(f"{__name__}.initialize invoked")
        return None

    async def shutdown(self, instance: Any) -> None:
        """关闭服务"""
        import logging

        logging.getLogger(__name__).info(f"{__name__}.shutdown invoked")
        return None


class DIContainer:
    """依赖注入容器"""

    def __init__(self):
        """初始化依赖注入容器"""
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}
        self._singletons: Dict[str, bool] = {}
        self._lifecycle: Dict[str, ServiceLifecycle] = {}
        self._context: ContextVar[Dict[str, Any]] = ContextVar("di_context", default={})

    def register_factory(
        self,
        name: str,
        factory: Callable,
        singleton: bool = True,
        lifecycle: Optional[ServiceLifecycle] = None,
    ):
        """
        注册服务工厂

        Args:
            name: 服务名称
            factory: 工厂函数
            singleton: 是否单例
            lifecycle: 生命周期管理器
        """
        self._factories[name] = factory
        self._singletons[name] = singleton
        if lifecycle:
            self._lifecycle[name] = lifecycle
        logger.info(f"Registered factory: {name} (singleton={singleton})")

    def register_instance(self, name: str, instance: Any):
        """
        注册服务实例

        Args:
            name: 服务名称
            instance: 服务实例
        """
        self._services[name] = instance
        self._singletons[name] = True
        logger.info(f"Registered instance: {name}")

    def get(self, name: str) -> Any:
        """
        获取服务实例

        Args:
            name: 服务名称

        Returns:
            服务实例

        Raises:
            KeyError: 服务未注册
        """
        # 检查上下文中的实例
        context = self._context.get({})
        if name in context:
            return context[name]

        # 检查是否已创建
        if name in self._services and self._singletons[name]:
            return self._services[name]

        # 使用工厂创建
        if name in self._factories:
            factory = self._factories[name]

            # 如果是单例且已创建，直接返回
            if self._singletons[name] and name in self._services:
                return self._services[name]

            # 创建新实例
            instance = factory()

            # 如果是单例，缓存实例
            if self._singletons[name]:
                self._services[name] = instance

            logger.debug(f"Created instance: {name}")
            return instance

        raise KeyError(f"Service not registered: {name}")

    def get_async(self, name: str) -> Any:
        """
        异步获取服务实例

        Args:
            name: 服务名称

        Returns:
            服务实例

        Raises:
            KeyError: 服务未注册
        """
        # 检查上下文中的实例
        context = self._context.get({})
        if name in context:
            return context[name]

        # 检查是否已创建
        if name in self._services and self._singletons[name]:
            return self._services[name]

        # 使用工厂创建
        if name in self._factories:
            factory = self._factories[name]

            # 如果是单例且已创建，直接返回
            if self._singletons[name] and name in self._services:
                return self._services[name]

            # 创建新实例
            instance = factory()

            # 如果有生命周期管理器，初始化
            if name in self._lifecycle:
                if inspect.iscoroutinefunction(instance.initialize):
                    asyncio.create_task(instance.initialize())
                else:
                    instance.initialize()

            # 如果是单例，缓存实例
            if self._singletons[name]:
                self._services[name] = instance

            logger.debug(f"Created async instance: {name}")
            return instance

        raise KeyError(f"Service not registered: {name}")

    def set_context(self, context: Dict[str, Any]):
        """
        设置依赖注入上下文

        Args:
            context: 上下文字典
        """
        self._context.set(context)

    def clear_context(self):
        """清除依赖注入上下文"""
        self._context.set({})

    async def shutdown(self):
        """关闭所有服务"""
        logger.info("Shutting down DI container")

        for name, lifecycle in self._lifecycle.items():
            try:
                instance = self._services.get(name)
                if instance and lifecycle:
                    if inspect.iscoroutinefunction(lifecycle.shutdown):
                        await lifecycle.shutdown(instance)
                    else:
                        # Sync shutdown - just call it
                        result = lifecycle.shutdown(instance)
                        # If it returns a coroutine, await it
                        if inspect.iscoroutine(result):
                            await result
                    logger.info(f"Shutdown service: {name}")
            except Exception as e:
                logger.error(f"Failed to shutdown service {name}: {e}")

        self._services.clear()
        logger.info("DI container shutdown completed")

    def get_stats(self) -> Dict[str, Any]:
        """获取容器统计信息"""
        return {
            "total_services": len(self._services),
            "registered_factories": len(self._factories),
            "singletons": len(self._singletons),
            "lifecycle_managed": len(self._lifecycle),
            "services": list(self._services.keys()),
        }


# 全局依赖注入容器实例
di_container = DIContainer()


def inject(service_name: str):
    """
    依赖注入装饰器

    Args:
        service_name: 服务名称

    Returns:
        装饰器函数
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 获取服务实例
            service = di_container.get_async(service_name)

            # 将服务作为参数注入
            return await func(service, *args, **kwargs)

        return wrapper

    return decorator


def inject_context(context: Dict[str, Any]):
    """
    上下文注入装饰器

    Args:
        context: 上下文字典

    Returns:
        装饰器函数
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 设置上下文
            old_context = di_container._context.get({})
            di_container.set_context(context)

            try:
                return await func(*args, **kwargs)
            finally:
                # 恢复上下文
                di_container.set_context(old_context)

        return wrapper

    return decorator


# 注册核心服务
def setup_core_services():
    """
    设置核心服务依赖注入

    Returns:
        设置结果
    """
    try:
        # 注册数据库服务
        def create_database_service():
            from core.db_engine import AsyncSessionLocal

            return AsyncSessionLocal

        di_container.register_factory("database", create_database_service, singleton=True)

        # 注册Redis服务
        def create_redis_service():
            import redis

            from config import REDIS_DB, REDIS_HOST, REDIS_PORT

            return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)

        di_container.register_factory("redis", create_redis_service, singleton=True)

        # 注册AI引擎服务
        def create_ai_engine_service():
            from core.ai_engine import get_llm_router

            if get_llm_router is None:
                raise RuntimeError("LLM router is not available")
            return get_llm_router()

        di_container.register_factory("ai_engine", create_ai_engine_service, singleton=True)

        # 注册告警服务
        def create_alert_service():
            from core.alert_service import AlertService

            return AlertService()

        di_container.register_factory("alert_service", create_alert_service, singleton=True)

        logger.info("Core services registered in DI container")

        return {"status": "success", "stats": di_container.get_stats()}

    except Exception as e:
        logger.error(f"Failed to setup core services: {e}")
        return {"status": "error", "error": str(e)}


async def setup_dependency_injection():
    """
    设置依赖注入

    Returns:
        设置结果
    """
    try:
        # 设置核心服务
        core_services_result = setup_core_services()

        logger.info("Dependency injection setup completed")

        return {"status": "success", "core_services": core_services_result}

    except Exception as e:
        logger.error(f"Dependency injection setup failed: {e}")
        return {"status": "error", "error": str(e)}
