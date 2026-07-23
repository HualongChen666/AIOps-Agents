# -*- coding: utf-8 -*-
"""
SSE Router
SSE路由
"""

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/api/v1/sse", tags=["SSE"])


@router.get("/events")
async def sse_events():
    """SSE事件推送"""

    async def event_stream():
        import asyncio

        count = 0
        while True:
            yield f"data: Event {count}\n\n"
            count += 1
            await asyncio.sleep(1)

    return StreamingResponse(event_stream())
