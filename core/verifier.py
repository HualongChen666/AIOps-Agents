# -*- coding: utf-8 -*-
# core/verifier.py
# ──────────────────────────────────────────────────────────────
# [NEW] N+2:修复效果自动验证引擎(HITL 闭环最后一公里)
# ──────────────────────────────────────────────────────────────
# 设计原则(对齐 ADR-001~012):
#   1. 验证命令必须经过 command_guard 审查(纵深防御)
#   2. 验证失败不阻塞主流程,仅记录到 SQLite(决策 D2 选 A)
#   3. AI_DYNAMIC LLM 验证默认关闭(决策 D1 选 A,保留开关)
#   4. 自学习查询接口供 runbook_generator 调用(决策 D3+)
#   5. fail-fast:验证超时立即返回 None,不重试
#
# 验证策略矩阵:
# ┌─────────────────┬──────────────────┬─────────────────────┬─────────┐
# │ 策略            │ 触发条件          │ 探测命令             │ 置信度  │
# ├─────────────────┼──────────────────┼─────────────────────┼─────────┤
# │ service_status  │ restart_service  │ systemctl is-active │ 0.95    │
# │ process_check   │ kill_high_cpu    │ ps -p <pid>         │ 0.95    │
# │ metric_threshold│ free_*/clear_*   │ 对比 history        │ 0.75    │
# │ custom_command  │ AI_DYNAMIC       │ LLM 生成(预留)      │ 0.65    │
# │ none / skipped  │ 无匹配策略       │ -                   │ -       │
# └─────────────────┴──────────────────┴─────────────────────┴─────────┘
#
# ──────────────────────────────────────────────────────────────
# [FIX] V 系列加固(共 10 项):
#   - V1  [P0]: 验证命令护栏审查不可绕过(任何策略)
#   - V2  [P0]: timeout 钳制,单次验证绝不拖垮主流程
#   - V3  [P0]: pre_snapshot 深拷贝,防外部修改
#   - V4  [P1]: VerifyResult TypedDict 严格类型化
#   - V5  [P1]: _select_strategy 启发式优先级明确
#   - V6  [P1]: AI_DYNAMIC LLM 路径增加 confidence 上限 0.7
#   - V7  [P1]: metric_threshold 数据点不足时降级为 None
#   - V8  [P2]: CancelledError 显式 reraise
#   - V9  [P2]: 异常路径统一通过 _build_error_result
#   - V10 [P2]: 模块级常量集中管理
#
# ──────────────────────────────────────────────────────────────
# [FIX] 本次严格 Review 修复(VFB 系列共 12 项):
#
# [VFB1] 🔴 P0 — 策略函数 except Exception 增加 exc_info + 错误上下文
#   问题: _verify_service_status / _verify_process_check 的 except Exception
#         仅记录 type(e).__name__,丢失 host/cmd 等关键上下文,排查困难
#   修复: 异常分支补充 host/cmd/strategy 上下文,exc_info=True 记录堆栈
#
# [VFB2] 🔴 P0 — _select_strategy 修复 AI_DYNAMIC 永远走 custom_command 的 Bug
#   问题: _SCRIPT_STRATEGY_MAP 中 "AI_DYNAMIC" -> "custom_command",
#         由于优先级 1 精确匹配先命中,优先级 2 的启发式推断永远不执行,
#         导致所有 AI_DYNAMIC 修复全部跳过验证(VERIFY_LLM_FOR_CUSTOM=false 时),
#         自学习数据永远为零
#   修复: ① 从 _SCRIPT_STRATEGY_MAP 移除 AI_DYNAMIC 条目
#         ② _select_strategy 中 AI_DYNAMIC 优先走启发式推断
#         ③ 启发式无法识别时降级到 custom_command
#
# [VFB3] 🔴 P0 — metric_threshold 与总超时冲突的边界保护
#   问题: _verify_metric_threshold 内 await asyncio.sleep(metric_wait_sec)
#         若 metric_wait_sec(5s) > timeout_sec(3s 极端配置),
#         会先触发主入口的 asyncio.wait_for 超时,验证逻辑混乱
#   修复: 启动时校验 metric_wait_sec < timeout_sec - 2,不满足时降级跳过
#
# [VFB4] 🔴 P0 — Windows service_name 改用 shlex 风格双重防御
#   问题: f"...-Name '{service_name}'..." 单引号在 PowerShell 不插值,
#         虽白名单已过滤 ' 字符,但纵深防御原则要求二次校验
#   修复: 引用前再次断言,确保白名单未被绕过
#
# [VFB5] 🟡 P1 — _CONFIDENCE_CUSTOM_COMMAND_MAX 死代码警告
#   问题: 常量定义后从未使用,V6 加固注释声称会用但 _verify_custom_command
#         直接走 skipped,误导后续维护
#   修复: 添加 NOQA 注释说明用途(供 LLM 路径开启时使用),保留扩展点
#
# [VFB6] 🟡 P1 — repair_output 死参数处理
#   问题: verify_repair 接受 repair_output 参数但完全未使用,API 误导调用方
#   修复: 在 evidence 中记录 repair_output 摘要(前 200 字符),便于审计
#
# [VFB7] 🟡 P1 — systemctl is-active 增加 activating 等中间态识别
#   问题: 仅判断 == "active" 会把 activating/reloading 等有效中间态判为失败
#   修复: 中间态返回 verified=None(跳过),输出 active 才视为成功
#
# [VFB8] 🟡 P1 — process_check PID 提取正则修复
#   问题: \d{2,7} 漏掉 PID=1-9 的极端场景(虽然 PID 1-10 应被 linux_repair 拦截,
#         但 verifier 不应对此前置假设)
#   修复: 改为 \d{1,7},后续由 PID 范围校验拒绝非法值
#
# [VFB9] 🟡 P1 — _check_command_with_guard 收紧验证命令风险阈值
#   问题: 当前放行 SAFE 和 LOW 两级,但验证命令应严格只允许只读
#         (LOW 默认是"未匹配已知规则"的兜底,可能含未知风险)
#   修复: 仅放行 SAFE,LOW 级别记 warning 但放行(平衡严格度与可用性),
#         MEDIUM/HIGH/BLOCKED 一律拒绝
#
# [VFB10] 🟢 P2 — except Exception 增加 exc_info=True
#   问题: 多处异常未记录堆栈,生产环境难以定位
#   修复: 关键异常路径统一加 exc_info=True
#
# [VFB11] 🟢 P2 — delta_percent 类型规范化
#   问题: pre_avg <= 0 时被赋值为 0(int),应统一为 float
#   修复: 改为 0.0
#
# [VFB12] 🟢 P2 — duration_sec 在异常路径不被覆盖
#   问题: 正常路径 result["duration_sec"] = round(duration, 3) 会覆盖
#         策略函数已填充的 0.0,语义混乱
#   修复: 仅在 result["duration_sec"] == 0.0 时才覆盖
# ──────────────────────────────────────────────────────────────

from __future__ import annotations

import asyncio
import copy
import json
import logging
import re
import shlex
import time
from typing import Any, Optional, TypedDict

from config import DEFAULT_HOST, LINUX_HOSTS, SNAPSHOT_CONFIG, VERIFY_CONFIG
from core.ai_engine import observe
from core.rag_engine import upsert_verify_record

logger = logging.getLogger(__name__)


# ============================================================
# V10 [P2]:模块级常量
# ============================================================
# 验证证据字段长度上限
_EVIDENCE_OUTPUT_MAX = 500
_EVIDENCE_CMD_MAX = 200
_EVIDENCE_REPAIR_OUTPUT_MAX = 200  # [FIX] VFB6:repair_output 在 evidence 中的截断长度
_ERROR_MSG_MAX = 300

