# DataAccessService

DataAccessService microservice.

## Run locally

```bash
uvicorn services.data_access_service.main_app:app --host 0.0.0.0 --port 9410
```

## Docker Compose

```bash
docker-compose -f services/data_access_service/docker-compose.yml up --build
```
