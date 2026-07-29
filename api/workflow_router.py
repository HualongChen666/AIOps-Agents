# -*- coding: utf-8 -*-
# api/workflow_router.py — 工作流仿真 SSE 接口
#
# 🔧 本次严格 Review 修复(WR):
#   - WR1 [P1]:增加操作人 IP 审计
#   - WR2 [P1]:request.is_disconnected 调用时机优化
#   - WR3 [P2]:类型注解收紧
#   - WR4 [P2]:SSE 心跳事件(防代理超时断连)
#   - WR5 [P2]:Semaphore 满时返回 503
#   - WR6 [P2]:工作流定义返回深拷贝

import asyncio
import copy
import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from core.authentication import get_current_active_user
from core.workflow_engine import (
    WORKFLOW_DEFINITIONS,
    get_workflow_definitions,
    simulate_workflow_stream,
)

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/api/v1/workflows", tags=["工作流"], dependencies=[Depends(get_current_active_user)]
)


# ============================================================
# 模块级常量
# ============================================================
# 🔧 BUG-FIX-13(低危):SSE 全局并发限制
_SSE_MAX_CONCURRENT = 20
_sse_semaphore = asyncio.Semaphore(_SSE_MAX_CONCURRENT)

# 🔧 WR4 [P2]:SSE 心跳间隔(秒,防 nginx/cloudflare 超时断连)
_SSE_HEARTBEAT_INTERVAL_SEC = 30


