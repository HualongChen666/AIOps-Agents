# -*- coding: utf-8 -*-
"""Real unit tests for the token budget helpers."""

from core.ai.token_budget import (
    calculate_prompt_budget,
    estimate_tokens,
    prompt_fits,
    select_model_that_fits,
)


def test_estimate_tokens_empty():
    assert estimate_tokens("") == 0


def test_estimate_tokens_ascii():
    """ASCII text should produce a positive token estimate."""
    count = estimate_tokens("hello world")
    assert count >= 1


def test_estimate_tokens_cjk():
    """CJK characters are counted with a different heuristic weight."""
    ascii_count = estimate_tokens("hello")
    cjk_count = estimate_tokens("你好")
    assert cjk_count > 1
    assert cjk_count != ascii_count


def test_prompt_fits():
    fits, prompt_tokens, total = prompt_fits("short", max_new_tokens=1, context_window=100)
    assert fits is True
    assert prompt_tokens >= 1
    assert total > prompt_tokens


def test_prompt_does_not_fit():
    fits, _, _ = prompt_fits("x" * 1000, max_new_tokens=10, context_window=20)
    assert fits is False


def test_calculate_prompt_budget():
    assert calculate_prompt_budget(100, 10, system_tokens=5) == 35
    assert calculate_prompt_budget(10, 20) == 0


def test_select_model_that_fits():
    configs = [
        {"name": "small", "context_window": 100, "cost_per_1k": 1.0},
        {"name": "large", "context_window": 1000, "cost_per_1k": 2.0},
    ]
    chosen = select_model_that_fits("x" * 2000, 10, configs)
    assert chosen["name"] == "large"
    chosen = select_model_that_fits("hi", 10, configs, preferred_model="large")
    assert chosen["name"] == "large"
    chosen = select_model_that_fits("x" * 10000, 10, configs)
    assert chosen is None
