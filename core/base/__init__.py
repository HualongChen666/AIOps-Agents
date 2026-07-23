# -*- coding: utf-8 -*-
"""
Unified Abstract Base Classes for AIOps Platform
Provides common interfaces for collectors, analyzers, executors, and storage components
"""

from .analyzer import BaseAnalyzer
from .collector import BaseCollector
from .executor import BaseExecutor
from .storage import BaseStorage

__all__ = ["BaseCollector", "BaseAnalyzer", "BaseExecutor", "BaseStorage"]
