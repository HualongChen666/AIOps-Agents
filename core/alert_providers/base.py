# -*- coding: utf-8 -*-
"""Base alert provider adapter interface and registry."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type


class AlertProvider(ABC):
    """Normalize a raw monitoring payload into the internal alert dict."""

    name: str = ""

    @abstractmethod
    def normalize(self, raw_payload: Any) -> List[Dict[str, Any]]:
        """Return a list of normalized alert dictionaries."""


_REGISTRY: Dict[str, Type[AlertProvider]] = {}


def register_alert_provider(cls: Type[AlertProvider]) -> Type[AlertProvider]:
    """Decorator that registers an AlertProvider implementation by ``name``."""
    _REGISTRY[cls.name] = cls
    return cls


def get_alert_provider(name: str) -> Optional[AlertProvider]:
    """Return an instance of the named provider, or ``None`` if not registered."""
    provider_cls = _REGISTRY.get(name)
    if provider_cls is None:
        return None
    return provider_cls()


def list_alert_providers() -> List[str]:
    """Return all registered provider names."""
    return sorted(_REGISTRY.keys())
