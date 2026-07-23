# -*- coding: utf-8 -*-
"""
Concurrency Control
并发控制
"""

import asyncio


class ConcurrencyController:
    """并发控制器"""

    def __init__(self, max_concurrent: int = 10):
        self.semaphore = asyncio.Semaphore(max_concurrent)

    async def run_with_limit(self, coro):
        async with self.semaphore:
            return await coro
