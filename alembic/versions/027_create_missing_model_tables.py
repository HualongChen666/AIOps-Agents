# -*- coding: utf-8 -*-
"""Create the model tables that migrations 001-026 never created.

``core/models.py`` declares 228 tables while the previous migration chain only
created 136 of them, so ``alembic upgrade head`` could not produce a schema the
application can run against.  The application silently compensated with
``Base.metadata.create_all`` at startup (core/db_engine.py, core/auth_db.py),
which is exactly why the gap went unnoticed.

This revision creates the 95 missing tables from the current model metadata in
dependency order, so a fresh ``alembic upgrade head`` yields a complete schema.

Note: migration 001 also creates three tables that have no ORM model
(``alert_history``, ``verify_records``, ``hardware_remediation_log``).  They are
deliberately left untouched here; dropping them is a product decision tracked
separately.

Revision ID: 027
Revises: 026
Create Date: 2026-09-10
"""
from alembic import op

revision = '027'
down_revision = '026'
branch_labels = None
depends_on = None

#: Tables declared in core/models.py that no migration created.  Computed from
#: the model ``__tablename__`` values minus the ``op.create_table`` calls in
#: revisions 001-026.
MISSING_TABLES = (
    'ai_capability_evaluations',
    'ai_evaluation_tasks',
    'ai_graph_edges',
    'ai_vectorizer_configs',
    'ai_vectorizer_jobs',
    'alert_acknowledgements',
    'alert_aggregation_rules',
    'alert_configurations',
    'alert_deduplication_rules',
    'alert_dynamic_threshold_rules',
    'alert_escalation_rules',
    'alert_forwarding_rules',
    'alert_integrations',
    'alert_routing_rules',
    'alert_rules',
    'alert_suppression_rules',
    'alert_webhook_configs',
    'alerts',
    'backups',
    'capacity_alerts',
    'capacity_benchmarks',
    'capacity_forecasts',
    'capacity_reservations',
    'capacity_resource_pools',
    'capacity_scenarios',
    'capacity_simulations',
    'capacity_thresholds',
    'capacity_trends',
    'capacity_utilization',
    'configs',
    'dashboard_layouts',
    'dashboard_widgets',
    'database_backups',
    'database_indexes',
    'database_migrations',
    'database_optimizations',
    'documentation_documents',
    'documentation_reviews',
    'documentation_templates',
    'documentation_versions',
    'enterprise_audit_logs',
    'enterprise_permissions',
    'enterprise_roles',
    'enterprise_settings',
    'enterprise_tenants',
    'enterprise_users',
    'infrastructure_provisioning_tasks',
    'infrastructure_resources',
    'itsm_changes',
    'itsm_incidents',
    'itsm_knowledge_base',
    'itsm_problems',
    'itsm_service_catalog',
    'itsm_slas',
    'knowledge',
    'localization_adapters',
    'localization_languages',
    'localization_resources',
    'localization_translations',
    'maturity_assessments',
    'metrics',
    'notification_channels',
    'performance_baselines',
    'performance_metrics',
    'performance_regressions',
    'performance_trends',
    'priority_history',
    'priority_rules',
    'priority_scores',
    'realtime_events',
    'realtime_streams',
    'realtime_subscriptions',
    'realtime_webhooks',
    'root_cause_conclusions',
    'root_cause_evidence',
    'root_cause_experiments',
    'root_cause_hypotheses',
    'service_monitor_alerts',
    'service_monitor_dashboards',
    'slo_alerts',
    'slo_definitions',
    'slo_objectives',
    'snapshots',
    'system_metrics',
    'tenant_configs',
    'tenant_members',
    'tenant_settings',
    'test_coverage_comparisons',
    'test_coverage_reports',
    'test_coverage_targets',
    'test_executions',
    'test_suites',
    'users',
    'workflow_executions',
    'workflows',
)


def _tables():
    from core.models import Base

    return [Base.metadata.tables[name] for name in MISSING_TABLES
            if name in Base.metadata.tables]


def upgrade():
    from core.models import Base

    Base.metadata.create_all(bind=op.get_bind(), tables=_tables(), checkfirst=True)


def downgrade():
    from core.models import Base

    Base.metadata.drop_all(bind=op.get_bind(), tables=_tables(), checkfirst=True)
