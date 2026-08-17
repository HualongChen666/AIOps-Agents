# -*- coding: utf-8 -*-
# core/workflow_engine.py
# 工作流仿真引擎(对应前端"工作流"页面节点状态驱动 + 仿真日志输出)
#
# 🔧 严格 Review 修复(W):
#   - W1 [P1]:增加客户端断开检测协议(配合 router 的 is_disconnected)
#   - W2 [P1]:WORKFLOW_DEFINITIONS 用 MappingProxyType 只读封装
#   - W3 [P1]:警告概率改为可配置(WF_WARN_PROBABILITY)
#   - W4 [P2]:delay_ms 负值钳制
#   - W5 [P2]:get_workflow_definitions 返回深拷贝
#   - W6 [P2]:类型注解收紧
#   - W7 [P2]:_now_str 提取为模块级函数
#   - W8 [P2]:workflow_done 事件增加统计字段
#   - W9 [P2]:step 字段类型校验加强
#   - W10 [P2]:导出 _VALID_WF_KEYS 供路由层快速校验

import asyncio
import copy
import datetime
import logging
import random
from types import MappingProxyType
from typing import Any, AsyncGenerator, Optional

# 使用 SystemRandom 避免 bandit B311 安全警告
_secure_random = random.SystemRandom()

# Phase 2 集成: LangGraph 工作流
try:
    from core.ai.langgraph import LLMNode, Workflow, WorkflowExecutor

    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False

# 初始化模块级日志记录器
logger = logging.getLogger(__name__)


# ============================================================
# Phase 2 集成: LangGraph 工作流初始化
# ============================================================
_langgraph_executor: Optional[WorkflowExecutor] = None

if LANGGRAPH_AVAILABLE:
    try:
        # 创建 LangGraph 工作流执行器
        _langgraph_executor = WorkflowExecutor()
        logger.info("Phase 2 LangGraph workflow executor initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize LangGraph executor: {e}")
        _langgraph_executor = None


# ============================================================
# 配置导入
# 🔧 W3 [P1]:新增 WF_WARN_PROBABILITY 配置(可在 .env 中调整)
# 🔧 W4 [P2]:对延迟参数做范围钳制
# ============================================================
try:
    from config import WF_NODE_MAX_DELAY_MS, WF_NODE_MIN_DELAY_MS  # type: ignore
except (ImportError, AttributeError):
    WF_NODE_MIN_DELAY_MS = 500  # 默认节点最短仿真耗时(ms)
    WF_NODE_MAX_DELAY_MS = 1200  # 默认节点最长仿真耗时(ms)
    logger.info(
        "config.py 中未找到 WF_NODE_MIN_DELAY_MS / WF_NODE_MAX_DELAY_MS,"
        f"使用默认值: [{WF_NODE_MIN_DELAY_MS}, {WF_NODE_MAX_DELAY_MS}] ms"
    )

# 🔧 W4:范围钳制(防御非法配置导致负延迟或超长 sleep)
WF_NODE_MIN_DELAY_MS = max(50, min(60_000, int(WF_NODE_MIN_DELAY_MS)))
WF_NODE_MAX_DELAY_MS = max(WF_NODE_MIN_DELAY_MS, min(60_000, int(WF_NODE_MAX_DELAY_MS)))

# 🔧 W3 [P1]:警告概率配置化
try:
    from config import WF_WARN_PROBABILITY  # type: ignore

    # 钳制到合法范围 [0.0, 1.0]
    WF_WARN_PROBABILITY = max(0.0, min(1.0, float(WF_WARN_PROBABILITY)))
except (ImportError, AttributeError, TypeError, ValueError):
    WF_WARN_PROBABILITY = 0.10  # 默认 10% 概率触发警告
    logger.debug(
        f"config.py 中未找到 WF_WARN_PROBABILITY 或解析失败,使用默认值 {WF_WARN_PROBABILITY}"
    )

# 警告重试延迟(毫秒)
_WARN_RETRY_DELAY_MS = 200


