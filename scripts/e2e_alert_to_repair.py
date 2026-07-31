# -*- coding: utf-8 -*-
import logging

"""End-to-end test: Prometheus alert -> approval -> repair -> audit."""
import json
import os
import sys

# Make the repository root importable from scripts/
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

# Avoid cp1252 UnicodeEncodeError when printing API responses with Chinese text.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Must set these before importing main/config so the in-process app uses a
# local SQLite DB and does not require an AI API key.
os.environ["POSTGRES_URL"] = "sqlite+aiosqlite:///e2e.db"
os.environ["INTERNAL_API_KEY"] = "e2e-test-key"
os.environ["HEAL_EXECUTE_ENABLED"] = "false"  # simulate repairs
os.environ["HARDWARE_EXECUTE_ENABLED"] = "false"  # simulate hardware repairs
# config.py now loads ai_api.env (AI_ENABLED=true / AI_TIMEOUT=5) so AI path is attempted.
# main.py lifespan uses _safe_init timeouts, no need for DISABLE_OPTIONAL_LAYERS.

from fastapi.testclient import TestClient
from sqlalchemy import create_engine

import core.models  # noqa: F401
from core.authentication import get_current_active_user
from core.database import Base
from main import app

app.dependency_overrides[get_current_active_user] = lambda: {"username": "e2e", "role": "admin"}

# Create the same SQLite file that the async engine will use.
engine = create_engine("sqlite:///e2e.db")
Base.metadata.create_all(engine)


def run():
    with TestClient(app) as client:
        client.headers["X-Internal-Key"] = "e2e-test-key"
        # 1. Ingest a Prometheus-style CPU alert
        payload = {
            "status": "firing",
            "alerts": [
                {
                    "status": "firing",
                    "labels": {
                        "alertname": "CPU_High",
                        "instance": "host-01",
                        "metric": "cpu_percent",
                        "platform": "windows",
                    },
                    "annotations": {
                        "summary": "CPU high on host-01",
                        "description": "CPU usage is above 90%",
                    },
                    "startsAt": "2026-07-29T12:00:00Z",
                }
            ],
        }
        r = client.post("/api/v1/alerts/prometheus", json=payload, timeout=30)
        print("WEBHOOK status", r.status_code)
        try:
            print(json.dumps(r.json(), indent=2, ensure_ascii=False))
        except Exception as e:
            logging.exception("Unexpected exception: %s", e)
            print(r.text)

        webhook = r.json()
        results = webhook.get("results", [])
        assert results, "No alerts were processed"
        alert_id = results[0].get("alert_id")
        assert alert_id, "alert_id missing from webhook response"

        # 2. Read pending approvals (HITL queue)
        r = client.get("/api/v1/approvals/pending", timeout=30)
        print("PENDING status", r.status_code)
        try:
            print(json.dumps(r.json(), indent=2, ensure_ascii=False))
        except Exception as e:
            logging.exception("Unexpected exception: %s", e)
            print(r.text)

        # 3. Approve and execute the repair
        r = client.patch(f"/api/v1/approvals/{alert_id}", timeout=30)
        print("APPROVE status", r.status_code)
        try:
            print(json.dumps(r.json(), indent=2, ensure_ascii=False))
        except Exception as e:
            logging.exception("Unexpected exception: %s", e)
            print(r.text)

        # 4. Read audit trail
        r = client.get("/api/v1/audit", timeout=30)
        print("AUDIT status", r.status_code)
        try:
            print(json.dumps(r.json(), indent=2, ensure_ascii=False))
        except Exception as e:
            logging.exception("Unexpected exception: %s", e)
            print(r.text)

        return 0


if __name__ == "__main__":
    raise SystemExit(run())
