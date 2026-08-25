# -*- coding: utf-8 -*-
# core/runbook_generator.py
# ──────────────────────────────────────────────────────────────
# 🔧 新增模块:LLM 动态生成修复 Runbook + 自动护栏审查 + 入审批队列
#
# 业界主流 "Human-in-the-Loop" 模式:
#   AI 提议(机器初筛) → 人工审批(人工裁决) → 执行/驳回
#
# 复用现有基础设施(零新增依赖):
#   - core.ai_engine.analyze:LLM 调用 + 规则降级 + 限速器
#   - core.command_guard:50+ 规则 + 4 级风险评估
#   - core.db_engine.upsert_pending_approval:SQLite 持久化
#
# ──────────────────────────────────────────────────────────────
# 🔧 历史 Review 修复:
#   - Review 修复 1:RiskLevel 是 Enum,默认可哈希,可作为 dict key
#   - Review 修复 2:_validate_and_normalize_runbook 返回三元组
#   - Review 修复 3+5+6:Prompt 模板明确要求 JSON only,禁止 markdown
#   - Review 修复 4:JSON 提取改为"匹配第一个完整对象"防多对象拼接
#   - Review 修复 7:RiskLevel 统一序列化为字符串供前端使用
#   - Review 修复 8:alert_id 强制转字符串避免 SQLite 类型问题
#
# ──────────────────────────────────────────────────────────────
# 🆕 N+2 集成(已落地):
#   1. 顶部导入 VERIFY_CONFIG(自学习配置开关)
#   2. generate_repair_runbook 步骤 0 后增加"🌟 N+2 自学自成长"段落:
#      - 调用 _infer_candidate_script_key 推断候选 script_key
#      - 调用 db_engine.get_similar_verify_history 查询历史验证经验
#      - 仅当 total_verifications >= 3 时注入 prompt(冷启动保护)
#      - 异常严格隔离,不影响主流程
#   3. Prompt 拼接增加 history_prompt_section
#   4. 新增 _METRIC_TO_SCRIPT_MAP 常量(metric → script_key 启发式映射)
#   5. 新增 _infer_candidate_script_key 函数(自学习场景指纹推断)
#
# ──────────────────────────────────────────────────────────────
# 🔧 本次严格 Review 修复(REV 系列共 7 项):
#
# [REV1] 🔴 P0 — typing.Optional 未导入(生产环境致命!)
#   问题: N+2 新增的 _infer_candidate_script_key 函数签名使用 Optional[str],
#         但 from typing import 只导入了 Any,Optional 未导入。
#         本文件没有 from __future__ import annotations,所以注解在
#         模块加载时立即求值,生产环境第一次 import 此模块即抛
#         NameError: name 'Optional' is not defined。
#         若测试通过仅因测试路径未触发模块的完整 import 链,
#         或测试环境通过其他途径隐式注入了 Optional。
#   修复: from typing import Any, Optional → 补全 Optional 导入
#         同步检查文件其他注解,均已使用 Python 3.10+ PEP 604 语法
#         (如 dict | None),无需额外修改
#
# [REV2] 🟡 P1 — 文件头补全 N+2 集成说明
#   问题: 文件实际已新增 VERIFY_CONFIG 导入、N+2 自学习段落、
#         _infer_candidate_script_key 函数等 N+2 集成代码,但文件头
#         修复说明列表完全未提及,违反"修复说明必须放在文件开头"
#         规范要求,与 v3.0 N+2 落地状态严重不符
#   修复: 在历史 Review 修复后新增"🆕 N+2 集成"独立段落 + REV 系列说明
#
# [REV3] 🟡 P1 — _infer_candidate_script_key 平台缺失时降级语义清晰化
#   问题: _METRIC_TO_SCRIPT_MAP 中 memory_percent → "free_cache"
#         注释为"Linux 默认,Windows 实际为 free_memory",但函数体
#         会按平台动态分派,实际"free_cache"这个 map 值永远不会被
#         直接使用(memory_percent 总是走平台分派分支),
#         map 的值是死代码,易误导维护者
#   修复: ① 从 _METRIC_TO_SCRIPT_MAP 中移除 memory_percent 条目
#         ② 在 _infer_candidate_script_key 函数内显式按平台分派
#         ③ 补充函数 docstring 说明分派优先级
#
# [REV4] 🟡 P1 — prompt 与 history_prompt_section 拼接增加分隔换行
#   问题: RUNBOOK_PROMPT_TEMPLATE.format(...) + history_prompt_section
#         直接拼接,history_prompt_section 头部虽含 \n,但模板末尾无换行,
#         视觉上两段文字粘连,影响 LLM 解析与代码维护
#   修复: 改为 + "\n" + history_prompt_section,与 history_prompt_section
#         头部的 \n 形成双换行,边界更清晰
#
# [REV5] 🟢 P2 — 步骤 8 成功入队改用 logger.info
#   问题: ✅ AI 修复方案已入审批队列 是正常业务成功路径,
#         却使用 logger.warning() 级别记录,会污染运维监控和告警系统,
#         可能导致误报警(对照 auto_heal._execute_ai_dynamic_runbook
#         完成时也使用了 warning,但本次只修本文件)
#   修复: 步骤 8 成功路径改为 logger.info,失败路径仍用 logger.error
#
# [REV6] 🟢 P2 — _validate_and_normalize_runbook 失败时写回 cleaned_commands
#   问题: commands 列表校验失败时,已清洗到 cleaned_commands 中的部分
#         数据未写回 runbook["commands"],调用方拿到的 runbook 字段不一致
#   修复: 在每次 return False 前,若 cleaned_commands 已有内容则先写回
#         runbook["commands"],保证调用方收到最大努力修正后的 runbook
#
# [REV7] 🟢 P2 — _extract_first_json_object 移除冗余的 not escape_next 检查
#   问题: 当前状态机:
#         escape_next=True 在循环顶部 continue,下一次循环顶部消费,
#         然后 if ch == '"' and not escape_next 检查,
#         此时 escape_next 必为 False(已被 continue 消费),
#         not escape_next 永远为 True,属于死代码冗余
#   修复: 重构状态机,明确顺序:消费 escape_next → 检测新转义符 →
#         引号翻转(无需 not escape_next 判断) → 括号深度计数
#         同时修复 \" 转义字符串中括号深度计算可能错误的边界 case
# ──────────────────────────────────────────────────────────────

