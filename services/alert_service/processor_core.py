# -*- coding: utf-8 -*-
"""Core alert processing pipeline used by the processor service."""

from __future__ import annotations

import asyncio
import json
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

from services.alert_service.aggregator import TimeWindowAggregator
from services.alert_service.classifier import Classifier
from services.alert_service.dedup import Deduplicator
from services.alert_service.escalator import Escalator
from services.alert_service.flapping_detector import FlappingDetector
from services.alert_service.mq import InMemoryMessageQueue
from services.alert_service.noise_suppressor import NoiseSuppressor
from services.alert_service.pattern_engine import PatternEngine
from services.alert_service.repository import AlertRepository
from services.alert_service.router import Router
from services.alert_service.saga import SagaContext, SagaOrchestrator, SagaStep
from services.alert_service.schemas import Alert, AlertSeverity, AlertStatus

# Dead-letter persistence for alerts that cannot be routed/published.
_DEAD_LETTER_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
_DEAD_LETTER_PATH = os.path.join(_DEAD_LETTER_DIR, "alert_dead_letter.jsonl")


def _ensure_dead_letter_dir() -> None:
    os.makedirs(_DEAD_LETTER_DIR, exist_ok=True)


def _append_dead_letter(payload: Dict[str, Any]) -> None:
    """Append a failed alert to a local JSONL file for later replay."""
    try:
        _ensure_dead_letter_dir()
        with open(_DEAD_LETTER_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")
    except Exception as e:
        logger.error(f"Failed to write dead letter: {e}")


class AlertPipeline:
    """End-to-end pipeline from raw alerts to routed notifications."""

    def __init__(
        self,
        repository: AlertRepository,
        mq: InMemoryMessageQueue,
        window_seconds: int = 300,
        max_concurrent: int = 20,
        max_retries: int = 3,
    ) -> None:
        self.repository = repository
        self.mq = mq
        self.window_seconds = window_seconds
        self.max_retries = max(1, max_retries)
        self.classifier = Classifier()
        self.noise_suppressor = NoiseSuppressor()
        self.deduplicator = Deduplicator(window_seconds=window_seconds)
        # Root-cause aggregation across hosts.
        self.aggregator = TimeWindowAggregator(
            window_seconds=window_seconds,
            mode="tumbling",
            signature_fields=("category", "alert_type", "metric"),
        )
        self.router = Router()
        self.escalator = Escalator()
        self.pattern_engine = PatternEngine()
        self.flapping_detector = FlappingDetector(window_seconds=window_seconds * 2)
        self.saga = SagaOrchestrator()
        self._aggregator_lock = asyncio.Lock()
        self._resolved_lock = asyncio.Lock()
        self._max_concurrent = max_concurrent
        self._concurrency_semaphore = asyncio.Semaphore(max_concurrent)
        self._resolved_fingerprints: Dict[str, float] = {}
        self._active_workers = 0
        self._running = False
        self._start_time = time.time()

    async def run(self) -> None:
        """Consume raw alerts from the message queue and process them."""
        self._running = True
        logger.info("Alert processor started")
        while self._running:
            try:
                payload = await asyncio.wait_for(self.mq.consume("alerts.raw"), timeout=1.0)
                alert = self._preprocess_payload(payload)
                if alert is None:
                    continue

                if alert.status == AlertStatus.RESOLVED:
                    await self._handle_resolved(alert)
                    continue

                await self._concurrency_semaphore.acquire()
                self._active_workers += 1
                asyncio.create_task(self._worker(alert))
            except asyncio.TimeoutError:
                await self._flush_aggregator()
            except asyncio.CancelledError:
                self._running = False
                break
            except Exception as e:
                logger.error(f"Processor loop error: {e}", exc_info=True)

        await self._drain()
        logger.info("Alert processor stopped")

    async def _worker(self, alert: Alert) -> None:
        """Run one alert through the pipeline and release the concurrency slot."""
        try:
            await self._process_alert_internal(alert)
        except asyncio.CancelledError:
            logger.debug(f"Alert processing cancelled: {alert.id}")
            raise
        except Exception as e:
            logger.error(f"Alert processing failed: {e}", exc_info=True)
        finally:
            self._active_workers -= 1
            self._concurrency_semaphore.release()

    async def _drain(self) -> None:
        """Wait for all in-flight workers to finish on shutdown."""
        while self._active_workers > 0:
            await asyncio.sleep(0.05)

    def _preprocess_payload(self, payload: Dict[str, Any]) -> Optional[Alert]:
        """Parse and enrich a raw queue payload, returning None for invalid entries."""
        if payload.get("type") != "alert":
            return None
        raw = payload.get("alert")
        if not raw:
            return None
        try:
            alert = Alert(**raw)
        except Exception as e:
            logger.warning(f"Invalid alert payload: {e}")
            return None

        # Ensure a stable fingerprint before flapping/dedup stages.
        self.deduplicator.fingerprint(alert)

        if alert.status != AlertStatus.RESOLVED:
            is_flapping = self.flapping_detector.update(alert.fingerprint, alert.status.value)
            if is_flapping:
                alert.tags["is_flapping"] = True
                alert.priority = "P0"
                logger.warning(f"Alert marked as flapping/P0: {alert.id}")

        return alert

    async def _handle_resolved(self, alert: Alert) -> None:
        """Handle a resolved notification: pair it with active firing alerts."""
        fingerprint = alert.fingerprint or self.deduplicator.fingerprint(alert)

        is_flapping = self.flapping_detector.update(fingerprint, "resolved")
        ttl = float(self.window_seconds) if is_flapping else 30.0
        async with self._resolved_lock:
            self._resolved_fingerprints[fingerprint] = time.time() + ttl

        # Publish a resolved notification for downstream consumers.
        await self.mq.publish(
            "alerts.routed",
            {
                "type": "resolved_alert",
                "alert": alert.model_dump(),
                "route": "resolved",
            },
        )
        logger.info(f"Resolved alert paired and published: {alert.id} ({fingerprint})")

    async def _is_resolved(self, fingerprint: str) -> bool:
        """Check whether this fingerprint has been resolved recently."""
        async with self._resolved_lock:
            expire_at = self._resolved_fingerprints.get(fingerprint)
            if expire_at is None:
                return False
            if time.time() > expire_at:
                self._resolved_fingerprints.pop(fingerprint, None)
                return False
            return True

    async def process_alert(self, alert: Alert) -> Dict[str, Any]:
        """Public API: process a single alert through the full pipeline."""
        async with self._concurrency_semaphore:
            return await self._process_alert_internal(alert)

    async def _process_alert_internal(self, alert: Alert) -> Dict[str, Any]:
        """Process a single alert through the full pipeline (concurrency protected)."""
        # Classify
        self.classifier.classify(alert)

        if alert.tags.get("is_flapping"):
            alert.priority = "P0"

        # Noise suppression (only for firing alerts)
        if alert.status != AlertStatus.RESOLVED and self.noise_suppressor.is_noise(alert):
            alert.status = AlertStatus.SUPPRESSED
            await self.repository.save(alert)
            return {"status": "suppressed", "alert_id": alert.id}

        # Deduplication
        if self.deduplicator.is_duplicate(alert):
            return {"status": "duplicate", "alert_id": alert.id}

        # Aggregation
        async with self._aggregator_lock:
            emitted = self.aggregator.add(alert)
        results: List[Dict[str, Any]] = []
        for item in emitted:
            results.append(await self._route_and_publish(item))
        return {"status": "buffered", "alert_id": alert.id, "results": results}

    async def _route_and_publish(self, alert: Alert) -> Dict[str, Any]:
        """Route, enrich and persist/publish a single emitted alert."""
        if await self._is_resolved(alert.fingerprint or ""):
            logger.info(f"Skipping publish for already-resolved alert: {alert.id}")
            return {"status": "resolved", "alert_id": alert.id}

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
        result = await self._saga_save_and_publish(alert)
        # Auto-heal is invoked only on the deduplicated/aggregated critical path
        asyncio.create_task(self._maybe_auto_heal(alert))
        return result

    async def _maybe_auto_heal(self, alert: Alert) -> None:
        """Invoke core auto-heal only for CRITICAL/P0 alerts after dedup/aggregation."""
        if alert.level != AlertSeverity.CRITICAL or alert.priority != "P0":
            return

        try:
            from core.auto_heal import try_auto_heal  # type: ignore[import-not-found]
        except Exception as import_err:
            logger.warning(f"auto-heal module not available: {import_err}")
            return

        try:
            result = await try_auto_heal(alert.model_dump())
            logger.info(f"auto-heal triggered for {alert.id}: {result.get('status')}")
        except Exception as e:
            logger.error(f"auto-heal failed for {alert.id}: {e}")

    async def _saga_save_and_publish(self, alert: Alert) -> Dict[str, Any]:
        ctx = SagaContext(data={"alert": alert, "alert_id": alert.id})

        async def save_action(ctx: SagaContext) -> Any:
            last_err: Optional[Exception] = None
            for attempt in range(self.max_retries):
                try:
                    alert_id = await self.repository.save(ctx.data["alert"])
                    ctx.data["saved"] = True
                    return alert_id
                except Exception as e:
                    last_err = e
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(0.2 * (2**attempt))
            raise last_err or Exception("save failed")

        async def publish_action(ctx: SagaContext) -> Any:
            if await self._is_resolved(ctx.data["alert"].fingerprint or ""):
                ctx.data["resolved"] = True
                return "resolved_skipped"

            payload = {
                "type": "routed_alert",
                "alert": ctx.data["alert"].model_dump(),
                "route": ctx.data["alert"].routed_to,
            }
            last_err: Optional[Exception] = None
            for attempt in range(self.max_retries):
                try:
                    await self.mq.publish("alerts.routed", payload)
                    ctx.data["published"] = True
                    return True
                except Exception as e:
                    last_err = e
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(0.2 * (2**attempt))
            raise last_err or Exception("publish failed")

        async def publish_compensation(ctx: SagaContext) -> Any:
            payload = {
                "type": "publish_failed",
                "alert_id": ctx.data["alert_id"],
                "route": ctx.data["alert"].routed_to,
                "timestamp": datetime.utcnow().isoformat(),
            }
            _append_dead_letter(payload)
            try:
                await self.mq.publish("alerts.failed", payload)
            except Exception as e:
                logger.error(f"Failed to publish dead-letter event: {e}")
            ctx.data["published"] = False

        steps = [
            SagaStep(name="save", action=save_action),
            SagaStep(name="publish", action=publish_action, compensation=publish_compensation),
        ]

        try:
            result = await self.saga.execute(steps, ctx)
        except Exception as e:
            logger.error(f"Saga failed for alert {alert.id}: {e}")
            _append_dead_letter(
                {
                    "type": "saga_failed",
                    "alert_id": alert.id,
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )
            raise

        result["alert_id"] = alert.id
        result["route"] = alert.routed_to
        return result

    async def flush(self, force: bool = False) -> List[Dict[str, Any]]:
        """Flush the aggregator and route/publish emitted alerts."""
        async with self._concurrency_semaphore:
            return await self._flush_internal(force)

    async def _flush_internal(self, force: bool = False) -> List[Dict[str, Any]]:
        """Flush aggregator without acquiring the concurrency semaphore."""
        async with self._aggregator_lock:
            emitted = self.aggregator.flush(force=force)
        results: List[Dict[str, Any]] = []
        for item in emitted:
            results.append(await self._route_and_publish(item))
        return results

    async def process_and_flush(self, alert: Alert) -> Dict[str, Any]:
        """Process an alert and immediately flush buffered windows."""
        async with self._concurrency_semaphore:
            result = await self._process_alert_internal(alert)
            result["flushed"] = await self._flush_internal(force=True)
            return result

    async def _flush_aggregator(self) -> None:
        await self._flush_internal(force=False)

    async def stop(self) -> None:
        self._running = False

    def uptime_seconds(self) -> int:
        return int(time.time() - self._start_time)

    def get_stats(self) -> Dict[str, Any]:
        """Return pipeline statistics including queue backlogs."""
        return {
            "dedup": self.deduplicator.get_stats(),
            "noise": self.noise_suppressor.get_stats(),
            "patterns": len(self.pattern_engine.get_patterns()),
            "flapping": self.flapping_detector.get_stats(),
            "resolved_pending": len(self._resolved_fingerprints),
            "queue_sizes": {
                "alerts.raw": self.mq.qsize("alerts.raw"),
                "alerts.routed": self.mq.qsize("alerts.routed"),
                "alerts.failed": self.mq.qsize("alerts.failed"),
            },
            "rules": {
                "classification": len(self.classifier.list_rules()),
                "routing": len(self.router.list_rules()),
                "escalation": len(self.escalator.list_rules()),
                "suppression": len(self.noise_suppressor.list_rules()),
            },
        }
