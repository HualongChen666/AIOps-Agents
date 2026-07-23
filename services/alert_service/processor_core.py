# -*- coding: utf-8 -*-
"""Core alert processing pipeline used by the processor service."""

from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, List

from loguru import logger

from services.alert_service.aggregator import TimeWindowAggregator
from services.alert_service.classifier import Classifier
from services.alert_service.dedup import Deduplicator
from services.alert_service.escalator import Escalator
from services.alert_service.mq import InMemoryMessageQueue
from services.alert_service.noise_suppressor import NoiseSuppressor
from services.alert_service.pattern_engine import PatternEngine
from services.alert_service.repository import AlertRepository
from services.alert_service.router import Router
from services.alert_service.saga import SagaContext, SagaOrchestrator, SagaStep
from services.alert_service.schemas import Alert, AlertStatus


class AlertPipeline:
    """End-to-end pipeline from raw alerts to routed notifications."""

    def __init__(
        self,
        repository: AlertRepository,
        mq: InMemoryMessageQueue,
        window_seconds: int = 300,
    ) -> None:
        self.repository = repository
        self.mq = mq
        self.classifier = Classifier()
        self.noise_suppressor = NoiseSuppressor()
        self.deduplicator = Deduplicator(window_seconds=window_seconds)
        self.aggregator = TimeWindowAggregator(window_seconds=window_seconds, mode="sliding")
        self.router = Router()
        self.escalator = Escalator()
        self.pattern_engine = PatternEngine()
        self.saga = SagaOrchestrator()
        self._running = False
        self._start_time = time.time()

    async def run(self) -> None:
        """Consume raw alerts from the message queue and process them."""
        self._running = True
        logger.info("Alert processor started")
        while self._running:
            try:
                payload = await asyncio.wait_for(self.mq.consume("alerts.raw"), timeout=1.0)
                await self._handle_payload(payload)
            except asyncio.TimeoutError:
                await self._flush_aggregator()
            except asyncio.CancelledError:
                self._running = False
                break
            except Exception as e:
                logger.error(f"Processor loop error: {e}", exc_info=True)
        logger.info("Alert processor stopped")

    async def _handle_payload(self, payload: Dict[str, Any]) -> None:
        if payload.get("type") != "alert":
            return
        raw = payload.get("alert")
        if not raw:
            return
        alert = Alert(**raw)
        await self.process_alert(alert)

    async def process_alert(self, alert: Alert) -> Dict[str, Any]:
        """Process a single alert through the full pipeline."""
        # Classify
        self.classifier.classify(alert)

        # Noise suppression
        if self.noise_suppressor.is_noise(alert):
            alert.status = AlertStatus.SUPPRESSED
            await self.repository.save(alert)
            return {"status": "suppressed", "alert_id": alert.id}

        # Deduplication
        if self.deduplicator.is_duplicate(alert):
            return {"status": "duplicate", "alert_id": alert.id}

        # Aggregation
        emitted = self.aggregator.add(alert)
        results: List[Dict[str, Any]] = []
        for item in emitted:
            results.append(await self._route_and_publish(item))
        return {"status": "buffered", "alert_id": alert.id, "results": results}

    async def _route_and_publish(self, alert: Alert) -> Dict[str, Any]:
        # Route
        self.router.route(alert)

        # Escalation tracking
        self.escalator.track(alert)
        escalation_target = self.escalator.should_escalate(alert)
        if escalation_target:
            alert.tags["escalation_target"] = escalation_target

        # Pattern recognition
        pattern = self.pattern_engine.predict(alert)
        alert.tags["pattern"] = pattern

        # Save + publish via saga for distributed transaction safety
        return await self._saga_save_and_publish(alert)

    async def _saga_save_and_publish(self, alert: Alert) -> Dict[str, Any]:
        ctx = SagaContext(data={"alert": alert, "alert_id": alert.id})

        async def save_action(ctx: SagaContext) -> Any:
            alert_id = await self.repository.save(ctx.data["alert"])
            ctx.data["saved"] = True
            return alert_id

        async def save_compensation(ctx: SagaContext) -> Any:
            await self.repository.delete(ctx.data["alert_id"])
            ctx.data["saved"] = False

        async def publish_action(ctx: SagaContext) -> Any:
            payload = {
                "type": "routed_alert",
                "alert": ctx.data["alert"].model_dump(),
                "route": ctx.data["alert"].routed_to,
            }
            await self.mq.publish("alerts.routed", payload)
            ctx.data["published"] = True
            return True

        async def publish_compensation(ctx: SagaContext) -> Any:
            await self.mq.publish(
                "alerts.failed",
                {
                    "type": "publish_failed",
                    "alert_id": ctx.data["alert_id"],
                },
            )
            ctx.data["published"] = False

        steps = [
            SagaStep(name="save", action=save_action, compensation=save_compensation),
            SagaStep(name="publish", action=publish_action, compensation=publish_compensation),
        ]

        result = await self.saga.execute(steps, ctx)
        result["alert_id"] = alert.id
        result["route"] = alert.routed_to
        return result

    async def flush(self, force: bool = False) -> List[Dict[str, Any]]:
        """Flush the aggregator and route/publish emitted alerts."""
        emitted = self.aggregator.flush(force=force)
        results: List[Dict[str, Any]] = []
        for item in emitted:
            results.append(await self._route_and_publish(item))
        return results

    async def process_and_flush(self, alert: Alert) -> Dict[str, Any]:
        """Process an alert and immediately flush buffered windows."""
        result = await self.process_alert(alert)
        result["flushed"] = await self.flush(force=True)
        return result

    async def _flush_aggregator(self) -> None:
        await self.flush(force=False)

    async def stop(self) -> None:
        self._running = False

    def uptime_seconds(self) -> int:
        return int(time.time() - self._start_time)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "dedup": self.deduplicator.get_stats(),
            "noise": self.noise_suppressor.get_stats(),
            "patterns": len(self.pattern_engine.get_patterns()),
            "rules": {
                "classification": len(self.classifier.list_rules()),
                "routing": len(self.router.list_rules()),
                "escalation": len(self.escalator.list_rules()),
                "suppression": len(self.noise_suppressor.list_rules()),
            },
        }
