# -*- coding: utf-8 -*-
"""
Module Health Check Interface
模块健康检查接口
"""

from abc import ABC, abstractmethod
from typing import Any, Dict

from loguru import logger


class ModuleHealthCheck(ABC):
    """模块健康检查标准接口"""

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """
        执行健康检查

        Returns:
            健康状态字典
        """

    @abstractmethod
    async def graceful_shutdown(self):
        """优雅关闭"""


class DatabaseModuleHealth(ModuleHealthCheck):
    """数据库模块健康检查"""

    def __init__(self):
        self._healthy = True

    async def health_check(self) -> Dict[str, Any]:
        """数据库健康检查"""
        try:
            from sqlalchemy import text

            from core.db_engine import AsyncSessionLocal

            async with AsyncSessionLocal() as session:
                await session.execute(text("SELECT 1"))
            return {
                "module": "database",
                "status": "healthy",
                "message": "Database connection successful",
            }
        except Exception as e:
            logger.info(f"Database health check failed: {e}")
            return {"module": "database", "status": "unhealthy", "error": str(e)}

    async def graceful_shutdown(self):
        """优雅关闭数据库连接"""
        logger.info("Database module graceful shutdown initiated")


class RedisModuleHealth(ModuleHealthCheck):
    """Redis模块健康检查"""

    def __init__(self):
        self._healthy = True

    async def health_check(self) -> Dict[str, Any]:
        """Redis健康检查"""
        try:
            import redis

            from config import REDIS_DB, REDIS_HOST, REDIS_PORT

            r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)
            r.ping()
            return {
                "module": "redis",
                "status": "healthy",
                "message": "Redis connection successful",
            }
        except Exception as e:
            logger.info(f"Redis health check failed: {e}")
            return {"module": "redis", "status": "unhealthy", "error": str(e)}

    async def graceful_shutdown(self):
        """优雅关闭Redis连接"""
        logger.info("Redis module graceful shutdown initiated")


class AIModuleHealth(ModuleHealthCheck):
    """AI引擎模块健康检查"""

    def __init__(self):
        self._healthy = True

    async def health_check(self) -> Dict[str, Any]:
        """AI引擎健康检查"""
        try:
            from core.ai_engine import get_llm_router

            get_llm_router()
            return {"module": "ai_engine", "status": "healthy", "message": "AI engine operational"}
        except Exception as e:
            logger.error(f"AI engine health check failed: {e}")
            return {"module": "ai_engine", "status": "unhealthy", "error": str(e)}

    async def graceful_shutdown(self):
        """优雅关闭AI引擎"""
        logger.info("AI engine graceful shutdown initiated")


# 全局模块健康检查注册表
module_health_registry = {
    "database": DatabaseModuleHealth(),
    "redis": RedisModuleHealth(),
    "ai_engine": AIModuleHealth(),
}


async def check_all_modules_health() -> Dict[str, Any]:
    """
    检查所有模块健康状态

    Returns:
        所有模块的健康状态
    """
    results = {}
    for module_name, health_checker in module_health_registry.items():
        try:
            results[module_name] = await health_checker.health_check()
        except Exception as e:
            logger.error(f"Health check failed for {module_name}: {e}")
            results[module_name] = {"module": module_name, "status": "error", "error": str(e)}

    return results