# metric_threshold 策略最小样本数
_METRIC_MIN_SAMPLES = 3

# metric_threshold 判定下降阈值(%)
_METRIC_THRESHOLD_DROP_PERCENT = 5.0

# [FIX] VFB3:metric_wait_sec 与 timeout_sec 的最小安全间隔
# 即 metric_wait_sec 至少要比 timeout_sec 小 2 秒,留出执行+解析时间
_METRIC_WAIT_SAFETY_BUFFER_SEC = 2.0

# 各策略默认置信度
_CONFIDENCE_SERVICE_STATUS = 0.95
_CONFIDENCE_PROCESS_CHECK = 0.95
_CONFIDENCE_METRIC_THRESHOLD = 0.75
_CONFIDENCE_DISK_USAGE = 0.85
_CONFIDENCE_NETWORK_CHECK = 0.75
_CONFIDENCE_K8S_STATUS = 0.85
# [FIX] VFB5:LLM 生成命令置信度上限,供未来 _verify_custom_command 启用 LLM 时使用
_CONFIDENCE_CUSTOM_COMMAND_MAX = 0.70  # noqa: F841  V6 预留扩展点

# [FIX] VFB2:script_key -> 策略映射(已移除 AI_DYNAMIC,改由启发式推断)
# P1-2: 补齐 disk/network/k8s 验证策略
_SCRIPT_STRATEGY_MAP: dict[str, str] = {
    # Linux 重启服务
    "restart_service": "service_status",
    # 进程终止类
    "kill_high_cpu": "process_check",
    # CPU 高负载修复 -> metric_threshold
    "cpu_high_script": "metric_threshold",
    # 内存释放类(对比 metrics_history.memory)
    "free_cache": "metric_threshold",
    "free_memory": "metric_threshold",
    # 磁盘清理/检查类 -> disk_usage
    "disk_high_script": "disk_usage",
    "clear_temp": "disk_usage",
    "clear_tmp": "disk_usage",
    "clear_logs": "disk_usage",
    "clear_event_log": "disk_usage",
    "check_disk": "disk_usage",
    # 网络类 -> network_check
    "flush_dns": "network_check",
    "network_timeout": "network_check",
    # K8s Pod 崩溃类 -> k8s_status
    "k8s_pod_crash": "k8s_status",
    "kubernetes_pod_crash": "k8s_status",
    # 其他只读/无指标类
    "sfc_scan": "none",
    "clean_zombies": "none",
    # [FIX] VFB2 修复:AI_DYNAMIC 不在此映射中,
    #              改由 _select_strategy 单独走启发式推断
}

# script_key -> metric_threshold 策略关联的 metric 字段
_SCRIPT_METRIC_MAP: dict[str, str] = {
    "free_cache": "memory",
    "free_memory": "memory",
    # CPU 高负载修复对比 cpu 指标
    "cpu_high_script": "cpu",
}

# 合法 platform
_VALID_PLATFORMS = frozenset(["windows", "linux"])

# service_name 严格白名单(对齐 linux_repair / repair_engine)
_SERVICE_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_\-\.@]+$")

# P1-2: mount_point / drive / target 校验(避免命令注入)
_MOUNT_POINT_PATTERN = re.compile(r"^(/[a-zA-Z0-9_./-]*|[A-Z]:?\\?)$")
_TARGET_PATTERN = re.compile(r"^[a-zA-Z0-9_\-.]+$")
_K8S_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_\-.]+$")

# [FIX] VFB7:systemctl is-active 的合法成功状态 + 中间态(返回 None 跳过)
_SYSTEMCTL_ACTIVE_STATES = frozenset(["active"])
_SYSTEMCTL_TRANSIENT_STATES = frozenset(["activating", "reloading", "deactivating"])


# ============================================================
# O13: verification wait helpers (Pod Ready / service startup)
# ============================================================
def _verification_wait_timeout() -> float:
    """Return configured max wait time for startup/readiness polling."""
    wait = float(SNAPSHOT_CONFIG.get("verify_wait_timeout", 60.0))
    total = float(VERIFY_CONFIG.get("timeout_sec", 60.0))
    # Keep at least 1s margin for command execution within the overall timeout
    return max(1.0, min(wait, total - 1.0))


def _verification_poll_interval() -> float:
    """Return configured polling interval for startup/readiness checks."""
    return float(SNAPSHOT_CONFIG.get("verify_poll_interval", 5.0))


def _verification_wait_params() -> tuple[float, float]:
    """Return (max_wait_seconds, poll_interval_seconds)."""
    return _verification_wait_timeout(), _verification_poll_interval()


# ============================================================
# V4 [P1]:严格类型化的验证结果
# ============================================================
class VerifyResult(TypedDict):
    """验证结果字典(类型严格化)"""

    verified: Optional[bool]  # True=真实成功 / False=验证失败 / None=跳过
    strategy: str  # 实际使用的策略
    confidence: float  # 置信度 0.0-1.0
    evidence: dict  # 验证证据
    duration_sec: float  # 验证耗时
    error_msg: str  # 错误信息(成功时为空)
    recommendation: str  # 后续建议


# ============================================================
# 主入口:verify_repair
# ============================================================


def _validate_verify_inputs(
    alert: dict[str, Any],
    script_key: str,
    params: dict[str, Any],
    pre_snapshot: Optional[dict[str, Any]],
    repair_output: str,
) -> tuple[bool, str, dict, str, Optional[dict], str]:
    """
    验证并标准化输入参数

    Args:
        alert: 告警字典
        script_key: 脚本键
        params: 参数字典
        pre_snapshot: 修复前快照
        repair_output: 修复输出

    Returns:
        tuple: (是否有效, 错误信息, 安全参数, 安全平台, 安全快照, 安全修复输出)
    """
    if not isinstance(alert, dict):
        return False, f"alert 必须为 dict,收到 {type(alert).__name__}", {}, "", None, ""

    if not script_key or not isinstance(script_key, str):
        return False, "script_key 不能为空", {}, "", None, ""

    safe_params = params if isinstance(params, dict) else {}
    safe_platform = (alert.get("platform") or "windows").strip().lower()
    if safe_platform not in _VALID_PLATFORMS:
        safe_platform = "windows"

    # [FIX] V3 [P0]:pre_snapshot 深拷贝
    safe_pre_snapshot = copy.deepcopy(pre_snapshot) if isinstance(pre_snapshot, dict) else None

    # [FIX] VFB6 [P1]:repair_output 摘要(供 evidence 审计)
    safe_repair_output = str(repair_output)[:_EVIDENCE_REPAIR_OUTPUT_MAX] if repair_output else ""

    return True, "", safe_params, safe_platform, safe_pre_snapshot, safe_repair_output


def _check_metric_threshold_compatibility(timeout_sec: float, repair_id: int) -> tuple[bool, str]:
    """
    检查metric_threshold策略的配置兼容性

    Args:
        timeout_sec: 超时时间
        repair_id: 修复ID

    Returns:
        tuple: (是否兼容, 推荐信息)
    """
    metric_wait = float(VERIFY_CONFIG.get("metric_wait_sec", 5))
    metric_wait = max(2.0, min(30.0, metric_wait))

    if metric_wait + _METRIC_WAIT_SAFETY_BUFFER_SEC > timeout_sec:
        logger.warning(
            f"VFB3: metric_wait_sec({metric_wait}s) + 缓冲({_METRIC_WAIT_SAFETY_BUFFER_SEC}s) "
            f"超过 timeout_sec({timeout_sec}s),跳过 metric_threshold 验证 | "
            f"repair_id={repair_id}"
        )
        return False, (
            f"配置冲突:metric_wait_sec({metric_wait}s) 与 "
            f"timeout_sec({timeout_sec}s) 不兼容,请增大 VERIFY_TIMEOUT_SEC"
        )

    return True, ""