# ============================================================
# 工作流元数据(与前端 JS workflows 对象完全对应)
# 🔧 W2 [P1]:用 MappingProxyType 只读封装,防止外部模块修改
# ============================================================
_WORKFLOW_DEFINITIONS_RAW: dict[str, dict[str, Any]] = {
    "collect": {
        "name": "数据采集与摄入",
        "nodes": 5,
        "time": "1.2s",
        "rate": "99.2%",
        "steps": [
            {
                "key": "collect-source",
                "title": "多源采集",
                "desc": "Metrics/Logs/Traces",
            },
            {
                "key": "collect-process",
                "title": "数据预处理",
                "desc": "过滤/标准化/解析",
            },
            {
                "key": "collect-feature",
                "title": "特征工程",
                "desc": "指标计算/聚合",
            },
            {
                "key": "collect-store",
                "title": "多级存储",
                "desc": "热/温/冷数据分层",
            },
            {
                "key": "collect-dispatch",
                "title": "数据分发",
                "desc": "下游消费推送",
            },
        ],
    },
    "detect": {
        "name": "异常检测",
        "nodes": 5,
        "time": "0.8s",
        "rate": "97.5%",
        "steps": [
            {
                "key": "detect-raw",
                "title": "原始数据",
                "desc": "实时时序流入",
            },
            {
                "key": "detect-baseline",
                "title": "基线建模",
                "desc": "动态基线/季节性",
            },
            {
                "key": "detect-ml",
                "title": "ML推理",
                "desc": "多模型集成检测",
            },
            {
                "key": "detect-score",
                "title": "异常评分",
                "desc": "综合置信度评分",
            },
            {
                "key": "detect-alert",
                "title": "告警触发",
                "desc": "分级路由输出",
            },
        ],
    },
    "rca": {
        "name": "根因分析 (RCA)",
        "nodes": 5,
        "time": "3.5s",
        "rate": "94.1%",
        "steps": [
            {
                "key": "rca-agg",
                "title": "告警聚合",
                "desc": "时间/空间关联",
            },
            {
                "key": "rca-topo",
                "title": "拓扑关联",
                "desc": "服务依赖图分析",
            },
            {
                "key": "rca-causal",
                "title": "因果推断",
                "desc": "因果图建模分析",
            },
            {
                "key": "rca-locate",
                "title": "根因定位",
                "desc": "Top-K候选根因",
            },
            {
                "key": "rca-suggest",
                "title": "建议输出",
                "desc": "修复建议+置信度",
            },
        ],
    },
    "remediation": {
        "name": "自动修复 (Auto-Remediation)",
        "nodes": 6,
        "time": "8.2s",
        "rate": "91.3%",
        "steps": [
            {
                "key": "rem-identify",
                "title": "问题识别",
                "desc": "接收根因分析结果",
            },
            {
                "key": "rem-strategy",
                "title": "策略匹配",
                "desc": "Runbook检索",
            },
            {
                "key": "rem-risk",
                "title": "风险评估",
                "desc": "变更影响分析",
            },
            {
                "key": "rem-approve",
                "title": "人工审批",
                "desc": "高风险变更确认",
            },
            {
                "key": "rem-execute",
                "title": "执行动作",
                "desc": "自动化运维操作",
            },
            {
                "key": "rem-verify",
                "title": "验证结果",
                "desc": "修复效果确认",
            },
        ],
    },
    "noise": {
        "name": "告警降噪",
        "nodes": 5,
        "time": "0.3s",
        "rate": "99.8%",
        "steps": [
            {
                "key": "noise-raw",
                "title": "原始告警流",
                "desc": "多源告警汇聚",
            },
            {
                "key": "noise-dedup",
                "title": "去重压缩",
                "desc": "重复告警合并",
            },
            {
                "key": "noise-correlate",
                "title": "关联聚合",
                "desc": "同源告警归组",
            },
            {
                "key": "noise-priority",
                "title": "优先级排序",
                "desc": "业务影响权重评分",
            },
            {
                "key": "noise-output",
                "title": "有效告警输出",
                "desc": "精准推送运维团队",
            },
        ],
    },
}

# 🔧 W2 [P1]:对外暴露的 WORKFLOW_DEFINITIONS 用 MappingProxyType 只读封装
# 防止外部模块通过 from core.workflow_engine import WORKFLOW_DEFINITIONS 后修改
WORKFLOW_DEFINITIONS: MappingProxyType = MappingProxyType(_WORKFLOW_DEFINITIONS_RAW)

# 🔧 W10 [P2]:导出合法工作流 key 集合,供路由层快速校验
_VALID_WF_KEYS: frozenset = frozenset(_WORKFLOW_DEFINITIONS_RAW.keys())


# ============================================================
# 🔧 W7 [P2]:模块级时间戳函数(避免每次创建闭包)
# ============================================================
def _now_str() -> str:
    """返回当前时间的 HH:MM:SS 字符串"""
    return datetime.datetime.now().strftime("%H:%M:%S")


