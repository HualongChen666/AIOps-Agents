# -*- coding: utf-8 -*-
# core/loki_sink.py
# component module for Loki log aggregation

from typing import Any, Dict


def push_to_loki(data: Dict[str, Any]) -> None:
    """Push data to Loki.

    Args:
        data: Data to push
    """
    import logging

    logging.getLogger(__name__).info(f"{__name__}.push_to_loki invoked")
    return None
