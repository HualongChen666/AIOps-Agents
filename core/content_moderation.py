# -*- coding: utf-8 -*-
"""
Content Moderation Module
内容安全审查模块

Provides a lightweight content safety check for AI inputs/outputs.
This is a minimal local implementation that does not require external APIs.
"""

from typing import List, Tuple, Union

# Simple local keyword blocklist for harmful/off-limited content
_BLOCKLIST = {
    "kill", "rm -rf /", "format disk", "delete system", "destroy",
    "drop database", "wipe all", "suicide", "self-harm", "credit card",
    "password", "secret key", "api key", "private key",
}


def moderate_content(
    text: Union[str, List[str], Tuple[str, ...]],
    *,
    threshold: int = 1,
) -> Tuple[bool, List[str]]:
    """
    Check whether the provided content is allowed.

    Args:
        text: Input text or list of texts to check.
        threshold: Number of blocklist hits before rejecting (default 1).

    Returns:
        A tuple (allowed, reasons). ``allowed`` is True when no violation is
        detected; ``reasons`` is a list of human-readable violation messages.
    """
    if isinstance(text, (list, tuple)):
        texts = list(text)
    else:
        texts = [text]

    violations: List[str] = []
    for content in texts:
        if not isinstance(content, str):
            content = str(content)
        lower = content.lower()
        for keyword in _BLOCKLIST:
            if keyword in lower:
                violations.append(f"Content contains prohibited keyword: {keyword}")
    if len(violations) >= threshold:
        return False, violations
    return True, []


async def moderate_content_async(
    text: Union[str, List[str], Tuple[str, ...]],
    *,
    threshold: int = 1,
) -> Tuple[bool, List[str]]:
    """Async-compatible wrapper around ``moderate_content``."""
    return moderate_content(text, threshold=threshold)
