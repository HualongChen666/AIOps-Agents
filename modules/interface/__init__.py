# -*- coding: utf-8 -*-
"""Interface layer package

Exports FastAPI routers and public APIs. Optional routers that depend on
external libraries or have known syntax issues are imported lazily with
fallback warnings, ensuring the whole project can be imported without
raising ImportError.
"""

import logging

logger = logging.getLogger(__name__)


def _safe_import(module_path: str, name: str = None):
    """Import a router safely.
    Returns the router object if import succeeds, otherwise logs a warning
    and returns ``None``.
    """
    try:
        module = __import__(module_path, fromlist=["router"])
        return getattr(module, "router") if name is None else getattr(module, name)
    except Exception as e:
        logger.warning(f"Failed to import {module_path}: {e}")
        return None


# Core routers (these are known to be import‑safe)
autoheal_router = _safe_import("api.autoheal_router")
cloud_router = _safe_import("api.cloud_router")
root_cause_router = _safe_import("api.root_cause_router")
capacity_router = _safe_import("api.capacity_router")
sla_router = _safe_import("api.sla_router")
cost_router = _safe_import("api.cost_router")
plugin_router = _safe_import("api.plugin_router")
trace_router = _safe_import("api.trace_router")
i18n_router = _safe_import("api.i18n_router")
health_router = _safe_import("api.health_router")
windows_repair_router = _safe_import("api.windows_repair_router")
# Additional routers that may have optional deps – guarded as well
teams_router = _safe_import("api.teams_router")
metrics_router = _safe_import("api.metrics_router")
alert_router = _safe_import("api.alert_router")
# Export only the successfully imported routers
__all__ = [name for name, obj in globals().items() if name.endswith("_router") and obj is not None]
