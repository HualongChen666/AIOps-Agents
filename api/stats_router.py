# -*- coding: utf-8 -*-
import hmac
import logging
import time
from threading import Lock
from typing import Any, Optional

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field

from config import ALLOWED_LOCAL_IPS, INTERNAL_API_KEY, TRUST_PROXY_HEADER
from core.stats_engine import get_real_summary, record_repair

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/stats", tags=["统计数据"])
_SUMMARY_CACHE_TTL_SEC = 2
_summary_cache: dict[str, Any] = {"data": None, "ts": 0.0}
_summary_cache_lock = Lock()


def _get_real_client_ip(request: Request) -> str:
    """
    获取真实客户端 IP

    🔧 BUG-FIX-22(中危):修复 X-Forwarded-For 取值方向错误
    🔧 SR1 [P1]:空字符串提前 return,逻辑更清晰
    """
    if TRUST_PROXY_HEADER:
        import config

        TRUSTED_PROXY_COUNT = getattr(config, "TRUSTED_PROXY_COUNT", 1)
        xff = request.headers.get("x-forwarded-for", "").strip()
        if not xff:
            return request.client.host if request.client else "unknown"
        ips = [ip.strip() for ip in xff.split(",") if ip.strip()]
        if ips:
            idx = max(0, len(ips) - 1 - TRUSTED_PROXY_COUNT)
            return str(ips[idx])
    return request.client.host if request.client else "unknown"


def _verify_internal_caller(request: Request, x_internal_key: Optional[str] = None) -> None:
    """
    验证调用者是否为可信内部来源

    优先级:
      1. INTERNAL_API_KEY 已配置 → 必须匹配 X-Internal-Key 请求头
      2. INTERNAL_API_KEY 未配置 → 仅允许本地回环地址访问
      3. 反向代理场景下(TRUST_PROXY_HEADER=true)强制要求密钥

    🔧 SR6 [P2]:使用 hmac.compare_digest 恒定时间比较,
                  防御针对密钥的时序攻击

    Raises:
        HTTPException(403) 不匹配任一条件
    """
    if INTERNAL_API_KEY:
        provided_key = x_internal_key or ""
        if not hmac.compare_digest(provided_key, INTERNAL_API_KEY):
            client_ip = _get_real_client_ip(request)
            logger.warning(
                f"内部接口拒绝访问(密钥不匹配)| ip={client_ip} |"
                f" 提供={'有' if x_internal_key else '无'}"
            )
            raise HTTPException(status_code=403, detail="禁止访问:此接口仅供内部调用")
        return
    if TRUST_PROXY_HEADER:
        client_ip = _get_real_client_ip(request)
        logger.warning(f"内部接口拒绝访问(代理场景下未配置密钥)| ip={client_ip}")
        raise HTTPException(
            status_code=403,
            detail="禁止访问:反向代理场景下必须配置 INTERNAL_API_KEY,否则白名单将失效",
        )
    client_ip = _get_real_client_ip(request)
    if client_ip not in ALLOWED_LOCAL_IPS:
        logger.warning(f"内部接口拒绝访问(非本地调用,且未配置 INTERNAL_API_KEY)| ip={client_ip}")
        raise HTTPException(
            status_code=403,
            detail="禁止访问:此接口仅供本地调用。如需远程调用,请在 .env 中设置 INTERNAL_API_KEY",
        )


class RepairRecordRequest(BaseModel):
    success: bool = Field(..., description="修复操作是否成功:true=成功,false=失败")
    rule_name: str = Field(
        default="", max_length=128, description="触发的修复规则名称(可选,用于审计追溯)"
    )
    script_key: str = Field(default="", max_length=64, description="执行的修复脚本 key(可选)")
    platform: str = Field(
        default="windows", pattern="^(windows|linux)$", description="目标平台(默认 windows)"
    )
    output: str = Field(
        default="", max_length=2000, description="修复输出摘要(可选,失败时建议填写)"
    )

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {
            "example": {
                "success": True,
                "rule_name": "example",
                "script_key": "example",
                "platform": "example",
                "output": "example",
            }
        },
    }


