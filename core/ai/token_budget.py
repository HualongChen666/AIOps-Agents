# -*- coding: utf-8 -*-
"""Token budget and context-window helpers.

Provides token-count estimation that is aware of CJK characters and, when
``tiktoken`` is installed, falls back to model-specific encodings. Also exposes
small helpers to decide whether a prompt fits inside a model's context window
and to compute the available token budget for a prompt.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, Optional, Tuple

try:
    import tiktoken

    TIKTOKEN_AVAILABLE = True
except Exception as e:
    logging.exception("Unexpected exception: %s", e)
    TIKTOKEN_AVAILABLE = False

# CJK ranges: Han, Hiragana, Katakana, Hangul
_CJK_RE = re.compile(
    r"[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]",
)


class ContextWindowExceededError(Exception):
    """Raised when a prompt does not fit into the selected model's context window."""

    def __init__(
        self, message: str, prompt_tokens: int, max_new_tokens: int, context_window: int
    ) -> None:
        super().__init__(message)
        self.prompt_tokens = prompt_tokens
        self.max_new_tokens = max_new_tokens
        self.context_window = context_window


def estimate_tokens(text: str, model: Optional[str] = None) -> int:
    """Estimate the number of tokens in ``text``.

    If ``tiktoken`` is available and ``model`` is provided, the model-specific
    encoding is used. Otherwise ``cl100k_base`` is attempted, and if that also
    fails a language-aware heuristic is used.
    """
    if not text:
        return 0

    if TIKTOKEN_AVAILABLE:
        try:
            if model:
                try:
                    enc = tiktoken.encoding_for_model(model)
                except Exception as e:
                    logging.exception("Unexpected exception: %s", e)
                    enc = tiktoken.get_encoding("cl100k_base")
            else:
                enc = tiktoken.get_encoding("cl100k_base")
            return len(enc.encode(text))
        except Exception as exc:  # pragma: no cover
            # Degrade gracefully to heuristic.
            logging.warning(f"Token count failed: {exc}")

    return _heuristic_token_count(text)


def _heuristic_token_count(text: str) -> int:
    """Language-aware token heuristic.

    CJK characters are estimated at ~2 characters per token; other characters
    are estimated at ~4 characters per token. This is intentionally more
    conservative for Chinese prompts than the previous ``len(text) // 4``.
    """
    cjk_chars = len(_CJK_RE.findall(text))
    other_chars = len(text) - cjk_chars
    # Avoid returning 0 for very short strings.
    return max(1, int(cjk_chars / 2.0 + other_chars / 4.0))


def prompt_fits(
    prompt: str,
    max_new_tokens: int,
    context_window: int,
    model: Optional[str] = None,
    reserve_tokens: int = 0,
) -> Tuple[bool, int, int]:
    """Return whether ``prompt`` + ``max_new_tokens`` fits in ``context_window``.

    Returns
    -------
    Tuple[bool, int, int]
        (fits, prompt_tokens, total_tokens)
    """
    prompt_tokens = estimate_tokens(prompt, model)
    total_tokens = prompt_tokens + max_new_tokens + reserve_tokens
    return total_tokens <= context_window, prompt_tokens, total_tokens


def calculate_prompt_budget(
    context_window: int,
    max_new_tokens: int,
    system_tokens: int = 0,
    reserve_tokens: int = 50,
) -> int:
    """Calculate how many prompt tokens we can afford.

    Keeps room for ``max_new_tokens``, an optional ``system_tokens`` block, and a
    small reserve for tokenizer noise / special tokens.
    """
    budget = context_window - max_new_tokens - system_tokens - reserve_tokens
    return max(0, budget)


def select_model_that_fits(
    prompt: str,
    max_new_tokens: int,
    model_configs: list[Dict[str, Any]],
    preferred_model: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Select the cheapest model whose ``context_window`` can hold the prompt.

    Models are sorted by ``cost_per_1k`` ascending. If ``preferred_model`` is
    supplied and fits, it is returned immediately.
    """
    if preferred_model:
        for cfg in model_configs:
            if cfg.get("name") == preferred_model or cfg.get("model") == preferred_model:
                window = cfg.get("context_window", cfg.get("max_tokens", 0))
                if prompt_fits(prompt, max_new_tokens, window, cfg.get("model"))[0]:
                    return cfg

    candidates = sorted(model_configs, key=lambda c: c.get("cost_per_1k", 0.0))
    for cfg in candidates:
        window = cfg.get("context_window", cfg.get("max_tokens", 0))
        if not window:
            continue
        if prompt_fits(prompt, max_new_tokens, window, cfg.get("model"))[0]:
            return cfg

    return None
