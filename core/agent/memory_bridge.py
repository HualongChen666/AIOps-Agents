# -*- coding: utf-8 -*-
"""Bridge between the autonomous executor and the scenario memory service.

Provides synchronous-ish wrappers around the async scenario memory orchestrator
so the executor can retrieve relevant experiences before planning and save an
experience after a plan completes. If the scenario memory service is unavailable
or the async runtime cannot be used, operations degrade to no-ops.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run an async coroutine synchronously when safe to do so."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # We are inside a running event loop (e.g. FastAPI). Synchronous
            # blocking is not safe, so we skip the call and rely on the async
            # caller to flush experiences explicitly.
            return None
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


class MemoryBridge:
    """Lightweight wrapper around the scenario memory orchestrator."""

    def __init__(self, orchestrator: Optional[Any] = None) -> None:
        self._orchestrator = orchestrator

    @classmethod
    def from_settings(cls) -> "MemoryBridge":
        """Create a bridge using the in-process scenario memory orchestrator."""
        try:
            from services.scenario_memory_service.cache import CacheManager
            from services.scenario_memory_service.config import settings
            from services.scenario_memory_service.orchestrator import (
                ScenarioMemoryOrchestrator,
            )

            return cls(ScenarioMemoryOrchestrator(cache=CacheManager(settings.redis_url)))
        except Exception as exc:
            logger.warning(f"Scenario memory not available for agent bridge: {exc}")
            return cls(None)

    def _ensure_orchestrator(self) -> Optional[Any]:
        if self._orchestrator is None:
            self._orchestrator = self.from_settings()._orchestrator
        return self._orchestrator

    def retrieve_relevant_experiences(
        self,
        query: str,
        top_k: int = 3,
        session_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve experiences relevant to ``query``."""
        orchestrator = self._ensure_orchestrator()
        if orchestrator is None:
            return []

        async def _retrieve() -> List[Dict[str, Any]]:
            from services.scenario_memory_service.schemas import (
                SimilarityQueryRequest,
            )

            # Search events by semantic similarity as the closest proxy for
            # "have we seen this situation before".
            response = await orchestrator.search_similar(
                SimilarityQueryRequest(query=query, top_k=top_k)
            )
            results = []
            for ev in response.results:
                payload = ev.event.payload or {}
                if (
                    session_id
                    and payload.get("session_id")
                    and payload.get("session_id") != session_id
                ):
                    continue
                results.append(
                    {
                        "event_id": ev.event_id,
                        "score": ev.score,
                        "event_type": ev.event.event_type,
                        "source": ev.event.source,
                        "payload": payload,
                    }
                )
            return results

        try:
            result = _run_async(_retrieve())
            return result or []
        except Exception as exc:
            logger.warning(f"Failed to retrieve experiences: {exc}")
            return []

    def save_experience(
        self,
        goal: str,
        tasks: List[Any],
        results: List[Any],
        summary: Dict[str, Any],
        session_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Persist the outcome of a diagnostic/repair session."""
        orchestrator = self._ensure_orchestrator()
        if orchestrator is None:
            return None

        outcome = summary.get("completed", 1) / max(1, summary.get("total", 1))
        situation = goal[:200]
        action = ", ".join(t.description for t in tasks[:5])
        confidence = float(summary.get("progress", outcome))

        async def _save() -> Dict[str, Any]:
            from services.scenario_memory_service.schemas import (
                EventMemory,
                LearnExperienceRequest,
                StoreEventRequest,
            )

            event_payload = {
                "goal": goal,
                "session_id": session_id,
                "tasks": [
                    {
                        "description": t.description,
                        "status": getattr(t.status, "value", str(t.status)),
                    }
                    for t in tasks
                ],
                "summary": summary,
            }
            await orchestrator.store_event(
                StoreEventRequest(
                    event=EventMemory(
                        event_type="diagnostic_session",
                        source="autonomous_executor",
                        payload=event_payload,
                        tags=["agent", "experience"],
                    )
                )
            )

            exp_resp = await orchestrator.learn_experience(
                LearnExperienceRequest(
                    situation=situation,
                    action=action,
                    outcome=f"completion={outcome:.2f}",
                    confidence=confidence,
                )
            )
            return {
                "experience_id": exp_resp.experience_id,
                "confidence": exp_resp.confidence,
                "learned": exp_resp.learned,
            }

        try:
            return _run_async(_save())
        except Exception as exc:
            logger.warning(f"Failed to save experience: {exc}")
            return None


def _action_signature(
    goal: str,
    task_description: str,
    tool_name: str,
    parameters: Dict[str, Any],
) -> str:
    """Create a normalized signature for a concrete action."""
    data = {
        "goal": goal.lower().strip(),
        "task": task_description.lower().strip(),
        "tool": tool_name,
        "params": _normalize_params(parameters),
    }
    return hashlib.sha256(
        json.dumps(data, ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()[:32]


def _normalize_params(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize parameters so semantically equivalent values produce the same key."""
    normalized: Dict[str, Any] = {}
    for key in sorted(parameters.keys()):
        value = parameters[key]
        if isinstance(value, (dict, list)):
            try:
                value = json.dumps(value, ensure_ascii=False, sort_keys=True)
            except Exception as e:
                logging.exception("Unexpected exception: %s", e)
                value = str(value)
        normalized[key] = value
    return normalized


__all__ = ["MemoryBridge", "_action_signature", "_normalize_params"]
