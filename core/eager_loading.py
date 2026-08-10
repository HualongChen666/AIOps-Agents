# -*- coding: utf-8 -*-
"""
Eager Loading Configuration
Eager Loading配置
"""

from typing import Any, Dict

# Eager loading configurations for common queries.
# The legacy string-based loader options are not valid in SQLAlchemy 2.0.
# Real loader options must be bound to ORM classes at runtime; this dict
# is intentionally empty until callers populate it with model-bound options.
EAGER_LOAD_CONFIGS: Dict[str, Any] = {}
