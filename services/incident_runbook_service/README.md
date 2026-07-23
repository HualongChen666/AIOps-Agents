# Incident Runbook Service

A FastAPI microservice for Incident Runbook operations.

## Run

```bash
uvicorn services.incident_runbook_service.main_app:app --host 0.0.0.0 --port 9547
```

## Docker Compose

```bash
cd services/incident_runbook_service
docker-compose up -d
```
