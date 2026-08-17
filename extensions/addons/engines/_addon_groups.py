"""Mapping of addon group definitions to actual filesystem paths.

This file is auto-generated as part of the addon refactor preparation.
Engine classes are left as placeholders (None) until they are assigned.
"""

ADDON_GROUPS = {
    "observability": {
        "engine": "extensions/addons/engines/monitoring_provider",
        "addons": [
            (
                "metrics_monitoring_service",
                "extensions/addons/observability/metrics_monitoring_service",
            ),
            ("alert_rule_service", "extensions/addons/infrastructure/alert_rule_service"),
            (
                "performance_monitoring_service",
                "extensions/addons/infrastructure/performance_monitoring_service",
            ),
            (
                "cloud_monitoring_service",
                "extensions/addons/infrastructure/cloud_monitoring_service",
            ),
            ("log_aggregation_service", "extensions/addons/observability/log_aggregation_service"),
            ("tracing_service", "extensions/addons/observability/tracing_service"),
            (
                "distributed_tracing_service",
                "extensions/addons/observability/distributed_tracing_service",
            ),
            ("topology_service", "extensions/addons/observability/topology_service"),
            (
                "datacenter_visualization_service",
                "extensions/addons/infrastructure/datacenter_visualization_service",
            ),
            (
                "prometheus_integration_service",
                "extensions/addons/integrations/prometheus_integration_service",
            ),
            (
                "grafana_integration_service",
                "extensions/addons/integrations/grafana_integration_service",
            ),
            (
                "datadog_integration_service",
                "extensions/addons/integrations/datadog_integration_service",
            ),
            (
                "elasticsearch_audit_service",
                "extensions/addons/integrations/elasticsearch_audit_service",
            ),
        ],
    },
    "data_platform": {
        "engine": "extensions/addons/engines/storage_driver",
        "addons": [
            ("cache_service", "extensions/addons/infrastructure/cache_service"),
            ("redis_shard_service", "extensions/addons/infrastructure/redis_shard_service"),
            (
                "postgresql_shard_service",
                "extensions/addons/infrastructure/postgresql_shard_service",
            ),
            ("qdrant_shard_service", "extensions/addons/infrastructure/qdrant_shard_service"),
            (
                "vector_retrieval_service",
                "extensions/addons/infrastructure/vector_retrieval_service",
            ),
            (
                "cache_optimization_service",
                "extensions/addons/infrastructure/cache_optimization_service",
            ),
            (
                "database_optimization_service",
                "extensions/addons/infrastructure/database_optimization_service",
            ),
            ("data_access_service", "extensions/addons/infrastructure/data_access_service"),
        ],
    },
    "infra_automation": {
        "engine": "extensions/addons/engines/infra_executor",
        "addons": [
            (
                "ansible_automation_service",
                "extensions/addons/infrastructure/ansible_automation_service",
            ),
            ("terraform_iac_service", "extensions/addons/infrastructure/terraform_iac_service"),
            (
                "kubernetes_orchestration_service",
                "extensions/addons/infrastructure/kubernetes_orchestration_service",
            ),
            (
                "automated_deployment_service",
                "extensions/addons/infrastructure/automated_deployment_service",
            ),
            ("automated_ops_service", "extensions/addons/infrastructure/automated_ops_service"),
            ("velero_backup_service", "extensions/addons/infrastructure/velero_backup_service"),
            (
                "pgbackrest_backup_service",
                "extensions/addons/infrastructure/pgbackrest_backup_service",
            ),
            (
                "backup_recovery_drill_service",
                "extensions/addons/infrastructure/backup_recovery_drill_service",
            ),
            ("chaos_mesh_service", "extensions/addons/infrastructure/chaos_mesh_service"),
            ("service_mesh_service", "extensions/addons/infrastructure/service_mesh_service"),
        ],
    },
    "security": {
        "engine": "extensions/addons/engines/security_scanner",
        "addons": [
            ("security_scanning_service", "extensions/addons/security/security_scanning_service"),
            ("security_audit_service", "extensions/addons/security/security_audit_service"),
            (
                "penetration_testing_service",
                "extensions/addons/security/penetration_testing_service",
            ),
            (
                "sqlalchemy_security_service",
                "extensions/addons/security/sqlalchemy_security_service",
            ),
            (
                "fastapi_security_service",
                "extensions/addons/infrastructure/fastapi_security_service",
            ),
            (
                "open_source_license_service",
                "extensions/addons/infrastructure/open_source_license_service",
            ),
        ],
    },
    "integration": {
        "engine": "extensions/addons/engines/connector_bus",
        "addons": [
            ("kafka_event_service", "extensions/addons/integrations/kafka_event_service"),
            ("message_queue_service", "extensions/addons/integrations/message_queue_service"),
            (
                "github_repository_service",
                "extensions/addons/integrations/github_repository_service",
            ),
            ("elk_stack_service", "extensions/addons/integrations/elk_stack_service"),
        ],
    },
    "workflow": {
        "engine": "extensions/addons/engines/workflow_engine",
        "addons": [
            ("workflow_engine_service", "extensions/addons/operations/workflow_engine_service"),
            ("workflow_service", "extensions/addons/operations/workflow_service"),
            ("incident_runbook_service", "extensions/addons/operations/incident_runbook_service"),
            ("capacity_planning_service", "extensions/addons/operations/capacity_planning_service"),
            ("scenario_memory_service", "extensions/addons/operations/scenario_memory_service"),
        ],
    },
    "governance": {
        "engine": "extensions/addons/engines/doc_policy_engine",
        "addons": [
            (
                "sphinx_documentation_service",
                "extensions/addons/documentation/sphinx_documentation_service",
            ),
            ("api_standards_service", "extensions/addons/infrastructure/api_standards_service"),
            ("data_standards_service", "extensions/addons/infrastructure/data_standards_service"),
            ("config_service", "extensions/addons/infrastructure/config_service"),
            ("user_service", "extensions/addons/infrastructure/user_service"),
            ("plugin_market_service", "extensions/addons/infrastructure/plugin_market_service"),
            ("plugin_system_service", "extensions/addons/infrastructure/plugin_system_service"),
        ],
    },
}
