# -*- coding: utf-8 -*-
"""
Dependency Injection Container
依赖注入容器

提供轻量级的依赖注入功能，解决循环依赖问题，不修改现有架构。
"""

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
        self._initialized: set = set()
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

    def _resolve(self, name: str) -> Any:
        """解析服务实例：上下文 → 单例缓存 → 工厂创建并缓存。

        ``get`` 与 ``get_async`` 共用此逻辑，避免两套几乎完全重复的实现。
        """
        context = self._context.get({})
        if name in context:
            return context[name]

        if name in self._services and self._singletons.get(name):
            return self._services[name]

        if name in self._factories:
            instance = self._factories[name]()
            if self._singletons.get(name):
                self._services[name] = instance
            logger.debug(f"Created instance: {name}")
            return instance

        raise KeyError(f"Service not registered: {name}")

    async def _initialize_instance(self, instance: Any) -> None:
        """调用实例的 ``initialize``（同步或异步）并等待其真正完成。"""
        init = getattr(instance, "initialize", None)
        if not callable(init):
            return
        result = init()
        if inspect.isawaitable(result):
            await result

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
        return self._resolve(name)

    async def get_async(self, name: str) -> Any:
        """
        异步获取服务实例，并 **等待** 带生命周期服务的初始化真正完成。

        与 ``get`` 共用解析逻辑；对注册了 ``lifecycle`` 的服务，本方法会
        ``await`` 其 ``initialize()``（同步实现则直接调用），确保返回的实例
        已经初始化完毕，而不再 fire-and-forget。

        Args:
            name: 服务名称

        Returns:
            已初始化的服务实例

        Raises:
            KeyError: 服务未注册
        """
        instance = self._resolve(name)

        if name in self._lifecycle and name not in self._initialized:
            await self._initialize_instance(instance)
            self._initialized.add(name)
            logger.debug(f"Initialized async instance: {name}")

        return instance

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
        self._initialized.clear()
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
            # 获取服务实例（等待初始化完成）
            service = await di_container.get_async(service_name)

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
