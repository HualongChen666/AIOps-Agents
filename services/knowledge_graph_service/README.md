# Knowledge Graph Service

A FastAPI microservice providing entity/relation modeling, graph construction,
query, reasoning, visualization, and specialized domain graphs for service
dependencies, infrastructure topology, and fault propagation.

## Running locally

```bash
uvicorn services.knowledge_graph_service.main_app:app --host 0.0.0.0 --port 9409
```

## Endpoints

- `GET /health`
- `GET /metrics`
- `GET /stats`
- `POST /entity/model`
- `POST /relation/model`
- `POST /graph/build`
- `POST /graph/query`
- `POST /graph/reason`
- `POST /graph/visualize`
- `POST /service-dependency/build`
- `POST /infrastructure/build`
- `POST /fault-propagation/build`
- `POST /rpc/{method}`

## Deployment

- Docker Compose: `docker-compose up`
- Kubernetes: `kubectl apply -f k8s/`
- Prometheus: scrape `http://knowledge-graph-service:9409/metrics`
