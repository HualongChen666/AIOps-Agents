# -*- coding: utf-8 -*-
"""gRPC module for Compliance Monitoring Service."""

from .client import ComplianceMonitoringRPCClient
from .server import ComplianceMonitoringRPCServer

__all__ = ["ComplianceMonitoringRPCClient", "ComplianceMonitoringRPCServer"]
