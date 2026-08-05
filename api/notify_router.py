# -*- coding: utf-8 -*-
import datetime
import logging
from typing import Any, Literal

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

import core.notify_engine as _notify_engine

from core.notify_engine import reload_notify_config, send_alert_notification
from core.oncall_adapter import get_oncall_adapter

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/api/notify", tags=["告警通知"]
)
_REQUIRED_ALERT_FIELDS = frozenset(["level", "title", "desc"])


def _safe_get_notify_config() -> dict[str, Any]:
    """
    🔧 NR1:安全访问 NOTIFY_CONFIG
    防御 notify_engine 模块加载失败或 NOTIFY_CONFIG 字段缺失
    """
    try:
        cfg = getattr(_notify_engine, "NOTIFY_CONFIG", None)
        if cfg is None or not isinstance(cfg, dict):
            logger.warning("NR1: NOTIFY_CONFIG 不存在或非 dict,返回空配置")
            return {"enabled": False}
        return cfg
    except Exception as e:
        logger.error(f"NR1: NOTIFY_CONFIG 访问异常: {e}", exc_info=True)
        return {"enabled": False}


class NotifyTestRequest(BaseModel):
    level: Literal["info", "warning", "critical"] = Field(
        default="critical", description="告警级别: info | warning | critical"
    )
    title: str = Field(
        default="AIOps 测试告警", min_length=1, max_length=100, description="告警标题"
    )
    desc: str = Field(
        default="这是一条测试告警消息", min_length=1, max_length=500, description="告警详情描述"
    )

    @field_validator("title", "desc")
    @classmethod
    def _strip_text(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("文本字段不能为纯空白")
        return v

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {"example": {"level": None, "title": "example", "desc": "example"}},
    }


@router.get(
    "/config",
    summary="获取通知渠道配置状态",
    responses={
        (200): {
            "description": "通知渠道配置状态",
            "content": {
                "application/json": {
                    "example": {
                        "enabled": True,
                        "channels": {
                            "email": {"configured": True, "recipient": "admin@example.com"},
                            "webhook": {"configured": True},
                        },
                    }
                }
            },
        },
        (401): {"description": "未授权"},
        (500): {"description": "获取配置失败"},
    },
)
async def get_notify_config() -> dict[str, Any]:
    """
    返回当前通知渠道的配置状态
    仅显示各渠道是否已配置(不返回敏感的 Webhook 地址)
    ✅ 修复7:每次调用时动态读取 NOTIFY_CONFIG
    🔧 NR1 [P1]:安全访问防御
    """
    logger.info("请求通知渠道配置状态")
    try:
        cfg = _safe_get_notify_config()
        return {
            "enabled": cfg.get("enabled", False),
            "min_level": cfg.get("min_level", "critical"),
            "wecom_configured": bool(cfg.get("wecom_webhook", "")),
            "dingtalk_configured": bool(cfg.get("dingtalk_webhook", "")),
            "feishu_configured": bool(cfg.get("feishu_webhook", "")),
            "email_configured": bool(cfg.get("email_webhook", "")),
        }
    except Exception as e:
        logger.error(f"获取通知配置失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取通知配置失败,请查看服务日志")


