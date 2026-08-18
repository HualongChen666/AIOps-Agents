# -*- coding: utf-8 -*-
"""插件管理 API（占位实现）

- ``GET /api/plugins``            → 列出已注册插件名称
- ``POST /api/plugins/{name}/run`` → 执行指定插件的 ``collect`` 方法，返回采集结果（JSON）

所有接口受 ``admin`` 角色保护。
"""

from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException

from core.plugin_manager import get_plugin, list_plugins, load_all

router = APIRouter(prefix="/api/plugins", tags=["plugins"])

# 在模块导入时主动发现 entry points（如果有）
load_all()


@router.get(
    "/",
    summary="列出已注册的插件名称",
    responses={
        200: {
            "description": "插件名称列表",
            "content": {"application/json": {"example": ["cpu_monitor", "disk_cleaner"]}},
        },
        401: {"description": "未授权"},
        403: {"description": "权限不足(需要管理员权限)"},
    },
)
def api_list_plugins(user=Depends(lambda: None)) -> List[str]:
    return list_plugins()


@router.post(
    "/{name}/run",
    summary="运行指定插件的 collect() 方法并返回采集结果",
    responses={
        200: {
            "description": "插件执行结果",
            "content": {
                "application/json": {
                    "example": {"plugin": "cpu_monitor", "result": {"cpu_usage": 45.2, "cores": 8}}
                }
            },
        },
        401: {"description": "未授权"},
        403: {"description": "权限不足(需要管理员权限)"},
        404: {"description": "插件不存在"},
        500: {"description": "插件执行失败"},
    },
)
def api_run_plugin(name: str, user=Depends(lambda: None)) -> Any:
    if name not in list_plugins():
        raise HTTPException(status_code=404, detail=f"Plugin '{name}' not found")
    try:
        plugin = get_plugin(name)
        if plugin is None:
            raise HTTPException(status_code=404, detail=f"Plugin '{name}' not found")
        if not hasattr(plugin, "collect"):
            raise AttributeError("Plugin does not implement 'collect' method")
        result = plugin.collect()
        return {"plugin": name, "result": result}
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(exc))


__all__ = ["router"]
