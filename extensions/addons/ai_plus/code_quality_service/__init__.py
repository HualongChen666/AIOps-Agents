"""
Code Quality Service
A microservice for comprehensive code quality analysis.
"""

__version__ = '1.0.0'
__author__ = 'AI Plus Team'

from .code_analyzer import CodeAnalyzer, Issue, CheckResult
from .quality_checker import QualityChecker, QualityReport, QualityLevel
from .metrics_collector import MetricsCollector, FileMetrics, ProjectMetrics

__all__ = [
    'CodeAnalyzer',
    'Issue',
    'CheckResult',
    'QualityChecker',
    'QualityReport',
    'QualityLevel',
    'MetricsCollector',
    'FileMetrics',
    'ProjectMetrics',
]