@router.post(
    "/test",
    summary="发送测试通知",
    responses={
        (200): {
            "description": "测试通知发送成功",
            "content": {
                "application/json": {
                    "example": {
                        "status": "ok",
                        "results": {"wecom": True, "dingtalk": True, "feishu": True},
                    }
                }
            },
        },
        (401): {"description": "未授权"},
        (422): {"description": "参数校验失败"},
        (500): {"description": "通知发送失败"},
    },
)
async def send_test_notify(req: NotifyTestRequest, request: Request) -> dict[str, Any]:
    """
    向所有已配置的渠道发送一条测试通知
    用于验证 Webhook 配置是否正确

    🔧 NR4 [P2]:记录操作人 IP
    """
    operator_ip = request.client.host if request.client else "unknown"
    logger.info(f"发送测试通知 | operator={operator_ip} | level={req.level} title={req.title}")
    cfg = _safe_get_notify_config()
    if not cfg.get("enabled"):
        return {
            "status": "skipped",
            "message": (
                "通知引擎未启用,请在 .env 中设置 NOTIFY_ENABLED=true,然后调用 POST"
                " /api/notify/reload 热重载配置"
            ),
        }
    test_alert: dict[str, Any] = {
        "level": req.level,
        "title": req.title,
        "desc": req.desc,
        "raw_time": datetime.datetime.now().strftime("%H:%M:%S"),
    }
    try:
        result = await send_alert_notification(test_alert)
        logger.info(f"测试通知发送完成 | operator={operator_ip} | result={result}")
        return {"status": "ok", "results": result}
    except Exception as e:
        logger.error(f"测试通知发送失败 | operator={operator_ip} | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"通知发送失败: {str(e)[:200]}")


@router.post(
    "/send",
    summary="手动推送告警通知",
    responses={
        (200): {
            "description": "告警推送成功",
            "content": {
                "application/json": {
                    "example": {
                        "status": "ok",
                        "results": {"wecom": True, "dingtalk": True, "feishu": True},
                    }
                }
            },
        },
        (401): {"description": "未授权"},
        (422): {"description": "参数校验失败(缺少必填字段或level不合法)"},
        (500): {"description": "通知推送失败"},
    },
)
async def send_manual_notify(
    request: Request,
    alert: dict[str, Any] = Body(
        ...,
        description="告警内容字典(必须含 level/title/desc 字段)",
        examples=[
            {
                "summary": "CPU 告警推送示例",
                "value": {
                    "level": "critical",
                    "title": "CPU 使用率异常飙升",
                    "desc": "当前主机 CPU 98.7%",
                    "raw_time": "10:30:00",
                },
            }
        ],
    ),
) -> dict[str, Any]:
    """
    手动推送一条告警通知到所有已配置渠道

    字段说明:
      level:    告警级别(info / warning / critical)
      title:    告警标题(必填)
      desc:     告警详情描述(必填)
      raw_time: 告警时间(可选,缺失时自动补充当前时间)

    🔧 NR2 [P1]:增加最小字段校验,防御 notify_engine 内部空指针
    🔧 NR4 [P2]:记录操作人 IP
    """
    operator_ip = request.client.host if request.client else "unknown"
    if not isinstance(alert, dict):
        raise HTTPException(
            status_code=422, detail=f"alert 必须是 dict,收到 {type(alert).__name__}"
        )
    missing = [
        f for f in _REQUIRED_ALERT_FIELDS if not alert.get(f) or not str(alert.get(f)).strip()
    ]
    if missing:
        raise HTTPException(status_code=422, detail=f"alert 缺少必填字段: {missing}(均不能为空)")
    level = str(alert.get("level", "")).lower()
    if level not in ("info", "warning", "critical"):
        raise HTTPException(
            status_code=422,
            detail=f"alert.level 必须是 info/warning/critical,收到: {alert.get('level')!r}",
        )
    logger.warning(
        f"手动推送告警通知 | operator={operator_ip} | title='{alert.get('title', '未命名')[:50]}'"
    )
    if not alert.get("raw_time"):
        alert["raw_time"] = datetime.datetime.now().strftime("%H:%M:%S")
        logger.debug("raw_time 字段缺失,已自动补充当前时间")
    try:
        result = await send_alert_notification(alert)
        return {"status": "ok", "results": result}
    except Exception as e:
        logger.error(f"手动通知推送失败 | operator={operator_ip} | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"通知推送失败: {str(e)[:200]}")


@router.post(
    "/reload",
    summary="热重载通知渠道配置",
    responses={
        (200): {
            "description": "配置热重载成功",
            "content": {
                "application/json": {
                    "example": {
                        "status": "ok",
                        "message": "通知配置已热重载",
                        "operator_ip": "127.0.0.1",
                        "config": {
                            "enabled": True,
                            "min_level": "critical",
                            "wecom_configured": True,
                        },
                    }
                }
            },
        },
        (401): {"description": "未授权"},
        (500): {"description": "热重载失败"},
    },
)
async def reload_config(request: Request) -> dict[str, Any]:
    """
    从环境变量重新加载通知渠道配置,无需重启服务

    使用场景:
      1. 修改 .env 中的 WECOM_WEBHOOK / FEISHU_WEBHOOK 等配置后
      2. 调用此接口立即生效,无需重启 uvicorn

    操作步骤:
      1. 编辑 .env 文件,修改/添加 Webhook 地址
      2. 调用 POST /api/notify/reload
      3. 调用 GET /api/notify/config 确认配置已更新
      4. 调用 POST /api/notify/test 验证推送是否正常

    🔧 NR7 [P2]:操作 IP 审计,便于追溯配置变更
    """
    operator_ip = request.client.host if request.client else "unknown"
    logger.warning(f"⚠️ 收到通知配置热重载请求 | operator={operator_ip}")
    try:
        new_config = reload_notify_config()
        logger.info(
            f"通知配置热重载成功 | operator={operator_ip} | enabled={new_config.get('enabled')} |"
            f" min_level={new_config.get('min_level')}"
        )
        return {
            "status": "ok",
            "message": "通知配置已热重载",
            "operator_ip": operator_ip,
            "config": {
                "enabled": new_config.get("enabled", False),
                "min_level": new_config.get("min_level", "critical"),
                "wecom_configured": bool(new_config.get("wecom_webhook", "")),
                "dingtalk_configured": bool(new_config.get("dingtalk_webhook", "")),
                "feishu_configured": bool(new_config.get("feishu_webhook", "")),
                "email_configured": bool(new_config.get("email_webhook", "")),
            },
        }
    except Exception as e:
        logger.error(f"通知配置热重载失败 | operator={operator_ip} | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"热重载失败: {str(e)[:200]}")


@router.get("/health", summary="通知模块健康检查", include_in_schema=False)
async def notify_health() -> dict[str, Any]:
    """
    🔧 NR5:通知模块健康检查
    返回模块加载状态、各渠道配置情况

    供运维监控调用,无需权限保护(仅返回状态信息)
    """
    try:
        cfg = _safe_get_notify_config()
        has_close_func = hasattr(_notify_engine, "close_http_client")
        return {
            "module_loaded": True,
            "close_func": has_close_func,
            "enabled": cfg.get("enabled", False),
            "channels": {
                "wecom": bool(cfg.get("wecom_webhook")),
                "dingtalk": bool(cfg.get("dingtalk_webhook")),
                "feishu": bool(cfg.get("feishu_webhook")),
                "email": bool(cfg.get("email_webhook")),
                "phone": bool(cfg.get("phone_provider")),
                "sms": bool(cfg.get("sms_provider")),
            },
            "configured_count": sum(
                [
                    bool(cfg.get("wecom_webhook")),
                    bool(cfg.get("dingtalk_webhook")),
                    bool(cfg.get("feishu_webhook")),
                    bool(cfg.get("email_webhook")),
                    bool(cfg.get("phone_provider")),
                    bool(cfg.get("sms_provider")),
                ]
            ),
        }
    except Exception as e:
        return {"module_loaded": False, "error": str(e)[:200]}


@router.get("/status", summary="查询通知发送/送达/已读状态")
async def get_notification_status(
    alert_id: str = "",
    fingerprint: str = "",
    channel: str = "",
    limit: int = 100,
) -> dict[str, Any]:
    """查询通知历史状态，支持按 alert_id/fingerprint/channel 过滤"""
    try:
        records = _notify_engine.get_notification_status(
            alert_id=alert_id or None,
            fingerprint=fingerprint or None,
            channel=channel or None,
            limit=limit,
        )
        return {"status": "ok", "count": len(records), "records": records}
    except Exception as e:
        logger.error(f"查询通知状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e)[:200])


@router.post("/read", summary="标记通知为已读")
async def mark_notification_read(payload: dict[str, Any]) -> dict[str, Any]:
    """标记指定 message_id 在某渠道上的通知为已读"""
    message_id = payload.get("message_id", "")
    channel = payload.get("channel", "")
    if not message_id or not channel:
        raise HTTPException(status_code=422, detail="message_id and channel are required")
    updated = _notify_engine.mark_notification_read(message_id, channel)
    return {"status": "ok" if updated else "not_found", "updated": updated}


@router.get("/oncall", summary="查询当前 oncall 值班人")
async def get_oncall(
    category: str = "",
    service: str = "",
    team: str = "",
) -> dict[str, Any]:
    """根据 category/service/team 查询 oncall 排班"""
    try:
        adapter = get_oncall_adapter()
        contacts = await adapter.lookup_async(
            category=category,
            service=service,
            team=team,
        )
        return {
            "status": "ok",
            "count": len(contacts),
            "contacts": [c.__dict__ for c in contacts],
        }
    except Exception as e:
        logger.error(f"查询 oncall 失败: {e}")
        raise HTTPException(status_code=500, detail=str(e)[:200])
