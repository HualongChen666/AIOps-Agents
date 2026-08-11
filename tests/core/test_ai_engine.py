# -*- coding: utf-8 -*-
"""Tests for core/ai_engine.py helper functions."""

from core.ai_engine import (
    _compute_prompt_token_budget,
    _redact_text,
    _redact_value,
    _rule_based_analysis,
)


def test_redact_text():
    assert _redact_text(None) == ""
    assert _redact_text("hello") == "hello"


def test_redact_value():
    assert _redact_value("hello") == "hello"
    assert _redact_value(["a", "b"]) == ["a", "b"]
    assert _redact_value({"x": 1}) == {"x": 1}


def test_compute_prompt_token_budget():
    budget = _compute_prompt_token_budget("system prompt")
    assert isinstance(budget, int)
    assert budget > 0


def test_rule_based_analysis():
    result = _rule_based_analysis("cpu high", "cpu=90", "linux")
    assert "AI 引擎暂不可用" in result
    assert "linux" in result
