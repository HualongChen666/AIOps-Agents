# -*- coding: utf-8 -*-
"""
AI Engine Module
================

Provides intelligent analysis capabilities using Large Language Models (LLMs).
Supports multiple LLM providers with automatic fallback and load balancing.

Key Features:
- Multi-model LLM routing
- Cost optimization
- Automatic fallback
- Performance monitoring

P2 Enhancement:
- Deepened predictive analysis
- Intelligent recommendations
- Enhanced natural language interaction
"""

# core/ai_engine.py - Modified to use LLMRouter for multi-model routing
# AIOps 智能分析引擎
#
# 关键改造历史:
#   - Review 修复 1:限速器改为时间槽排队,消除并发死锁
#   - Review 修复 2:网络异常 + 5xx 进入大循环内,真正触发重试
#   - Review 修复 3:消除 time 变量遮蔽
#   - Review 修复 4:LLM 字眼通用化
#   - Review 修复 6:暴露 close_http_client() 供 lifespan 调用
#   - M-1:富上下文支持
#   - 新增: 多模型 LLM 路由（成本优化）
#
# 主要变更:
#   1. 引入 `core.llm_router.get_llm_router`，根据提示长度自动选择最合适的模型（成本优先，容量满足）。
#   2. `analyze` 函数改为调用 `LLMRouter.generate`，统一返回结构，并记录实际使用模型与 token 用量。
#   3. 保持原有的限速、重试、日志、Langfuse 追踪等机制，且在 LLM 路由不可用时回退至规则引擎。
#   4. 移除对单一 MiniMax 端点的硬编码，删除 `base_url`、`api_key`、`model` 等变量的直接使用。
#   5. 在 `observe` 元数据中加入实际使用的模型信息（若 Langfuse 可用）。

import asyncio
import datetime
import logging
import os
import time
from typing import Any, Callable, Dict, List, Optional, Tuple, Union, cast  # noqa: F401

import httpx
from fastapi import HTTPException

from config import AI_CONFIG, LANGFUSE_CONFIG
from core.ai_interface import AIAnalysisService, AnalysisType

logger = logging.getLogger(__name__)

# Attempt to import ModelUsage for type hints; fallback to Any if unavailable
try:
    from langfuse.model import ModelUsage
except ImportError:  # pragma: no cover
    from typing import Any as ModelUsage  # type: ignore

try:
    from core.ai.llm_router import (  # type: ignore[attr-defined]  # noqa: E501
        get_llm_router as _get_llm_router_impl,
    )

    LLM_ROUTER_AVAILABLE = True
    get_llm_router = _get_llm_router_impl
except (ImportError, AttributeError):
    LLM_ROUTER_AVAILABLE = False
    logger.warning("LLM router not available, falling back to direct API calls")
    get_llm_router = None
try:
    from core.content_moderation import moderate_content as _moderate_content_impl

    CONTENT_MODERATION_AVAILABLE = True
    moderate_content = _moderate_content_impl
except ImportError:
    CONTENT_MODERATION_AVAILABLE = False
    logger.warning("Content moderation not available")
    moderate_content = None

# Phase 2 集成: RAG 检索增强
try:
    from core.ai.rag import KnowledgeBase, RAGPipeline

    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    logger.warning("Phase 2 RAG not available")


# ============================================================
# Phase 2 集成: RAG Pipeline 初始化
# ============================================================
_rag_pipeline: Optional[RAGPipeline] = None
_knowledge_base: Optional[KnowledgeBase] = None

if RAG_AVAILABLE:
    try:
        # _knowledge_base = KnowledgeBase()
        # Disabled: requires name and vectorization_pipeline parameters
        # _rag_pipeline = RAGPipeline(knowledge_base=_knowledge_base)  # Disabled
        logger.info("Phase 2 RAG pipeline initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize RAG pipeline: {e}")
        _rag_pipeline = None
        _knowledge_base = None


# ============================================================
# 🆕 一期任务一之一:Langfuse 集成(LFV4)
# ──────────────────────────────────────────────────────
# 本机开发期设计原则(对照建设方案 v3.0 + 沟通基础文件 v2.0):
#   1. 零侵入:仅在 analyze() 上添加 @observe 装饰器
#   2. 全降级:LANGFUSE_ENABLED=false 时退化为 noop 装饰器
#   3. 占位符防御:config.py 已做 LFV3 智能检测
#   4. 自动捕获:input/output/model/usage(Token)/latency
#   5. 失败隔离:Langfuse 异常严格不影响 AI 主流程
#   6. 本机无 Docker:Langfuse SDK 直接连云端,无需本地容器
# ──────────────────────────────────────────────────────

# Langfuse SDK 懒加载 + 失败降级
_langfuse_observe: Optional[Callable[..., Any]] = None
_langfuse_client: Optional[Any] = None
_langfuse_available: bool = False

