---
pack: operations
enabled_by: INCIDENT_RESPONSE_ENABLED
docker_profile: operations
core_dependency: False
---

# Scenario Memory Service

FastAPI microservice for episodic and semantic memory.

## Run locally

```bash
uvicorn services.scenario_memory_service.main_app:app --reload --port 9408
```

## Endpoints

- `GET /health` - health check
- `GET /metrics` - Prometheus metrics
- `GET /stats` - service statistics
- `POST /store/event` - store an event memory
- `POST /search/similar` - vector similarity search
- `POST /learn/experience` - learn from experience
- `POST /accumulate/knowledge` - accumulate knowledge triples
- `POST /recognize/pattern` - pattern recognition
- `POST /memory/short-term/{key}` - store short-term memory
- `GET /memory/short-term/{key}` - retrieve short-term memory
- `POST /memory/long-term/{key}` - store long-term memory
- `GET /memory/long-term/{key}` - retrieve long-term memory
- `POST /memory/semantic` - store semantic memory
- `GET /memory/semantic/{entity}` - retrieve semantic memory
- `POST /memory/procedural` - store procedural memory
- `GET /memory/procedural/{key}` - retrieve procedural memory
- `POST /rpc/{method}` - RPC dispatcher
