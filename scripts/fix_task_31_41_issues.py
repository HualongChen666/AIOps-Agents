#!/usr/bin/env python3
"""Targeted, minimal fixes to make all tasks 31-41 pass mypy and bandit."""

from __future__ import annotations

import re
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def fix_cache_pass(cache_path: Path) -> None:
    text = read(cache_path)
    # Replace bare `except Exception: ... pass` with a debug log.
    text = re.sub(
        r"(^[ \t]+)except Exception:\s*\n\1    pass\s*$",
        r'\1except Exception as exc:\n\1    logger.debug(f"Redis cache operation failed: {exc}")',
        text,
        flags=re.MULTILINE,
    )
    write(cache_path, text)


def fix_llm_router_retry() -> None:
    path = BASE / "services" / "llm_router_service" / "retry.py"
    text = read(path)
    # Add TypeVar import and typevar
    text = text.replace(
        "from typing import Any, Awaitable, Callable, List, Optional",
        "from typing import Any, Awaitable, Callable, List, Optional, TypeVar",
    )
    text = text.replace(
        "class LLMRetryEngine:\n"
        '    """Execute coroutines with configurable exponential backoff."""',
        'T = TypeVar("T")\n\n\n'
        "class LLMRetryEngine:\n"
        '    """Execute coroutines with configurable exponential backoff."""',
    )
    old_sig = (
        "    async def execute(\n"
        "        self,\n"
        "        fn: Callable[..., Awaitable[Any]],\n"
        "        *args: Any,\n"
        "        policy_name: Optional[str] = None,\n"
        "        **kwargs: Any,\n"
        "    ) -> Any:"
    )
    new_sig = (
        "    async def execute(\n"
        "        self,\n"
        "        fn: Callable[..., Awaitable[T]],\n"
        "        *args: Any,\n"
        "        policy_name: Optional[str] = None,\n"
        "        **kwargs: Any,\n"
        "    ) -> T:"
    )
    text = text.replace(old_sig, new_sig)
    # Remove `if last_error: raise last_error; return None` with generic-safe raise
    old_tail = "        if last_error:\n" "            raise last_error\n" "        return None"
    new_tail = (
        "        if last_error is None:\n"
        '            raise RuntimeError("Retry policy did not produce a result")\n'
        "        raise last_error"
    )
    text = text.replace(old_tail, new_tail)
    write(path, text)


def fix_llm_router_rpc_server() -> None:
    path = BASE / "services" / "llm_router_service" / "grpc" / "server.py"
    text = read(path)
    text = text.replace(
        "self._handlers: Dict[str, Callable[..., Awaitable[Any]]] = {}",
        "self._handlers: Dict[str, Callable[..., Any]] = {}",
    )
    text = text.replace(
        "def register(self, method: str, handler: Callable[..., Awaitable[Any]]) -> None:",
        "def register(self, method: str, handler: Callable[..., Any]) -> None:",
    )
    write(path, text)


def fix_chatopenai_mypy(*service_names: str) -> None:
    for svc in service_names:
        path = BASE / "services" / svc / "orchestrator.py"
        text = read(path)
        text = text.replace(
            "            model = ChatOpenAI(\n",
            "            model = ChatOpenArrayDisabled(  # type: ignore[call-arg]\n",
        )
        # Undo if accidentally changed; safer to use regex.
        text = text.replace("ChatOpenArrayDisabled", "ChatOpenAI")
        write(path, text)
        # Actually the above replace is a no-op after undo; use regex below.


def fix_chatopenai_mypy_v2(*service_names: str) -> None:
    for svc in service_names:
        path = BASE / "services" / svc / "orchestrator.py"
        text = read(path)
        text = re.sub(
            r"^(\s+)model = ChatOpenAI\($",
            r"\1model = ChatOpenAI(  # type: ignore[call-arg]",
            text,
            flags=re.MULTILINE,
        )
        write(path, text)


def fix_data_access_service() -> None:
    path = BASE / "services" / "data_access_service" / "service.py"
    text = read(path)
    text = text.replace("import random", "import secrets")
    text = text.replace("random.choice", "secrets.choice")
    text = text.replace(
        "hashlib.md5(key.encode())",
        "hashlib.md5(key.encode(), usedforsecurity=False)",
    )
    write(path, text)


def fix_scenario_memory_asserts() -> None:
    path = BASE / "services" / "scenario_memory_service" / "orchestrator.py"
    text = read(path)
    text = text.replace(
        "        assert existing.experience_id is not None",
        "        if existing.experience_id is None:\n"
        '            raise ValueError("experience_id must not be None")',
    )
    text = text.replace(
        "            assert entry.knowledge_id is not None",
        "            if entry.knowledge_id is None:\n"
        '                raise ValueError("knowledge_id must not be None")',
    )
    text = text.replace(
        "                assert existing_kid is not None",
        "                if existing_kid is None:\n"
        '                    raise ValueError("knowledge_id must not be None")',
    )
    write(path, text)


def main() -> None:
    cache_files = [
        "services/llm_router_service/cache.py",
        "services/rag_service/cache.py",
        "services/agent_orchestration_service/cache.py",
        "services/data_access_service/cache.py",
        "services/cache_service/cache.py",
        "services/vector_retrieval_service/cache.py",
    ]
    for rel in cache_files:
        fix_cache_pass(BASE / rel)

    fix_llm_router_retry()
    fix_llm_router_rpc_server()
    fix_chatopenai_mypy_v2("rag_service", "agent_orchestration_service")
    fix_data_access_service()
    fix_scenario_memory_asserts()

    print("Fixes applied. Run `black .` and verification scripts to confirm.")


if __name__ == "__main__":
    main()
