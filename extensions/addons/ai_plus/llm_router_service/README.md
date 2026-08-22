---
pack: ai-plus
enabled_by: LLM_ROUTER_ENABLED
docker_profile: ai-plus
core_dependency: False
---

# LLM Router Service

Microservice for LLM routing, cost optimization, load balancing, retries and multi-provider support.

## Run locally

```bash
uvicorn services.llm_router_service.main_app:app --host 0.0.0.0 --port 9405
```

## Docker Compose

```bash
docker-compose -f services/llm_router_service/docker-compose.yml up --build
```
