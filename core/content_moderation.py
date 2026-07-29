# -*- coding: utf-8 -*-
"""
Content Moderation Module
内容安全审查模块

Provides a lightweight content safety check for AI inputs/outputs.
This is a minimal local implementation that does not require external APIs.
"""

import re
from typing import List, Tuple, Union

# Simple local keyword blocklist for harmful/off-limited content and prompt injection.
_HARMFUL_BLOCKLIST = {
    "rm -rf /",
    "format disk",
    "delete system",
    "destroy",
    "drop database",
    "wipe all",
    "suicide",
    "self-harm",
    "credit card",
    "password",
    "secret key",
    "api key",
    "private key",
}

_PROMPT_INJECTION_BLOCKLIST = {
    # English
    "ignore previous",
    "ignore all previous",
    "disregard",
    "override instructions",
    "new instructions",
    "ignore the above",
    "you are now",
    "roleplay",
    "do anything now",
    "system override",
    "prompt injection",
    # Chinese
    "忽略之前",
    "忽略以上",
    "忘掉之前",
    "新的指令",
    "覆盖指令",
    "假装你是",
    "现在你是",
    "不要遵守",
}

_SHELL_LIKE_PATTERNS = {
    "rm -rf",
    "killall",
    "shutdown",
    "reboot",
    "halt",
    "poweroff",
    "format c:",
    "del /f",
    "rd /s",
    "kubectl delete",
    "drop table",
    "exec(",
    "eval(",
    "__import__",
    "subprocess",
    "os.system",
}

# Prompt-injection / instruction-override indicators (case-insensitive).
_PROMPT_INJECTION_PATTERNS = [
    re.compile(
        r"\bignore\s+(all\s+)?(previous|above|prior)\s+(instructions?|prompt|context)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bdisregard\s+(all\s+)?(previous|above|prior)\s+(instructions?|prompt|context)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(you are|act as|pretend to be)\s+(now\s+)?(an?\s+)?\w+\s+with\s+no\s+restrictions\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bforget\s+(everything|all\s+previous)\b", re.IGNORECASE),
    # The literal "system:" pattern is too broad for SRE prompts (e.g.
    # "operating system:", "file system:"). Keep the blocklist phrase
    # "system override" instead.
    re.compile(r"\bnew\s+instruction\s*:", re.IGNORECASE),
    re.compile(r"\boutput\s+(only|just)\s+raw\s+(code|command|json|script)\b", re.IGNORECASE),
    # Remote code execution / data exfiltration indicators
    re.compile(
        r"\b(curl|wget|Invoke-WebRequest|iwr)\b[^\n]*"
        r"(?:\||;|&&|>)\s*"
        r"(?:bash|sh|powershell|pwsh|Invoke-Expression|iex)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\$\(.*\)", re.IGNORECASE),
    re.compile(r"`[^`]*`", re.IGNORECASE),
    re.compile(r"\b(Invoke-Expression|IEX)\b", re.IGNORECASE),
]


def moderate_content(
    text: Union[str, List[str], Tuple[str, ...]],
    *,
    threshold: int = 1,
    check_injection: bool = True,
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
        for keyword in _HARMFUL_BLOCKLIST | _PROMPT_INJECTION_BLOCKLIST | _SHELL_LIKE_PATTERNS:
            if keyword in lower:
                violations.append(f"Content contains prohibited keyword: {keyword}")

        if check_injection:
            for pattern in _PROMPT_INJECTION_PATTERNS:
                if pattern.search(content):
                    violations.append(
                        f"Potential prompt injection detected: {pattern.pattern[:80]}"
                    )
                    break

    if len(violations) >= threshold:
        return False, violations
    return True, []


def sanitize_for_llm(
    text: Union[str, List[str], Tuple[str, ...]],
    *,
    max_length: int = 2000,
    delimiter: str = "--- USER CONTENT ---",
) -> str:
    """Sanitize content for LLM consumption: truncate, strip controls, wrap."""
    if isinstance(text, (list, tuple)):
        text = "\n".join(str(t) for t in text)
    if not isinstance(text, str):
        text = str(text)
    # Strip control characters except common whitespace.
    safe = "".join(ch for ch in text if ch == "\n" or ch == "\t" or ch == "\r" or ord(ch) >= 32)
    safe = safe[:max_length]
    return f"{delimiter}\n{safe}\n{delimiter}"


async def moderate_content_async(
    text: Union[str, List[str], Tuple[str, ...]],
    *,
    threshold: int = 1,
    check_injection: bool = True,
) -> Tuple[bool, List[str]]:
    """Async-compatible wrapper around ``moderate_content``."""
    return moderate_content(text, threshold=threshold, check_injection=check_injection)
