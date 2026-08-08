# -*- coding: utf-8 -*-
"""SSE Router - streams real alert events from the in-memory alert history."""

import asyncio
import json
from typing import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from core.alert_engine import alert_history

router = APIRouter(prefix="/api/v1/sse", tags=["SSE"])


@router.get("/events")
async def sse_events() -> StreamingResponse:
    """SSE 事件推送：基于内存告警历史实时推送新告警。"""

    async def event_stream() -> AsyncIterator[str]:
        seen = len(alert_history)
        while True:
            current = list(alert_history)
            if len(current) > seen:
                for alert in current[: len(current) - seen]:
                    payload = json.dumps(alert, ensure_ascii=False, default=str)
                    yield f"event: alert\ndata: {payload}\n\n"
                seen = len(current)
            else:
                # 心跳保活
                yield "event: heartbeat\ndata: {}\n\n"
            await asyncio.sleep(1)

    return StreamingResponse(event_stream(), media_type="text/event-stream")
