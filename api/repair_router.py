# -*- coding: utf-8 -*-
import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from core.repair_engine import execute_repair, get_repair_history, get_repair_scripts

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/repairs", tags=["自动修复"])


class RepairRequest(BaseModel):
    script_key: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="修复脚本键名,对应 REPAIR_SCRIPTS 中的 key",
        examples=["clear_temp"],
    )
    params: dict[str, str] = Field(
        default_factory=dict, description="修复脚本所需参数,如 {'service_name': 'nginx'}"
    )

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {"example": {"script_key": "example", "params": {}}},
    }


@router.get(
    "/scripts",
    summary="获取所有可用修复脚本",
    responses={
        (200): {
            "description": "修复脚本列表",
            "content": {
                "application/json": {
                    "example": {
                        "scripts": {
                            "clear_temp": {"name": "清理临时文件", "risk": "low"},
                            "restart_service": {"name": "重启服务", "risk": "medium"},
                        }
                    }
                }
            },
        },
        (500): {"description": "获取失败"},
    },
)
async def list_scripts() -> dict[str, Any]:
    """
    返回预置修复脚本列表
    对应前端修复面板的脚本选择区域
    """
    logger.info("请求修复脚本列表")
    try:
        scripts = get_repair_scripts()
        logger.debug(f"返回 {len(scripts)} 个可用修复脚本")
        return {"scripts": scripts}
    except Exception as e:
        logger.error(f"获取修复脚本列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取修复脚本列表失败: {str(e)[:200]}")


@router.post(
    "/execute",
    summary="执行修复脚本",
    responses={
        (200): {
            "description": "执行结果",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "script_key": "clear_temp",
                        "exit_code": 0,
                        "output": "清理完成",
                        "executed_at": "2026-07-03T09:00:00Z",
                    }
                }
            },
        },
        (403): {"description": "指令被护栏拦截"},
        (404): {"description": "脚本不存在"},
        (422): {"description": "参数校验失败"},
        (500): {"description": "执行失败"},
    },
)
async def run_repair(req: RepairRequest, request: Request) -> dict[str, Any]:
    """
    真实执行 PowerShell 修复脚本

    ⚠️ 高风险操作说明:
      - risk=high 的脚本(如终止进程)需谨慎使用
      - 服务需以管理员权限运行,否则部分脚本会失败
      - 所有执行记录保存到修复历史

    🔧 RR2 [P1]:错误码细分
        - 参数校验错误(pid 非数字、缺少必填等)→ 422
        - 脚本不存在 → 404
        - 命令被护栏拦截 → 403
        - 执行内部异常 → 500

    🔧 RR5 [P2]:记录操作人 IP
    """
    operator_ip = request.client.host if request.client else "unknown"
    logger.warning(
        f"收到修复请求 | operator={operator_ip} | script_key='{req.script_key}' | 参数={req.params}"
    )
    try:
        result = await execute_repair(req.script_key, req.params)
    except Exception as e:
        logger.error(f"执行修复脚本时发生未预期异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"修复引擎内部错误: {str(e)[:200]}")
    if result is None:
        logger.error("execute_repair 返回 None,修复引擎异常")
        raise HTTPException(status_code=500, detail="修复引擎未返回结果,请检查服务日志")
    if not isinstance(result, dict):
        logger.error(f"execute_repair 返回非 dict 类型: {type(result).__name__}")
        raise HTTPException(status_code=500, detail="修复引擎返回类型异常")
    if not result.get("success") and "error" in result:
        error_msg = str(result["error"])
        if result.get("blocked"):
            safe_alt = result.get("safe_alternative", "")
            detail = f"指令被护栏拦截: {error_msg}"
            if safe_alt:
                detail += f"\n安全替代方案: {safe_alt}"
            logger.warning(
                f"修复被护栏拦截 | operator={operator_ip} | script_key='{req.script_key}'"
            )
            raise HTTPException(status_code=403, detail=detail)
        if "未知修复脚本" in error_msg or "not found" in error_msg.lower():
            logger.warning(f"修复脚本不存在 | script_key='{req.script_key}'")
            raise HTTPException(status_code=404, detail=error_msg)
        param_error_keywords = (
            "pid",
            "service_name",
            "缺少必要参数",
            "必须为",
            "禁止操作",
            "不允许",
        )
        if any(kw in error_msg for kw in param_error_keywords):
            logger.warning(f"修复参数校验失败 | script_key='{req.script_key}' | {error_msg}")
            raise HTTPException(status_code=422, detail=error_msg)
        logger.warning(
            f"修复脚本执行失败 | operator={operator_ip} | script_key='{req.script_key}' |"
            f" error={error_msg}"
        )
        raise HTTPException(status_code=500, detail=error_msg)
    logger.info(
        f"修复脚本执行成功 | operator={operator_ip} | script_key='{req.script_key}' |"
        f" output_length={len(str(result.get('output', '')))}"
    )
    return result


@router.get(
    "/history",
    summary="获取修复历史记录",
    responses={
        (200): {
            "description": "修复历史记录",
            "content": {
                "application/json": {
                    "example": {
                        "history": [
                            {
                                "script_key": "clear_temp",
                                "exit_code": 0,
                                "executed_at": "2026-07-03T09:00:00Z",
                            }
                        ],
                        "total": 1,
                    }
                }
            },
        },
        (500): {"description": "获取失败"},
    },
)
async def get_history(
    limit: int = Query(default=20, ge=1, le=500, description="返回记录数量上限,范围 1-500")
) -> dict[str, Any]:
    """
    返回最近的修复执行历史记录(时间倒序)
    包含每次修复的脚本名称、执行结果、输出内容

    🔧 RR1 [P1]:原代码调用了 2 次 get_repair_history(分别取 records 和 total),
                  浪费 CPU 且可能数据不一致(并发写入时)。
                  修复:1 次查询,total = len(records)
    🔧 RR4 [P2]:limit 二次钳制
    """
    safe_limit = max(1, min(500, int(limit) if limit else 20))
    logger.info(f"请求修复历史记录,limit={safe_limit}")
    try:
        records = get_repair_history(safe_limit)
        total = len(records)
        logger.debug(f"修复历史查询成功 | 返回={total}条")
        return {"total": total, "records": records}
    except Exception as e:
        logger.error(f"获取修复历史记录失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取修复历史失败: {str(e)[:200]}")
