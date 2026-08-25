# -*- coding: utf-8 -*-
import logging

from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from core.authentication import get_current_active_user
from core.database import Base
from core.metrics_history import METRICS_HISTORY as metrics_history
from main import app

"""End-to-end test: Prometheus alert -> approval -> repair -> audit."""
import json
import os
import sys
import threading
import warnings
from datetime import datetime

# Suppress known third-party deprecation warnings before importing TestClient.
warnings.filterwarnings("ignore", message=".*httpx.*starlette.*testclient.*deprecated.*")
warnings.filterwarnings("ignore", message="pkg_resources is deprecated as an API.*")

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


import core.models  # noqa: F401

app.dependency_overrides[get_current_active_user] = lambda: {"username": "e2e", "role": "admin"}

# Create the same SQLite file that the async engine will use.
engine = create_engine("sqlite:///e2e.db")
Base.metadata.create_all(engine)


def run():
    with TestClient(app) as client:
        client.headers["X-Internal-Key"] = "e2e-test-key"

        # Pre-seed CPU metrics so metric_threshold verification has enough samples.
        for _ in range(3):
            metrics_history.push(
                cpu=92.0, memory=50.0, net_in=0.0, timestamp=datetime.now().strftime("%H:%M:%S")
            )

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
        if not results:
            raise ValueError("No alerts were processed")
        alert_id = results[0].get("alert_id")
        if not alert_id:
            raise ValueError("alert_id missing from webhook response")

        # 2. Read pending approvals (HITL queue)
        r = client.get("/api/v1/approvals/pending", timeout=30)
        print("PENDING status", r.status_code)
        try:
            print(json.dumps(r.json(), indent=2, ensure_ascii=False))
        except Exception as e:
            logging.exception("Unexpected exception: %s", e)
            print(r.text)

        # 3. Approve and execute the repair
        # While the repair is running, push lower CPU values into metrics_history
        # so the metric_threshold verification sees a real drop.
        def _drop_cpu():
            for _ in range(5):
                metrics_history.push(
                    cpu=8.0, memory=50.0, net_in=0.0, timestamp=datetime.now().strftime("%H:%M:%S")
                )

        timer = threading.Timer(1.0, _drop_cpu)
        timer.start()

        r = client.patch(f"/api/v1/approvals/{alert_id}", timeout=30)
        timer.join()
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
