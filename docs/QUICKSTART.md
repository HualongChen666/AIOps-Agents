# Quick Start

Run `aiops-agent` locally in five minutes.

## 1. Clone and configure

```bash
git clone https://github.com/aiops-team/aiops-agent.git
cd aiops-agent
cp env.example .env
```

`.env` is already populated with safe defaults: every command starts in dry-run
mode. You do not need real cloud credentials or LLM keys for the demo.

## 2. Start the stack

```bash
docker compose up
```

This starts the API (`http://localhost:8000`), PostgreSQL, Redis, and Prometheus.

## 3. Open the API docs

Visit `http://localhost:8000/docs` in your browser.

## 4. Send a Prometheus alert

```bash
curl -X POST http://localhost:8000/api/v1/alerts/prometheus \
  -H "Content-Type: application/json" \
  -d @examples/curl/createAnomaly.sh
```

The response contains `alert_id` and `approval_id`.

## 5. Review and approve

```bash
# list pending approvals
curl http://localhost:8000/api/v1/approvals/pending

# approve the alert
curl -X PATCH http://localhost:8000/api/v1/approvals/<alert_id>
```

Because `HARDWARE_EXECUTE_ENABLED=false` and `HEAL_DRY_RUN=true`, all generated
commands are simulated and no real infrastructure is touched.

---

## Demo

A 5-minute asciinema walkthrough will be added here. Until then, follow the
steps above to see a complete alert-to-dry-run-repair flow.
