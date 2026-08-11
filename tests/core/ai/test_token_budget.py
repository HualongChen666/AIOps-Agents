# -*- coding: utf-8 -*-
"""Tests for core/ai/token_budget.py."""

from core.ai.token_budget import (
    calculate_prompt_budget,
    estimate_tokens,
    prompt_fits,
    select_model_that_fits,
)


def test_estimate_tokens():
    assert estimate_tokens("") == 0
    assert estimate_tokens("hello world") > 0
    assert estimate_tokens("中文测试", model="unknown") > 0


def test_prompt_fits():
    fits, prompt_tokens, total = prompt_fits("hello", max_new_tokens=10, context_window=100)
    assert fits is True
    assert total > prompt_tokens

    fits2, _, _ = prompt_fits("x" * 1000, max_new_tokens=10, context_window=5)
    assert fits2 is False


def test_calculate_prompt_budget():
    assert calculate_prompt_budget(100, 10) == 40
    assert calculate_prompt_budget(10, 20) == 0


def test_select_model_that_fits():
    configs = [
        {"name": "small", "context_window": 100, "cost_per_1k": 0.1},
        {"name": "large", "context_window": 1000, "cost_per_1k": 1.0},
    ]
    selected = select_model_that_fits("hi", max_new_tokens=10, model_configs=configs)
    assert selected is not None
    assert selected["name"] == "small"

    preferred = select_model_that_fits(
        "x" * 1000, max_new_tokens=10, model_configs=configs, preferred_model="large"
    )
    assert preferred is not None
    assert preferred["name"] == "large"
