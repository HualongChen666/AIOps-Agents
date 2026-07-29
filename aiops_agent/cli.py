# -*- coding: utf-8 -*-
"""Command-line interface for the AIOps SRE Agent."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

import httpx

DEFAULT_BASE_URL = os.getenv("AIOPS_API_URL", "http://127.0.0.1:8000").rstrip("/")
INTERNAL_KEY = os.getenv("AIOPS_INTERNAL_KEY") or os.getenv("INTERNAL_API_KEY")


def _headers() -> dict[str, str]:
    h = {"Accept": "application/json"}
    if INTERNAL_KEY:
        h["X-Internal-Key"] = INTERNAL_KEY
    return h


def _print(data: Any) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False))


def _client() -> httpx.Client:
    return httpx.Client(base_url=DEFAULT_BASE_URL, timeout=30.0)


def cmd_incidents(_args: argparse.Namespace) -> None:
    with _client() as client:
        r = client.get("/api/v1/approvals/pending", headers=_headers())
        r.raise_for_status()
        _print(r.json())


def cmd_approve(args: argparse.Namespace) -> None:
    with _client() as client:
        r = client.patch(f"/api/v1/approvals/{args.alert_id}", headers=_headers())
        r.raise_for_status()
        _print(r.json())


def cmd_reject(args: argparse.Namespace) -> None:
    with _client() as client:
        r = client.post(
            "/api/v1/approvals/reject",
            json={"alert_id": args.alert_id, "reason": args.reason},
            headers=_headers(),
        )
        r.raise_for_status()
        _print(r.json())


def cmd_audit(args: argparse.Namespace) -> None:
    with _client() as client:
        r = client.get(
            "/api/v1/audit",
            params={"limit": args.limit},
            headers=_headers(),
        )
        r.raise_for_status()
        _print(r.json())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="aiops-agent",
        description="CLI for the AIOps SRE Agent.",
    )
    sub = parser.add_subparsers(dest="command", help="Commands")

    p = sub.add_parser("incidents", help="List pending approvals/incidents")
    p.set_defaults(func=cmd_incidents)

    p = sub.add_parser("approve", help="Approve an incident by alert_id")
    p.add_argument("alert_id", help="Alert ID to approve")
    p.set_defaults(func=cmd_approve)

    p = sub.add_parser("reject", help="Reject an incident by alert_id")
    p.add_argument("alert_id", help="Alert ID to reject")
    p.add_argument("--reason", default="用户驳回", help="Rejection reason")
    p.set_defaults(func=cmd_reject)

    p = sub.add_parser("audit", help="Show audit log")
    p.add_argument("--limit", type=int, default=100, help="Number of records")
    p.set_defaults(func=cmd_audit)

    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 1

    try:
        args.func(args)
    except httpx.HTTPError as exc:
        print(f"API error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