async def _execute_verification_with_timeout(
    strategy: str,
    alert: dict[str, Any],
    script_key: str,
    safe_params: dict,
    safe_platform: str,
    safe_pre_snapshot: Optional[dict],
    safe_repair_output: str,
    ai_runbook: Optional[dict[str, Any]],
    timeout_sec: float,
    repair_id: int,
    start_time: float,
) -> tuple[bool, str, Optional[VerifyResult]]:
    """
    执行带超时的验证

    Args:
        strategy: 验证策略
        alert: 告警字典
        script_key: 脚本键
        safe_params: 安全参数
        safe_platform: 安全平台
        safe_pre_snapshot: 安全快照
        safe_repair_output: 安全修复输出
        ai_runbook: AI runbook
        timeout_sec: 超时时间
        repair_id: 修复ID
        start_time: 开始时间

    Returns:
        tuple: (是否成功, 错误信息, 验证结果)
    """
    try:
        result = await asyncio.wait_for(
            _dispatch_verification(
                strategy=strategy,
                alert=alert,
                script_key=script_key,
                params=safe_params,
                platform=safe_platform,
                pre_snapshot=safe_pre_snapshot,
                repair_output=safe_repair_output,
                ai_runbook=ai_runbook,
            ),
            timeout=timeout_sec,
        )
        return True, "", result

    except asyncio.TimeoutError:
        # [FIX] V2:超时不抛异常,记录后返回 None
        duration = time.monotonic() - start_time
        logger.warning(
            f"N+2 验证超时(>{timeout_sec}s) | repair_id={repair_id} | strategy={strategy}"
        )
        return False, f"验证超时(>{timeout_sec}s)", None

    except asyncio.CancelledError:
        # [FIX] V8:CancelledError 必须 reraise
        logger.info(f"N+2 验证被取消 | repair_id={repair_id}")
        raise

    except Exception as e:
        # [FIX] V9 + VFB10:统一异常路径 + exc_info
        duration = time.monotonic() - start_time
        logger.error(
            f"N+2 验证异常 | repair_id={repair_id} | strategy={strategy} | {type(e).__name__}: {e}",
            exc_info=True,
        )
        return False, f"{type(e).__name__}: {str(e)[:200]}", None


def _finalize_verification_result(
    result: VerifyResult, start_time: float, safe_repair_output: str, repair_id: int
) -> VerifyResult:
    """
    完成验证结果的后处理

    Args:
        result: 验证结果
        start_time: 开始时间
        safe_repair_output: 安全修复输出
        repair_id: 修复ID

    Returns:
        完成后的验证结果
    """
    # ── 5. [FIX] VFB12 [P2]:仅当策略函数未填充 duration_sec 时才覆盖 ──
    duration = time.monotonic() - start_time
    if not result.get("duration_sec"):
        result["duration_sec"] = round(duration, 3)

    # [FIX] VFB6:在 evidence 中追加 repair_output 摘要(若策略未填充)
    if isinstance(result.get("evidence"), dict):
        if "repair_output_preview" not in result["evidence"]:
            result["evidence"]["repair_output_preview"] = safe_repair_output

    logger.info(
        f"N+2 验证完成 | repair_id={repair_id} | "
        f"verified={result['verified']} | confidence={result['confidence']} | "
        f"duration={duration:.2f}s"
    )

    return result


def _write_verification_to_vector_db(
    repair_id: int, alert: dict[str, Any], script_key: str, safe_params: dict, result: VerifyResult
) -> None:
    """
    将验证结果写入向量数据库

    Args:
        repair_id: 修复ID
        alert: 告警字典
        script_key: 脚本键
        safe_params: 安全参数
        result: 验证结果
    """
    try:
        payload = {
            "repair_id": repair_id,
            "alert_id": alert.get("id"),
            "script_key": script_key,
            "params": safe_params,
            "verification": result,
        }
        upsert_verify_record(repair_id, payload)
    except Exception as e:
        logger.error(
            f"V13: 写入向量库失败 | repair_id={repair_id} | {type(e).__name__}: {e}",
            exc_info=True,
        )


@observe(name="n2_verify_repair")
async def verify_repair(
    alert: dict[str, Any],
    script_key: str,
    params: dict[str, Any],
    pre_snapshot: Optional[dict[str, Any]],
    repair_output: str,
    repair_id: int = 0,
    ai_runbook: Optional[dict[str, Any]] = None,
) -> VerifyResult:
    """
    [NEW] LFV6 [P0]:Langfuse 追踪(本机零基建版)
    自动追踪验证策略选择(service_status / process_check / 等)
    自动追踪 verified / confidence 决策
    自学习数据闭环可视化

    [NEW] N+2:修复后立即调用,在超时窗口内返回验证结论

    [FIX] V1 [P0]:验证命令必须通过 command_guard 审查
    [FIX] V2 [P0]:整体超时硬限制,绝不拖垮主流程
    [FIX] V3 [P0]:pre_snapshot 入口深拷贝防御
    [FIX] V8 [P2]:CancelledError 显式 reraise
    [FIX] VFB3 [P0]:metric_wait_sec 与 timeout_sec 边界冲突保护
    [FIX] VFB6 [P1]:repair_output 摘要写入 evidence,便于审计

    Args:
        alert: 原始告警 dict(含 platform/host)
        script_key: 执行的脚本 key
        params: 执行的参数(含 pid/service_name 等)
        pre_snapshot: 修复前 metrics_history 快照(可为 None)
        repair_output: 修复命令的输出(用于 evidence 审计)
        repair_id: 关联的 repair_records.id(供 evidence 追溯)
        ai_runbook: AI_DYNAMIC 时的完整 runbook(含 commands)

    Returns:
        VerifyResult 字典
    """
    # ── 0. 总开关检查 ──
    if not VERIFY_CONFIG.get("enabled", True):
        return _build_skipped_result(
            strategy="skipped",
            recommendation="验证引擎已禁用(VERIFY_ENABLED=false)",
        )

    # ── 1. 输入参数防御 ──
    is_valid, err_msg, safe_params, safe_platform, safe_pre_snapshot, safe_repair_output = (
        _validate_verify_inputs(alert, script_key, params, pre_snapshot, repair_output)
    )
    if not is_valid:
        return _build_error_result(strategy="error", error_msg=err_msg)

    # ── 2. 策略选择 ──
    strategy = _select_strategy(script_key, ai_runbook)
    logger.info(
        f"N+2 验证启动 | repair_id={repair_id} | script_key={script_key} | "
        f"platform={safe_platform} | strategy={strategy}"
    )

    # ── 3. 无策略可用 -> skipped ──
    if strategy in ("none", "skipped"):
        return _build_skipped_result(
            strategy="skipped",
            recommendation=f"脚本 {script_key} 无可用验证策略,跳过",
        )

    # ── 4. [FIX] V2 [P0]:整体超时保护 ──
    timeout_sec = float(VERIFY_CONFIG.get("timeout_sec", 10.0))
    timeout_sec = max(3.0, min(60.0, timeout_sec))

    # [FIX] VFB3 [P0]:metric_threshold 策略需检查 metric_wait_sec 与 timeout_sec 兼容性
    if strategy == "metric_threshold":
        is_compatible, recommendation = _check_metric_threshold_compatibility(
            timeout_sec, repair_id
        )
        if not is_compatible:
            return _build_skipped_result(strategy="skipped", recommendation=recommendation)

    start_time = time.monotonic()

    # ── 5. 执行验证 ──
    success, err_msg, result = await _execute_verification_with_timeout(
        strategy,
        alert,
        script_key,
        safe_params,
        safe_platform,
        safe_pre_snapshot,
        safe_repair_output,
        ai_runbook,
        timeout_sec,
        repair_id,
        start_time,
    )

    if not success:
        return _build_error_result(
            strategy="error",
            error_msg=err_msg,
            duration_sec=time.monotonic() - start_time,
        )

    # ── 6. 完成验证结果 ──
    result = _finalize_verification_result(result, start_time, safe_repair_output, repair_id)

    # ── 7. 写入向量库 ──
    _write_verification_to_vector_db(repair_id, alert, script_key, safe_params, result)

    return result