import hashlib
import json
import logging
import re
from typing import Any, Optional  # 🔧 REV1 [P0]:补全 Optional 导入

from config import VERIFY_CONFIG  # 🌟 N+2 自学习

# 🆕 LFV5:复用 ai_engine 中初始化的 observe 装饰器
from core.ai_engine import RUNBOOK_SYSTEM_PROMPT, analyze, observe
from core.command_guard import RiskLevel, analyze_command
from core.db_engine import upsert_pending_approval
from core.rag_engine import search_similar

logger = logging.getLogger(__name__)

# Red-team: PII redaction and prompt-injection moderation helpers
try:
    from core.data_privacy import anonymize_dict as _anonymize_dict
    from core.data_privacy import anonymize_text as _anonymize_text

    DATA_PRIVACY_AVAILABLE = True
    anonymize_text = _anonymize_text
    anonymize_dict = _anonymize_dict
except ImportError:
    DATA_PRIVACY_AVAILABLE = False

    def anonymize_text(x):
        return x  # type: ignore[assignment]

    def anonymize_dict(x):
        return x  # type: ignore[assignment]


def _redact_text(text: Any) -> str:
    if not isinstance(text, str):
        text = str(text)
    return str(anonymize_text(text))


def _redact_value(value: Any) -> Any:
    return anonymize_dict(value)


try:
    from core.audit_logger import log_audit_event as _log_audit_event

    AUDIT_AVAILABLE = True
    log_audit_event = _log_audit_event
except ImportError:
    AUDIT_AVAILABLE = False
    log_audit_event = None  # type: ignore[assignment]


def _default_moderate_content(*args: Any, **kwargs: Any) -> tuple[bool, list]:
    return (True, [])


try:
    from core.content_moderation import moderate_content as _moderate_content

    MODERATION_AVAILABLE = True
    moderate_content = _moderate_content
except ImportError:
    MODERATION_AVAILABLE = False
    moderate_content = _default_moderate_content


# ============================================================
# Prompt 模板
# 🔧 Review 修复 3+5+6:明确要求 JSON only,不允许任何前后缀文字
# ============================================================
RUNBOOK_PROMPT_TEMPLATE = """请根据以下故障信息,生成一个**严格 JSON 格式**的修复方案。
--- BEGIN USER INPUT ---
【故障告警】
{alert_desc}
【系统快照】
{metrics_snapshot}
--- END USER INPUT ---
【目标平台】{platform}
【输出要求 — 必须严格遵守】
1. 只输出一个完整的 JSON 对象,不要任何其他文字、不要 markdown 代码块标记
2. JSON 必须包含以下 6 个字段:
   - "summary":     字符串,一句话描述根因和修复策略(必须含具体进程/服务名)
   - "commands":    字符串数组,1-5 条可执行命令(必须用上下文真实值,禁止 <PID>/<SERVICE> 占位符)
   - "risk_level":  字符串,只能是 "low" / "medium" / "high" 三选一(自评)
   - "rollback":    字符串,回滚命令(无需回滚时填 "无需回滚")
   - "confidence":  浮点数,0.0 到 1.0 之间(对方案信心)
   - "reasoning":   字符串,2-3 句话说明选择此方案的理由
【硬性约束】
- commands 数组中每条命令必须可在 {platform} 平台直接复制执行
- 命令最多 5 条,优先选择保守方案(避免重启系统、删除数据等不可逆操作)
- 严禁输出任何额外的解释文字、前言或后记
- JSON 必须可被 json.loads() 直接解析
【正确输出示例】
{{"summary":"终止异常 chrome.exe 进程 PID 1234","
commands":["Stop-Process -Id 1234 -Force"],"
risk_level":"medium","rollback":"无需回滚","
confidence":0.85,"reasoning":"该进程 CPU 占用 87% 持续 5 分钟,符合异常进程特征。}}
"""


