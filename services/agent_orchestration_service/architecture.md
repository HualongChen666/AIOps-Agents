# Agent Orchestration Service Architecture (Task 33.1)

## Overview

The Agent Orchestration Service is a FastAPI microservice that coordinates
multiple specialized agents to solve AIOps tasks.

## Service Decomposition

- **Task decomposition**: `AgentOrchestrator.decompose_task` splits a task
  into subtasks based on keyword heuristics.
- **Multi-agent collaboration**: `AgentOrchestrator.collaborate` dispatches
  agents and aggregates their outputs.
- **Execution coordination**: `AgentOrchestrator.coordinate` executes a plan
  of subtasks sequentially or in parallel.
- **Result aggregation**: `AgentOrchestrator.aggregate` combines agent
  outputs by concatenation, merging, or voting.
- **Error handling**: `AgentOrchestrator.handle_error` classifies errors and
  proposes recovery strategies.
- **Specialized agents**: monitor, diagnostic, repair, and analysis agents.
- **LangGraph integration**: optional graph execution with deterministic
  fallback.
- **REST API**: `/health`, `/metrics`, `/stats`, `/decompose`, `/run/{agent_type}`,
  `/coordinate`, `/collaborate`, `/aggregate`, `/handle-error`, `/rpc/{method}`
- **Monitoring**: Prometheus metrics
- **gRPC**: in-memory RPC server/client for inter-service communication

## Deployment

- Docker Compose for local development
- Kubernetes for production
- Prometheus for monitoring
