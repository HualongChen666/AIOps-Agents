# -*- coding: utf-8 -*-
"""
Module Initialization Dependencies
模块初始化依赖图
"""

MODULE_DEPENDENCIES = {
    "database": [],
    "redis": ["database"],
    "ai_engine": ["redis", "database"],
    "alert_engine": ["database"],
    "cache": ["redis"],
    "metrics": ["database"],
    "business_metrics": ["alert_engine", "metrics"],
}

INITIALIZATION_ORDER = [
    "database",
    "redis",
    "ai_engine",
    "alert_engine",
    "cache",
    "metrics",
    "business_metrics",
]


def validate_initialization_order():
    """验证初始化顺序"""
    for i, module in enumerate(INITIALIZATION_ORDER):
        deps = MODULE_DEPENDENCIES.get(module, [])
        for dep in deps:
            if dep not in INITIALIZATION_ORDER[:i]:
                raise ValueError(f"Dependency {dep} of {module} not initialized before {module}")
    return True
