# -*- coding: utf-8 -*-
"""Collect layer package

This package re‑exports the core collection utilities so that external
code can import from ``modules.collect`` instead of the original ``core``
module.  Keeping the re‑exports preserves backward compatibility while
providing a clear logical separation for the seven‑layer architecture.
"""

# Cloud / Kubernetes collectors. (The former ``core.event_store``,
# ``core.prometheus_collector`` and ``core.trace_monitor`` re-exports were dead
# references — those modules do not exist — and have been removed.)
from core.cloud_collector import *  # noqa: F401,F403
from core.k8s_collector import *  # noqa: F401,F403