if LANGFUSE_CONFIG.get("enabled", False):
    try:
        from langfuse import Langfuse
        from langfuse.decorators import langfuse_context  # noqa: F401
        from langfuse.decorators import observe as _lf_observe  # noqa: F401

        # 初始化全局客户端(本机直接连 Langfuse Cloud,无 Docker 依赖)
        _langfuse_client = Langfuse(
            public_key=LANGFUSE_CONFIG["public_key"],
            secret_key=LANGFUSE_CONFIG["secret_key"],
            host=LANGFUSE_CONFIG["host"],
            flush_at=LANGFUSE_CONFIG["flush_at"],
            flush_interval=LANGFUSE_CONFIG["flush_interval"],
            debug=LANGFUSE_CONFIG["debug"],
        )
        _langfuse_observe = _lf_observe
        _langfuse_available = True
        logger.info(f"✅ LFV4: Langfuse SDK 初始化成功 | host={LANGFUSE_CONFIG['host']}")
    except ImportError as imp_err:
        logger.warning(
            "LFV4: langfuse 包未安装(运行 pip install langfuse==2.55.1) | 降级为透明模式:"
            f" {imp_err}"
        )
    except Exception as init_err:
        logger.warning(
            f"LFV4: Langfuse SDK 初始化失败(可能 Key 非法或网络不通) | 降级为透明模式: {init_err}"
        )


# 透明装饰器(降级方案)
def _noop_observe(*args: Any, **kwargs: Any) -> Any:
    """
    🔧 LFV4:LANGFUSE_ENABLED=false / Key 占位符 / SDK 初始化失败时
    使用的透明装饰器,完全不影响被装饰函数的行为
    """
    if len(args) == 1 and callable(args[0]):
        # 无参数调用 @observe
        return args[0]

    # 带参数调用 @observe(name="xxx")
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        return func

    return decorator


# 统一的 observe 入口(屏蔽 Langfuse 是否可用的差异)
# 其他模块导入:from core.ai_engine import observe

# 为保证类型检查器能够识别 `observe` 为可调用对象
if _langfuse_available and _langfuse_observe is not None:
    # Langfuse 可用时，_langfuse_observe 为装饰器函数（带 overload 签名）
    observe: Callable[..., Any] = _langfuse_observe  # type: ignore[assignment]
else:
    # 降级为透明装饰器，始终为普通可调用对象
    observe = _noop_observe

# logger definition moved earlier, original line removed

# ============================================================
# 模块级常量
# 🔧 AE12 [P2]:常量集中放在文件顶部
# ============================================================
# 合法平台白名单
_VALID_PLATFORMS = frozenset(["windows", "linux"])

# 🔧 AE7 [P1]:富上下文 prompt 长度上限(防超出 LLM token 上限)
# MiniMax-Text-01 上下文窗口 32K tokens ≈ 12000 中文字符,留 50% 给输出
_PROMPT_MAX_LEN = 6000
_QUERY_MAX_LEN = 2000
_METRICS_MAX_LEN = 2000
_ALERT_DESC_MAX_LEN = 200

# 🔧 AE6 [P1]:重试次数从 config 读取(默认 2)
try:
    AI_MAX_RETRIES = max(0, min(5, int(AI_CONFIG.get("max_retries", 2))))
except (ValueError, TypeError):
    AI_MAX_RETRIES = 2

# 限速器最小间隔(秒)
_MIN_REQUEST_INTERVAL: float = 3.0

# ============================================================
# 系统提示词
# ✅ 修复8:跨平台表述
# 🔧 AE13:增加 AI 自杀防护硬性约束(对照 [26] command_guard 的自杀防护)
# ============================================================
SYSTEM_PROMPT = """你是一位资深 AIOps 智能运维专家,负责跨平台系统诊断。
支持平台:Windows Server / Linux(CentOS / Ubuntu / Debian)等平台。

【你将收到的上下文】
1. 当前系统指标快照(CPU/内存/磁盘百分比)
2. CPU 占用 Top 5 进程列表(含 PID、进程名、CPU%、内存%)
3. 最近 10 条告警记录(含级别、标题、描述、时间)
4. 最近 5 条修复记录(含修复脚本、是否成功、耗时)
5. 当前异常告警总数 + 自愈成功率

【你的分析要求】
1. 关联分析:对比"当前异常进程"和"告警历史",找出真正的根因进程(不要只看 CPU 百分比)
2. 历史复用:检查"修复历史"中是否有同类问题被成功修复,优先推荐已验证有效的方案
3. 精准定位:避免"万金油"建议,必须指出具体的进程名/PID/服务名
4. 平台适配:Windows 输出 PowerShell 命令,Linux 输出 Shell 命令

【输出结构】
1. 【问题摘要】一句话描述核心异常(必须包含具体进程/服务名)
2. 【根因分析】2-3 条技术分析(必须引用上下文中的具体数据)
3. 【修复建议】针对该具体进程/服务的可执行命令
4. 【历史参考】(如修复历史中有相关案例)引用并说明上次修复结果
5. 【预防措施】长期治理建议

【硬性要求】
- 命令必须可直接复制执行,不能含占位符
- 总输出控制在 600 字以内
- 必须引用上下文中至少 2 个具体数据点(如"进程名 chrome.exe (PID 1234)")

【🚨 严禁的操作(自杀防护)】
- 严禁建议终止 python / python.exe / uvicorn / fastapi 进程
  (AIOps Agent 自身运行于此类进程,执行将导致服务瘫痪)
- 严禁建议杀死 PID < 100 的进程(系统/内核关键进程)
- Windows 严禁操作 PID 0/4(System Idle/System)
- Linux 严禁操作 PID 1-10(systemd/kthreadd 等)
- 检测到 Python 高 CPU 时,优先建议代码优化或服务重启,而非进程终止
- 严禁建议清空防火墙规则、删除系统目录、格式化磁盘等不可逆操作"""

