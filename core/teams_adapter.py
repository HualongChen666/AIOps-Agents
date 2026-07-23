# -*- coding: utf-8 -*-
"""
Microsoft Teams Integration Adapter
Teams 集成适配器

Provides a minimal incoming-webhook based client for Microsoft Teams.
Supports plain and adaptive-card style interactive messages.
"""

import asyncio
from typing import Any, Dict, List, Optional

import httpx
from loguru import logger as _logger

from config import TEAMS_WEBHOOK_URL

_HTTP_CLIENT: Optional[httpx.AsyncClient] = None
_HTTP_CLIENT_LOCK = asyncio.Lock()


async def _get_http_client() -> httpx.AsyncClient:
    global _HTTP_CLIENT
    if _HTTP_CLIENT is None or _HTTP_CLIENT.is_closed:
        _HTTP_CLIENT = httpx.AsyncClient(timeout=15.0)
    return _HTTP_CLIENT


def _is_configured() -> bool:
    return bool(TEAMS_WEBHOOK_URL)


def _build_message(text: str, title: Optional[str] = None, color: Optional[str] = None) -> Dict[str, Any]:
    message: Dict[str, Any] = {"@type": "MessageCard", "@context": "https://schema.org/extensions", "text": text}
    if title:
        message["title"] = title
    if color:
        message["themeColor"] = color
    return message


def _build_adaptive_card(
    text: str,
    title: Optional[str] = None,
    actions: Optional[List[Dict[str, Any]]] = None,
    color: Optional[str] = None,
) -> Dict[str, Any]:
    body: List[Dict[str, Any]] = []
    if title:
        body.append({"type": "TextBlock", "text": title, "weight": "bolder", "size": "medium"})
    body.append({"type": "TextBlock", "text": text, "wrap": True})

    adaptive_card: Dict[str, Any] = {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "contentUrl": None,
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.3",
                    "body": body,
                },
            }
        ],
    }

    if actions:
        ms_actions = []
        for action in actions:
            action_type = action.get("type", "Action.OpenUrl")
            if action_type == "Action.OpenUrl":
                ms_actions.append(
                    {
                        "type": "Action.OpenUrl",
                        "title": action.get("title", action.get("text", "Open")),
                        "url": action.get("url", action.get("value", "")),
                    }
                )
            else:
                ms_actions.append(
                    {
                        "type": "Action.Submit",
                        "title": action.get("title", action.get("text", "Submit")),
                        "data": {"action": action.get("action", "submit"), "value": action.get("value")},
                    }
                )
        adaptive_card["attachments"][0]["content"]["actions"] = ms_actions

    if color:
        adaptive_card.setdefault("summary", text)

    return adaptive_card


async def post_message(
    text: str,
    title: Optional[str] = None,
    channel: Optional[str] = None,
    color: Optional[str] = None,
) -> Dict[str, Any]:
    """Send a simple text/caption message to the configured Teams webhook."""
    if not _is_configured():
        raise RuntimeError("Microsoft Teams webhook is not configured")

    webhook_url = TEAMS_WEBHOOK_URL
    message = _build_message(text=text, title=title, color=color)

    client = await _get_http_client()
    response = await client.post(webhook_url, json=message)
    response.raise_for_status()

    _logger.info("Teams message posted successfully to webhook")
    return {"status": "ok", "http_status": response.status_code, "text": response.text or ""}


async def post_interactive_message(
    title: str,
    description: str,
    actions: List[Dict[str, Any]],
    channel: Optional[str] = None,
    color: Optional[str] = None,
) -> Dict[str, Any]:
    """Send an adaptive card message with action buttons to Teams."""
    if not _is_configured():
        raise RuntimeError("Microsoft Teams webhook is not configured")

    webhook_url = TEAMS_WEBHOOK_URL
    card = _build_adaptive_card(
        text=description,
        title=title,
        actions=actions,
        color=color,
    )

    client = await _get_http_client()
    response = await client.post(webhook_url, json=card)
    response.raise_for_status()

    _logger.info("Teams interactive card posted successfully to webhook")
    return {"status": "ok", "http_status": response.status_code, "text": response.text or ""}


async def close_teams_client() -> None:
    """Close the Teams HTTP client singleton."""
    global _HTTP_CLIENT
    if _HTTP_CLIENT and not _HTTP_CLIENT.is_closed:
        await _HTTP_CLIENT.aclose()
        _logger.info("Teams HTTP client closed")
