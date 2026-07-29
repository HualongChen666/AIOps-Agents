# AIOps SRE Agent – Core vs Add-ons

`aiops-agent` ships as a **core** product plus a collection of opt-in **add-on feature packs**. The core product handles Prometheus alert ingestion, normalization, approval gating, audit, and deterministic repair. Add-ons extend the agent with AI/ML, observability, topology, incident workflow, multi-cloud integrations, security, IaC, and plugin capabilities.

---

## Quick toggle

All add-ons are controlled by a single master switch and per-pack flags in `config.py` (or via environment variables):

```text
ENABLE_ADDONS=false
RAG_ENABLED=false
LLM_ROUTER_ENABLED=false
TOPOLOGY_ENABLED=false
TRACING_ENABLED=false
LOG_AGGREGATION_ENABLED=false
INCIDENT_RESPONSE_ENABLED=false
WORKFLOW_ENABLED=false
INTEGRATIONS_ENABLED=false
SECURITY_SCANNING_ENABLED=false
PENETRATION_TESTING_ENABLED=false
PLUGINS_ENABLED=false
SHARDING_ENABLED=false
I18N_ENABLED=false
DOC_GENERATION_ENABLED=false
```

Per-pack flags are only honored when `ENABLE_ADDONS=true`. Set them in your `.env` file or in `docker-compose.yml`.

---

## Feature pack reference

|Pack|What you get|Services|API routers|Flags|
|------|--------------|----------|-------------|-------|
|**Core** (always on)|Alert ingest, approval, audit, auto-heal, repair, health|`alert_service`, `agent_orchestration_service`, `repair_service`, `audit_service`|`alert`, `alert_webhook`, `autoheal`, `audit`, `health`, `hitl_approval`, `repair_scripts`, `linux`, `windows`, `guard`, `api_performance`, `cost`, `user`, `sso`|—|
|**AI Plus**|RAG runbooks, multi-LLM routing, root cause analysis|`rag_service`, `llm_router_service`, `knowledge_graph_service`|`ai`, `advanced_ai`, `ai_feedback`, `root_cause`, `rag`, `rag_history`, `qdrant`|`LLM_ROUTER_ENABLED`, `RAG_ENABLED`|
|**Observability & Topology**|Dependency graphs, metrics, tracing, logs|`topology_service`, `metrics_monitoring_service`, `distributed_tracing_service`, `tracing_service`, `log_aggregation_service`|`metrics`, `topology`, `topology_view`, `service_mesh`, `service_discovery`, `service_monitoring`, `realtime`, `tracing`, `apm`, `log`|`TOPOLOGY_ENABLED`, `TRACING_ENABLED`, `LOG_AGGREGATION_ENABLED`, `METRICS_ENABLED`|
|**SRE Operations**|Incident workflow, runbooks, capacity planning|`incident_response_service`, `incident_runbook_service`, `workflow_service`, `workflow_engine_service`, `capacity_planning_service`, `scenario_memory_service`|`workflow`, `workflow_visualization`, `hitl`, `priority`, `batch`, `notify`|`INCIDENT_RESPONSE_ENABLED`, `WORKFLOW_ENABLED`|
|**Multi-Cloud & Integrations**|Datadog, Grafana, ELK, Prometheus, GitHub, Kafka, message queues|`datadog_integration_service`, `grafana_integration_service`, `elk_stack_service`, `elasticsearch_audit_service`, `prometheus_integration_service`, `github_repository_service`, `message_queue_service`, `kafka_event_service`|`integration`, `itsm`, `dashboard`|`INTEGRATIONS_ENABLED`|
|**Security & Compliance**|Security scanning, pentest, RBAC/ABAC helpers|`security_audit_service`, `security_scanning_service`, `penetration_testing_service`, `sqlalchemy_security_service`|`enterprise`, `backup`|`SECURITY_SCANNING_ENABLED`, `PENETRATION_TESTING_ENABLED`|
|**Infrastructure & Plugin Ecosystem**|Backup/DR, IaC, sharding, plugins, localization|`velero_backup_service`, `pgbackrest_backup_service`, `backup_recovery_drill_service`, `terraform_iac_service`, `ansible_automation_service`, `cache_service`, `cache_optimization_service`, `postgresql_shard_service`, `redis_shard_service`, `qdrant_shard_service`, `plugin_system_service`, `plugin_market_service`|`chaos`, `cloud`, `mcp`, `plugin*`, `infrastructure`, `grpc`, `grpc_service`, `i18n`, `localization*`, `database_optimization`, `system_resource`, `test_*`|`PLUGINS_ENABLED`, `SHARDING_ENABLED`, `I18N_ENABLED`, `MCP_ENABLED`|
|**Documentation & Tooling**|Auto-generated docs and frontend tooling|`sphinx_documentation_service`|`doc_generator`, `documentation`, `frontend_enhancement`, `graphql`|`DOC_GENERATION_ENABLED, GRAPHQL_ENABLED`|

---

## Docker Compose usage

### Core only

```bash
docker compose up
```

### Core + AI Plus pack

```bash
docker compose -f docker-compose.yml -f docker-compose.addons.yml --profile ai-plus up
```

### Core + all add-ons

```bash
docker compose -f docker-compose.yml -f docker-compose.addons.yml --profile all-addons up
```

Available profiles: `ai-plus`, `observability`, `operations`, `integrations`, `security`, `infrastructure`, `documentation`, `all-addons`.

When `MICROSERVICE_MODE=remote`, the add-on services are reachable on the `aiops-network` Docker network and `gateway/services_client.py` can be extended with per-service URLs such as:

```text
RAG_SERVICE_URL=http://rag-service:8000
LLM_ROUTER_SERVICE_URL=http://llm-router-service:8000
TOPOLOGY_SERVICE_URL=http://topology-service:8000
INCIDENT_RESPONSE_SERVICE_URL=http://incident-response-service:8000
```

---

## Physical code organization

- Core services stay in `services/` (`alert_service`, `agent_orchestration_service`, `repair_service`, `audit_service`).
- Add-on services have been moved to `extensions/addons/<pack>/` while keeping `services` as the Python package root. `services/__init__.py` extends `__path__` to include the `extensions/addons/<pack>` directories, so all existing `import services.<name>` and `from services.<name> import ...` statements continue to work.

Runtime behavior

- `main.py` imports every `api/` router at startup but only mounts add-on routers when `ENABLE_ADDONS` and the matching pack flag are `true`.
- The lifespan `_safe_init` helper skips all non-core 7-Layer and optional manager initializations when `ENABLE_ADDONS=false`. Core inits such as database setup, PID registration, ABAC policies, and business metrics always run.
- `/docs` (Swagger UI) reflects only the mounted routers, so core-only mode does not display `/rag`, `/chaos`, `/cloud`, `/plugin*`, or other add-on endpoints.

---

## Writing a new add-on

1. Create a `extensions/addons/<pack>/<your_addon>_service/` FastAPI microservice or a new `api/<your_addon>_router.py`.
2. Add a `YOUR_ADDON_ENABLED` flag to `config.py` and `.env.example`.
3. Add the router to `ADDON_ROUTERS` in `main.py` with the new flag.
4. Add a service entry to `docker-compose.addons.yml` under the appropriate `profiles`.
5. Write tests under `tests/` and mark add-on tests with `@pytest.mark.addons`.
6. Update this document and `README.md`.