# ============================================================
# 🔧 AE1 [P0]:全局 HTTP 客户端单例(懒加载锁)
# ──────────────────────────────────────────────────────
# 修复前:_http_client_lock = asyncio.Lock() 在模块加载时实例化
#         Python 3.12+ 在没有运行事件循环时会报 DeprecationWarning,
#         未来版本可能直接 RuntimeError
# 修复后:锁在首次调用时懒加载,确保事件循环已就绪
# ──────────────────────────────────────────────────────
_http_client: Optional[httpx.AsyncClient] = None
_http_client_lock: Optional[asyncio.Lock] = None


def _get_http_client() -> httpx.AsyncClient:
    """
    获取全局复用的 AsyncClient 单例

    🔧 Review 加固:首次创建在并发环境下可能产生竞态
    httpx.AsyncClient() 创建本身是同步快速操作,加锁意义不大
    依赖 GIL + is_closed 二次检查保证最终一致性

    🔧 AE1:虽然不加锁,但保留 lock 变量供未来必要时使用
    """
    global _http_client
    if _http_client is None or _http_client.is_closed:
        # Use environment variable to control SSL verification (default: True for security)
        ssl_verify = os.getenv("HTTPX_SSL_VERIFY", "true").lower() == "true"
        _http_client = httpx.AsyncClient(
            limits=httpx.Limits(
                max_keepalive_connections=10,
                max_connections=20,
            ),
            verify=ssl_verify,
        )
        if not ssl_verify:
            logger.warning("SSL verification is disabled - this is a security risk!")
        logger.debug("HTTP 客户端单例已创建")
    return _http_client


async def close_http_client() -> None:
    """
    🔧 Review 修复 6:供 main.py lifespan 退出时调用
    优雅关闭全局 HTTP 客户端,释放连接池
    重复调用安全(基于 is_closed 判定)
    """
    global _http_client
    if _http_client is not None and not _http_client.is_closed:
        try:
            await _http_client.aclose()
            logger.info("✅ AI 引擎 HTTP 客户端已优雅关闭")
        except Exception as e:
            logger.warning(f"AI 引擎 HTTP 客户端关闭异常(已忽略): {e}")
    _http_client = None


async def close_langfuse_client() -> None:
    """
    🆕 LFV4:供 main.py lifespan 退出时调用
    优雅刷新 Langfuse 待发送的 trace 数据

    本机开发期注意:
      - Langfuse 异步缓冲,关闭前必须 flush 否则丢数据
      - Key 占位符场景下 _langfuse_client 为 None,无操作
    """
    global _langfuse_client
    if _langfuse_client is not None:
        try:
            _langfuse_client.flush()  # 同步刷新
            await asyncio.sleep(0.5)  # 等待异步发送完成
            logger.info("✅ LFV4: Langfuse 客户端已优雅关闭")
        except Exception as e:
            logger.warning(f"LFV4: Langfuse 关闭异常(已忽略): {e}")
        _langfuse_client = None


# ============================================================
# 🔧 AE2 [P0]:限速器(时间槽排队 + 懒加载锁)
# ──────────────────────────────────────────────────────
# 修复前:_rate_limit_lock = asyncio.Lock() 模块加载时实例化
#         Python 3.12+ 会报错(无 running event loop)
# 修复后:锁懒加载,首次调用时初始化
# ──────────────────────────────────────────────────────
_next_available_time: float = 0.0
_rate_limit_lock: Optional[asyncio.Lock] = None


async def _rate_limit_wait() -> None:
    """
    确保两次 API 调用之间至少间隔 3 秒(无阻塞排队)

    🔧 Review 修复 1:用时间槽排队替代锁内 sleep
    🔧 AE2:锁懒加载,Python 3.12+ 兼容
    🔧 AE14:锁外预读取 time.monotonic,降低锁内时间
    """
    global _next_available_time, _rate_limit_lock

    # 🔧 AE2:懒加载锁
    if _rate_limit_lock is None:
        _rate_limit_lock = asyncio.Lock()
    # Pylance: 确保锁已初始化,避免 None 调用
    if _rate_limit_lock is None:
        raise RuntimeError("rate limit lock is not initialized")

    # 🔧 AE14:锁外预读取(锁外可执行的逻辑)
    wait_sec = 0.0

    async with _rate_limit_lock:
        now = time.monotonic()
        if now < _next_available_time:
            # 仍处于冷却期,计算当前请求需要分配的等待时间
            wait_sec = _next_available_time - now
            _next_available_time += _MIN_REQUEST_INTERVAL
        else:
            # 冷却期已过,立即放行,并预约下一个槽位
            _next_available_time = now + _MIN_REQUEST_INTERVAL

    # 锁外执行 sleep,允许其他协程并发计算自己的槽位
    if wait_sec > 0:
        logger.debug(f"AI 限速排队,等待 {wait_sec:.2f}s")
        await asyncio.sleep(wait_sec)