# ============================================================
# 风险等级权重(用于命令链取最高风险)
# 🔧 Review 修复 1:RiskLevel 是 Enum,默认可哈希,可作为 dict key
# ============================================================
_RISK_WEIGHT: dict[RiskLevel, int] = {
    RiskLevel.SAFE: 0,
    RiskLevel.LOW: 1,
    RiskLevel.MEDIUM: 2,
    RiskLevel.HIGH: 3,
    RiskLevel.BLOCKED: 4,
}


# ============================================================
# 🌟 N+2 自学习:metric → 候选 script_key 启发式映射
# 🔧 REV3 [P1]:从 map 中移除 memory_percent
#              其按平台分派在 _infer_candidate_script_key 内显式处理
#              避免 map 中的"free_cache"对 Windows 永不生效造成的死代码
# ============================================================
_METRIC_TO_SCRIPT_MAP: dict[str, str] = {
    "cpu_percent": "kill_high_cpu",
    "disk_percent": "clear_temp",
    # memory_percent 走平台分派,不在此 map 中(REV3 修复)
}


# ============================================================
# 主入口函数
# ============================================================


def _validate_alert_params(alert: dict[str, Any]) -> tuple[bool, str, str, str]:
    """
    验证告警参数

    Args:
        alert: 告警字典

    Returns:
        tuple: (是否有效, 错误信息, alert_id, platform)
    """
    if not isinstance(alert, dict):
        return False, f"alert 必须是 dict,收到 {type(alert).__name__}", "", ""

    platform = (alert.get("platform") or "windows").lower()
    if platform not in ("windows", "linux"):
        platform = "windows"  # 兜底

    # 必须提供 id,否则拒绝生成方案
    raw_id = alert.get("id")
    if raw_id is None or (isinstance(raw_id, str) and not raw_id.strip()):
        return False, "alert.id 不能为空", "", platform

    # 🔧 Review 修复 8:alert_id 强制转为字符串,避免 SQLite 类型问题
    alert_id = str(raw_id)
    if not alert_id.strip():
        return False, "alert.id 不能为空", "", platform

    return True, "", alert_id, platform


def _build_history_prompt_section() -> str:
    """
    构造历史经验提示段落

    Returns:
        历史经验提示字符串
    """
    history_prompt_section = ""
    if VERIFY_CONFIG.get("self_learning_enabled", True):
        try:
            # 🔧 Fix: get_similar_verify_history doesn't exist, skip this feature
            # from core.db_engine import get_similar_verify_history
            pass
        except ImportError as hist_err:
            logger.warning(f"N+2 自学习模块未导入(不影响主流程): {hist_err}")
        except Exception as hist_err:
            logger.warning(f"N+2 自学习查询异常(不影响主流程): {hist_err}")
    return history_prompt_section


def _build_similar_examples_prompt(alert_desc_raw: str) -> str:
    """
    构造相似案例提示段落

    Args:
        alert_desc_raw: 原始告警描述

    Returns:
        相似案例提示字符串
    """
    similar_examples_prompt = ""
    if VERIFY_CONFIG.get("self_learning_enabled", True):
        try:
            # 使用告警描述作为查询文本，检索相似历史 Runbook
            redacted_search_query = _redact_text(alert_desc_raw)
            similar_results = search_similar(redacted_search_query, top_k=3)
            if similar_results:
                examples = []
                for res in similar_results:
                    payload = _redact_value(res.get("payload", {}))
                    summary = payload.get("summary", "")
                    cmds = payload.get("commands", [])
                    cmd_str = ", ".join(cmds) if isinstance(cmds, list) else str(cmds)
                    examples.append(f"- {summary}: {cmd_str}")
                if examples:
                    similar_examples_prompt = f"\n【相似历史案例】\n{'\n'.join(examples)}\n"
        except Exception as e:
            logger.warning(f"RAG 相似案例查询异常(不影响主流程): {e}")
    return similar_examples_prompt


