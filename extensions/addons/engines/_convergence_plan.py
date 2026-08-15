# -*- coding: utf-8 -*-
"""Concrete convergence plan for the 7 addon shared engines.

Each engine entry lists which existing modules/* (or core.* where explicitly
allowed) capability should be reused for a given method.  A value of ``None``
means no importable, directly equivalent component exists and the current real
``requests``/``subprocess``/CLI implementation should be kept for now.
"""

CONVERGENCE_PLAN = {
    "monitoring_provider": {
        "engine_path": "extensions/addons/engines/monitoring_provider.py",
        "reuses": {
            "query": None,
            "push_alert": (
                "modules.observability.smart_alerting",
                "SmartAlertingEngine.evaluate_metrics",
            ),
            "get_topology": (
                "modules.apm.dependency_analyzer",
                "DependencyAnalyzer.discover_topology",
            ),
            "logs": None,
            "traces": None,
            "health": None,
        },
        "notes": (
            "SmartAlertingEngine.evaluate_metrics can build/evaluate alert rules; "
            "the engine should still handle the HTTP POST to Alertmanager/Datadog. "
            "DependencyAnalyzer.discover_topology returns a DependencyTopology object "
            "whose .to_dict() gives the nodes/edges shape the engine already returns. "
            "No equivalent reusable remote log/trace query or HTTP/CLI health probe exists."
        ),
    },
    "storage_driver": {
        "engine_path": "extensions/addons/engines/storage_driver.py",
        "reuses": {
            "cache_get": None,
            "cache_set": None,
            "sql": (
                "modules.storage.postgres.storage",
                "PostgreSQLStorage.execute_query",
            ),
            "vector_create_collection": None,
            "vector_upsert": (
                "modules.analyze.runbook.vector_store",
                "VectorStore.add_documents_batch",
            ),
            "vector_search": (
                "modules.analyze.runbook.vector_store",
                "VectorStore.search",
            ),
            "get_stats": None,
        },
        "notes": (
            "PostgreSQLStorage.execute_query covers SQL execution with proper pooling. "
            "VectorStore is content/RAG-oriented (text embeddings, semantic search), "
            "so vector_upsert/search reuse requires an adapter from the engine's raw "
            "id/vector/payload model to VectorStore's document model. No reusable Redis "
            "cache or aggregate stats component was found."
        ),
    },
    "infra_executor": {
        "engine_path": "extensions/addons/engines/infra_executor.py",
        "reuses": {
            "CliExecutor.run": None,
            "AnsibleExecutor.run": (
                "modules.execute.auto_heal.playbook_manager",
                "PlaybookManager.execute_playbook",
            ),
            "TerraformExecutor.run": None,
            "HelmExecutor.run": None,
            "K8sExecutor.run": None,
            "BaseInfraService.execute_operation": None,
        },
        "notes": (
            "PlaybookManager.execute_playbook is the only importable execution wrapper "
            "that matches an existing executor (Ansible). K8s operations can be migrated "
            "to AutoHealOperator for healing-oriented flows, but there is no generic "
            "kubectl run method. Generic CLI/Terraform/Helm remain subprocess-based."
        ),
    },
    "security_scanner": {
        "engine_path": "extensions/addons/engines/security_scanner.py",
        "reuses": {
            "scan_code": None,
            "scan_dependencies": None,
            "scan_api": None,
            "scan_network": None,
            "scan_container": None,
            "check_license": None,
            "check_sql_injection": None,
            "check_api_baseline": None,
        },
        "notes": (
            "No equivalent reusable security scanner, license checker, SQL-injection "
            "regex rule set, or OpenAPI baseline validator exists in modules/*. Keep "
            "the existing subprocess wrappers for bandit/semgrep/safety/zap/nmap/trivy."
        ),
    },
    "connector_bus": {
        "engine_path": "extensions/addons/engines/connector_bus.py",
        "reuses": {
            "produce": None,
            "consume": None,
            "publish_queue": None,
            "subscribe_queue": None,
            "webhook_send": None,
            "github_request": None,
        },
        "notes": (
            "No reusable messaging/integration bus exists in modules/*; the Kafka/"
            "RabbitMQ/SQS/HTTP webhook implementations are engine-specific CLI wrappers."
        ),
    },
    "workflow_engine": {
        "engine_path": "extensions/addons/engines/workflow_engine.py",
        "reuses": {
            "run_workflow": (
                "core.ai.langgraph.workflow",
                "Workflow.execute",
            ),
            "get_scenario_memory": (
                "modules.analyze.runbook.vector_store",
                "VectorStore.search",
            ),
            "capacity_analysis": None,
            "RunbookRunner.run_runbook": (
                "modules.execute.auto_heal.playbook_manager",
                "PlaybookManager.execute_playbook",
            ),
        },
        "notes": (
            "core.ai.langgraph.workflow.Workflow.execute is a graph-based state-machine "
            "runner; converging the step-list engine requires translating each step type "
            "(http/cli/python/decision) into a WorkflowNode. VectorStore.search replaces "
            "scenario-memory lookup. Capacity recommendation logic has no direct reusable "
            "counterpart because modules.analyze.capacity is currently unimportable."
        ),
    },
    "doc_policy_engine": {
        "engine_path": "extensions/addons/engines/doc_policy_engine.py",
        "reuses": {
            "DocEngine.build_docs": None,
            "PolicyEngine.lint_openapi": None,
            "PolicyEngine.validate_schema": None,
            "PolicyEngine.load_config": (
                "core.config_manager",
                "ConfigManager.get_config_value",
            ),
            "PolicyEngine.user_lookup": (
                "core.authentication",
                "get_user_by_username",
            ),
            "PolicyEngine.plugin_index": None,
            "PolicyEngine.plugin_load": None,
            "PolicyEngine.plugin_unload": None,
        },
        "notes": (
            "ConfigManager.get_config_value (core.config_manager) can replace key lookup "
            "from JSON/YAML/env once the key path is expressed in dot-notation. "
            "core.authentication.get_user_by_username is the real user lookup the engine "
            "already falls back to. No reusable Sphinx doc builder, OpenAPI linter, schema "
            "validator, or plugin loader/unloader was found."
        ),
    },
}
