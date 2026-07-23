# User Service

Microservice for user management, RBAC, organization tree, OAuth2/JWT authentication, sessions, and audit logs.

## Run locally

```bash
uvicorn services.user_service.main_app:app --host 0.0.0.0 --port 9401
```

## Docker Compose

```bash
docker-compose -f services/user_service/docker-compose.yml up --build
```
