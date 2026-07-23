# -*- coding: utf-8 -*-
"""ML-based and rule-based alert pattern recognition."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from loguru import logger

from services.alert_service.schemas import Alert

try:
    from sklearn.cluster import MiniBatchKMeans
    from sklearn.feature_extraction.text import TfidfVectorizer

    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


@dataclass
class _Pattern:
    pattern_id: str
    signature: str
    count: int = 0
    examples: List[str] = None  # type: ignore[assignment]

    def __post_init__(self):
        if self.examples is None:
            self.examples = []


class PatternEngine:
    """Recognize alert patterns using rule-based signatures and optional ML clustering."""

    def __init__(self, min_samples: int = 3, n_clusters: int = 5) -> None:
        self.min_samples = min_samples
        self.n_clusters = n_clusters
        self._patterns: Dict[str, _Pattern] = {}
        self._vectorizer: Optional[TfidfVectorizer] = None
        self._model: Optional[Any] = None
        self._texts: List[str] = []
        self._trained = False

        if SKLEARN_AVAILABLE:
            self._vectorizer = TfidfVectorizer(max_features=100)

    def _signature(self, alert: Alert) -> str:
        data = {
            "level": alert.level,
            "category": alert.category,
            "alert_type": alert.alert_type,
            "host": alert.host,
            "metric": alert.metric,
        }
        payload = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]

    def _text(self, alert: Alert) -> str:
        return f"{alert.title} {alert.description}"

    def train(self, alerts: List[Alert]) -> None:
        for alert in alerts:
            sig = self._signature(alert)
            if sig not in self._patterns:
                self._patterns[sig] = _Pattern(pattern_id=sig, signature=sig)
            self._patterns[sig].count += 1
            self._patterns[sig].examples.append(self._text(alert))

        self._texts.extend(self._text(a) for a in alerts)

        if SKLEARN_AVAILABLE and len(self._texts) >= self.min_samples:
            try:
                vectors = self._vectorizer.fit_transform(self._texts)  # type: ignore[union-attr]
                clusters = min(self.n_clusters, max(1, len(self._texts) // 2))
                self._model = MiniBatchKMeans(n_clusters=clusters, random_state=42)
                self._model.fit(vectors)
                self._trained = True
                logger.info(f"Pattern engine trained on {len(self._texts)} alerts")
            except Exception as e:
                logger.warning(f"ML pattern training failed: {e}")
                self._trained = False

    def predict(self, alert: Alert) -> str:
        text = self._text(alert)
        sig = self._signature(alert)

        if self._trained and SKLEARN_AVAILABLE and self._vectorizer and self._model:
            try:
                vec = self._vectorizer.transform([text])
                cluster = self._model.predict(vec)[0]
                return f"ml-cluster-{cluster}"
            except Exception as e:
                logger.debug(f"ML prediction failed: {e}")

        if sig in self._patterns:
            return self._patterns[sig].pattern_id
        return "unknown"

    def get_patterns(self) -> Dict[str, Dict[str, Any]]:
        return {
            pid: {
                "signature": p.signature,
                "count": p.count,
                "examples": p.examples[:5],
            }
            for pid, p in self._patterns.items()
        }
