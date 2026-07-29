# -*- coding: utf-8 -*-
"""Flapping detection for alert status transitions."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict

from loguru import logger


@dataclass
class _FlapState:
    last_status: str
    transition_count: int = 0
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)


class FlappingDetector:
    """Detect flapping alerts by counting status transitions within a window."""

    def __init__(
        self,
        window_seconds: int = 600,
        threshold: int = 3,
    ) -> None:
        self.window_seconds = window_seconds
        self.threshold = threshold
        self._states: Dict[str, _FlapState] = {}

    def update(self, fingerprint: str, status: str) -> bool:
        """Record a status transition and return whether it is flapping."""
        now = time.time()
        self._evict(now)

        state = self._states.get(fingerprint)
        if not state:
            self._states[fingerprint] = _FlapState(last_status=status)
            return False

        if state.last_status != status:
            state.transition_count += 1
            state.last_status = status

        state.last_seen = now
        is_flapping = state.transition_count >= self.threshold
        if is_flapping:
            logger.warning(
                f"Flapping detected for {fingerprint} " f"(transitions={state.transition_count})"
            )
        return is_flapping

    def is_flapping(self, fingerprint: str) -> bool:
        state = self._states.get(fingerprint)
        return bool(state and state.transition_count >= self.threshold)

    def clear(self, fingerprint: str) -> None:
        self._states.pop(fingerprint, None)

    def _evict(self, now: float) -> None:
        cutoff = now - self.window_seconds
        expired = [fp for fp, s in self._states.items() if s.last_seen < cutoff]
        for fp in expired:
            del self._states[fp]

    def get_stats(self) -> Dict[str, int]:
        return {
            "active_states": len(self._states),
            "flapping_alerts": sum(
                1 for s in self._states.values() if s.transition_count >= self.threshold
            ),
        }