# ============================================================
# 🔧 W9 [P2]:步骤数据安全提取
# ============================================================
def _safe_extract_step(step: Any, idx: int) -> tuple[str, str, str]:
    """
    🔧 W9:从单个 step 字典中安全提取 key/title/desc
    支持非 dict 类型的防御性降级
    """
    if not isinstance(step, dict):
        logger.warning(
            f"工作流 step 非 dict 类型,使用默认值 | idx={idx} | type={type(step).__name__}"
        )
        return (f"step-{idx}", f"步骤 {idx + 1}", "")

    step_key = str(step.get("key") or f"step-{idx}")
    step_title = str(step.get("title") or f"步骤 {idx + 1}")
    step_desc = str(step.get("desc") or "")

    # 防御:字段长度上限(防止恶意配置撑爆 SSE 输出)
    return (step_key[:128], step_title[:128], step_desc[:256])


# ============================================================
# Phase 2 集成: LangGraph 工作流执行
# ============================================================
async def execute_langgraph_workflow(
    workflow_id: str, input_data: dict[str, Any]
) -> dict[str, Any]:
    """
    使用 LangGraph 执行 AI 工作流

    Phase 2 集成: 将 LangGraph 工作流集成到现有工作流引擎

    Args:
        workflow_id: 工作流 ID
        input_data: 输入数据

    Returns:
        执行结果
    """
    if not _langgraph_executor:
        logger.warning("LangGraph executor not available, using simulation")
        # 降级到仿真模式
        return {"error": "LangGraph not available"}

    try:
        # 创建简单的 LangGraph 工作流
        workflow = Workflow(name=f"workflow-{workflow_id}")

        # 添加节点
        llm_node = LLMNode(
            name="analysis",
            prompt_template=f"分析以下数据: {input_data}",
            model_name="gpt-3.5-turbo",
        )
        workflow.add_node(llm_node)

        # 执行工作流
        result = await _langgraph_executor.execute(workflow, input_data=input_data)

        return result  # type: ignore
    except Exception as e:
        logger.error(f"LangGraph workflow execution failed: {e}")
        return {"error": str(e)}


