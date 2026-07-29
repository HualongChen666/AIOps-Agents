# -*- coding: utf-8 -*-
"""
tools.py
-------
AI Agent 工具生态建设。

功能：
- 工具定义和注册
- 工具执行
- 工具组合和链式调用
- 工具自动选择
- 目标：工具使用准确率 ≥ 90%
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from . import observability_client

logger = logging.getLogger(__name__)

try:
    from core.command_guard import RiskLevel
    from core.command_guard import analyze_command as _analyze_command

    COMMAND_GUARD_AVAILABLE = True
except Exception as e:
    logging.exception("Unexpected exception: %s", e)
    COMMAND_GUARD_AVAILABLE = False
    RiskLevel = None  # type: ignore[misc,assignment]
    _analyze_command = None  # type: ignore[assignment]

try:
    from core.audit_logger import log_audit_event as _log_audit_event

    AUDIT_AVAILABLE = True
except Exception as e:
    logging.exception("Unexpected exception: %s", e)
    AUDIT_AVAILABLE = False
    _log_audit_event = None  # type: ignore[assignment]


def _audit_tool(tool_name: str, status: str, details: Optional[Dict[str, Any]] = None) -> None:
    """Best-effort audit wrapper for tool executions."""
    if AUDIT_AVAILABLE and _log_audit_event:
        try:
            _log_audit_event(
                event_type="AGENT_TOOL_EXECUTED",
                user="system",
                resource=tool_name,
                action=tool_name,
                status=status,
                details=details or {},
            )
        except Exception as exc:
            logger.warning(f"Tool audit failed: {exc}")


def _guard_command_param(param_name: str, value: Any) -> None:
    """Run command_guard over command-like string parameters before execution."""
    if not COMMAND_GUARD_AVAILABLE or not _analyze_command:
        return
    if not isinstance(value, str):
        return
    if not value:
        return
    if param_name in _COMMAND_PARAM_NAMES:
        result = _analyze_command(value)
        if RiskLevel is not None and result.get("risk_level") in (
            RiskLevel.BLOCKED,
            RiskLevel.HIGH,
        ):
            raise ValueError(
                f"Tool parameter {param_name} blocked by command_guard "
                f"(risk={result.get('risk_level')}, reason={result.get('reason')}): {result}"
            )


# Parameter value whitelist patterns (applied before tool execution)
_MAX_PARAM_LEN = 128
_MAX_TEXT_LEN = 1000

# Names that accept free-form description text, but still must not contain shell metacharacters.
_TEXT_PARAM_NAMES = {"goal", "description"}

# Name-based default patterns
_NAME_PATTERNS = {
    "service_name": re.compile(r"^[A-Za-z0-9_.\-]+$"),
    "target": re.compile(r"^[A-Za-z0-9_.\-:/@]+$"),
    "service": re.compile(r"^[A-Za-z0-9_.\-]+$"),
    "host": re.compile(r"^[A-Za-z0-9_.\-:/@]+$"),
    "level": re.compile(r"^[A-Za-z0-9_]+$"),
    "method": re.compile(r"^[A-Za-z0-9_]+$"),
    "strategy": re.compile(r"^[A-Za-z0-9_]+$"),
    "role": re.compile(r"^[A-Za-z0-9_]+$"),
    "type": re.compile(r"^[A-Za-z0-9_]+$"),
    "alert_id": re.compile(r"^[A-Za-z0-9_\-:.]+$"),
}

_SAFE_TEXT_PATTERN = re.compile(r"^[\u4e00-\u9fa5A-Za-z0-9_\s.,:;?!()\[\]/'\"@-]+$")
_SHELL_METACHAR_PATTERN = re.compile(r"[;|&$`\\<>{}\n\r]")

# Int-like parameter names (must be convertible to int and fall within _INT_PARAM_RANGES)
_INT_PARAM_NAMES = {
    "duration",
    "interval",
    "timeout",
    "replicas",
    "lines",
    "time_range_hours",
    "hours",
    "limit",
    "_depth",
}

# Integer parameter ranges (inclusive)
_INT_PARAM_RANGES = {
    "duration": (1, 300),
    "interval": (1, 300),
    "timeout": (1, 300),
    "replicas": (0, 1000),
    "lines": (1, 10000),
    "time_range_hours": (0, 168),
    "hours": (0, 168),
    "limit": (1, 10000),
    "_depth": (0, 3),
}

# Float-like parameter names
_FLOAT_PARAM_NAMES = {"threshold"}
_FLOAT_PARAM_RANGES = {
    "threshold": (0.0, 1.0),
}

# Boolean parameters
_BOOL_PARAM_NAMES = {"wait", "dry_run"}

# List-like parameter names
_LIST_PARAM_NAMES = {"available_tools", "tools", "data"}

# Size / depth limits
_MAX_LIST_LENGTH = 10000
_MAX_CONTEXT_DEPTH = 3
_DEFAULT_TOOL_TIMEOUT = float(os.environ.get("AIOPS_TOOL_TIMEOUT", "30"))

# Dangerous keys that should be passed to command_guard even inside dicts
_COMMAND_PARAM_NAMES = {"command", "cmd", "script", "rollback_command"}

# Data-container parameter names whose values are observability payloads; strict
# per-string pattern validation is skipped to allow arbitrary log/metric/trace text.
_DATA_CONTAINER_NAMES = {
    "alert",
    "metrics_data",
    "correlated_alerts",
    "change_events",
    "verification_data",
    "kubernetes_events",
    "container_metrics",
    "host_metrics",
    "database_metrics",
}


# ----------------------------------------------------------------------
# 1️⃣ 工具类别枚举
# ----------------------------------------------------------------------
class ToolCategory(Enum):
    """工具类别"""

    MONITORING = "monitoring"
    ANALYSIS = "analysis"
    EXECUTION = "execution"
    NOTIFICATION = "notification"
    DIAGNOSTIC = "diagnostic"


# ----------------------------------------------------------------------
# 2️⃣ 工具定义
# ----------------------------------------------------------------------
@dataclass
class Tool:
    """工具定义"""

    name: str
    description: str
    category: ToolCategory
    function: Callable
    parameters: Dict[str, Any] = field(default_factory=dict)
    required_params: List[str] = field(default_factory=list)
    optional_params: List[str] = field(default_factory=list)
    examples: List[Dict[str, Any]] = field(default_factory=list)
    param_patterns: Dict[str, Any] = field(default_factory=dict)

    def execute(
        self,
        dry_run: bool = False,
        timeout: Optional[Union[int, float]] = None,
        **kwargs,
    ) -> Any:
        """执行工具。

        Parameters
        ----------
        dry_run : bool
            如为 True，仅返回预演结果，不真正调用底层函数。
        timeout : int | float | None
            最大执行秒数。未指定时使用默认值或工具参数中的 ``timeout``。
        **kwargs
            工具参数。
        """
        # 检查必需参数
        missing_params = [p for p in self.required_params if p not in kwargs]
        if missing_params:
            raise ValueError(f"Missing required parameters: {missing_params}")

        # 参数安全验证
        self._validate_parameters(kwargs)

        # 合并默认参数并做数值范围裁剪
        params = self._clamp_parameter_ranges({**self.parameters, **kwargs})

        # 确定执行超时
        exec_timeout = timeout
        if exec_timeout is None:
            exec_timeout = params.get("timeout")
        if exec_timeout is None:
            exec_timeout = _DEFAULT_TOOL_TIMEOUT
        try:
            exec_timeout = float(exec_timeout)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid timeout value: {exec_timeout}") from exc

        # 若底层函数不接受 timeout 参数，则不将其传入函数
        allowed = (
            set(self.required_params) | set(self.optional_params) | set(self.parameters.keys())
        )
        try:
            sig = inspect.signature(self.function)
            for param in sig.parameters.values():
                if param.kind == param.VAR_KEYWORD:
                    allowed = set(params.keys())
                    break
                allowed.add(param.name)
        except (TypeError, ValueError):
            pass
        if "timeout" not in allowed and "timeout" in params:
            params.pop("timeout")

        # 预演模式：不执行，只返回计划
        if dry_run:
            return {
                "dry_run": True,
                "tool": self.name,
                "category": self.category.value,
                "parameters": {k: str(v) for k, v in params.items()},
                "execution_timeout": exec_timeout,
                "note": "Would execute if not in dry-run mode",
            }

        # 执行工具函数
        try:
            return self._execute_with_timeout(params, exec_timeout)
        except Exception as e:
            logger.error(f"Tool {self.name} execution failed: {e}")
            raise

    def _clamp_parameter_ranges(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """对常用数值型参数做硬范围限制，防止 LLM 生成极端参数拖垮系统。"""
        clamps = {
            "duration": (10, 3600),
            "interval": (5, 300),
            "limit": (1, 1000),
            "lines": (1, 1000),
            "time_range_hours": (1, 24),
            "hours": (1, 168),
        }
        for key, (lo, hi) in clamps.items():
            if key in params:
                try:
                    value = int(params[key])
                except (TypeError, ValueError):
                    continue
                if value < lo or value > hi:
                    logger.warning(
                        f"Parameter '{key}' for tool '{self.name}' clamped from {value} to "
                        f"{max(lo, min(value, hi))}"
                    )
                params = {**params, key: max(lo, min(value, hi))}
        return params

    def _execute_with_timeout(self, params: Dict[str, Any], timeout: float) -> Any:
        """带统一超时的工具执行包装。"""

        async def _run() -> Any:
            if asyncio.iscoroutinefunction(self.function):
                return await asyncio.wait_for(self.function(**params), timeout=timeout)
            return await asyncio.wait_for(
                asyncio.to_thread(self.function, **params),
                timeout=timeout,
            )

        try:
            asyncio.get_running_loop()
            return _run()
        except RuntimeError:
            return asyncio.run(_run())

    def _validate_parameters(self, params: Dict[str, Any]) -> None:
        """验证参数安全性（白名单模式）。

        - 只允许声明过的参数名（required + optional + defaults + function signature）。
        - 字符串值按参数名匹配白名单正则或通用安全规则。
        - 数值/列表/字典参数做类型、范围与内容校验。
        - 对 dict 类型参数递归校验，并对 command/cmd/script 键调用 command_guard。
        """
        allowed = (
            set(self.required_params) | set(self.optional_params) | set(self.parameters.keys())
        )

        # 从函数签名推导允许的参数名
        try:
            sig = inspect.signature(self.function)
            for param in sig.parameters.values():
                if param.kind == param.VAR_KEYWORD:
                    allowed = set(params.keys())
                    break
                allowed.add(param.name)
        except (TypeError, ValueError):
            pass

        for key, value in params.items():
            if key not in allowed:
                raise ValueError(
                    f"Parameter '{key}' is not allowed for tool '{self.name}'; "
                    f"allowed parameters are: {sorted(allowed)}"
                )
            self._validate_value(key, value, depth=0)

    def _validate_value(self, name: str, value: Any, depth: int = 0) -> None:
        """递归校验单个参数值。"""
        if depth > _MAX_CONTEXT_DEPTH:
            raise ValueError(
                f"Parameter '{name}' exceeds maximum nested depth of {_MAX_CONTEXT_DEPTH}"
            )

        # 数据容器（alert/metrics_data/日志/追踪等）只校验尺寸上限，不做字符白名单校验
        if any(name == n or name.endswith(f"[{n}]") for n in _DATA_CONTAINER_NAMES):
            if isinstance(value, list) and len(value) > _MAX_LIST_LENGTH:
                raise ValueError(
                    f"Parameter '{name}' exceeds maximum list length of {_MAX_LIST_LENGTH}"
                )
            if isinstance(value, dict):
                for k, v in value.items():
                    if k in _COMMAND_PARAM_NAMES and isinstance(v, str):
                        _guard_command_param(k, v)
            return

        # 布尔型参数
        if name in _BOOL_PARAM_NAMES:
            if not isinstance(value, bool):
                raise ValueError(f"Parameter '{name}' must be a boolean")
            return

        # 整数型参数 + 范围
        if name in _INT_PARAM_NAMES:
            if isinstance(value, bool):
                raise ValueError(f"Parameter '{name}' must be an integer (got bool)")
            try:
                ivalue = int(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Parameter '{name}' must be an integer") from exc
            min_v, max_v = _INT_PARAM_RANGES.get(name, (1, 100000))
            if ivalue < min_v or ivalue > max_v:
                raise ValueError(f"Parameter '{name}' must be between {min_v} and {max_v}")
            return

        # 浮点型参数 + 范围
        if name in _FLOAT_PARAM_NAMES:
            if isinstance(value, bool):
                raise ValueError(f"Parameter '{name}' must be a float (got bool)")
            try:
                fvalue = float(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Parameter '{name}' must be a number") from exc
            min_v, max_v = _FLOAT_PARAM_RANGES.get(name, (float("-inf"), float("inf")))
            if fvalue < min_v or fvalue > max_v:
                raise ValueError(f"Parameter '{name}' must be between {min_v} and {max_v}")
            return

        # 列表参数 (also allow comma-separated string for some callers)
        if name in _LIST_PARAM_NAMES or isinstance(value, list):
            if isinstance(value, str):
                # The tool function normalizes comma-separated strings into lists.
                if len(value) > _MAX_TEXT_LEN:
                    raise ValueError(
                        f"Parameter '{name}' exceeds maximum length of {_MAX_TEXT_LEN}"
                    )
                pattern = _NAME_PATTERNS.get("service")
                for item in value.split(","):
                    item = item.strip()
                    if item == "":
                        continue
                    if pattern is not None and not pattern.match(item):
                        raise ValueError(
                            f"Parameter '{name}' item '{item}' contains disallowed characters"
                        )
            elif isinstance(value, list):
                if len(value) > _MAX_LIST_LENGTH:
                    raise ValueError(
                        f"Parameter '{name}' exceeds maximum list length of {_MAX_LIST_LENGTH}"
                    )
                for i, item in enumerate(value):
                    self._validate_value(f"{name}[{i}]", item, depth=depth + 1)
                return
            else:
                raise ValueError(f"Parameter '{name}' must be a list")

        # 字典参数：递归校验，并对命令键调用 command_guard
        if isinstance(value, dict):
            for k, v in value.items():
                if isinstance(v, str):
                    self._validate_string_value(k, v, allow_text=True)
                    if k in _COMMAND_PARAM_NAMES:
                        _guard_command_param(k, v)
                elif isinstance(v, (dict, list)):
                    self._validate_value(k, v, depth=depth + 1)
                elif isinstance(v, bool):
                    pass
                else:
                    # 其它标量也允许
                    pass
            return

        # 字符串参数
        if isinstance(value, str):
            is_text = name in _TEXT_PARAM_NAMES
            self._validate_string_value(name, value, allow_text=is_text)
            _guard_command_param(name, value)

    def _validate_string_value(self, name: str, value: str, allow_text: bool = False):
        """校验单个字符串参数值。"""
        if not isinstance(value, str):
            return

        # Empty strings are only allowed for free-form text parameters or
        # parameters that do not have a strict name-based pattern. This blocks
        # bypasses like target="", service="", service_name="" which would
        # otherwise skip the regex whitelist.
        if value == "":
            if (
                name in _NAME_PATTERNS
                or name in _INT_PARAM_NAMES
                or name in _FLOAT_PARAM_NAMES
                or name in _BOOL_PARAM_NAMES
                or name in _LIST_PARAM_NAMES
            ):
                raise ValueError(f"Parameter '{name}' cannot be empty")
            if allow_text:
                return
            # For unpatterned, non-structured parameters, keep allowing empty.
            return

        max_len = _MAX_TEXT_LEN if allow_text else _MAX_PARAM_LEN
        if len(value) > max_len:
            raise ValueError(f"Parameter '{name}' exceeds maximum length of {max_len}")

        # Path traversal check applies to all string parameters.
        if "../" in value or "..\\" in value:
            raise ValueError(f"Parameter '{name}' contains path traversal attempt")

        # Reject shell metacharacters globally.
        if _SHELL_METACHAR_PATTERN.search(value):
            raise ValueError(
                f"Parameter '{name}' contains dangerous characters (shell metacharacters)"
            )

        # Explicit per-tool or name-based whitelist.
        pattern = self.param_patterns.get(name)
        if pattern is None:
            pattern = _NAME_PATTERNS.get(name)

        if pattern is not None:
            if not pattern.match(value):
                raise ValueError(
                    f"Parameter '{name}' value '{value[:50]}' does not match allowed pattern"
                )
            return

        # Default strict whitelist for unspecified string parameters.
        if not _SAFE_TEXT_PATTERN.match(value):
            raise ValueError(f"Parameter '{name}' value contains disallowed characters")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "parameters": self.parameters,
            "required_params": self.required_params,
            "optional_params": self.optional_params,
            "examples": self.examples,
        }


# ----------------------------------------------------------------------
# 3️⃣ 工具审批管理
# ----------------------------------------------------------------------
class ToolApprovalManager:
    """工具注册/注销审批管理器。

    默认不启用审批（保持向后兼容），但可通过 ``approval_required`` 或环境变量
    ``AIOPS_TOOL_REGISTRATION_APPROVAL_REQUIRED`` 开启。开启后，未审批的工具
    注册/注销将被拒绝。
    """

    def __init__(self, approval_required: bool = False):
        self.approval_required = approval_required
        self._approved: Dict[str, str] = {}

    def request_approval(self, tool_name: str, requester: str, reason: str = "") -> str:
        """提交工具注册/注销审批请求（当前立即批准，用于审计）"""
        request_id = f"approval_{tool_name}_{int(time.time())}"
        logger.info(f"Tool approval requested: {request_id} for {tool_name} by {requester}")
        return request_id

    def approve(self, tool_name: str, approver: str) -> None:
        """批准工具"""
        self._approved[tool_name] = approver
        logger.info(f"Tool '{tool_name}' approved by {approver}")

    def is_approved(self, tool_name: str) -> bool:
        """是否已批准（未启用审批时恒为 True）"""
        if not self.approval_required:
            return True
        return tool_name in self._approved

    def revoke(self, tool_name: str) -> None:
        """撤销批准"""
        self._approved.pop(tool_name, None)


# ----------------------------------------------------------------------
# 4️⃣ 工具注册表
# ----------------------------------------------------------------------
class ToolRegistry:
    """工具注册表（支持可选的注册审批流程）"""

    def __init__(self, approval_required: Optional[bool] = None):
        """
        Parameters
        ----------
        approval_required : bool, optional
            是否要求注册/注销工具时经过审批。默认从环境变量读取。
        """
        self.tools: Dict[str, Tool] = {}
        self.approval_manager = ToolApprovalManager(
            approval_required=self._resolve_approval_required(approval_required)
        )
        self._initializing = True
        self._initialize_default_tools()
        self._initializing = False

    @staticmethod
    def _resolve_approval_required(value: Optional[bool]) -> bool:
        if value is not None:
            return bool(value)
        env = os.environ.get("AIOPS_TOOL_REGISTRATION_APPROVAL_REQUIRED", "false").lower()
        return env in ("1", "true", "yes", "on")

    def _is_initializing(self) -> bool:
        return getattr(self, "_initializing", False)

    def _check_approval(
        self,
        tool_name: str,
        approved_by: Optional[str] = None,
    ) -> None:
        """检查并记录审批。初始化期间跳过。"""
        if self._is_initializing():
            return
        if not self.approval_manager.is_approved(tool_name):
            if not approved_by:
                raise PermissionError(
                    f"Tool '{tool_name}' registration/unregistration requires approval. "
                    f"Call approve_tool('{tool_name}', approver) first or pass approved_by="
                )
            self.approval_manager.approve(tool_name, approved_by)

    def register(self, tool: Tool, approved_by: Optional[str] = None) -> None:
        """注册工具。开启审批时需提供 approved_by 或预先 approve_tool。"""
        self._check_approval(tool.name, approved_by)
        self.tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")

    def unregister(self, tool_name: str, approved_by: Optional[str] = None) -> None:
        """注销工具。开启审批时需提供 approved_by 或预先 approve_tool。"""
        if tool_name not in self.tools:
            return
        self._check_approval(tool_name, approved_by)
        del self.tools[tool_name]
        logger.info(f"Unregistered tool: {tool_name}")

    def approve_tool(self, tool_name: str, approver: str) -> None:
        """预先批准工具注册/注销"""
        self.approval_manager.approve(tool_name, approver)

    def request_tool_approval(self, tool_name: str, requester: str, reason: str = "") -> str:
        """提交工具注册/注销审批请求"""
        return self.approval_manager.request_approval(tool_name, requester, reason)

    def is_tool_approved(self, tool_name: str) -> bool:
        """查询工具是否已被批准"""
        return self.approval_manager.is_approved(tool_name)

    def get_tool(self, tool_name: str) -> Optional[Tool]:
        """获取工具"""
        return self.tools.get(tool_name)

    def list_tools(
        self,
        category: Optional[ToolCategory] = None,
    ) -> List[Tool]:
        """列出工具"""
        if category is None:
            return list(self.tools.values())
        return [tool for tool in self.tools.values() if tool.category == category]

    def search_tools(
        self,
        query: str,
    ) -> List[Tool]:
        """搜索工具"""
        query_lower = query.lower()
        results = []

        for tool in self.tools.values():
            # 搜索名称和描述
            if query_lower in tool.name.lower() or query_lower in tool.description.lower():
                results.append(tool)

        return results

    def _initialize_default_tools(self):
        """初始化默认工具"""
        # 监控工具
        self.register(
            Tool(
                name="collect_metrics",
                description="收集系统指标（CPU、内存、磁盘等）",
                category=ToolCategory.MONITORING,
                function=self._collect_metrics,
                required_params=["target"],
                optional_params=["duration", "interval"],
            )
        )

        self.register(
            Tool(
                name="collect_logs",
                description="收集系统日志",
                category=ToolCategory.MONITORING,
                function=self._collect_logs,
                required_params=["service"],
                optional_params=["level", "lines"],
            )
        )

        self.register(
            Tool(
                name="collect_service_metrics",
                description="收集服务级指标（请求量、错误率、延迟、连接池等）",
                category=ToolCategory.MONITORING,
                function=self._collect_service_metrics,
                required_params=["service_name"],
                optional_params=["time_range_hours"],
            )
        )

        self.register(
            Tool(
                name="collect_network_metrics",
                description="收集网络指标（丢包率、延迟、DNS 解析失败等）",
                category=ToolCategory.MONITORING,
                function=self._collect_network_metrics,
                required_params=["target"],
                optional_params=["duration"],
            )
        )

        self.register(
            Tool(
                name="collect_change_events",
                description="收集最近的变更记录（配置变更、发布、扩缩容）",
                category=ToolCategory.MONITORING,
                function=self._collect_change_events,
                required_params=["target"],
                optional_params=["hours", "change_events"],
            )
        )

        self.register(
            Tool(
                name="collect_kubernetes_events",
                description="收集 Kubernetes 事件（如 OOMKilled、节点异常）",
                category=ToolCategory.MONITORING,
                function=self._collect_kubernetes_events,
                required_params=["namespace"],
                optional_params=["field_selector", "limit"],
            )
        )

        self.register(
            Tool(
                name="collect_container_metrics",
                description="收集容器指标（内存使用、Limit、OOM 状态）",
                category=ToolCategory.MONITORING,
                function=self._collect_container_metrics,
                required_params=["pod_name"],
                optional_params=["namespace", "container_metrics"],
            )
        )

        self.register(
            Tool(
                name="collect_host_metrics",
                description="收集宿主机指标与硬件错误（EDAC/MCE）",
                category=ToolCategory.MONITORING,
                function=self._collect_host_metrics,
                required_params=["node_name"],
                optional_params=["host_metrics"],
            )
        )

        self.register(
            Tool(
                name="collect_database_metrics",
                description="收集数据库指标与慢查询",
                category=ToolCategory.MONITORING,
                function=self._collect_database_metrics,
                required_params=["database"],
                optional_params=["time_range_hours", "database_metrics"],
            )
        )

        self.register(
            Tool(
                name="collect_correlated_alerts",
                description="收集同时段的关联告警",
                category=ToolCategory.MONITORING,
                function=self._collect_correlated_alerts,
                required_params=["service"],
                optional_params=["limit"],
            )
        )

        self.register(
            Tool(
                name="collect_topology",
                description="收集服务拓扑与依赖关系",
                category=ToolCategory.DIAGNOSTIC,
                function=self._collect_topology,
                required_params=["service"],
            )
        )

        # 分析工具
        self.register(
            Tool(
                name="analyze_anomaly",
                description="检测异常",
                category=ToolCategory.ANALYSIS,
                function=self._analyze_anomaly,
                required_params=["data"],
                optional_params=["threshold", "method"],
            )
        )

        self.register(
            Tool(
                name="root_cause_analysis",
                description="根因分析（支持传入 alert、metrics_data、correlated_alerts、change_events、verification_data）",  # noqa: E501
                category=ToolCategory.ANALYSIS,
                function=self._root_cause_analysis,
                required_params=["alert_id"],
                optional_params=[
                    "method",
                    "alert",
                    "metrics_data",
                    "correlated_alerts",
                    "change_events",
                    "verification_data",
                ],
            )
        )

        # 执行工具
        self.register(
            Tool(
                name="restart_service",
                description="重启服务",
                category=ToolCategory.EXECUTION,
                function=self._restart_service,
                required_params=["service_name"],
                optional_params=["timeout"],
            )
        )

        self.register(
            Tool(
                name="scale_service",
                description="扩缩容服务",
                category=ToolCategory.EXECUTION,
                function=self._scale_service,
                required_params=["service_name", "replicas"],
                optional_params=["strategy"],
            )
        )

        # 诊断工具
        self.register(
            Tool(
                name="check_health",
                description="健康检查",
                category=ToolCategory.DIAGNOSTIC,
                function=self._check_health,
                required_params=["target"],
            )
        )

        self.register(
            Tool(
                name="run_diagnostic",
                description="运行诊断",
                category=ToolCategory.DIAGNOSTIC,
                function=self._run_diagnostic,
                required_params=["target"],
                optional_params=["type"],
            )
        )

        # 子代理工具
        self.register(
            Tool(
                name="dispatch_subagent",
                description="将子任务分派给子 Agent 执行",
                category=ToolCategory.EXECUTION,
                function=self._dispatch_subagent,
                required_params=["goal"],
                optional_params=["context", "available_tools", "role", "wait", "_depth", "dry_run"],
            )
        )

    # 默认工具实现（示例）
    def _collect_metrics(
        self, target: str, duration: int = 60, interval: int = 5
    ) -> Dict[str, Any]:
        """收集指标：优先查询 Prometheus 节点指标，否则返回兜底结构。"""
        logger.info(f"Collecting metrics for {target}")
        try:
            safe_target = observability_client._safe_label(target)
            prom_url = observability_client.get_prometheus_url()
            if prom_url:
                end = time.time()
                start = end - duration
                cpu_idle = observability_client._extract_prom_scalar_value(
                    observability_client.query_prometheus_range(
                        f"avg by (instance) (rate(node_cpu_seconds_total{{instance=~'{safe_target}.*',mode='idle'}}[1m]))",  # noqa: E501
                        start,
                        end,
                        f"{interval}s",
                    )
                )
                cpu_usage = 100.0 - (cpu_idle * 100.0) if cpu_idle is not None else None

                mem_avail = observability_client._extract_prom_scalar_value(
                    observability_client.query_prometheus(
                        f"node_memory_MemAvailable_bytes{{instance=~'{safe_target}.*'}}"
                    )
                )
                mem_total = observability_client._extract_prom_scalar_value(
                    observability_client.query_prometheus(
                        f"node_memory_MemTotal_bytes{{instance=~'{safe_target}.*'}}"
                    )
                )
                memory_usage = (
                    (mem_total - mem_avail) / mem_total * 100.0
                    if mem_total and mem_avail is not None and mem_total > 0
                    else None
                )

                disk_usage = observability_client._extract_prom_scalar_value(
                    observability_client.query_prometheus(
                        f"100 - (node_filesystem_avail_bytes{{instance=~'{safe_target}.*',fstype!='tmpfs'}} / node_filesystem_size_bytes * 100)"  # noqa: E501
                    )
                )

                return {
                    "target": safe_target,
                    "cpu_usage": cpu_usage,
                    "memory_usage": memory_usage,
                    "disk_usage": disk_usage,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "source": "prometheus",
                }
        except Exception as exc:
            logger.warning(f"Prometheus metric collection failed for {target}: {exc}")

        return {
            "target": target,
            "cpu_usage": None,
            "memory_usage": None,
            "disk_usage": None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "note": "No Prometheus integration configured; returning empty placeholders",
        }

    def _collect_logs(self, service: str, level: str = "INFO", lines: int = 100) -> List[str]:
        """收集日志（当前为占位实现，限制返回条数并对服务名做校验）"""
        logger.info(f"Collecting logs for {service}")
        safe_service = observability_client._safe_label(service)
        safe_level = observability_client._safe_label(level)
        return [f"[{safe_level}] Service {safe_service} log line {i}" for i in range(lines)]

    def _analyze_anomaly(
        self,
        data: List[float],
        threshold: float = 0.5,
        method: str = "transformer",
    ) -> Dict[str, Any]:
        """异常检测"""
        logger.info(f"Analyzing anomaly with {method}")
        # 实际实现应调用异常检测模型
        return {
            "method": method,
            "is_anomaly": max(data) > threshold,
            "anomaly_score": max(data),
        }

    async def _root_cause_analysis(
        self,
        alert_id: str,
        method: str = "causal",
        alert: Optional[Dict[str, Any]] = None,
        metrics_data: Optional[Dict[str, Any]] = None,
        correlated_alerts: Optional[List[Dict[str, Any]]] = None,
        change_events: Optional[List[Dict[str, Any]]] = None,
        verification_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """根因分析

        优先使用调用方传入的 alert / metrics_data / correlated_alerts /
        change_events / verification_data，未传时回退到 alert_id 自身。
        """
        logger.info(f"Root cause analysis for {alert_id} using {method}")
        try:
            from core.root_cause_intelligence import (
                ROOT_CAUSE_INTELLIGENCE_AVAILABLE,
                root_cause_intelligence_engine,
            )

            if ROOT_CAUSE_INTELLIGENCE_AVAILABLE:
                resolved_alert = (
                    dict(alert)
                    if alert
                    else {"id": alert_id, "title": "root cause tool invocation"}
                )
                resolved_alert.setdefault("id", alert_id)
                resolved_metrics = dict(metrics_data) if metrics_data else {}
                resolved_context = {
                    "correlated_alerts": correlated_alerts or [],
                    "change_events": change_events or [],
                }
                if verification_data:
                    resolved_context["verification_data"] = verification_data
                hypotheses = await root_cause_intelligence_engine.analyze_root_causes_enhanced(
                    alert=resolved_alert,
                    metrics_data=resolved_metrics,
                    context=resolved_context,
                )
                candidates = []
                for h in hypotheses[:5]:
                    candidates.append(
                        {
                            "root_cause": getattr(h, "root_cause", str(h)),
                            "confidence": getattr(h, "confidence", 0.5),
                            "expected_observations_if_true": getattr(
                                h, "expected_observations", []
                            ),
                            "missing_data": getattr(h, "missing_data", []),
                            "is_verifiable": getattr(h, "verification_status", "pending")
                            == "verified",
                            "evidence": getattr(h, "evidence", []),
                        }
                    )
                return {
                    "alert_id": alert_id,
                    "method": method,
                    "candidates": candidates,
                    "escalation_recommended": not any(c["confidence"] >= 0.75 for c in candidates),
                }
        except Exception as e:
            logger.warning(f"Root cause engine invocation failed: {e}")

        # 兜底：返回显式待验证的候选集合，避免给出单一虚假结论
        return {
            "alert_id": alert_id,
            "method": method,
            "candidates": [
                {
                    "root_cause": "unknown",
                    "confidence": 0.0,
                    "expected_observations_if_true": [],
                    "missing_data": ["alert details", "metrics_data", "topology"],
                    "is_verifiable": False,
                    "evidence": [],
                }
            ],
            "escalation_recommended": True,
            "escalation_reason": "Insufficient data for root cause analysis tool",
            "confidence": 0.0,
        }

    def _restart_service(self, service_name: str, timeout: int = 30) -> Dict[str, Any]:
        """重启服务"""
        logger.info(f"Restarting service {service_name}")
        # 实际实现应调用服务管理接口
        return {
            "service": service_name,
            "status": "restarted",
            "timeout": timeout,
        }

    def _scale_service(
        self,
        service_name: str,
        replicas: int,
        strategy: str = "rolling",
    ) -> Dict[str, Any]:
        """扩缩容服务"""
        logger.info(f"Scaling service {service_name} to {replicas} replicas")
        # 实际实现应调用扩缩容接口
        return {
            "service": service_name,
            "replicas": replicas,
            "strategy": strategy,
            "status": "scaled",
        }

    def _check_health(self, target: str) -> Dict[str, Any]:
        """健康检查"""
        logger.info(f"Checking health of {target}")
        # 实际实现应调用健康检查接口
        return {
            "target": target,
            "healthy": True,
            "status": "ok",
        }

    def _run_diagnostic(self, target: str, type: str = "basic") -> Dict[str, Any]:
        """运行诊断"""
        logger.info(f"Running {type} diagnostic for {target}")
        # 实际实现应调用诊断工具
        return {
            "target": target,
            "type": type,
            "healthy": True,
            "status": "ok",
        }

    def _collect_service_metrics(
        self,
        service_name: str,
        time_range_hours: int = 1,
    ) -> Dict[str, Any]:
        """收集服务级指标（请求量、错误率、延迟、连接池等）。"""
        logger.info(f"Collecting service metrics for {service_name} over last {time_range_hours}h")
        safe_service = observability_client._safe_label(service_name)
        result: Dict[str, Any] = {
            "service": safe_service,
            "time_range_hours": time_range_hours,
        }

        # 1. 优先从 Prometheus 取标准 SLI
        try:
            if observability_client.get_prometheus_url():
                prom_metrics = observability_client.query_service_metrics(
                    safe_service, time_range_hours
                )
                result.update(
                    {k: v for k, v in prom_metrics.items() if k not in ("source", "service")}
                )
                result["prometheus_available"] = True
        except Exception as e:
            logger.warning(f"Prometheus service metrics query failed: {e}")

        # 2. 再从 ServiceMonitoringManager 合并内存中的指标
        try:
            from core.service_monitoring_manager import get_service_monitoring_manager

            mgr = get_service_monitoring_manager()
            metrics = mgr.get_service_metrics(
                service_name, time_range=timedelta(hours=time_range_hours)
            )
            manager_metrics = {}
            for m in metrics:
                key = str(getattr(m, "metric_name", m))
                manager_metrics[key] = {
                    "value": getattr(m, "value", None),
                    "timestamp": getattr(m, "timestamp", None),
                }
            if manager_metrics:
                result["manager_metrics"] = manager_metrics
        except Exception as e:
            logger.warning(f"Service monitoring manager collection failed: {e}")

        # 3. 兜底结构，提示数据缺失
        if "prometheus_available" not in result and "manager_metrics" not in result:
            result["metrics"] = {
                "request_rate": "unknown",
                "error_rate": "unknown",
                "latency_p95": "unknown",
                "connection_pool_usage": "unknown",
            }
            result["note"] = "No Prometheus or service monitoring manager data available"
        return result

    def _collect_network_metrics(self, target: str, duration: int = 60) -> Dict[str, Any]:
        """收集网络指标（丢包率、延迟、DNS 解析失败等）。"""
        logger.info(f"Collecting network metrics for {target} over {duration}s")
        try:
            safe_target = observability_client._safe_label(target)
            metrics = observability_client.query_network_metrics(safe_target)
            metrics["duration"] = duration
            return metrics
        except Exception as e:
            logger.warning(f"Network metrics collection failed: {e}")
        return {
            "target": target,
            "packet_loss_percent": None,
            "latency_ms": None,
            "dns_resolution_error_rate": None,
            "note": "Network metric collection requires network monitoring integration",
        }

    def _collect_change_events(
        self,
        target: str,
        hours: int = 24,
        change_events: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """收集最近的变更记录（外部 CI/CD API + 本地配置审计日志）。"""
        logger.info(f"Collecting change events for {target} in last {hours}h")
        safe_target = observability_client._safe_label(target)
        events = list(change_events) if change_events else []

        # 1. 外部变更/发布事件 API
        try:
            ext_events = observability_client.query_change_events(safe_target, hours)
            if isinstance(ext_events, list):
                for e in ext_events:
                    if isinstance(e, dict):
                        events.append(e)
        except Exception as e:
            logger.warning(f"External change events API failed: {e}")

        # 2. 本地配置审计日志
        try:
            from core.config_manager import config_manager

            cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).timestamp()
            for entry in getattr(config_manager, "_audit_log", []):
                if not isinstance(entry, dict):
                    continue
                ts = entry.get("timestamp", 0)
                if isinstance(ts, (int, float)) and ts >= cutoff:
                    target_match = target in str(entry.get("change", ""))
                    if target == "all" or target_match:
                        events.append(
                            {
                                "timestamp": ts,
                                "type": entry.get("type", "config_change"),
                                "target": entry.get("change", ""),
                                "description": str(entry.get("details", ""))[:200],
                            }
                        )
        except Exception as e:
            logger.warning(f"Local change event collection failed: {e}")

        return sorted(events, key=lambda x: x.get("timestamp", 0), reverse=True)[:100]

    def _collect_kubernetes_events(
        self,
        namespace: str = "default",
        field_selector: str = "",
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """收集 Kubernetes 事件（如 OOMKilled、节点异常）。"""
        logger.info(f"Collecting Kubernetes events for namespace={namespace}")
        try:
            safe_ns = observability_client._safe_label(namespace)
            events = observability_client.query_kubernetes_events(
                safe_ns if safe_ns not in ("all", "*") else None,
                field_selector or None,
                limit=limit,
            )
            if isinstance(events, list):
                return events[:limit]
        except Exception as e:
            logger.warning(f"Kubernetes event collection failed: {e}")
        return []

    def _collect_container_metrics(
        self,
        pod_name: str,
        namespace: str = "default",
        container_metrics: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """收集容器指标（内存使用、Limit、OOM 状态）。"""
        logger.info(f"Collecting container metrics for {pod_name}/{namespace}")
        safe_pod = observability_client._safe_label(pod_name)
        safe_ns = observability_client._safe_label(namespace)
        if container_metrics:
            return {"pod_name": safe_pod, "namespace": safe_ns, **container_metrics}

        result: Dict[str, Any] = {
            "pod_name": safe_pod,
            "namespace": safe_ns,
        }
        try:
            pod = observability_client.query_kubernetes_pod(safe_pod, safe_ns)
            result["kubernetes_available"] = pod.get("available", False)
            result["phase"] = pod.get("phase")
            result["last_state"] = pod.get("last_state", {})

            if observability_client.get_prometheus_url():
                result["memory_usage_bytes"] = observability_client._extract_prom_scalar_value(
                    observability_client.query_prometheus(
                        f"container_memory_working_set_bytes{{pod='{safe_pod}',namespace='{safe_ns}'}}"  # noqa: E501
                    )
                )
                result["memory_limit_bytes"] = observability_client._extract_prom_scalar_value(
                    observability_client.query_prometheus(
                        f"container_spec_memory_limit_bytes{{pod='{safe_pod}',namespace='{safe_ns}'}}"  # noqa: E501
                    )
                )
                result["memory_usage_percent"] = (
                    (result["memory_usage_bytes"] / result["memory_limit_bytes"]) * 100.0
                    if result["memory_usage_bytes"] and result["memory_limit_bytes"]
                    else None
                )
        except Exception as e:
            logger.warning(f"Container metric collection failed: {e}")
        if not result.get("kubernetes_available") and "memory_usage_bytes" not in result:
            result["note"] = "No Kubernetes/Prometheus integration configured"
        return result

    def _collect_host_metrics(
        self,
        node_name: str,
        host_metrics: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """收集宿主机指标与硬件错误（EDAC/MCE）。"""
        logger.info(f"Collecting host metrics for {node_name}")
        safe_node = observability_client._safe_label(node_name)
        if host_metrics:
            return {"node_name": safe_node, **host_metrics}

        result: Dict[str, Any] = {"node_name": safe_node}
        try:
            node = observability_client.query_kubernetes_node(safe_node)
            result["kubernetes_available"] = node.get("available", False)
            result["conditions"] = node.get("conditions", {})

            if observability_client.get_prometheus_url():
                result["memory_usage_percent"] = observability_client._extract_prom_scalar_value(
                    observability_client.query_prometheus(
                        f"100 - (node_memory_MemAvailable_bytes{{instance=~'{safe_node}.*'}} / node_memory_MemTotal_bytes * 100)"  # noqa: E501
                    )
                )
                result["edac_correctable_errors"] = observability_client._extract_prom_scalar_value(
                    observability_client.query_prometheus(
                        f"node_edac_correctable_errors_total{{instance=~'{safe_node}.*'}}"
                    )
                )
                result["mce_errors"] = observability_client._extract_prom_scalar_value(
                    observability_client.query_prometheus(
                        f"node_mce_errors_total{{instance=~'{safe_node}.*'}}"
                    )
                )
        except Exception as e:
            logger.warning(f"Host metric collection failed: {e}")
        if not result.get("kubernetes_available") and "memory_usage_percent" not in result:
            result["note"] = "No Kubernetes/Prometheus integration configured"
        return result

    def _collect_database_metrics(
        self,
        database: str,
        time_range_hours: int = 1,
        database_metrics: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """收集数据库指标与慢查询。"""
        logger.info(f"Collecting database metrics for {database} over last {time_range_hours}h")
        safe_database = observability_client._safe_label(database)
        if database_metrics:
            return {"database": safe_database, **database_metrics}

        result: Dict[str, Any] = {"database": safe_database, "time_range_hours": time_range_hours}
        try:
            if observability_client.get_prometheus_url():
                result["slow_query_rate"] = observability_client._extract_prom_scalar_value(
                    observability_client.query_prometheus(
                        f"rate(db_slow_queries_total{{database='{safe_database}'}}[5m])"
                    )
                )
                result["active_connections"] = observability_client._extract_prom_scalar_value(
                    observability_client.query_prometheus(
                        f"db_connections_active{{database='{safe_database}'}}"
                    )
                )
                result["avg_query_duration_ms"] = observability_client._extract_prom_scalar_value(
                    observability_client.query_prometheus(
                        f"(rate(db_query_duration_seconds_sum{{database='{safe_database}'}}[5m]) / rate(db_query_duration_seconds_count{{database='{safe_database}'}}[5m])) * 1000"  # noqa: E501
                    )
                )
        except Exception as e:
            logger.warning(f"Database metric collection failed: {e}")
        if not any(k in result for k in ("slow_query_rate", "active_connections")):
            result["note"] = "No Prometheus database metrics integration configured"
        return result

    def _collect_correlated_alerts(self, service: str, limit: int = 20) -> List[Dict[str, Any]]:
        """收集同时段的关联告警"""
        logger.info(f"Collecting correlated alerts for {service}")
        try:
            from core.alert_engine import alert_history

            all_alerts = [a for a in alert_history if isinstance(a, dict)]
            correlated = []
            for a in all_alerts:
                title = str(a.get("title", ""))
                desc = str(a.get("desc", ""))
                host = str(a.get("host", ""))
                source = str(a.get("source", ""))
                txt = f"{title} {desc} {host} {source}"
                if service in txt or service == "all":
                    correlated.append(
                        {
                            "level": str(a.get("level", "info")),
                            "title": str(a.get("title", ""))[:200],
                            "desc": str(a.get("desc", ""))[:500],
                            "raw_time": str(a.get("raw_time", ""))[:32],
                            "source": str(a.get("source", ""))[:64],
                            "host": str(a.get("host", ""))[:64],
                        }
                    )
            return correlated[:limit]
        except Exception as e:
            logger.warning(f"Correlated alert collection failed: {e}")
        return []

    def _collect_topology(self, service: str) -> Dict[str, Any]:
        """收集服务拓扑与依赖关系"""
        logger.info(f"Collecting topology for {service}")
        try:
            from core.root_cause_intelligence import root_cause_intelligence_engine

            topo_graph = getattr(root_cause_intelligence_engine, "topology_graph", {})
            dependencies: Dict[str, List[str]] = {}
            for node, deps in topo_graph.items():
                dependencies[str(node)] = [str(d) for d in deps]
            downstream = dependencies.get(service, [])
            upstream = [n for n, ds in dependencies.items() if service in ds]
            return {
                "service": service,
                "downstream_dependencies": downstream,
                "upstream_callers": upstream,
                "full_dependencies": dependencies,
            }
        except Exception as e:
            logger.warning(f"Topology collection failed: {e}")
        return {
            "service": service,
            "downstream_dependencies": [],
            "upstream_callers": [],
            "full_dependencies": {},
            "note": "Topology engine not populated",
            "result": "healthy",
        }

    def _dispatch_subagent(
        self,
        goal: str,
        context: Optional[Dict[str, Any]] = None,
        available_tools: Optional[Any] = None,
        role: str = "worker",
        wait: bool = True,
        _depth: int = 0,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """分派子 Agent 执行子任务"""
        # 延迟导入，避免循环依赖
        from .subagent import SubAgentDispatcher

        context = context or {}
        tools: List[str] = []
        if available_tools is None:
            tools = []
        elif isinstance(available_tools, str):
            tools = [t.strip() for t in available_tools.split(",") if t.strip()]
        elif isinstance(available_tools, list):
            tools = [str(t) for t in available_tools]

        dispatcher = SubAgentDispatcher(max_workers=2, dry_run=dry_run)
        try:
            if wait:
                result = dispatcher.dispatch(
                    goal=goal,
                    context=context,
                    available_tools=tools,
                    role=role,
                    wait=True,
                    _depth=_depth,
                )
                return result.to_dict()  # type: ignore[union-attr]

            future = dispatcher.dispatch(
                goal=goal,
                context=context,
                available_tools=tools,
                role=role,
                wait=False,
                _depth=_depth,
            )
            return {
                "agent_id": "pending",
                "status": "dispatched",
                "goal": goal,
                "role": role,
                "future": future,
            }
        finally:
            # 同步等待模式下关闭调度器；异步模式由调用方持有 future
            if wait:
                dispatcher.shutdown(wait=True)


# ----------------------------------------------------------------------
# 4️⃣ 工具选择器
# ----------------------------------------------------------------------
class ToolSelector:
    """工具选择器"""

    def __init__(self, registry: ToolRegistry):
        """
        Parameters
        ----------
        registry : ToolRegistry
            工具注册表
        """
        self.registry = registry

    def select_tool(
        self,
        task_description: str,
        context: Dict[str, Any],
    ) -> Optional[Tool]:
        """
        自动选择工具

        Parameters
        ----------
        task_description : str
            任务描述
        context : Dict[str, Any]
            上下文信息

        Returns
        -------
        Tool or None
            选择的工具
        """
        # 基于关键词匹配（优先匹配更具体的关键词）
        task_lower = task_description.lower()

        # 收集日志（更具体的关键词优先）
        if any(kw in task_lower for kw in ["日志", "log"]):
            tools = self.registry.list_tools(ToolCategory.MONITORING)
            for tool in tools:
                if "log" in tool.name.lower():
                    return tool

        # 收集指标
        if any(kw in task_lower for kw in ["收集", "指标", "监控", "metrics", "collect"]):
            tools = self.registry.list_tools(ToolCategory.MONITORING)
            for tool in tools:
                if "metric" in tool.name.lower():
                    return tool

        # 异常检测
        if any(kw in task_lower for kw in ["异常", "检测", "anomaly", "detect"]):
            tools = self.registry.list_tools(ToolCategory.ANALYSIS)
            for tool in tools:
                if "anomaly" in tool.name.lower():
                    return tool

        # 根因分析
        if any(kw in task_lower for kw in ["根因", "分析", "root cause", "analyze"]):
            tools = self.registry.list_tools(ToolCategory.ANALYSIS)
            for tool in tools:
                if "root" in tool.name.lower():
                    return tool

        # 重启服务
        if any(kw in task_lower for kw in ["重启", "restart"]):
            tools = self.registry.list_tools(ToolCategory.EXECUTION)
            for tool in tools:
                if "restart" in tool.name.lower():
                    return tool

        # 扩缩容
        if any(kw in task_lower for kw in ["扩容", "缩容", "scale"]):
            tools = self.registry.list_tools(ToolCategory.EXECUTION)
            for tool in tools:
                if "scale" in tool.name.lower():
                    return tool

        # 变更/配置/发布/扩缩容
        if any(
            kw in task_lower
            for kw in [
                "变更",
                "配置",
                "发布",
                "部署",
                "扩缩容",
                "change",
                "config",
                "deploy",
                "release",
                "scale",
            ]
        ):
            tools = self.registry.list_tools(ToolCategory.MONITORING)
            for tool in tools:
                if "change" in tool.name.lower():
                    return tool

        # 关联告警/同时段告警
        if any(
            kw in task_lower for kw in ["关联", "同时段", "告警", "correlate", "related", "alert"]
        ):
            tools = self.registry.list_tools(ToolCategory.MONITORING)
            for tool in tools:
                if "correlated" in tool.name.lower():
                    return tool

        # 服务指标 / SLI（流量/错误率/延迟/连接池）
        if any(
            kw in task_lower
            for kw in [
                "服务指标",
                "sli",
                "qps",
                "rps",
                "错误率",
                "延迟",
                "连接池",
                "latency",
                "error rate",
                "connection pool",
                "traffic",
            ]
        ):
            tools = self.registry.list_tools(ToolCategory.MONITORING)
            for tool in tools:
                if "service" in tool.name.lower() and "metric" in tool.name.lower():
                    return tool

        # 网络 / 丢包 / DNS
        if any(
            kw in task_lower
            for kw in ["网络", "丢包", "dns", "network", "packet", "latency", "drop"]
        ):
            tools = self.registry.list_tools(ToolCategory.MONITORING)
            for tool in tools:
                if "network" in tool.name.lower():
                    return tool

        # 数据库 / SQL 慢查询
        if any(
            kw in task_lower
            for kw in [
                "数据库",
                "sql",
                "慢查询",
                "slow query",
                "query",
                "db",
                "connection pool",
            ]
        ):
            tools = self.registry.list_tools(ToolCategory.MONITORING)
            for tool in tools:
                if "database" in tool.name.lower():
                    return tool

        # Kubernetes / 容器 / OOM
        if any(
            kw in task_lower
            for kw in [
                "pod",
                "容器",
                "container",
                "oom",
                "oomkilled",
                "kubernetes",
                "k8s",
                "node",
                "宿主机",
                "host",
            ]
        ):
            tools = self.registry.list_tools(ToolCategory.MONITORING)
            for tool in tools:
                if any(name in tool.name.lower() for name in ["kubernetes", "container", "host"]):
                    return tool

        # 拓扑/依赖
        if any(
            kw in task_lower
            for kw in ["拓扑", "依赖", "dependency", "topology", "upstream", "downstream", "调用链"]
        ):
            tools = self.registry.list_tools(ToolCategory.DIAGNOSTIC)
            for tool in tools:
                if "topolog" in tool.name.lower():
                    return tool

        # 健康检查
        if any(kw in task_lower for kw in ["健康", "检查", "health", "check"]):
            tools = self.registry.list_tools(ToolCategory.DIAGNOSTIC)
            for tool in tools:
                if "health" in tool.name.lower():
                    return tool

        # 如果没有匹配，返回 None
        logger.warning(f"No tool matched for task: {task_description}")
        return None

    def select_tools_for_chain(
        self,
        task_chain: List[str],
        context: Dict[str, Any],
    ) -> List[Tool]:
        """
        为任务链选择工具

        Parameters
        ----------
        task_chain : List[str]
            任务链
        context : Dict[str, Any]
            上下文信息

        Returns
        -------
        List[Tool]
            工具列表
        """
        tools = []

        for task in task_chain:
            tool = self.select_tool(task, context)
            if tool:
                tools.append(tool)

        return tools


# ----------------------------------------------------------------------
# 5️⃣ 工具执行器
# ----------------------------------------------------------------------
class ToolExecutor:
    """工具执行器（支持 dry-run、统一超时、重试、审计脱敏）"""

    def __init__(
        self,
        registry: ToolRegistry,
        dry_run: bool = False,
        default_timeout: Optional[float] = None,
        retry_policy: Optional[Dict[str, Any]] = None,
    ):
        """
        Parameters
        ----------
        registry : ToolRegistry
            工具注册表
        dry_run : bool
            全局 dry-run 开关。为 True 时执行类工具只返回预演结果。
        default_timeout : float
            默认工具执行超时（秒）。
        retry_policy : dict
            重试策略，例如 {"max_retries": 2, "backoff": [1, 2, 4]}。
        """
        self.registry = registry
        self.selector = ToolSelector(registry)
        self.execution_history: List[Dict[str, Any]] = []
        self.dry_run = dry_run
        self.default_timeout = (
            default_timeout if default_timeout is not None else _DEFAULT_TOOL_TIMEOUT
        )
        self.retry_policy = retry_policy or {"max_retries": 2, "backoff": [1, 2, 4]}
        self._sensitive_keys = {
            "password",
            "secret",
            "token",
            "api_key",
            "apikey",
            "credential",
            "auth",
            "private_key",
        }

    def _sanitize_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """脱敏参数：对疑似敏感字段统一替换为 ***。"""
        sanitized: Dict[str, Any] = {}
        for k, v in params.items():
            if any(sk in k.lower() for sk in self._sensitive_keys):
                sanitized[k] = "***"
            elif isinstance(v, dict):
                sanitized[k] = self._sanitize_params(v)
            elif isinstance(v, list):
                sanitized[k] = [
                    (
                        self._sanitize_params({"_": item})["_"]
                        if isinstance(item, dict)
                        else (
                            "***"
                            if isinstance(item, str)
                            and any(sk in k.lower() for sk in self._sensitive_keys)
                            else item
                        )
                    )
                    for item in v
                ]
            else:
                sanitized[k] = v
        return sanitized

    def _should_retry(self, tool: Tool, exc: Exception) -> bool:
        """仅对读/监控/分析类工具的超时或连接类错误重试。"""
        if tool.category == ToolCategory.EXECUTION:
            return False
        if isinstance(exc, asyncio.TimeoutError):
            return True
        if isinstance(exc, (OSError, ConnectionError)):
            return True
        return False

    def _execute_with_retry(
        self,
        tool: Tool,
        dry_run: bool,
        timeout: Optional[float],
        kwargs: Dict[str, Any],
    ) -> Any:
        """统一超时 + 指数退避重试。"""
        max_retries = (
            0
            if tool.category == ToolCategory.EXECUTION
            else self.retry_policy.get("max_retries", 2)
        )
        backoff = self.retry_policy.get("backoff", [1, 2, 4])
        last_exc: Optional[Exception] = None

        for attempt in range(max_retries + 1):
            try:
                return tool.execute(dry_run=dry_run, timeout=timeout, **kwargs)
            except Exception as exc:
                last_exc = exc
                if attempt >= max_retries or not self._should_retry(tool, exc):
                    raise
                sleep_time = (
                    backoff[attempt] if attempt < len(backoff) else backoff[-1] if backoff else 1
                )
                logger.warning(
                    f"Tool {tool.name} execution failed (attempt {attempt + 1}/{max_retries + 1}), "
                    f"retrying after {sleep_time}s: {exc}"
                )
                time.sleep(sleep_time)

        raise last_exc  # pragma: no cover

    def execute_tool(
        self,
        tool_name: str,
        **kwargs,
    ) -> Any:
        """
        执行单个工具

        Parameters
        ----------
        tool_name : str
            工具名称
        **kwargs
            工具参数

        Returns
        -------
        Any
            执行结果
        """
        tool = self.registry.get_tool(tool_name)
        if tool is None:
            raise ValueError(f"Tool not found: {tool_name}")

        dry_run = kwargs.pop("dry_run", self.dry_run)
        timeout = kwargs.pop("timeout", self.default_timeout)

        logger.info(f"Executing tool: {tool_name} (dry_run={dry_run}, timeout={timeout})")

        try:
            result = self._execute_with_retry(tool, dry_run, timeout, kwargs)

            # 记录执行历史（参数脱敏）
            log_params = self._sanitize_params(kwargs)
            self.execution_history.append(
                {
                    "tool": tool_name,
                    "parameters": log_params,
                    "result": str(result),
                    "success": True,
                    "dry_run": dry_run,
                    "timeout": timeout,
                }
            )
            _audit_tool(
                tool_name, "success", {"params": {k: str(v) for k, v in log_params.items()}}
            )

            return result
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")

            log_params = self._sanitize_params(kwargs)
            self.execution_history.append(
                {
                    "tool": tool_name,
                    "parameters": log_params,
                    "result": str(e),
                    "success": False,
                    "dry_run": dry_run,
                    "timeout": timeout,
                }
            )
            _audit_tool(
                tool_name,
                "failure",
                {"error": str(e), "params": {k: str(v) for k, v in log_params.items()}},
            )

            raise

    def execute_chain(
        self,
        tool_chain: List[Tuple[str, Dict[str, Any]]],
    ) -> List[Any]:
        """
        执行工具链

        Parameters
        ----------
        tool_chain : List[Tuple[str, Dict[str, Any]]]
            工具链 [(tool_name, params), ...]

        Returns
        -------
        List[Any]
            执行结果列表
        """
        results = []

        for tool_name, params in tool_chain:
            try:
                result = self.execute_tool(tool_name, **params)
                results.append(result)
            except Exception as e:
                logger.error(f"Chain execution failed at {tool_name}: {e}")
                break

        return results

    def execute_with_auto_selection(
        self,
        task_description: str,
        context: Dict[str, Any],
    ) -> Any:
        """
        自动选择工具并执行

        Parameters
        ----------
        task_description : str
            任务描述
        context : Dict[str, Any]
            上下文信息

        Returns
        -------
        Any
            执行结果
        """
        tool = self.selector.select_tool(task_description, context)
        if tool is None:
            raise ValueError(f"No tool found for task: {task_description}")

        # 从上下文中推断参数
        params = self._infer_parameters(tool, context)

        return self.execute_tool(
            tool.name,
            dry_run=self.dry_run,
            timeout=self.default_timeout,
            **params,
        )

    def _infer_parameters(
        self,
        tool: Tool,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """从上下文推断工具参数（含可选参数）"""
        params = {}

        for param in tool.required_params:
            if param in context:
                params[param] = context[param]
            else:
                # 尝试从上下文中查找相关值或兼容别名
                if param == "target":
                    params[param] = (
                        context.get("service") or context.get("service_name") or "system"
                    )
                elif param == "service":
                    params[param] = (
                        context.get("target") or context.get("service_name") or "unknown"
                    )
                elif param == "service_name":
                    params[param] = context.get("service") or context.get("target") or "unknown"
                elif param == "data":
                    params[param] = context.get("metrics", [])
                elif param == "alert_id":
                    # 从 alert 对象或显式 alert_id 获取
                    alert = context.get("alert") or {}
                    params[param] = alert.get("id") or context.get("alert_id") or "unknown"

        # 同时纳入可选参数（如果上下文中存在），支持 _depth、dry_run 等内部参数传递
        for param in tool.optional_params:
            if param in context:
                params[param] = context[param]
            elif param == "service_name" and "service" in context:
                params[param] = context["service"]
            elif param == "service_name" and "target" in context:
                params[param] = context["target"]

        return params

    def get_execution_statistics(self) -> Dict[str, Any]:
        """获取执行统计"""
        total = len(self.execution_history)
        successful = sum(1 for h in self.execution_history if h["success"])
        failed = total - successful

        return {
            "total": total,
            "successful": successful,
            "failed": failed,
            "success_rate": successful / total if total > 0 else 0,
        }


# ----------------------------------------------------------------------
# 6️⃣ 工厂函数
# ----------------------------------------------------------------------
def create_tool_registry() -> ToolRegistry:
    """创建工具注册表"""
    return ToolRegistry()


def create_tool_executor(registry: Optional[ToolRegistry] = None) -> ToolExecutor:
    """创建工具执行器"""
    if registry is None:
        registry = create_tool_registry()
    return ToolExecutor(registry)


# ----------------------------------------------------------------------
# 7️⃣ CLI 用于快速测试
# ----------------------------------------------------------------------
if __name__ == "__main__":  # pragma: no cover
    pass

    logging.basicConfig(level=logging.INFO)

    # 测试工具注册表
    logger.info("Testing tool registry")
    registry = create_tool_registry()

    tools = registry.list_tools()
    logger.info(f"Registered {len(tools)} tools:")
    for tool in tools:
        logger.info(f"  - {tool.name}: {tool.description}")

    # 测试工具选择
    logger.info("Testing tool selector")
    selector = ToolSelector(registry)

    selected_tool: Optional[Tool] = selector.select_tool("收集系统指标", {"target": "system"})
    logger.info(f"Selected tool: {selected_tool.name if selected_tool else None}")

    # 测试工具执行
    logger.info("Testing tool executor")
    executor = create_tool_executor(registry)

    result = executor.execute_tool("collect_metrics", target="system")
    logger.info(f"Execution result: {result}")

    # 测试执行统计
    stats = executor.get_execution_statistics()
    logger.info(f"Execution statistics: {stats}")

    logger.info("Test passed!")