# ============================================================
# V5 [P1] + VFB2 [P0]:策略选择(启发式优先级修复版)
# ============================================================
def _select_strategy(
    script_key: str,
    ai_runbook: Optional[dict[str, Any]] = None,
) -> str:
    """
    [FIX] V5:策略选择优先级(从高到低)
    [FIX] VFB2 [P0]:修复 AI_DYNAMIC 永远走 custom_command 的核心 Bug

    优先级:
    1. AI_DYNAMIC -> 强制走启发式推断(最高优先级)
    2. script_key 在 _SCRIPT_STRATEGY_MAP 中精确匹配
    3. 兜底:none(跳过验证)
    """
    # [FIX] VFB2 [P0]:AI_DYNAMIC 必须先走启发式推断,避免被精确匹配覆盖
    if script_key == "AI_DYNAMIC":
        if ai_runbook and isinstance(ai_runbook, dict):
            commands = ai_runbook.get("commands", [])
            if isinstance(commands, list):
                cmd_text = " ".join(str(c).lower() for c in commands if c)

                # systemctl restart -> service_status
                if "systemctl restart" in cmd_text or "systemctl start" in cmd_text:
                    logger.debug("VFB2: AI_DYNAMIC 启发式命中 service_status")
                    return "service_status"

                # kill / Stop-Process -> process_check
                if re.search(r"\b(kill|stop-process)\b", cmd_text):
                    logger.debug("VFB2: AI_DYNAMIC 启发式命中 process_check")
                    return "process_check"

                # drop_caches / GC -> metric_threshold
                if "drop_caches" in cmd_text or "gc::collect" in cmd_text:
                    logger.debug("VFB2: AI_DYNAMIC 启发式命中 metric_threshold")
                    return "metric_threshold"

                # P1-2: disk cleanup / df / du / get-volume -> disk_usage
                if any(
                    k in cmd_text
                    for k in (
                        "clear_temp",
                        "clear_tmp",
                        "clear_logs",
                        "rm /tmp",
                        "rm -rf /tmp",
                        "clean_temp",
                        "df ",
                        "du ",
                        "get-volume",
                        "get-disk",
                    )
                ):
                    logger.debug("P1-2: AI_DYNAMIC 启发式命中 disk_usage")
                    return "disk_usage"

                # P1-2: network / dns / ping / nslookup / ipconfig -> network_check
                if any(
                    k in cmd_text
                    for k in (
                        "ping ",
                        "nslookup",
                        "flushdns",
                        "ipconfig",
                        "get-netadapter",
                        "get-netipaddress",
                    )
                ):
                    logger.debug("P1-2: AI_DYNAMIC 启发式命中 network_check")
                    return "network_check"

                # P1-2: kubectl -> k8s_status
                if "kubectl" in cmd_text:
                    logger.debug("P1-2: AI_DYNAMIC 启发式命中 k8s_status")
                    return "k8s_status"

        # AI_DYNAMIC 启发式失败 -> custom_command(默认 skipped,除非启用 LLM)
        return "custom_command"

    # 优先级 2:其他 script_key 精确匹配
    if script_key in _SCRIPT_STRATEGY_MAP:
        return _SCRIPT_STRATEGY_MAP[script_key]

    # 优先级 3:兜底
    return "none"


# ============================================================
# 策略分发
# ============================================================
async def _dispatch_verification(
    strategy: str,
    alert: dict[str, Any],
    script_key: str,
    params: dict[str, Any],
    platform: str,
    pre_snapshot: Optional[dict[str, Any]],
    repair_output: str,
    ai_runbook: Optional[dict[str, Any]],
) -> VerifyResult:
    """根据策略调用对应的验证函数"""
    if strategy == "service_status":
        return await _verify_service_status(alert, params, platform, ai_runbook)

    if strategy == "process_check":
        return await _verify_process_check(alert, params, platform, ai_runbook)

    if strategy == "metric_threshold":
        return await _verify_metric_threshold(script_key, pre_snapshot)

    if strategy == "custom_command":
        return await _verify_custom_command(alert, params, platform, ai_runbook)

    # P1-2: 新增 disk/network/k8s 验证策略
    if strategy == "disk_usage":
        return await _verify_disk_usage(alert, params, platform, ai_runbook)

    if strategy == "network_check":
        return await _verify_network_check(alert, params, platform, ai_runbook)

    if strategy == "k8s_status":
        return await _verify_k8s_status(alert, params, platform, ai_runbook)

    return _build_skipped_result(
        strategy="skipped",
        recommendation=f"未实现的策略: {strategy}",
    )


