# -*- coding: utf-8 -*-
"""Configuration for Compliance Monitoring Service."""

import os


class Config:
    """Service configuration."""

    SERVICE_NAME = "compliance_monitoring_service"
    
    # HTTP Server
    HTTP_HOST = os.getenv("HTTP_HOST", "0.0.0.0")
    HTTP_PORT = int(os.getenv("PORT", "8010"))
    
    # gRPC Server
    GRPC_HOST = os.getenv("GRPC_HOST", "0.0.0.0")
    GRPC_PORT = int(os.getenv("GRPC_PORT", "50060"))
    
    # Storage paths
    ALERT_STORAGE_PATH = os.getenv("ALERT_STORAGE_PATH", "./alerts")
    TREND_STORAGE_PATH = os.getenv("TREND_STORAGE_PATH", "./trends")
    REPORT_STORAGE_PATH = os.getenv("REPORT_STORAGE_PATH", "./reports")
    
    # Monitoring configuration
    AUTO_MONITOR_ENABLED = os.getenv("AUTO_MONITOR_ENABLED", "true").lower() == "true"
    MONITOR_INTERVAL = int(os.getenv("MONITOR_INTERVAL", "3600"))  # 1 hour
    ALERT_THRESHOLD = float(os.getenv("ALERT_THRESHOLD", "0.8"))  # 80%
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
