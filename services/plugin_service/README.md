# Plugin Service

Plugin microservice: plugin registration, execution tracking and configuration
management. The business logic lives in `service.py` (used in-process by
`api/plugin_router.py`); this package additionally ships a standalone HTTP
service so it can run as an independent microservice like the other four.

## Layout

| File | Role |
|------|------|
| `main_app.py` | FastAPI application (HTTP surface + health + metrics + RPC) |
| `main.py` | Standalone runner: `python -m services.plugin_service.main [port]` |
| `config.py` | `BaseSettings`, env prefix `PLUGIN_SERVICE_` |
| `db.py` | Sync engine/sessionmaker; in-memory SQLite when `USE_IN_MEMORY=true` |
| `repository.py` | SQLAlchemy repositories (plugin / execution / config) |
| `service.py` | Business logic |
| `saga.py` | Saga with compensation for plugin registration |
| `metrics.py` | Prometheus counters/histograms |
| `health_check.py` | Health payload |
| `grpc/` | In-process RPC server + client (mirrors audit service) |
| `k8s/` | Deployment + Service manifests |

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Liveness + plugin count |
| GET | `/metrics` | Prometheus exposition |
| GET | `/stats` | Aggregate plugin/execution counters |
| POST/GET | `/plugins` | Create / list plugins |
| GET/PUT/DELETE | `/plugins/{plugin_id}` | Fetch / update / delete |
| GET | `/plugins/by-name/{name}` | Lookup by unique name |
| POST | `/plugins/{name}/run` | Execute a plugin, persist the execution |
| POST/GET | `/executions` | Record / list executions |
| GET | `/executions/{execution_id}` | Fetch an execution |
| POST/GET | `/configs` | Create config / (list via by-plugin) |
| GET/PUT/DELETE | `/configs/{config_id}` | Fetch / update / delete config |
| GET | `/configs/by-plugin/{plugin_id}` | Config for a plugin |
| POST | `/sagas/plugin-registration` | Register plugin + config atomically |
| GET/POST | `/rpc`, `/rpc/{method}` | RPC dispatch |

## Run

```bash
# in-memory (no dependencies)
PLUGIN_SERVICE_USE_IN_MEMORY=true python -m services.plugin_service.main 9501

# against PostgreSQL
PLUGIN_SERVICE_DATABASE_URL=postgresql+psycopg2://postgres:secret@localhost:5432/aiops \
  python -m services.plugin_service.main 9501
```

## Docker

```bash
docker compose -f services/plugin_service/docker-compose.yml up --build
```

## Kubernetes

Create the shared database secret first (see
`services/k8s/db-secret.example.yaml`), then apply `k8s/deployment.yaml`. The
manifest injects `PLUGIN_SERVICE_DATABASE_URL` from that secret and runs with
`PLUGIN_SERVICE_USE_IN_MEMORY=false`.

## Tests

```bash
PLUGIN_SERVICE_USE_IN_MEMORY=true pytest tests/services/test_plugin_service_coverage.py
```
