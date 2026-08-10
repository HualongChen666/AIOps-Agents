# Architecture

## Overview

`aiops-agent` is a FastAPI application that sits between Prometheus Alertmanager
and your remediation tooling. It turns webhook payloads into a normalized alert,
analyzes the alert, selects or generates a repair runbook, and enforces an
approval gate before any command is executed.

## Data flow

1. **Ingest** — `POST /api/v1/alerts/prometheus` receives Alertmanager JSON.
2. **Normalize** — `core/alert_providers/prometheus.py` converts it to a uniform
 alert model `{id, title, metric, severity, platform, ...}`.
3. **Analyze** — `core/heal_graph.py` builds a state object. If an LLM is
 configured, it proposes a root cause; otherwise the rule engine selects a
 runbook.
4. **Select runbook** — `core/auto_heal.py` and the global
 `repair_script_library` pick `cpu_high_script`, `ipmi_power_cycle`,
 `redfish_reboot`, etc.
5. **Approve** — `GET/POST /api/v1/approvals` lets an operator review the
 generated plan.
6. **Execute** — `apply_fix` runs the runbook. Hardware scripts are dry-run
 unless `HARDWARE_EXECUTE_ENABLED=true`.
7. **Verify** — `evaluate` checks the result and records metrics plus a snapshot
 for rollback/audit.

## Core vs Add-ons

`main.py` is the converged API gateway. By default it mounts only the **core**
routers (alerts, approvals, audit, autoheal, health, repair, user/SSO, etc.) and
initializes only the core lifecycle components. All other `api/` routers and
7-Layer managers belong to opt-in **add-on feature packs**.

Add-ons are disabled by default via `ENABLE_ADDONS=false` in `config.py`.
Individual packs are toggled with flags such as `RAG_ENABLED`,
`TOPOLOGY_ENABLED`, `WORKFLOW_ENABLED`, `PLUGINS_ENABLED`, and
`SECURITY_SCANNING_ENABLED`. When `ENABLE_ADDONS=true` and a pack flag is
true, `main.py` mounts the corresponding routers and the lifespan manager
initializes the relevant services. In `MICROSERVICE_MODE=remote` the gateway
forwards add-on calls to the standalone services defined in
`docker-compose.addons.yml`.

## Key components

- `api/` — FastAPI routers. Core routers are always mounted; add-on routers are
 gated by `ENABLE_ADDONS` and pack flags.
- `core/` — Heal graph, alert providers, auto-heal logic, repair script library.
- `extensions/hardware_remediation/` — Dry-run IPMI, Redfish, RAID, SMART,
 Kubernetes, and ticket scripts.
- `extensions/addons/<pack>/` — Opt-in domain microservices physically grouped
 by feature pack (AI Plus, Observability, Operations, Integrations, Security,
 Infrastructure, Documentation). `services/__init__.py` adds these directories
 to the `services` package `__path__`, so `import services.<name>` still works
 without changing any import statements. Core services remain in `services/`.
- `tests/` — Unit, API, integration, and E2E tests. Use `pytest -m core` for
 core-only tests and `pytest -m addons` for add-on tests.

## Deployment targets

Single container via `docker compose`, or Kubernetes using the manifests under
`k8s_manifests/` and `helm/`.
