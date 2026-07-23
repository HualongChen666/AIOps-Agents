# -*- coding: utf-8 -*-
"""
Eager Loading Configuration
Eager Loading配置
"""

from typing import Any, Dict

# Eager loading configurations for common queries.
# The legacy string-based loader options are not valid in SQLAlchemy 2.0,
# so this is kept as a safe placeholder dict. Callers can build proper
# class-bound loader options from models at runtime.
EAGER_LOAD_CONFIGS: Dict[str, Any] = {}