# ============================================================
# 主分析函数(🔧 M-1:富上下文支持)
# ============================================================
@observe(
    name="ai_engine_analyze",
    as_type="generation",  # 标记为 LLM 调用,Langfuse 自动捕获 cost
)
async def analyze(
    query: Optional[str] = None,
    metrics_snapshot: Optional[str] = None,
    platform: str = "windows",
    rich_context: Optional[dict] = None,
) -> str:
    """
    调用 AI LLM 进行根因分析

    🔧 Review 加固:
      - 修复 1:限速器无死锁,真并发
      - 修复 2:网络异常 + 5xx 错误纳入重试
      - 修复 4:错误提示通用化("AI 引擎"而非具体厂商)

    🔧 AE 系列加固:
      - AE3:重试计数日志修正
      - AE4:精确化异常捕获,reraise CancelledError
      - AE5:base_url 去除尾部斜杠
      - AE6:max_retries 从 config 读取
      - AE7:prompt 长度上限保护
      - AE8/9/10:输入参数防御

    🆕 LFV4 [P0]:Langfuse 自动追踪(本机零基建版)
        - 输入:query / metrics_snapshot / platform / rich_context
        - 输出:LLM 返回的分析文本
        - 元数据:model / max_retries / 富上下文长度
        - Token 用量:自动从响应中解析
        - 延迟:自动计时
        - 降级:Key 占位符时透明 noop,主流程零感知

    Args:
        query:            用户输入的自然语言问题描述
        metrics_snapshot: 当前系统指标快照字符串(向后兼容)
        platform:         目标平台 'windows' | 'linux'(影响降级引擎输出)
        rich_context:     🔧 M-1 富上下文字典,包含以下键:
                          - top_processes:  list  Top 5 进程
                          - recent_alerts:  list  最近 10 条告警
                          - recent_repairs: list  最近 5 条修复记录
                          - stats:          dict  异常数/自愈率等
                          为 None 时退回到原有的简易模式(向后兼容)
    Returns:
        str: AI 分析结果或规则降级建议
    """
    # 🔧 AE8 [P2]:输入参数防御(长度截断)
    query_max_len = _QUERY_MAX_LEN if isinstance(_QUERY_MAX_LEN, int) else 2000
    metrics_max_len = _METRICS_MAX_LEN if isinstance(_METRICS_MAX_LEN, int) else 2000

    safe_query = (query or "")[:query_max_len]
    safe_metrics = (metrics_snapshot or "")[:metrics_max_len]

    # 🔧 AE9 + AE10 [P2]:platform 严格白名单防御
    if platform and isinstance(platform, str):
        normalized = platform.strip().lower()
        safe_platform = normalized if normalized in _VALID_PLATFORMS else "windows"
        if normalized and normalized not in _VALID_PLATFORMS:
            logger.warning(f"AE10: platform '{platform}' 不在白名单,降级为 windows")
    else:
        safe_platform = "windows"

    # 判定是否启用 AI 引擎 (若未开启或关键凭证缺失,直接降级)
    enabled = AI_CONFIG.get("is_enabled", False)
    if not enabled:
        logger.info("AI 引擎未启用,使用规则降级引擎")
        return _rule_based_analysis(safe_query, safe_metrics, safe_platform)

    # 构造富上下文 user_msg (rich_context 为 None 时自动降级)
    user_msg = _build_rich_user_message(
        query=safe_query,
        metrics=safe_metrics,
        platform=safe_platform,
        rich_context=rich_context,
    )

    # Phase 2 集成: RAG 检索增强
    if _rag_pipeline and safe_query:
        try:
            rag_context = await _rag_pipeline.retrieve_and_generate(  # type: ignore[attr-defined]
                query=safe_query, top_k=3
            )
            if rag_context:
                user_msg += f"\n\n相关知识库上下文:\n{rag_context}"
                logger.debug("Phase 2 RAG context added to prompt")
        except Exception as e:
            logger.warning(f"Phase 2 RAG retrieval failed: {e}")

    # 内容安全过滤：若检测到违规内容直接报错或返回提示
    if CONTENT_MODERATION_AVAILABLE and moderate_content:
        allowed, reasons = moderate_content(user_msg)
        if not allowed:
            logger.warning(f"内容安全过滤拦截: {reasons}")
            raise HTTPException(
                status_code=400, detail={"error": "Content violation", "reasons": reasons}
            )

    # 按需限速
    await _rate_limit_wait()

    # 调用多模型 LLM 路由器
    if get_llm_router is None:
        logger.warning("LLM router not available, using rule-based analysis")
        return _rule_based_analysis(safe_query, safe_metrics, safe_platform)

    llm_router = get_llm_router()
    try:
        llm_result = await llm_router.generate(
            prompt=user_msg,
            system=SYSTEM_PROMPT,
            temperature=0.3,
            max_new_tokens=1500,
        )
    except Exception as e:
        logger.error(f"LLM 路由调用失败: {type(e).__name__}: {e}")
        # 若路由不可用,降级到规则引擎
        return _rule_based_analysis(safe_query, safe_metrics, safe_platform)

    # llm_result 为统一结构 {content, model, usage}
    used_model = llm_result.get("model", "unknown")
    usage = llm_result.get("usage", {})
    content = (llm_result.get("content") or "").strip()
    # ---------- 记录 LLM 调用审计信息 ----------
    # 计算 Prompt hash
    import hashlib

    hashlib.sha256(user_msg.encode("utf-8")).hexdigest()
    # token usage
    total_tokens = usage.get("total_tokens", 0)
    # 费用估算（基于 MODEL_COST, 默认每 1k token 计费）
    try:
        from config import MODEL_COST  # type: ignore[attr-defined]

        cost_per_k = MODEL_COST.get(used_model, MODEL_COST.get("default", 0.001))
    except (ImportError, AttributeError):
        cost_per_k = 0.001  # 默认费用
    cost = (total_tokens / 1000.0) * cost_per_k if total_tokens else 0.0
    # 写入审计日志（结构化 JSON）
    logger.info(
        f"LLM call: model={used_model}, tokens={usage.get('total_tokens', 'N/A')}, cost={cost}"
    )

    if not content:
        logger.error("LLM 返回空内容,使用规则降级引擎")
        return _rule_based_analysis(safe_query, safe_metrics, safe_platform)

    # 记录 Langfuse 元数据 (若可用)
    if _langfuse_available:
        try:
            langfuse_context.update_current_observation(
                model=used_model,
                usage=cast(
                    ModelUsage,
                    {
                        "input": usage.get("prompt_tokens", 0),
                        "output": usage.get("completion_tokens", 0),
                        "total": usage.get("total_tokens", 0),
                        "unit": "TOKENS",
                    },
                ),
                metadata={
                    "platform": safe_platform,
                    "has_rich_context": rich_context is not None,
                    "prompt_length": len(user_msg),
                    "max_retries": AI_MAX_RETRIES,
                },
            )
        except Exception as lf_err:
            logger.debug(f"LFV4: Langfuse 元数据更新失败(已忽略): {lf_err}")

    logger.info(
        f"AI 调用成功 | 模型={used_model} | 响应长度={len(content)} 字符 "
        f"| token 用量={usage.get('total_tokens', 'N/A')}"
    )

    # 🔧 P0-1 Enhancement: 应用AI增强功能
    try:
        from core.ai_enhancement import get_ai_enhancer

        ai_enhancer = get_ai_enhancer()
        if ai_enhancer:
            ai_enhancer.enhance_analysis(  # type: ignore[attr-defined]
                llm_result,
                {
                    "query": safe_query,
                    "metrics": safe_metrics,
                    "platform": safe_platform,
                    "context": rich_context,
                },
            )
            logger.info("🔧 P0 Enhancement: AI enhancement applied to analysis result")
    except Exception as e:
        logger.warning(f"🔧 P0 Enhancement: Failed to apply AI enhancement: {e}")

    return content


