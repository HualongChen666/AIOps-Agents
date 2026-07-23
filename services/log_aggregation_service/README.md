# Log Aggregation Service

A FastAPI microservice for Log Aggregation operations.

## Run

```bash
uvicorn services.log_aggregation_service.main_app:app --host 0.0.0.0 --port 9567
```

## Docker Compose

```bash
cd services/log_aggregation_service
docker-compose up -d
```