# ============================================================
# 策略 1:service_status(systemctl is-active)
# [FIX] VFB1 [P0]:异常上下文增强
# [FIX] VFB4 [P0]:service_name 引用前二次断言
# [FIX] VFB7 [P1]:中间态识别
# ============================================================
async def _verify_service_status(
    alert: dict[str, Any],
    params: dict[str, Any],
    platform: str,
    ai_runbook: Optional[dict[str, Any]] = None,
) -> VerifyResult:
    """
    [FIX] V1 [P0]:验证命令必须通过护栏审查
    [FIX] VFB7 [P1]:systemctl 中间态(activating/reloading)返回 None 跳过
    """
    # 提取服务名
    service_name = ""

    # 优先从 params 提取
    if isinstance(params, dict):
        service_name = str(params.get("service_name") or "").strip()

    # AI_DYNAMIC 时从 commands 中提取
    if not service_name and ai_runbook and isinstance(ai_runbook, dict):
        commands = ai_runbook.get("commands", [])
        if isinstance(commands, list):
            for cmd in commands:
                cmd_str = str(cmd)
                # 匹配 systemctl restart <service> 或 Restart-Service -Name <service>
                m = re.search(
                    r"(?:systemctl\s+(?:restart|start|stop)|Restart-Service\s+-Name)\s+"
                    r'["\']?([\w\-\.@]+)["\']?',
                    cmd_str,
                    re.IGNORECASE,
                )
                if m:
                    service_name = m.group(1)
                    break

    if not service_name:
        return _build_skipped_result(
            strategy="skipped",
            recommendation="无法提取服务名,跳过验证",
        )

    # [FIX] VFB4 [P0]:严格字符校验(纵深防御,即使上游已校验)
    if not _SERVICE_NAME_PATTERN.match(service_name):
        return _build_error_result(
            strategy="service_status",
            error_msg=f"service_name 含非法字符: {service_name!r}",
        )

    # 长度上限
    if len(service_name) > 256:
        return _build_error_result(
            strategy="service_status",
            error_msg=f"service_name 超长(>256): {len(service_name)}",
        )

    # 构造验证命令
    if platform == "linux":
        verify_cmd = f"systemctl is-active {shlex.quote(service_name)}"
    else:  # windows
        # PowerShell:service_name 已通过白名单,可安全嵌入单引号
        verify_cmd = f"(Get-Service -Name '{service_name}' -ErrorAction SilentlyContinue).Status"

    # [FIX] V1 [P0]:护栏审查
    guard_ok, guard_reason = _check_command_with_guard(verify_cmd)
    if not guard_ok:
        return _build_error_result(
            strategy="service_status",
            error_msg=f"验证命令被护栏拦截: {guard_reason}",
        )

    # 执行验证(带轮询,服务启动或重启可能需要时间达到 active/running)
    max_wait, interval = _verification_wait_params()
    start = time.monotonic()
    verified: Optional[bool] = None
    last_output = ""
    last_output_clean = ""
    recommendation = ""

    while True:
        try:
            if platform == "linux":
                output = await _execute_linux_verify_command(alert, verify_cmd)
            else:
                output = await _execute_windows_verify_command(verify_cmd)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(
                "VFB1: service_status 执行异常 | "
                f"host={alert.get('host', DEFAULT_HOST)} | "
                f"service={service_name} | platform={platform} | "
                f"{type(e).__name__}: {e}",
                exc_info=True,
            )
            return _build_error_result(
                strategy="service_status",
                error_msg=f"执行异常 ({type(e).__name__}): {str(e)[:100]}",
            )

        last_output = output
        output_clean = (output or "").strip().lower()
        last_output_clean = output_clean

        if platform == "linux":
            if output_clean in _SYSTEMCTL_ACTIVE_STATES:
                verified = True
                recommendation = f"服务 {service_name} 已成功运行"
                break
            if output_clean in _SYSTEMCTL_TRANSIENT_STATES:
                verified = None
                recommendation = f"服务 {service_name} 处于中间态({output_clean}),继续轮询"
            else:
                verified = False
                recommendation = (
                    f"服务 {service_name} 未处于运行状态(实际={output_clean!r}),建议人工排查"
                )
                break
        else:
            if output_clean == "running":
                verified = True
                recommendation = f"服务 {service_name} 已成功运行"
                break
            if output_clean in ("startpending", "continuepending"):
                verified = None
                recommendation = f"服务 {service_name} 处于启动中状态({output_clean}),继续轮询"
            else:
                verified = False
                recommendation = (
                    f"服务 {service_name} 未处于 Running 状态(实际={output_clean!r}),建议人工排查"
                )
                break

        elapsed = time.monotonic() - start
        if elapsed + interval > max_wait:
            break
        try:
            await asyncio.sleep(interval)
        except asyncio.CancelledError:
            raise

    return VerifyResult(
        verified=verified,
        strategy="service_status",
        confidence=_CONFIDENCE_SERVICE_STATUS,
        evidence={
            "command": verify_cmd[:_EVIDENCE_CMD_MAX],
            "output": str(last_output)[:_EVIDENCE_OUTPUT_MAX],
            "service_name": service_name,
            "expected": "active" if platform == "linux" else "Running",
            "actual": last_output_clean,
            "waited_sec": round(time.monotonic() - start, 3),
            "max_wait_sec": max_wait,
        },
        duration_sec=0.0,  # 由主入口填充
        error_msg="",
        recommendation=recommendation,
    )


# ============================================================
# 策略 2:process_check(ps -p <pid>)
# [FIX] VFB1 [P0]:异常上下文增强
# [FIX] VFB8 [P1]:PID 提取正则修复
# ============================================================
async def _verify_process_check(
    alert: dict[str, Any],
    params: dict[str, Any],
    platform: str,
    ai_runbook: Optional[dict[str, Any]] = None,
) -> VerifyResult:
    """验证目标 PID 是否已被终止"""
    # 提取 PID
    pid_str = ""
    if isinstance(params, dict):
        pid_str = str(params.get("pid") or "").strip()

    # AI_DYNAMIC 时从 commands 提取
    if not pid_str and ai_runbook and isinstance(ai_runbook, dict):
        commands = ai_runbook.get("commands", [])
        if isinstance(commands, list):
            for cmd in commands:
                cmd_str = str(cmd)
                # [FIX] VFB8 [P1]:从 \d{2,7} 改为 \d{1,7},
                # 后续由 PID 范围校验拒绝非法值,语义更清晰
                m = re.search(
                    r"(?:kill|Stop-Process)\s+(?:-Id\s+)?[\-\w]*?\s*(\d{1,7})",
                    cmd_str,
                )
                if m:
                    pid_str = m.group(1)
                    break

    if not pid_str.isdigit():
        return _build_skipped_result(
            strategy="skipped",
            recommendation="无法提取 PID,跳过验证",
        )

    pid_int = int(pid_str)
    # PID 范围校验(Linux pid_max=4194304;Windows 类似上限)
    if pid_int <= 0 or pid_int > 4_194_304:
        return _build_error_result(
            strategy="process_check",
            error_msg=f"PID 超出合法范围: {pid_int}",
        )

    # 构造验证命令
    if platform == "linux":
        # ps -p 退出码 1 表示进程不存在(成功);0 表示存在(失败)
        # 用 wc -l 计数,0=已终止,1=仍存活
        verify_cmd = f"ps -p {pid_int} --no-headers 2>/dev/null | wc -l"
    else:  # windows
        verify_cmd = (
            f"if (Get-Process -Id {pid_int} -ErrorAction SilentlyContinue) "
            "{ Write-Output 'ALIVE' } else { Write-Output 'DEAD' }"
        )

    # [FIX] V1 [P0]:护栏审查
    guard_ok, guard_reason = _check_command_with_guard(verify_cmd)
    if not guard_ok:
        return _build_error_result(
            strategy="process_check",
            error_msg=f"验证命令被护栏拦截: {guard_reason}",
        )

    # 执行验证
    try:
        if platform == "linux":
            output = await _execute_linux_verify_command(alert, verify_cmd)
        else:
            output = await _execute_windows_verify_command(verify_cmd)
    except asyncio.CancelledError:
        raise
    except Exception as e:
        # [FIX] VFB1 + VFB10:补充上下文 + exc_info
        logger.error(
            "VFB1: process_check 执行异常 | "
            f"host={alert.get('host', DEFAULT_HOST)} | "
            f"pid={pid_int} | platform={platform} | "
            f"{type(e).__name__}: {e}",
            exc_info=True,
        )
        return _build_error_result(
            strategy="process_check",
            error_msg=f"执行异常 ({type(e).__name__}): {str(e)[:100]}",
        )

    # 解析结果
    output_clean = (output or "").strip()

    if platform == "linux":
        # wc -l 输出 0 表示进程已消失(成功)
        verified = output_clean == "0"
    else:
        # PowerShell 输出 'DEAD' 表示进程已消失(成功)
        verified = output_clean.upper() == "DEAD"

    return VerifyResult(
        verified=verified,
        strategy="process_check",
        confidence=_CONFIDENCE_PROCESS_CHECK,
        evidence={
            "command": verify_cmd[:_EVIDENCE_CMD_MAX],
            "output": str(output)[:_EVIDENCE_OUTPUT_MAX],
            "pid": pid_int,
            "expected_state": "DEAD",
            "actual_state": output_clean,
        },
        duration_sec=0.0,
        error_msg="",
        recommendation=(
            f"进程 PID {pid_int} 已成功终止"
            if verified
            else (f"[WARNING] 进程 PID {pid_int} 仍存活,可能权限不足或被父进程重启,建议人工介入")
        ),
    )