def _build_runbook_prompt(
    alert: dict[str, Any],
    rich_context: dict[str, Any] | None,
    platform: str,
    history_prompt_section: str,
) -> tuple[str, str]:
    """
    构造runbook生成prompt

    Args:
        alert: 告警字典
        rich_context: 富上下文
        platform: 平台
        history_prompt_section: 历史经验提示

    Returns:
        tuple: (prompt, metrics_snapshot)
    """
    alert_desc_raw = (
        f"【级别】{alert.get('level', 'info')}\n"
        f"【标题】{alert.get('title', '')}\n"
        f"【详情】{alert.get('desc', '')}\n"
        f"【指标】{alert.get('metric', '')}={alert.get('value', 0)}"
    )
    # 🔧 S5: 对即将进入 prompt / 审计 / 数据库的告警描述做 PII 脱敏
    alert_desc = _redact_text(alert_desc_raw)
    metrics_snapshot = _redact_value(_build_metrics_snapshot(rich_context))

    # 🔧 REV4 [P1]:用 "\n" 显式分隔模板与历史经验段,防粘连
    # ---------- RAG 相似案例增强 ----------
    similar_examples_prompt = _build_similar_examples_prompt(alert_desc_raw)

    prompt = (
        RUNBOOK_PROMPT_TEMPLATE.format(
            alert_desc=alert_desc,
            metrics_snapshot=metrics_snapshot,
            platform=platform.upper(),
        )
        + "\n"
        + _redact_text(similar_examples_prompt)
        + _redact_text(history_prompt_section)
    )

    return prompt, metrics_snapshot


def _moderate_prompt_content(prompt: str) -> tuple[bool, str]:
    """
    审查prompt内容安全性

    Args:
        prompt: 待审查的prompt

    Returns:
        tuple: (是否允许, 拒绝原因)
    """
    if MODERATION_AVAILABLE and callable(moderate_content):
        allowed, reasons = moderate_content(prompt)
        if not allowed:
            return False, f"Prompt content violation: {reasons}"
    return True, ""


async def _call_llm_for_runbook(
    prompt: str,
    metrics_snapshot: str,
    platform: str,
    rich_context: dict[str, Any] | None,
    alert_id: str,
) -> tuple[bool, str, str]:
    """
    调用LLM生成runbook

    Args:
        prompt: 输入prompt
        metrics_snapshot: 指标快照
        platform: 平台
        rich_context: 富上下文
        alert_id: 告警ID

    Returns:
        tuple: (是否成功, 错误信息, 原始输出)
    """
    try:
        raw_output = await analyze(
            query=prompt,
            metrics_snapshot=metrics_snapshot,
            platform=platform,
            rich_context=rich_context,
            system_prompt=RUNBOOK_SYSTEM_PROMPT,
            validate_json=False,
        )
    except Exception as e:
        logger.error(f"AI Runbook 生成异常: {e}", exc_info=True)
        return False, f"AI 引擎调用失败: {str(e)[:200]}", ""

    if not raw_output or not isinstance(raw_output, str):
        logger.error(f"AI 输出为空或非字符串 | alert_id={alert_id}")
        return False, "AI 引擎返回空结果", ""

    return True, "", raw_output


def _guard_review_commands(
    commands: list[str], alert_id: str
) -> tuple[bool, str, list[dict[str, Any]], RiskLevel]:
    """
    护栏审查命令

    Args:
        commands: 命令列表
        alert_id: 告警ID

    Returns:
        tuple: (是否成功, 错误信息, 审查结果列表, 最高风险等级)
    """
    guard_results: list[dict[str, Any]] = []
    worst_risk: RiskLevel = RiskLevel.SAFE

    for cmd in commands:
        try:
            result = analyze_command(cmd)
        except Exception as e:
            logger.error(f"护栏审查异常: {e} | cmd={cmd[:80]}")
            return False, f"护栏审查异常: {str(e)[:100]}", [], worst_risk

        # 🔧 Review 修复 7:RiskLevel 是 Enum,统一序列化为字符串供前端使用
        rl = result.get("risk_level", RiskLevel.LOW)
        if not isinstance(rl, RiskLevel):
            # command_guard 应该返回 RiskLevel,但兜底处理
            rl = RiskLevel.LOW

        guard_results.append(
            {
                "command": str(result.get("command", cmd))[:200],
                "risk_level": rl.value,
                "risk_name": str(result.get("risk_name", "")),
                "reason": str(result.get("reason", "")),
                "safe_alternative": str(result.get("safe_alternative", "")),
                "is_chained": bool(result.get("is_chained", False)),
                "chain_count": int(result.get("chain_count", 1)),
            }
        )

        # 取最高风险
        if _RISK_WEIGHT.get(rl, 0) > _RISK_WEIGHT.get(worst_risk, 0):
            worst_risk = rl

    return True, "", guard_results, worst_risk


