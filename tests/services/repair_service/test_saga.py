# -*- coding: utf-8 -*-
"""Tests for Saga distributed transaction orchestrator."""

from __future__ import annotations

import pytest

from services.repair_service.saga import SagaOrchestrator
from services.repair_service.schemas import SagaStep


class TestSaga:
    @pytest.mark.asyncio
    async def test_saga_success(self):
        saga = SagaOrchestrator()
        steps = [
            SagaStep(step_id="s1", service="a", action="act", compensation="comp"),
            SagaStep(step_id="s2", service="b", action="act", compensation="comp"),
        ]

        async def action() -> dict:
            return {"ok": True}

        async def comp() -> dict:
            return {"ok": True}

        saga.register("s1", steps, {"act": action}, {"comp": comp})
        result = await saga.execute("s1")
        assert result["success"]

    @pytest.mark.asyncio
    async def test_saga_compensation(self):
        saga = SagaOrchestrator()
        steps = [
            SagaStep(step_id="s1", service="a", action="act", compensation="comp"),
            SagaStep(step_id="s2", service="b", action="fail", compensation="comp"),
        ]

        called = {"comp": False}

        async def action() -> dict:
            return {"ok": True}

        async def fail() -> dict:
            raise RuntimeError("boom")

        async def comp() -> dict:
            called["comp"] = True
            return {"ok": True}

        saga.register("s2", steps, {"act": action, "fail": fail}, {"comp": comp})
        result = await saga.execute("s2")
        assert not result["success"]
        assert called["comp"]