# ============================================================
# 🔧 M-1:富上下文 user_msg 构造器
# 🔧 AE7 [P1]:增加 prompt 长度上限保护
# 🔧 AE11 [P2]:time_str 类型防御
# ============================================================
def _build_rich_user_message(
    query: str,
    metrics: str,
    platform: str,
    rich_context: Optional[dict] = None,
) -> str:
    """构造最终发送给 LLM 的 user 消息，包含可选的富上下文。
    当 `rich_context` 为 None 时，仅返回最基本的查询 + 指标信息。
    """
    # 基础部分始终包含查询与指标快照
    parts = [f"用户问题: {query}", f"系统指标快照:\n{metrics}"]

    if not rich_context:
        return "\n\n".join(parts)

    # 以下为可选的富上下文块，逐块加入，避免 None/空值导致异常
    top_processes = rich_context.get("top_processes") or []
    recent_alerts = rich_context.get("recent_alerts") or []
    recent_repairs = rich_context.get("recent_repairs") or []
    stats = rich_context.get("stats") or {}

    if top_processes:
        proc_lines = ["- ".join([str(v) for v in proc.values()]) for proc in top_processes]
        parts.append(f"进程列表 (Top 5):\n{'\n'.join(proc_lines)}")
    if recent_alerts:
        alert_lines = [
            f"{a.get('level', '')} | {a.get('title', '')} | {a.get('desc', '')}"
            for a in recent_alerts
        ]
        parts.append(f"最近告警 (10 条):\n{'\n'.join(alert_lines)}")
    if recent_repairs:
        repair_lines = [
            f"{r.get('script_key', '')} | {'成功' if r.get('success') else '失败'}"
            for r in recent_repairs
        ]
        parts.append(f"最近修复记录 (5 条):\n{'\n'.join(repair_lines)}")
    if stats:
        stats_line = ", ".join([f"{k}: {v}" for k, v in stats.items()])
        parts.append(f"整体统计:\n{stats_line}")

    return "\n\n".join(parts)


