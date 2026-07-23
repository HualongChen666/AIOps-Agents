# -*- coding: utf-8 -*-
import logging
import re
from typing import Any, Literal, Optional

from fastapi import APIRouter, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field, field_validator

from config import ALLOWED_LOCAL_IPS, GUARD_DEFAULT_HOST
from core.command_guard import (
    RiskLevel,
    analyze_command,
    dry_run_preview,
    get_audit_log,
    is_command_allowed,
    record_audit,
    rewrite_to_safe,
)


def mask_sensitive(log: dict) -> dict:
    """脱敏处理审计日志中的敏感信息"""
    masked_log = log.copy()
    if "command" in masked_log:
        command = masked_log["command"]
        if isinstance(command, str):
            masked_log["command"] = command[:50] + "..." if len(command) > 50 else command
    return masked_log


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/guard", tags=["高危指令管控"])
_AUDIT_STATS_QUERY_LIMIT = 5000
_VALID_HOST_PATTERN = re.compile("^[a-zA-Z0-9._\\-:]+$")


class CommandCheckRequest(BaseModel):
    """
    🔧 BUG-FIX-7+8(中危):兼容旧字段 + 防止客户端伪造
    🔧 GR5 [P2]:target_host 字符过滤
    """

    model_config = {"extra": "ignore"}
    command: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="要检查的命令字符串",
        examples=["rm -rf /tmp/cache"],
    )
    target_host: str = Field(
        default=GUARD_DEFAULT_HOST,
        max_length=128,
        description="命令将要执行的目标主机(业务字段,非审计字段)",
        validation_alias="host",
    )

    @field_validator("target_host")
    @classmethod
    def _validate_target_host(cls, v: str) -> str:
        v = (v or GUARD_DEFAULT_HOST).strip()[:128]
        if not v:
            return GUARD_DEFAULT_HOST
        if not _VALID_HOST_PATTERN.match(v):
            cleaned = re.sub("[^a-zA-Z0-9._\\-:]", "", v)
            return cleaned[:128] or GUARD_DEFAULT_HOST
        return v

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {"example": {"command": "example", "target_host": "example"}},
    }


class CommandRewriteRequest(BaseModel):
    command: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="要改写的命令",
        examples=["rm -rf /tmp/old_data"],
    )

    model_config = {"extra": "ignore", "json_schema_extra": {"example": {"command": "example"}}}


def _safe_record_audit(
    host: str, command: str, risk_level: str, executor: str, audit_status: str
) -> bool:
    """
    🔧 GR1 [P0]:安全审计写入,失败仅打 warning,不阻塞主流程
    Returns:
        True=审计成功,False=审计失败(已记录日志)
    """
    try:
        record_audit(
            host=host,
            command=command,
            risk_level=risk_level,
            executor=executor,
            result=audit_status,
        )
        return True
    except Exception as audit_err:
        logger.warning(f"GR1: 审计写入失败(不影响护栏检查): {audit_err}")
        return False


def _get_executor_info(request: Request) -> tuple[str, str]:
    """
    🔧 GR2 [P1]:从请求中提取执行者身份(防御 None)
    Returns:
        (executor, source_ip)
    """
    if request.client is not None:
        source_ip = request.client.host or "unknown"
    else:
        source_ip = "unknown"
    if source_ip in ALLOWED_LOCAL_IPS or source_ip == "unknown":
        executor = "local_caller"
    else:
        executor = f"remote@{source_ip}"
    return executor, source_ip


def _verify_audit_access(request: Request, x_internal_key: Optional[str] = None) -> None:
    """
    🔧 GR3 [P1]:验证审计接口访问权限
    复用 stats_router 的权限校验设计

    Raises:
        HTTPException(403) 不满足条件
    """
    try:
        from config import INTERNAL_API_KEY, TRUST_PROXY_HEADER
    except ImportError:
        INTERNAL_API_KEY = ""
        TRUST_PROXY_HEADER = ""
    _, source_ip = _get_executor_info(request)
    if INTERNAL_API_KEY:
        if x_internal_key != INTERNAL_API_KEY:
            logger.warning(
                f"GR3: 审计接口拒绝访问(密钥不匹配)| ip={source_ip} |"
                f" 提供={'有' if x_internal_key else '无'}"
            )
            raise HTTPException(status_code=403, detail="禁止访问:审计接口需要 X-Internal-Key 认证")
        return
    if TRUST_PROXY_HEADER:
        logger.warning(f"GR3: 审计接口拒绝访问(代理场景下未配置密钥)| ip={source_ip}")
        raise HTTPException(
            status_code=403, detail="禁止访问:反向代理场景下必须配置 INTERNAL_API_KEY"
        )
    if source_ip not in ALLOWED_LOCAL_IPS:
        logger.warning(f"GR3: 审计接口拒绝访问(非本地调用)| ip={source_ip}")
        raise HTTPException(
            status_code=403,
            detail="禁止访问:审计接口仅供本地调用。如需远程调用,请在 .env 中设置 INTERNAL_API_KEY",
        )