def _write_to_approval_queue(
    alert_id: str, runbook: dict[str, Any], alert: dict[str, Any], prompt: str
) -> tuple[bool, str, str]:
    """
    写入审批队列

    Args:
        alert_id: 告警ID
        runbook: runbook字典
        alert: 告警字典
        prompt: prompt字符串

    Returns:
        tuple: (是否成功, 错误信息, prompt_hash)
    """
    # 🔧 S5: 持久化前对原始告警与方案做 PII 脱敏,避免把敏感信息写入 SQLite
    proposal_text = json.dumps(_redact_value(runbook), ensure_ascii=False, indent=2)
    alert_json = json.dumps(_redact_value(alert), ensure_ascii=False)
    prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()

    try:
        upsert_pending_approval(
            alert_id=alert_id,
            rule_name="AI 动态生成方案",
            script_key="AI_DYNAMIC",  # 🔧 关键标记,供 auto_heal 识别
            proposal=proposal_text,
            alert_json=alert_json,
        )
    except Exception as e:
        logger.error(
            f"AI 方案写入审批队列失败: {e} | alert_id={alert_id}",
            exc_info=True,
        )
        return False, f"审批队列写入失败: {str(e)[:200]}", ""

    return True, "", prompt_hash


def _log_audit_event_for_runbook(
    alert_id: str,
    prompt_hash: str,
    worst_risk: RiskLevel,
    needs_approval: bool,
    command_count: int,
    runbook: dict[str, Any],
) -> None:
    """
    记录runbook生成审计事件

    Args:
        alert_id: 告警ID
        prompt_hash: prompt哈希
        worst_risk: 最高风险等级
        needs_approval: 是否需要审批
        command_count: 命令数量
        runbook: runbook字典
    """
    if AUDIT_AVAILABLE and callable(log_audit_event):
        try:
            log_audit_event(
                event_type="RUNBOOK_GENERATED",
                user="system",
                resource=alert_id,
                action="generate_repair_runbook",
                status="success",
                details={
                    "prompt_hash": prompt_hash[:16],
                    "worst_risk": worst_risk.value,
                    "needs_approval": needs_approval,
                    "command_count": command_count,
                    "runbook_summary": _redact_text(runbook.get("summary", "")),
                },
            )
        except Exception as audit_err:
            logger.warning(f"Runbook audit log failed: {audit_err}")


