---
pack: core
enabled_by: N/A (always on)
docker_profile: core
core_dependency: True
---

# Agent Orchestration Service

Microservice for multi-agent collaboration and task orchestration.
Provides task decomposition, execution coordination, result aggregation,
error handling, monitoring/diagnostic/repair/analysis agents, and
LangGraph integration with deterministic fallbacks.

## Run locally

```bash
uvicorn services.agent_orchestration_service.main_app:app --host 0.0.0.0 --port 9407
```

## Docker Compose

```bash
docker-compose -f services/agent_orchestration_service/docker-compose.yml up --build
```
