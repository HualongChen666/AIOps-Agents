# -*- coding: utf-8 -*-
# api/schemas/__init__.py
"""API Schemas Package

This package contains unified Pydantic models for API requests/responses
to eliminate duplicate code patterns across routers.
"""

from .repair import (
    CloudRepairRequest,
    DockerRepairRequest,
    K8sRepairRequest,
    LinuxRepairRequest,
    UnifiedRepairRequest,
    WindowsRepairRequest,
)

__all__ = [
    "K8sRepairRequest",
    "CloudRepairRequest",
    "UnifiedRepairRequest",
    "LinuxRepairRequest",
    "WindowsRepairRequest",
    "DockerRepairRequest",
]