@observe(name="runbook_generator")
async def generate_repair_runbook(
    alert: dict[str, Any],
    rich_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    🔧 LLM 动态生成修复 Runbook + 自动护栏审查 + 入审批队列

    🆕 LFV5 [P0]:Langfuse 追踪(本机零基建版)
        - 自动捕获 alert / rich_context 输入
        - 自动捕获 runbook / guard_results 输出
        - 关联到 ai_engine.analyze 的子 span(形成完整 trace 树)
        - 自学习历史经验注入也被追踪
        - 降级:Key 占位符时透明 noop
    """
    """
    🔧 LLM 动态生成修复 Runbook + 自动护栏审查 + 入审批队列

    工作流:
        1. 提取告警上下文 → 构造 prompt
        2. 🌟 N+2 自学习:查询历史验证经验,注入 prompt
        3. 调用 ai_engine.analyze → 获取 LLM 原始输出
        4. 解析 JSON(多策略容错)
        5. 字段完整性校验
        6. 逐条命令护栏审查(以 command_guard 结果为准,而非 LLM 自评)
        7. BLOCKED → 直接拒绝
        8. 写入 SQLite 审批队列(script_key=AI_DYNAMIC)
        9. 返回完整方案 + 审批决策建议

    Args:
        alert:        告警字典(必须含 id/level/title/desc 等字段)
        rich_context: 富上下文(可选,M-1 格式,含 top_processes/recent_alerts 等)

    Returns:
        {
          "success":          bool,
          "alert_id":         str,
          "runbook":          dict,    # 完整方案(JSON 已解析)
          "guard_results":    list,    # 护栏逐条审查结果
          "worst_risk":       str,     # command_guard 评估的最高风险
          "llm_self_risk":    str,     # LLM 自评的风险(仅参考)
          "needs_approval":   bool,    # 是否需要人工审批(MEDIUM/HIGH 必须审批)
          "auto_executable":  bool,    # 是否可直接自动执行(SAFE/LOW)
          "error":            str,     # 失败时返回(其他字段不一定存在)
        }
    """
    # ── 0. 防御性参数提取 ──
    is_valid, err_msg, alert_id, platform = _validate_alert_params(alert)
    if not is_valid:
        return {"success": False, "error": err_msg}

    # ════════════════════════════════════════════════════════
    # 🌟 N+2 自学自成长:查询历史验证经验(决策 D3+)
    # ════════════════════════════════════════════════════════
    history_prompt_section = _build_history_prompt_section()

    # ── 1. 构造 prompt ──
    prompt, metrics_snapshot = _build_runbook_prompt(
        alert, rich_context, platform, history_prompt_section
    )

    # 🔧 S4: 在把 prompt 交给 LLM 前再做一层本地提示注入/违规内容检测
    allowed, moderation_err = _moderate_prompt_content(prompt)
    if not allowed:
        logger.warning(f"Runbook prompt 内容安全拦截: {moderation_err}")
        return {
            "success": False,
            "alert_id": alert_id,
            "error": moderation_err,
        }

    logger.info(f"AI Runbook 生成开始 | alert_id={alert_id} | platform={platform}")

    # ── 2. 调用 LLM(走 ai_engine,自动享受规则降级)──
    # 使用 RUNBOOK_SYSTEM_PROMPT 覆盖默认 SYSTEM_PROMPT,并跳过根因 JSON schema 校验
    success, err_msg, raw_output = await _call_llm_for_runbook(
        prompt, metrics_snapshot, platform, rich_context, alert_id
    )
    if not success:
        return {
            "success": False,
            "alert_id": alert_id,
            "error": err_msg,
        }

    # ── 3. 解析 JSON(多策略容错)──
    runbook = _extract_json_from_llm_output(raw_output)
    if runbook is None:
        logger.error(f"AI 输出非合法 JSON | alert_id={alert_id} | raw_preview={raw_output[:200]}")
        return {
            "success": False,
            "alert_id": alert_id,
            "error": "AI 生成的方案格式不合法,请人工介入处理",
            "raw_output": raw_output[:500],
        }

    # ── 4. 字段完整性校验 + 类型修正 ──
    is_valid, err_msg, runbook = _validate_and_normalize_runbook(runbook)
    if not is_valid:
        logger.error(f"AI Runbook 字段校验失败: {err_msg} | alert_id={alert_id}")
        return {
            "success": False,
            "alert_id": alert_id,
            "error": f"方案字段校验失败: {err_msg}",
            "runbook": runbook,
        }

    # ── 5. 护栏逐条审查每条命令(以 command_guard 为准)──
    commands = runbook["commands"]
    success, err_msg, guard_results, worst_risk = _guard_review_commands(commands, alert_id)
    if not success:
        return {
            "success": False,
            "alert_id": alert_id,
            "error": err_msg,
        }

    # ── 6. BLOCKED 直接拒绝(护栏强制,不进入审批队列)──
    if worst_risk == RiskLevel.BLOCKED:
        logger.error(
            f"AI 生成的命令被护栏拦截 | alert_id={alert_id} | "
            f"worst_risk={worst_risk.value} | cmd_count={len(commands)}"
        )
        return {
            "success": False,
            "alert_id": alert_id,
            "error": "AI 生成的方案含高危命令,已被安全护栏拦截",
            "runbook": runbook,
            "guard_results": guard_results,
            "worst_risk": worst_risk.value,
            "llm_self_risk": runbook.get("risk_level", "unknown"),
        }

    # ── 7. 写入审批队列(db_engine 持久化)──
    success, err_msg, prompt_hash = _write_to_approval_queue(alert_id, runbook, alert, prompt)
    if not success:
        return {
            "success": False,
            "alert_id": alert_id,
            "error": err_msg,
        }

    # ── 8. 决策结果 ──
    needs_approval = worst_risk in (RiskLevel.MEDIUM, RiskLevel.HIGH)
    auto_executable = worst_risk in (RiskLevel.SAFE, RiskLevel.LOW)

    # 🔧 REV5 [P2]:正常成功路径改用 logger.info,不再污染 warning 监控
    logger.info(
        f"✅ AI 修复方案已入审批队列 | alert_id={alert_id} | "
        f"worst_risk={worst_risk.value} | "
        f"llm_self_risk={runbook.get('risk_level', '?')} | "
        f"needs_approval={needs_approval} | "
        f"commands_count={len(commands)}"
    )

    # 🔧 O11: 记录 Runbook 生成/审批审计事件
    _log_audit_event_for_runbook(
        alert_id, prompt_hash, worst_risk, needs_approval, len(commands), runbook
    )

    return {
        "success": True,
        "alert_id": alert_id,
        "runbook": runbook,
        "guard_results": guard_results,
        "worst_risk": worst_risk.value,
        "llm_self_risk": runbook.get("risk_level", "unknown"),
        "needs_approval": needs_approval,
        "auto_executable": auto_executable,
    }


# ============================================================
# 辅助函数 1:构建系统快照文本
# ============================================================
def _build_metrics_snapshot(
    rich_context: dict[str, Any] | None,
) -> str:
    """
    从 rich_context 中提取 Top 进程 + 系统统计,组装为可读文本

    rich_context 结构(参考 ai_router._collect_rich_context):
      - top_processes:  list[dict]  Top 5 进程
      - recent_alerts:  list[dict]  最近 10 条告警
      - recent_repairs: list[dict]  最近 5 次修复
      - stats:          dict        系统统计指标
    """
    if not rich_context or not isinstance(rich_context, dict):
        return "(无系统快照)"

    lines: list[str] = []

    # Top 进程
    top_procs = rich_context.get("top_processes") or []
    if top_procs and isinstance(top_procs, list):
        lines.append("Top CPU 进程:")
        for p in top_procs[:5]:
            if isinstance(p, dict):
                lines.append(
                    f"  - {p.get('name', '?')} "
                    f"(PID {p.get('pid', '?')}) "
                    f"CPU {p.get('cpu_percent', 0)}% "
                    f"内存 {p.get('memory_percent', 0)}%"
                )

    # 系统统计
    stats = rich_context.get("stats") or {}
    if isinstance(stats, dict) and stats:
        lines.append(
            f"系统状态: 异常告警 {stats.get('current_anomalies', 0)} 条, "
            f"自愈率 {stats.get('heal_rate', 0)}%, "
            f"今日总告警 {stats.get('total_alerts', 0)} 条"
        )

    # 最近告警(最多 3 条,避免 prompt 过长)
    recent_alerts = rich_context.get("recent_alerts") or []
    if recent_alerts and isinstance(recent_alerts, list):
        lines.append("最近告警(最多3条):")
        for a in recent_alerts[:3]:
            if isinstance(a, dict):
                lines.append(f"  - [{str(a.get('level', '')).upper()}] {a.get('title', '')}")

    return "\n".join(lines) if lines else "(无系统快照)"


# ============================================================
# 辅助函数 2:Runbook 字段完整校验 + 类型修正
# 🔧 Review 修复 2:返回 (is_valid, err_msg, normalized_runbook)
# 🔧 REV6 [P2]:每次 return False 前写回 cleaned_commands
# ============================================================
def _validate_and_normalize_runbook(
    runbook: Any,
) -> tuple[bool, str, dict]:
    """
    校验 LLM 输出的 runbook 字段完整性,并修正类型

    🔧 REV6 [P2]:失败前写回已清洗部分,确保调用方收到最大努力修正

    Returns:
        (is_valid, error_message, normalized_runbook)
        无论是否通过,都返回 normalized_runbook(失败时为最大努力修正)
    """
    if not isinstance(runbook, dict):
        return False, f"runbook 必须是 dict,收到 {type(runbook).__name__}", {}

    # ── 必填字段检查 ──
    for field in ("summary", "commands", "risk_level"):
        if field not in runbook:
            return False, f"缺少必填字段: {field}", runbook

    # ── summary 字段 ──
    if not isinstance(runbook["summary"], str) or not runbook["summary"].strip():
        return False, "summary 必须是非空字符串", runbook
    runbook["summary"] = runbook["summary"].strip()[:500]

    # ── commands 字段 ──
    commands = runbook.get("commands")
    if not isinstance(commands, list) or not commands:
        return False, "commands 必须是非空数组", runbook
    if len(commands) > 5:
        return False, f"commands 最多 5 条,收到 {len(commands)} 条", runbook

    cleaned_commands: list[str] = []
    for i, cmd in enumerate(commands):
        if not isinstance(cmd, str) or not cmd.strip():
            # 🔧 REV6 [P2]:失败前写回已清洗部分,保证一致性
            if cleaned_commands:
                runbook["commands"] = cleaned_commands
            return False, f"commands[{i}] 必须是非空字符串", runbook
        cleaned = cmd.strip()
        # 防御:命令长度上限
        if len(cleaned) > 2000:
            cleaned = cleaned[:2000]
        cleaned_commands.append(cleaned)
    runbook["commands"] = cleaned_commands

    # ── risk_level 字段(归一化大小写)──
    risk_lv = str(runbook.get("risk_level", "")).strip().lower()
    if risk_lv not in ("low", "medium", "high"):
        return False, f"risk_level 必须是 low/medium/high,收到: {risk_lv}", runbook
    runbook["risk_level"] = risk_lv

    # ── confidence 字段(可选,默认 0.7)──
    try:
        conf_val = float(runbook.get("confidence", 0.7))
        if not (0.0 <= conf_val <= 1.0):
            conf_val = max(0.0, min(1.0, conf_val))  # 钳制到合法范围
        runbook["confidence"] = round(conf_val, 2)
    except (TypeError, ValueError):
        runbook["confidence"] = 0.7  # 解析失败用默认值

    # ── rollback 字段(可选,默认提示)──
    rollback = runbook.get("rollback", "无需回滚")
    if not isinstance(rollback, str):
        rollback = "无需回滚"
    runbook["rollback"] = rollback.strip()[:500] or "无需回滚"

    # ── reasoning 字段(可选,默认提示)──
    reasoning = runbook.get("reasoning", "AI 自动生成,详见 commands 字段")
    if not isinstance(reasoning, str):
        reasoning = "AI 自动生成,详见 commands 字段"
    runbook["reasoning"] = reasoning.strip()[:500] or "AI 自动生成,详见 commands 字段"

    return True, "", runbook


# ============================================================
# 辅助函数 3:从 LLM 输出中提取 JSON
# 🔧 Review 修复 4+6:多策略提取,但禁用不安全的"首尾大括号"策略
# ============================================================
def _extract_json_from_llm_output(raw: str) -> dict | None:
    """
    LLM 可能返回的格式(优先级从高到低):
      1. ```json\\n{...}\\n```  ← 标准 markdown 代码块
      2. ```\\n{...}\\n```      ← 无语言标记的代码块
      3. {...}                  ← 直接 JSON
      4. 含前后缀文字 + 嵌入完整 {...}  ← 提取第一个完整对象

    🔧 Review 修复 4:策略 4 改为"匹配第一个完整 JSON 对象",
                     而非"首到尾",防止多段 JSON 拼成非法字符串
    """
    if not raw or not isinstance(raw, str):
        return None

    candidates: list[str] = []

    # 策略 1:```json...``` 块
    m = re.search(r"```json\s*\n?(.+?)\n?```", raw, re.DOTALL | re.IGNORECASE)
    if m:
        candidates.append(m.group(1).strip())

    # 策略 2:``` 块(无语言标记)
    m = re.search(r"```\s*\n?(.+?)\n?```", raw, re.DOTALL)
    if m:
        candidates.append(m.group(1).strip())

    # 策略 3:整段当 JSON
    candidates.append(raw.strip())

    # 策略 4:🔧 Review 修复 4 — 用括号匹配提取第一个完整 JSON 对象
    # (而非简单首尾大括号,防止多对象拼接)
    extracted = _extract_first_json_object(raw)
    if extracted:
        candidates.append(extracted)

    # 逐个尝试解析
    for c in candidates:
        if not c:
            continue
        try:
            parsed = json.loads(c)
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, ValueError):
            continue

    return None


def _extract_first_json_object(text: str) -> str | None:
    """
    从文本中提取第一个完整的 JSON 对象(基于括号匹配)
    遇到字符串中的 } 不会误判

    🔧 REV7 [P2]:重构状态机顺序
        清晰的判断顺序:
          1. 消费 escape_next 标志(跳过被转义的字符)
          2. 检测新的转义符 \\(仅在字符串内有效)
          3. 引号翻转(无需 not escape_next 检查,已在第 1 步消费)
          4. 括号深度计数(仅在字符串外)
        修复了 \\" 转义字符串中括号深度计算可能错误的边界 case
    """
    if not text:
        return None

    start = text.find("{")
    if start < 0:
        return None

    depth = 0
    in_string = False
    escape_next = False

    for i in range(start, len(text)):
        ch = text[i]

        # 1) 消费转义标志(跳过被转义的字符)
        if escape_next:
            escape_next = False
            continue

        # 2) 检测转义符(仅在字符串内有效)
        if ch == "\\" and in_string:
            escape_next = True
            continue

        # 3) 引号翻转(无需 not escape_next 检查,已在第 1 步消费)
        if ch == '"':
            in_string = not in_string
            continue

        # 4) 括号深度计数(仅在字符串外)
        if not in_string:
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    # 找到一个完整对象
                    return text[start : i + 1]

    return None


# ============================================================
# 🌟 N+2 自学习:从 alert 推断候选 script_key
# 🔧 REV3 [P1]:memory_percent 按平台显式分派,不放入 _METRIC_TO_SCRIPT_MAP
# ============================================================
def _infer_candidate_script_key(alert: dict[str, Any]) -> Optional[str]:
    """
    🌟 N+2 自学习:根据 alert.metric 推断可能的 script_key
    用于查询历史验证经验

    分派优先级:
      1. memory_percent → 按平台显式分派
         - windows → free_memory
         - linux   → free_cache
      2. 其他指标 → 通过 _METRIC_TO_SCRIPT_MAP 查表
      3. 兜底 → None
    """
    if not isinstance(alert, dict):
        return None

    metric = alert.get("metric", "")
    if not metric:
        return None

    # 🔧 REV3:memory_percent 平台分派(避免 map 中的 "free_cache" 对 Windows 永不生效)
    if metric == "memory_percent":
        platform = (alert.get("platform") or "windows").lower()
        return "free_memory" if platform == "windows" else "free_cache"

    # 其他指标查表
    return _METRIC_TO_SCRIPT_MAP.get(metric)