def _extract_request_identity(request: Request) -> tuple[str, str, str]:
    """提取请求身份信息

    Returns:
        (executor, source_ip, user_agent)
    """
    executor, source_ip = _get_executor_info(request)
    user_agent = request.headers.get("user-agent", "")[:100]
    return executor, source_ip, user_agent


def _build_check_response(
    analysis_result: dict, executor: str, source_ip: str, audit_recorded: bool
) -> dict[str, Any]:
    """构建检查响应

    Returns:
        响应字典
    """
    risk_level = analysis_result["risk_level"]
    return {
        "command": str(analysis_result.get("command", ""))[:2000],
        "risk_level": risk_level.value,
        "risk_name": str(analysis_result.get("risk_name", "")),
        "reason": str(analysis_result.get("reason", "")),
        "action": str(analysis_result.get("action", "")),
        "safe_alternative": str(analysis_result.get("safe_alternative", "")),
        "is_chained": bool(analysis_result.get("is_chained", False)),
        "chain_count": int(analysis_result.get("chain_count", 1)),
        "audit": {"executor": executor, "source_ip": source_ip, "recorded": audit_recorded},
    }


@router.post(
    "/check",
    summary="检查命令风险等级",
    responses={
        (200): {
            "description": "命令风险评估结果",
            "content": {
                "application/json": {
                    "example": {
                        "command": "rm -rf /tmp/cache",
                        "risk_level": "high",
                        "risk_name": "高危删除操作",
                        "reason": "删除系统目录",
                        "action": "approve",
                        "safe_alternative": "rm -rf /tmp/cache/*",
                        "is_chained": False,
                        "chain_count": 1,
                        "audit": {
                            "executor": "local_caller",
                            "source_ip": "127.0.0.1",
                            "recorded": True,
                        },
                    }
                }
            },
        },
        (422): {"description": "参数校验失败"},
        (500): {"description": "指令风险检查失败"},
    },
)
async def check_command(req: CommandCheckRequest, request: Request) -> dict[str, Any]:
    """
    分析命令的风险等级,返回风险评估结果

    🔧 BUG-FIX-14(中危):审计身份字段(executor/source_ip)由服务端从请求中提取
                          客户端无法伪造,确保审计日志可信
    🔧 GR1 [P0]:审计写入异常不阻塞主流程

    返回字段:
      risk_level: safe / low / medium / high / blocked
      action:     execute / confirm / approve / block
      reason:     风险说明
      safe_alternative: 安全替代方案(如有)
      is_chained: 是否为命令链(含 ; && || |)
      audit:      { executor, source_ip, recorded }(服务端提取,不可伪造)
    """
    executor, source_ip, user_agent = _extract_request_identity(request)
    logger.info(
        f"指令风险检查 | executor={executor} | target_host={req.target_host} | ua={user_agent[:30]}"
        f" | cmd={req.command[:80]}"
    )
    try:
        analysis_result = analyze_command(req.command)
        risk_level = analysis_result["risk_level"]
        audit_recorded = True
        if risk_level in (RiskLevel.HIGH, RiskLevel.BLOCKED):
            audit_recorded = _safe_record_audit(
                host=req.target_host,
                command=req.command,
                risk_level=risk_level.value,
                executor=executor,
                audit_status=f"checked_{risk_level.value}",
            )
        return _build_check_response(analysis_result, executor, source_ip, audit_recorded)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"指令检查异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="指令风险检查失败,请查看服务日志")


