# -*- coding: utf-8 -*-
"""
Example Plugins for AIOps Platform

This package contains example plugins demonstrating various plugin types:
- CustomMetricsCollectorPlugin: Collects metrics from external APIs
- AnomalyDetectorPlugin: Detects anomalies in time-series data
- SlackNotifierPlugin: Sends notifications to Slack
"""

from .custom_metrics_collector import CustomMetricsCollectorPlugin
from .anomaly_detector import AnomalyDetectorPlugin
from .slack_notifier import SlackNotifierPlugin

__all__ = [
    "CustomMetricsCollectorPlugin",
    "AnomalyDetectorPlugin",
    "SlackNotifierPlugin",
]