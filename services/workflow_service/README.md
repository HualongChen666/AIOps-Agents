# Workflow Service

Microservice for workflow orchestration, scheduling, state machine management, and execution monitoring.

## Services

- `workflow-orchestrator` (port 9201): API gateway and orchestration
- `workflow-scheduler` (port 9202): Task scheduling and queue management
- `workflow-executor` (port 9203): Execution, monitoring, and retry

## Run locally

```bash
uvicorn services.workflow_service.workflow_orchestrator_app:app --host 0.0.0.0 --port 9201
uvicorn services.workflow_service.scheduler_app:app --host 0.0.0.0 --port 9202
uvicorn services.workflow_service.executor_app:app --host 0.0.0.0 --port 9203
```

## Docker Compose

```bash
docker-compose -f services/workflow_service/docker-compose.yml up --build
```