@router.get(
    "/summary",
    summary="获取真实统计摘要数据",
    responses={(200): {"description": "统计摘要数据"}, (500): {"description": "统计数据计算失败"}},
)
def get_summary() -> dict[str, Any]:
    """
    返回总览大盘真实统计数据,替换前端随机模拟值
    对应:
      今日告警数 / 修复成功数 / MTTD / RCA准确率 /
      降噪效率 / 自愈成功率 / Agent健康度

    🔧 SR3 [P2]:路由层 2 秒 TTL 缓存
        - stats_engine.get_real_summary 内部已有 5 秒 TTL 缓存
        - 此处再加 2 秒缓存作为路由层快速防护
        - 高频轮询场景(如多用户同时刷新)可减少函数调用开销
    """
    now = time.monotonic()
    with _summary_cache_lock:
        if (
            _summary_cache["data"] is not None
            and now - _summary_cache["ts"] < _SUMMARY_CACHE_TTL_SEC
        ):
            logger.debug("统计摘要命中路由层缓存")
            return dict(_summary_cache["data"])
    logger.debug("请求真实统计摘要数据")
    try:
        summary = get_real_summary()
        with _summary_cache_lock:
            _summary_cache["data"] = dict(summary)
            _summary_cache["ts"] = time.monotonic()
        logger.debug(
            f"统计摘要返回成功 | 告警={summary.get('total_alerts')} 修复={summary.get('resolved')}"
            f" 自愈率={summary.get('heal_rate')}%"
        )
        return summary
    except Exception as e:
        logger.error(f"统计摘要计算失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"统计数据计算失败: {str(e)[:200]}")


@router.post(
    "/repair/record",
    summary="记录修复操作结果(内部接口)",
    responses={
        (200): {"description": "记录成功"},
        (401): {"description": "权限验证失败"},
        (500): {"description": "记录失败"},
    },
)
def record_repair_result(
    payload: RepairRecordRequest,
    request: Request,
    x_internal_key: Optional[str] = Header(default=None, alias="X-Internal-Key"),
) -> dict[str, Any]:
    """
    记录一次修复操作的执行结果到统计引擎

    🔧 BUG-FIX-12(中危):此接口为内部接口,需通过权限校验
    🔧 SR2 [P1]:支持额外字段(rule_name/script_key/platform/output)
    🔧 SR4 [P2]:与 stats_engine.record_repair 接口完全对齐
    🔧 SR6 [P2]:_verify_internal_caller 内部使用 hmac.compare_digest

    访问方式:
      1. 若 .env 配置了 INTERNAL_API_KEY,需在请求头携带 X-Internal-Key
      2. 否则仅允许本地回环地址(127.0.0.1)访问
      3. 反向代理场景(TRUST_PROXY_HEADER=true)下必须配置密钥

    请求示例:
      curl -X POST http://localhost:8000/api/stats/repair/record \\
           -H "X-Internal-Key: your-secret-key" \\
           -H "Content-Type: application/json" \\
           -d '{"success": true, "rule_name": "CPU 高负载修复", "script_key": "kill_high_cpu"}'
    """
    _verify_internal_caller(request, x_internal_key)
    logger.info(
        f"记录修复结果 | success={payload.success} | rule={payload.rule_name or 'N/A'} |"
        f" script={payload.script_key or 'N/A'} | platform={payload.platform}"
    )
    try:
        repair_data = {
            "success": payload.success,
            "alert_time": None,
            "rule_name": payload.rule_name,
            "script_key": payload.script_key,
            "platform": payload.platform,
            "output": payload.output,
        }
        record_repair(repair_data)
        with _summary_cache_lock:
            _summary_cache["data"] = None
            _summary_cache["ts"] = 0.0
        return {
            "status": "ok",
            "message": f"修复结果已记录: {'成功' if payload.success else '失败'}",
            "details": {
                "success": payload.success,
                "rule_name": payload.rule_name or None,
                "script_key": payload.script_key or None,
                "platform": payload.platform,
            },
        }
    except Exception as e:
        logger.error(f"修复结果记录失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"修复结果记录失败: {str(e)[:200]}")