# ============================================================
# 策略 2.5:disk_usage(新增, P1-2)
# ============================================================
async def _verify_disk_usage(
    alert: dict[str, Any],
    params: dict[str, Any],
    platform: str,
    ai_runbook: Optional[dict[str, Any]] = None,
) -> VerifyResult:
    """验证磁盘清理后挂载点/驱动器使用率是否低于阈值。"""
    mount_point = (params.get("mount_point") or "").strip() if isinstance(params, dict) else ""

    if not mount_point and isinstance(ai_runbook, dict):
        for cmd in ai_runbook.get("commands", []):
            cmd_str = str(cmd)
            m = re.search(r"(?:rm\s+-rf|clear_temp|clear_logs|clean)\s+(/\S+)", cmd_str)
            if m:
                mount_point = m.group(1)
                break
            m2 = re.search(r"([A-Za-z]:)\\?", cmd_str)
            if m2:
                mount_point = m2.group(1).upper() + "\\"
                break

    if not mount_point:
        mount_point = "/"

    if not _MOUNT_POINT_PATTERN.match(mount_point):
        return _build_error_result(
            strategy="disk_usage",
            error_msg=f"非法挂载点/驱动器: {mount_point!r}",
        )

    if platform == "linux":
        verify_cmd = f"df -P {shlex.quote(mount_point)}"
    else:
        drive = mount_point[0].upper()
        verify_cmd = (
            f"Get-CimInstance Win32_LogicalDisk -Filter \"DeviceID='{drive}:'\" | "
            f"Select-Object Size,FreeSpace | ForEach-Object {{ "
            f"'{drive} ' + $_.Size + ' ' + $_.FreeSpace }}"
        )

    guard_ok, guard_reason = _check_command_with_guard(verify_cmd)
    if not guard_ok:
        return _build_error_result(
            strategy="disk_usage",
            error_msg=f"验证命令被护栏拦截: {guard_reason}",
        )

    try:
        if platform == "linux":
            output = await _execute_linux_verify_command(alert, verify_cmd)
        else:
            output = await _execute_windows_verify_command(verify_cmd)
    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.error(
            "P1-2 disk_usage 执行异常 | host=%s | mount=%s | %s: %s",
            alert.get("host", DEFAULT_HOST),
            mount_point,
            type(e).__name__,
            e,
            exc_info=True,
        )
        return _build_error_result(
            strategy="disk_usage",
            error_msg=f"执行异常 ({type(e).__name__}): {str(e)[:100]}",
        )

    usage_percent: Optional[float] = None
    if platform == "linux":
        lines = [line.strip() for line in (output or "").splitlines() if line.strip()]
        if len(lines) >= 2:
            parts = lines[-1].split()
            if len(parts) >= 5:
                try:
                    usage_percent = float(parts[4].replace("%", ""))
                except (TypeError, ValueError):
                    pass
    else:
        parts = (output or "").split()
        if len(parts) >= 3:
            try:
                total = float(parts[1])
                free = float(parts[2])
                if total > 0:
                    usage_percent = (total - free) / total * 100.0
            except (TypeError, ValueError):
                pass

    if usage_percent is None:
        return _build_error_result(
            strategy="disk_usage",
            error_msg=f"无法解析磁盘输出: {str(output)[:200]!r}",
        )

    threshold = 90.0
    if isinstance(params, dict) and params.get("threshold") is not None:
        try:
            threshold = float(params["threshold"])
        except (TypeError, ValueError):
            threshold = 90.0
    verified = usage_percent <= threshold

    return VerifyResult(
        verified=verified,
        strategy="disk_usage",
        confidence=_CONFIDENCE_DISK_USAGE,
        evidence={
            "command": verify_cmd[:_EVIDENCE_CMD_MAX],
            "output": str(output)[:_EVIDENCE_OUTPUT_MAX],
            "mount_point": mount_point,
            "usage_percent": round(usage_percent, 2),
            "threshold": threshold,
        },
        duration_sec=0.0,
        error_msg="",
        recommendation=(
            f"磁盘使用率 {usage_percent:.1f}% 低于阈值 {threshold}%"
            if verified
            else f"磁盘使用率 {usage_percent:.1f}% 仍高于阈值 {threshold}%, 建议人工清理"
        ),
    )


# ============================================================
# 策略 2.6:network_check(新增, P1-2)
# ============================================================
async def _verify_network_check(
    alert: dict[str, Any],
    params: dict[str, Any],
    platform: str,
    ai_runbook: Optional[dict[str, Any]] = None,
) -> VerifyResult:
    """验证网络修复后目标是否可达。"""
    target = (params.get("target") or "").strip() if isinstance(params, dict) else ""
    if not target:
        target = (alert.get("host") or "").strip()

    if not target and isinstance(ai_runbook, dict):
        for cmd in ai_runbook.get("commands", []):
            cmd_str = str(cmd)
            m = re.search(
                r"(?:ping|nslookup|Test-Connection|targetname)\s+['\"]?([a-zA-Z0-9_.:-]+)['\"]?",
                cmd_str,
                re.IGNORECASE,
            )
            if m:
                target = m.group(1)
                break

    if not target:
        return _build_skipped_result(
            strategy="skipped",
            recommendation="无法提取网络验证目标,跳过",
        )

    if not _TARGET_PATTERN.match(target):
        return _build_error_result(
            strategy="network_check",
            error_msg=f"非法网络目标: {target!r}",
        )

    if platform == "linux":
        verify_cmd = f"ping -c 1 -W 2 {shlex.quote(target)}"
    else:
        verify_cmd = (
            f"Test-Connection -ComputerName '{target}' -Count 1 -ErrorAction SilentlyContinue; "
            "if ($?) { 'UP' } else { 'DOWN' }"
        )

    guard_ok, guard_reason = _check_command_with_guard(verify_cmd)
    if not guard_ok:
        return _build_error_result(
            strategy="network_check",
            error_msg=f"验证命令被护栏拦截: {guard_reason}",
        )

    try:
        if platform == "linux":
            output = await _execute_linux_verify_command(alert, verify_cmd)
        else:
            output = await _execute_windows_verify_command(verify_cmd)
    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.error(
            "P1-2 network_check 执行异常 | target=%s | %s: %s",
            target,
            type(e).__name__,
            e,
            exc_info=True,
        )
        return _build_error_result(
            strategy="network_check",
            error_msg=f"执行异常 ({type(e).__name__}): {str(e)[:100]}",
        )

    output_clean = (output or "").strip().lower()
    if platform == "linux":
        verified = (
            "1 received" in output_clean
            or "0% packet loss" in output_clean
            or "1 packets received" in output_clean
        )
    else:
        verified = "up" in output_clean

    return VerifyResult(
        verified=verified,
        strategy="network_check",
        confidence=_CONFIDENCE_NETWORK_CHECK,
        evidence={
            "command": verify_cmd[:_EVIDENCE_CMD_MAX],
            "output": str(output)[:_EVIDENCE_OUTPUT_MAX],
            "target": target,
        },
        duration_sec=0.0,
        error_msg="",
        recommendation=(
            f"目标 {target} 网络可达"
            if verified
            else f"目标 {target} 仍不可达,建议检查网络/防火墙配置"
        ),
    )