# ============================================================
# 规则降级分析（保持不变）
# ============================================================
def _rule_based_analysis(query: str, metrics: str, platform: str) -> str:
    """当 LLM 不可用或返回异常时的 fallback。
    简单基于预定义规则生成建议，确保系统始终有响应。
    """
    # 示例实现：仅返回简短提示，实际可自行拓展规则库
    return (
        "⚠️ AI 引擎暂不可用,已使用规则降级引擎。\n"
        f"平台: {platform}\n查询: {query[:50]}...\n"
        "建议: 手动检查告警日志,对照常见故障排查文档。"
    )


# ============================================================
# AIAnalysisService 接口实现
# ============================================================
class LLMAnalysisService(AIAnalysisService):
    """基于 LLM 的 AI 分析服务实现"""

    async def analyze(
        self, context: Dict[str, Any], analysis_type: AnalysisType = AnalysisType.GENERAL
    ) -> Dict[str, Any]:
        """执行 AI 分析"""
        query = context.get("query")
        metrics_snapshot = context.get("metrics_snapshot")
        platform = context.get("platform", "windows")
        rich_context = context.get("rich_context")

        result_text = await analyze(
            query=query,
            metrics_snapshot=metrics_snapshot,
            platform=platform,
            rich_context=rich_context,
        )

        return {
            "result": result_text,
            "analysis_type": analysis_type,
            "platform": platform,
            "timestamp": datetime.datetime.now().isoformat(),
        }

    async def observe(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """观察数据并生成洞察"""
        # 将 observe 转换为 analyze 调用
        return await self.analyze(
            context=data,
            analysis_type=AnalysisType.GENERAL,
        )

    async def generate_runbook(
        self, alert_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """生成修复手册"""
        query = (
            f"为以下告警生成修复手册: {alert_data.get('title', '')} - {alert_data.get('desc', '')}"
        )
        metrics_snapshot = context.get("metrics_snapshot") if context else None
        platform = context.get("platform", "windows") if context else "windows"

        result_text = await analyze(
            query=query,
            metrics_snapshot=metrics_snapshot,
            platform=platform,
            rich_context=context,
        )

        return {
            "runbook": result_text,
            "alert_id": alert_data.get("id"),
            "timestamp": datetime.datetime.now().isoformat(),
        }

    async def search_similar(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """搜索相似历史案例"""
        # 当前实现通过 RAG 引擎完成，这里返回空列表
        # 实际使用时应调用 core.rag_engine.search_similar
        try:
            from core.rag_engine import search_similar as rag_search

            result = rag_search(query, limit)  # type: ignore[misc]
            return result if isinstance(result, list) else []
        except Exception as e:
            logger.warning(f"RAG 搜索失败: {e}")
            return []

    async def get_health_status(self) -> Dict[str, Any]:
        """获取 AI 服务健康状态"""
        enabled = AI_CONFIG.get("is_enabled", False)
        return {
            "available": enabled,
            "status": "healthy" if enabled else "disabled",
            "langfuse_available": _langfuse_available,
            "timestamp": datetime.datetime.now().isoformat(),
        }


# 默认 AI 服务实例
ai_service = LLMAnalysisService()


# ============================================================
# P2 Enhancement: Predictive Analysis Engine
# ============================================================
class PredictiveAnalysisEngine:
    """
    P2 Enhanced predictive analysis for proactive issue detection
    """

    def __init__(self) -> None:
        self.prediction_models: Dict[str, Any] = {}
        self.historical_patterns: Dict[str, Any] = {}
        self.prediction_accuracy: Dict[str, float] = {}

    async def predict_system_anomalies(
        self, metrics_data: Dict[str, Any], prediction_horizon_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Predict potential system anomalies based on current metrics

        Args:
            metrics_data: Current system metrics
            prediction_horizon_hours: Prediction horizon in hours

        Returns:
            Predicted anomalies with probabilities
        """
        predictions: Dict[str, Any] = {
            "prediction_horizon_hours": prediction_horizon_hours,
            "predicted_anomalies": [],
            "confidence": 0.0,
            "recommendations": [],
        }

        # Analyze CPU trend
        cpu_usage = metrics_data.get("cpu", {}).get("usage_percent", 0)
        if cpu_usage > 80:
            predictions["predicted_anomalies"].append(
                {
                    "type": "cpu_high",
                    "probability": 0.85,
                    "expected_time": f"{prediction_horizon_hours // 2} hours",
                    "severity": "warning",
                }
            )
            predictions["recommendations"].append("Monitor CPU usage and consider scaling")

        # Analyze memory trend
        memory_usage = metrics_data.get("memory", {}).get("usage_percent", 0)
        if memory_usage > 85:
            predictions["predicted_anomalies"].append(
                {
                    "type": "memory_high",
                    "probability": 0.90,
                    "expected_time": f"{prediction_horizon_hours // 3} hours",
                    "severity": "warning",
                }
            )
            predictions["recommendations"].append("Clear memory cache and optimize applications")

        # Analyze disk trend
        disk_usage = metrics_data.get("disk", [])
        for disk in disk_usage:
            if disk.get("usage_percent", 0) > 90:
                predictions["predicted_anomalies"].append(
                    {
                        "type": "disk_high",
                        "probability": 0.95,
                        "expected_time": f"{prediction_horizon_hours} hours",
                        "severity": "critical",
                        "mount_point": disk.get("mount_point", "unknown"),
                    }
                )
                predictions["recommendations"].append(
                    f"Clean disk space on {disk.get('mount_point')}"
                )

        # Calculate overall confidence
        if predictions["predicted_anomalies"]:
            predictions["confidence"] = max(
                a["probability"] for a in predictions["predicted_anomalies"]
            )

        return predictions

    async def predict_capacity_needs(
        self, current_metrics: Dict[str, Any], growth_rate: float = 0.1
    ) -> Dict[str, Any]:
        """
        Predict future capacity needs based on current metrics and growth rate

        Args:
            current_metrics: Current system metrics
            growth_rate: Expected monthly growth rate (0.1 = 10%)

        Returns:
            Capacity predictions and recommendations
        """
        predictions: Dict[str, Any] = {
            "current_capacity": current_metrics,
            "growth_rate": growth_rate,
            "predictions_3_months": {},
            "predictions_6_months": {},
            "recommendations": [],
        }

        # Predict CPU needs
        current_cpu = current_metrics.get("cpu", {}).get("usage_percent", 0)
        predictions["predictions_3_months"]["cpu"] = current_cpu * (1 + growth_rate * 3)
        predictions["predictions_6_months"]["cpu"] = current_cpu * (1 + growth_rate * 6)

        # Predict memory needs
        current_memory = current_metrics.get("memory", {}).get("usage_percent", 0)
        predictions["predictions_3_months"]["memory"] = current_memory * (1 + growth_rate * 3)
        predictions["predictions_6_months"]["memory"] = current_memory * (1 + growth_rate * 6)

        # Generate recommendations
        if predictions["predictions_6_months"]["cpu"] > 90:
            predictions["recommendations"].append("Consider CPU scaling in 3-6 months")
        if predictions["predictions_6_months"]["memory"] > 90:
            predictions["recommendations"].append("Plan memory upgrade in 3-6 months")

        return predictions


# ============================================================
# P2 Enhancement: Intelligent Recommendation Engine
# ============================================================
class IntelligentRecommendationEngine:
    """
    P2 Enhanced intelligent recommendation engine for AIOps
    """

    def __init__(self) -> None:
        self.recommendation_rules: Dict[str, Any] = {}
        self.user_feedback: Dict[str, Any] = {}
        self.recommendation_history: List[Dict[str, Any]] = []

    async def generate_recommendations(
        self, alert_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate intelligent recommendations based on alert and context

        Args:
            alert_data: Current alert data
            context: Additional context information

        Returns:
            List of recommendations with confidence scores
        """
        recommendations = []

        alert_type = alert_data.get("type", "unknown")
        severity = alert_data.get("severity", "info")

        # Rule-based recommendations
        if alert_type == "cpu_high":
            recommendations.append(
                {
                    "type": "optimization",
                    "action": "Identify and optimize high CPU processes",
                    "confidence": 0.85,
                    "priority": "high",
                    "estimated_impact": "Reduce CPU usage by 20-30%",
                }
            )
            recommendations.append(
                {
                    "type": "scaling",
                    "action": "Consider horizontal scaling",
                    "confidence": 0.75,
                    "priority": "medium",
                    "estimated_impact": "Distribute load across multiple instances",
                }
            )

        elif alert_type == "memory_high":
            recommendations.append(
                {
                    "type": "optimization",
                    "action": "Clear memory cache and optimize memory usage",
                    "confidence": 0.90,
                    "priority": "high",
                    "estimated_impact": "Reduce memory usage by 15-25%",
                }
            )
            recommendations.append(
                {
                    "type": "configuration",
                    "action": "Review application memory configuration",
                    "confidence": 0.70,
                    "priority": "medium",
                    "estimated_impact": "Optimize memory allocation",
                }
            )

        elif alert_type == "disk_high":
            recommendations.append(
                {
                    "type": "maintenance",
                    "action": "Clean temporary files and logs",
                    "confidence": 0.95,
                    "priority": "high",
                    "estimated_impact": "Free up disk space",
                }
            )
            recommendations.append(
                {
                    "type": "capacity",
                    "action": "Consider disk expansion",
                    "confidence": 0.80,
                    "priority": "medium",
                    "estimated_impact": "Increase storage capacity",
                }
            )

        # Severity-based recommendations
        if severity == "critical":
            recommendations.append(
                {
                    "type": "escalation",
                    "action": "Escalate to on-call team immediately",
                    "confidence": 1.0,
                    "priority": "critical",
                    "estimated_impact": "Ensure immediate attention",
                }
            )

        # Sort by confidence and priority
        recommendations.sort(key=lambda r: (r["confidence"], r["priority"]), reverse=True)

        # Store in history
        self.recommendation_history.append(
            {
                "alert_id": alert_data.get("id"),
                "recommendations": recommendations,
                "timestamp": datetime.datetime.now().isoformat(),
            }
        )

        return recommendations

    async def get_personalized_recommendations(
        self, user_id: str, historical_actions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate personalized recommendations based on user's historical actions

        Args:
            user_id: User identifier
            historical_actions: User's historical action data

        Returns:
            Personalized recommendations
        """
        recommendations = []

        # Analyze user's preferred action types
        action_types = [action.get("type") for action in historical_actions]
        most_common_type = (
            max(set(action_types), key=action_types.count) if action_types else "optimization"
        )

        # Generate personalized recommendations based on preferences
        if most_common_type == "optimization":
            recommendations.append(
                {
                    "type": "optimization",
                    "action": "Optimization-based solution (based on your preference)",
                    "confidence": 0.85,
                    "personalization_reason": "You frequently choose optimization actions",
                }
            )
        elif most_common_type == "scaling":
            recommendations.append(
                {
                    "type": "scaling",
                    "action": "Scaling-based solution (based on your preference)",
                    "confidence": 0.85,
                    "personalization_reason": "You frequently choose scaling actions",
                }
            )

        return recommendations


# ============================================================
# P2 Enhancement: Natural Language Interaction
# ============================================================
class NaturalLanguageInteraction:
    """
    P2 Enhanced natural language interaction for AIOps
    """

    def __init__(self) -> None:
        self.conversation_history: Dict[str, List[Dict[str, Any]]] = {}
        self.intent_classifier: Optional[Any] = None
        self.entity_extractor: Optional[Any] = None

    async def process_natural_language_query(
        self, query: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process natural language query and generate response

        Args:
            query: Natural language query from user
            context: Additional context information

        Returns:
            Processed response with intent and entities
        """
        # Classify intent
        intent = await self._classify_intent(query)

        # Extract entities
        entities = await self._extract_entities(query)

        # Generate response based on intent
        response = await self._generate_response(intent, entities, context or {})

        return {
            "query": query,
            "intent": intent,
            "entities": entities,
            "response": response,
            "confidence": 0.85,
        }

    async def _classify_intent(self, query: str) -> str:
        """Classify the intent of the natural language query"""
        query_lower = query.lower()

        if any(word in query_lower for word in ["what", "status", "health", "check"]):
            return "status_query"
        elif any(word in query_lower for word in ["why", "reason", "cause", "root cause"]):
            return "root_cause_query"
        elif any(word in query_lower for word in ["how", "fix", "repair", "solve"]):
            return "repair_query"
        elif any(word in query_lower for word in ["predict", "forecast", "expect"]):
            return "prediction_query"
        elif any(word in query_lower for word in ["recommend", "suggest", "advise"]):
            return "recommendation_query"
        else:
            return "general_query"

    async def _extract_entities(self, query: str) -> Dict[str, Any]:
        """Extract entities from the natural language query"""
        entities = {}

        # Extract metric types
        if "cpu" in query.lower():
            entities["metric"] = "cpu"
        elif "memory" in query.lower():
            entities["metric"] = "memory"
        elif "disk" in query.lower():
            entities["metric"] = "disk"

        # Extract time ranges
        if "last hour" in query.lower():
            entities["time_range"] = "1h"
        elif "today" in query.lower():
            entities["time_range"] = "24h"
        elif "week" in query.lower():
            entities["time_range"] = "7d"

        return entities

    async def _generate_response(
        self, intent: str, entities: Dict[str, Any], context: Dict[str, Any]
    ) -> str:
        """Generate response based on intent and entities"""
        metric = entities.get("metric", "system")

        if intent == "status_query":
            return f"Current {metric} status: {context.get('metrics', {}).get(metric, 'unknown')}"
        elif intent == "root_cause_query":
            return f"Analyzing root cause for {metric} issue..."
        elif intent == "repair_query":
            return f"Generating repair suggestions for {metric}..."
        elif intent == "prediction_query":
            return f"Predicting {metric} trends for the next 24 hours..."
        elif intent == "recommendation_query":
            return f"Generating recommendations for {metric} optimization..."
        else:
            return f"I understand you're asking about {metric}. Let me help you with that."

    async def maintain_conversation(self, user_id: str, message: str) -> Dict[str, Any]:
        """
        Maintain conversation context across multiple turns

        Args:
            user_id: User identifier
            message: User's message

        Returns:
            Response with conversation context
        """
        if user_id not in self.conversation_history:
            self.conversation_history[user_id] = []

        self.conversation_history[user_id].append(
            {"role": "user", "content": message, "timestamp": datetime.datetime.now().isoformat()}
        )

        # Process the message
        response = await self.process_natural_language_query(message)

        # Add response to history
        self.conversation_history[user_id].append(
            {
                "role": "assistant",
                "content": response["response"],
                "timestamp": datetime.datetime.now().isoformat(),
            }
        )

        # Keep only last 10 messages
        if len(self.conversation_history[user_id]) > 10:
            self.conversation_history[user_id] = self.conversation_history[user_id][-10:]

        response["conversation_history"] = self.conversation_history[user_id]
        return response


# ============================================================
# P2 Enhancement: Global instances
# ============================================================
predictive_analysis_engine = PredictiveAnalysisEngine()
intelligent_recommendation_engine = IntelligentRecommendationEngine()
natural_language_interaction = NaturalLanguageInteraction()
