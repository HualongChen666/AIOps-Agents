# -*- coding: utf-8 -*-
"""Tests for core/integration_helpers.py."""

from core.integration_helpers import (
    apply_enhanced_retry_to_function,
    enhance_ai_engine,
    enhance_notify_engine,
)


def test_apply_enhanced_retry_to_function():
    def add(a, b):
        return a + b

    wrapped = apply_enhanced_retry_to_function(add, max_attempts=2)
    assert wrapped(1, 2) == 3


def test_enhance_notify_engine():
    enhance_notify_engine()


def test_enhance_ai_engine():
    enhance_ai_engine()
