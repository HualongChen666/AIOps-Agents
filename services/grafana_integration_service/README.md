# Grafana Integration Service

A FastAPI microservice for Grafana Integration operations.

## Run

```bash
uvicorn services.grafana_integration_service.main_app:app --host 0.0.0.0 --port 9531
```

## Docker Compose

```bash
cd services/grafana_integration_service
docker-compose up -d
```
