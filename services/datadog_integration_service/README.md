# Datadog Integration Service

A FastAPI microservice for Datadog Integration operations.

## Run

```bash
uvicorn services.datadog_integration_service.main_app:app --host 0.0.0.0 --port 9533
```

## Docker Compose

```bash
cd services/datadog_integration_service
docker-compose up -d
```