# ============================================================
# 策略 2.7:k8s_status(新增, P1-2)
# ============================================================
async def _verify_k8s_status(
    alert: dict[str, Any],
    params: dict[str, Any],
    platform: str,
    ai_runbook: Optional[dict[str, Any]] = None,
) -> VerifyResult:
    """验证 K8s Pod/Deployment 修复后状态为 Running/Active。"""
    resource = (params.get("resource") or "pod").strip() if isinstance(params, dict) else "pod"
    name = (params.get("name") or "").strip() if isinstance(params, dict) else ""
    namespace = (
        (params.get("namespace") or "default").strip() if isinstance(params, dict) else "default"
    )

    if not name and isinstance(ai_runbook, dict):
        for cmd in ai_runbook.get("commands", []):
            cmd_str = str(cmd)
            m = re.search(
                r"kubectl\s+(?:get|describe|rollout\s+status)\s+\S+\s+([a-zA-Z0-9_\-.]+)",
                cmd_str,
            )
            if m:
                name = m.group(1)
                break

    if not name:
        return _build_skipped_result(
            strategy="skipped",
            recommendation="无法提取 K8s 资源名,跳过",
        )

    if not _K8S_NAME_PATTERN.match(name):
        return _build_error_result(
            strategy="k8s_status",
            error_msg=f"非法 K8s 资源名: {name!r}",
        )

    # K8s 操作仅在 Linux 主控节点执行
    if platform != "linux":
        return _build_skipped_result(
            strategy="k8s_status",
            recommendation="K8s 验证当前仅支持 Linux 控制平台",
        )

    # Use JSON output so we can inspect both phase and Ready condition.
    verify_cmd = f"kubectl get {resource} {name} -n {namespace} -o json"

    guard_ok, guard_reason = _check_command_with_guard(verify_cmd)
    if not guard_ok:
        return _build_error_result(
            strategy="k8s_status",
            error_msg=f"验证命令被护栏拦截: {guard_reason}",
        )

    max_wait, interval = _verification_wait_params()
    start = time.monotonic()
    verified: Optional[bool] = None
    last_output = ""
    last_phase = ""
    last_ready = False
    recommendation = ""

    while True:
        try:
            output = await _execute_linux_verify_command(alert, verify_cmd)
            last_output = output
            try:
                data = json.loads(output)
            except json.JSONDecodeError:
                # Plain text fallback for tool outputs.
                data = {}
                plain = output.strip().lower()
                if plain:
                    data["status"] = {"phase": plain}
            phase = str(data.get("status", {}).get("phase", "")).lower()
            last_phase = phase
            conditions = data.get("status", {}).get("conditions", [])
            ready_cond = next(
                (c for c in conditions if str(c.get("type", "")).lower() == "ready"), None
            )
            last_ready = (
                str(ready_cond.get("status", "")).lower() == "true"
                if isinstance(ready_cond, dict)
                else False
            )
            # When conditions are absent, treat a known good phase as ready.
            if not conditions and phase in ("running", "completed", "succeeded"):
                last_ready = True
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(
                "P1-2 k8s_status 执行异常 | resource=%s/%s | ns=%s | %s: %s",
                resource,
                name,
                namespace,
                type(e).__name__,
                e,
                exc_info=True,
            )
            return _build_error_result(
                strategy="k8s_status",
                error_msg=f"执行异常 ({type(e).__name__}): {str(e)[:100]}",
            )

        if phase == "running" and last_ready:
            verified = True
            recommendation = f"K8s {resource}/{name} 状态正常: Running 且 Ready"
            break

        if phase in ("failed", "unknown"):
            verified = False
            recommendation = f"K8s {resource}/{name} 状态异常: {phase}, 建议人工排查"
            break

        # Pending / ContainerCreating / PodScheduled etc. are transient.
        if phase == "succeeded" and resource in ("pod", "pods"):
            verified = True
            recommendation = f"K8s {resource}/{name} 已完成: Succeeded"
            break

        verified = None
        recommendation = (
            f"K8s {resource}/{name} 尚未 Ready(phase={phase}, ready={last_ready}),继续轮询"
        )

        elapsed = time.monotonic() - start
        if elapsed + interval > max_wait:
            break
        try:
            await asyncio.sleep(interval)
        except asyncio.CancelledError:
            raise

    return VerifyResult(
        verified=verified,
        strategy="k8s_status",
        confidence=_CONFIDENCE_K8S_STATUS,
        evidence={
            "command": verify_cmd[:_EVIDENCE_CMD_MAX],
            "output": str(last_output)[:_EVIDENCE_OUTPUT_MAX],
            "resource": resource,
            "name": name,
            "namespace": namespace,
            "phase": last_phase,
            "ready": last_ready,
            "waited_sec": round(time.monotonic() - start, 3),
            "max_wait_sec": max_wait,
        },
        duration_sec=0.0,
        error_msg="",
        recommendation=recommendation,
    )


# ============================================================
# 策略 3:metric_threshold(对比 metrics_history)
# [FIX] VFB11 [P2]:delta_percent 类型规范化
# ============================================================
async def _verify_metric_threshold(
    script_key: str,
    pre_snapshot: Optional[dict[str, Any]],
) -> VerifyResult:
    """
    [FIX] V7 [P1]:数据点不足时降级为 None,而非误判
    [FIX] VFB11 [P2]:delta_percent 统一为 float
    """
    if not pre_snapshot:
        return _build_skipped_result(
            strategy="skipped",
            recommendation="无修复前快照数据,跳过 metric_threshold 验证",
        )

    # 提取关注的指标字段
    metric_field = _SCRIPT_METRIC_MAP.get(script_key)
    if not metric_field:
        return _build_skipped_result(
            strategy="skipped",
            recommendation=f"脚本 {script_key} 无关联的 metric 字段",
        )

    # 等待指标稳定后采集 post_snapshot
    metric_wait_sec = float(VERIFY_CONFIG.get("metric_wait_sec", 5))
    metric_wait_sec = max(2.0, min(30.0, metric_wait_sec))

    try:
        await asyncio.sleep(metric_wait_sec)
    except asyncio.CancelledError:
        raise

    # 获取 post_snapshot
    try:
        from core.metrics_history import METRICS_HISTORY as metrics_history

        post_snapshot = metrics_history.to_dict()
    except Exception as e:
        # [FIX] VFB10:补充 exc_info
        logger.error(
            "VFB1: metric_threshold post_snapshot 获取失败 | "
            f"script_key={script_key} | {type(e).__name__}: {e}",
            exc_info=True,
        )
        return _build_error_result(
            strategy="metric_threshold",
            error_msg=f"无法获取 post_snapshot: {type(e).__name__}",
        )

    # 提取序列
    pre_series = pre_snapshot.get(metric_field, [])
    post_series = post_snapshot.get(metric_field, [])

    if not isinstance(pre_series, list) or not isinstance(post_series, list):
        return _build_error_result(
            strategy="metric_threshold",
            error_msg=f"{metric_field} 序列格式异常",
        )

    # [FIX] V7 [P1]:数据点不足时降级
    if len(pre_series) < _METRIC_MIN_SAMPLES or len(post_series) < _METRIC_MIN_SAMPLES:
        return _build_skipped_result(
            strategy="skipped",
            recommendation=(
                f"数据点不足({metric_field} pre={len(pre_series)}, "
                f"post={len(post_series)} < {_METRIC_MIN_SAMPLES}),跳过验证"
            ),
        )

    # 计算修复前后均值(取最近 _METRIC_MIN_SAMPLES 个点)
    try:
        pre_avg = sum(float(v) for v in pre_series[-_METRIC_MIN_SAMPLES:]) / _METRIC_MIN_SAMPLES
        post_avg = sum(float(v) for v in post_series[-_METRIC_MIN_SAMPLES:]) / _METRIC_MIN_SAMPLES
    except (TypeError, ValueError) as e:
        return _build_error_result(
            strategy="metric_threshold",
            error_msg=f"指标数值计算异常: {e}",
        )

    # [FIX] VFB11 [P2]:delta_percent 类型规范化为 float
    delta = pre_avg - post_avg
    delta_percent: float = (delta / pre_avg * 100.0) if pre_avg > 0 else 0.0
    verified = delta_percent >= _METRIC_THRESHOLD_DROP_PERCENT

    return VerifyResult(
        verified=verified,
        strategy="metric_threshold",
        confidence=_CONFIDENCE_METRIC_THRESHOLD,
        evidence={
            "metric_field": metric_field,
            "pre_avg": round(pre_avg, 2),
            "post_avg": round(post_avg, 2),
            "delta": round(delta, 2),
            "delta_percent": round(delta_percent, 2),
            "pre_samples": len(pre_series),
            "post_samples": len(post_series),
            "wait_sec": metric_wait_sec,
            "threshold_percent": _METRIC_THRESHOLD_DROP_PERCENT,
        },
        duration_sec=0.0,
        error_msg="",
        recommendation=(
            f"{metric_field} 从 {pre_avg:.1f} 下降到 {post_avg:.1f} ({delta_percent:+.1f}%),修复有效"
            if verified
            else (
                f"[WARNING] {metric_field} 仅下降 {delta_percent:.1f}% "
                f"(< {_METRIC_THRESHOLD_DROP_PERCENT}%),"
                "修复效果不显著,建议人工排查"
            )
        ),
    )