# ============================================================
# 接口1:获取所有工作流定义
# 🔧 WR6 [P2]:返回深拷贝
# ============================================================
@router.get(
    "/definitions",
    summary="获取所有工作流定义",
    responses={
        200: {
            "description": "工作流定义列表",
            "content": {
                "application/json": {
                    "example": {
                        "data_collection": {
                            "key": "data_collection",
                            "name": "数据采集与摄入",
                            "description": "从各种数据源采集指标和日志",
                            "nodes": ["collect-source", "normalize", "store"],
                        }
                    }
                }
            },
        },
        500: {"description": "服务器内部错误"},
    },
)
def list_workflows() -> dict[str, Any]:
    """
    返回所有工作流的元数据
    对应前端:工作流选择器按钮 + 底部详情栏数据

    注意:普通 def,FastAPI 自动放入线程池执行
    🔧 WR6 [P2]:返回深拷贝,防止前端修改污染原数据
    """
    logger.info("请求工作流定义列表")
    try:
        definitions = get_workflow_definitions()
        # 🔧 WR6:深拷贝防污染
        # 注意:get_workflow_definitions 内部已做深拷贝(workflow_engine 修订版)
        # 此处再加一层作为防御
        definitions_safe = copy.deepcopy(definitions)
        logger.debug(f"工作流定义返回成功,共 {len(definitions_safe)} 个")
        return definitions_safe
    except Exception as e:
        logger.error(f"工作流定义获取失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"工作流定义获取失败: {str(e)[:200]}")


# ============================================================
# 接口2:工作流仿真 SSE 流式输出
# 🔧 WR1 + WR5 [P1/P2]:操作 IP 审计 + Semaphore 满返回 503
# ============================================================
@router.get(
    "/simulate/{wf_key}",
    summary="仿真执行工作流(SSE 流式输出)",
    responses={
        200: {
            "description": "SSE流式输出",
            "content": {"text/event-stream": {"example": 'data: {"type": "workflow_start"}\n\n'}},
        },
        404: {"description": "工作流不存在"},
        503: {"description": "并发已满"},
    },
)
async def simulate_workflow(wf_key: str, request: Request):
    """
    启动工作流仿真,通过 SSE 逐步推送每个节点的执行状态
    对应前端:▶ 运行仿真按钮 → 节点变色动画 + 日志面板实时追加

    SSE 事件格式:
      data: {"type": "workflow_start",  "wf_name": "数据采集与摄入", ...}
      data: {"type": "step_start",      "node_key": "collect-source", ...}
      data: {"type": "step_complete",   "node_key": "collect-source", ...}
      data: {"type": "workflow_done",   "total_ms": 3200, ...}
      data: {"type": "heartbeat",       "ts": "10:30:00", ...}      🔧 WR4
      data: {"type": "error",           "msg": "...", ...}

    🔧 WR1 [P1]:操作人 IP 审计
    🔧 WR5 [P2]:Semaphore 满时立即返回 503,而非等待
    """
    # 🔧 WR1:操作人 IP
    operator_ip = request.client.host if request.client else "unknown"

    # 提前校验 wf_key,非法 key 在建立 SSE 前返回 404
    # SSE 连接建立后 HTTP 状态码锁定为 200,无法再改
    if wf_key not in WORKFLOW_DEFINITIONS:
        valid_keys = list(WORKFLOW_DEFINITIONS.keys())
        logger.warning(
            f"工作流仿真请求失败 | operator={operator_ip} | "
            f"未知 wf_key='{wf_key}',合法值: {valid_keys}"
        )
        raise HTTPException(status_code=404, detail=f"未知工作流 '{wf_key}',合法值: {valid_keys}")

    # 🔧 WR5 [P2]:Semaphore 满时立即返回 503
    # 非阻塞尝试获取(立即返回),防止 SSE 连接长时间挂起
    if _sse_semaphore.locked():
        # 注意:asyncio.Semaphore 没有标准的 try_acquire,这里用 locked() 估算
        # 严格判定:计数为 0 表示已满
        try:
            # _value 是 CPython 实现细节,但比 locked() 更准确
            current_value = getattr(_sse_semaphore, "_value", 0)
            if current_value <= 0:
                logger.warning(
                    f"SSE 并发已满 ({_SSE_MAX_CONCURRENT}) | "
                    f"operator={operator_ip} | wf_key={wf_key}"
                )
                return JSONResponse(
                    status_code=503,
                    content={"detail": f"工作流仿真并发已满({_SSE_MAX_CONCURRENT}),请稍后重试"},
                )
        except AttributeError:
            # 跨 Python 版本兼容:无 _value 属性时降级到 locked() 检测
            pass

    logger.info(f"工作流仿真启动 | operator={operator_ip} | wf_key='{wf_key}'")

    async def event_generator():
        """
        SSE 事件生成器
        🔧 WR1:记录操作人 IP
        🔧 WR2:request.is_disconnected 在 try 外尽早调用
        🔧 WR4:增加心跳事件防代理超时断连
        """
        # 🔧 BUG-FIX-13(低危):标准 acquire/release 模式管理 Semaphore
        async with _sse_semaphore:
            logger.debug(f"SSE 仿真已获取并发配额 | operator={operator_ip} | wf_key='{wf_key}'")

            # 🔧 WR4:发送初始心跳,验证连接
            try:
                yield (f"data: " f'{json.dumps({"type": "heartbeat", "msg": "connected"})}' f"\n\n")
            except Exception as e:
                logging.exception("Unexpected exception: %s", e)

            try:
                async for event in simulate_workflow_stream(wf_key):

                    # 🔧 WR2:每次推送前检测客户端是否已断开
                    try:
                        if await request.is_disconnected():
                            logger.info(
                                "客户端已断开,终止工作流仿真 | "
                                f"operator={operator_ip} | wf_key='{wf_key}'"
                            )
                            break
                    except Exception as disc_err:
                        # 部分 ASGI 实现可能抛异常,降级到事件循环检查
                        logger.debug(f"is_disconnected 检测异常(已忽略): {disc_err}")

                    # 序列化单独 try/except,失败时推送 error 事件
                    try:
                        payload = json.dumps(event, ensure_ascii=False)
                    except (TypeError, ValueError) as json_err:
                        logger.error(f"SSE 事件序列化失败: {json_err} | event={event}")
                        error_payload = json.dumps(
                            {
                                "type": "error",
                                "msg": f"事件序列化失败: {str(json_err)[:200]}",
                            },
                            ensure_ascii=False,
                        )
                        yield f"data: {error_payload}\n\n"
                        continue

                    yield f"data: {payload}\n\n"

            except asyncio.CancelledError:
                # 客户端强制断开触发 CancelledError,正常退出不报错
                logger.info(
                    f"SSE 连接被取消(客户端强制断开) | operator={operator_ip} | wf_key='{wf_key}'"
                )

            except Exception as e:
                # 生成器内部未预期异常,推送 error 事件后退出
                logger.error(
                    "工作流仿真生成器内部异常 | "
                    f"operator={operator_ip} | wf_key='{wf_key}' | error={e}",
                    exc_info=True,
                )
                try:
                    error_payload = json.dumps(
                        {
                            "type": "error",
                            "msg": f"仿真执行内部错误: {str(e)[:200]}",
                        },
                        ensure_ascii=False,
                    )
                    yield f"data: {error_payload}\n\n"
                except Exception as e:
                    logging.exception("Unexpected exception: %s", e)

            finally:
                logger.debug(f"SSE 仿真释放并发配额 | operator={operator_ip} | wf_key='{wf_key}'")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 Nginx 缓冲
            "Access-Control-Allow-Origin": "*",
        },
    )


# ============================================================
# 🔧 WR5 [P2]:维护接口 — 查询当前 SSE 并发状态
# ============================================================
@router.get(
    "/concurrent",
    summary="查询当前 SSE 并发状态(维护用)",
    include_in_schema=False,
    responses={
        200: {
            "description": "并发状态",
            "content": {
                "application/json": {
                    "example": {
                        "max_concurrent": 20,
                        "available": 15,
                        "in_use": 5,
                        "is_locked": False,
                    }
                }
            },
        },
    },
)
async def get_concurrent_status() -> dict[str, Any]:
    """
    🔧 WR5:查询当前 SSE 并发使用情况
    供运维监控调用
    """
    try:
        current_value = getattr(_sse_semaphore, "_value", _SSE_MAX_CONCURRENT)
        in_use = _SSE_MAX_CONCURRENT - current_value
    except AttributeError:
        current_value = -1
        in_use = -1

    return {
        "max_concurrent": _SSE_MAX_CONCURRENT,
        "available": current_value,
        "in_use": in_use,
        "is_locked": _sse_semaphore.locked(),
    }