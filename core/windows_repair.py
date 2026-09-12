# -*- coding: utf-8 -*-
"""``windows_repair`` module.

Windows 平台修复门面（façade），委托到真实实现 ``core.repair_engine``。

历史问题（已修复）：本模块曾是遗留空壳，``execute_windows_repair`` 恒返回
``{}``、``get_windows_repair_history`` 恒返回 ``[]``，而 ``WindowsStrategy``
引用的正是这个空壳，导致 Windows 修复/历史在运行期完全不可用。

现在本模块不再自造桩实现，而是：
  * 脚本注册表 ``WINDOWS_REPAIR_SCRIPTS`` 由真实 PowerShell 脚本库动态派生；
  * ``execute_windows_repair`` 直接调用 ``core.repair_engine.execute_repair``
    （内含 command_guard 审查、参数注入防护、SQLite 持久化）；
  * ``get_windows_repair_history`` 读取真实修复历史。

Top-level functions: execute_windows_repair, get_windows_repair_history
"""

from typing import Any, Dict, List

from core.repair_engine import (
    execute_repair as _engine_execute_repair,
    get_repair_history as _engine_get_repair_history,
    get_repair_scripts as _engine_get_repair_scripts,
)


def _build_script_registry() -> Dict[str, Any]:
    """从真实修复引擎派生脚本注册表。

    Returns:
        dict: ``{script_key: {name, description, params, risk}}``
    """
    registry: Dict[str, Any] = {}
    for script in _engine_get_repair_scripts():
        registry[script["key"]] = {
            "name": script["name"],
            "description": script["description"],
            "params": list(script.get("params", [])),
            "risk": script.get("risk", "unknown"),
        }
    return registry


# Windows 修复脚本注册表（与核心引擎保持同源，只读用途）
WINDOWS_REPAIR_SCRIPTS: Dict[str, Any] = _build_script_registry()


async def execute_windows_repair(script_key: str, params: Dict[str, str]) -> Dict[str, Any]:
    """执行 Windows 修复脚本（委托到真实修复引擎）。

    Args:
        script_key: 修复脚本键（见 ``WINDOWS_REPAIR_SCRIPTS``）
        params: 脚本参数

    Returns:
        真实执行结果（含 success/output/error/return_code/风险与持久化状态）
    """
    return await _engine_execute_repair(script_key, params or {})


def get_windows_repair_history(limit: int = 10) -> List[Dict[str, Any]]:
    """获取 Windows 修复历史（委托到真实修复引擎）。

    Args:
        limit: 最大返回条数

    Returns:
        真实修复历史记录列表
    """
    return _engine_get_repair_history(limit)