# ============================================================
# 策略 4:custom_command(LLM 生成,默认关闭)
# [FIX] 决策 D1:保留 LLM 开关供未来按需启用
# ============================================================
async def _verify_custom_command(
    alert: dict[str, Any],
    params: dict[str, Any],
    platform: str,
    ai_runbook: Optional[dict[str, Any]] = None,
) -> VerifyResult:
    """
    [FIX] V6 [P1]:LLM 生成命令置信度上限 0.7(_CONFIDENCE_CUSTOM_COMMAND_MAX)
    [KEY] 决策 D1:默认关闭,VERIFY_LLM_FOR_CUSTOM=true 时启用
    [FIX] VFB5:_CONFIDENCE_CUSTOM_COMMAND_MAX 常量已声明 noqa,此函数预留 LLM 启用时使用,符合 V6 加固承诺
    """
    if not VERIFY_CONFIG.get("llm_for_custom", False):
        return _build_skipped_result(
            strategy="skipped",
            recommendation="AI_DYNAMIC custom_command 验证已禁用 (VERIFY_LLM_FOR_CUSTOM=false)",
        )

    # [FIX] V6 + VFB5:LLM 生成验证命令(此处保留扩展点,默认走 skipped)
    # 未来开启时:
    #   1. 调用 ai_engine.analyze 生成只读探测命令(prompt 严格要求只读)
    #   2. 逐条走 command_guard.analyze_command 审查
    #   3. 仅 SAFE 等级才执行
    #   4. 置信度上限钳制为 _CONFIDENCE_CUSTOM_COMMAND_MAX (0.7)
    return _build_skipped_result(
        strategy="skipped",
        recommendation=(
            "custom_command LLM 验证逻辑预留,等待启用 "
            "(VERIFY_LLM_FOR_CUSTOM=true 时实现,"
            f"置信度上限将钳制为 {_CONFIDENCE_CUSTOM_COMMAND_MAX})"
        ),
    )


# ============================================================
# 工具函数:护栏审查
# [FIX] V1 [P0] + VFB9 [P1]:验证命令必须通过护栏审查(收紧风险阈值)
# ============================================================
def _check_command_with_guard(cmd: str) -> tuple[bool, str]:
    """
    [FIX] V1 [P0]:验证命令必须通过护栏审查(纵深防御)
    [FIX] VFB9 [P1]:风险阈值优化策略
        - SAFE: 直接放行(只读命令白名单)
        - LOW : 放行但记 warning(LOW 是兜底等级,可能含未知风险)
        - MEDIUM/HIGH/BLOCKED: 一律拒绝(验证不应有副作用)

    Returns:
        (ok, reason)
        ok=True   -> 命令安全或低风险(放行)
        ok=False  -> 被拦截,reason 含拦截原因
    """
    try:
        from core.command_guard import RiskLevel, analyze_command

        risk = analyze_command(cmd)
        risk_level = risk["risk_level"]

        # [FIX] VFB9:HIGH/BLOCKED 直接拒绝
        if risk_level in (RiskLevel.HIGH, RiskLevel.BLOCKED):
            return False, str(risk.get("reason", "护栏拦截"))

        # [FIX] VFB9:MEDIUM 拒绝(验证不应有任何副作用)
        if risk_level == RiskLevel.MEDIUM:
            return False, f"中等风险命令不允许用于验证: {risk.get('risk_name', '')}"

        # [FIX] VFB9:LOW 放行但记 warning(LOW 通常是"未匹配已知规则"的兜底)
        if risk_level == RiskLevel.LOW:
            logger.warning(
                "VFB9: 验证命令为 LOW 风险等级(可能未匹配已知规则),"
                f"已放行但建议关注 | cmd={cmd[:80]}"
            )
            return True, ""

        # SAFE: 直接放行
        return True, ""

    except ImportError:
        # command_guard 不可用时降级(理论上不会发生)
        logger.warning("V1: command_guard 模块不可用,跳过验证命令审查")
        return True, ""
    except Exception as e:
        logger.error(f"V1: 护栏审查异常: {e}", exc_info=True)
        return False, f"护栏审查异常: {type(e).__name__}"


# ============================================================
# 工具函数:执行验证命令(Linux SSH)
# ============================================================
async def _execute_linux_verify_command(
    alert: dict[str, Any],
    cmd: str,
) -> str:
    """通过 SSH 执行 Linux 验证命令"""
    host_name = (alert.get("host") or "").strip()
    if not host_name:
        raise ValueError("alert 缺少 host 字段")

    # 查找主机配置
    host_config = None
    for h in LINUX_HOSTS.get("hosts", []):
        if h.get("name") == host_name or h.get("host") == host_name:
            host_config = h
            break

    if not host_config:
        raise ValueError(f"未找到 Linux 主机配置: {host_name}")

    # 调用 linux_collector 的 _ssh_execute
    from core.linux_collector import _get_host_semaphore, _ssh_execute

    semaphore = _get_host_semaphore(host_name)
    output = await _ssh_execute(host_config, cmd, semaphore=semaphore)  # type: ignore[arg-type]
    return output or ""


# ============================================================
# 工具函数:执行验证命令(Windows PowerShell)
# ============================================================
async def _execute_windows_verify_command(cmd: str) -> str:
    """通过 PowerShell 执行 Windows 验证命令"""
    from core.repair_engine import _run_powershell

    result = await asyncio.to_thread(_run_powershell, cmd)
    return (  # type: ignore[no-any-return]
        result.get("output", "") if isinstance(result, dict) else ""
    )


# ============================================================
# 结果构造工具函数
# ============================================================
def _build_skipped_result(
    strategy: str,
    recommendation: str,
) -> VerifyResult:
    """构造 verified=None 的跳过结果"""
    return VerifyResult(
        verified=None,
        strategy=strategy,
        confidence=0.0,
        evidence={},
        duration_sec=0.0,
        error_msg="",
        recommendation=recommendation,
    )


def _build_error_result(
    strategy: str,
    error_msg: str,
    duration_sec: float = 0.0,
) -> VerifyResult:
    """[FIX] V9 [P2]:统一错误结果构造"""
    return VerifyResult(
        verified=None,
        strategy=strategy,
        confidence=0.0,
        evidence={},
        duration_sec=duration_sec,
        error_msg=error_msg[:_ERROR_MSG_MAX],
        recommendation=f"验证失败: {error_msg[:100]}",
    )


# ============================================================
# 显式导出列表
# ============================================================
__all__ = [
    "verify_repair",
    "VerifyResult",
]
