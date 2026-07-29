#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Minimal AIOps Agent Python SDK demo.

Usage:
    export AIOPS_BASE_URL=http://localhost:8000
    python sdk/python/demo.py
"""

import io
import os
import sys

import requests

# Force UTF-8 output on Windows terminals that default to cp1252.
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True
    )
    sys.stderr = io.TextIOWrapper(
        sys.stderr.buffer, encoding="utf-8", errors="replace", line_buffering=True
    )
elif hasattr(sys.stdout, "reconfigure"):
    reconfigure = getattr(sys.stdout, "reconfigure")
    reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        getattr(sys.stderr, "reconfigure")(encoding="utf-8", errors="replace")

BASE_URL = os.getenv("AIOPS_BASE_URL", "http://localhost:8000").rstrip("/")


def main() -> None:
    print(f"Connecting to AIOps Agent at {BASE_URL}")

    # Health check
    resp = requests.get(f"{BASE_URL}/health", timeout=10)
    print("Health:", resp.status_code, resp.json())

    # Submit an AI root-cause analysis request
    ai_resp = requests.post(
        f"{BASE_URL}/api/ai/analyze",
        json={
            "query": "CPU usage is high, analyze root cause",
            "platform": "windows",
            "include_metrics": True,
        },
        timeout=30,
    )
    if ai_resp.status_code == 200:
        print("AI analyze:", ai_resp.status_code, ai_resp.json())
    else:
        print("AI analyze:", ai_resp.status_code, ai_resp.text[:200])

    # List recent alerts
    alerts_resp = requests.get(f"{BASE_URL}/api/v1/alerts", params={"limit": 5}, timeout=10)
    print("Alerts:", alerts_resp.status_code, alerts_resp.json())


if __name__ == "__main__":
    main()