@router.post(
    "/allowed",
    summary="快速判断命令是否允许执行",
    responses={
        (200): {
            "description": "快速检查结果",
            "content": {"application/json": {"example": {"command": "ls -la", "allowed": True}}},
        },
        (422): {"description": "参数校验失败"},
        (500): {"description": "指令检查失败"},
    },
)
async def check_allowed(req: CommandCheckRequest) -> dict[str, Any]:
    """
    快速判断:BLOCKED → False,其他 → True
    适用于前端输入框实时校验
    """
    logger.debug(f"快速检查: {req.command[:60]}")
    try:
        allowed = is_command_allowed(req.command)
        return {"command": req.command, "allowed": allowed}
    except Exception as e:
        logger.error(f"快速检查异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="指令检查失败")


@router.post(
    "/rewrite",
    summary="将高危命令改写为安全版本",
    responses={
        (200): {
            "description": "命令改写结果",
            "content": {
                "application/json": {
                    "example": {
                        "original": "rm -rf /tmp/old_data",
                        "rewritten": "mv /tmp/old_data /tmp/trash/old_data",
                        "changed": True,
                        "message": "已改写为安全版本",
                    }
                }
            },
        },
        (422): {"description": "参数校验失败"},
        (500): {"description": "指令改写失败"},
    },
)
async def rewrite_command(req: CommandRewriteRequest) -> dict[str, Any]:
    """将 rm 等高危命令改写为安全版本(如 rm → mv 到回收站)"""
    logger.info(f"指令改写请求: {req.command[:80]}")
    try:
        original = req.command
        rewritten = rewrite_to_safe(original)
        changed = rewritten != original
        return {
            "original": original,
            "rewritten": rewritten,
            "changed": changed,
            "message": "已改写为安全版本" if changed else "无需改写",
        }
    except Exception as e:
        logger.error(f"指令改写异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="指令改写失败")


@router.post(
    "/dryrun",
    summary="生成命令的 Dry-run 预览",
    responses={
        (200): {
            "description": "Dry-run预览结果",
            "content": {
                "application/json": {
                    "example": {
                        "original": "rm -rf /tmp/cache",
                        "preview": "Would delete: /tmp/cache/file1.txt, /tmp/cache/file2.txt",
                    }
                }
            },
        },
        (422): {"description": "参数校验失败"},
        (500): {"description": "Dry-run预览生成失败"},
    },
)
async def dryrun_command(req: CommandCheckRequest) -> dict[str, Any]:
    """生成命令预览版本(不实际执行),用于确认影响范围"""
    logger.debug(f"Dry-run 预览: {req.command[:80]}")
    try:
        preview = dry_run_preview(req.command)
        return {"original": req.command, "preview": preview}
    except Exception as e:
        logger.error(f"Dry-run 异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Dry-run 预览生成失败")


@router.get(
    "/audit",
    summary="获取命令执行审计日志(需权限)",
    responses={
        (200): {
            "description": "审计日志列表",
            "content": {
                "application/json": {
                    "example": {
                        "total": 50,
                        "filter": {"risk_level": "high"},
                        "logs": [
                            {
                                "command": "rm -rf /tmp",
                                "risk_level": "high",
                                "executor": "local_caller",
                                "timestamp": "2026-07-02T10:30:00Z",
                            }
                        ],
                    }
                }
            },
        },
        (403): {"description": "权限不足(需要本地访问或X-Internal-Key)"},
        (500): {"description": "获取审计日志失败"},
    },
)
async def get_audit(
    request: Request,
    limit: int = Query(default=50, ge=1, le=500),
    risk_level: Optional[Literal["safe", "low", "medium", "high", "blocked"]] = Query(
        default=None, description="按风险等级过滤(留空返回全部)"
    ),
    x_internal_key: Optional[str] = Header(default=None, alias="X-Internal-Key"),
) -> dict[str, Any]:
    """
    返回最近的命令执行审计日志
    含:谁 / 何时 / 在哪 / 做了什么 / 风险等级 / 执行结果

    🔧 GR3 [P1]:增加权限保护(本地访问 / X-Internal-Key)
    🔧 GR8 [P2]:增加 risk_level 过滤参数
    """
    _verify_audit_access(request, x_internal_key)
    logger.info(f"请求审计日志 | limit={limit} | filter={risk_level or '全部'}")
    try:
        query_limit = limit * 3 if risk_level else limit
        query_limit = min(query_limit, _AUDIT_STATS_QUERY_LIMIT)
        raw_logs = get_audit_log(query_limit)
        logs = [mask_sensitive(log) for log in raw_logs]
        if risk_level:
            logs = [log for log in logs if log.get("risk_level") == risk_level]
        logs = logs[:limit]
        return {"total": len(logs), "filter": {"risk_level": risk_level}, "logs": logs}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取审计日志失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取审计日志失败")


@router.get(
    "/stats",
    summary="获取审计统计摘要(需权限)",
    responses={
        (200): {
            "description": "审计统计摘要",
            "content": {
                "application/json": {
                    "example": {
                        "total": 1000,
                        "level_counts": {
                            "safe": 800,
                            "low": 150,
                            "medium": 30,
                            "high": 15,
                            "blocked": 5,
                        },
                        "blocked_count": 5,
                        "high_count": 15,
                        "block_rate": 0.5,
                        "query_limit": 5000,
                    }
                }
            },
        },
        (403): {"description": "权限不足(需要本地访问或X-Internal-Key)"},
        (500): {"description": "获取审计统计失败"},
    },
)
async def get_audit_stats(
    request: Request, x_internal_key: Optional[str] = Header(default=None, alias="X-Internal-Key")
) -> dict[str, Any]:
    """
    返回审计日志的统计摘要
    含各风险等级命令数量、拦截率等

    🔧 GR3 [P1]:增加权限保护
    🔧 GR4 [P1]:从硬编码 500 改为常量
    """
    _verify_audit_access(request, x_internal_key)
    logger.info("请求审计统计摘要")
    try:
        logs = get_audit_log(limit=_AUDIT_STATS_QUERY_LIMIT)
        total = len(logs)
        level_counts: dict[str, int] = {}
        for log in logs:
            lv = str(log.get("risk_level", "unknown"))
            level_counts[lv] = level_counts.get(lv, 0) + 1
        blocked_count = level_counts.get("blocked", 0)
        high_count = level_counts.get("high", 0)
        block_rate = round(blocked_count / total * 100, 1) if total > 0 else 0.0
        return {
            "total": total,
            "level_counts": level_counts,
            "blocked_count": blocked_count,
            "high_count": high_count,
            "block_rate": block_rate,
            "query_limit": _AUDIT_STATS_QUERY_LIMIT,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取审计统计失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取审计统计失败")
