---
pack: observability
enabled_by: TOPOLOGY_ENABLED
docker_profile: observability
core_dependency: False
---

# Topology Service

Microservice for service topology discovery, dependency modeling, impact analysis, and visualization.

## Services

- `topology-orchestrator` (port 9101): API gateway and orchestration
- `topology-analyzer` (port 9102): Dependency modeling and impact analysis
- `topology-visualizer` (port 9103): D3.js visualization and WebSocket real-time updates

## Run locally

```bash
uvicorn services.topology_service.orchestrator:app --host 0.0.0.0 --port 9101
uvicorn services.topology_service.analyzer:app --host 0.0.0.0 --port 9102
uvicorn services.topology_service.visualizer:app --host 0.0.0.0 --port 9103
```

## Docker Compose

```bash
docker-compose -f services/topology_service/docker-compose.yml up --build
```
