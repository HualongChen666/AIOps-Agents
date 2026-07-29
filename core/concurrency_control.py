# -*- coding: utf-8 -*-
"""
Concurrency Control
并发控制
"""

import asyncio
import os

# Global agent session concurrency limit; set via AIOPS_MAX_AGENT_SESSIONS.
AGENT_SESSION_LIMIT = int(os.getenv("AIOPS_MAX_AGENT_SESSIONS", "50"))
agent_session_semaphore = asyncio.Semaphore(AGENT_SESSION_LIMIT)


class ConcurrencyController:
    """并发控制器"""

    def __init__(self, max_concurrent: int = 10):
        self.semaphore = asyncio.Semaphore(max_concurrent)

    async def run_with_limit(self, coro):
        async with self.semaphore:
            return await coro