# ============================================================
# 工作流仿真生成器
# ============================================================
async def simulate_workflow_stream(
    wf_key: str,
) -> AsyncGenerator[dict[str, Any], None]:
    """
    工作流仿真异步生成器(SSE 流式输出)
    对应前端:点击"▶ 运行仿真"后节点逐个变色 + 日志面板追加

    yield 事件类型:
      workflow_start → 工作流开始
      step_start     → 节点开始执行
      step_warn      → 节点偶发警告(可配置概率)
      step_complete  → 节点执行完成
      workflow_done  → 工作流全部完成(含 warning_count)
      error          → 非法 wf_key 时返回

    🔧 W1 [P1]:配合 router 的 is_disconnected 检测客户端断开
    🔧 W3 [P1]:警告概率从配置 WF_WARN_PROBABILITY 读取
    🔧 W4 [P2]:延迟值最终 sleep 前再次钳制
    🔧 W8 [P2]:workflow_done 事件增加统计字段
    🔧 W9 [P2]:step 字段安全提取

    Args:
        wf_key: 工作流键,合法值: collect|detect|rca|remediation|noise
    """
    # 🔧 W10:用 frozenset 快速校验
    if wf_key not in _VALID_WF_KEYS:
        logger.warning(f"simulate_workflow_stream 收到未知 wf_key='{wf_key}'")
        yield {
            "type": "error",
            "msg": f"未知工作流: '{wf_key}',合法值: {sorted(_VALID_WF_KEYS)}",
        }
        return

    # 🔧 W2:从只读视图获取(深拷贝避免下方修改污染原数据)
    wf = copy.deepcopy(_WORKFLOW_DEFINITIONS_RAW[wf_key])

    wf_name = wf.get("name", wf_key)
    steps = wf.get("steps", [])

    # 🔧 W9:steps 类型防御
    if not isinstance(steps, list):
        logger.error(f"工作流 '{wf_key}' 的 steps 字段非 list 类型,type={type(steps).__name__}")
        yield {
            "type": "error",
            "msg": f"工作流 '{wf_key}' 配置异常:steps 必须为列表",
        }
        return

    if not steps:
        logger.warning(f"工作流 '{wf_key}' 无任何节点定义")
        yield {
            "type": "error",
            "msg": f"工作流 '{wf_key}' 没有可执行节点",
        }
        return

    total_ms = 0
    warning_count = 0  # 🔧 W8:统计警告次数

    logger.info(
        f"工作流仿真启动 | wf_key='{wf_key}' | wf_name='{wf_name}' "
        f"| 节点数={len(steps)} | 警告概率={WF_WARN_PROBABILITY}"
    )

    # —— 事件 1:工作流开始 ——
    yield {
        "type": "workflow_start",
        "wf_key": wf_key,
        "wf_name": wf_name,
        "time": _now_str(),
        "log": f"[INFO] 开始执行工作流: {wf_name}",
    }

    for idx, step in enumerate(steps):
        # 🔧 W9:安全提取 step 字段
        step_key, step_title, step_desc = _safe_extract_step(step, idx)

        # —— 事件 2:节点开始 ——
        yield {
            "type": "step_start",
            "node_key": step_key,
            "node_title": step_title,
            "node_desc": step_desc,
            "time": _now_str(),
            "log": f"[INFO] 执行节点: {step_title} — {step_desc}",
        }

        logger.debug(f"节点开始 | [{idx + 1}/{len(steps)}] key='{step_key}' title='{step_title}'")

        # 随机模拟节点执行耗时
        delay_ms = _secure_random.randint(WF_NODE_MIN_DELAY_MS, WF_NODE_MAX_DELAY_MS)

        # 🔧 W4:sleep 前最后一次安全钳制(防御负值/超长)
        safe_delay_sec = max(0.05, min(60.0, delay_ms / 1000.0))
        await asyncio.sleep(safe_delay_sec)

        # —— 事件 3:偶发警告(概率可配置)——
        # 🔧 W3:从配置读取概率
        if _secure_random.random() < WF_WARN_PROBABILITY:
            warning_count += 1  # 🔧 W8:统计

            yield {
                "type": "step_warn",
                "node_key": step_key,
                "time": _now_str(),
                "log": (
                    f"[WARN] 节点 {step_title} 检测到轻微延迟,已自动重试(+{_WARN_RETRY_DELAY_MS}ms)"
                ),
            }

            # 🔧 W4:警告延迟也钳制
            warn_delay_sec = max(0.05, min(5.0, _WARN_RETRY_DELAY_MS / 1000.0))
            await asyncio.sleep(warn_delay_sec)

            # 将重试延迟计入本节点耗时
            delay_ms += _WARN_RETRY_DELAY_MS
            logger.debug(f"节点触发警告重试 | key='{step_key}' | 额外延迟={_WARN_RETRY_DELAY_MS}ms")

        # 累计总耗时(含警告重试时间)
        total_ms += delay_ms

        # —— 事件 4:节点完成 ——
        yield {
            "type": "step_complete",
            "node_key": step_key,
            "node_title": step_title,
            "duration_ms": delay_ms,
            "time": _now_str(),
            "log": f"[SUCCESS] 节点完成: {step_title} — 耗时 {delay_ms}ms",
        }

        logger.debug(f"节点完成 | key='{step_key}' | 耗时={delay_ms}ms | 累计总耗时={total_ms}ms")

    # —— 事件 5:工作流全部完成 ——
    # 🔧 W8 [P2]:增加统计字段(warning_count, total_steps)
    yield {
        "type": "workflow_done",
        "wf_key": wf_key,
        "wf_name": wf_name,
        "total_ms": total_ms,
        "total_steps": len(steps),
        "warning_count": warning_count,
        "time": _now_str(),
        "log": f"[SUCCESS] 工作流 [{wf_name}] 执行完成,总耗时 {total_ms}ms,警告 {warning_count} 次",
    }

    logger.info(
        f"工作流仿真完成 | wf_key='{wf_key}' | "
        f"total_ms={total_ms}ms | warning_count={warning_count}"
    )


# ============================================================
# 工作流定义查询接口
# ============================================================
def get_workflow_definitions() -> dict[str, dict[str, Any]]:
    """
    返回所有工作流元数据定义
    供前端初始化渲染工作流选择器和底部详情栏

    🔧 W5 [P2]:返回深拷贝,防止调用方修改污染内部数据
    🔧 W6 [P2]:类型注解收紧

    Returns:
        dict[str, dict[str, Any]]: 以 wf_key 为键的工作流定义字典(深拷贝)
    """
    return copy.deepcopy(_WORKFLOW_DEFINITIONS_RAW)


