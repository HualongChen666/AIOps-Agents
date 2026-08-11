# -*- coding: utf-8 -*-
"""Tests for core/smart_cache_strategy.py."""

from core.smart_cache_strategy import SmartCacheStrategy


def test_get_ttl():
    assert SmartCacheStrategy.get_ttl("k", 101, 100) == 60
    assert SmartCacheStrategy.get_ttl("k", 11, 100) == 300
    assert SmartCacheStrategy.get_ttl("k", 1, 100) == 3600


def test_get_cache_tier():
    assert SmartCacheStrategy.get_cache_tier("any") == "cold"