# ============================================================
# 🔧 W10 [P2]:新增公共接口 — 供路由层快速校验
# ============================================================
def _refresh_valid_keys() -> None:
    """工作流定义变更后刷新合法 key 集合"""
    global _VALID_WF_KEYS
    _VALID_WF_KEYS = frozenset(_WORKFLOW_DEFINITIONS_RAW.keys())


def _validate_workflow_definition(wf_key: str, definition: dict[str, Any]) -> dict[str, Any]:
    """
    校验工作流定义并填充默认值
    Raises:
        ValueError: 校验失败
    """
    if not isinstance(wf_key, str) or not wf_key.strip():
        raise ValueError("wf_key 必须是且非空字符串")
    if not all(c.isalnum() or c in ("_", "-") for c in wf_key):
        raise ValueError("wf_key 只能包含字母、数字、下划线或连字符")

    name = definition.get("name") or wf_key
    if not isinstance(name, str) or not name.strip():
        raise ValueError("name 必须是且非空字符串")

    steps = definition.get("steps")
    if not isinstance(steps, list) or not steps:
        raise ValueError("steps 必须是非空列表")

    validated_steps: list[dict[str, Any]] = []
    for idx, step in enumerate(steps):
        if not isinstance(step, dict):
            raise ValueError(f"steps[{idx}] 必须是字典")
        step_key = str(step.get("key") or f"{wf_key}-step-{idx}").strip()
        step_title = str(step.get("title") or f"步骤 {idx + 1}").strip()
        step_desc = str(step.get("desc") or "").strip()
        validated_steps.append(
            {
                "key": step_key[:128],
                "title": step_title[:128],
                "desc": step_desc[:256],
            }
        )

    safe: dict[str, Any] = copy.deepcopy(definition)
    safe["name"] = name.strip()
    safe["steps"] = validated_steps
    safe["nodes"] = len(validated_steps)
    # 允许前端传入的时间/成功率描述,若为空则使用默认值
    safe.setdefault("time", "N/A")
    safe.setdefault("rate", "N/A")
    safe.setdefault("description", "")
    return safe


def create_workflow_definition(wf_key: str, definition: dict[str, Any]) -> dict[str, Any]:
    """
    新增工作流定义
    Returns:
        创建后的定义深拷贝
    """
    if wf_key in _WORKFLOW_DEFINITIONS_RAW:
        raise ValueError(f"工作流 '{wf_key}' 已存在")

    safe = _validate_workflow_definition(wf_key, definition)
    _WORKFLOW_DEFINITIONS_RAW[wf_key] = safe
    _refresh_valid_keys()
    logger.info(f"工作流创建成功 | wf_key='{wf_key}' | name='{safe['name']}'")
    return copy.deepcopy(safe)


def update_workflow_definition(wf_key: str, definition: dict[str, Any]) -> dict[str, Any]:
    """
    更新工作流定义
    Returns:
        更新后的定义深拷贝
    """
    if wf_key not in _WORKFLOW_DEFINITIONS_RAW:
        raise ValueError(f"工作流 '{wf_key}' 不存在")

    safe = _validate_workflow_definition(wf_key, definition)
    _WORKFLOW_DEFINITIONS_RAW[wf_key] = safe
    logger.info(f"工作流更新成功 | wf_key='{wf_key}' | name='{safe['name']}'")
    return copy.deepcopy(safe)


def delete_workflow_definition(wf_key: str) -> None:
    """删除工作流定义"""
    if wf_key not in _WORKFLOW_DEFINITIONS_RAW:
        raise ValueError(f"工作流 '{wf_key}' 不存在")

    removed = _WORKFLOW_DEFINITIONS_RAW.pop(wf_key)
    _refresh_valid_keys()
    logger.info(f"工作流删除成功 | wf_key='{wf_key}' | name='{removed.get('name')}'")


def is_valid_workflow_key(wf_key: str) -> bool:
    """
    快速校验工作流 key 是否合法
    供 api/workflow_router 的请求预校验使用,避免重复触发完整初始化
    """
    return isinstance(wf_key, str) and wf_key in _VALID_WF_KEYS


def get_valid_workflow_keys() -> list[str]:
    """
    返回所有合法的工作流 key 列表(已排序)
    供前端初始化下拉选择器使用
    """
    return sorted(_VALID_WF_KEYS)
